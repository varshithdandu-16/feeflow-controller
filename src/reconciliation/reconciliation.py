from dataclasses import dataclass, asdict
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


def reconcile_case(
    fee_row: pd.Series,
    gateway_row: Optional[pd.Series],
    settlement_row: Optional[pd.Series],
    bank_row: Optional[pd.Series],
) -> ReconciliationFinding:

    case_id = str(fee_row["case_id"])

    # ---------------------------------------------------------
    # 1. Missing payment gateway record
    # ---------------------------------------------------------
    if gateway_row is None:
        return ReconciliationFinding(
            case_id=case_id,
            status="EXCEPTION",
            severity="HIGH",
            discrepancy_type="MISSING_GATEWAY_RECORD",
            message="Fee ledger record has no matching payment gateway transaction.",
            evidence={
                "fee_id": fee_row["fee_id"],
            },
        )

    # ---------------------------------------------------------
    # 2. Gateway → Settlement identity check
    # ---------------------------------------------------------
    gateway_transaction_id = str(gateway_row["gateway_transaction_id"])

    if settlement_row is None:
        return ReconciliationFinding(
            case_id=case_id,
            status="EXCEPTION",
            severity="HIGH",
            discrepancy_type="MISSING_SETTLEMENT_RECORD",
            message="Payment gateway transaction has no matching settlement record.",
            evidence={
                "gateway_transaction_id": gateway_transaction_id,
                "gateway_amount": gateway_row["gateway_amount"],
            },
        )

    # ---------------------------------------------------------
    # 3. Gateway → Settlement amount check
    # ---------------------------------------------------------
    gateway_amount = float(gateway_row["gateway_amount"])
    settlement_amount = float(settlement_row["settlement_amount"])

    if gateway_amount != settlement_amount:
        return ReconciliationFinding(
            case_id=case_id,
            status="EXCEPTION",
            severity="HIGH",
            discrepancy_type="GATEWAY_SETTLEMENT_AMOUNT_MISMATCH",
            message="Gateway amount does not match settlement amount.",
            evidence={
                "gateway_transaction_id": gateway_transaction_id,
                "gateway_amount": gateway_amount,
                "settlement_amount": settlement_amount,
                "difference": settlement_amount - gateway_amount,
            },
        )

    # ---------------------------------------------------------
    # 4. Missing bank record
    # ---------------------------------------------------------
    if bank_row is None:
        return ReconciliationFinding(
            case_id=case_id,
            status="EXCEPTION",
            severity="HIGH",
            discrepancy_type="MISSING_BANK_RECORD",
            message="Settlement record has no matching bank statement entry.",
            evidence={
                "settlement_id": settlement_row["settlement_id"],
                "settlement_amount": settlement_amount,
            },
        )

    # ---------------------------------------------------------
    # 5. Settlement → Bank amount check
    # ---------------------------------------------------------
    bank_amount = float(bank_row["bank_amount"])

    if settlement_amount != bank_amount:
        return ReconciliationFinding(
            case_id=case_id,
            status="EXCEPTION",
            severity="HIGH",
            discrepancy_type="SETTLEMENT_BANK_AMOUNT_MISMATCH",
            message="Settlement amount does not match bank statement amount.",
            evidence={
                "settlement_id": settlement_row["settlement_id"],
                "settlement_amount": settlement_amount,
                "bank_amount": bank_amount,
                "difference": bank_amount - settlement_amount,
            },
        )

    # ---------------------------------------------------------
    # 6. Currency consistency
    # ---------------------------------------------------------
    currencies = {
        str(fee_row["currency"]),
        str(gateway_row["currency"]),
        str(settlement_row["currency"]),
        str(bank_row["currency"]),
    }

    if len(currencies) != 1:
        return ReconciliationFinding(
            case_id=case_id,
            status="EXCEPTION",
            severity="MEDIUM",
            discrepancy_type="CURRENCY_MISMATCH",
            message="Currency differs between financial sources.",
            evidence={
                "currencies": sorted(currencies),
            },
        )

    # ---------------------------------------------------------
    # 7. Fully reconciled
    # ---------------------------------------------------------
    return ReconciliationFinding(
        case_id=case_id,
        status="MATCHED",
        severity="NONE",
        discrepancy_type=None,
        message="All available financial records reconciled successfully.",
        evidence={
            "gateway_transaction_id": gateway_transaction_id,
            "settlement_id": settlement_row["settlement_id"],
            "amount": settlement_amount,
            "currency": settlement_row["currency"],
        },
    )


def reconcile_all() -> list[ReconciliationFinding]:
    """Reconcile all cases across the four financial sources."""

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

    findings = []

    for _, fee_row in fee_ledger.iterrows():
        case_id = str(fee_row["case_id"])

        finding = reconcile_case(
            fee_row=fee_row,
            gateway_row=gateway_by_case.get(case_id),
            settlement_row=settlement_by_case.get(case_id),
            bank_row=bank_by_case.get(case_id),
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