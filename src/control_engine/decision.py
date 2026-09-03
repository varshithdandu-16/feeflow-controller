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


@dataclass
class ControlDecision:
    case_id: str
    status: str
    exception_code: str
    severity: Severity
    action: Action
    reason: str

RECONCILIATION_TO_CONTROL = {
    "MISSING_GATEWAY_TRANSACTION": "MISSING_GATEWAY_RECORD",
    "MISSING_SETTLEMENT": "MISSING_SETTLEMENT_RECORD",
    "GATEWAY_SETTLEMENT_AMOUNT_MISMATCH": "SETTLEMENT_AMOUNT_MISMATCH",
    "MISSING_BANK_SETTLEMENT": "MISSING_BANK_RECORD",
    "SETTLEMENT_BANK_AMOUNT_MISMATCH": "BANK_AMOUNT_MISMATCH",
    "CURRENCY_MISMATCH": "CURRENCY_MISMATCH",
}

EXCEPTION_RULES = {
    "GATEWAY_SETTLEMENT_AMOUNT_MISMATCH": {
    "severity": Severity.HIGH,
    "action": Action.HUMAN_REVIEW,
    "reason": "Gateway amount does not match settlement amount."
},

"SETTLEMENT_BANK_AMOUNT_MISMATCH": {
    "severity": Severity.CRITICAL,
    "action": Action.HUMAN_REVIEW,
    "reason": "Settlement amount does not match bank statement amount."
},

"CURRENCY_MISMATCH": {
    "severity": Severity.MEDIUM,
    "action": Action.HUMAN_REVIEW,
    "reason": "Currency differs between financial sources."
},

    "BANK_AMOUNT_MISMATCH": {
        "severity": Severity.CRITICAL,
        "action": Action.HUMAN_REVIEW,
        "reason": "Bank-posted amount does not match the expected settlement amount."
    },

    "MISSING_GATEWAY_RECORD": {
        "severity": Severity.HIGH,
        "action": Action.HUMAN_REVIEW,
        "reason": "Expected gateway transaction record is missing."
    },

    "MISSING_SETTLEMENT_RECORD": {
        "severity": Severity.HIGH,
        "action": Action.HUMAN_REVIEW,
        "reason": "Expected settlement record is missing."
    },

    "MISSING_BANK_RECORD": {
        "severity": Severity.CRITICAL,
        "action": Action.HUMAN_REVIEW,
        "reason": "Expected bank posting record is missing."
    },

    "DUPLICATE_BANK_REFERENCE": {
        "severity": Severity.CRITICAL,
        "action": Action.BLOCK,
        "reason": "Duplicate bank reference detected."
    },

    "INVALID_PROCESSOR_STATUS": {
        "severity": Severity.MEDIUM,
        "action": Action.HUMAN_REVIEW,
        "reason": "Processor status is outside the approved state set."
    },
}


def evaluate_case(
    case_id: str,
    status: str,
    exception_code: str
) -> ControlDecision:

    if status in {"PASS", "MATCHED"}:
        return ControlDecision(
            case_id=case_id,
            status=status,
            exception_code="NONE",
            severity=Severity.LOW,
            action=Action.AUTO_CLEAR,
            reason="All reconciliation controls passed."
        )

    rule = EXCEPTION_RULES.get(exception_code)

    if rule is None:
        return ControlDecision(
            case_id=case_id,
            status=status,
            exception_code=exception_code,
            severity=Severity.HIGH,
            action=Action.HUMAN_REVIEW,
            reason="Unknown exception requires manual investigation."
        )

    return ControlDecision(
        case_id=case_id,
        status=status,
        exception_code=exception_code,
        severity=rule["severity"],
        action=rule["action"],
        reason=rule["reason"]
    )