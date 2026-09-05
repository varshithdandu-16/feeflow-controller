from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Action(str, Enum):
    AUTO_CLEAR = "AUTO_CLEAR"
    MONITOR = "MONITOR"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ControlDecision:
    case_id: str
    status: str
    exception_code: str
    severity: Severity
    action: Action
    reason: str


EXCEPTION_RULES = {
    "GATEWAY_AMOUNT_MISMATCH": {
        "severity": Severity.HIGH,
        "action": Action.HUMAN_REVIEW,
        "reason":
            "Gateway amount differs from the expected "
            "transaction amount.",
    },
    "SETTLEMENT_AMOUNT_MISMATCH": {
        "severity": Severity.HIGH,
        "action": Action.HUMAN_REVIEW,
        "reason":
            "Settlement amount differs from the expected amount.",
    },
    "BANK_AMOUNT_MISMATCH": {
        "severity": Severity.CRITICAL,
        "action": Action.HUMAN_REVIEW,
        "reason":
            "Bank-posted amount does not match the "
            "expected settlement amount.",
    },
    "MISSING_GATEWAY_RECORD": {
        "severity": Severity.HIGH,
        "action": Action.HUMAN_REVIEW,
        "reason":
            "Expected gateway transaction record is missing.",
    },
    "MISSING_SETTLEMENT_RECORD": {
        "severity": Severity.HIGH,
        "action": Action.HUMAN_REVIEW,
        "reason":
            "Expected settlement record is missing.",
    },
    "MISSING_BANK_RECORD": {
        "severity": Severity.CRITICAL,
        "action": Action.HUMAN_REVIEW,
        "reason":
            "Expected bank posting record is missing.",
    },
    "INVALID_PROCESSOR_STATUS": {
        "severity": Severity.MEDIUM,
        "action": Action.HUMAN_REVIEW,
        "reason":
            "Processor status is outside the approved state set.",
    },
    "DUPLICATE_BANK_REFERENCE": {
        "severity": Severity.CRITICAL,
        "action": Action.BLOCK,
        "reason":
            "Duplicate bank reference detected across "
            "multiple transactions.",
    },
    "CURRENCY_MISMATCH": {
        "severity": Severity.MEDIUM,
        "action": Action.HUMAN_REVIEW,
        "reason":
            "Currency differs between financial sources.",
    },
    "GATEWAY_SETTLEMENT_ID_MISMATCH": {
        "severity": Severity.HIGH,
        "action": Action.HUMAN_REVIEW,
        "reason":
            "Settlement references a different "
            "gateway transaction.",
    },
    "SETTLEMENT_BANK_ID_MISMATCH": {
        "severity": Severity.CRITICAL,
        "action": Action.HUMAN_REVIEW,
        "reason":
            "Bank statement references a different "
            "settlement record.",
    },
}


def evaluate_case(
    case_id: str,
    status: str,
    exception_code: str,
) -> ControlDecision:
    normalized_status = str(status).upper()
    normalized_exception = str(
        exception_code or "NONE"
    ).upper()

    if (
        normalized_status in {
            "PASS",
            "MATCHED",
        }
        and normalized_exception == "NONE"
    ):
        return ControlDecision(
            case_id=case_id,
            status=normalized_status,
            exception_code="NONE",
            severity=Severity.LOW,
            action=Action.AUTO_CLEAR,
            reason=
                "All reconciliation controls passed.",
        )

    rule = EXCEPTION_RULES.get(
        normalized_exception
    )

    if rule is None:
        return ControlDecision(
            case_id=case_id,
            status=normalized_status,
            exception_code=normalized_exception,
            severity=Severity.HIGH,
            action=Action.HUMAN_REVIEW,
            reason=
                "Unknown exception requires "
                "manual investigation.",
        )

    return ControlDecision(
        case_id=case_id,
        status=normalized_status,
        exception_code=normalized_exception,
        severity=rule["severity"],
        action=rule["action"],
        reason=rule["reason"],
    )