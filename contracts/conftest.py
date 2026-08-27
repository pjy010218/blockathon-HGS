"""Test fixtures: compile once, then deploy to an in-process EVM per test.

The tests never touch a public network. ``EthereumTesterProvider`` runs a real
EVM inside the test process, so contract behaviour is exercised for real without
an RPC endpoint, a funded key, or a testnet faucet.

Accounts are kept in distinct roles so the issuer rules are exercised honestly:
the owner is not a submitter, and one account is deliberately left unregistered.
"""

from __future__ import annotations

import pytest

pytest.importorskip("web3", reason="Install contracts/requirements.txt to run contract tests")

from web3 import EthereumTesterProvider, Web3  # noqa: E402

from build import compile_credential, compile_registry  # noqa: E402

# Roles are named in the contract's interface; these are the stored encodings.
ROLE_COMMUNITY = b"community".ljust(32, b"\x00")
ROLE_GOVERNMENT = b"government".ljust(32, b"\x00")


@pytest.fixture(scope="session")
def compiled_registry() -> tuple[list[dict], str]:
    return compile_registry()


@pytest.fixture(scope="session")
def compiled_credential() -> tuple[list[dict], str]:
    return compile_credential()


@pytest.fixture
def web3() -> Web3:
    return Web3(EthereumTesterProvider())


@pytest.fixture
def owner(web3: Web3) -> str:
    """Deploys the registry and administers the issuer list. Never a submitter."""

    return web3.eth.accounts[0]


@pytest.fixture
def submitter(web3: Web3) -> str:
    return web3.eth.accounts[1]


@pytest.fixture
def other_submitter(web3: Web3) -> str:
    return web3.eth.accounts[2]


@pytest.fixture
def unregistered(web3: Web3) -> str:
    """Holds no issuer role, so it must not be able to anchor anything."""

    return web3.eth.accounts[3]


@pytest.fixture
def registry(
    web3: Web3,
    compiled_registry: tuple[list[dict], str],
    owner: str,
    submitter: str,
    other_submitter: str,
):
    abi, bytecode = compiled_registry
    factory = web3.eth.contract(abi=abi, bytecode=bytecode)
    receipt = web3.eth.wait_for_transaction_receipt(
        factory.constructor().transact({"from": owner})
    )
    deployed = web3.eth.contract(address=receipt["contractAddress"], abi=abi)

    for account in (submitter, other_submitter):
        web3.eth.wait_for_transaction_receipt(
            deployed.functions.registerIssuer(account, "community").transact(
                {"from": owner}
            )
        )
    return deployed


@pytest.fixture
def credential(
    web3: Web3, compiled_credential: tuple[list[dict], str], registry, owner: str
):
    abi, bytecode = compiled_credential
    factory = web3.eth.contract(abi=abi, bytecode=bytecode)
    receipt = web3.eth.wait_for_transaction_receipt(
        factory.constructor(registry.address).transact({"from": owner})
    )
    return web3.eth.contract(address=receipt["contractAddress"], abi=abi)
