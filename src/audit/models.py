from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class AuditRecord:
    run_id: str
    case_id: str
    timestamp: str

    reconciliation_status: str
    exception_code: str | None

    control_action: str
    severity: str

    agent_action: str
    requires_human: bool

    reason: str
    evidence: dict[str, Any]