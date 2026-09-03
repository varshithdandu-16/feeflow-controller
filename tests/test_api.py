from fastapi.testclient import TestClient

from src.agent.assessment import assess_control_result
from src.agent.contracts import AgentAction, AgentRunStatus
from src.api.main import app


client = TestClient(app)


def test_clear_assessment_requires_no_human():
    result = {
        "case_id": "FF-TEST-CLEAR",
        "control": {
            "action": "AUTO_CLEAR",
            "severity": "LOW",
            "reason": "All controls passed.",
        },
    }

    assessment = assess_control_result(result)

    assert assessment.case_id == "FF-TEST-CLEAR"
    assert assessment.action == AgentAction.CLEAR
    assert assessment.requires_human is False


def test_human_review_requires_human():
    result = {
        "case_id": "FF-TEST-HUMAN",
        "control": {
            "action": "HUMAN_REVIEW",
            "severity": "HIGH",
            "reason": "Gateway amount does not match settlement amount.",
        },
    }

    assessment = assess_control_result(result)

    assert assessment.case_id == "FF-TEST-HUMAN"
    assert assessment.action == AgentAction.HUMAN_REVIEW
    assert assessment.requires_human is True


def test_agent_run_endpoint():
    response = client.post("/agent/run")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] in {
        AgentRunStatus.COMPLETED.value,
        AgentRunStatus.REQUIRES_HUMAN.value,
    }

    assert "cases_processed" in data
    assert "summary" in data
    assert "assessments" in data

    assert data["cases_processed"] == len(data["assessments"])


def test_agent_run_summary_is_consistent():
    response = client.post("/agent/run")

    assert response.status_code == 200

    data = response.json()
    summary = data["summary"]

    total = (

        summary["clear"]
        + summary["monitor"]
        + summary["human_review"]
        + summary["blocked"]
    )

    assert total == data["cases_processed"]

    if summary["human_review"] > 0 or summary["blocked"] > 0:
        assert data["status"] == AgentRunStatus.REQUIRES_HUMAN.value