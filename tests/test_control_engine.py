import pandas as pd

from src.control_engine.decision import evaluate_case


def test_pass_case():
    result = evaluate_case(
        case_id="FF-0001",
        status="PASS",
        exception_code="NONE",
    )

    assert result.action.value == "AUTO_CLEAR"
    assert result.severity.value == "LOW"


def test_gateway_mismatch():
    result = evaluate_case(
        case_id="FF-0041",
        status="EXCEPTION",
        exception_code="GATEWAY_AMOUNT_MISMATCH",
    )

    assert result.action.value == "HUMAN_REVIEW"
    assert result.severity.value == "HIGH"


def test_duplicate_bank_reference():
    result = evaluate_case(
        case_id="FF-0068",
        status="EXCEPTION",
        exception_code="DUPLICATE_BANK_REFERENCE",
    )

    assert result.action.value == "BLOCK"
    assert result.severity.value == "CRITICAL"


def test_generated_control_decisions():
    df = pd.read_csv("data/expected/control_decisions.csv")

    assert len(df) == 70
    assert "case_id" in df.columns
    assert "action" in df.columns
    assert "severity" in df.columns
    assert "exception_code" in df.columns