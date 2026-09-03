from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional


# =========================================================
# PERSISTENT LOCAL STORAGE
# =========================================================

RUNS_FILE = Path("data/agent_runs.json")

_lock = Lock()


# =========================================================
# TIME
# =========================================================

def _utc_now() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


# =========================================================
# STORAGE INITIALIZATION
# =========================================================

def _ensure_storage() -> None:
    """Create the local storage file when necessary."""

    RUNS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not RUNS_FILE.exists():
        RUNS_FILE.write_text(
            "[]",
            encoding="utf-8",
        )


# =========================================================
# READ STORAGE
# =========================================================

def _read_runs() -> List[Dict[str, Any]]:
    """Read all persisted agent runs."""

    _ensure_storage()

    try:
        content = RUNS_FILE.read_text(
            encoding="utf-8"
        )

        if not content.strip():
            return []

        data = json.loads(content)

        if not isinstance(data, list):
            raise ValueError(
                "Agent run storage must contain a JSON list."
            )

        return data

    except json.JSONDecodeError as exc:
        raise ValueError(
            "Agent run storage contains invalid JSON: "
            f"{exc}"
        ) from exc


# =========================================================
# WRITE STORAGE
# =========================================================

def _write_runs(
    runs: List[Dict[str, Any]],
) -> None:
    """Atomically write agent runs to local storage."""

    _ensure_storage()

    temporary_file = RUNS_FILE.with_suffix(".tmp")

    temporary_file.write_text(
        json.dumps(
            runs,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    temporary_file.replace(
        RUNS_FILE
    )


# =========================================================
# SAVE AGENT RUN
# =========================================================

def save_agent_run(
    result: Any,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Persist one complete FeeFlow Controller agent run.

    This function stores workflow information only.

    It NEVER:
        - executes payments
        - releases payments
        - approves transactions
        - rejects transactions
        - blocks transactions
        - modifies financial records
    """

    resolved_run_id = (
        run_id
        or getattr(
            result,
            "run_id",
            None,
        )
    )

    if not resolved_run_id:
        raise ValueError(
            "Agent run_id is required for persistence."
        )

    assessments = getattr(
        result,
        "assessments",
        [],
    )

    investigations = getattr(
        result,
        "investigations",
        [],
    )

    review_cases = getattr(
        result,
        "review_cases",
        [],
    )

    review_decisions = getattr(
        result,
        "review_decisions",
        [],
    )

    human_review_packets = getattr(
        result,
        "human_review_packets",
        [],
    )

    audit_records = getattr(
        result,
        "audit_records",
        [],
    )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    summary = {
        "clear": 0,
        "monitor": 0,
        "human_review": 0,
        "blocked": 0,
    }

    for assessment in assessments:

        action = getattr(
            assessment,
            "action",
            None,
        )

        if action is None:
            continue

        action_value = getattr(
            action,
            "value",
            str(action),
        )

        if action_value == "CLEAR":
            summary["clear"] += 1

        elif action_value == "MONITOR":
            summary["monitor"] += 1

        elif action_value == "HUMAN_REVIEW":
            summary["human_review"] += 1

        elif action_value == "BLOCKED":
            summary["blocked"] += 1

    # -----------------------------------------------------
    # Serialize safely
    # -----------------------------------------------------

    record = {
        "run_id": resolved_run_id,

        "created_at": _utc_now(),

        "status": getattr(
            getattr(
                result,
                "status",
                None,
            ),
            "value",
            getattr(
                result,
                "status",
                "UNKNOWN",
            ),
        ),

        "cases_processed": len(
            assessments
        ),

        "summary": summary,

        "assessments": [
            asdict(item)
            for item in assessments
        ],

        "investigations": [
            asdict(item)
            for item in investigations
        ],

        "review_cases": [
            asdict(item)
            for item in review_cases
        ],

        "review_decisions": [
            asdict(item)
            for item in review_decisions
        ],

        "human_review_packets": [
            asdict(item)
            for item in human_review_packets
        ],

        "human_decisions": [],

        "audit_records": [
            asdict(item)
            for item in audit_records
        ],
    }

    # -----------------------------------------------------
    # Persist atomically
    # -----------------------------------------------------

    with _lock:

        runs = _read_runs()

        # Idempotent by run_id.
        runs = [
            existing
            for existing in runs
            if existing.get("run_id")
            != resolved_run_id
        ]

        runs.append(record)

        _write_runs(runs)

    return record


# =========================================================
# LIST RUNS
# =========================================================

def list_agent_runs() -> List[Dict[str, Any]]:
    """Return persisted agent runs, newest first."""

    with _lock:
        runs = _read_runs()

    return sorted(
        runs,
        key=lambda item: item.get(
            "created_at",
            "",
        ),
        reverse=True,
    )


# =========================================================
# GET ONE RUN
# =========================================================

def get_agent_run(
    run_id: str,
) -> Optional[Dict[str, Any]]:
    """Retrieve one persisted agent run."""

    if not run_id or not run_id.strip():
        raise ValueError(
            "run_id cannot be empty."
        )

    with _lock:
        runs = _read_runs()

    for run in runs:

        if run.get("run_id") == run_id:
            return run

    return None


# =========================================================
# FIND REVIEW CASE
# =========================================================

def _find_case_in_run(
    run: Dict[str, Any],
    case_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Find a review case in either supported representation.

    Older runs may contain `review_cases`.

    Newer agent runs may expose the same workflow item as
    `human_review_packets`.

    This compatibility layer prevents the human-review API
    from depending on one internal representation.
    """

    # -----------------------------------------------------
    # Primary representation
    # -----------------------------------------------------

    for case in run.get(
        "review_cases",
        [],
    ):

        if case.get("case_id") == case_id:
            return case

    # -----------------------------------------------------
    # Human review packet representation
    # -----------------------------------------------------

    for packet in run.get(
        "human_review_packets",
        [],
    ):

        if packet.get("case_id") == case_id:
            return packet

    return None


# =========================================================
# HUMAN REVIEW QUEUE
# =========================================================

def get_review_queue() -> List[Dict[str, Any]]:
    """
    Build the current human-review queue.

    Only OPEN cases are returned.

    Both review_cases and human_review_packets are supported.
    """

    queue: List[Dict[str, Any]] = []

    for run in list_agent_runs():

        # -------------------------------------------------
        # Existing review decisions
        # -------------------------------------------------

        decisions_by_case = {
            decision.get("case_id"): decision
            for decision in run.get(
                "review_decisions",
                [],
            )
        }

        # -------------------------------------------------
        # Prefer review_cases when available.
        # Otherwise use human_review_packets.
        # -------------------------------------------------

        raw_cases = run.get(
            "review_cases",
            [],
        )

        if not raw_cases:

            raw_cases = run.get(
                "human_review_packets",
                [],
            )

        # -------------------------------------------------
        # Build queue
        # -------------------------------------------------

        for review_case in raw_cases:

            status = review_case.get(
                "status",
                "OPEN",
            )

            if status != "OPEN":
                continue

            case_id = review_case.get(
                "case_id"
            )

            if not case_id:
                continue

            queue.append(
                {
                    "run_id": run.get(
                        "run_id"
                    ),

                    "case_id": case_id,

                    "finding": review_case.get(
                        "finding"
                    ),

                    "risk": review_case.get(
                        "risk"
                    ),

                    "explanation": review_case.get(
                        "explanation"
                    ),

                    "evidence": review_case.get(
                        "evidence",
                        {},
                    ),

                    "recommendation": review_case.get(
                        "recommendation"
                    ),

                    "confidence": review_case.get(
                        "confidence"
                    ),

                    "status": status,

                    "review_decision":
                        decisions_by_case.get(
                            case_id
                        ),
                }
            )

    return queue


# =========================================================
# HUMAN DECISION
# =========================================================

def record_human_decision(
    case_id: str,
    decision: str,
    reason: str,
    reviewer: str,
    decided_at: str,
) -> Dict[str, Any]:
    """
    Persist a human review decision.

    IMPORTANT:
    This changes workflow state only.

    It NEVER:
        - executes a payment
        - releases a payment
        - approves a transaction
        - rejects a transaction
        - blocks a transaction
        - modifies a financial record
    """

    # -----------------------------------------------------
    # Validate case ID
    # -----------------------------------------------------

    if not case_id or not case_id.strip():
        raise ValueError(
            "case_id cannot be empty."
        )

    case_id = case_id.strip()

    # -----------------------------------------------------
    # Validate decision
    # -----------------------------------------------------

    if not decision or not decision.strip():
        raise ValueError(
            "decision cannot be empty."
        )

    decision = decision.strip()

    # -----------------------------------------------------
    # Validate reason
    # -----------------------------------------------------

    if not reason or not reason.strip():
        raise ValueError(
            "reason cannot be empty."
        )

    reason = reason.strip()

    # -----------------------------------------------------
    # Validate reviewer
    # -----------------------------------------------------

    if not reviewer or not reviewer.strip():
        raise ValueError(
            "reviewer cannot be empty."
        )

    reviewer = reviewer.strip()

    # -----------------------------------------------------
    # Validate timestamp
    # -----------------------------------------------------

    if not decided_at or not decided_at.strip():
        raise ValueError(
            "decided_at cannot be empty."
        )

    decided_at = decided_at.strip()

    # -----------------------------------------------------
    # Build immutable workflow record
    # -----------------------------------------------------

    human_decision = {
        "case_id": case_id,
        "decision": decision,
        "reason": reason,
        "reviewer": reviewer,
        "decided_at": decided_at,
    }

    # -----------------------------------------------------
    # Persist workflow state
    # -----------------------------------------------------

    with _lock:

        runs = _read_runs()

        target_run: Optional[
            Dict[str, Any]
        ] = None

        target_case: Optional[
            Dict[str, Any]
        ] = None

        # -------------------------------------------------
        # Search newest runs first.
        # -------------------------------------------------

        for run in sorted(
            runs,
            key=lambda item: item.get(
                "created_at",
                "",
            ),
            reverse=True,
        ):

            candidate = _find_case_in_run(
                run,
                case_id,
            )

            if candidate is not None:

                target_run = run
                target_case = candidate

                break

        # -------------------------------------------------
        # Case must exist
        # -------------------------------------------------

        if (
            target_run is None
            or target_case is None
        ):
            raise ValueError(
                f"Review case {case_id} "
                "was not found."
            )

        # -------------------------------------------------
        # Case must still be open
        # -------------------------------------------------

        current_status = target_case.get(
            "status",
            "OPEN",
        )

        if current_status != "OPEN":

            raise ValueError(
                f"Review case {case_id} "
                f"is not OPEN. Current status: "
                f"{current_status}."
            )

        # -------------------------------------------------
        # Mark workflow case as resolved
        # -------------------------------------------------

        target_case["status"] = "RESOLVED"

        # -------------------------------------------------
        # Preserve decision history
        # -------------------------------------------------

        human_decisions = target_run.setdefault(
            "human_decisions",
            [],
        )

        human_decisions.append(
            human_decision
        )

        # -------------------------------------------------
        # Also keep a workflow decision reference.
        #
        # This does NOT represent a financial action.
        # -------------------------------------------------

        review_decisions = target_run.setdefault(
            "review_decisions",
            [],
        )

        review_decisions.append(
            {
                "case_id": case_id,
                "status": "RESOLVED",
                "decision": decision,
                "reason": reason,
                "reviewer": reviewer,
                "decided_at": decided_at,
            }
        )

        # -------------------------------------------------
        # Persist
        # -------------------------------------------------

        _write_runs(runs)

    return human_decision


# =========================================================
# AUDIT RECORDS
# =========================================================

def get_audit_records(
    run_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve audit records.

    If run_id is supplied, only records from that run
    are returned.
    """

    if run_id:

        run = get_agent_run(
            run_id
        )

        if run is None:
            return []

        return run.get(
            "audit_records",
            [],
        )

    records: List[
        Dict[str, Any]
    ] = []

    for run in list_agent_runs():

        records.extend(
            run.get(
                "audit_records",
                [],
            )
        )

    return records