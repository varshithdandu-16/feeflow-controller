from dataclasses import asdict

from src.api.service import run_control_pipeline

from src.agent.assessment import assess_control_result
from src.agent.case_manager import create_review_case
from src.agent.contracts import AgentRunResult, AgentRunStatus
from src.agent.human_review import prepare_human_review
from src.agent.investigator import investigate_case
from src.agent.review_manager import manage_review_case
from src.agent.run_store import save_agent_run

from src.audit.logger import create_audit_record, create_run_id


def run_agent() -> AgentRunResult:
    """
    Execute one complete FeeFlow Controller agent run.

    Deterministic financial controls remain authoritative.
    The agent interprets findings, investigates exceptions,
    routes human review, prepares evidence, and creates audit records.

    The agent never approves, releases, executes, or modifies payments.
    """

    # ---------------------------------------------------------
    # 1. Start one agent run
    # ---------------------------------------------------------

    run_id = create_run_id()

    # ---------------------------------------------------------
    # 2. Execute deterministic financial controls
    # ---------------------------------------------------------

    control_results = run_control_pipeline()

    # ---------------------------------------------------------
    # 3. Assess every control result
    # ---------------------------------------------------------

    assessments = []

    for control_result in control_results:
        reconciliation = control_result.get("reconciliation", {})
        control = control_result.get("control", {})

        # Preserve the authoritative control decision while enriching
        # the agent explanation with the actual reconciliation finding.
        enriched_result = {
            **control_result,
            "control": {
                **control,
                "reason": (
                    f"{control.get('reason', 'No control reason supplied.')} "
                    f"Reconciliation: "
                    f"{reconciliation.get('message', 'No reconciliation message supplied.')}"
                ),
            },
        }

        assessment = assess_control_result(enriched_result)
        assessments.append(assessment)

    # ---------------------------------------------------------
    # 4. Prepare workflow collections
    # ---------------------------------------------------------

    investigations = []
    review_cases = []
    review_decisions = []
    human_review_packets = []

    # ---------------------------------------------------------
    # 5. Investigate cases requiring attention
    # ---------------------------------------------------------

    for control_result, assessment in zip(
        control_results,
        assessments,
    ):

        if not assessment.requires_human:
            continue

        reconciliation = control_result.get(
            "reconciliation",
            {},
        )

        control = control_result.get(
            "control",
            {},
        )

        investigation = investigate_case(
            case_id=assessment.case_id,
            action=assessment.action,
            severity=control.get(
                "severity",
                reconciliation.get(
                    "severity",
                    "UNKNOWN",
                ),
            ),
            reason=assessment.reason,
            evidence=reconciliation.get(
                "evidence",
                {},
            ),
        )

        investigations.append(investigation)

        # -----------------------------------------------------
        # Create human review case
        # -----------------------------------------------------

        review_case = create_review_case(
            investigation=investigation,
        )

        review_cases.append(review_case)

        # -----------------------------------------------------
        # Route review
        # -----------------------------------------------------

        review_decision = manage_review_case(
            review_case=review_case,
        )

        review_decisions.append(review_decision)

        # -----------------------------------------------------
        # Prepare human review packet
        # -----------------------------------------------------

        human_review_packet = prepare_human_review(
            review_case=review_case,
            review_decision=review_decision,
        )

        human_review_packets.append(
            human_review_packet
        )

    # ---------------------------------------------------------
    # 6. Determine overall agent status
    # ---------------------------------------------------------

    requires_human = any(
        assessment.requires_human
        for assessment in assessments
    )

    if requires_human:
        status = AgentRunStatus.REQUIRES_HUMAN
    else:
        status = AgentRunStatus.COMPLETED

    # ---------------------------------------------------------
    # 7. Create audit record for every case
    # ---------------------------------------------------------

    audit_records = []

    for control_result, assessment in zip(
        control_results,
        assessments,
    ):

        reconciliation = control_result.get(
            "reconciliation",
            {},
        )

        control = control_result.get(
            "control",
            {},
        )

        audit_input = {
            **asdict(assessment),

            "reconciliation_status": reconciliation.get(
                "status",
                "UNKNOWN",
            ),

            "exception_code": control.get(
                "exception_code",
                reconciliation.get(
                    "discrepancy_type",
                    "NONE",
                ),
            ),

            "control_action": control.get(
                "action",
                "UNKNOWN",
            ),

            "severity": control.get(
                "severity",
                reconciliation.get(
                    "severity",
                    "UNKNOWN",
                ),
            ),

            "reconciliation_message": reconciliation.get(
                "message",
                "No reconciliation message supplied.",
            ),

            "evidence": reconciliation.get(
                "evidence",
                {},
            ),
        }

        audit_record = create_audit_record(
            run_id=run_id,
            assessment=audit_input,
        )

        audit_records.append(audit_record)

    # ---------------------------------------------------------
    # 8. Build complete agent result
    # ---------------------------------------------------------

    result = AgentRunResult(
        status=status,
        assessments=assessments,
        audit_records=audit_records,
        investigations=investigations,
        review_cases=review_cases,
        review_decisions=review_decisions,
        human_review_packets=human_review_packets,
    )

    # ---------------------------------------------------------
    # 9. Persist complete run
    # ---------------------------------------------------------

    save_agent_run(
        result=result,
        run_id=run_id,
    )

    # ---------------------------------------------------------
    # 10. Return result to API
    # ---------------------------------------------------------

    return result