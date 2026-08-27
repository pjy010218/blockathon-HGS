"""File-based data processing with JSONL output and hash-based deduplication."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from app.data_pipeline.community import normalize_community_event
from app.data_pipeline.errors import BatchSummary
from app.data_pipeline.ems import normalize_ems_event, normalize_ems_row
from app.data_pipeline.grouping import group_community_rows, group_ems_rows
from app.models.schemas import WaterQualityRecordCreate
from app.services.hashing import sha256_hex


def _hashable_payload(record: WaterQualityRecordCreate) -> dict[str, Any]:
    payload = record.model_dump(mode="json")
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("row_number", None)
    return payload


def record_with_hash(record: WaterQualityRecordCreate) -> dict[str, Any]:
    payload = record.model_dump(mode="json")
    payload["content_hash"] = sha256_hex(_hashable_payload(record))
    return payload


def _write_unique_records(
    records: Iterable[WaterQualityRecordCreate],
    output: Path,
    summary: BatchSummary,
) -> None:
    seen_hashes: set[str] = set()
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            content_hash = sha256_hex(_hashable_payload(record))
            if content_hash in seen_hashes:
                summary.duplicates += 1
                continue
            seen_hashes.add(content_hash)
            item = record.model_dump(mode="json")
            item["content_hash"] = content_hash
            stream.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
            summary.created += 1


def _csv_rows(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def process_community_csv(input_path: Path, output_path: Path) -> BatchSummary:
    summary = BatchSummary()

    def records() -> Iterator[WaterQualityRecordCreate]:
        for row_number, group in enumerate(group_community_rows(_csv_rows(input_path)), start=2):
            try:
                yield normalize_community_event(group, row_number=row_number)
            except Exception as error:
                summary.add_error(row_number, error, group[0] if group else {})

    _write_unique_records(records(), output_path, summary)
    return summary


def process_ems_csv(input_path: Path, output_path: Path) -> BatchSummary:
    summary = BatchSummary()

    def records() -> Iterator[WaterQualityRecordCreate]:
        for row_number, group in enumerate(group_ems_rows(_csv_rows(input_path)), start=2):
            supported = [normalize_ems_row(row, row_number=row_number) for row in group]
            summary.skipped_unmatched_params += sum(item is None for item in supported)
            try:
                yield normalize_ems_event(group, row_number=row_number)
            except Exception as error:
                summary.add_error(row_number, error, group[0] if group else {})

    _write_unique_records(records(), output_path, summary)
    return summary


def summary_as_dict(summary: BatchSummary) -> dict[str, Any]:
    return {
        "created": summary.created,
        "skipped_unmatched_params": summary.skipped_unmatched_params,
        "duplicates": summary.duplicates,
        "errors": [
            {
                "row_number": item.row_number,
                "message": item.message,
                "raw_payload": item.raw_payload,
            }
            for item in summary.errors
        ],
    }
