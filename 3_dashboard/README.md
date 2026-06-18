# 3. Dashboard

This folder is **the result**. A single self-contained web page that turns the SQL output from `../2_sql_analysis/` into something a non-technical viewer can read in 30 seconds.

## To open it

Just double-click `index.html`.

```bash
open 3_dashboard/index.html
```

If your browser refuses to load Chart.js from the CDN over `file://`, run a tiny local server:

```bash
python3 -m http.server 8765 --directory 3_dashboard
# then visit http://127.0.0.1:8765/index.html
```

## What's on the page

- **6 KPI cards.** 520 learners, 1,832 sessions, 19,608 responses, 69.1% overall accuracy, 44s median response time, 4 domains.
- **Domain coverage.** Distinct learners per domain.
- **Sessions completed vs abandoned.** Stacked, per domain.
- **Accuracy by difficulty.** D1 / D2 / D3.
- **Accuracy by cohort × domain.** Grouped bars.
- **Response time distribution.** Log-spaced histogram so the right tail is readable.
- **Response time across sequence position.** The learning-effect curve.
- **Mean response time: correct vs incorrect, per domain.** Plus a written headline finding.
- **Top 10 learners per domain.** Tabbed table with progress bars. Anonymized IDs.
- **Learners who completed all four domains.** 248 of 520, with a scrollable list.
- **Event-cleaning pipeline.** Row counts after each cleaning step.
- **Question bank shape.** Questions per domain × difficulty.

## Files in this folder

```
3_dashboard/
├── index.html              # Open this. Self-contained, all data inlined.
├── index.template.html     # Source template (placeholder: __DASHBOARD_DATA__).
├── build_dashboard_data.py # ETL + anonymization + render. Reads ../data/, writes ../1_data/ + index.html.
├── dashboard_data.json     # Pre-computed aggregates. Same JSON inlined into index.html.
├── profile.json            # Author byline + project metadata. Edit to change the page header.
└── README.md               # This file.
```

## To rebuild

You only need to do this if you change the data in `../data/` (the raw, gitignored source). The committed `index.html` is already built.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pandas pyarrow pyyaml
python3 3_dashboard/build_dashboard_data.py
```

The build script:

1. Loads `../data/students.csv`, `sessions.json`, `responses.parquet`, `events.csv`, plus the four YAML question banks
2. Applies the cleaning steps (dedupe, regex-validate `student_id`, drop blank timestamps)
3. Builds a deterministic `student_id → S-NNN` mapping and applies it to every table
4. Computes domain coverage, accuracy by difficulty, accuracy by cohort × domain, top performers, response-time histogram and trend, completers
5. Writes `dashboard_data.json` and inlines the same JSON into `index.html`
6. Also writes anonymized data + `questions.csv` + `events_raw.csv` to `../1_data/` so the SQL files in `../2_sql_analysis/` can run against them

## To change the byline

Open `profile.json` and fill in:

```json
{
  "name": "Your Name",
  "email": "you@example.com",
  "github": "https://github.com/your-handle",
  "linkedin": "https://www.linkedin.com/in/your-handle/"
}
```

Anything left as `YOUR_*` or ending in `@example.com` is treated as a placeholder and hidden in the UI. Rerun the build after editing.

## Privacy & security notes

- Every identifier on the page is anonymized. The PII-leak audit in the build process verifies that zero real student IDs, uniqnames, or emails appear in `index.html`, `dashboard_data.json`, or any committed data file.
- Chart.js is pinned to version 4.4.4 with a Subresource Integrity (SRI) SHA-384 hash. The browser refuses to execute tampered bytes from the CDN.
- All dynamic strings rendered into the page go through an HTML-escaping helper. The inlined JSON has `</` escaped to prevent script-tag breakout.
- External links use `rel="noopener noreferrer"` so opened tabs cannot share window references with this page.
