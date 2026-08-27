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


def canonical_field_for_ems_code(code: str) -> str | None:
    return EMS_CODE_TO_FIELD.get(code.strip().upper())
