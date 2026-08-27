from __future__ import annotations


class SignatureError(ValueError):
    """The signature is missing, malformed, or does not cover the content hash."""


def recover_signer(content_hash: str, signature: str) -> str:
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
    except ImportError as error:
        raise SignatureError("eth_account is required to verify wallet signatures.") from error

    digest = content_hash.removeprefix("0x")
    if len(digest) != 64:
        raise SignatureError("A signed content hash must be 32 bytes.")
    try:
        message = encode_defunct(primitive=bytes.fromhex(digest))
        return Account.recover_message(message, signature=signature)
    except Exception as error:
        raise SignatureError("The signature could not be recovered.") from error
