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

    Workflow:

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
                ↓
        Persistent Run Storage

    The deterministic control engine remains authoritative.

    The agent does NOT:

        - approve transactions
        - reject transactions
        - release payments
        - execute payments
        - modify financial records
    """

    # =====================================================
    # 1. Create one ID for this complete agent execution
    # =====================================================

    run_id = create_run_id()

    # =====================================================
    # 2. Run deterministic financial controls
    # =====================================================

    control_results = run_control_pipeline()

    # =====================================================
    # 3. Assess every control result
    # =====================================================

    assessments = [
        assess_control_result(result)
        for result in control_results
    ]

    # =====================================================
    # 4. Prepare workflow collections
    # =====================================================

    investigations = []
    review_cases = []
    review_decisions = []
    human_review_packets = []

    # =====================================================
    # 5. Investigate exceptions and route them
    # =====================================================

    for control_result, assessment in zip(
        control_results,
        assessments,
    ):
        # CLEAR and MONITOR cases do not require
        # investigation or human review.
        if not assessment.requires_human:
            continue

        # -------------------------------------------------
        # Investigation
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Create review case
        # -------------------------------------------------

        review_case = create_review_case(
            investigation=investigation,
        )

        review_cases.append(review_case)

        # -------------------------------------------------
        # Route through Review Manager
        # -------------------------------------------------

        review_decision = manage_review_case(
            review_case=review_case,
        )

        review_decisions.append(review_decision)

        # -------------------------------------------------
        # Build human-review packet
        # -------------------------------------------------

        human_review_packet = prepare_human_review(
            review_case=review_case,
            review_decision=review_decision,
        )

        human_review_packets.append(
            human_review_packet
        )

    # =====================================================
    # 6. Determine overall agent status
    # =====================================================

    requires_human = any(
        assessment.requires_human
        for assessment in assessments
    )

    status = (
        AgentRunStatus.REQUIRES_HUMAN
        if requires_human
        else AgentRunStatus.COMPLETED
    )

    # =====================================================
    # 7. Create audit records
    # =====================================================

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

        audit_records.append(
            create_audit_record(
                run_id=run_id,
                assessment=audit_input,
            )
        )

    # =====================================================
    # 8. Build complete agent result
    # =====================================================

    result = AgentRunResult(
        status=status,
        assessments=assessments,
        audit_records=audit_records,
        investigations=investigations,
        review_cases=review_cases,
        review_decisions=review_decisions,
        human_review_packets=human_review_packets,
    )

    # =====================================================
    # 9. Persist operational run
    # =====================================================

    save_agent_run(
        result=result,
        run_id=run_id,
    )

    # =====================================================
    # 10. Return complete agent execution
    # =====================================================

    return result