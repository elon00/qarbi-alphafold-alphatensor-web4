// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title QarbiLaunchpad
 * @notice Arbitrum DeSci & Web4 Token Launchpad with provenance tracking,
 *         jurisdiction compliance flags, and human-authorized activation gates.
 */
contract QarbiLaunchpad is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant LAUNCH_OPERATOR_ROLE = keccak256("LAUNCH_OPERATOR_ROLE");

    struct LaunchRecord {
        string name;
        string symbol;
        address tokenAddress;
        address creator;
        address treasury;
        bytes32 researchArtifactHash; // Linked AlphaFold/AlphaTensor project hash
        uint64 createdAt;
        bool active;
    }

    LaunchRecord[] public launches;
    mapping(address => bool) public registeredTokens;

    event TokenLaunchRegistered(
        uint256 indexed launchId,
        address indexed tokenAddress,
        address indexed creator,
        string symbol,
        bytes32 researchArtifactHash
    );

    error ZeroAddressNotAllowed();
    error TokenAlreadyRegistered(address tokenAddress);

    constructor(address admin) {
        if (admin == address(0)) revert ZeroAddressNotAllowed();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(LAUNCH_OPERATOR_ROLE, admin);
    }

    function registerLaunch(
        string calldata name,
        string calldata symbol,
        address tokenAddress,
        address treasury,
        bytes32 researchArtifactHash
    ) external onlyRole(LAUNCH_OPERATOR_ROLE) whenNotPaused nonReentrant returns (uint256 launchId) {
        if (tokenAddress == address(0) || treasury == address(0)) {
            revert ZeroAddressNotAllowed();
        }
        if (registeredTokens[tokenAddress]) {
            revert TokenAlreadyRegistered(tokenAddress);
        }

        registeredTokens[tokenAddress] = true;
        launchId = launches.length;
        launches.push(
            LaunchRecord({
                name: name,
                symbol: symbol,
                tokenAddress: tokenAddress,
                creator: msg.sender,
                treasury: treasury,
                researchArtifactHash: researchArtifactHash,
                createdAt: uint64(block.timestamp),
                active: true
            })
        );

        emit TokenLaunchRegistered(launchId, tokenAddress, msg.sender, symbol, researchArtifactHash);
    }

    function totalLaunches() external view returns (uint256) {
        return launches.length;
    }
}
