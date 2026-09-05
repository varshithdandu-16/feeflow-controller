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
from src.agent.run_store import (
    get_review_queue,
)


router = APIRouter(
    prefix="/review",
    tags=["Human Review"],
)


class HumanDecisionRequest(
    BaseModel
):
    decision: str = Field(
        ...,
        min_length=1,
    )

    reason: str = Field(
        ...,
        min_length=1,
    )

    reviewer: str = Field(
        ...,
        min_length=1,
    )


@router.api_route(
    "/cases",
    methods=["GET", "POST"],
)
def get_review_cases():
    try:
        cases = get_review_queue()

        return {
            "status":
                "review_queue_ready",

            "total_cases":
                len(cases),

            "cases":
                cases,
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
                "Unable to load review queue: "
                f"{exc}"
            ),
        ) from exc


@router.post(
    "/cases/{case_id}/decision"
)
def submit_review_decision(
    case_id: str,
    request: HumanDecisionRequest,
):
    try:
        decision = submit_human_decision(
            case_id=case_id,
            decision=request.decision,
            reason=request.reason,
            reviewer=request.reviewer,
        )

        return {
            "status":
                "human_decision_recorded",

            "decision":
                asdict(decision),

            "financial_transaction_modified":
                False,
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
                "Unable to record human decision: "
                f"{exc}"
            ),
        ) from exc