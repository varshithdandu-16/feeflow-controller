from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


@dataclass
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
    """Load one validated financial source."""
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Required source not found: {path}")

    return pd.read_csv(path)


def _exception(
    case_id: str,
    discrepancy_type: str,
    message: str,
    evidence: dict,
    severity: str = "HIGH",
) -> ReconciliationFinding:
    """Create a consistent, evidence-rich reconciliation exception."""
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
    duplicate_bank_references: Optional[set[str]] = None,
) -> ReconciliationFinding:
    """
    Reconcile one fee transaction across all available sources.

    The fee ledger is the expected transaction amount. Each downstream
    source is checked independently so that one mismatch cannot hide
    another. Evidence identifies the source pair, expected/observed
    values, identifiers, and exact difference for reviewer remediation.
    """

    case_id = str(fee_row["case_id"])
    fee_amount = float(fee_row["fee_amount"])
    fee_currency = str(fee_row["currency"])
    fee_id = str(fee_row["fee_id"])

    # 1. Gateway presence
    if gateway_row is None:
        return _exception(
            case_id=case_id,
            discrepancy_type="MISSING_GATEWAY_RECORD",
            message="Fee ledger record has no matching payment gateway transaction.",
            evidence={
                "source": "fee_ledger -> payment_gateway",
                "fee_id": fee_id,
                "expected": {"gateway_record": True},
                "observed": {"gateway_record": False},
            },
        )

    gateway_transaction_id = str(gateway_row["gateway_transaction_id"])
    gateway_fee_id = str(gateway_row["fee_id"])
    gateway_amount = float(gateway_row["gateway_amount"])
    gateway_currency = str(gateway_row["currency"])
    processor_status = str(gateway_row["processor_status"]).upper()

    # 2. Gateway identity and amount against the original fee ledger
    if gateway_fee_id != fee_id:
        return _exception(
            case_id=case_id,
            discrepancy_type="GATEWAY_FEE_ID_MISMATCH",
            message="Gateway transaction is linked to a different fee record.",
            evidence={
                "source": "fee_ledger -> payment_gateway",
                "fee_id": fee_id,
                "gateway_transaction_id": gateway_transaction_id,
                "expected": {"fee_id": fee_id},
                "observed": {"fee_id": gateway_fee_id},
            },
        )

    if gateway_amount != fee_amount:
        return _exception(
            case_id=case_id,
            discrepancy_type="GATEWAY_AMOUNT_MISMATCH",
            message="Gateway amount does not match the expected fee amount.",
            evidence={
                "source": "fee_ledger -> payment_gateway",
                "fee_id": fee_id,
                "gateway_transaction_id": gateway_transaction_id,
                "currency": fee_currency,
                "expected_amount": fee_amount,
                "observed_amount": gateway_amount,
                "difference": fee_amount - gateway_amount,
            },
        )

    # 3. Processor state validation
    if processor_status not in {"AUTHORIZED", "CAPTURED"}:
        return _exception(
            case_id=case_id,
            discrepancy_type="INVALID_PROCESSOR_STATUS",
            message="Processor status is outside the approved payment state set.",
            evidence={
                "source": "payment_gateway",
                "gateway_transaction_id": gateway_transaction_id,
                "expected_statuses": ["AUTHORIZED", "CAPTURED"],
                "observed_status": processor_status,
            },
            severity="MEDIUM",
        )

    # 4. Settlement presence
    if settlement_row is None:
        return _exception(
            case_id=case_id,
            discrepancy_type="MISSING_SETTLEMENT_RECORD",
            message="Payment gateway transaction has no matching settlement record.",
            evidence={
                "source": "payment_gateway -> settlement",
                "gateway_transaction_id": gateway_transaction_id,
                "expected": {"settlement_record": True},
                "observed": {"settlement_record": False},
            },
        )

    settlement_id = str(settlement_row["settlement_id"])
    settlement_gateway_id = str(settlement_row["gateway_transaction_id"])
    settlement_amount = float(settlement_row["settlement_amount"])
    settlement_currency = str(settlement_row["currency"])

    # 5. Settlement identity and amount against the gateway/expected fee
    if settlement_gateway_id != gateway_transaction_id:
        return _exception(
            case_id=case_id,
            discrepancy_type="SETTLEMENT_GATEWAY_ID_MISMATCH",
            message="Settlement record references a different gateway transaction.",
            evidence={
                "source": "payment_gateway -> settlement",
                "gateway_transaction_id": gateway_transaction_id,
                "settlement_id": settlement_id,
                "expected": {"gateway_transaction_id": gateway_transaction_id},
                "observed": {"gateway_transaction_id": settlement_gateway_id},
            },
        )

    if settlement_amount != fee_amount:
        return _exception(
            case_id=case_id,
            discrepancy_type="SETTLEMENT_AMOUNT_MISMATCH",
            message="Settlement amount does not match the expected transaction amount.",
            evidence={
                "source": "fee_ledger -> settlement",
                "fee_id": fee_id,
                "gateway_transaction_id": gateway_transaction_id,
                "settlement_id": settlement_id,
                "currency": fee_currency,
                "expected_amount": fee_amount,
                "observed_amount": settlement_amount,
                "difference": fee_amount - settlement_amount,
            },
        )

    # 6. Bank presence
    if bank_row is None:
        return _exception(
            case_id=case_id,
            discrepancy_type="MISSING_BANK_RECORD",
            message="Settlement record has no matching bank statement entry.",
            evidence={
                "source": "settlement -> bank_statement",
                "settlement_id": settlement_id,
                "settlement_amount": settlement_amount,
                "expected": {"bank_record": True},
                "observed": {"bank_record": False},
            },
            severity="CRITICAL",
        )

    bank_reference = str(bank_row["bank_reference"])
    bank_settlement_id = str(bank_row["settlement_id"])
    bank_amount = float(bank_row["bank_amount"])
    bank_currency = str(bank_row["currency"])

    # 7. Bank identity
    if bank_settlement_id != settlement_id:
        return _exception(
            case_id=case_id,
            discrepancy_type="BANK_SETTLEMENT_ID_MISMATCH",
            message="Bank statement entry references a different settlement record.",
            evidence={
                "source": "settlement -> bank_statement",
                "settlement_id": settlement_id,
                "bank_reference": bank_reference,
                "expected": {"settlement_id": settlement_id},
                "observed": {"settlement_id": bank_settlement_id},
            },
            severity="CRITICAL",
        )

    # 8. Bank amount against the settled amount
    if bank_amount != settlement_amount:
        return _exception(
            case_id=case_id,
            discrepancy_type="BANK_AMOUNT_MISMATCH",
            message="Bank-posted amount does not match the expected settlement amount.",
            evidence={
                "source": "settlement -> bank_statement",
                "settlement_id": settlement_id,
                "bank_reference": bank_reference,
                "currency": settlement_currency,
                "expected_amount": settlement_amount,
                "observed_amount": bank_amount,
                "difference": settlement_amount - bank_amount,
            },
            severity="CRITICAL",
        )

    # 9. Duplicate bank reference detection is global, not row-local.
    if (
        duplicate_bank_references is not None
        and bank_reference in duplicate_bank_references
    ):
        return _exception(
            case_id=case_id,
            discrepancy_type="DUPLICATE_BANK_REFERENCE",
            message="Bank reference is reused across multiple transactions.",
            evidence={
                "source": "bank_statement",
                "bank_reference": bank_reference,
                "settlement_id": settlement_id,
                "duplicate": True,
                "expected": {"unique_bank_reference": True},
                "observed": {"unique_bank_reference": False},
            },
            severity="CRITICAL",
        )

    # 10. Currency consistency across every source
    currencies = {
        fee_currency,
        gateway_currency,
        settlement_currency,
        bank_currency,
    }

    if len(currencies) != 1:
        return _exception(
            case_id=case_id,
            discrepancy_type="CURRENCY_MISMATCH",
            message="Currency differs between financial sources.",
            evidence={
                "source": "fee_ledger -> payment_gateway -> settlement -> bank_statement",
                "fee_currency": fee_currency,
                "gateway_currency": gateway_currency,
                "settlement_currency": settlement_currency,
                "bank_currency": bank_currency,
                "currencies": sorted(currencies),
            },
            severity="MEDIUM",
        )

    # 11. Fully reconciled
    return ReconciliationFinding(
        case_id=case_id,
        status="MATCHED",
        severity="NONE",
        discrepancy_type=None,
        message="All available financial records reconciled successfully.",
        evidence={
            "source": "fee_ledger -> payment_gateway -> settlement -> bank_statement",
            "fee_id": fee_id,
            "gateway_transaction_id": gateway_transaction_id,
            "settlement_id": settlement_id,
            "bank_reference": bank_reference,
            "amount": fee_amount,
            "currency": fee_currency,
            "processor_status": processor_status,
        },
    )


