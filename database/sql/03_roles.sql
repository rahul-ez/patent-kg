-- Run as a MySQL administrator after replacing password placeholders locally.
CREATE USER IF NOT EXISTS 'patent_app'@'%' IDENTIFIED BY 'replace_locally';
CREATE USER IF NOT EXISTS 'patent_reporter'@'%' IDENTIFIED BY 'replace_locally';
GRANT SELECT, INSERT, UPDATE, DELETE ON patent_intelligence.* TO 'patent_app'@'%';
GRANT SELECT ON patent_intelligence.vw_patent_retrieval TO 'patent_reporter'@'%';
GRANT SELECT ON patent_intelligence.vw_domain_year_counts TO 'patent_reporter'@'%';
GRANT SELECT ON patent_intelligence.vw_case_risk_summary TO 'patent_reporter'@'%';
FLUSH PRIVILEGES;
