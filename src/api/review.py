from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agent.human_decision import submit_human_decision
from src.agent.run_store import get_review_queue


router = APIRouter(
    prefix="/review",
    tags=["Human Review"],
)


# =========================================================
# HUMAN DECISION REQUEST
# =========================================================

class HumanDecisionRequest(BaseModel):
    decision: str = Field(
        ...,
        min_length=1,
        description="Human review workflow decision.",
    )

    reason: str = Field(
        ...,
        min_length=1,
        description="Reason for the human decision.",
    )

    reviewer: str = Field(
        ...,
        min_length=1,
        description="Reviewer identity.",
    )


# =========================================================
# GET CURRENT HUMAN REVIEW QUEUE
# =========================================================

@router.api_route("/cases", methods=["GET", "POST"])
def get_review_cases():
    """
    Return persisted human-review cases.

    IMPORTANT:
    This endpoint does NOT start a new agent run.

    It reads the cases already created by the agent.
    """

    try:
        cases = get_review_queue()

        return {
            "status": "review_queue_ready",
            "total_cases": len(cases),
            "cases": cases,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load review queue: {exc}",
        ) from exc

# =========================================================
# SUBMIT HUMAN REVIEW DECISION
# =========================================================

@router.post("/cases/{case_id}/decision")
def submit_review_decision(
    case_id: str,
    request: HumanDecisionRequest,
):
    """
    Record a human review workflow decision.

    This changes workflow state only.

    It does NOT:
        - execute a payment
        - release a payment
        - approve a transaction
        - reject a transaction
        - modify a financial transaction
    """

    try:
        decision = submit_human_decision(
            case_id=case_id,
            decision=request.decision,
            reason=request.reason,
            reviewer=request.reviewer,
        )

        return {
            "status": "human_decision_recorded",
            "decision": asdict(decision),
            "financial_transaction_modified": False,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to record human decision: {exc}",
        ) from exc