"""Pure water-quality data transformation utilities.

This package is deliberately independent of the HTTP API, frontend, wallet, and
blockchain layers. It converts source-shaped rows into the existing canonical
Pydantic models.
"""

from app.data_pipeline.community import normalize_community_event, normalize_community_row
from app.data_pipeline.ems import normalize_ems_event, normalize_ems_row
from app.data_pipeline.grouping import group_community_rows, group_ems_rows
from app.data_pipeline.mapping import (
    COMMUNITY_FIELD_ALIASES,
    EMS_PARAMETER_CODES,
    canonical_parameter_for_ems_code,
)

__all__ = [
    "COMMUNITY_FIELD_ALIASES",
    "EMS_PARAMETER_CODES",
    "canonical_parameter_for_ems_code",
    "group_ems_rows",
    "group_community_rows",
    "normalize_community_event",
    "normalize_community_row",
    "normalize_ems_event",
    "normalize_ems_row",
]
