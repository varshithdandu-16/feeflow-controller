from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, TYPE_CHECKING


# =========================================================
# TYPE-ONLY IMPORTS
# =========================================================

if TYPE_CHECKING:
    from src.agent.case_manager import ReviewCase
    from src.agent.review_manager import ReviewDecision
    from src.audit.models import AuditRecord


# =========================================================
# AGENT RUN STATUS
# =========================================================

class AgentRunStatus(str, Enum):
    """
    Overall status of one complete FeeFlow Controller run.
    """

    COMPLETED = "COMPLETED"
    REQUIRES_HUMAN = "REQUIRES_HUMAN"


# =========================================================
# AGENT ACTION
# =========================================================

class AgentAction(str, Enum):
    """
    Workflow action produced by the agent assessment layer.

    These actions never directly execute financial operations.
    """

    CLEAR = "CLEAR"
    MONITOR = "MONITOR"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCKED = "BLOCKED"


# =========================================================
# AGENT ASSESSMENT
# =========================================================

@dataclass(frozen=True)
class AgentAssessment:
    """
    Assessment of one deterministic control result.

    The assessment layer interprets the authoritative
    deterministic control output.
    """

    case_id: str
    action: AgentAction
    reason: str
    requires_human: bool


# =========================================================
# AGENT INVESTIGATION
# =========================================================

@dataclass(frozen=True)
class AgentInvestigation:
    """
    Investigation result for an exception.

    Investigation is evidence-driven and does not execute
    or modify any financial transaction.
    """

    case_id: str
    finding: str
    risk: str
    explanation: str
    evidence: dict[str, Any]
    recommendation: AgentAction
    confidence: float


# =========================================================
# HUMAN REVIEW PACKET
# =========================================================

@dataclass(frozen=True)
class HumanReviewPacket:
    """
    Structured information prepared for human review.

    This packet supports a human decision workflow.
    It does not itself approve, reject, release, or
    modify a financial transaction.
    """

    case_id: str
    priority: str
    assigned_to: str
    finding: str
    risk: str
    explanation: str
    evidence: dict[str, Any]
    recommendation: str
    confidence: float
    status: str


# =========================================================
# COMPLETE AGENT RUN RESULT
# =========================================================

@dataclass
class AgentRunResult:
    """
    Complete result produced by one FeeFlow Controller
    agent execution.

    Agent workflow:

        Deterministic Controls
                ↓
            Assessment
                ↓
          Investigation
                ↓
           Review Case
                ↓
          Review Manager
                ↓
       Human Review Packet
                ↓
              Audit

    The deterministic control engine remains authoritative.

    The agent does NOT:

        - approve transactions
        - reject transactions
        - release payments
        - execute payments
        - modify financial records
    """

    status: AgentRunStatus

    assessments: list[AgentAssessment]

    audit_records: list["AuditRecord"]

    investigations: list[AgentInvestigation]

    review_cases: list["ReviewCase"]

    review_decisions: list["ReviewDecision"]

    # -----------------------------------------------------
    # Optional until the human-review packet stage is
    # connected to the orchestrator.
    #
    # This prevents older valid agent runs from breaking
    # while keeping the contract ready for the next stage.
    # -----------------------------------------------------

    human_review_packets: list[HumanReviewPacket] | None = None

    def __post_init__(self) -> None:
        """
        Normalize an omitted packet collection to an empty list.
        """

        if self.human_review_packets is None:
            self.human_review_packets = []