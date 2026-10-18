"""
Chapter 5 — x402 Bazaar Payment Architecture & Persistent ACID Receipt Store
Implements HTTP 402 Payment-Required negotiation, Bazaar resource discovery metadata,
and replay-resistant SQLite receipt consumption bound to (receipt_id, resource_path, payer, chain_id).
"""

from __future__ import annotations
import hashlib
import hmac
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class X402PaymentRequirement:
    status_code: int
    version: str
    network: str
    chain_id: int
    resource_path: str
    amount_atomic: str
    token_symbol: str
    recipient_address: str
    bazaar_discovery_tag: str
    nonce: str


class X402BazaarGateway:
    """
    ACID-backed x402 payment verifier and Bazaar discovery service for Arbitrum AlphaFold/AlphaTensor APIs.
    Prevents receipt replay across process restarts.
    """

    def __init__(self, db_path: str | Path, treasury_address: str, hmac_secret: str, chain_id: int = 421614):
        if not treasury_address.startswith("0x") or len(treasury_address) != 42:
            raise ValueError("Invalid Arbitrum treasury address.")
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.treasury_address = treasury_address
        self.hmac_secret = hmac_secret.encode("utf-8")
        self.chain_id = chain_id
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS x402_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    tx_hash TEXT UNIQUE NOT NULL,
                    payer_address TEXT NOT NULL,
                    resource_path TEXT NOT NULL,
                    amount_atomic TEXT NOT NULL,
                    chain_id INTEGER NOT NULL,
                    consumed_at INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def list_bazaar_resources(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/api/x402/alphafold/fold-verify",
                "description": "Verify AlphaFold PDB C-alpha trace & pLDDT confidence for Arbitrum DeSci bounty",
                "amount_atomic": "1000000",  # 1.00 USDC (6 decimals) or QARBI atomic units
                "token": "USDC",
                "chain_id": self.chain_id,
                "bazaar_category": "desci.protein-folding",
            },
            {
                "path": "/api/x402/alphatensor/rank-verify",
                "description": "Verify AlphaTensor (U, V, W) bilinear matrix decomposition rank reduction",
                "amount_atomic": "2500000",
                "token": "USDC",
                "chain_id": self.chain_id,
                "bazaar_category": "desci.tensor-algorithms",
            },
        ]

    def create_402_challenge(self, resource_path: str, amount_atomic: str, nonce: str) -> X402PaymentRequirement:
        return X402PaymentRequirement(
            status_code=402,
            version="x402-v2",
            network="arbitrum-sepolia" if self.chain_id == 421614 else "arbitrum-one",
            chain_id=self.chain_id,
            resource_path=resource_path,
            amount_atomic=amount_atomic,
            token_symbol="USDC",
            recipient_address=self.treasury_address,
            bazaar_discovery_tag="qarbi-alphafold-alphatensor",
            nonce=nonce,
        )

    def sign_facilitator_proof(
        self,
        receipt_id: str,
        tx_hash: str,
        payer_address: str,
        resource_path: str,
        amount_atomic: str,
    ) -> str:
        canonical = f"{receipt_id}|{tx_hash}|{payer_address.lower()}|{resource_path}|{amount_atomic}|{self.chain_id}"
        return hmac.new(self.hmac_secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_and_consume_receipt(
        self,
        receipt_id: str,
        tx_hash: str,
        payer_address: str,
        resource_path: str,
        amount_atomic: str,
        required_amount_atomic: str,
        signature: str,
    ) -> Dict[str, Any]:
        if int(amount_atomic) < int(required_amount_atomic):
            raise PermissionError("Insufficient x402 payment amount.")
        if not tx_hash.startswith("0x") or len(tx_hash) != 66:
            raise ValueError("Invalid Arbitrum transaction hash format.")

        expected_sig = self.sign_facilitator_proof(
            receipt_id=receipt_id,
            tx_hash=tx_hash,
            payer_address=payer_address,
            resource_path=resource_path,
            amount_atomic=amount_atomic,
        )
        if not hmac.compare_digest(expected_sig, signature):
            raise PermissionError("Invalid x402 facilitator signature.")

        now_ts = int(time.time())
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO x402_receipts
                    (receipt_id, tx_hash, payer_address, resource_path, amount_atomic, chain_id, consumed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (receipt_id, tx_hash, payer_address.lower(), resource_path, amount_atomic, self.chain_id, now_ts),
                )
                conn.commit()
        except sqlite3.IntegrityError as exc:
            raise PermissionError(f"Replay detected: receipt or tx_hash already consumed ({exc})") from exc

        return {
            "status": "SETTLED",
            "receipt_id": receipt_id,
            "tx_hash": tx_hash,
            "resource_path": resource_path,
            "chain_id": self.chain_id,
            "consumed_at": now_ts,
        }
