// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title QarbiToken ($QARBI)
 * @notice Arbitrum Layer-2 Web4 token with governed uncapped lifetime supply and
 *         strict annual emission rate ceilings:
 *         M(t) = min(R(t), annual_emission_limit(t))
 * @dev Designed for OpenZeppelin v5 on Arbitrum One (42161) and Arbitrum Sepolia (421614).
 */
contract QarbiToken is ERC20, ERC20Burnable, Pausable, AccessControl, ERC20Permit, ERC20Votes {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant POLICY_GOVERNOR_ROLE = keccak256("POLICY_GOVERNOR_ROLE");

    uint256 public constant EPOCH_DURATION = 365 days;
    uint256 public constant MAX_ANNUAL_EMISSION_BPS = 1000; // 10.00% max annual emission cap

    uint256 public currentEpochStart;
    uint256 public currentEpochStartSupply;
    uint256 public currentEpochMinted;
    uint256 public annualEmissionBps;

    event EpochEmissionMinted(address indexed to, uint256 amount, uint256 epochMintedTotal, uint256 epochCeiling);
    event AnnualEmissionBpsUpdated(uint256 previousBps, uint256 newBps);

    error EmissionCeilingExceeded(uint256 requested, uint256 remainingAllowed);
    error InvalidEmissionBps(uint256 providedBps, uint256 maxBps);
    error ZeroAddressDisallowed();

    constructor(
        address defaultAdmin,
        address initialTreasury,
        uint256 initialSupply,
        uint256 initialAnnualEmissionBps
    )
        ERC20("QARBI AlphaFold AlphaTensor Web4 Token", "QARBI")
        ERC20Permit("QARBI AlphaFold AlphaTensor Web4 Token")
    {
        if (defaultAdmin == address(0) || initialTreasury == address(0)) {
            revert ZeroAddressDisallowed();
        }
        if (initialAnnualEmissionBps > MAX_ANNUAL_EMISSION_BPS) {
            revert InvalidEmissionBps(initialAnnualEmissionBps, MAX_ANNUAL_EMISSION_BPS);
        }

        _grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
        _grantRole(MINTER_ROLE, defaultAdmin);
        _grantRole(PAUSER_ROLE, defaultAdmin);
        _grantRole(POLICY_GOVERNOR_ROLE, defaultAdmin);

        currentEpochStart = block.timestamp;
        annualEmissionBps = initialAnnualEmissionBps;

        if (initialSupply > 0) {
            _mint(initialTreasury, initialSupply);
        }
        currentEpochStartSupply = totalSupply();
    }

    /**
     * @notice Computes the maximum allowed emission for the active 365-day epoch.
     */
    function currentEpochEmissionLimit() public view returns (uint256) {
        return (currentEpochStartSupply * annualEmissionBps) / 10_000;
    }

    /**
     * @notice Mints new tokens strictly within the governed annual emission ceiling:
     *         M(t) = min(R(t), annual_emission_limit(t))
     */
    function mintGoverned(address to, uint256 requestedAmount) external onlyRole(MINTER_ROLE) whenNotPaused {
        if (to == address(0)) revert ZeroAddressDisallowed();
        if (block.timestamp >= currentEpochStart + EPOCH_DURATION) {
            currentEpochStart = block.timestamp;
            currentEpochStartSupply = totalSupply();
            currentEpochMinted = 0;
        }

        uint256 ceiling = currentEpochEmissionLimit();
        uint256 remaining = ceiling > currentEpochMinted ? (ceiling - currentEpochMinted) : 0;
        if (requestedAmount > remaining) {
            revert EmissionCeilingExceeded(requestedAmount, remaining);
        }

        currentEpochMinted += requestedAmount;
        _mint(to, requestedAmount);
        emit EpochEmissionMinted(to, requestedAmount, currentEpochMinted, ceiling);
    }

    function setAnnualEmissionBps(uint256 newBps) external onlyRole(POLICY_GOVERNOR_ROLE) {
        if (newBps > MAX_ANNUAL_EMISSION_BPS) {
            revert InvalidEmissionBps(newBps, MAX_ANNUAL_EMISSION_BPS);
        }
        uint256 old = annualEmissionBps;
        annualEmissionBps = newBps;
        emit AnnualEmissionBpsUpdated(old, newBps);
    }

    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    function _update(address from, address to, uint256 value)
        internal
        override(ERC20, ERC20Votes)
        whenNotPaused
    {
        super._update(from, to, value);
    }

    function nonces(address owner)
        public
        view
        override(ERC20Permit, Nonces)
        returns (uint256)
    {
        return super.nonces(owner);
    }
}
