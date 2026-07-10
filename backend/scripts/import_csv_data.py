"""Deprecated compatibility entry point.

The former script imported into obsolete model/table names. It is intentionally
blocked so it cannot corrupt the final BusMind schema.
"""

from __future__ import annotations


def main() -> int:
    print(
        "This importer is deprecated because it targets obsolete tables.\n"
        "Run the official importer from the project root instead:\n"
        "  python database/import/import_processed_to_mysql.py "
        "--processed-dir data/processed --dry-run\n"
        "Then remove --dry-run after checking the output."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
