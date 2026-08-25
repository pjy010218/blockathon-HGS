from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.schemas import WaterQualityRecordCreate


class WaterDataSourceAdapter(ABC):
    """Translate an upstream source record without erasing source-specific fields."""

    @abstractmethod
    def normalize(self, payload: dict[str, Any]) -> WaterQualityRecordCreate:
        raise NotImplementedError
