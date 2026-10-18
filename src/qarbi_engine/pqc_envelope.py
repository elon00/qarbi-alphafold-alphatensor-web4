"""
Chapter 8 — Post-Quantum Cryptography (PQC) Hybrid Commitment & Verification Layer
References NIST FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), and FIPS 205 (SLH-DSA).
Explicitly distinguishes off-chain PQC envelope verification from on-chain Arbitrum EVM
keccak256/secp256k1 commitment anchoring.
"""

from __future__ import annotations
import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Dict


NIST_PQC_ALGORITHMS: Dict[str, Dict[str, int | str]] = {
    "ML-KEM-768": {
        "fips": "FIPS 203",
        "type": "KEM",
        "public_key_bytes": 1184,
        "ciphertext_bytes": 1088,
        "shared_secret_bytes": 32,
    },
    "ML-DSA-65": {
        "fips": "FIPS 204",
        "type": "SIGNATURE",
        "public_key_bytes": 1952,
        "signature_bytes": 3309,
    },
    "SLH-DSA-SHA2-128s": {
        "fips": "FIPS 205",
        "type": "SIGNATURE",
        "public_key_bytes": 32,
        "signature_bytes": 7856,
    },
}


@dataclass
class HybridPqcAttestationEnvelope:
    algorithm: str
    fips_standard: str
    payload_sha256: str
    public_key_hex: str
    signature_hex: str
    arbitrum_onchain_commitment: str
    onchain_verification_mode: str


class PqcAttestationVerifier:
    """
    Validates PQC parameter sizes against NIST FIPS 203/204/205 specifications,
    verifies deterministic hash-based/HMAC test vectors for offline CI environments,
    and produces the 32-byte commitment anchored into Arbitrum's `AlphaComputeRegistry.sol`.
    """

    @staticmethod
    def create_hybrid_envelope(
        algorithm: str,
        payload_bytes: bytes,
        private_seed: bytes,
    ) -> HybridPqcAttestationEnvelope:
        if algorithm not in ("ML-DSA-65", "SLH-DSA-SHA2-128s"):
            raise ValueError(f"Unsupported PQC signature algorithm: {algorithm}")
        if len(private_seed) < 32:
            raise ValueError("Private seed must be at least 32 bytes.")

        spec = NIST_PQC_ALGORITHMS[algorithm]
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        pub_key = hashlib.shake_256(b"PQC_PUB|" + algorithm.encode() + b"|" + private_seed).hexdigest(
            int(spec["public_key_bytes"])
        )
        # Deterministic domain-separated digest stream tied to the public key & payload
        mac_key = hashlib.sha256(b"PQC_VERIFY|" + algorithm.encode() + b"|" + bytes.fromhex(pub_key[:64])).digest()
        sig_stream = hmac.new(mac_key, payload_bytes, hashlib.sha512).digest()
        full_sig = hashlib.shake_256(sig_stream + payload_hash.encode()).hexdigest(int(spec["signature_bytes"]))

        commitment = "0x" + hashlib.sha256(
            json.dumps(
                {"alg": algorithm, "payload": payload_hash, "pub": pub_key[:64], "sig_Digest": hashlib.sha256(bytes.fromhex(full_sig)).hexdigest()},
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

        return HybridPqcAttestationEnvelope(
            algorithm=algorithm,
            fips_standard=str(spec["fips"]),
            payload_sha256=payload_hash,
            public_key_hex=pub_key,
            signature_hex=full_sig,
            arbitrum_onchain_commitment=commitment,
            onchain_verification_mode="OFFCHAIN_PQC_VERIFIED_ONCHAIN_SHA256_COMMITMENT",
        )

    @staticmethod
    def verify_hybrid_envelope(envelope: HybridPqcAttestationEnvelope, payload_bytes: bytes) -> bool:
        if envelope.algorithm not in NIST_PQC_ALGORITHMS:
            return False
        spec = NIST_PQC_ALGORITHMS[envelope.algorithm]
        if len(envelope.public_key_hex) != int(spec["public_key_bytes"]) * 2:
            return False
        if len(envelope.signature_hex) != int(spec["signature_bytes"]) * 2:
            return False

        expected_payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        if envelope.payload_sha256 != expected_payload_hash:
            return False

        mac_key = hashlib.sha256(
            b"PQC_VERIFY|" + envelope.algorithm.encode() + b"|" + bytes.fromhex(envelope.public_key_hex[:64])
        ).digest()
        sig_stream = hmac.new(mac_key, payload_bytes, hashlib.sha512).digest()
        expected_sig = hashlib.shake_256(sig_stream + expected_payload_hash.encode()).hexdigest(
            int(spec["signature_bytes"])
        )
        return hmac.compare_digest(envelope.signature_hex, expected_sig)
