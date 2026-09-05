from fastapi import (
    APIRouter,
    HTTPException,
)

from src.agent.run_store import (
    get_audit_records,
)


router = APIRouter(
    prefix="/audit",
    tags=["Audit"],
)


@router.get("/records")
def get_audit_records_endpoint():
    try:
        records = get_audit_records()

        return {
            "status":
                "audit_ready",

            "total_records":
                len(records),

            "records":
                records,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load audit records: "
                f"{exc}"
            ),
        ) from exc