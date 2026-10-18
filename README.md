# QARBI: Arbitrum Web4 Decentralized AlphaFold & AlphaTensor Compute & DeSci Protocol

**Repository Target:** `https://github.com/elon00/qarbi-alphafold-alphatensor-web4`  
**Primary L2 Network:** [Arbitrum One](https://arbiscan.io/) (Chain ID `42161`) & [Arbitrum Sepolia Testnet](https://sepolia.arbiscan.io/) (Chain ID `421614`)  
**Core Scientific Engines:** [Google DeepMind AlphaFold 2](https://github.com/google-deepmind/alphafold), [AlphaFold 3](https://github.com/google-deepmind/alphafold3), [AlphaTensor](https://github.com/google-deepmind/alphatensor), and [AlphaTensor-Quantum](https://github.com/google-deepmind/alphatensor_quantum)

## Overview

QARBI (`elon00/qarbi-alphafold-alphatensor-web4`) is an Arbitrum Layer-2 decentralized Web 4.0 scientific compute, algorithmic discovery, and cryptocurrency protocol under the QMOOSA engineering standard. It unifies verifiable protein folding ([AlphaFold](https://github.com/google-deepmind/alphafold)) and low-rank bilinear tensor decomposition ([AlphaTensor](https://github.com/google-deepmind/alphatensor)) with:

1. **Arbitrum Rollup Smart Contracts (Solidity 0.8.24 / OpenZeppelin v5):**
   - `QarbiToken.sol`: Governed uncapped-supply ERC-20 token (`$QARBI`) enforcing strict epoch emission ceilings (`M(t) = min(R(t), annual_emission_limit(t))`), role-based access control, ERC20Votes governance, and emergency pause gates.
   - `QarbiLaunchpad.sol`: Deterministic Arbitrum token & DeSci compute-pool launchpad with vesting schedules, treasury split enforcement, and on-chain provenance registry.
   - `AlphaComputeRegistry.sol`: On-chain commitment and bounty settlement registry for verified AlphaTensor tensor factorizations (`U, V, W` rank reductions) and AlphaFold structure attestations (PDB/mmCIF SHA-256 + pLDDT & PAE confidence bounds).
2. **QuickNode Arbitrum RPC & Streams Adapter (`src/qarbi_engine/arbitrum_rpc.py`):**
   - Circuit-breaker, retry-aware, chain-ID-verifying RPC client supporting Arbitrum One (`42161`) and Arbitrum Sepolia (`421614`) via [QuickNode Arbitrum Endpoints](https://www.quicknode.com/docs/arbitrum).
3. **x402 Bazaar Payment & Settlement Engine (`src/qarbi_engine/x402_bazaar.py`):**
   - Full [x402 Protocol](https://x402.org/) (`HTTP 402 Payment Required`) negotiation, Bazaar discovery metadata, and ACID SQLite order-bound receipt store preventing replay attacks across restarts.
4. **Conway B3/S23 Cellular Automaton Engine (`src/qarbi_engine/conway_engine.py`):**
   - Deterministic [B3/S23](https://conwaylife.com/wiki/Conway%27s_Game_of_Life) grid evolution, SHA-256 state hashing, checkpoint/rollback snapshots, and still-life/oscillator/glider invariants.
5. **AlphaFold & AlphaTensor Verifiable Scientific Compute Engine (`src/qarbi_engine/alpha_science.py`):**
   - Exact bilinear tensor decomposition verifier (`[[u, v, w]]` exact matrix multiplication reconstruction over $\mathbb{R}$ and $\mathbb{Z}_2$, verifying Strassen/AlphaTensor rank-7 $2\times2$ and custom tensor factorizations) + AlphaFold PDB/mmCIF coordinate parser, distogram/contact-map generator, and pLDDT confidence verifier.
6. **Post-Quantum Cryptography Envelope (`src/qarbi_engine/pqc_envelope.py`):**
   - [NIST PQC](https://csrc.nist.gov/projects/post-quantum-cryptography) domain-separated commitment and hybrid key/signature envelope structure aligned with FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), and FIPS 205 (SLH-DSA), explicitly distinguishing off-chain PQC verification from Arbitrum EVM `secp256k1` precompiles.
7. **Raven RSI & REA Governance Subsystem (`src/qarbi_engine/raven_rea_governor.py`):**
   - Governed recursive self-improvement pipeline (`OBSERVE -> DIAGNOSE -> PROPOSE -> PATCH -> TEST -> REVIEW -> APPROVE -> DEPLOY -> MONITOR`) modeled for [EverMind-AI/Raven](https://github.com/EverMind-AI/Raven) and [morluto/rea](https://github.com/morluto/rea) binary/AST inspection, enforcing immutable human-approval gates for mainnet & treasury actions.
8. **Multiwallet & EIP-681 Arbitrum QR Payment Generator (`src/qarbi_engine/wallet_qr.py`):**
   - Strict Arbitrum address checksum verification (EIP-55), cross-chain confusion guard, and EIP-681 payment URI + SVG/ASCII QR payload generator.
9. **Fail-Closed Reality Gate (`scripts/reality_gate.py`):**
   - Executes unit, smoke, sanity, and regression suites, inspects secrets and CI gates, and writes verifiable `reports/FINAL_SCORECARD.json` and `reports/FINAL_SCORECARD.md` without fabricating mainnet deployment claims.

## Quickstart

```bash
# 1. Run the complete unit, smoke, sanity, and regression test suite
python3 -m unittest discover -s tests -p "test_*.py" -v

# 2. Run the fail-closed Reality Gate & generate reports/FINAL_SCORECARD.md
python3 scripts/reality_gate.py
```
