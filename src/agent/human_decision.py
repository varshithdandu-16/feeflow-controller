from dataclasses import dataclass
from datetime import datetime, timezone

from src.agent.run_store import (
    record_human_decision,
)


# =========================================================
# ALLOWED HUMAN WORKFLOW DECISIONS
# =========================================================

ALLOWED_DECISIONS = {
    "CONFIRM_REVIEW",
    "ESCALATE",
    "REQUEST_MORE_EVIDENCE",
}


# =========================================================
# HUMAN DECISION MODEL
# =========================================================

@dataclass(frozen=True)
class HumanDecision:
    """
    A human review disposition recorded by the system.

    This is workflow state only.

    It does NOT:
        - approve a payment
        - reject a payment
        - release a payment
        - block a payment
        - execute a payment
        - modify a financial transaction
    """

    case_id: str
    decision: str
    reason: str
    reviewer: str
    decided_at: str


# =========================================================
# SUBMIT HUMAN DECISION
# =========================================================

def submit_human_decision(
    case_id: str,
    decision: str,
    reason: str,
    reviewer: str,
) -> HumanDecision:
    """
    Record a human review workflow decision.

    Financial execution remains completely outside
    this function.
    """

    # -----------------------------------------------------
    # Normalize inputs
    # -----------------------------------------------------

    normalized_case_id = (
        case_id.strip()
        if isinstance(case_id, str)
        else ""
    )

    normalized_decision = (
        decision.strip().upper()
        if isinstance(decision, str)
        else ""
    )

    normalized_reason = (
        reason.strip()
        if isinstance(reason, str)
        else ""
    )

    normalized_reviewer = (
        reviewer.strip()
        if isinstance(reviewer, str)
        else ""
    )

    # -----------------------------------------------------
    # Validate case ID
    # -----------------------------------------------------

    if not normalized_case_id:

        raise ValueError(
            "case_id cannot be empty."
        )

    # -----------------------------------------------------
    # Validate decision
    # -----------------------------------------------------

    if normalized_decision not in ALLOWED_DECISIONS:

        raise ValueError(
            f"Invalid human decision: "
            f"{normalized_decision}. "
            f"Allowed values: "
            f"{sorted(ALLOWED_DECISIONS)}"
        )

    # -----------------------------------------------------
    # Validate reason
    # -----------------------------------------------------

    if not normalized_reason:

        raise ValueError(
            "A reason is required for every human decision."
        )

    # -----------------------------------------------------
    # Validate reviewer
    # -----------------------------------------------------

    if not normalized_reviewer:

        raise ValueError(
            "Reviewer identity is required."
        )

    # -----------------------------------------------------
    # Create UTC timestamp
    # -----------------------------------------------------

    decided_at = datetime.now(
        timezone.utc
    ).isoformat()

    # -----------------------------------------------------
    # Create immutable decision object
    # -----------------------------------------------------

    human_decision = HumanDecision(
        case_id=normalized_case_id,
        decision=normalized_decision,
        reason=normalized_reason,
        reviewer=normalized_reviewer,
        decided_at=decided_at,
    )

    # -----------------------------------------------------
    # Persist workflow decision
    # -----------------------------------------------------

    record_human_decision(
        case_id=human_decision.case_id,

        decision=human_decision.decision,

        reason=human_decision.reason,

        reviewer=human_decision.reviewer,

        decided_at=human_decision.decided_at,
    )

    return human_decision