"""
Neo4j Database Dump — run after build_full_kg.py
=================================================
Exports the Neo4j 'neo4j' database to a .dump file that teammates
can load with scripts/load_kg.py.

IMPORTANT: Your Neo4j DBMS must be STOPPED before running this.
Stop it in Neo4j Desktop, then run:

    cd patent-kg/backend
    python scripts/dump_kg.py

The dump file will be saved to:
    patent-kg/data/kg_dump/neo4j.dump

Share this file with teammates via Google Drive / OneDrive / shared storage.
"""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

_BACKEND  = Path(__file__).resolve().parent.parent
_DUMP_DIR = _BACKEND.parent / "data" / "kg_dump"

load_dotenv(_BACKEND.parent / ".env")

# NEO4J_HOME must point to the DBMS root (the folder containing bin/)
# e.g. C:\Users\you\.Neo4jDesktop2\Data\dbmss\dbms-<id>
NEO4J_HOME = os.getenv(
    "NEO4J_HOME",
    r"C:\Users\samku\.Neo4jDesktop2\Data\dbmss\dbms-47a4a4b2-4d37-440f-bdc5-e8fc41bfdfc9",
)


def main():
    neo4j_admin = Path(NEO4J_HOME) / "bin" / "neo4j-admin.bat"

    if not neo4j_admin.exists():
        print(f"[ERROR] neo4j-admin.bat not found at: {neo4j_admin}")
        print("Set NEO4J_HOME in your .env to the DBMS root folder.")
        sys.exit(1)

    _DUMP_DIR.mkdir(parents=True, exist_ok=True)
    dump_path = _DUMP_DIR / "neo4j.dump"

    print("=" * 60)
    print("  NEO4J DATABASE DUMP")
    print("=" * 60)
    print(f"  neo4j-admin : {neo4j_admin}")
    print(f"  Output      : {dump_path}")
    print()

    # Confirm the DB is stopped
    answer = input("  Have you stopped the DBMS in Neo4j Desktop? [y/N]: ").strip().lower()
    if answer != "y":
        print("  Please stop the DBMS first, then re-run this script.")
        sys.exit(0)

    print("\n  Running dump (this may take a minute) ...")

    result = subprocess.run(
        [
            str(neo4j_admin),
            "database", "dump", "neo4j",
            f"--to-path={_DUMP_DIR}",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"\n[ERROR] Dump failed:\n{result.stderr}")
        sys.exit(1)

    size_mb = dump_path.stat().st_size / (1024 * 1024) if dump_path.exists() else 0
    print(f"\n  Dump complete: {dump_path}  ({size_mb:.1f} MB)")
    print()
    print("  Share this file with teammates.")
    print("  They load it with:  python scripts/load_kg.py --dump <path_to_neo4j.dump>")
    print("=" * 60)


if __name__ == "__main__":
    main()
