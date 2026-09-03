from dataclasses import dataclass

from src.agent.case_manager import ReviewCase


@dataclass(frozen=True)
class ReviewDecision:
    """
    Data-driven decision produced by the review manager.

    The review manager does not approve, reject, release,
    or modify any financial transaction.
    """

    case_id: str
    status: str
    priority: str
    assigned_to: str
    decision: str
    reason: str
    confidence: float


def manage_review_case(
    review_case: ReviewCase,
) -> ReviewDecision:
    """
    Determine how a human-review case should be handled.

    Decision is based on:
        - risk
        - recommendation
        - confidence

    This is a workflow-management layer only.
    Financial execution remains outside the agent.
    """

    if not review_case.case_id:
        raise ValueError(
            "Review case_id cannot be empty."
        )

    if review_case.status != "OPEN":
        raise ValueError(
            f"Review case {review_case.case_id} "
            f"is not open."
        )

    if not 0.0 <= review_case.confidence <= 1.0:
        raise ValueError(
            f"Review case confidence must be between 0 and 1 "
            f"for case {review_case.case_id}."
        )

    risk = review_case.risk.upper()
    recommendation = review_case.recommendation.upper()

    # ---------------------------------------------------------
    # BLOCKED cases receive the highest review priority.
    # ---------------------------------------------------------
    if recommendation == "BLOCK":
        return ReviewDecision(
            case_id=review_case.case_id,
            status="OPEN",
            priority="CRITICAL",
            assigned_to="FINANCIAL_RISK_REVIEW",
            decision="HUMAN_DECISION_REQUIRED",
            reason=(
                "The case is blocked by the control policy. "
                "A human reviewer must investigate the evidence "
                "before any further financial workflow proceeds."
            ),
            confidence=review_case.confidence,
        )

    # ---------------------------------------------------------
    # High/Critical risk exceptions require immediate review.
    # ---------------------------------------------------------
    if risk in {"CRITICAL", "HIGH"}:
        return ReviewDecision(
            case_id=review_case.case_id,
            status="OPEN",
            priority="HIGH",
            assigned_to="FINANCIAL_RISK_REVIEW",
            decision="HUMAN_DECISION_REQUIRED",
            reason=(
                "The investigation indicates elevated financial risk. "
                "The case has been routed for human investigation."
            ),
            confidence=review_case.confidence,
        )

    # ---------------------------------------------------------
    # Normal human-review exceptions.
    # ---------------------------------------------------------
    if recommendation == "HUMAN_REVIEW":
        return ReviewDecision(
            case_id=review_case.case_id,
            status="OPEN",
            priority="NORMAL",
            assigned_to="FINANCIAL_OPERATIONS_REVIEW",
            decision="HUMAN_DECISION_REQUIRED",
            reason=(
                "The agent identified an exception that requires "
                "human investigation before resolution."
            ),
            confidence=review_case.confidence,
        )

    # ---------------------------------------------------------
    # Fallback for any review case that does not match
    # a higher-priority condition.
    # ---------------------------------------------------------
    return ReviewDecision(
        case_id=review_case.case_id,
        status="OPEN",
        priority="NORMAL",
        assigned_to="FINANCIAL_OPERATIONS_REVIEW",
        decision="HUMAN_DECISION_REQUIRED",
        reason=(
            "The case requires human review based on the "
            "available investigation evidence."
        ),
        confidence=review_case.confidence,
    )