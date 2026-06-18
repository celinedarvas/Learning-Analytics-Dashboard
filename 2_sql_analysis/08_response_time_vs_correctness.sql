-- ============================================================
-- 08_response_time_vs_correctness.sql
-- THE HEADLINE FINDING.
--
-- Question: do students rush their wrong answers? In other words,
-- are incorrect responses systematically faster than correct ones?
--
-- I expected to see a big gap. If wrong answers were 10-15 seconds
-- faster, that would mean students are guessing or disengaging.
--
-- Approach: average response_time_seconds for (correct, incorrect)
-- inside each domain. Same join pattern as before.
--
-- Result: the gap is tiny. ~52-54s in both buckets across all four
--    domains. The biggest swing is sql_duckdb (incorrect answers
--    come in ~3s faster), and pandas_core actually goes the other
--    direction (~2s SLOWER on incorrect answers).
--
-- So what: students put roughly the same time into questions they
--    miss as into questions they get right. Wrong answers are not
--    rushing or disengagement. They are real conceptual gaps.
--    For an instructor that means the fix is content, not pacing.
-- ============================================================

SELECT 
    q.domain, 
    r.is_correct, 
    AVG(r.response_time_seconds) AS avg_response_time,
    COUNT(*)                     AS n_responses
FROM read_parquet('../1_data/responses.parquet')  r
JOIN read_csv_auto('../1_data/questions.csv')     q ON r.question_id = q.question_id
WHERE r.is_correct IS NOT NULL
GROUP BY q.domain, r.is_correct
ORDER BY q.domain, r.is_correct DESC;   -- TRUE before FALSE inside each domain