def reconcile_all() -> list[ReconciliationFinding]:
    """Reconcile all fee-ledger cases across the four financial sources."""

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

    duplicate_bank_references = set(
        bank.loc[
            bank["bank_reference"].duplicated(keep=False),
            "bank_reference",
        ]
        .astype(str)
        .tolist()
    )

    findings = []

    for _, fee_row in fee_ledger.iterrows():
        case_id = str(fee_row["case_id"])
        findings.append(
            reconcile_case(
                fee_row=fee_row,
                gateway_row=gateway_by_case.get(case_id),
                settlement_row=settlement_by_case.get(case_id),
                bank_row=bank_by_case.get(case_id),
                duplicate_bank_references=duplicate_bank_references,
            )
        )

    return findings


def main() -> None:
    findings = reconcile_all()

    matched = sum(finding.status == "MATCHED" for finding in findings)
    exceptions = len(findings) - matched

    print("\nFeeFlow Controller — Reconciliation")
    print("=" * 45)
    print(f"Cases processed : {len(findings)}")
    print(f"Matched         : {matched}")
    print(f"Exceptions      : {exceptions}")

    print("\nFindings:")
    print("-" * 45)

    for finding in findings:
        print(
            f"{finding.case_id} | "
            f"{finding.status} | "
            f"{finding.severity} | "
            f"{finding.discrepancy_type or 'NONE'}"
        )


if __name__ == "__main__":
    main()
