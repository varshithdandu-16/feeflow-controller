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

    case_id = data["cases"][0]["case_id"]

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