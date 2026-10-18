"""
AlphaFold & AlphaTensor Verifiable Scientific Compute Engine for Arbitrum DeSci
- AlphaTensor: Verifies low-rank bilinear tensor decompositions (U, V, W) for matrix multiplication
  in both real arithmetic (R) and modular binary arithmetic (Z_2), matching Google DeepMind's
  AlphaTensor framework (https://github.com/google-deepmind/alphatensor).
- AlphaFold: Parses PDB ATOM coordinates, computes pairwise C-alpha contact maps / distograms,
  extracts per-residue pLDDT confidence scores (stored in the B-factor column of AlphaFold PDBs),
  and produces deterministic SHA-256 attestations ready for Arbitrum `AlphaComputeRegistry.sol`.
"""

from __future__ import annotations
import hashlib
import json
import math
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class TensorDecompositionProof:
    matrix_dims: Tuple[int, int, int]  # (m, k, n) for A(m x k) * B(k x n) = C(m x n)
    discovered_rank: int
    baseline_rank: int
    exact_over_reals: bool
    exact_over_z2: bool
    tensor_spec_hash: str
    factor_hash: str


class AlphaTensorVerifier:
    """
    Verifies bilinear tensor decompositions (U, V, W) of shape:
      U: (m*k, R), V: (k*n, R), W: (m*n, R)
    such that for any A (m x k) and B (k x n),
      vec(A @ B)_i = sum_{r=1..R} W_{i, r} * (sum_p U_{p, r} vec(A)_p) * (sum_q V_{q, r} vec(B)_q)
    """

    @staticmethod
    def build_strassen_2x2_factors() -> Tuple[List[List[int]], List[List[int]], List[List[int]]]:
        """
        Returns the classic rank-7 2x2 matrix multiplication tensor factors (U, V, W)
        rediscovered and generalized by AlphaTensor (baseline naive rank = 8).
        Index flattening for 2x2 matrix M: [M_00, M_01, M_10, M_11]
        """
        # 7 scalar products m_0 .. m_6:
        # m0 = (A00 + A11)(B00 + B11)
        # m1 = (A10 + A11)B00
        # m2 = A00(B01 - B11)
        # m3 = A11(B10 - B00)
        # m4 = (A00 + A01)B11
        # m5 = (A10 - A00)(B00 + B01)
        # m6 = (A01 - A11)(B10 + B11)
        U = [
            [1, 0, 1, 0, 1, -1, 0],  # A00
            [0, 0, 0, 0, 1, 0, 1],   # A01
            [0, 1, 0, 0, 0, 1, 0],   # A10
            [1, 1, 0, 1, 0, 0, -1],  # A11
        ]
        V = [
            [1, 1, 0, -1, 0, 1, 0],  # B00
            [0, 0, 1, 0, 0, 1, 0],   # B01
            [0, 0, 0, 1, 0, 0, 1],   # B10
            [1, 0, -1, 0, 1, 0, 1],  # B11
        ]
        # C00 = m0 + m3 - m4 + m6
        # C01 = m2 + m4
        # C10 = m1 + m3
        # C11 = m0 - m1 + m2 + m5
        W = [
            [1, 0, 0, 1, -1, 0, 1],  # C00
            [0, 0, 1, 0, 1, 0, 0],   # C01
            [0, 1, 0, 1, 0, 0, 0],   # C10
            [1, -1, 1, 0, 0, 1, 0],  # C11
        ]
        return U, V, W

    @staticmethod
    def verify_decomposition(
        m: int,
        k: int,
        n: int,
        U: List[List[int]],
        V: List[List[int]],
        W: List[List[int]],
    ) -> TensorDecompositionProof:
        if len(U) != m * k or len(V) != k * n or len(W) != m * n:
            raise ValueError("Factor matrix row counts do not match (m*k, k*n, m*n).")
        rank = len(U[0])
        if any(len(row) != rank for row in U + V + W):
            raise ValueError("Inconsistent rank dimension across U, V, W.")

        exact_reals = True
        exact_z2 = True

        for a_row in range(m):
            for a_col in range(k):
                p = a_row * k + a_col
                for b_row in range(k):
                    for b_col in range(n):
                        q = b_row * n + b_col
                        for c_row in range(m):
                            for c_col in range(n):
                                idx_c = c_row * n + c_col
                                expected = 1 if (a_row == c_row and a_col == b_row and b_col == c_col) else 0
                                reconstructed = sum(U[p][r] * V[q][r] * W[idx_c][r] for r in range(rank))
                                if reconstructed != expected:
                                    exact_reals = False
                                if (reconstructed % 2) != (expected % 2):
                                    exact_z2 = False

        spec_hash = "0x" + hashlib.sha256(f"alphatensor:{m}:{k}:{n}".encode("utf-8")).hexdigest()
        factor_payload = json.dumps({"U": U, "V": V, "W": W}, separators=(",", ":")).encode("utf-8")
        factor_hash = "0x" + hashlib.sha256(factor_payload).hexdigest()

        return TensorDecompositionProof(
            matrix_dims=(m, k, n),
            discovered_rank=rank,
            baseline_rank=m * k * n,
            exact_over_reals=exact_reals,
            exact_over_z2=exact_z2,
            tensor_spec_hash=spec_hash,
            factor_hash=factor_hash,
        )


