USE patent_intelligence;

-- Q1: selection + projection — active AI-domain patents after 2020.
SELECT p.patent_id, p.title, p.publication_year
FROM patents p JOIN domains d ON d.domain_id=p.domain_id
WHERE d.name='AI' AND p.publication_year >= 2020;

-- Q2: join + grouping + HAVING — assignees with at least ten patents.
SELECT a.name, COUNT(*) AS patent_count
FROM assignees a JOIN patent_assignees pa ON pa.assignee_id=a.assignee_id
GROUP BY a.assignee_id, a.name HAVING COUNT(*) >= 10 ORDER BY patent_count DESC;

-- Q3: correlated subquery — patents cited above their domain average.
SELECT p.patent_id, p.title, p.cited_by_patent_count
FROM patents p
WHERE p.cited_by_patent_count > (
  SELECT AVG(p2.cited_by_patent_count) FROM patents p2 WHERE p2.domain_id=p.domain_id
);

-- Q4: multiway join — prolific inventor/CPC combinations.
SELECT i.name AS inventor, c.cpc_code, COUNT(DISTINCT pi.patent_id) AS patent_count
FROM patent_inventors pi JOIN inventors i ON i.inventor_id=pi.inventor_id
JOIN patent_cpc_codes pc ON pc.patent_id=pi.patent_id JOIN cpc_codes c ON c.cpc_code=pc.cpc_code
GROUP BY i.inventor_id, i.name, c.cpc_code ORDER BY patent_count DESC LIMIT 20;

-- Q5: division-style query — assignees represented in every requested CPC section.
SELECT a.name
FROM assignees a JOIN patent_assignees pa ON pa.assignee_id=a.assignee_id
JOIN patent_cpc_codes pc ON pc.patent_id=pa.patent_id JOIN cpc_codes c ON c.cpc_code=pc.cpc_code
WHERE c.section IN ('A','G','H')
GROUP BY a.assignee_id, a.name HAVING COUNT(DISTINCT c.section)=3;

-- Q6: family-size report with a derived relation.
SELECT p.patent_id, p.title, COUNT(f.related_patent_id) AS family_size
FROM patents p LEFT JOIN patent_families f ON f.patent_id=p.patent_id
GROUP BY p.patent_id, p.title HAVING COUNT(f.related_patent_id) > 1
ORDER BY family_size DESC LIMIT 20;

-- Q7: update — archive an inactive draft case (safe parameterized application equivalent required in code).
UPDATE analysis_cases SET status='archived'
WHERE status='draft' AND updated_at < CURRENT_TIMESTAMP - INTERVAL 30 DAY;

-- Q8: delete — remove failed runs older than seven days; FK cascades clean dependent rows.
DELETE FROM analysis_runs
WHERE run_status='failed' AND started_at < CURRENT_TIMESTAMP - INTERVAL 7 DAY;
