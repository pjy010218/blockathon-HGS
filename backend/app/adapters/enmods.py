from __future__ import annotations

from typing import Any

from app.adapters.base import WaterDataSourceAdapter
from app.models.schemas import WaterQualityRecordCreate


class EnmodsAdapter(WaterDataSourceAdapter):
    """Placeholder for the B.C. EnMoDS/BC Data Catalogue connector.

    Keep the upstream row in ``raw_payload`` when implementing the field mapping.
    Do not discard fields that have no current canonical equivalent.
    """

    def normalize(self, payload: dict[str, Any]) -> WaterQualityRecordCreate:
        raise NotImplementedError("EnMoDS field mapping is the next implementation step")
