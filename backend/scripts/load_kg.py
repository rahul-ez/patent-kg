"""
Neo4j Database Load — for teammates
=====================================
Loads the shared .dump file into your local Neo4j DBMS.
Run this instead of build_full_kg.py if you have the dump file.

Usage:
    cd patent-kg/backend
    python scripts/load_kg.py --dump <path_to_neo4j.dump>

Example:
    python scripts/load_kg.py --dump "C:/Shared/neo4j.dump"

IMPORTANT:
    1. Your Neo4j DBMS must be STOPPED before loading.
    2. Stop it in Neo4j Desktop, then run this script.
    3. After loading, start the DBMS again in Neo4j Desktop.

NEO4J_HOME must be set in your .env file (see .env.example).
It should point to your DBMS root folder, e.g.:
    NEO4J_HOME=C:\\Users\\you\\.Neo4jDesktop2\\Data\\dbmss\\dbms-<your-id>
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

_BACKEND = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND.parent / ".env")

NEO4J_HOME = os.getenv("NEO4J_HOME", "")


def main():
    parser = argparse.ArgumentParser(description="Load a Neo4j dump file.")
    parser.add_argument(
        "--dump", required=True,
        help="Path to the neo4j.dump file shared by your teammate.",
    )
    args = parser.parse_args()

    dump_file = Path(args.dump).resolve()
    if not dump_file.exists():
        print(f"[ERROR] Dump file not found: {dump_file}")
        sys.exit(1)

    if not NEO4J_HOME:
        print("[ERROR] NEO4J_HOME is not set in your .env file.")
        print("Set it to your DBMS root folder, e.g.:")
        print(r"  NEO4J_HOME=C:\Users\you\.Neo4jDesktop2\Data\dbmss\dbms-<your-id>")
        sys.exit(1)

    neo4j_admin = Path(NEO4J_HOME) / "bin" / "neo4j-admin.bat"
    if not neo4j_admin.exists():
        print(f"[ERROR] neo4j-admin.bat not found at: {neo4j_admin}")
        print("Check that NEO4J_HOME points to the correct DBMS folder.")
        sys.exit(1)

    print("=" * 60)
    print("  NEO4J DATABASE LOAD")
    print("=" * 60)
    print(f"  Dump file   : {dump_file}  ({dump_file.stat().st_size / 1e6:.1f} MB)")
    print(f"  neo4j-admin : {neo4j_admin}")
    print(f"  Target DB   : neo4j  (existing data will be overwritten)")
    print()

    answer = input("  Have you stopped the DBMS in Neo4j Desktop? [y/N]: ").strip().lower()
    if answer != "y":
        print("  Please stop the DBMS first, then re-run this script.")
        sys.exit(0)

    print("\n  Loading dump (this may take a minute) ...")

    result = subprocess.run(
        [
            str(neo4j_admin),
            "database", "load", "neo4j",
            f"--from-path={dump_file.parent}",
            "--overwrite-destination=true",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"\n[ERROR] Load failed:\n{result.stderr}")
        sys.exit(1)

    print("\n  Load complete.")
    print("  Start your DBMS in Neo4j Desktop, then open:")
    print("  http://localhost:7474")
    print("=" * 60)


if __name__ == "__main__":
    main()
