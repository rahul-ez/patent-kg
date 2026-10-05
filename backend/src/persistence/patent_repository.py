"""MySQL-backed metadata repository with a CSV fallback for offline AI use."""
from __future__ import annotations

import logging

import pandas as pd

from .database import DatabaseUnavailable, get_engine

logger = logging.getLogger(__name__)

_COLUMNS = [
    "patent_id", "title", "abstract", "domain", "url", "jurisdiction",
    "cites_patent_count", "cited_by_patent_count", "family_size",
    "publication_year", "legal_status",
]


def load_patent_dataframe() -> pd.DataFrame | None:
    """Read the retrieval projection from MySQL, returning ``None`` when offline.

    The pipeline remains usable before bootstrap because its CSV fallback is
    intentional; once MySQL is configured it becomes the metadata authority.
    """
    try:
        from sqlalchemy import text
        with get_engine().connect() as connection:
            frame = pd.read_sql(text("""
                SELECT patent_id, title, abstract, domain, url,
                       jurisdiction, cites_patent_count, cited_by_patent_count,
                       family_size, publication_year, legal_status
                FROM vw_patent_retrieval
            """), connection)
    except (DatabaseUnavailable, ModuleNotFoundError):
        return None
    except Exception as exc:
        logger.warning("MySQL patent metadata unavailable; falling back to CSV: %s", exc)
        return None

    for column in _COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    # Nullable SQL integers otherwise become strings such as "2024.0", which
    # downstream year/count parsers cannot read as integers.
    for column in ("cites_patent_count", "cited_by_patent_count", "family_size", "publication_year"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64").astype(str).replace("<NA>", "")
    logger.info("Loaded %d patent metadata rows from MySQL.", len(frame))
    return frame[_COLUMNS].fillna("").astype(str)
