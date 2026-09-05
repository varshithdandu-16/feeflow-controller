import pandas as pd

from src.reconciliation.reconciliation import reconcile_all, reconcile_case


def _row(**values):
    return pd.Series(values)


def test_reconcile_all_matches_ground_truth_scenarios():
    findings = reconcile_all()
    by_case = {finding.case_id: finding for finding in findings}

    assert len(findings) == 70
    assert sum(f.status == "MATCHED" for f in findings) == 40
    assert sum(f.status == "EXCEPTION" for f in findings) == 30

    expected_codes = {
        **{f"FF-{i:04d}": "GATEWAY_AMOUNT_MISMATCH" for i in range(41, 46)},
        **{f"FF-{i:04d}": "SETTLEMENT_AMOUNT_MISMATCH" for i in range(46, 51)},
        **{f"FF-{i:04d}": "BANK_AMOUNT_MISMATCH" for i in range(51, 56)},
        **{f"FF-{i:04d}": "MISSING_GATEWAY_RECORD" for i in range(56, 60)},
        **{f"FF-{i:04d}": "MISSING_SETTLEMENT_RECORD" for i in range(60, 63)},
        **{f"FF-{i:04d}": "MISSING_BANK_RECORD" for i in range(63, 66)},
        **{f"FF-{i:04d}": "INVALID_PROCESSOR_STATUS" for i in range(66, 68)},
        **{f"FF-{i:04d}": "DUPLICATE_BANK_REFERENCE" for i in range(68, 71)},
    }

    for case_id, code in expected_codes.items():
        finding = by_case[case_id]
        assert finding.status == "EXCEPTION"
        assert finding.discrepancy_type == code
        assert finding.evidence


def test_gateway_amount_mismatch_reports_expected_and_observed_amounts():
    finding = reconcile_all()[40]

    assert finding.case_id == "FF-0041"
    assert finding.discrepancy_type == "GATEWAY_AMOUNT_MISMATCH"
    assert finding.evidence["expected_amount"] == 125000.0
    assert finding.evidence["observed_amount"] == 124500.0
    assert finding.evidence["difference"] == 500.0


def test_bank_amount_mismatch_reports_expected_and_observed_amounts():
    finding = reconcile_all()[50]

    assert finding.case_id == "FF-0051"
    assert finding.discrepancy_type == "BANK_AMOUNT_MISMATCH"
    assert finding.severity == "CRITICAL"
    assert finding.evidence["expected_amount"] == 100000.0
    assert finding.evidence["observed_amount"] == 99000.0
    assert finding.evidence["difference"] == 1000.0


def test_duplicate_bank_reference_is_blockable_by_control_engine():
    finding = reconcile_all()[67]

    assert finding.case_id == "FF-0068"
    assert finding.discrepancy_type == "DUPLICATE_BANK_REFERENCE"
    assert finding.severity == "CRITICAL"
    assert finding.evidence["duplicate"] is True


def test_invalid_processor_status_is_detected_before_clear():
    finding = reconcile_all()[65]

    assert finding.case_id == "FF-0066"
    assert finding.discrepancy_type == "INVALID_PROCESSOR_STATUS"
    assert finding.evidence["observed_status"] == "UNKNOWN_STATUS"
    assert finding.severity == "MEDIUM"


def test_missing_records_include_source_and_expected_observed_evidence():
    findings = reconcile_all()
    missing_gateway = findings[55]
    missing_settlement = findings[59]
    missing_bank = findings[62]

    assert missing_gateway.evidence["source"] == "fee_ledger -> payment_gateway"
    assert missing_settlement.evidence["source"] == "payment_gateway -> settlement"
    assert missing_bank.evidence["source"] == "settlement -> bank_statement"
    assert missing_gateway.evidence["observed"]["gateway_record"] is False
    assert missing_settlement.evidence["observed"]["settlement_record"] is False
    assert missing_bank.evidence["observed"]["bank_record"] is False
