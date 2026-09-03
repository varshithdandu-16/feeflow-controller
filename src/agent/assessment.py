from src.agent.contracts import AgentAction, AgentAssessment


def assess_control_result(result: dict) -> AgentAssessment:
    """
    Convert one deterministic control result into an agent assessment.

    The deterministic control engine remains authoritative.
    This layer only interprets the control decision.

    No financial side effects are performed here.
    """

    if not isinstance(result, dict):
        raise TypeError("Control result must be a dictionary.")

    case_id = result.get("case_id")
    control = result.get("control")

    if not case_id:
        raise ValueError("Control result is missing 'case_id'.")

    if not isinstance(control, dict):
        raise ValueError(
            f"Control result for case {case_id} is missing 'control'."
        )

    action = control.get("action")
    severity = control.get("severity", "UNKNOWN")
    reason = control.get("reason", "No reason supplied.")

    if action == "AUTO_CLEAR":
        return AgentAssessment(
            case_id=case_id,
            action=AgentAction.CLEAR,
            reason=(
                "Deterministic controls passed. "
                "No exception requires intervention."
            ),
            requires_human=False,
        )

    if action == "MONITOR":
        return AgentAssessment(
            case_id=case_id,
            action=AgentAction.MONITOR,
            reason=(
                "Control engine classified this case for monitoring. "
                f"Severity: {severity}. {reason}"
            ),
            requires_human=False,
        )

    if action == "HUMAN_REVIEW":
        return AgentAssessment(
            case_id=case_id,
            action=AgentAction.HUMAN_REVIEW,
            reason=(
                "Financial exception requires human investigation. "
                f"Severity: {severity}. {reason}"
            ),
            requires_human=True,
        )

    if action == "BLOCK":
        return AgentAssessment(
            case_id=case_id,
            action=AgentAction.BLOCK,
            reason=(
                "Control policy requires the case to be blocked. "
                f"Severity: {severity}. {reason}"
            ),
            requires_human=True,
        )

    raise ValueError(
        f"Unsupported control action for case {case_id}: {action}"
    )