-- ============================================================
-- 06_top_performers_window_function.sql
--
-- Question: who are the top 3 students in each domain by accuracy?
-- Only count students who answered at least 5 knowledge questions
-- in that domain so we are not crowning someone who got lucky on
-- a single question.
--
-- Approach: this needs a window function (RANK) because regular
-- ORDER BY + LIMIT only gives me one global top-N. I want one
-- top-N per domain. So:
--   1. Compute accuracy per (domain, student) in a CTE
--   2. RANK() OVER(PARTITION BY domain ORDER BY accuracy DESC)
--      gives each student a rank inside their own domain
--   3. Filter the outer query to rank <= 3
--
-- HAVING COUNT(*) >= 5 inside the CTE is the "answered at least 5"
-- threshold. Note: data_viz caps at 4 questions per student in this
-- dataset, so the dashboard relaxes to >= min(5, max_in_domain)
-- per domain. The strict >= 5 version below matches the original
-- assignment spec.
--
-- Result: per-domain leaderboards, often tied at 100% accuracy.
--    RANK() (not DENSE_RANK or ROW_NUMBER) intentionally allows
--    ties to share the top spot.
-- ============================================================

WITH ranked AS (
    SELECT 
        q.domain, 
        s.student_id,
        AVG(CAST(r.is_correct AS INT))                                   AS accuracy,
        RANK() OVER (
            PARTITION BY q.domain
            ORDER BY AVG(CAST(r.is_correct AS INT)) DESC
        )                                                                AS domain_rank
    FROM read_parquet('../1_data/responses.parquet')   r
    JOIN read_csv_auto('../1_data/students.csv')       s ON r.student_id  = s.student_id
    JOIN read_csv_auto('../1_data/questions.csv')      q ON r.question_id = q.question_id
    WHERE r.is_correct IS NOT NULL
    GROUP BY q.domain, s.student_id
    HAVING COUNT(r.response_id) >= 5      -- minimum sample size per student per domain
)
SELECT domain, student_id, accuracy, domain_rank
FROM ranked
WHERE domain_rank <= 3
ORDER BY domain, domain_rank;
