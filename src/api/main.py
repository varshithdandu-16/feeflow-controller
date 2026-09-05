from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.agent.orchestrator import run_agent
from src.agent.run_store import get_latest_agent_run
from src.api.service import run_control_pipeline
from src.api.review import router as review_router
from src.api.audit import router as audit_router
from src.api.transaction import router as transaction_router


app = FastAPI(
    title="FeeFlow Controller",
    description=(
        "Deterministic financial control, reconciliation, "
        "agent investigation, human review, and audit API"
    ),
    version="0.1.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REGISTER ROUTERS
# =========================================================

app.include_router(review_router)
app.include_router(audit_router)
app.include_router(transaction_router)


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
# APPLICATION STATE
# =========================================================

@app.get("/state")
def application_state():
    """
    Return the latest persisted FeeFlow application state.
    """

    try:
        latest = get_latest_agent_run()

        return {
            "status": "ok",
            "state": latest,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load application state: {exc}",
        ) from exc


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
# LATEST AGENT RUN
# =========================================================

@app.get("/agent/latest")
def latest_agent_run():
    """
    Return the newest persisted agent run for UI hydration.
    """

    try:
        run = get_latest_agent_run()

        return {
            "status": "available",
            "run": run,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load latest agent run: {exc}",
        ) from exc


# =========================================================
# COMPLETE AGENT PIPELINE
# =========================================================

@app.post("/agent/run")
def run_agent_endpoint():
    """
    Execute one complete FeeFlow Controller agent run.

    The response shape intentionally matches the frontend:
    cases_processed, summary, assessments, investigations,
    review_cases, review_decisions, and audit_records are all
    returned at the top level.
    """

    try:
        result = run_agent()

        # -----------------------------------------------------
        # SUMMARY
        # -----------------------------------------------------

        clear_count = sum(
            1
            for assessment in result.assessments
            if assessment.action.value == "CLEAR"
        )

        monitor_count = sum(
            1
            for assessment in result.assessments
            if assessment.action.value == "MONITOR"
        )

        human_review_count = sum(
            1
            for assessment in result.assessments
            if assessment.action.value == "HUMAN_REVIEW"
        )

        blocked_count = sum(
            1
            for assessment in result.assessments
            if assessment.action.value == "BLOCKED"
        )

        summary = {
            "clear": clear_count,
            "monitor": monitor_count,
            "human_review": human_review_count,
            "blocked": blocked_count,
        }

        # -----------------------------------------------------
        # ASSESSMENTS
        # -----------------------------------------------------

        assessments = [
            {
                "case_id": assessment.case_id,
                "action": assessment.action.value,
                "reason": assessment.reason,
                "requires_human": assessment.requires_human,
            }
            for assessment in result.assessments
        ]

        # -----------------------------------------------------
        # INVESTIGATIONS
        # -----------------------------------------------------

        investigations = [
            {
                "case_id": investigation.case_id,
                "finding": investigation.finding,
                "risk": investigation.risk,
                "explanation": investigation.explanation,
                "evidence": investigation.evidence,
                "recommendation": (
                    investigation.recommendation.value
                    if hasattr(
                        investigation.recommendation,
                        "value",
                    )
                    else investigation.recommendation
                ),
                "confidence": investigation.confidence,
            }
            for investigation in result.investigations
        ]

        # -----------------------------------------------------
        # REVIEW CASES
        # -----------------------------------------------------

        review_cases = [
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
        ]

        # -----------------------------------------------------
        # REVIEW DECISIONS
        # -----------------------------------------------------

        review_decisions = [
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
        ]

        # -----------------------------------------------------
        # AUDIT RECORDS
        # -----------------------------------------------------

        audit_records = [
            asdict(record)
            for record in result.audit_records
        ]

        # -----------------------------------------------------
        # FRONTEND-COMPATIBLE RESPONSE
        # -----------------------------------------------------

        return {
            "status": result.status.value,
            "cases_processed": len(result.assessments),
            "summary": summary,
            "assessments": assessments,
            "investigations": investigations,
            "review_cases": review_cases,
            "review_decisions": review_decisions,
            "audit_records": audit_records,
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Required financial source is unavailable: {exc}",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent validation failed: {exc}",
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {exc}",
        ) from exc