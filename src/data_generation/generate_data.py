from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 42
TOTAL_CASES = 70

fake = Faker()
Faker.seed(SEED)
rng = np.random.default_rng(SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
EXPECTED_DIR = PROJECT_ROOT / "data" / "expected"


# ============================================================
# CONTROLLED SCENARIO PLAN
# ============================================================

SCENARIOS = (
    ["MATCHED"] * 40
    + ["GATEWAY_AMOUNT_MISMATCH"] * 5
    + ["SETTLEMENT_AMOUNT_MISMATCH"] * 5
    + ["BANK_AMOUNT_MISMATCH"] * 5
    + ["MISSING_GATEWAY"] * 4
    + ["MISSING_SETTLEMENT"] * 3
    + ["MISSING_BANK"] * 3
    + ["INVALID_STATUS"] * 2
    + ["DUPLICATE_BANK_REFERENCE"] * 3
)

assert len(SCENARIOS) == TOTAL_CASES


# ============================================================
# ALLOWED VALUES
# ============================================================

CURRENCIES = ["INR"]

PAYMENT_METHODS = [
    "UPI",
    "CARD",
    "NET_BANKING",
]

FEE_STATUSES = [
    "INITIATED",
    "PAYMENT_PENDING",
    "PAID",
]

PROCESSOR_STATUSES = [
    "AUTHORIZED",
    "CAPTURED",
    "FAILED",
]

SETTLEMENT_STATUSES = [
    "PENDING",
    "SETTLED",
]

BANK_STATUSES = [
    "CREDITED",
    "POSTED",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def random_amount():
    """Generate a realistic education-fee amount."""
    return int(rng.choice([
        15000,
        25000,
        30000,
        45000,
        50000,
        75000,
        100000,
        125000,
    ]))


def make_timestamp(case_number):
    """Create deterministic timestamps for each case."""
    base_time = datetime(2026, 1, 1, 9, 0, 0)
    return base_time + timedelta(hours=case_number * 2)


# ============================================================
# CASE GENERATION
# ============================================================

def generate_case(case_number, scenario):
    """
    Generate one complete financial transaction lifecycle.

    The function creates the Fee Ledger first and then derives
    the dependent records from it.
    """

    case_id = f"FF-{case_number:04d}"
    fee_id = f"FEE-{case_number:04d}"
    gateway_id = f"GW-{case_number:04d}"
    settlement_id = f"SET-{case_number:04d}"
    bank_reference = f"BANK-{case_number:04d}"

    student_id = f"STU-{case_number:04d}"
    merchant_id = f"MER-{(case_number % 5) + 1:03d}"

    amount = random_amount()
    currency = "INR"
    payment_method = rng.choice(PAYMENT_METHODS)
    timestamp = make_timestamp(case_number)

    # --------------------------------------------------------
    # Base records
    # --------------------------------------------------------

    fee_record = {
        "case_id": case_id,
        "fee_id": fee_id,
        "student_id": student_id,
        "merchant_id": merchant_id,
        "currency": currency,
        "fee_amount": amount,
        "created_at": timestamp.isoformat(),
        "fee_status": "PAID",
    }

    gateway_record = {
        "case_id": case_id,
        "gateway_transaction_id": gateway_id,
        "fee_id": fee_id,
        "payment_method": payment_method,
        "gateway_amount": amount,
        "currency": currency,
        "processor_status": "CAPTURED",
        "processed_at": (timestamp + timedelta(minutes=5)).isoformat(),
    }

    settlement_record = {
        "case_id": case_id,
        "settlement_id": settlement_id,
        "gateway_transaction_id": gateway_id,
        "settlement_amount": amount,
        "currency": currency,
        "settlement_status": "SETTLED",
        "settlement_date": (
            timestamp + timedelta(hours=4)
        ).isoformat(),
    }

    bank_record = {
        "case_id": case_id,
        "bank_reference": bank_reference,
        "settlement_id": settlement_id,
        "bank_amount": amount,
        "currency": currency,
        "bank_status": "CREDITED",
        "bank_posted_at": (
            timestamp + timedelta(hours=6)
        ).isoformat(),
    }

    # --------------------------------------------------------
    # Ground truth
    # --------------------------------------------------------

    expected_status = "PASS"
    exception_code = "NONE"
    expected_action = "NO_ACTION"
    expected_difference = 0

    # --------------------------------------------------------
    # Controlled exceptions
    # --------------------------------------------------------

    if scenario == "GATEWAY_AMOUNT_MISMATCH":
        gateway_record["gateway_amount"] = amount - 500

        expected_status = "EXCEPTION"
        exception_code = "GATEWAY_AMOUNT_MISMATCH"
        expected_action = "HUMAN_REVIEW"
        expected_difference = 500

    elif scenario == "SETTLEMENT_AMOUNT_MISMATCH":
        settlement_record["settlement_amount"] = amount - 500

        expected_status = "EXCEPTION"
        exception_code = "SETTLEMENT_AMOUNT_MISMATCH"
        expected_action = "HUMAN_REVIEW"
        expected_difference = 500

    elif scenario == "BANK_AMOUNT_MISMATCH":
        bank_record["bank_amount"] = amount - 1000

        expected_status = "EXCEPTION"
        exception_code = "BANK_AMOUNT_MISMATCH"
        expected_action = "HUMAN_REVIEW"
        expected_difference = 1000

    elif scenario == "MISSING_GATEWAY":
        gateway_record = None

        expected_status = "EXCEPTION"
        exception_code = "MISSING_GATEWAY_RECORD"
        expected_action = "HUMAN_REVIEW"

    elif scenario == "MISSING_SETTLEMENT":
        settlement_record = None

        expected_status = "EXCEPTION"
        exception_code = "MISSING_SETTLEMENT_RECORD"
        expected_action = "HUMAN_REVIEW"

    elif scenario == "MISSING_BANK":
        bank_record = None

        expected_status = "EXCEPTION"
        exception_code = "MISSING_BANK_RECORD"
        expected_action = "HUMAN_REVIEW"

    elif scenario == "INVALID_STATUS":
        gateway_record["processor_status"] = "UNKNOWN_STATUS"

        expected_status = "EXCEPTION"
        exception_code = "INVALID_PROCESSOR_STATUS"
        expected_action = "HUMAN_REVIEW"

    elif scenario == "DUPLICATE_BANK_REFERENCE":
        bank_record["bank_reference"] = "BANK-DUPLICATE-001"

        expected_status = "EXCEPTION"
        exception_code = "DUPLICATE_BANK_REFERENCE"
        expected_action = "HUMAN_REVIEW"

    ground_truth = {
        "case_id": case_id,
        "expected_reconciliation_status": expected_status,
        "exception_code": exception_code,
        "expected_action": expected_action,
        "expected_difference": expected_difference,
    }

    return (
        fee_record,
        gateway_record,
        settlement_record,
        bank_record,
        ground_truth,
        scenario,
    )


# ============================================================
# GENERATE ALL CASES
# ============================================================

def generate_all_cases():
    fee_records = []
    gateway_records = []
    settlement_records = []
    bank_records = []
    ground_truth_records = []

    scenario_records = []

    for case_number, scenario in enumerate(SCENARIOS, start=1):

        (
            fee,
            gateway,
            settlement,
            bank,
            ground_truth,
            scenario_name,
        ) = generate_case(case_number, scenario)

        fee_records.append(fee)

        if gateway is not None:
            gateway_records.append(gateway)

        if settlement is not None:
            settlement_records.append(settlement)

        if bank is not None:
            bank_records.append(bank)

        ground_truth_records.append(ground_truth)

        scenario_records.append({
            "case_id": ground_truth["case_id"],
            "scenario": scenario_name,
        })

    return (
        fee_records,
        gateway_records,
        settlement_records,
        bank_records,
        ground_truth_records,
        scenario_records,
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_generated_data(
    fee_df,
    gateway_df,
    settlement_df,
    bank_df,
    ground_truth_df,
    scenario_df,
):
    """Validate structural and scenario-level expectations."""

    print("\nRunning validation...\n")

    # ---- Case count ----

    assert len(fee_df) == 70
    assert len(ground_truth_df) == 70

    # ---- Required IDs ----

    assert fee_df["case_id"].is_unique
    assert fee_df["fee_id"].is_unique

    assert gateway_df["gateway_transaction_id"].is_unique
    assert settlement_df["settlement_id"].is_unique

    # Bank references intentionally contain a duplicate scenario.
    duplicate_count = bank_df["bank_reference"].duplicated().sum()
    assert duplicate_count == 2

    # ---- Amount validation ----

    assert (fee_df["fee_amount"] > 0).all()
    assert (gateway_df["gateway_amount"] > 0).all()
    assert (settlement_df["settlement_amount"] > 0).all()
    assert (bank_df["bank_amount"] > 0).all()

    # ---- Ground truth validation ----

    assert set(
        ground_truth_df["expected_reconciliation_status"]
    ) == {"PASS", "EXCEPTION"}

    exception_count = (
        ground_truth_df["expected_reconciliation_status"]
        == "EXCEPTION"
    ).sum()

    assert exception_count == 30

    # ---- Scenario distribution ----

    scenario_counts = scenario_df["scenario"].value_counts().to_dict()

    expected_counts = {
        "MATCHED": 40,
        "GATEWAY_AMOUNT_MISMATCH": 5,
        "SETTLEMENT_AMOUNT_MISMATCH": 5,
        "BANK_AMOUNT_MISMATCH": 5,
        "MISSING_GATEWAY": 4,
        "MISSING_SETTLEMENT": 3,
        "MISSING_BANK": 3,
        "INVALID_STATUS": 2,
        "DUPLICATE_BANK_REFERENCE": 3,
    }

    assert scenario_counts == expected_counts

    print("✓ Case count: 70")
    print("✓ Normal cases: 40")
    print("✓ Exception cases: 30")
    print("✓ IDs validated")
    print("✓ Amounts validated")
    print("✓ Ground truth validated")
    print("✓ Scenario distribution validated")
    print("✓ Duplicate-reference scenario validated")
    print("\nALL VALIDATIONS PASSED")


# ============================================================
# SAVE DATA
# ============================================================

def save_data(
    fee_records,
    gateway_records,
    settlement_records,
    bank_records,
    ground_truth_records,
    scenario_records,
):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)

    fee_df = pd.DataFrame(fee_records)
    gateway_df = pd.DataFrame(gateway_records)
    settlement_df = pd.DataFrame(settlement_records)
    bank_df = pd.DataFrame(bank_records)
    ground_truth_df = pd.DataFrame(ground_truth_records)
    scenario_df = pd.DataFrame(scenario_records)

    fee_df.to_csv(RAW_DIR / "fee_ledger.csv", index=False)
    gateway_df.to_csv(RAW_DIR / "payment_gateway.csv", index=False)
    settlement_df.to_csv(RAW_DIR / "settlement.csv", index=False)
    bank_df.to_csv(RAW_DIR / "bank_statement.csv", index=False)

    ground_truth_df.to_csv(
        EXPECTED_DIR / "reconciliation_ground_truth.csv",
        index=False,
    )

    scenario_df.to_csv(
        EXPECTED_DIR / "scenario_manifest.csv",
        index=False,
    )

    validate_generated_data(
        fee_df,
        gateway_df,
        settlement_df,
        bank_df,
        ground_truth_df,
        scenario_df,
    )

    print("\nGenerated files:")

    print(f"  {RAW_DIR / 'fee_ledger.csv'}")
    print(f"  {RAW_DIR / 'payment_gateway.csv'}")
    print(f"  {RAW_DIR / 'settlement.csv'}")
    print(f"  {RAW_DIR / 'bank_statement.csv'}")
    print(
        f"  {EXPECTED_DIR / 'reconciliation_ground_truth.csv'}"
    )
    print(f"  {EXPECTED_DIR / 'scenario_manifest.csv'}")


# ============================================================
# MAIN
# ============================================================

def main():
    (
        fee_records,
        gateway_records,
        settlement_records,
        bank_records,
        ground_truth_records,
        scenario_records,
    ) = generate_all_cases()

    save_data(
        fee_records,
        gateway_records,
        settlement_records,
        bank_records,
        ground_truth_records,
        scenario_records,
    )


if __name__ == "__main__":
    main()