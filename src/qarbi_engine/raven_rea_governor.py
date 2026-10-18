"""
Chapter 9 & 10 — Raven RSI Loop, REA Static/Runtime Inspector & Multimodel AI Agentics
Integrates governed recursive self-improvement (EverMind-AI/Raven pattern) and
REA (morluto/rea) AST/interface inspection under strict human-approval boundaries.
"""

from __future__ import annotations
import ast
import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


FORBIDDEN_AUTONOMOUS_ACTIONS = {
    "DISABLE_CODEQL",
    "MINT_MAINNET_TOKENS",
    "TRANSFER_TREASURY_FUNDS",
    "EXPOSE_PRIVATE_KEYS",
    "BYPASS_BRANCH_PROTECTION",
    "DEPLOY_MAINNET_UNAPPROVED",
}


@dataclass
class ReaInspectionReport:
    file_path: str
    sha256: str
    classes: List[str]
    functions: List[str]
    imports: List[str]
    unsafe_calls: List[str]


@dataclass
class RavenExperimentRecord:
    experiment_id: str
    stage: str
    hypothesis: str
    proposed_action: str
    baseline_score: float
    candidate_score: float
    human_approved: bool
    accepted: bool
    rejection_reason: str = ""


class ReaCodeInspector:
    """Deterministic Python AST & interface inspector following REA reverse-engineering principles."""

    UNSAFE_IDENTIFIERS = {"eval", "exec", "os.system", "pickle.loads"}

    @classmethod
    def inspect_python_file(cls, file_path: str | Path) -> ReaInspectionReport:
        p = Path(file_path)
        source = p.read_text(encoding="utf-8")
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        tree = ast.parse(source, filename=str(p))

        classes: List[str] = []
        functions: List[str] = []
        imports: List[str] = []
        unsafe_calls: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in cls.UNSAFE_IDENTIFIERS:
                    unsafe_calls.append(node.func.id)

        return ReaInspectionReport(
            file_path=str(p),
            sha256=digest,
            classes=sorted(classes),
            functions=sorted(functions),
            imports=sorted(set(imports)),
            unsafe_calls=unsafe_calls,
        )


class RavenRsiGovernor:
    """
    Enforces the governed RSI loop:
    OBSERVE -> DIAGNOSE -> PROPOSE -> PATCH -> TEST -> REVIEW -> APPROVE -> DEPLOY -> MONITOR
    Blocks forbidden autonomous modifications and regressions.
    """

    VALID_STAGES = (
        "OBSERVE",
        "DIAGNOSE",
        "PROPOSE",
        "PATCH",
        "TEST",
        "REVIEW",
        "APPROVE",
        "DEPLOY",
        "MONITOR",
    )

    def __init__(self) -> None:
        self.ledger: List[RavenExperimentRecord] = []

    def evaluate_proposal(
        self,
        experiment_id: str,
        hypothesis: str,
        proposed_action: str,
        baseline_score: float,
        candidate_score: float,
        tests_passed: bool,
        human_approved: bool = False,
    ) -> RavenExperimentRecord:
        if proposed_action in FORBIDDEN_AUTONOMOUS_ACTIONS:
            rec = RavenExperimentRecord(
                experiment_id=experiment_id,
                stage="REVIEW",
                hypothesis=hypothesis,
                proposed_action=proposed_action,
                baseline_score=baseline_score,
                candidate_score=candidate_score,
                human_approved=human_approved,
                accepted=False,
                rejection_reason=f"Blocked by safety policy: {proposed_action} is forbidden.",
            )
            self.ledger.append(rec)
            return rec

        if not tests_passed:
            rec = RavenExperimentRecord(
                experiment_id=experiment_id,
                stage="TEST",
                hypothesis=hypothesis,
                proposed_action=proposed_action,
                baseline_score=baseline_score,
                candidate_score=candidate_score,
                human_approved=human_approved,
                accepted=False,
                rejection_reason="Candidate patch failed sandboxed test verification.",
            )
            self.ledger.append(rec)
            return rec

        if candidate_score < baseline_score:
            rec = RavenExperimentRecord(
                experiment_id=experiment_id,
                stage="REVIEW",
                hypothesis=hypothesis,
                proposed_action=proposed_action,
                baseline_score=baseline_score,
                candidate_score=candidate_score,
                human_approved=human_approved,
                accepted=False,
                rejection_reason="Candidate regressed benchmark score relative to baseline.",
            )
            self.ledger.append(rec)
            return rec

        rec = RavenExperimentRecord(
            experiment_id=experiment_id,
            stage="APPROVE" if human_approved else "REVIEW",
            hypothesis=hypothesis,
            proposed_action=proposed_action,
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            human_approved=human_approved,
            accepted=True,
            rejection_reason="",
        )
        self.ledger.append(rec)
        return rec
