from src.agent.contracts import AgentAction, AgentInvestigation


def investigate_case(
    case_id: str,
    action: AgentAction,
    severity: str,
    reason: str,
    evidence: dict,
) -> AgentInvestigation:
    """
    Investigate a control exception using the deterministic
    control decision and available evidence.

    This investigation layer provides structured reasoning
    for human review.

    It does not approve, reject, release, execute,
    or modify any financial transaction.
    """

    if not case_id:
        raise ValueError(
            "Investigation case_id cannot be empty."
        )

    if not isinstance(action, AgentAction):
        raise ValueError(
            f"Invalid agent action for case {case_id}: {action}"
        )

    if not severity:
        raise ValueError(
            f"Investigation severity cannot be empty "
            f"for case {case_id}."
        )

    if not reason:
        raise ValueError(
            f"Investigation reason cannot be empty "
            f"for case {case_id}."
        )

    if not isinstance(evidence, dict):
        raise ValueError(
            f"Investigation evidence must be a dictionary "
            f"for case {case_id}."
        )

    normalized_severity = severity.upper()

    # =====================================================
    # BLOCKED CASE
    # =====================================================

    if action == AgentAction.BLOCKED:
        return AgentInvestigation(
            case_id=case_id,
            finding="Financial control exception requires blocking.",
            risk="CRITICAL",
            explanation=(
                "The deterministic control engine identified a "
                "blocking condition. The agent preserves the "
                "control decision and routes the case for human "
                "investigation."
            ),
            evidence=evidence,
            recommendation=AgentAction.BLOCKED,
            confidence=1.0,
        )

    # =====================================================
    # HUMAN REVIEW CASE
    # =====================================================

    if action == AgentAction.HUMAN_REVIEW:
        risk = (
            "CRITICAL"
            if normalized_severity == "CRITICAL"
            else "HIGH"
            if normalized_severity == "HIGH"
            else "MEDIUM"
        )

        confidence = (
            1.0
            if normalized_severity in {"CRITICAL", "HIGH"}
            else 0.9
        )

        return AgentInvestigation(
            case_id=case_id,
            finding="Financial control exception requires human review.",
            risk=risk,
            explanation=(
                "The deterministic control engine identified an "
                "exception that cannot be resolved automatically. "
                "The agent has collected the available evidence "
                "and routed the case to human review."
            ),
            evidence=evidence,
            recommendation=AgentAction.HUMAN_REVIEW,
            confidence=confidence,
        )

    # =====================================================
    # MONITOR CASE
    # =====================================================

    if action == AgentAction.MONITOR:
        return AgentInvestigation(
            case_id=case_id,
            finding="Financial activity requires monitoring.",
            risk="MEDIUM",
            explanation=(
                "The deterministic control engine identified a "
                "condition that does not require immediate human "
                "intervention but should remain under monitoring."
            ),
            evidence=evidence,
            recommendation=AgentAction.MONITOR,
            confidence=0.9,
        )

    # =====================================================
    # CLEAR CASE
    # =====================================================

    if action == AgentAction.CLEAR:
        return AgentInvestigation(
            case_id=case_id,
            finding="No material financial control exception detected.",
            risk="LOW",
            explanation=(
                "The deterministic control engine cleared the case. "
                "No human investigation is required."
            ),
            evidence=evidence,
            recommendation=AgentAction.CLEAR,
            confidence=1.0,
        )

    # =====================================================
    # SAFETY FALLBACK
    # =====================================================

    raise ValueError(
        f"Unsupported agent action '{action}' "
        f"for case {case_id}."
    )