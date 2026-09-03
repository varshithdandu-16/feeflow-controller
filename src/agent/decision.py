from dataclasses import dataclass

from src.agent.contracts import AgentAction, AgentInvestigation


@dataclass(frozen=True)
class AgentDecision:
    """
    Final workflow decision produced after investigation.

    This layer decides what the agent should do next.
    It does NOT execute any financial transaction.
    """

    case_id: str
    action: AgentAction
    reason: str
    confidence: float
    next_step: str
    requires_human: bool


def make_agent_decision(
    investigation: AgentInvestigation,
) -> AgentDecision:
    """
    Convert an investigation into an actionable agent workflow decision.

    Decision hierarchy:

        BLOCK
            -> Human review before any further processing

        HUMAN_REVIEW
            -> Human investigation required

        MONITOR
            -> Continue under monitoring

        CLEAR
            -> No exception requires intervention

    The deterministic control engine remains authoritative.
    This function only determines the next workflow state.

    No financial side effects are performed here.
    """

    if not investigation.case_id:
        raise ValueError(
            "Investigation case_id cannot be empty."
        )

    if not 0.0 <= investigation.confidence <= 1.0:
        raise ValueError(
            f"Investigation confidence must be between 0 and 1 "
            f"for case {investigation.case_id}."
        )

    action = investigation.recommendation

    if action == AgentAction.BLOCK:
        return AgentDecision(
            case_id=investigation.case_id,
            action=AgentAction.BLOCK,
            reason=(
                "The investigation confirms that the deterministic "
                "control policy requires this case to remain blocked."
            ),
            confidence=investigation.confidence,
            next_step="HUMAN_REVIEW",
            requires_human=True,
        )

    if action == AgentAction.HUMAN_REVIEW:
        return AgentDecision(
            case_id=investigation.case_id,
            action=AgentAction.HUMAN_REVIEW,
            reason=(
                "The investigation confirms that this financial "
                "exception requires human investigation."
            ),
            confidence=investigation.confidence,
            next_step="HUMAN_REVIEW",
            requires_human=True,
        )

    if action == AgentAction.MONITOR:
        return AgentDecision(
            case_id=investigation.case_id,
            action=AgentAction.MONITOR,
            reason=(
                "The investigation does not require immediate human "
                "intervention. The case should remain under monitoring."
            ),
            confidence=investigation.confidence,
            next_step="MONITOR",
            requires_human=False,
        )

    if action == AgentAction.CLEAR:
        return AgentDecision(
            case_id=investigation.case_id,
            action=AgentAction.CLEAR,
            reason=(
                "The investigation found no exception requiring "
                "additional intervention."
            ),
            confidence=investigation.confidence,
            next_step="COMPLETE",
            requires_human=False,
        )

    raise ValueError(
        f"Unsupported investigation recommendation "
        f"for case {investigation.case_id}: {action}"
    )