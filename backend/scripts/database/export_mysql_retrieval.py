"""Export MySQL's retrieval view for a reproducible FAISS rebuild."""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BACKEND / "src"))

from persistence.patent_repository import load_patent_dataframe  # noqa: E402


if __name__ == "__main__":
    frame = load_patent_dataframe()
    if frame is None:
        raise SystemExit("MySQL retrieval view is unavailable. Bootstrap and configure MySQL first.")
    destination = _BACKEND.parent / "data" / "vector_store" / "mysql_retrieval_export.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)
    print(f"Exported {len(frame):,} MySQL retrieval rows to {destination}")
