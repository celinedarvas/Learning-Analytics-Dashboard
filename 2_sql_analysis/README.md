# 2. SQL Analysis

This folder is **the work**. Eight SQL queries that take the data in `../1_data/` and answer eight specific questions about how students performed.

I wrote these in DuckDB. Each one is in its own `.sql` file so you can read it on its own without needing to scroll through a notebook.

## How to read this folder

Open the `.sql` files in numerical order. Each file has the same shape:

```
-- Question: what am I trying to find out?
-- Approach: how am I going to find it?
-- Result:   what came back, and what does it mean?

[the actual SQL]
```

If you want to run them, see "How to run" at the bottom.

## The eight queries, in order

| # | File | Question | Headline result |
|---|---|---|---|
| 01 | `01_data_cleaning.sql` | How many rows survive each cleaning step on `events.csv`? | 69,628 → 67,563 (97% retention) |
| 02 | `02_domain_coverage.sql` | How many distinct students completed at least one full session per domain? | 421, 421, 417, 403. Coverage is even. |
| 03 | `03_accuracy_by_difficulty.sql` | Do harder questions get answered correctly less often? | Yes. D1 = 69.9%, D2 = 69.0%, D3 = 67.8%. |
| 04 | `04_accuracy_by_cohort_and_domain.sql` | How does accuracy break down by cohort × domain? | 3 × 4 matrix. W2025 has the strongest data_viz (74.5%), W2025 has the weakest pandas_core (66.3%). |
| 05 | `05_completers_all_four_domains.sql` | How many students completed all four domains? | 248 of 520 (47.7%). Demonstrates `HAVING`. |
| 06 | `06_top_performers_window_function.sql` | Top 3 students per domain by accuracy. | Window function with `RANK() OVER (PARTITION BY domain ...)`. |
| 07 | `07_response_time_by_sequence_position.sql` | Do response times change as students get further into a session? | Yes, classic learning-effect curve. Spike at position 1, then declining. |
| 08 | `08_response_time_vs_correctness.sql` | Do students rush their wrong answers? | **No.** Mean time is ~52-54s in both buckets. The headline finding. |

## What each query is meant to show as a SQL skill

This is for the reviewer who is checking whether I can actually write SQL, not just describe results.

| File | SQL skill on display |
|---|---|
| 01 | CTEs, regex pattern matching (`regexp_matches`), step-by-step auditable pipeline |
| 02 | `COUNT(DISTINCT ...)`, filtered aggregation, sort-by-aggregate |
| 03 | Multi-table join, casting bool to int for averaging, `IS NOT NULL` filtering |
| 04 | Three-way join, multi-key `GROUP BY`, ordered output for stakeholder readability |
| 05 | `HAVING` vs `WHERE` (the classic interview question), group-level filter on `COUNT(DISTINCT domain) = 4` |
| 06 | Window function (`RANK() OVER (PARTITION BY ... ORDER BY ...)`), CTE wrapping a window so the outer query can filter on `rank <= 3` |
| 07 | Simple aggregate over a sequence column, lays the groundwork for the chart in the dashboard |
| 08 | Cross-tab style aggregate by (category, boolean), the most informative result in the project |

## How to run

Each `.sql` file is self-contained. It uses DuckDB's inline file readers (`read_csv_auto`, `read_parquet`, `read_json_auto`), so there is no setup step.

Install DuckDB (one-time): https://duckdb.org/docs/installation/

Run a single query:
```bash
duckdb < 02_domain_coverage.sql
```

Run all eight queries:
```bash
./run_all.sh
```

If you prefer to start a DuckDB session and load the data into named views first:
```bash
duckdb
.read 00_setup.sql
.read 02_domain_coverage.sql
```

## Where the SQL came from

These queries are lifted from the analytical notebook that produced the dashboard in `../3_dashboard/`. I extracted them, cleaned them up to be standalone, and added the result documentation. The final dashboard recomputes the same numbers in pandas at build time so the page can be a single static file with no SQL engine running in the browser. If you want to verify any number on the dashboard, you can run the corresponding `.sql` here and confirm.
