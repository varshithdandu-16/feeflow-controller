from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Expected columns for each financial source
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = {
    "fee_ledger": {
        "case_id",
        "fee_id",
        "student_id",
        "merchant_id",
        "currency",
        "fee_amount",
        "created_at",
        "fee_status",
    },
    "payment_gateway": {
        "case_id",
        "gateway_transaction_id",
        "fee_id",
        "payment_method",
        "gateway_amount",
        "currency",
        "processor_status",
        "processed_at",
    },
    "settlement": {
        "case_id",
        "settlement_id",
        "gateway_transaction_id",
        "settlement_amount",
        "currency",
        "settlement_status",
        "settlement_date",
    },
    "bank_statement": {
        "case_id",
        "bank_reference",
        "settlement_id",
        "bank_amount",
        "currency",
        "bank_status",
        "bank_posted_at",
    },
}


# ---------------------------------------------------------------------------
# Basic validation helpers
# ---------------------------------------------------------------------------

def validate_required_columns(
    dataframe: pd.DataFrame,
    record_type: str,
) -> None:
    """
    Verify that a dataframe contains every required field
    for its financial record type.
    """

    if record_type not in REQUIRED_COLUMNS:
        raise ValueError(f"Unknown record type: {record_type}")

    actual_columns = set(dataframe.columns)
    required_columns = REQUIRED_COLUMNS[record_type]

    missing_columns = required_columns - actual_columns

    if missing_columns:
        raise ValueError(
            f"{record_type}: missing required columns: "
            f"{sorted(missing_columns)}"
        )


def validate_not_null(
    dataframe: pd.DataFrame,
    record_type: str,
) -> None:
    """
    Required fields must not contain null values.
    """

    required_columns = REQUIRED_COLUMNS[record_type]

    null_columns = [
        column
        for column in required_columns
        if dataframe[column].isna().any()
    ]

    if null_columns:
        raise ValueError(
            f"{record_type}: null values found in: "
            f"{sorted(null_columns)}"
        )


def validate_non_negative_amount(
    dataframe: pd.DataFrame,
    amount_column: str,
    record_type: str,
) -> None:
    """
    Financial amounts cannot be negative.
    """

    invalid_amounts = dataframe[
        dataframe[amount_column] < 0
    ]

    if not invalid_amounts.empty:
        raise ValueError(
            f"{record_type}: negative values found in {amount_column}"
        )


def validate_datetime(
    dataframe: pd.DataFrame,
    column: str,
    record_type: str,
) -> None:
    """
    Verify that a timestamp/date field can be interpreted as a datetime.
    """

    parsed = pd.to_datetime(
        dataframe[column],
        errors="coerce",
    )

    if parsed.isna().any():
        raise ValueError(
            f"{record_type}: invalid datetime values in {column}"
        )


# ---------------------------------------------------------------------------
# Record-type validation
# ---------------------------------------------------------------------------

def validate_fee_ledger(dataframe: pd.DataFrame) -> None:
    validate_required_columns(dataframe, "fee_ledger")
    validate_not_null(dataframe, "fee_ledger")

    validate_non_negative_amount(
        dataframe,
        "fee_amount",
        "fee_ledger",
    )

    validate_datetime(
        dataframe,
        "created_at",
        "fee_ledger",
    )


def validate_payment_gateway(dataframe: pd.DataFrame) -> None:
    validate_required_columns(dataframe, "payment_gateway")
    validate_not_null(dataframe, "payment_gateway")

    validate_non_negative_amount(
        dataframe,
        "gateway_amount",
        "payment_gateway",
    )

    validate_datetime(
        dataframe,
        "processed_at",
        "payment_gateway",
    )


def validate_settlement(dataframe: pd.DataFrame) -> None:
    validate_required_columns(dataframe, "settlement")
    validate_not_null(dataframe, "settlement")

    validate_non_negative_amount(
        dataframe,
        "settlement_amount",
        "settlement",
    )

    validate_datetime(
        dataframe,
        "settlement_date",
        "settlement",
    )


def validate_bank_statement(dataframe: pd.DataFrame) -> None:
    validate_required_columns(dataframe, "bank_statement")
    validate_not_null(dataframe, "bank_statement")

    validate_non_negative_amount(
        dataframe,
        "bank_amount",
        "bank_statement",
    )

    validate_datetime(
        dataframe,
        "bank_posted_at",
        "bank_statement",
    )


# ---------------------------------------------------------------------------
# Complete source validation
# ---------------------------------------------------------------------------

def validate_all_sources(data_directory: str = "data/raw") -> None:
    """
    Validate the four financial source datasets.
    """

    data_path = Path(data_directory)

    fee_ledger = pd.read_csv(
        data_path / "fee_ledger.csv"
    )

    payment_gateway = pd.read_csv(
        data_path / "payment_gateway.csv"
    )

    settlement = pd.read_csv(
        data_path / "settlement.csv"
    )

    bank_statement = pd.read_csv(
        data_path / "bank_statement.csv"
    )

    validate_fee_ledger(fee_ledger)
    validate_payment_gateway(payment_gateway)
    validate_settlement(settlement)
    validate_bank_statement(bank_statement)

    print("Schema validation passed.")