from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)

from src.agent.run_store import (
    record_human_decision,
)


ALLOWED_DECISIONS = {
    "CONFIRM_REVIEW",
    "ESCALATE",
    "REQUEST_MORE_EVIDENCE",
}


@dataclass(frozen=True)
class HumanDecision:
    case_id: str
    decision: str
    reason: str
    reviewer: str
    decided_at: str


def submit_human_decision(
    case_id: str,
    decision: str,
    reason: str,
    reviewer: str,
) -> HumanDecision:

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

    if not normalized_case_id:
        raise ValueError(
            "case_id cannot be empty."
        )

    if (
        normalized_decision
        not in ALLOWED_DECISIONS
    ):
        raise ValueError(
            "Invalid human decision: "
            f"{normalized_decision}. "
            "Allowed values: "
            f"{sorted(ALLOWED_DECISIONS)}"
        )

    if not normalized_reason:
        raise ValueError(
            "A reason is required for every human decision."
        )

    if not normalized_reviewer:
        raise ValueError(
            "Reviewer identity is required."
        )

    decided_at = datetime.now(
        timezone.utc
    ).isoformat()

    result = HumanDecision(
        case_id=normalized_case_id,
        decision=normalized_decision,
        reason=normalized_reason,
        reviewer=normalized_reviewer,
        decided_at=decided_at,
    )

    record_human_decision(
        case_id=result.case_id,
        decision=result.decision,
        reason=result.reason,
        reviewer=result.reviewer,
        decided_at=result.decided_at,
    )

    return result