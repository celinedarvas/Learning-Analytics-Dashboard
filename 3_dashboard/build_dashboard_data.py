"""Pre-compute every chart/table the dashboard needs into a single JSON file.

Pipeline:
  1. Load four heterogeneous formats (CSV, NDJSON, Parquet, YAML)
  2. Clean events (dedupe, regex-validate student_id, drop blank timestamps)
  3. Anonymize all student-identifying fields with a deterministic mapping
     so the published artifact contains zero personally-identifying information
  4. Compute domain coverage, accuracy by difficulty / cohort, top performers,
     response-time distribution, sequence-position trend, and synthesis stats
  5. Write `dashboard_data.json` and inline it into `index.html`
  6. Optionally write anonymized derivative datasets to `anonymized_data/`
     so the project is reproducible from a public repo without exposing PII

Usage:
    python build_dashboard_data.py
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
QBANKS = ROOT / "question_banks"
HERE = Path(__file__).resolve().parent
OUT = HERE / "dashboard_data.json"
TEMPLATE = HERE / "index.template.html"
HTML_OUT = HERE / "index.html"
PROFILE = HERE / "profile.json"
ANON_DIR = ROOT / "1_data"

VALID_ID = re.compile(r"^U\d{8}$")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def to_native(obj: Any) -> Any:
    """Recursively convert numpy/pandas scalars into JSON-safe Python types."""
    if isinstance(obj, dict):
        return {str(k): to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_native(v) for v in obj]
    if obj is None:
        return None
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:  # pragma: no cover
            pass
    return obj


def load_profile() -> dict:
    """Load author / project metadata. Placeholders (YOUR_*) are filtered later."""
    if not PROFILE.exists():
        return {}
    return json.loads(PROFILE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def load_question_banks() -> pd.DataFrame:
    rows = []
    for path in sorted(QBANKS.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as fh:
            # safe_load avoids the unsafe FullLoader/UnsafeLoader (codeguard XML/serialization rule)
            bank = yaml.safe_load(fh)
        domain = bank.get("domain") or path.stem
        for q in bank.get("questions", []):
            qtype = (q.get("type") or "").lower()
            if qtype == "self_report":
                continue
            rows.append(
                {
                    "domain": domain,
                    "question_id": q.get("id") or q.get("question_id"),
                    "sub_skill": q.get("sub_skill"),
                    "difficulty": q.get("difficulty"),
                    "dimension": q.get("dimension"),
                    "correct_answer": q.get("correct_answer"),
                }
            )
    return pd.DataFrame(rows)


def load_sessions() -> pd.DataFrame:
    records = []
    with (DATA / "sessions.json").open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    df = pd.json_normalize(records, sep="_")
    df["started_at"] = pd.to_datetime(df["started_at"], utc=True, errors="coerce")
    df["ended_at"] = pd.to_datetime(df["ended_at"], utc=True, errors="coerce")
    return df


def load_events() -> pd.DataFrame:
    df = pd.read_csv(DATA / "events.csv")
    df = df.drop_duplicates()
    df = df[df["student_id"].astype(str).str.match(VALID_ID, na=False)]
    df = df[df["timestamp"].notna() & (df["timestamp"].astype(str).str.strip() != "")]
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=False)
    return df


# ---------------------------------------------------------------------------
# Anonymization
# ---------------------------------------------------------------------------
def build_id_map(student_ids: list[str]) -> dict[str, dict[str, str]]:
    """Deterministic mapping from real student_id -> portfolio-safe pseudonyms.

    Sorted-then-numbered so the same input always yields the same output, but
    the order in the source data does not leak (we sort first).
    """
    mapping: dict[str, dict[str, str]] = {}
    for i, sid in enumerate(sorted(set(student_ids)), start=1):
        n = f"{i:03d}"
        mapping[sid] = {
            "student_id": f"S-{n}",
            "uniqname": f"learner{n}",
            "first_name": f"Student",
            "last_name": n,
            "display": f"Student {n}",
        }
    return mapping


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    students = pd.read_csv(DATA / "students.csv")
    sessions = load_sessions()
    responses = pd.read_parquet(DATA / "responses.parquet")
    events = load_events()
    questions = load_question_banks()

    # ------------------------------------------------------------------
    # Anonymize. Build the mapping from the union of all student IDs we
    # see across files (defensive: events.csv had a few malformed IDs we
    # already filtered out).
    # ------------------------------------------------------------------
    all_ids: set[str] = set()
    for df in (students, sessions, responses, events):
        if "student_id" in df.columns:
            all_ids.update(df["student_id"].dropna().astype(str).tolist())
    id_map = build_id_map(sorted(all_ids))

    def remap_id(s: Any) -> Any:
        return id_map.get(s, {}).get("student_id", s)

    def remap_uniqname_from_old(s: Any) -> Any:
        # Look up by the *original* student_id before we rewrite the column.
        return id_map.get(s, {}).get("uniqname", None)

    # Anonymize students. Build display name from the new pseudonymized ID
    # (e.g. "S-001" -> "Student 001"). Drop every direct identifier.
    students_anon = students.copy()
    students_anon["uniqname"] = students_anon["student_id"].map(remap_uniqname_from_old)
    students_anon["student_id"] = students_anon["student_id"].map(remap_id)
    students_anon["display_name"] = students_anon["student_id"].map(
        lambda s: s.replace("S-", "Student ") if isinstance(s, str) else s
    )
    for col in ("first_name", "last_name", "email"):
        if col in students_anon.columns:
            students_anon = students_anon.drop(columns=[col])

    # Same remap on every other table.
    sessions["student_id"] = sessions["student_id"].map(remap_id)
    responses["student_id"] = responses["student_id"].map(remap_id)
    events["student_id"] = events["student_id"].map(remap_id)

    students = students_anon

    # ------------------------------------------------------------------
    # Treat is_correct as nullable bool (parquet stores it as object).
    # ------------------------------------------------------------------
    responses["is_correct_bool"] = responses["is_correct"].map(
        {True: True, False: False, "True": True, "False": False}
    )
    knowledge = responses[responses["is_correct_bool"].notna()].copy()

    # ------------------------------------------------------------------
    # Headline KPIs
    # ------------------------------------------------------------------
    kpis = {
        "total_students": int(students["student_id"].nunique()),
        "total_sessions": int(len(sessions)),
        "abandoned_sessions": int(sessions["abandoned"].sum()),
        "abandoned_pct": float(sessions["abandoned"].mean() * 100),
        "total_responses": int(len(responses)),
        "knowledge_responses": int(len(knowledge)),
        "overall_accuracy_pct": float(knowledge["is_correct_bool"].mean() * 100),
        "median_response_time": float(knowledge["response_time_seconds"].median()),
        "domains": sorted(responses["domain"].unique().tolist()),
        "cohorts": sorted(students["cohort"].dropna().unique().tolist()),
    }

    # ------------------------------------------------------------------
    # Domain coverage (distinct students with non-abandoned session)
    # ------------------------------------------------------------------
    non_abandoned = sessions[~sessions["abandoned"]]
    domain_coverage = (
        non_abandoned.groupby("domain")["student_id"]
        .nunique()
        .sort_values(ascending=False)
        .reset_index(name="distinct_students")
    )

    sessions_by_domain = (
        sessions.groupby("domain")
        .agg(total=("session_id", "count"), abandoned=("abandoned", "sum"))
        .reset_index()
    )
    sessions_by_domain["completed"] = (
        sessions_by_domain["total"] - sessions_by_domain["abandoned"]
    )

    # ------------------------------------------------------------------
    # Accuracy by difficulty
    # ------------------------------------------------------------------
    knowledge_q = knowledge.merge(
        questions[["domain", "question_id", "difficulty"]],
        on=["domain", "question_id"],
        how="left",
    )
    accuracy_by_difficulty = (
        knowledge_q.dropna(subset=["difficulty"])
        .groupby("difficulty")
        .agg(mean_accuracy=("is_correct_bool", "mean"), n=("is_correct_bool", "size"))
        .reset_index()
        .sort_values("difficulty")
    )
    accuracy_by_difficulty["mean_accuracy_pct"] = (
        accuracy_by_difficulty["mean_accuracy"] * 100
    )

    # ------------------------------------------------------------------
    # Accuracy by cohort and domain
    # ------------------------------------------------------------------
    knowledge_with_cohort = knowledge.merge(
        students[["student_id", "cohort"]], on="student_id", how="left"
    )
    accuracy_cohort_domain = (
        knowledge_with_cohort.dropna(subset=["cohort"])
        .groupby(["cohort", "domain"])
        .agg(
            mean_accuracy=("is_correct_bool", "mean"),
            n_responses=("is_correct_bool", "size"),
        )
        .reset_index()
    )
    accuracy_cohort_domain["mean_accuracy_pct"] = (
        accuracy_cohort_domain["mean_accuracy"] * 100
    )

    # ------------------------------------------------------------------
    # Students completing all four domains (non-abandoned)
    # ------------------------------------------------------------------
    completers = (
        non_abandoned.groupby("student_id")["domain"].nunique().reset_index(
            name="n_domains"
        )
    )
    all_four_ids = completers[completers["n_domains"] == 4]["student_id"]
    completers_table = (
        students[students["student_id"].isin(all_four_ids)][
            ["student_id", "uniqname", "cohort", "program"]
        ]
        .sort_values("student_id")
        .head(50)
    )
    n_completers = int(len(all_four_ids))

    # ------------------------------------------------------------------
    # Top students per domain (>=5 knowledge responses; min(5, max) per domain
    # so data_viz, which caps at 4 questions per student, still surfaces).
    # ------------------------------------------------------------------
    per_student_domain = (
        knowledge.groupby(["domain", "student_id"])
        .agg(
            accuracy=("is_correct_bool", "mean"),
            n_questions=("is_correct_bool", "size"),
        )
        .reset_index()
    )
    per_student_domain = per_student_domain.merge(
        students[["student_id", "uniqname"]], on="student_id", how="left"
    )
    top_per_domain: dict[str, list[dict]] = {}
    top_thresholds: dict[str, int] = {}
    for d, grp in per_student_domain.groupby("domain"):
        threshold = int(min(5, grp["n_questions"].max()))
        top_thresholds[d] = threshold
        ranked = (
            grp[grp["n_questions"] >= threshold]
            .sort_values(["accuracy", "n_questions"], ascending=[False, False])
            .head(10)
            .copy()
        )
        ranked["accuracy_pct"] = ranked["accuracy"] * 100
        top_per_domain[d] = ranked[
            ["student_id", "uniqname", "n_questions", "accuracy_pct"]
        ].to_dict(orient="records")

    # ------------------------------------------------------------------
    # Response time vs sequence position
    # ------------------------------------------------------------------
    seq_trend = (
        knowledge.groupby("sequence_position")
        .agg(
            mean_response_time=("response_time_seconds", "mean"),
            n=("response_time_seconds", "size"),
        )
        .reset_index()
        .sort_values("sequence_position")
    )

    # ------------------------------------------------------------------
    # Response-time histogram (log-spaced bins)
    # ------------------------------------------------------------------
    times = knowledge["response_time_seconds"].astype(float)
    times = times[times > 0]
    log_bins = [round(10 ** (i / 4), 2) for i in range(0, 20)]  # 1s -> ~3162s
    bin_series = pd.cut(times, bins=log_bins, include_lowest=True)
    histogram = (
        bin_series.value_counts()
        .sort_index()
        .rename_axis("bucket")
        .reset_index(name="count")
    )
    histogram["lower"] = histogram["bucket"].apply(lambda iv: float(iv.left))
    histogram["upper"] = histogram["bucket"].apply(lambda iv: float(iv.right))
    histogram = histogram.drop(columns=["bucket"])

    # ------------------------------------------------------------------
    # Response time vs correctness, per domain
    # ------------------------------------------------------------------
    rt_by_correct = (
        knowledge.groupby(["domain", "is_correct_bool"])
        .agg(
            mean_rt=("response_time_seconds", "mean"),
            median_rt=("response_time_seconds", "median"),
            n=("response_time_seconds", "size"),
        )
        .reset_index()
    )
    rt_by_correct["is_correct"] = rt_by_correct["is_correct_bool"].map(
        {True: "correct", False: "incorrect"}
    )
    rt_pivot = rt_by_correct.pivot(
        index="domain", columns="is_correct", values="mean_rt"
    ).reset_index()

    # ------------------------------------------------------------------
    # Browser / platform breakdowns
    # ------------------------------------------------------------------
    browser_breakdown = (
        sessions.groupby("metadata_browser")["session_id"]
        .count()
        .reset_index(name="sessions")
        if "metadata_browser" in sessions.columns
        else pd.DataFrame(columns=["metadata_browser", "sessions"])
    )
    platform_breakdown = (
        sessions.groupby("platform")["session_id"].count().reset_index(name="sessions")
    )

    # ------------------------------------------------------------------
    # Event-cleaning summary
    # ------------------------------------------------------------------
    raw_events = pd.read_csv(DATA / "events.csv")
    cleaning_steps = [
        {"step": "Original rows", "rows": int(len(raw_events))},
    ]
    after_dedup = raw_events.drop_duplicates()
    cleaning_steps.append({"step": "After dedupe", "rows": int(len(after_dedup))})
    after_id = after_dedup[
        after_dedup["student_id"].astype(str).str.match(VALID_ID, na=False)
    ]
    cleaning_steps.append({"step": "Valid student_id", "rows": int(len(after_id))})
    after_ts = after_id[
        after_id["timestamp"].notna()
        & (after_id["timestamp"].astype(str).str.strip() != "")
    ]
    cleaning_steps.append({"step": "Non-blank timestamp", "rows": int(len(after_ts))})

    qbank_summary = (
        questions.groupby(["domain", "difficulty"]).size().reset_index(name="n")
    )

    # ------------------------------------------------------------------
    # Author/project profile (filter out obvious placeholders).
    # ------------------------------------------------------------------
    raw_profile = load_profile()
    profile = {
        k: v
        for k, v in raw_profile.items()
        if not (
            isinstance(v, str)
            and (
                v.startswith("YOUR_")
                or "YOUR_HANDLE" in v
                or v.endswith("@example.com")
            )
        )
        and not k.startswith("_")
    }

    # ------------------------------------------------------------------
    # Bundle and emit
    # ------------------------------------------------------------------
    payload = {
        "profile": profile,
        "kpis": kpis,
        "domain_coverage": domain_coverage.to_dict(orient="records"),
        "sessions_by_domain": sessions_by_domain.to_dict(orient="records"),
        "accuracy_by_difficulty": accuracy_by_difficulty[
            ["difficulty", "mean_accuracy_pct", "n"]
        ].to_dict(orient="records"),
        "accuracy_cohort_domain": accuracy_cohort_domain[
            ["cohort", "domain", "mean_accuracy_pct", "n_responses"]
        ].to_dict(orient="records"),
        "all_four_completers": {
            "count": n_completers,
            "students": completers_table.to_dict(orient="records"),
        },
        "top_per_domain": top_per_domain,
        "top_thresholds": top_thresholds,
        "sequence_trend": seq_trend.to_dict(orient="records"),
        "response_time_histogram": histogram.to_dict(orient="records"),
        "response_time_by_correctness": rt_pivot.fillna(0).to_dict(orient="records"),
        "browser_breakdown": browser_breakdown.to_dict(orient="records"),
        "platform_breakdown": platform_breakdown.to_dict(orient="records"),
        "cleaning_steps": cleaning_steps,
        "question_bank_summary": qbank_summary.to_dict(orient="records"),
    }

    payload_native = to_native(payload)
    OUT.write_text(json.dumps(payload_native, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1024:.1f} KB)")

    if TEMPLATE.exists():
        compact = json.dumps(payload_native, separators=(",", ":"))
        # </ inside <script> can break the parser even for type=application/json
        compact = compact.replace("</", "<\\/")
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "__DASHBOARD_DATA__", compact
        )
        HTML_OUT.write_text(html, encoding="utf-8")
        print(f"Wrote {HTML_OUT} ({HTML_OUT.stat().st_size / 1024:.1f} KB)")

    # ------------------------------------------------------------------
    # Anonymized derivative datasets so the project is reproducible from a
    # public repo without exposing PII. The originals stay gitignored.
    # ------------------------------------------------------------------
    ANON_DIR.mkdir(exist_ok=True)
    students.to_csv(ANON_DIR / "students.csv", index=False)
    sessions.to_json(
        ANON_DIR / "sessions.json", orient="records", lines=True, date_format="iso"
    )
    responses.drop(columns=["is_correct_bool"]).to_parquet(
        ANON_DIR / "responses.parquet", index=False
    )
    events.to_csv(ANON_DIR / "events.csv", index=False)

    # Flatten the question bank to a CSV so the .sql files in 2_sql_analysis/
    # can join against it without needing to parse YAML.
    questions.to_csv(ANON_DIR / "questions.csv", index=False)

    # Also emit a "raw" events file that preserves the cleaning issues
    # (duplicates, malformed IDs, blank timestamps). This is what
    # 2_sql_analysis/01_data_cleaning.sql reads so the row-drop counts at
    # each cleaning step are real and reproducible.
    #
    # Three anonymization passes:
    #   1. Valid IDs (matching ^U\d{8}$) seen in the cleaned roster
    #      (students/sessions/responses/cleaned-events) -> S-NNN via id_map.
    #   2. Malformed IDs in the source data (a valid 8-digit ID with extra
    #      characters appended, e.g. "U12345678X") often contain a real
    #      student ID as a substring, so we replace each unique malformed
    #      value with an INVALID-NNN sentinel. The regex filter in the
    #      cleaning SQL still drops them.
    #   3. Valid-format IDs that only appear in raw events.csv (e.g. a
    #      student whose only rows had blank timestamps and so got filtered
    #      out of the id_map source). These could still be real IDs, so
    #      mint a fresh pseudonym from the same S-NNN namespace.
    events_raw = pd.read_csv(DATA / "events.csv")
    raw_ids = events_raw["student_id"].astype(str)
    malformed_unique = sorted({sid for sid in raw_ids if not VALID_ID.match(sid)})
    malformed_map = {
        sid: f"INVALID-{i:03d}" for i, sid in enumerate(malformed_unique, start=1)
    }
    extra_valid_map: dict[str, str] = {}
    next_idx = len(id_map) + 1

    def remap_for_raw(s: Any) -> Any:
        nonlocal next_idx
        s_str = str(s)
        if s_str in id_map:
            return id_map[s_str]["student_id"]
        if s_str in malformed_map:
            return malformed_map[s_str]
        if VALID_ID.match(s_str):
            if s_str not in extra_valid_map:
                extra_valid_map[s_str] = f"S-{next_idx:03d}"
                next_idx += 1
            return extra_valid_map[s_str]
        return s_str  # defensive: NaN / empty / unexpected

    events_raw["student_id"] = raw_ids.map(remap_for_raw)
    events_raw.to_csv(ANON_DIR / "events_raw.csv", index=False)

    print(f"Wrote anonymized data + questions.csv + events_raw.csv to {ANON_DIR}/")


if __name__ == "__main__":
    main()
