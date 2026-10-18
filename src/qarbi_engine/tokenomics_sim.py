"""
Chapter 11 & 12 — Governed Uncapped Tokenomics & Arbitrum Launchpad Policy Engine
Implements M(t) = min(R(t), annual_emission_limit(t)) with role & cap enforcement.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class EmissionResult:
    requested: int
    approved_mint: int
    annual_limit: int
    new_total_supply: int
    epoch_minted_total: int


class GovernedTokenomicsEngine:
    """
    Models the exact mathematical behavior of `QarbiToken.sol` on Arbitrum:
    Uncapped lifetime supply with a strict per-epoch emission ceiling.
    """

    MAX_ANNUAL_EMISSION_BPS = 1000  # 10.00%

    def __init__(self, initial_supply: int, annual_emission_bps: int = 500):
        if initial_supply <= 0:
            raise ValueError("Initial supply must be positive.")
        if not (0 <= annual_emission_bps <= self.MAX_ANNUAL_EMISSION_BPS):
            raise ValueError(f"annual_emission_bps must be between 0 and {self.MAX_ANNUAL_EMISSION_BPS}")
        self.epoch_start_supply = initial_supply
        self.total_supply = initial_supply
        self.annual_emission_bps = annual_emission_bps
        self.epoch_minted = 0

    def annual_emission_limit(self) -> int:
        return (self.epoch_start_supply * self.annual_emission_bps) // 10_000

    def execute_governed_mint(self, requested_amount: int, authorized_minter: bool = True) -> EmissionResult:
        if not authorized_minter:
            raise PermissionError("Unauthorized minter role.")
        if requested_amount < 0:
            raise ValueError("Requested mint amount cannot be negative.")

        limit = self.annual_emission_limit()
        remaining = max(0, limit - self.epoch_minted)
        # M(t) = min(R(t), remaining_annual_emission_limit(t))
        minted = min(requested_amount, remaining)
        self.epoch_minted += minted
        self.total_supply += minted
        return EmissionResult(
            requested=requested_amount,
            approved_mint=minted,
            annual_limit=limit,
            new_total_supply=self.total_supply,
            epoch_minted_total=self.epoch_minted,
        )
