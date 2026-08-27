from __future__ import annotations

import os

from eth_utils import is_address, to_checksum_address


class IssuerConfigurationError(ValueError):
    """Raised when operator issuer configuration contains an invalid address."""


def _parse_addresses(value: str | None) -> set[str]:
    if not value:
        return set()
    addresses: set[str] = set()
    for item in value.split(","):
        address = item.strip()
        if not address:
            continue
        if not is_address(address):
            raise IssuerConfigurationError(
                "Issuer configuration contains an invalid Ethereum address."
            )
        addresses.add(to_checksum_address(address).lower())
    return addresses


class IssuerRegistry:
    """Allowlist of wallets permitted to ingest under a role.

    On-chain `isIssuer` stays the source of truth after registration. Until
    the API queries the contract on every request, operators mirror those
    addresses in COMMUNITY_ISSUERS and GOVERNMENT_ISSUERS.
    """

    def __init__(
        self,
        *,
        community: list[str] | None = None,
        government: list[str] | None = None,
    ) -> None:
        self._community = _normalize_configured_addresses(community or [])
        self._government = _normalize_configured_addresses(government or [])
        if community is None:
            self._community = _parse_addresses(os.getenv("COMMUNITY_ISSUERS"))
        if government is None:
            self._government = _parse_addresses(os.getenv("GOVERNMENT_ISSUERS"))

    def is_issuer(self, address: str, role: str) -> bool:
        normalized = address.lower()
        if role == "community":
            return normalized in self._community
        if role == "government":
            return normalized in self._government
        return False

    def require(self, address: str, role: str) -> None:
        if not self.is_issuer(address, role):
            raise PermissionError(
                f"This wallet is not registered as a {role} issuer."
            )

    def reset(self, *, community: list[str], government: list[str]) -> None:
        self._community = _normalize_configured_addresses(community)
        self._government = _normalize_configured_addresses(government)


def _normalize_configured_addresses(addresses: list[str]) -> set[str]:
    normalized: set[str] = set()
    for address in addresses:
        address = address.strip()
        if not is_address(address):
            raise IssuerConfigurationError(
                "Issuer configuration contains an invalid Ethereum address."
            )
        normalized.add(to_checksum_address(address).lower())
    return normalized
