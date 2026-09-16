from pathlib import Path

# __file__ is patent-kg/backend/src/config/paths.py
# parents[0] -> config/
# parents[1] -> src/
# parents[2] -> backend/
# parents[3] -> patent-kg/
# parents[3] -> patent-kg/
ROOT = Path(__file__).resolve().parents[3]

PATENT_KG_DIR = ROOT
BACKEND_DIR = ROOT / "backend"

# Centralized data paths
DATA_DIR = ROOT / "data"
PROCESSED_DATA = DATA_DIR / "processed"
VECTOR_STORE = DATA_DIR / "vector_store"
