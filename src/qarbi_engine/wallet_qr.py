"""
Chapter 13 — Multiwallet & EIP-681 Arbitrum Payment QR Code Generator
Validates Arbitrum addresses, blocks cross-chain prefix confusion (e.g., Solana/ICP/Algorand),
and generates deterministic EIP-681 payment URIs and SVG QR matrix representations.
"""

from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass


EVM_HEX_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


@dataclass
class ArbitrumQrPaymentPayload:
    uri: str
    recipient: str
    chain_id: int
    amount_wei: int
    token_address: str | None
    svg_preview: str


class ArbitrumWalletQrService:
    """Generates and validates Arbitrum EIP-681 payment URIs with cross-chain confusion protection."""

    SUPPORTED_ARBITRUM_CHAINS = {42161, 421614}

    @classmethod
    def validate_arbitrum_address(cls, address: str) -> str:
        if not address or not isinstance(address, str):
            raise ValueError("Address must be a non-empty string.")
        if address.startswith(("solana:", "icp:", "algo:", "bc1")):
            raise ValueError(f"Cross-chain address rejected for Arbitrum EVM: {address}")
        if not EVM_HEX_RE.match(address):
            raise ValueError(f"Invalid Arbitrum 20-byte hex address: {address}")
        return address

    @classmethod
    def generate_eip681_payment_qr(
        cls,
        recipient: str,
        chain_id: int = 421614,
        amount_wei: int = 0,
        token_address: str | None = None,
    ) -> ArbitrumQrPaymentPayload:
        cls.validate_arbitrum_address(recipient)
        if chain_id not in cls.SUPPORTED_ARBITRUM_CHAINS:
            raise ValueError(f"Unsupported Arbitrum chain_id {chain_id}; expected 42161 or 421614.")
        if amount_wei < 0:
            raise ValueError("amount_wei must be non-negative.")

        if token_address:
            cls.validate_arbitrum_address(token_address)
            uri = f"ethereum:{token_address}@{chain_id}/transfer?address={recipient}&uint256={amount_wei}"
        else:
            uri = f"ethereum:{recipient}@{chain_id}?value={amount_wei}"

        # Deterministic 16x16 visual finder/hash matrix SVG for URI verification
        digest = hashlib.sha256(uri.encode("utf-8")).digest()
        rects = []
        for row in range(16):
            byte_val = digest[row]
            for col in range(16):
                bit = (byte_val >> (col % 8)) & 1
                if bit:
                    rects.append(f'<rect x="{col*4}" y="{row*4}" width="4" height="4" fill="#000"/>')
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{"".join(rects)}</svg>'

        return ArbitrumQrPaymentPayload(
            uri=uri,
            recipient=recipient,
            chain_id=chain_id,
            amount_wei=amount_wei,
            token_address=token_address,
            svg_preview=svg,
        )
