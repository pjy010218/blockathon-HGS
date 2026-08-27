from __future__ import annotations

# Canonical intersection used for EMS filtering and community mapping.
# Codes are compared case-insensitively.

EMS_CODE_TO_FIELD: dict[str, str] = {
    "0004": "ph",
    "PH-F": "ph",
    "DO-F": "dissolved_oxygen",
    "0011": "conductivity",
    "EC-F": "conductivity",
    "SC-F": "conductivity",
    "TEMF": "temperature",
    "1110": "nitrate",
    "1111": "nitrite",
    "1107": "hardness",
    "0147": "e_coli",
}

CANONICAL_UNITS: dict[str, str] = {
    "ph": "pH",
    "dissolved_oxygen": "mg/L",
    "conductivity": "µS/cm",
    "temperature": "°C",
    "nitrate": "mg/L",
    "nitrite": "mg/L",
    "hardness": "mg/L as CaCO3",
    "e_coli": "CFU/100mL",
}

UNDETECTED_TOKENS = {"", "NOT_DETECTED", "ND", "N/A", "NA", "NULL"}

COMMUNITY_COLUMN_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ph", ("ph",)),
    ("dissolved_oxygen", ("oxygen", "dissolved_oxygen")),
    ("conductivity", ("conductivity",)),
    ("temperature", ("water_temperature", "temperature")),
    ("nitrate", ("nitrates", "nitrate")),
    ("nitrite", ("nitrites", "nitrite")),
    ("hardness", ("hardness",)),
    ("e_coli", ("e_coli", "ecoli")),
)


def canonical_field_for_ems_code(code: str) -> str | None:
    return EMS_CODE_TO_FIELD.get(code.strip().upper())


def canonical_field_for_community_column(name: str) -> str | None:
    key = name.strip().lower()
    for field, hints in COMMUNITY_COLUMN_HINTS:
        for hint in hints:
            if key == hint or key.startswith(f"{hint} ") or key.startswith(f"{hint}("):
                return field
    return None


def parse_measurement_value(raw: object) -> object | None:
    if raw is None:
        return None
    if isinstance(raw, str) and raw.strip().upper() in UNDETECTED_TOKENS:
        return None
    if isinstance(raw, (int, float, bool)):
        return raw
    text = str(raw).strip()
    if text.upper() in UNDETECTED_TOKENS:
        return None
    try:
        return float(text)
    except ValueError:
        return None
