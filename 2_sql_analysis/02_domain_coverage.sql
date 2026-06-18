-- ============================================================
-- 02_domain_coverage.sql
--
-- Question: for each subject domain, how many distinct students
-- actually completed at least one full (non-abandoned) session?
--
-- Approach: filter to non-abandoned sessions only, then count
-- distinct student_id per domain. ORDER BY descending so the
-- best-covered domain is at the top.
--
-- Result: pandas_core 421, python_fundamentals 421, sql_duckdb 417,
--    data_viz 403. Coverage is even across domains. The 18 student
--    gap between pandas_core (421) and data_viz (403) is the only
--    visible difference.
-- ============================================================

SELECT 
    domain, 
    COUNT(DISTINCT student_id) AS distinct_students
FROM read_json_auto('../1_data/sessions.json')
WHERE abandoned = false              -- only sessions the student finished
GROUP BY domain
ORDER BY distinct_students DESC;     -- best-covered domain first
