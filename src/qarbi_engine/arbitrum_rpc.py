"""
Chapter 3 & 4 — Arbitrum Multichain Adapter & QuickNode RPC Service
Supports Arbitrum One (Chain ID 42161) and Arbitrum Sepolia (Chain ID 421614)
with circuit-breaker health tracking, secret redaction, and failover management.
"""

from __future__ import annotations
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


SUPPORTED_NETWORKS: Dict[str, Dict[str, Any]] = {
    "arbitrum-one": {
        "chain_id": 42161,
        "hex_chain_id": "0xa4b1",
        "explorer": "https://arbiscan.io",
        "native_symbol": "ETH",
        "rollup": "Arbitrum Nitro Optimistic Rollup",
    },
    "arbitrum-sepolia": {
        "chain_id": 421614,
        "hex_chain_id": "0x66eee",
        "explorer": "https://sepolia.arbiscan.io",
        "native_symbol": "ETH",
        "rollup": "Arbitrum Nitro Sepolia Testnet",
    },
}


@dataclass
class RpcEndpointHealth:
    provider_name: str
    redacted_url: str
    network: str
    expected_chain_id: int
    circuit_open: bool
    consecutive_failures: int
    last_checked_ts: float


class ArbitrumQuickNodeAdapter:
    """
    Chain-adapter and QuickNode RPC manager for Arbitrum L2.
    Enforces strict network validation and redacts private QuickNode tokens in logs.
    """

    def __init__(
        self,
        network: str = "arbitrum-sepolia",
        quicknode_rpc_url: Optional[str] = None,
        fallback_rpc_url: str = "https://sepolia-rollup.arbitrum.io/rpc",
        circuit_breaker_threshold: int = 3,
    ):
        if network not in SUPPORTED_NETWORKS:
            raise ValueError(
                f"Unsupported network '{network}'. Supported Arbitrum networks: {list(SUPPORTED_NETWORKS.keys())}"
            )
        self.network = network
        self.chain_meta = SUPPORTED_NETWORKS[network]
        self.quicknode_rpc_url = quicknode_rpc_url or ""
        self.fallback_rpc_url = fallback_rpc_url
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.consecutive_failures = 0
        self.circuit_open = False

    @staticmethod
    def redact_rpc_url(url: str) -> str:
        if not url:
            return "<UNCONFIGURED>"
        # Redact QuickNode token segments after .quiknode.pro/
        return re.sub(r"(\.quiknode\.pro/)([^/?#]+)", r"\1<REDACTED_TOKEN>", url)

    def build_json_rpc_payload(self, method: str, params: Optional[List[Any]] = None, request_id: int = 1) -> Dict[str, Any]:
        if not method or not isinstance(method, str):
            raise ValueError("RPC method must be a non-empty string.")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or [],
        }

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.circuit_breaker_threshold:
            self.circuit_open = True

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.circuit_open = False

    def verify_chain_id_response(self, hex_chain_id: str) -> bool:
        actual = int(hex_chain_id, 16)
        expected = self.chain_meta["chain_id"]
        if actual != expected:
            self.record_failure()
            raise RuntimeError(f"Chain ID mismatch on {self.network}: expected {expected}, got {actual}")
        self.record_success()
        return True

    def health_status(self) -> RpcEndpointHealth:
        active_url = self.quicknode_rpc_url if (self.quicknode_rpc_url and not self.circuit_open) else self.fallback_rpc_url
        provider = "QuickNode" if active_url == self.quicknode_rpc_url and self.quicknode_rpc_url else "ArbitrumFallback"
        return RpcEndpointHealth(
            provider_name=provider,
            redacted_url=self.redact_rpc_url(active_url),
            network=self.network,
            expected_chain_id=self.chain_meta["chain_id"],
            circuit_open=self.circuit_open,
            consecutive_failures=self.consecutive_failures,
            last_checked_ts=time.time(),
        )
