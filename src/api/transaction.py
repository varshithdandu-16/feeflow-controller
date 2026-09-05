from fastapi import (
    APIRouter,
    HTTPException,
)
from pydantic import (
    BaseModel,
    Field,
)

from src.api.service import (
    run_control_pipeline,
)


router = APIRouter(
    prefix="/verify",
    tags=["Transaction Verification"],
)


class TransactionVerificationRequest(
    BaseModel
):
    case_id: str = Field(
        ...,
        min_length=1,
    )


@router.post("/transaction")
def verify_transaction(
    request: TransactionVerificationRequest,
):
    case_id = request.case_id.strip()

    if not case_id:
        raise HTTPException(
            status_code=400,
            detail="A transaction case ID is required.",
        )

    try:
        results = run_control_pipeline()

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Required financial source is unavailable: "
                f"{exc}"
            ),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Financial data validation failed: "
                f"{exc}"
            ),
        ) from exc

    result = next(
        (
            item
            for item in results
            if item.get("case_id")
            == case_id
        ),
        None,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Transaction case {case_id} "
                "was not found."
            ),
        )

    control = result["control"]
    reconciliation = result[
        "reconciliation"
    ]

    return {
        "status":
            "verification_completed",

        "case_id":
            case_id,

        "decision":
            control["action"],

        "risk":
            control["severity"],

        "human_action_required":
            control["action"]
            in {
                "HUMAN_REVIEW",
                "BLOCK",
            },

        "human_action":
            control["action"],

        "reason":
            control["reason"],

        "reconciliation": {
            "status":
                reconciliation["status"],
            "severity":
                reconciliation["severity"],
            "discrepancy_type":
                reconciliation[
                    "discrepancy_type"
                ],
            "message":
                reconciliation["message"],
            "evidence":
                reconciliation["evidence"],
        },

        "control":
            control,

        "financial_transaction_modified":
            False,
    }