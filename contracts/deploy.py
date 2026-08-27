"""Deploy this project's contracts to an Ethereum network.

Configuration comes from the environment so no key ever reaches the repository:

    ETH_RPC_URL      JSON-RPC endpoint for the target network
    ETH_PRIVATE_KEY  Deploying account's key. Testnet only.

Usage::

    .venv/bin/python deploy.py --dry-run
    .venv/bin/python deploy.py
    .venv/bin/python deploy.py --contract VolunteerCredential --registry 0x...

VolunteerCredential reads the registry, so it needs the deployed registry address.

The script refuses to run against Ethereum mainnet. This project anchors to a
testnet only; a mainnet deployment would be a decision to make deliberately and
not by leaving an RPC URL set.
"""

from __future__ import annotations

import argparse
import os
import sys

from web3 import Web3

from build import CREDENTIAL_NAME, REGISTRY_NAME, compile_contract

MAINNET_CHAIN_ID = 1
CONFIRMATION_TIMEOUT_SECONDS = 300


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(f"{name} is not set. See the module docstring for required configuration.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy a contract")
    parser.add_argument(
        "--contract",
        default=REGISTRY_NAME,
        choices=[REGISTRY_NAME, CREDENTIAL_NAME],
        help="Which contract to deploy.",
    )
    parser.add_argument(
        "--registry",
        help=f"Deployed {REGISTRY_NAME} address. Required for {CREDENTIAL_NAME}.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compile, report the gas estimate and deployer balance, then stop.",
    )
    arguments = parser.parse_args()

    if arguments.contract == CREDENTIAL_NAME and not arguments.registry:
        sys.exit(f"--registry is required when deploying {CREDENTIAL_NAME}.")

    rpc_url = _require_env("ETH_RPC_URL")
    private_key = _require_env("ETH_PRIVATE_KEY")

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        sys.exit("Could not reach the RPC endpoint. Check ETH_RPC_URL.")

    chain_id = web3.eth.chain_id
    if chain_id == MAINNET_CHAIN_ID:
        sys.exit("Refusing to deploy to Ethereum mainnet. This project is testnet only.")

    account = web3.eth.account.from_key(private_key)
    balance_wei = web3.eth.get_balance(account.address)

    constructor_arguments = (
        (Web3.to_checksum_address(arguments.registry),)
        if arguments.contract == CREDENTIAL_NAME
        else ()
    )

    abi, bytecode = compile_contract(arguments.contract)
    factory = web3.eth.contract(abi=abi, bytecode=bytecode)
    constructor = factory.constructor(*constructor_arguments)
    gas_estimate = constructor.estimate_gas({"from": account.address})

    print(f"contract         : {arguments.contract}")
    print(f"network chain id : {chain_id}")
    print(f"deployer         : {account.address}")
    print(f"balance          : {web3.from_wei(balance_wei, 'ether')} ETH")
    print(f"gas estimate     : {gas_estimate}")

    if arguments.dry_run:
        print("dry run: nothing was broadcast")
        return

    if balance_wei == 0:
        sys.exit("Deployer balance is zero. Fund the account from a testnet faucet first.")

    transaction = constructor.build_transaction(
        {
            "from": account.address,
            "nonce": web3.eth.get_transaction_count(account.address),
            "chainId": chain_id,
        }
    )
    signed = account.sign_transaction(transaction)
    transaction_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"transaction      : {transaction_hash.hex()}")
    print("waiting for confirmation...")

    receipt = web3.eth.wait_for_transaction_receipt(
        transaction_hash, timeout=CONFIRMATION_TIMEOUT_SECONDS
    )
    if receipt["status"] != 1:
        sys.exit(f"Deployment transaction reverted in block {receipt['blockNumber']}.")

    print(f"contract address : {receipt['contractAddress']}")
    print(f"block number     : {receipt['blockNumber']}")
    print(f"gas used         : {receipt['gasUsed']}")


if __name__ == "__main__":
    main()
