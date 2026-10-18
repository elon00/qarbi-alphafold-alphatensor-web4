// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title AlphaComputeRegistry
 * @notice Verifiable Arbitrum registry for open-source AlphaFold protein structure
 *         predictions and AlphaTensor matrix-multiplication tensor decompositions.
 */
contract AlphaComputeRegistry is AccessControl, ReentrancyGuard {
    bytes32 public constant VERIFIER_ROLE = keccak256("VERIFIER_ROLE");

    struct AlphaFoldAttestation {
        bytes32 sequenceHash;      // SHA-256 of FASTA sequence
        bytes32 structureHash;     // SHA-256 of mmCIF/PDB coordinate file
        bytes32 pqcSignatureHash;  // SHA-256 of off-chain ML-DSA-65 / SLH-DSA signature envelope
        uint16 meanPlddtScaled;    // Mean pLDDT * 100 (e.g., 9425 = 94.25)
        address researcher;
        uint64 timestamp;
        bool verified;
    }

    struct AlphaTensorAttestation {
        bytes32 tensorSpecHash;    // SHA-256 of matrix dimensions (m, k, n) and target tensor T
        bytes32 factorHash;        // SHA-256 of (U, V, W) factor matrices
        uint16 discoveredRank;     // Number of scalar multiplications R
        uint16 baselineRank;       // Standard or prior known rank
        address researcher;
        uint64 timestamp;
        bool verified;
    }

    mapping(bytes32 => AlphaFoldAttestation) public alphafoldRecords;
    mapping(bytes32 => AlphaTensorAttestation) public alphatensorRecords;

    event AlphaFoldSubmitted(bytes32 indexed attestationId, address indexed researcher, uint16 meanPlddtScaled);
    event AlphaTensorSubmitted(bytes32 indexed attestationId, address indexed researcher, uint16 discoveredRank);

    error DuplicateAttestation(bytes32 attestationId);
    error InvalidConfidenceScore(uint16 score);
    error InvalidRankImprovement(uint16 discoveredRank, uint16 baselineRank);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(VERIFIER_ROLE, admin);
    }

    function registerAlphaFoldStructure(
        bytes32 attestationId,
        bytes32 sequenceHash,
        bytes32 structureHash,
        bytes32 pqcSignatureHash,
        uint16 meanPlddtScaled
    ) external nonReentrant {
        if (alphafoldRecords[attestationId].timestamp != 0) {
            revert DuplicateAttestation(attestationId);
        }
        if (meanPlddtScaled > 10000) {
            revert InvalidConfidenceScore(meanPlddtScaled);
        }
        alphafoldRecords[attestationId] = AlphaFoldAttestation({
            sequenceHash: sequenceHash,
            structureHash: structureHash,
            pqcSignatureHash: pqcSignatureHash,
            meanPlddtScaled: meanPlddtScaled,
            researcher: msg.sender,
            timestamp: uint64(block.timestamp),
            verified: hasRole(VERIFIER_ROLE, msg.sender)
        });
        emit AlphaFoldSubmitted(attestationId, msg.sender, meanPlddtScaled);
    }

    function registerAlphaTensorDecomposition(
        bytes32 attestationId,
        bytes32 tensorSpecHash,
        bytes32 factorHash,
        uint16 discoveredRank,
        uint16 baselineRank
    ) external nonReentrant {
        if (alphatensorRecords[attestationId].timestamp != 0) {
            revert DuplicateAttestation(attestationId);
        }
        if (discoveredRank == 0 || discoveredRank > baselineRank) {
            revert InvalidRankImprovement(discoveredRank, baselineRank);
        }
        alphatensorRecords[attestationId] = AlphaTensorAttestation({
            tensorSpecHash: tensorSpecHash,
            factorHash: factorHash,
            discoveredRank: discoveredRank,
            baselineRank: baselineRank,
            researcher: msg.sender,
            timestamp: uint64(block.timestamp),
            verified: hasRole(VERIFIER_ROLE, msg.sender)
        });
        emit AlphaTensorSubmitted(attestationId, msg.sender, discoveredRank);
    }
}
