"""Manual UI failure fixture, NOT a production server or a live AI test.

Temporarily stop the real API, then run:
    venv/Scripts/python.exe tests/serve_unsaved_fixture.py
The existing frontend proxy will display an explicitly unsaved analysis.
No database is contacted and no test record is created.
"""
import os
import sys
import types
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'backend/src'))

from fastapi import FastAPI
import uvicorn
from api.routers import pipeline
from persistence import analysis_store
from persistence.database import DatabaseUnavailable


def offline(*args, **kwargs):
    raise DatabaseUnavailable('Controlled unavailable-database fixture')


def fixture(idea, top_k=5, gnn_mode='novelty'):
    return {
        'query_id': 'unsaved-ui-fixture', 'query_text': idea,
        'model': 'Controlled UI fixture (not live AI)', 'top_k': top_k,
        'nlp_result': {'clean_text': idea, 'keywords': ['sensor'], 'entities': [], 'source': 'fixture'},
        'results': [], 'kg_status': 'skipped_database_offline',
        'gnn_status': 'skipped_missing_model', 'indexed_count': 36353,
    }


if __name__ == '__main__':
    app = FastAPI(title='Unsaved UI verification fixture')
    app.include_router(pipeline.router, prefix='/api')
    module = types.ModuleType('integration.pipeline')
    module.run_end_to_end = fixture
    with patch.dict(sys.modules, {'integration.pipeline': module}), patch.dict(os.environ, {'PERSISTENCE_REQUIRED': 'false'}), patch.object(analysis_store, 'persist_pipeline_result', side_effect=offline):
        uvicorn.run(app, host='127.0.0.1', port=8000)
