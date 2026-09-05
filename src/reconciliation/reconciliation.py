from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

APPROVED_PROCESSOR_STATUSES = {"CAPTURED"}


@dataclass(frozen=True)
class ReconciliationFinding:
    case_id: str
    status: str
    severity: str
    discrepancy_type: Optional[str]
    message: str
    evidence: dict

    def to_dict(self) -> dict:
        return asdict(self)


def load_source(filename: str) -> pd.DataFrame:
    """Load one financial source CSV."""

    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Required source not found: {path}"
        )

    return pd.read_csv(path)


def _base_evidence(
    fee_row: pd.Series,
    gateway_row: Optional[pd.Series],
    settlement_row: Optional[pd.Series],
    bank_row: Optional[pd.Series],
) -> dict:
    """
    Build a traceable evidence snapshot using the financial
    records available for this case.
    """

    evidence = {
        "case_id": str(fee_row["case_id"]),
        "fee_id": str(fee_row["fee_id"]),
        "student_id": str(fee_row["student_id"]),
        "merchant_id": str(fee_row["merchant_id"]),
        "currency": str(fee_row["currency"]),
        "fee_amount": float(fee_row["fee_amount"]),
        "fee_status": str(fee_row["fee_status"]),
        "customer_commitment_amount": float(
            fee_row["fee_amount"]
        ),
    }

    if gateway_row is not None:
        evidence.update(
            {
                "gateway_transaction_id": str(
                    gateway_row["gateway_transaction_id"]
                ),
                "gateway_fee_id": str(
                    gateway_row["fee_id"]
                ),
                "payment_method": str(
                    gateway_row["payment_method"]
                ),
                "gateway_amount": float(
                    gateway_row["gateway_amount"]
                ),
                "gateway_currency": str(
                    gateway_row["currency"]
                ),
                "processor_status": str(
                    gateway_row["processor_status"]
                ),
                "processor_processed_at": str(
                    gateway_row["processed_at"]
                ),
            }
        )

    if settlement_row is not None:
        evidence.update(
            {
                "settlement_id": str(
                    settlement_row["settlement_id"]
                ),
                "settlement_gateway_transaction_id": str(
                    settlement_row["gateway_transaction_id"]
                ),
                "settlement_amount": float(
                    settlement_row["settlement_amount"]
                ),
                "settlement_currency": str(
                    settlement_row["currency"]
                ),
                "settlement_status": str(
                    settlement_row["settlement_status"]
                ),
                "settlement_date": str(
                    settlement_row["settlement_date"]
                ),
            }
        )

    if bank_row is not None:
        evidence.update(
            {
                "bank_reference": str(
                    bank_row["bank_reference"]
                ),
                "bank_settlement_id": str(
                    bank_row["settlement_id"]
                ),
                "bank_amount": float(
                    bank_row["bank_amount"]
                ),
                "bank_currency": str(
                    bank_row["currency"]
                ),
                "bank_status": str(
                    bank_row["bank_status"]
                ),
                "bank_posted_at": str(
                    bank_row["bank_posted_at"]
                ),
                "merchant_observed_amount": float(
                    bank_row["bank_amount"]
                ),
            }
        )

    return evidence


def _finding(
    *,
    case_id: str,
    severity: str,
    discrepancy_type: str,
    message: str,
    evidence: dict,
) -> ReconciliationFinding:
    return ReconciliationFinding(
        case_id=case_id,
        status="EXCEPTION",
        severity=severity,
        discrepancy_type=discrepancy_type,
        message=message,
        evidence=evidence,
    )


