from __future__ import annotations

from typing import Any

from src.agent.contracts import (
    AgentAction,
    AgentInvestigation,
)


def _human_amount(value: Any) -> str:
    if value is None:
        return "not available"

    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def investigate_case(
    case_id: str,
    action: AgentAction,
    severity: str,
    reason: str,
    evidence: dict[str, Any],
) -> AgentInvestigation:
    if not case_id:
        raise ValueError(
            "case_id cannot be empty."
        )

    if not isinstance(evidence, dict):
        raise TypeError(
            "evidence must be a dictionary."
        )

    normalized_severity = str(
        severity
    ).upper()

    failed_stage = evidence.get(
        "failed_stage"
    )

    failure_direction = evidence.get(
        "failure_direction"
    )

    discrepancy_type = evidence.get(
        "discrepancy_type"
    )

    if failed_stage:
        stage_text = str(
            failed_stage
        ).replace("_", " ")
    else:
        stage_text = (
            "No failure; all required controls passed."
        )

    location_text = (
        str(failure_direction)
        if failure_direction
        else "No failed comparison identified."
    )

    amount_sentence = ""

    if (
        "expected_amount" in evidence
        or "observed_amount" in evidence
    ):
        amount_sentence = (
            f" Expected "
            f"{_human_amount(evidence.get('expected_amount'))};"
            f" observed "
            f"{_human_amount(evidence.get('observed_amount'))};"
            f" difference "
            f"{_human_amount(evidence.get('difference', 0))}."
        )

    discrepancy_sentence = (
        f" Exception type: {discrepancy_type}."
        if discrepancy_type
        else ""
    )

    detailed_explanation = (
        f"{reason} "
        f"The first detected failure occurred at "
        f"{location_text}. "
        f"Control stage: {stage_text}."
        f"{amount_sentence}"
        f"{discrepancy_sentence}"
    )

    evidence_copy = dict(evidence)

    if action == AgentAction.BLOCKED:
        return AgentInvestigation(
            case_id=case_id,
            finding=(
                "Critical financial control condition "
                "requires the case to be blocked."
            ),
            risk="CRITICAL",
            explanation=detailed_explanation,
            evidence=evidence_copy,
            recommendation=AgentAction.BLOCKED,
            confidence=1.0,
        )

    if action == AgentAction.HUMAN_REVIEW:
        risk = (
            "CRITICAL"
            if normalized_severity == "CRITICAL"
            else "HIGH"
            if normalized_severity == "HIGH"
            else "MEDIUM"
        )

        confidence = (
            1.0
            if normalized_severity
            in {
                "CRITICAL",
                "HIGH",
            }
            else 0.9
        )

        return AgentInvestigation(
            case_id=case_id,
            finding=(
                "Financial control exception "
                "requires human review."
            ),
            risk=risk,
            explanation=detailed_explanation,
            evidence=evidence_copy,
            recommendation=AgentAction.HUMAN_REVIEW,
            confidence=confidence,
        )

    if action == AgentAction.MONITOR:
        return AgentInvestigation(
            case_id=case_id,
            finding=(
                "Financial activity "
                "requires monitoring."
            ),
            risk="MEDIUM",
            explanation=detailed_explanation,
            evidence=evidence_copy,
            recommendation=AgentAction.MONITOR,
            confidence=0.9,
        )

    if action == AgentAction.CLEAR:
        return AgentInvestigation(
            case_id=case_id,
            finding=(
                "No material financial "
                "control exception detected."
            ),
            risk="LOW",
            explanation=(
                "All required deterministic "
                "reconciliation controls passed "
                "across the financial path from "
                "fee ledger to payment gateway, "
                "settlement, and bank evidence."
            ),
            evidence=evidence_copy,
            recommendation=AgentAction.CLEAR,
            confidence=1.0,
        )

    raise ValueError(
        f"Unsupported agent action "
        f"'{action}' for case {case_id}."
    )