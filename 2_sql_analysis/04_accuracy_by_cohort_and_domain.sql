-- ============================================================
-- 04_accuracy_by_cohort_and_domain.sql
--
-- Question: how does accuracy break down by student cohort
-- (F2025, W2025, W2026) and subject domain?
--
-- Approach: three-way join. Responses for the score, students for
-- the cohort, questions for the domain. Group by (cohort, domain),
-- sort cohort first then accuracy descending so the strongest
-- domain in each cohort is at the top.
--
-- Result: a 3 cohorts x 4 domains matrix of accuracy values. Lets
--    me spot which cohort is strongest where, and whether the
--    spread between domains is bigger inside one cohort than
--    another.
-- ============================================================

SELECT 
    s.cohort, 
    q.domain, 
    AVG(CAST(r.is_correct AS INT)) AS mean_accuracy,
    COUNT(r.response_id)           AS n_responses
FROM read_parquet('../1_data/responses.parquet')      r
JOIN read_csv_auto('../1_data/students.csv')          s ON r.student_id  = s.student_id
JOIN read_csv_auto('../1_data/questions.csv')         q ON r.question_id = q.question_id
WHERE r.is_correct IS NOT NULL    -- exclude self-report questions
GROUP BY s.cohort, q.domain
ORDER BY s.cohort, mean_accuracy DESC;
