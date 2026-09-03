from dataclasses import dataclass
from typing import Any

from src.agent.case_manager import ReviewCase
from src.agent.review_manager import ReviewDecision


@dataclass(frozen=True)
class HumanReviewPacket:
    """
    Read-only package presented to a human reviewer.

    This component does not approve, reject, release,
    block, or modify any financial transaction.

    It only organizes the evidence and routing information
    already produced by the agent.
    """

    case_id: str
    status: str
    priority: str
    assigned_to: str

    finding: str
    risk: str
    explanation: str

    evidence: dict[str, Any]

    recommendation: str
    decision: str
    reason: str

    confidence: float

    human_action_required: bool


def prepare_human_review(
    review_case: ReviewCase,
    review_decision: ReviewDecision,
) -> HumanReviewPacket:
    """
    Build a structured human-review packet.

    The human reviewer receives:
        - the original case finding
        - risk level
        - investigation explanation
        - supporting evidence
        - recommendation
        - review priority
        - routing information
        - confidence

    The agent remains advisory and workflow-oriented.
    Final financial decisions remain outside this system.
    """

    # -----------------------------------------------------
    # Validate case
    # -----------------------------------------------------

    if not review_case.case_id:
        raise ValueError(
            "Human-review case_id cannot be empty."
        )

    if review_case.case_id != review_decision.case_id:
        raise ValueError(
            "Review case and review decision case_id "
            "must match."
        )

    # -----------------------------------------------------
    # Validate decision
    # -----------------------------------------------------

    if not review_decision.assigned_to:
        raise ValueError(
            f"Review case {review_case.case_id} "
            "has no reviewer assignment."
        )

    if not review_decision.priority:
        raise ValueError(
            f"Review case {review_case.case_id} "
            "has no review priority."
        )

    if not 0.0 <= review_decision.confidence <= 1.0:
        raise ValueError(
            f"Review decision confidence must be between "
            f"0 and 1 for case {review_case.case_id}."
        )

    # -----------------------------------------------------
    # Normalize recommendation
    # -----------------------------------------------------

    recommendation = review_case.recommendation

    if hasattr(recommendation, "value"):
        recommendation = recommendation.value

    recommendation = str(recommendation)

    # -----------------------------------------------------
    # Build immutable review packet
    # -----------------------------------------------------

    return HumanReviewPacket(
        case_id=review_case.case_id,
        status=review_decision.status,
        priority=review_decision.priority,
        assigned_to=review_decision.assigned_to,

        finding=review_case.finding,
        risk=review_case.risk,
        explanation=review_case.explanation,

        evidence=review_case.evidence,

        recommendation=recommendation,
        decision=review_decision.decision,
        reason=review_decision.reason,

        confidence=review_decision.confidence,

        human_action_required=(
            review_decision.decision
            == "HUMAN_DECISION_REQUIRED"
        ),
    )