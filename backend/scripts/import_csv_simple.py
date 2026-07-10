"""Deprecated compatibility entry point for the old ad-hoc schema importer."""

from __future__ import annotations


def main() -> int:
    print(
        "This script is disabled because its CREATE TABLE and INSERT fields do not "
        "match database/schema/init_busmind.sql.\n"
        "Use:\n"
        "  python database/import/import_processed_to_mysql.py "
        "--processed-dir data/processed --dry-run"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
