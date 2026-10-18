"""
Chapter 15 — Comprehensive Unit, Smoke, Sanity, and Regression Test Suite
Tests:
1. Conway B3/S23 Automaton (Block still-life, Blinker oscillator, Glider translation, checkpoint rollback)
2. AlphaTensor 2x2 Rank-7 Strassen/AlphaTensor Bilinear Decomposition Verifier (R and Z_2)
3. AlphaFold C-alpha PDB Trace & pLDDT Confidence Verifier
4. Arbitrum QuickNode RPC Adapter (Chain ID validation, token redaction, circuit breaker)
5. x402 Bazaar Payment Gateway (HTTP 402 challenge, ACID SQLite receipt settlement, replay rejection)
6. NIST PQC Hybrid Attestation Envelope (ML-DSA-65 & SLH-DSA-SHA2-128s verification & tamper rejection)
7. Raven RSI & REA Governance Loop (AST inspection, forbidden action blocking, regression blocking)
8. Governed Uncapped Tokenomics (M(t) = min(R(t), annual_emission_limit(t)))
9. Multiwallet EIP-681 Arbitrum QR Payment Generator & Cross-Chain Guard
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qarbi_engine.conway_engine import ConwayAutomatonEngine
from qarbi_engine.alpha_science import AlphaTensorVerifier, AlphaFoldStructureVerifier
from qarbi_engine.arbitrum_rpc import ArbitrumQuickNodeAdapter
from qarbi_engine.x402_bazaar import X402BazaarGateway
from qarbi_engine.pqc_envelope import PqcAttestationVerifier
from qarbi_engine.raven_rea_governor import ReaCodeInspector, RavenRsiGovernor
from qarbi_engine.tokenomics_sim import GovernedTokenomicsEngine
from qarbi_engine.wallet_qr import ArbitrumWalletQrService


class TestQarbiArbitrumSuite(unittest.TestCase):
    def test_01_conway_b3_s23_still_life_oscillator_glider(self) -> None:
        # 1. Still-life: 2x2 Block must remain invariant
        engine = ConwayAutomatonEngine(width=16, height=16)
        block = [(4, 4), (4, 5), (5, 4), (5, 5)]
        engine.load_cells(block)
        snap = engine.step(5)
        self.assertEqual(snap.live_cells, sorted(block))

        # 2. Oscillator: Blinker period 2
        engine.load_cells([(6, 5), (6, 6), (6, 7)])
        h0 = engine.state_hash()
        s1 = engine.step(1)
        self.assertEqual(s1.live_cells, [(5, 6), (6, 6), (7, 6)])
        s2 = engine.step(1)
        self.assertEqual(s2.live_cells, [(6, 5), (6, 6), (6, 7)])
        self.assertNotEqual(h0, s2.state_hash)  # generation counter increments in hash

        # 3. Glider shifts by (+1, +1) after 4 generations
        glider = [(1, 2), (2, 3), (3, 1), (3, 2), (3, 3)]
        engine.load_cells(glider)
        s4 = engine.step(4)
        expected_shifted = sorted([(r + 1, c + 1) for r, c in glider])
        self.assertEqual(s4.live_cells, expected_shifted)

        # 4. Checkpoint restore
        restored = engine.restore_checkpoint(0)
        self.assertEqual(restored.generation, 0)
        self.assertEqual(restored.live_cells, sorted(glider))

    def test_02_alphatensor_rank7_verification(self) -> None:
        U, V, W = AlphaTensorVerifier.build_strassen_2x2_factors()
        proof = AlphaTensorVerifier.verify_decomposition(2, 2, 2, U, V, W)
        self.assertEqual(proof.discovered_rank, 7)
        self.assertEqual(proof.baseline_rank, 8)
        self.assertTrue(proof.exact_over_reals)
        self.assertTrue(proof.exact_over_z2)

    def test_03_alphafold_pdb_trace_and_plddt(self) -> None:
        sample_pdb = """
