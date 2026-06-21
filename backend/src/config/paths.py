from pathlib import Path

# __file__ is project_root/patent-kg/backend/src/config/paths.py
# parents[0] -> config/
# parents[1] -> src/
# parents[2] -> backend/
# parents[3] -> patent-kg/
# parents[4] -> project_root/
ROOT = Path(__file__).resolve().parents[4]

PATENT_KG_DIR = ROOT / "patent-kg"
BACKEND_DIR = PATENT_KG_DIR / "backend"

# Centralized data paths
DATA_DIR = ROOT / "data"
PROCESSED_DATA = DATA_DIR / "processed"
VECTOR_STORE = PATENT_KG_DIR / "data" / "vector_store"
