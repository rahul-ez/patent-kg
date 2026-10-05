"""Keep computed output and saving status distinct, with safe public errors."""
import logging
import os

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def attach_saving_status(result: dict, save) -> dict:
    try:
        saved = save()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("Analysis persistence failed (%s)", type(exc).__name__)
        if os.getenv("PERSISTENCE_REQUIRED", "false").lower() == "true":
            raise HTTPException(status_code=503, detail="Analysis completed, but saving to MySQL failed.") from exc
        result.update(persistence_status="not_saved", persistence_message="Results are available, but were not saved to MySQL.")
    else:
        result.update(saved or {})
        result["persistence_status"] = "persisted"
    return result
