-- ============================================================
-- 00_setup.sql
-- Loads the four data files into named views so the rest of the
-- queries in this folder can read them without copy-pasting the
-- file paths everywhere. Run this once at the start of a session.
--
-- DuckDB CLI:
--     duckdb
--     .read 00_setup.sql
--     .read 02_domain_coverage.sql
--
-- Each numbered query file is also self-contained: you can run
-- any one of them on its own without doing setup first.
-- ============================================================

CREATE OR REPLACE VIEW students  AS SELECT * FROM read_csv_auto('../1_data/students.csv');
CREATE OR REPLACE VIEW sessions  AS SELECT * FROM read_json_auto('../1_data/sessions.json');
CREATE OR REPLACE VIEW responses AS SELECT * FROM read_parquet ('../1_data/responses.parquet');
CREATE OR REPLACE VIEW events    AS SELECT * FROM read_csv_auto('../1_data/events.csv');
CREATE OR REPLACE VIEW questions AS SELECT * FROM read_csv_auto('../1_data/questions.csv');

-- Sanity check: all five tables should report a non-zero count.
SELECT 'students'  AS table_name, COUNT(*) AS rows FROM students  UNION ALL
SELECT 'sessions',                COUNT(*)        FROM sessions  UNION ALL
SELECT 'responses',               COUNT(*)        FROM responses UNION ALL
SELECT 'events',                  COUNT(*)        FROM events    UNION ALL
SELECT 'questions',               COUNT(*)        FROM questions;
