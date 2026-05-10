"""
Full Knowledge Graph Builder — one-time offline run
====================================================
Populates Neo4j with the complete patent corpus (~58K patents) and all
satellite data: assignees, inventors, CPC codes, family edges, paper nodes.

Run from the patent-kg/backend directory:

    cd patent-kg/backend
    python scripts/build_full_kg.py

Prerequisites:
    1. Neo4j DBMS is running in Neo4j Desktop.
    2. .env file exists with NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD.
    3. All 7 CSV files are present in the project root (C:/PantentsAI/).

After completion this script prints dump instructions.
Run scripts/dump_kg.py next to produce the shareable .dump file.
"""

import logging
import sys
import time
from pathlib import Path

# Ensure src/ is importable when run as a script
_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND / "src"))

from dotenv import load_dotenv
load_dotenv(_BACKEND.parent / ".env")

from kg.builder import KGBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("build_full_kg")


def main():
    logger.info("=" * 60)
    logger.info("  FULL KNOWLEDGE GRAPH BUILD")
    logger.info("  This is a one-time operation. Go grab a coffee.")
    logger.info("=" * 60)

    t0 = time.perf_counter()

    with KGBuilder() as builder:
        builder.build_full_graph(batch_size=2000)

    elapsed = time.perf_counter() - t0
    mins, secs = divmod(int(elapsed), 60)

    logger.info("=" * 60)
    logger.info("  BUILD COMPLETE in %dm %02ds", mins, secs)
    logger.info("=" * 60)
    logger.info("")
    logger.info("Next step — create the shareable dump file:")
    logger.info("  1. Stop your Neo4j DBMS in Neo4j Desktop.")
    logger.info("  2. Run:  python scripts/dump_kg.py")
    logger.info("  3. Share the resulting .dump file with your teammates.")
    logger.info("")


if __name__ == "__main__":
    main()
