-- ============================================================
-- 01_data_cleaning.sql
--
-- Question: how many rows survive each step of the events.csv
-- cleaning pipeline?
--
-- The raw events log has duplicates, malformed student_id values
-- (the ID format is locked, so anything that does not match the
-- pattern is a malformed row), and some rows with a blank
-- timestamp. I want to drop all three.
--
-- Approach: do each cleaning step in its own CTE so the row count
-- after each step is auditable. Anyone reviewing my work can see
-- exactly what got removed and why.
--
-- Note on the regex: in the original data the ID format was
-- "U" + exactly 8 digits ('^U\d{8}$'). For this portable artifact
-- I anonymized valid IDs to "S-" + digits, so the regex below
-- matches '^S-\d+$'. Malformed IDs (anything that did not match
-- the original format) were passed through unchanged, so the
-- filter still catches them.
--
-- Result: 69,628 -> 68,263 -> 67,910 -> 67,563 rows.
--    97.0% of the raw events survive the pipeline.
--    Most of the loss is duplicates (-1,365 rows), then a smaller
--    drop from malformed IDs (-353 rows), then blank timestamps
--    (-347 rows).
-- ============================================================

WITH original AS (
    SELECT * FROM read_csv_auto('../1_data/events_raw.csv')
),
deduped AS (
    SELECT DISTINCT * FROM original
),
valid_id AS (
    -- Drop anything that does not match the (anonymized) ID format.
    SELECT * FROM deduped
    WHERE regexp_matches(student_id, '^S-\d+$')
),
non_blank_ts AS (
    SELECT * FROM valid_id
    WHERE timestamp IS NOT NULL
      AND TRIM(CAST(timestamp AS VARCHAR)) <> ''
)
SELECT 'Original rows'        AS step, COUNT(*) AS rows FROM original     UNION ALL
SELECT 'After dedupe',                 COUNT(*)         FROM deduped       UNION ALL
SELECT 'Valid student_id',             COUNT(*)         FROM valid_id      UNION ALL
SELECT 'Non-blank timestamp',          COUNT(*)         FROM non_blank_ts;
