"""Errors and structured results for batch data processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class DataNormalizationError(ValueError):
    """A source row cannot be converted into a canonical record."""


@dataclass(frozen=True)
class RowError:
    row_number: int | None
    message: str
    raw_payload: dict[str, Any]


@dataclass
class BatchSummary:
    created: int = 0
    skipped_unmatched_params: int = 0
    duplicates: int = 0
    errors: list[RowError] = field(default_factory=list)

    def add_error(self, row_number: int | None, error: Exception, raw_payload: dict[str, Any]) -> None:
        self.errors.append(RowError(row_number, str(error), dict(raw_payload)))
