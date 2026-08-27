"""Normalize an EMS CSV into deduplicated canonical JSONL records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.data_pipeline.batch import process_ems_csv, summary_as_dict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="EMS CSV input path")
    parser.add_argument("output", type=Path, help="Canonical JSONL output path")
    args = parser.parse_args()
    summary = process_ems_csv(args.input, args.output)
    print(json.dumps(summary_as_dict(summary), ensure_ascii=False, indent=2))
    return 0 if not summary.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
