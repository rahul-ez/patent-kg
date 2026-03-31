# Objective: Data Ingestion & Transformation Checklist

- [ ] **Download sample dataset** (100k patents via PatentsView API) using `backend/src/ingestions/download_patents.py`.
- [ ] **Parse to normalized CSVs:** `patents.csv`, `inventors.csv`, `assignees.csv`, `citations.csv`.
- [ ] **Clean & deduplicate** the CSVs.
- [ ] **NLP preprocessing:** Create `backend/src/nlp/extract_entities.py` using `spaCy` to extract technical terms into `entities.csv` and `keywords.csv`.
- [ ] **Acceptance:** Verify ingestion pipeline logic and output schemas.