@dataclass
class AlphaFoldStructureProof:
    sequence: str
    residue_count: int
    mean_plddt: float
    mean_plddt_scaled: int
    contact_pairs_under_8a: int
    sequence_hash: str
    structure_hash: str


class AlphaFoldStructureVerifier:
    """
    Parses AlphaFold PDB output lines (ATOM records for C-alpha backbone atoms),
    verifies pLDDT confidence scores (encoded in the PDB B-factor column per DeepMind spec),
    computes the C-alpha pairwise distance contact map (< 8.0 Angstroms),
    and produces deterministic hashes for Arbitrum on-chain registration.
    """

    AA3_TO_1 = {
        "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
        "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
        "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
        "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
    }

    @classmethod
    def verify_pdb_ca_trace(cls, pdb_text: str) -> AlphaFoldStructureProof:
        ca_atoms: List[Tuple[str, int, float, float, float, float]] = []
        for raw_line in pdb_text.splitlines():
            line = raw_line.strip()
            if not line.startswith("ATOM"):
                continue
            parts = line.split()
            # Standard PDB columns or whitespace-delimited ATOM record:
            # ATOM <serial> CA <resName> <chain> <resSeq> <x> <y> <z> <occupancy> <bFactor/pLDDT>
            if len(parts) >= 11 and parts[2] == "CA":
                res_name = parts[3].upper()
                res_seq = int(parts[5])
                x, y, z = float(parts[6]), float(parts[7]), float(parts[8])
                plddt = float(parts[10])
                if not (0.0 <= plddt <= 100.0):
                    raise ValueError(f"Invalid AlphaFold pLDDT value {plddt} at residue {res_seq}")
                ca_atoms.append((cls.AA3_TO_1.get(res_name, "X"), res_seq, x, y, z, plddt))

        if not ca_atoms:
            raise ValueError("No C-alpha (CA) ATOM records found in PDB input.")

        sequence = "".join(item[0] for item in ca_atoms)
        mean_plddt = sum(item[5] for item in ca_atoms) / len(ca_atoms)
        mean_plddt_scaled = int(round(mean_plddt * 100))

        contacts = 0
        for i in range(len(ca_atoms)):
            for j in range(i + 1, len(ca_atoms)):
                dx = ca_atoms[i][2] - ca_atoms[j][2]
                dy = ca_atoms[i][3] - ca_atoms[j][3]
                dz = ca_atoms[i][4] - ca_atoms[j][4]
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                if dist < 8.0:
                    contacts += 1

        seq_hash = "0x" + hashlib.sha256(sequence.encode("utf-8")).hexdigest()
        struct_hash = "0x" + hashlib.sha256(pdb_text.strip().encode("utf-8")).hexdigest()

        return AlphaFoldStructureProof(
            sequence=sequence,
            residue_count=len(ca_atoms),
            mean_plddt=round(mean_plddt, 2),
            mean_plddt_scaled=mean_plddt_scaled,
            contact_pairs_under_8a=contacts,
            sequence_hash=seq_hash,
            structure_hash=struct_hash,
        )
