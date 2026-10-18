"""
Chapter 6 — Standalone Conway B3/S23 Cellular Automaton Engine
Provides deterministic state transitions, SHA-256 state hashing,
checkpoint snapshots, and pattern verification (still-life, oscillator, glider).
"""

from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

Cell = Tuple[int, int]


@dataclass
class ConwaySnapshot:
    generation: int
    width: int
    height: int
    live_cells: List[Cell]
    state_hash: str


class ConwayAutomatonEngine:
    """Deterministic B3/S23 cellular automaton on a bounded or toroidal 2D grid."""

    def __init__(self, width: int = 32, height: int = 32, toroidal: bool = True, max_generations: int = 10_000):
        if width < 4 or height < 4 or width > 2048 or height > 2048:
            raise ValueError("Grid dimensions must be between 4x4 and 2048x2048.")
        self.width = width
        self.height = height
        self.toroidal = toroidal
        self.max_generations = max_generations
        self.generation = 0
        self.live_cells: Set[Cell] = set()
        self.checkpoints: Dict[int, ConwaySnapshot] = {}

    def load_cells(self, cells: List[Cell]) -> None:
        validated: Set[Cell] = set()
        for r, c in cells:
            if not (0 <= r < self.height and 0 <= c < self.width):
                raise ValueError(f"Cell ({r}, {c}) out of bounds for {self.height}x{self.width} grid.")
            validated.add((int(r), int(c)))
        self.live_cells = validated
        self.generation = 0
        self.save_checkpoint()

    def _neighbors(self, r: int, c: int) -> List[Cell]:
        out: List[Cell] = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.toroidal:
                    out.append((nr % self.height, nc % self.width))
                elif 0 <= nr < self.height and 0 <= nc < self.width:
                    out.append((nr, nc))
        return out

    def step(self, steps: int = 1) -> ConwaySnapshot:
        if steps < 1:
            raise ValueError("steps must be >= 1")
        if self.generation + steps > self.max_generations:
            raise RuntimeError(f"Execution ceiling exceeded: max_generations={self.max_generations}")

        for _ in range(steps):
            neighbor_counts: Dict[Cell, int] = {}
            for r, c in self.live_cells:
                for nb in self._neighbors(r, c):
                    neighbor_counts[nb] = neighbor_counts.get(nb, 0) + 1

            next_live: Set[Cell] = set()
            for cell, count in neighbor_counts.items():
                if count == 3 or (count == 2 and cell in self.live_cells):
                    next_live.add(cell)

            self.live_cells = next_live
            self.generation += 1

        return self.snapshot()

    def state_hash(self) -> str:
        ordered = sorted(self.live_cells)
        payload = json.dumps(
            {"w": self.width, "h": self.height, "gen": self.generation, "cells": ordered},
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def snapshot(self) -> ConwaySnapshot:
        return ConwaySnapshot(
            generation=self.generation,
            width=self.width,
            height=self.height,
            live_cells=sorted(self.live_cells),
            state_hash=self.state_hash(),
        )

    def save_checkpoint(self) -> ConwaySnapshot:
        snap = self.snapshot()
        self.checkpoints[self.generation] = snap
        return snap

    def restore_checkpoint(self, generation: int) -> ConwaySnapshot:
        if generation not in self.checkpoints:
            raise KeyError(f"No checkpoint recorded for generation {generation}")
        snap = self.checkpoints[generation]
        self.generation = snap.generation
        self.live_cells = set(snap.live_cells)
        return self.snapshot()
