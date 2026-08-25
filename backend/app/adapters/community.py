from __future__ import annotations

from typing import Any

from app.adapters.base import WaterDataSourceAdapter
from app.models.schemas import WaterQualityRecordCreate


class CommunityDataAdapter(WaterDataSourceAdapter):
    """Placeholder for DataStream/Water Rangers API connectors."""

    def normalize(self, payload: dict[str, Any]) -> WaterQualityRecordCreate:
        raise NotImplementedError(
            "DataStream/Water Rangers field mapping is the next implementation step"
        )
