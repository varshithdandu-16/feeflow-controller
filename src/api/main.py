from dataclasses import asdict

from fastapi import FastAPI, HTTPException

from src.agent.orchestrator import run_agent
from src.api.service import run_control_pipeline
from src.api.review import router as review_router


app = FastAPI(
    title="FeeFlow Controller",
    description=(
        "Deterministic financial control, reconciliation, "
        "agent investigation, human review, and audit API"
    ),
    version="0.1.0",
)


# =========================================================
# REGISTER ROUTERS
# =========================================================

app.include_router(review_router)


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "feeflow-controller",
        "version": "0.1.0",
    }


# =========================================================
# DETERMINISTIC CONTROL PIPELINE
# =========================================================

@app.post("/controls/run")
def run_controls():
    """
    Execute the deterministic financial control pipeline.
    """

    try:
        results = run_control_pipeline()

        auto_clear = sum(
            result["control"]["action"] == "AUTO_CLEAR"
            for result in results
        )

        monitor = sum(
            result["control"]["action"] == "MONITOR"
            for result in results
        )

        human_review = sum(
            result["control"]["action"] == "HUMAN_REVIEW"
            for result in results
        )

        blocked = sum(
            result["control"]["action"] == "BLOCK"
            for result in results
        )

        return {
            "status": "completed",
            "cases_processed": len(results),
            "summary": {
                "auto_clear": auto_clear,
                "monitor": monitor,
                "human_review": human_review,
                "blocked": blocked,
            },
            "results": results,
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Required financial source is unavailable: {exc}",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Financial data validation failed: {exc}",
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Control pipeline failed unexpectedly.",
        ) from exc


# =========================================================
# COMPLETE AGENT PIPELINE
# =========================================================

@app.post("/agent/run")
def run_agent_endpoint():
    """
    Execute one complete FeeFlow Controller agent run.
    """

    try:
        result = run_agent()

        summary = {
            "clear": sum(
                1
                for assessment in result.assessments
                if assessment.action.value == "CLEAR"
            ),
            "monitor": sum(
                1
                for assessment in result.assessments
                if assessment.action.value == "MONITOR"
            ),
            "human_review": sum(
                1
                for assessment in result.assessments
                if assessment.action.value == "HUMAN_REVIEW"
            ),
            "blocked": sum(
                1
                for assessment in result.assessments
                if assessment.action.value == "BLOCKED"
            ),
        }

        return {
            "status": result.status.value,
            "cases_processed": len(result.assessments),

            "summary": summary,

            "assessments": [
                {
                    "case_id": assessment.case_id,
                    "action": assessment.action.value,
                    "reason": assessment.reason,
                    "requires_human": assessment.requires_human,
                }
                for assessment in result.assessments
            ],

            "investigations": [
                {
                    "case_id": investigation.case_id,
                    "finding": investigation.finding,
                    "risk": investigation.risk,
                    "explanation": investigation.explanation,
                    "evidence": investigation.evidence,
                    "recommendation": (
                        investigation.recommendation.value
                    ),
                    "confidence": investigation.confidence,
                }
                for investigation in result.investigations
            ],

            "review_cases": [
                {
                    "case_id": review_case.case_id,
                    "finding": review_case.finding,
                    "risk": review_case.risk,
                    "explanation": review_case.explanation,
                    "evidence": review_case.evidence,
                    "recommendation": review_case.recommendation,
                    "confidence": review_case.confidence,
                    "status": review_case.status,
                }
                for review_case in result.review_cases
            ],

            "review_decisions": [
                {
                    "case_id": decision.case_id,
                    "status": decision.status,
                    "priority": decision.priority,
                    "assigned_to": decision.assigned_to,
                    "decision": decision.decision,
                    "reason": decision.reason,
                    "confidence": decision.confidence,
                }
                for decision in result.review_decisions
            ],

            "audit_records": [
                asdict(record)
                for record in result.audit_records
            ],
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Required financial source is unavailable: {exc}",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Financial data validation failed: {exc}",
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {exc}",
        ) from exc