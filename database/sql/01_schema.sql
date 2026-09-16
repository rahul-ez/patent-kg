-- MySQL 8.0+ normalized source-of-truth schema.
-- Run with: mysql -u root -p < database/sql/01_schema.sql
CREATE DATABASE IF NOT EXISTS patent_intelligence CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE patent_intelligence;

CREATE TABLE domains (
  domain_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE patents (
  patent_id VARCHAR(80) PRIMARY KEY,
  title TEXT NOT NULL,
  abstract TEXT NOT NULL,
  publication_year SMALLINT NULL,
  legal_status VARCHAR(50) NULL,
  cited_by_patent_count INT NOT NULL DEFAULT 0,
  url VARCHAR(2048) NULL,
  domain_id INT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT ck_patent_year CHECK (publication_year IS NULL OR publication_year BETWEEN 1800 AND 2200),
  CONSTRAINT ck_patent_citations CHECK (cited_by_patent_count >= 0),
  CONSTRAINT fk_patent_domain FOREIGN KEY (domain_id) REFERENCES domains(domain_id),
  INDEX ix_patent_year_domain (publication_year, domain_id)
) ENGINE=InnoDB;

CREATE TABLE assignees (
  assignee_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(500) NOT NULL UNIQUE
) ENGINE=InnoDB;
CREATE TABLE inventors (
  inventor_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(500) NOT NULL UNIQUE
) ENGINE=InnoDB;
CREATE TABLE cpc_codes (
  cpc_code VARCHAR(32) PRIMARY KEY,
  section CHAR(1) NOT NULL,
  description TEXT NULL,
  INDEX ix_cpc_section (section)
) ENGINE=InnoDB;
CREATE TABLE npl_references (
  npl_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  citation TEXT NOT NULL,
  normalized_key CHAR(64) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE patent_assignees (
  patent_id VARCHAR(80) NOT NULL,
  assignee_id INT NOT NULL,
  PRIMARY KEY (patent_id, assignee_id),
  FOREIGN KEY (patent_id) REFERENCES patents(patent_id) ON DELETE CASCADE,
  FOREIGN KEY (assignee_id) REFERENCES assignees(assignee_id)
) ENGINE=InnoDB;
CREATE TABLE patent_inventors (
  patent_id VARCHAR(80) NOT NULL,
  inventor_id INT NOT NULL,
  PRIMARY KEY (patent_id, inventor_id),
  FOREIGN KEY (patent_id) REFERENCES patents(patent_id) ON DELETE CASCADE,
  FOREIGN KEY (inventor_id) REFERENCES inventors(inventor_id)
) ENGINE=InnoDB;
CREATE TABLE patent_cpc_codes (
  patent_id VARCHAR(80) NOT NULL,
  cpc_code VARCHAR(32) NOT NULL,
  PRIMARY KEY (patent_id, cpc_code),
  FOREIGN KEY (patent_id) REFERENCES patents(patent_id) ON DELETE CASCADE,
  FOREIGN KEY (cpc_code) REFERENCES cpc_codes(cpc_code)
) ENGINE=InnoDB;
CREATE TABLE patent_npl_references (
  patent_id VARCHAR(80) NOT NULL,
  npl_id BIGINT NOT NULL,
  PRIMARY KEY (patent_id, npl_id),
  FOREIGN KEY (patent_id) REFERENCES patents(patent_id) ON DELETE CASCADE,
  FOREIGN KEY (npl_id) REFERENCES npl_references(npl_id)
) ENGINE=InnoDB;
CREATE TABLE patent_families (
  patent_id VARCHAR(80) NOT NULL,
  related_patent_id VARCHAR(80) NOT NULL,
  relation_type VARCHAR(32) NOT NULL,
  PRIMARY KEY (patent_id, related_patent_id, relation_type),
  CONSTRAINT ck_family_distinct CHECK (patent_id <> related_patent_id),
  FOREIGN KEY (patent_id) REFERENCES patents(patent_id) ON DELETE CASCADE,
  FOREIGN KEY (related_patent_id) REFERENCES patents(patent_id) ON DELETE CASCADE
) ENGINE=InnoDB;
CREATE TABLE citation_snapshots (
  snapshot_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  patent_id VARCHAR(80) NOT NULL,
  cited_by_count INT NOT NULL,
  observed_on DATETIME NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_citation_snapshot (patent_id, observed_on),
  CONSTRAINT ck_snapshot_citations CHECK (cited_by_count >= 0),
  FOREIGN KEY (patent_id) REFERENCES patents(patent_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE app_users (
  user_id CHAR(36) PRIMARY KEY,
  email VARCHAR(320) NOT NULL UNIQUE,
  display_name VARCHAR(120) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;
CREATE TABLE roles (
  role_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;
CREATE TABLE user_roles (
  user_id CHAR(36) NOT NULL,
  role_id INT NOT NULL,
  PRIMARY KEY (user_id, role_id),
  FOREIGN KEY (user_id) REFERENCES app_users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE analysis_cases (
  case_id CHAR(36) PRIMARY KEY,
  owner_user_id CHAR(36) NULL,
  title VARCHAR(250) NOT NULL,
  idea_text TEXT NOT NULL,
  status ENUM('draft','active','archived') NOT NULL DEFAULT 'draft',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (owner_user_id) REFERENCES app_users(user_id) ON DELETE SET NULL,
  INDEX ix_case_owner_status (owner_user_id, status)
) ENGINE=InnoDB;
CREATE TABLE analysis_runs (
  run_id CHAR(36) PRIMARY KEY,
  case_id CHAR(36) NOT NULL,
  query_id VARCHAR(64) NULL UNIQUE,
  gnn_mode ENUM('novelty','graph_sim') NOT NULL,
  top_k TINYINT UNSIGNED NOT NULL,
  run_status ENUM('running','completed','failed') NOT NULL DEFAULT 'running',
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME NULL,
  pipeline_payload JSON NULL,
  CONSTRAINT ck_run_top_k CHECK (top_k BETWEEN 1 AND 100),
  FOREIGN KEY (case_id) REFERENCES analysis_cases(case_id) ON DELETE CASCADE,
  INDEX ix_run_case_started (case_id, started_at)
) ENGINE=InnoDB;
CREATE TABLE run_patent_results (
  run_id CHAR(36) NOT NULL,
  patent_id VARCHAR(80) NOT NULL,
  rank_position SMALLINT UNSIGNED NOT NULL,
  source ENUM('faiss','kg_family','kg_cpc') NOT NULL,
  expansion_type VARCHAR(32) NULL,
  semantic_score DOUBLE NULL,
  graph_score DOUBLE NULL,
  combined_score DOUBLE NULL,
  novelty_score DOUBLE NULL,
  PRIMARY KEY (run_id, patent_id),
  UNIQUE KEY uq_run_rank (run_id, rank_position),
  CONSTRAINT ck_run_rank CHECK (rank_position > 0),
  FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
  FOREIGN KEY (patent_id) REFERENCES patents(patent_id)
) ENGINE=InnoDB;
CREATE TABLE evaluation_metrics (
  metric_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id CHAR(36) NOT NULL UNIQUE,
  patentability_score DOUBLE NOT NULL,
  risk VARCHAR(20) NOT NULL,
  verdict VARCHAR(100) NOT NULL,
  payload JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id) ON DELETE CASCADE
) ENGINE=InnoDB;
CREATE TABLE improvement_recommendations (
  recommendation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id CHAR(36) NOT NULL,
  position SMALLINT UNSIGNED NOT NULL,
  category VARCHAR(80) NOT NULL,
  recommendation TEXT NOT NULL,
  rationale TEXT NULL,
  UNIQUE KEY uq_recommendation_position (run_id, position),
  CONSTRAINT ck_recommendation_position CHECK (position > 0),
  FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id) ON DELETE CASCADE
) ENGINE=InnoDB;

INSERT IGNORE INTO roles(name) VALUES ('admin'), ('analyst'), ('report_reader');
