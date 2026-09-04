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
    FeeFlow Controller autonomous agent.

    Agent workflow:

        Financial Controls
                ↓
            Assessment
                ↓
        Risk Investigation
                ↓
        Human Review Routing
                ↓
          Review Packet
                ↓
              Audit
                ↓
          Save Agent Run

    The agent observes financial-control results and
    automatically decides what workflow each case needs.

    The agent does NOT:
        - approve payments
        - release payments
        - execute payments
        - modify financial records

    Financial controls remain authoritative.
    """

    # ---------------------------------------------------------
    # 1. Start one agent run
    # ---------------------------------------------------------

    run_id = create_run_id()

    # ---------------------------------------------------------
    # 2. Get financial cases from the existing control engine
    # ---------------------------------------------------------

    control_results = run_control_pipeline()

    # ---------------------------------------------------------
    # 3. Agent assesses every financial case
    # ---------------------------------------------------------

    assessments = []

    for control_result in control_results:
        assessment = assess_control_result(control_result)
        assessments.append(assessment)

    # ---------------------------------------------------------
    # 4. Prepare agent workflow results
    # ---------------------------------------------------------

    investigations = []
    review_cases = []
    review_decisions = []
    human_review_packets = []

    # ---------------------------------------------------------
    # 5. Agent handles cases that need attention
    # ---------------------------------------------------------

    for control_result, assessment in zip(
        control_results,
        assessments,
    ):

        # Safe cases continue automatically.
        if not assessment.requires_human:
            continue

        # -----------------------------------------------------
        # Investigate suspicious / exceptional case
        # -----------------------------------------------------

        investigation = investigate_case(
            case_id=assessment.case_id,
            action=assessment.action,
            severity=control_result["control"]["severity"],
            reason=control_result["control"]["reason"],
            evidence=control_result.get(
                "evidence",
                {},
            ),
        )

        investigations.append(investigation)

        # -----------------------------------------------------
        # Create a human-review case
        # -----------------------------------------------------

        review_case = create_review_case(
            investigation=investigation,
        )

        review_cases.append(review_case)

        # -----------------------------------------------------
        # Automatically route the case
        # -----------------------------------------------------

        review_decision = manage_review_case(
            review_case=review_case,
        )

        review_decisions.append(review_decision)

        # -----------------------------------------------------
        # Prepare everything a human reviewer needs
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
    # 7. Create audit record for EVERY case
    # ---------------------------------------------------------

    audit_records = []

    for control_result, assessment in zip(
        control_results,
        assessments,
    ):

        assessment_data = asdict(assessment)

        audit_input = {
            **assessment_data,

            "reconciliation_status": control_result.get(
                "reconciliation_status",
                "UNKNOWN",
            ),

            "exception_code": control_result.get(
                "exception_code",
            ),

            "control_action": control_result["control"].get(
                "action",
                "UNKNOWN",
            ),

            "severity": control_result["control"].get(
                "severity",
                "UNKNOWN",
            ),

            "evidence": control_result.get(
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
    # 9. Save the complete agent run
    # ---------------------------------------------------------

    save_agent_run(
        result=result,
        run_id=run_id,
    )

    # ---------------------------------------------------------
    # 10. Return result to FastAPI
    # ---------------------------------------------------------

    return result