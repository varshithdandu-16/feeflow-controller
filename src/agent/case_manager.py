from dataclasses import dataclass

from src.agent.contracts import AgentInvestigation


@dataclass(frozen=True)
class ReviewCase:
    case_id: str
    finding: str
    risk: str
    explanation: str
    evidence: list[str]
    recommendation: str
    confidence: float
    status: str


def create_review_case(
    investigation: AgentInvestigation,
) -> ReviewCase:
    """
    Convert an agent investigation into a structured
    human-review case.

    This module does not approve, reject, block, or modify
    any financial transaction.
    """

    if not investigation.case_id:
        raise ValueError("Investigation case_id cannot be empty.")

    if not investigation.finding:
        raise ValueError(
            f"Investigation finding cannot be empty for case "
            f"{investigation.case_id}."
        )

    if not 0.0 <= investigation.confidence <= 1.0:
        raise ValueError(
            f"Investigation confidence must be between 0 and 1 "
            f"for case {investigation.case_id}."
        )

    return ReviewCase(
        case_id=investigation.case_id,
        finding=investigation.finding,
        risk=investigation.risk,
        explanation=investigation.explanation,
        evidence=list(investigation.evidence),
        recommendation=investigation.recommendation.value,
        confidence=investigation.confidence,
        status="OPEN",
    )