from datetime import datetime, timezone
from uuid import uuid4

from src.audit.models import AuditRecord


def create_run_id() -> str:
    """Create a unique identifier for one agent execution."""
    return f"RUN-{uuid4().hex[:12].upper()}"


def create_audit_record(
    run_id: str,
    assessment: dict,
) -> AuditRecord:
    """
    Create an immutable-style audit record from an agent assessment.

    This function performs no financial side effects.
    """

    return AuditRecord(
        run_id=run_id,
        case_id=assessment["case_id"],
        timestamp=datetime.now(timezone.utc).isoformat(),

        reconciliation_status=assessment.get(
            "reconciliation_status",
            "UNKNOWN",
        ),
        exception_code=assessment.get(
            "exception_code",
        ),

        control_action=assessment.get(
            "control_action",
            "UNKNOWN",
        ),
        severity=assessment.get(
            "severity",
            "UNKNOWN",
        ),

        agent_action=assessment["action"],
        requires_human=assessment["requires_human"],

        reason=assessment["reason"],
        evidence=assessment.get(
            "evidence",
            {},
        ),
    )