from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_submit_human_review_decision():
    response = client.post(
        "/review/cases"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_cases"] > 0
    assert len(data["cases"]) > 0

    # -------------------------------------------------
    # Select an OPEN review case.
    # The first case may already be RESOLVED.
    # -------------------------------------------------

    open_cases = [
        case
        for case in data["cases"]
        if case.get("status") == "OPEN"
    ]

    assert len(open_cases) > 0, (
        "No OPEN human-review case is available."
    )

    case_id = open_cases[0]["case_id"]

    # -------------------------------------------------
    # Submit human decision
    # -------------------------------------------------

    decision_response = client.post(
        f"/review/cases/{case_id}/decision",
        json={
            "decision": "ESCALATE",
            "reason": (
                "Evidence requires additional "
                "financial investigation."
            ),
            "reviewer": "FINANCIAL_RISK_REVIEW",
        },
    )

    assert decision_response.status_code == 200

    result = decision_response.json()

    assert result["status"] == (
        "human_decision_recorded"
    )

    assert result[
        "financial_transaction_modified"
    ] is False

    assert result["decision"]["case_id"] == case_id

    assert result["decision"]["decision"] == "ESCALATE"

    assert result["decision"]["reviewer"] == (
        "FINANCIAL_RISK_REVIEW"
    )