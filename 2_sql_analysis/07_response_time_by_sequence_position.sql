-- ============================================================
-- 07_response_time_by_sequence_position.sql
--
-- Question: do students answer faster as they get further into a
-- session?
--
-- Approach: group all knowledge responses by their position in
-- the session (1 = first question, 2 = second, etc.) and average
-- response_time_seconds. If there is a learning effect, the curve
-- should slope down.
--
-- Result: response time spikes on question 1, then declines as
--    students acclimate to the platform. Classic learning-effect
--    curve. The mean keeps drifting down even at later positions,
--    so it is not just a "first question is slow" artifact.
-- ============================================================

SELECT 
    sequence_position, 
    AVG(response_time_seconds) AS mean_response_time,
    COUNT(*)                   AS n
FROM read_parquet('../1_data/responses.parquet')
WHERE is_correct IS NOT NULL    -- exclude self-report questions
GROUP BY sequence_position
ORDER BY sequence_position;
