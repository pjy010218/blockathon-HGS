from __future__ import annotations

import os


def _parse_addresses(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip().lower() for item in value.split(",") if item.strip()}


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
        self._community = {address.lower() for address in (community or [])}
        self._government = {address.lower() for address in (government or [])}
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
        self._community = {address.lower() for address in community}
        self._government = {address.lower() for address in government}
