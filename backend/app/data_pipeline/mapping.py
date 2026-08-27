"""Canonical parameter mappings shared by community and EMS transformations."""

from __future__ import annotations

import re
from typing import Final

from app.models.parameters import (
    CANONICAL_UNITS as PROJECT_CANONICAL_UNITS,
    EMS_CODE_TO_FIELD,
)

COMMUNITY_FIELD_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "ph": ("ph", "ph_std_units"),
    "dissolved_oxygen": ("oxygen", "dissolved_oxygen", "do"),
    "conductivity": ("conductivity", "specific_conductance"),
    "temperature": ("water_temperature", "temperature", "water_temp"),
    "nitrate": ("nitrates", "nitrate"),
    "nitrite": ("nitrites", "nitrite"),
    "hardness": ("hardness",),
    "e_coli": ("e_coli", "ecoli", "e_coli_cfu_per_100ml"),
}

EMS_PARAMETER_CODES: Final[dict[str, tuple[str, ...]]] = {
    field: tuple(code for code, mapped_field in EMS_CODE_TO_FIELD.items() if mapped_field == field)
    for field in set(EMS_CODE_TO_FIELD.values())
}

CANONICAL_UNITS: Final[dict[str, str]] = dict(PROJECT_CANONICAL_UNITS)


def normalized_key(value: object) -> str:
    """Normalize a source column name for alias matching."""

    text = str(value).strip().casefold()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def canonical_parameter_for_ems_code(code: object) -> str | None:
    return EMS_CODE_TO_FIELD.get(str(code).strip().upper())


def canonical_parameter_for_community_field(field: object) -> str | None:
    normalized = normalized_key(field)
    for canonical, aliases in COMMUNITY_FIELD_ALIASES.items():
        if normalized in {normalized_key(alias) for alias in aliases}:
            return canonical
        if any(normalized.startswith(f"{normalized_key(alias)}_") for alias in aliases):
            return canonical
    return None