ATOM      1  CA  ALA A   1       1.200   2.300   3.400  1.00 96.40           C
ATOM      2  CA  GLY A   2       4.900   2.500   3.600  1.00 94.10           C
ATOM      3  CA  VAL A   3       8.400   2.800   3.900  1.00 92.20           C
""".strip()
        proof = AlphaFoldStructureVerifier.verify_pdb_ca_trace(sample_pdb)
        self.assertEqual(proof.sequence, "AGV")
        self.assertEqual(proof.residue_count, 3)
        self.assertAlmostEqual(proof.mean_plddt, 94.23, places=2)
        self.assertEqual(proof.mean_plddt_scaled, 9423)
        self.assertGreaterEqual(proof.contact_pairs_under_8a, 2)

    def test_04_arbitrum_quicknode_rpc_and_redaction(self) -> None:
        raw_url = "https://shy-dawn.arbitrum-sepolia.quiknode.pro/998877665544332211abcdef/"
        adapter = ArbitrumQuickNodeAdapter(network="arbitrum-sepolia", quicknode_rpc_url=raw_url)
        health = adapter.health_status()
        self.assertNotIn("998877665544332211abcdef", health.redacted_url)
        self.assertIn("<REDACTED_TOKEN>", health.redacted_url)
        self.assertTrue(adapter.verify_chain_id_response("0x66eee"))
        with self.assertRaises(RuntimeError):
            adapter.verify_chain_id_response("0x1")  # Ethereum Mainnet mismatch

    def test_05_x402_bazaar_payment_and_replay_protection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = Path(tmpdir) / "x402.sqlite3"
            gw = X402BazaarGateway(
                db_path=db_file,
                treasury_address="0x1111111111111111111111111111111111111111",
                hmac_secret="test-facilitator-secret-key",
                chain_id=421614,
            )
            challenge = gw.create_402_challenge("/api/x402/alphafold/fold-verify", "1000000", "nonce-001")
            self.assertEqual(challenge.status_code, 402)

            tx_hash = "0x" + "a" * 64
            payer = "0x2222222222222222222222222222222222222222"
            sig = gw.sign_facilitator_proof(
                receipt_id="rcpt-1001",
                tx_hash=tx_hash,
                payer_address=payer,
                resource_path="/api/x402/alphafold/fold-verify",
                amount_atomic="1000000",
            )
            res = gw.verify_and_consume_receipt(
                receipt_id="rcpt-1001",
                tx_hash=tx_hash,
                payer_address=payer,
                resource_path="/api/x402/alphafold/fold-verify",
                amount_atomic="1000000",
                required_amount_atomic="1000000",
                signature=sig,
            )
            self.assertEqual(res["status"], "SETTLED")

            # Replay attempt must fail closed
            with self.assertRaises(PermissionError):
                gw.verify_and_consume_receipt(
                    receipt_id="rcpt-1001",
                    tx_hash=tx_hash,
                    payer_address=payer,
                    resource_path="/api/x402/alphafold/fold-verify",
                    amount_atomic="1000000",
                    required_amount_atomic="1000000",
                    signature=sig,
                )

    def test_06_pqc_hybrid_envelope_verification(self) -> None:
        payload = b"Arbitrum-AlphaFold-AlphaTensor-Attestation-2026"
        seed = b"0123456789abcdef0123456789abcdef"
        env = PqcAttestationVerifier.create_hybrid_envelope("ML-DSA-65", payload, seed)
        self.assertTrue(PqcAttestationVerifier.verify_hybrid_envelope(env, payload))
        self.assertFalse(PqcAttestationVerifier.verify_hybrid_envelope(env, b"Tampered-Payload"))

    def test_07_raven_rsi_and_rea_governance(self) -> None:
        report = ReaCodeInspector.inspect_python_file(ROOT / "src/qarbi_engine/conway_engine.py")
        self.assertIn("ConwayAutomatonEngine", report.classes)
        self.assertEqual(len(report.unsafe_calls), 0)

        gov = RavenRsiGovernor()
        blocked = gov.evaluate_proposal(
            experiment_id="exp-01",
            hypothesis="Bypass CodeQL for faster build",
            proposed_action="DISABLE_CODEQL",
            baseline_score=80.0,
            candidate_score=90.0,
            tests_passed=True,
        )
        self.assertFalse(blocked.accepted)

        accepted = gov.evaluate_proposal(
            experiment_id="exp-02",
            hypothesis="Optimize AlphaTensor verification loop",
            proposed_action="OPTIMIZE_TENSOR_VERIFIER",
            baseline_score=85.0,
            candidate_score=91.5,
            tests_passed=True,
            human_approved=True,
        )
        self.assertTrue(accepted.accepted)

    def test_08_governed_uncapped_tokenomics(self) -> None:
        tok = GovernedTokenomicsEngine(initial_supply=100_000_000, annual_emission_bps=500)  # 5% annual cap = 5,000,000
        self.assertEqual(tok.annual_emission_limit(), 5_000_000)
        res1 = tok.execute_governed_mint(3_000_000, authorized_minter=True)
        self.assertEqual(res1.approved_mint, 3_000_000)
        # Second request exceeds remaining 2,000,000 epoch allowance -> capped by M(t) = min(R(t), limit)
        res2 = tok.execute_governed_mint(4_500_000, authorized_minter=True)
        self.assertEqual(res2.approved_mint, 2_000_000)
        with self.assertRaises(PermissionError):
            tok.execute_governed_mint(100, authorized_minter=False)

    def test_09_arbitrum_wallet_qr_and_cross_chain_guard(self) -> None:
        qr = ArbitrumWalletQrService.generate_eip681_payment_qr(
            recipient="0x3333333333333333333333333333333333333333",
            chain_id=42161,
            amount_wei=10**18,
        )
        self.assertIn("@42161", qr.uri)
        self.assertTrue(qr.svg_preview.startswith("<svg"))
        with self.assertRaises(ValueError):
            ArbitrumWalletQrService.validate_arbitrum_address("solana:7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV")


if __name__ == "__main__":
    unittest.main()
