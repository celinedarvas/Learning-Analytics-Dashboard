# 1. The Data

This folder is the dataset the rest of the project runs on.

I worked with **520 students**, **1,832 sessions**, and **19,608 question responses** across four technical assessment domains: Python Fundamentals, Pandas Core, SQL with DuckDB, and Data Visualization.

Every identifier in this folder has been anonymized. Real student IDs (`U` + 8 digits in the source data) became `S-001`, `S-002`, etc. Names and emails were dropped entirely. The mapping is deterministic, so the same student always gets the same pseudonym across files.

## What's in here

| File | Format | Rows | What it is |
|---|---|---|---|
| `students.csv` | CSV | 520 | One row per learner. Cohort, section, program. PII removed. |
| `sessions.json` | NDJSON | 1,832 | One JSON object per line. A session is a sitting where a learner attempts questions in one domain. Includes start/end time, abandoned flag, browser, screen width. |
| `responses.parquet` | Parquet | 19,608 | One row per answer. Includes selected option, correct flag, response time, sequence position within the session. |
| `events.csv` | CSV | 67,563 | Cleaned activity log. One row per UI event (question viewed, answer submitted, etc.). |
| `events_raw.csv` | CSV | 69,628 | Same as above but BEFORE cleaning. Used by `2_sql_analysis/01_data_cleaning.sql` to demonstrate the cleaning pipeline produces real row drops. |
| `questions.csv` | CSV | 235 | One row per question with its domain, difficulty, sub-skill, and correct answer. Flattened from the original YAML question banks during the build. |

## Schema (the columns that matter)

**`students.csv`**
```
student_id   uniqname     cohort   section   program   display_name
S-001        learner001   F2025    1         BSI       Student 001
```

**`sessions.json`** (one line per session)
```json
{"session_id":"sess-00001","student_id":"S-001","domain":"sql_duckdb",
 "started_at":"2026-03-14T10:28:00Z","ended_at":"2026-03-14T10:40:00Z",
 "abandoned":false,"platform":"web","n_questions_seen":9,
 "metadata_browser":"Safari","metadata_screen_width":1280}
```

**`responses.parquet`**
```
response_id    session_id   student_id   domain      question_id
selected_option   is_correct   response_time_seconds   sequence_position
```

**`questions.csv`**
```
domain        question_id              sub_skill   difficulty   dimension   correct_answer
pandas_core   pd-mc-merge-basics       merging     D2           knowledge   A
```

## How the data was cleaned

Three steps, in this order:

1. **Drop duplicate rows** in `events.csv` (-1,365 rows)
2. **Filter out malformed `student_id`** (anything not matching `^U\d{8}$` in the original data) (-353 rows)
3. **Drop rows with a blank `timestamp`** (-347 rows)

The query that produces these row counts lives in `../2_sql_analysis/01_data_cleaning.sql`. The two events files (`events.csv` and `events_raw.csv`) are both shipped here so the cleaning step is auditable end to end.

## Privacy

Every artifact in this folder went through an automated PII-leak audit before being committed. The audit checks that no real `student_id`, `uniqname`, name, or email value from the source dataset appears in any of these files. The audit passes with zero leaks.