def reconcile_case(
    fee_row: pd.Series,
    gateway_row: Optional[pd.Series],
    settlement_row: Optional[pd.Series],
    bank_row: Optional[pd.Series],
    duplicate_bank_references: Optional[
        dict[str, list[str]]
    ] = None,
) -> ReconciliationFinding:
    """
    Reconcile one transaction through:

        fee ledger
            -> payment gateway
            -> settlement
            -> bank statement
    """

    case_id = str(fee_row["case_id"])

    evidence = _base_evidence(
        fee_row=fee_row,
        gateway_row=gateway_row,
        settlement_row=settlement_row,
        bank_row=bank_row,
    )

    fee_amount = float(fee_row["fee_amount"])

    # =========================================================
    # STAGE 1 — FEE LEDGER -> PAYMENT GATEWAY
    # =========================================================

    if gateway_row is None:
        evidence.update(
            {
                "failed_stage": (
                    "FEE_LEDGER_TO_PAYMENT_GATEWAY"
                ),
                "failure_direction": (
                    "fee_ledger → payment_gateway"
                ),
                "source": (
                    "fee_ledger -> payment_gateway"
                ),
                "expected": {
                    "fee_ledger_record": True,
                    "gateway_record": True,
                    "amount": fee_amount,
                },
                "observed": {
                    "fee_ledger_record": True,
                    "gateway_record": False,
                    "amount": None,
                },
                "expected_amount": fee_amount,
                "observed_amount": None,
                "difference": None,
                "difference_abs": None,
                "expected_source": "fee_ledger",
                "observed_source": "payment_gateway",
            }
        )

        return _finding(
            case_id=case_id,
            severity="HIGH",
            discrepancy_type="MISSING_GATEWAY_RECORD",
            message=(
                "The fee-ledger commitment has no matching "
                "payment-gateway transaction."
            ),
            evidence=evidence,
        )

    gateway_amount = float(
        gateway_row["gateway_amount"]
    )

    if fee_amount != gateway_amount:
        difference = abs(
            gateway_amount - fee_amount
        )

        evidence.update(
            {
                "failed_stage": (
                    "FEE_LEDGER_TO_PAYMENT_GATEWAY"
                ),
                "failure_direction": (
                    "fee_ledger → payment_gateway"
                ),
                "source": (
                    "fee_ledger -> payment_gateway"
                ),
                "expected": {
                    "fee_ledger_record": True,
                    "gateway_record": True,
                    "amount": fee_amount,
                },
                "observed": {
                    "fee_ledger_record": True,
                    "gateway_record": True,
                    "amount": gateway_amount,
                },
                "expected_amount": fee_amount,
                "observed_amount": gateway_amount,
                "difference": difference,
                "difference_abs": difference,
                "expected_source": "fee_ledger",
                "observed_source": "payment_gateway",
            }
        )

        return _finding(
            case_id=case_id,
            severity="HIGH",
            discrepancy_type="GATEWAY_AMOUNT_MISMATCH",
            message=(
                "Gateway amount does not match the expected "
                "fee-ledger amount."
            ),
            evidence=evidence,
        )

    # =========================================================
    # STAGE 2 — PAYMENT GATEWAY PROCESSOR STATUS
    # =========================================================

    processor_status = str(
        gateway_row["processor_status"]
    ).upper()

    if processor_status not in APPROVED_PROCESSOR_STATUSES:
        evidence.update(
            {
                "failed_stage": (
                    "PAYMENT_GATEWAY_PROCESSOR_STATUS"
                ),
                "failure_direction": (
                    "payment_gateway → processor_state"
                ),
                "source": (
                    "payment_gateway.processor_status "
                    "-> approved_processor_status"
                ),
                "expected": {
                    "processor_status": "CAPTURED",
                },
                "observed": {
                    "processor_status": processor_status,
                },
                "observed_status": processor_status,
                "approved_processor_statuses": sorted(
                    APPROVED_PROCESSOR_STATUSES
                ),
            }
        )

        return _finding(
            case_id=case_id,
            severity="MEDIUM",
            discrepancy_type="INVALID_PROCESSOR_STATUS",
            message=(
                f"Processor status '{processor_status}' "
                "is outside the approved captured state."
            ),
            evidence=evidence,
        )

    # =========================================================
    # STAGE 3 — PAYMENT GATEWAY -> SETTLEMENT
    # =========================================================

    if settlement_row is None:
        evidence.update(
            {
                "failed_stage": (
                    "PAYMENT_GATEWAY_TO_SETTLEMENT"
                ),
                "failure_direction": (
                    "payment_gateway → settlement"
                ),
                "source": (
                    "payment_gateway -> settlement"
                ),
                "expected": {
                    "payment_gateway_record": True,
                    "settlement_record": True,
                    "amount": gateway_amount,
                },
                "observed": {
                    "payment_gateway_record": True,
                    "settlement_record": False,
                    "amount": None,
                },
                "expected_amount": gateway_amount,
                "observed_amount": None,
                "difference": None,
                "difference_abs": None,
                "expected_source": "payment_gateway",
                "observed_source": "settlement",
            }
        )

        return _finding(
            case_id=case_id,
            severity="HIGH",
            discrepancy_type="MISSING_SETTLEMENT_RECORD",
            message=(
                "The captured gateway transaction has no "
                "matching settlement record."
            ),
            evidence=evidence,
        )

    # =========================================================
    # STAGE 4 — GATEWAY -> SETTLEMENT IDENTITY
    # =========================================================

    gateway_transaction_id = str(
        gateway_row["gateway_transaction_id"]
    )

    settlement_gateway_transaction_id = str(
        settlement_row["gateway_transaction_id"]
    )

    if (
        gateway_transaction_id
        != settlement_gateway_transaction_id
    ):
        evidence.update(
            {
                "failed_stage": (
                    "PAYMENT_GATEWAY_TO_SETTLEMENT_IDENTITY"
                ),
                "failure_direction": (
                    "payment_gateway → settlement"
                ),
                "source": (
                    "payment_gateway -> settlement"
                ),
                "expected": {
                    "gateway_transaction_id": (
                        gateway_transaction_id
                    ),
                },
                "observed": {
                    "gateway_transaction_id": (
                        settlement_gateway_transaction_id
                    ),
                },
                "expected_gateway_transaction_id": (
                    gateway_transaction_id
                ),
                "observed_settlement_gateway_transaction_id": (
                    settlement_gateway_transaction_id
                ),
            }
        )

        return _finding(
            case_id=case_id,
            severity="HIGH",
            discrepancy_type="GATEWAY_SETTLEMENT_ID_MISMATCH",
            message=(
                "Settlement references a different "
                "gateway transaction."
            ),
            evidence=evidence,
        )

    # =========================================================
    # STAGE 5 — EXPECTED AMOUNT -> SETTLEMENT
    # =========================================================

    settlement_amount = float(
        settlement_row["settlement_amount"]
    )

    if fee_amount != settlement_amount:
        difference = abs(
            settlement_amount - fee_amount
        )

        evidence.update(
            {
                "failed_stage": (
                    "EXPECTED_AMOUNT_TO_SETTLEMENT"
                ),
                "failure_direction": (
                    "fee_ledger → settlement"
                ),
                "source": (
                    "fee_ledger -> settlement"
                ),
                "expected": {
                    "fee_ledger_record": True,
                    "settlement_record": True,
                    "amount": fee_amount,
                },
                "observed": {
                    "fee_ledger_record": True,
                    "settlement_record": True,
                    "amount": settlement_amount,
                },
                "expected_amount": fee_amount,
                "observed_amount": settlement_amount,
                "difference": difference,
                "difference_abs": difference,
                "expected_source": "fee_ledger",
                "observed_source": "settlement",
            }
        )

        return _finding(
            case_id=case_id,
            severity="HIGH",
            discrepancy_type="SETTLEMENT_AMOUNT_MISMATCH",
            message=(
                "Settlement amount does not match "
                "the expected transaction amount."
            ),
            evidence=evidence,
        )

    # =========================================================
    # STAGE 6 — SETTLEMENT -> BANK
    # =========================================================

    if bank_row is None:
        evidence.update(
            {
                "failed_stage": (
                    "SETTLEMENT_TO_BANK"
                ),
                "failure_direction": (
                    "settlement → bank_statement"
                ),
                "source": (
                    "settlement -> bank_statement"
                ),
                "expected": {
                    "settlement_record": True,
                    "bank_record": True,
                    "amount": settlement_amount,
                },
                "observed": {
                    "settlement_record": True,
                    "bank_record": False,
                    "amount": None,
                },
                "expected_amount": settlement_amount,
                "observed_amount": None,
                "difference": None,
                "difference_abs": None,
                "expected_source": "settlement",
                "observed_source": "bank_statement",
            }
        )

        return _finding(
            case_id=case_id,
            severity="CRITICAL",
            discrepancy_type="MISSING_BANK_RECORD",
            message=(
                "A valid settlement exists, but no matching "
                "bank statement entry was found."
            ),
            evidence=evidence,
        )

    # =========================================================
    # STAGE 7 — SETTLEMENT -> BANK IDENTITY
    # =========================================================

    settlement_id = str(
        settlement_row["settlement_id"]
    )

    bank_settlement_id = str(
        bank_row["settlement_id"]
    )

    if settlement_id != bank_settlement_id:
        evidence.update(
            {
                "failed_stage": (
                    "SETTLEMENT_TO_BANK_IDENTITY"
                ),
                "failure_direction": (
                    "settlement → bank_statement"
                ),
                "source": (
                    "settlement -> bank_statement"
                ),
                "expected": {
                    "settlement_id": settlement_id,
                },
                "observed": {
                    "settlement_id": bank_settlement_id,
                },
                "expected_settlement_id": settlement_id,
                "observed_bank_settlement_id": (
                    bank_settlement_id
                ),
            }
        )

        return _finding(
            case_id=case_id,
            severity="CRITICAL",
            discrepancy_type="SETTLEMENT_BANK_ID_MISMATCH",
            message=(
                "Bank statement references a different "
                "settlement record."
            ),
            evidence=evidence,
        )

    # =========================================================
    # STAGE 8 — SETTLEMENT -> BANK AMOUNT
    # =========================================================

    bank_amount = float(
        bank_row["bank_amount"]
    )

    if settlement_amount != bank_amount:
        difference = abs(
            bank_amount - settlement_amount
        )

        evidence.update(
            {
                "failed_stage": (
                    "SETTLEMENT_TO_BANK_AMOUNT"
                ),
                "failure_direction": (
                    "settlement → bank_statement"
                ),
                "source": (
                    "settlement -> bank_statement"
                ),
                "expected": {
                    "settlement_record": True,
                    "bank_record": True,
                    "amount": settlement_amount,
                },
                "observed": {
                    "settlement_record": True,
                    "bank_record": True,
                    "amount": bank_amount,
                },
                "expected_amount": settlement_amount,
                "observed_amount": bank_amount,
                "difference": difference,
                "difference_abs": difference,
                "expected_source": "settlement",
                "observed_source": "bank_statement",
            }
        )

        return _finding(
            case_id=case_id,
            severity="CRITICAL",
            discrepancy_type="BANK_AMOUNT_MISMATCH",
            message=(
                "Bank-posted amount does not match "
                "the expected settlement amount."
            ),
            evidence=evidence,
        )

    # =========================================================
    # STAGE 9 — DUPLICATE BANK REFERENCE
    # =========================================================

    bank_reference = str(
        bank_row["bank_reference"]
    )

    if duplicate_bank_references:
        duplicate_cases = (
            duplicate_bank_references.get(
                bank_reference,
                [],
            )
        )

        if len(duplicate_cases) > 1:
            evidence.update(
                {
                    "failed_stage": (
                        "BANK_REFERENCE_UNIQUENESS"
                    ),
                    "failure_direction": (
                        "bank_statement.bank_reference"
                    ),
                    "source": (
                        "bank_statement.bank_reference"
                    ),
                    "expected": {
                        "unique_bank_reference": True,
                    },
                    "observed": {
                        "unique_bank_reference": False,
                    },
                    "duplicate": True,
                    "duplicate_bank_reference": (
                        bank_reference
                    ),
                    "duplicate_cases": duplicate_cases,
                }
            )

            return _finding(
                case_id=case_id,
                severity="CRITICAL",
                discrepancy_type=(
                    "DUPLICATE_BANK_REFERENCE"
                ),
                message=(
                    "The bank reference is reused across "
                    "multiple transactions and cannot be "
                    "treated as unique evidence."
                ),
                evidence=evidence,
            )

    # =========================================================
    # STAGE 10 — CURRENCY CONSISTENCY
    # =========================================================

    currencies = {
        str(fee_row["currency"]),
        str(gateway_row["currency"]),
        str(settlement_row["currency"]),
        str(bank_row["currency"]),
    }

    if len(currencies) != 1:
        evidence.update(
            {
                "failed_stage": (
                    "CURRENCY_CONSISTENCY"
                ),
                "failure_direction": (
                    "financial_sources"
                ),
                "source": (
                    "financial_sources.currency"
                ),
                "expected": {
                    "single_currency": True,
                },
                "observed": {
                    "single_currency": False,
                },
                "currencies": sorted(currencies),
            }
        )

        return _finding(
            case_id=case_id,
            severity="MEDIUM",
            discrepancy_type="CURRENCY_MISMATCH",
            message=(
                "Currency differs between financial sources."
            ),
            evidence=evidence,
        )

    # =========================================================
    # FULLY RECONCILED
    # =========================================================

    evidence.update(
        {
            "failed_stage": None,
            "failure_direction": None,
            "source": (
                "fee_ledger -> payment_gateway -> "
                "settlement -> bank_statement"
            ),
            "expected": {
                "fee_ledger_record": True,
                "gateway_record": True,
                "settlement_record": True,
                "bank_record": True,
                "amount": fee_amount,
            },
            "observed": {
                "fee_ledger_record": True,
                "gateway_record": True,
                "settlement_record": True,
                "bank_record": True,
                "amount": bank_amount,
            },
            "expected_amount": fee_amount,
            "observed_amount": bank_amount,
            "difference": 0.0,
            "difference_abs": 0.0,
            "expected_source": "fee_ledger",
            "observed_source": "bank_statement",
            "duplicate": False,
        }
    )

    return ReconciliationFinding(
        case_id=case_id,
        status="MATCHED",
        severity="NONE",
        discrepancy_type=None,
        message=(
            "All required financial records reconciled successfully."
        ),
        evidence=evidence,
    )


