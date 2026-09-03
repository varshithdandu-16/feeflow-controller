from src.control_engine.decision import evaluate_case
from src.reconciliation.reconciliation import reconcile_all
from src.reconciliation.schema import validate_all_sources
def run_control_pipeline() -> list[dict]:
    """
    Execute the complete deterministic FeeFlow control pipeline.

    Pipeline:
        1. Validate all financial source schemas.
        2. Reconcile the financial records.
        3. Evaluate every reconciliation finding using the
           deterministic control engine.
        4. Return structured findings and control decisions.

    This function performs no financial side effects.
    It only validates, reconciles, evaluates, and reports.
    """

    # ------------------------------------------------------------------
    # STEP 1: Validate source data
    # ------------------------------------------------------------------
    #
    # Fail immediately if the financial input data is structurally
    # invalid. We do not allow reconciliation to continue with
    # malformed source data.
    #
    validate_all_sources()

    # ------------------------------------------------------------------
    # STEP 2: Reconcile financial records
    # ------------------------------------------------------------------

    findings = reconcile_all()

    # ------------------------------------------------------------------
    # STEP 3: Apply deterministic control decisions
    # ------------------------------------------------------------------

    results = []

    for finding in findings:
        decision = evaluate_case(
            case_id=finding.case_id,
            status=finding.status,
            exception_code=finding.discrepancy_type or "NONE",
        )

        results.append(
            {
                "case_id": finding.case_id,

                "reconciliation": {
                    "status": finding.status,
                    "severity": finding.severity,
                    "discrepancy_type": finding.discrepancy_type,
                    "message": finding.message,
                    "evidence": finding.evidence,
                },

                "control": {
                    "status": decision.status,
                    "exception_code": decision.exception_code,
                    "severity": decision.severity.value,
                    "action": decision.action.value,
                    "reason": decision.reason,
                },
            }
        )

    return results