USE patent_intelligence;

CREATE OR REPLACE VIEW vw_patent_retrieval AS
SELECT p.patent_id, p.title, p.abstract, d.name AS domain, p.publication_year,
       p.legal_status, p.cited_by_patent_count, p.url
FROM patents p LEFT JOIN domains d ON d.domain_id = p.domain_id;

CREATE OR REPLACE VIEW vw_domain_year_counts AS
SELECT d.name AS domain, p.publication_year, COUNT(*) AS patent_count
FROM patents p LEFT JOIN domains d ON d.domain_id = p.domain_id
GROUP BY d.name, p.publication_year;

CREATE OR REPLACE VIEW vw_case_risk_summary AS
SELECT c.case_id, c.title, c.status, r.run_id, r.started_at,
       e.patentability_score, e.risk, e.verdict
FROM analysis_cases c
LEFT JOIN analysis_runs r ON r.case_id = c.case_id
LEFT JOIN evaluation_metrics e ON e.run_id = r.run_id;