def reconcile_all() -> list[ReconciliationFinding]:
    """
    Reconcile every fee-ledger case against all available
    financial sources.
    """

    fee_ledger = load_source("fee_ledger.csv")
    gateway = load_source("payment_gateway.csv")
    settlement = load_source("settlement.csv")
    bank = load_source("bank_statement.csv")

    gateway_by_case = {
        str(row["case_id"]): row
        for _, row in gateway.iterrows()
    }

    settlement_by_case = {
        str(row["case_id"]): row
        for _, row in settlement.iterrows()
    }

    bank_by_case = {
        str(row["case_id"]): row
        for _, row in bank.iterrows()
    }

    duplicate_bank_references: dict[
        str,
        list[str],
    ] = {}

    for _, row in bank.iterrows():
        reference = str(
            row["bank_reference"]
        )

        duplicate_bank_references.setdefault(
            reference,
            [],
        ).append(
            str(row["case_id"])
        )

    findings: list[ReconciliationFinding] = []

    for _, fee_row in fee_ledger.iterrows():
        case_id = str(
            fee_row["case_id"]
        )

        finding = reconcile_case(
            fee_row=fee_row,
            gateway_row=gateway_by_case.get(case_id),
            settlement_row=settlement_by_case.get(case_id),
            bank_row=bank_by_case.get(case_id),
            duplicate_bank_references=(
                duplicate_bank_references
            ),
        )

        findings.append(finding)

    return findings


def main() -> None:
    findings = reconcile_all()

    matched = sum(
        finding.status == "MATCHED"
        for finding in findings
    )

    exceptions = len(findings) - matched

    print()
    print("FeeFlow Controller — Reconciliation")
    print("=" * 50)
    print(
        f"Cases processed : {len(findings)}"
    )
    print(
        f"Matched         : {matched}"
    )
    print(
        f"Exceptions      : {exceptions}"
    )

    print()
    print("Findings:")
    print("-" * 50)

    for finding in findings:
        print(
            f"{finding.case_id} | "
            f"{finding.status} | "
            f"{finding.severity} | "
            f"{finding.discrepancy_type or 'NONE'}"
        )


if __name__ == "__main__":
    main()