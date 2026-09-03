from dataclasses import asdict

from fastapi import (
    APIRouter,
    HTTPException,
)

from pydantic import (
    BaseModel,
    Field,
)

from src.agent.human_decision import (
    submit_human_decision,
)

from src.agent.orchestrator import (
    run_agent,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/review",
    tags=["Human Review"],
)


# =========================================================
# HUMAN DECISION REQUEST
# =========================================================

class HumanDecisionRequest(BaseModel):
    """
    Request submitted by a human reviewer.

    This represents a review-workflow disposition only.
    """

    decision: str = Field(
        ...,
        description=(
            "Human review disposition."
        ),
    )

    reason: str = Field(
        ...,
        min_length=1,
        description=(
            "Reason for the human decision."
        ),
    )

    reviewer: str = Field(
        ...,
        min_length=1,
        description=(
            "Reviewer identity."
        ),
    )


# =========================================================
# GET REVIEW QUEUE
# =========================================================

@router.post("/cases")
def get_review_cases():
    """
    Generate the current agent run and return
    human-review packets.

    Workflow-only endpoint.

    It does NOT:

        - approve transactions
        - reject transactions
        - block transactions
        - release payments
        - execute payments
        - modify financial records
    """

    try:

        # -------------------------------------------------
        # Run complete agent workflow
        # -------------------------------------------------

        result = run_agent()

        # -------------------------------------------------
        # Convert review packets to API data
        # -------------------------------------------------

        cases = [
            asdict(packet)
            for packet
            in result.human_review_packets
        ]

        # -------------------------------------------------
        # Return review queue
        # -------------------------------------------------

        return {
            "status": (
                "review_queue_ready"
            ),

            "agent_status": (
                result.status.value
            ),

            "total_cases": len(
                cases
            ),

            "cases": cases,
        }

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Required financial source "
                f"is unavailable: {exc}"
            ),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Review data validation "
                f"failed: {exc}"
            ),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to generate "
                f"review queue: {exc}"
            ),
        ) from exc


# =========================================================
# SUBMIT HUMAN REVIEW DECISION
# =========================================================

@router.post(
    "/cases/{case_id}/decision"
)
def submit_review_decision(
    case_id: str,
    request: HumanDecisionRequest,
):
    """
    Record a human review disposition.

    This endpoint changes review workflow state only.

    It does NOT:

        - execute a payment
        - release a payment
        - modify a transaction
        - approve a financial transaction
        - reject a financial transaction
        - block a financial transaction
    """

    try:

        # -------------------------------------------------
        # Record human workflow decision
        # -------------------------------------------------

        decision = submit_human_decision(
            case_id=case_id,

            decision=request.decision,

            reason=request.reason,

            reviewer=request.reviewer,
        )

        # -------------------------------------------------
        # Return structured result
        # -------------------------------------------------

        return {
            "status": (
                "human_decision_recorded"
            ),

            "decision": asdict(
                decision
            ),

            "financial_transaction_modified": (
                False
            ),
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to record "
                f"human decision: {exc}"
            ),
        ) from exc