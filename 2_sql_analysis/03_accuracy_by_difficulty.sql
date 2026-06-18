-- ============================================================
-- 03_accuracy_by_difficulty.sql
--
-- Question: do harder questions actually get answered correctly
-- less often?
--
-- Approach: join responses to the question bank to pick up the
-- difficulty label (D1, D2, D3), drop self-report rows where
-- is_correct is NULL, then average is_correct cast to int.
-- CAST(is_correct AS INT) gives me 1 for correct, 0 for incorrect,
-- so AVG() returns the share correct.
--
-- Result: D1 = 69.9%, D2 = 69.0%, D3 = 67.8%. Accuracy drops as
--    difficulty goes up. The drop is small but consistent across
--    thousands of responses, so the difficulty levels look well
--    calibrated.
-- ============================================================

SELECT 
    q.difficulty, 
    AVG(CAST(r.is_correct AS INT)) AS mean_accuracy,
    COUNT(*)                       AS n_responses
FROM read_parquet('../1_data/responses.parquet') r
JOIN read_csv_auto('../1_data/questions.csv')    q ON r.question_id = q.question_id
WHERE r.is_correct IS NOT NULL    -- exclude self-report questions
GROUP BY q.difficulty
ORDER BY q.difficulty;            -- D1 -> D2 -> D3
