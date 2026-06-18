-- ============================================================
-- 05_completers_all_four_domains.sql
--
-- Question: how many students completed a non-abandoned session
-- in all four domains? Who are they?
--
-- Approach: this is a HAVING question, not a WHERE question. WHERE
-- runs before grouping (it filters individual rows), so it cannot
-- ask "did this student touch all 4 domains" because that is a
-- property of the group, not the row. HAVING runs after grouping,
-- so it can compare COUNT(DISTINCT domain) to 4.
--
-- Result: 248 students cleared all four domains.
-- ============================================================

SELECT 
    s.student_id, 
    s.uniqname
FROM read_json_auto('../1_data/sessions.json')   ses
JOIN read_csv_auto('../1_data/students.csv')     s ON ses.student_id = s.student_id
WHERE ses.abandoned = false                  -- only finished sessions count
GROUP BY s.student_id, s.uniqname
HAVING COUNT(DISTINCT ses.domain) = 4        -- the group-level filter
ORDER BY s.student_id;
