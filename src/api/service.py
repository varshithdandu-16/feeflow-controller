from src.control_engine.decision import (
    evaluate_case,
)
from src.reconciliation.reconciliation import (
    reconcile_all,
)
from src.reconciliation.schema import (
    validate_all_sources,
)


def run_control_pipeline() -> list[dict]:
    validate_all_sources()

    findings = reconcile_all()

    results = []

    for finding in findings:
        decision = evaluate_case(
            case_id=finding.case_id,
            status=finding.status,
            exception_code=(
                finding.discrepancy_type
                or "NONE"
            ),
        )

        results.append(
            {
                "case_id": finding.case_id,
                "reconciliation_status":
                    finding.status,
                "exception_code":
                    finding.discrepancy_type,
                "evidence":
                    finding.evidence,
                "reconciliation": {
                    "status":
                        finding.status,
                    "severity":
                        finding.severity,
                    "discrepancy_type":
                        finding.discrepancy_type,
                    "message":
                        finding.message,
                    "evidence":
                        finding.evidence,
                },
                "control": {
                    "status":
                        decision.status,
                    "exception_code":
                        decision.exception_code,
                    "severity":
                        decision.severity.value,
                    "action":
                        decision.action.value,
                    "reason":
                        decision.reason,
                },
            }
        )

    return results