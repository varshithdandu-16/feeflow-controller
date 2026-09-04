from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


# ============================================================
# FeeFlow persistent application state
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
STATE_FILE = DATA_DIR / "application_state.json"

_lock = Lock()


def _default_state() -> dict[str, Any]:
    return {
        "version": "1.0",
        "updated_at": None,
        "last_control_run": None,
        "last_agent_run": None,
        "review_cases": [],
        "review_decisions": [],
        "audit_records": [],
    }


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not STATE_FILE.exists():
        _write_state(_default_state())


def _read_state() -> dict[str, Any]:
    _ensure_storage()

    try:
        with STATE_FILE.open("r", encoding="utf-8") as file:
            state = json.load(file)

        if not isinstance(state, dict):
            return _default_state()

        return state

    except (json.JSONDecodeError, OSError):
        return _default_state()


def _write_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temporary_file = STATE_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(
            state,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    temporary_file.replace(STATE_FILE)


def get_state() -> dict[str, Any]:
    """
    Return the complete persisted application state.
    """
    with _lock:
        return _read_state()


def save_control_run(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Persist the latest deterministic control execution.
    """

    with _lock:
        state = _read_state()

        now = datetime.now(timezone.utc).isoformat()

        summary = {
            "cases_processed": len(results),
            "auto_clear": sum(
                result.get("control", {}).get("action") == "AUTO_CLEAR"
                for result in results
            ),
            "monitor": sum(
                result.get("control", {}).get("action") == "MONITOR"
                for result in results
            ),
            "human_review": sum(
                result.get("control", {}).get("action") == "HUMAN_REVIEW"
                for result in results
            ),
            "blocked": sum(
                result.get("control", {}).get("action") == "BLOCK"
                for result in results
            ),
        }

        state["updated_at"] = now

        state["last_control_run"] = {
            "executed_at": now,
            "summary": summary,
            "results": results,
        }

        _write_state(state)

        return state


def save_agent_run(agent_result: dict[str, Any]) -> dict[str, Any]:
    """
    Persist the latest complete agent execution.
    """

    with _lock:
        state = _read_state()

        now = datetime.now(timezone.utc).isoformat()

        state["updated_at"] = now

        state["last_agent_run"] = {
            "executed_at": now,
            **agent_result,
        }

        _write_state(state)

        return state


def save_review_cases(
    review_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Persist the current human-review queue.
    """

    with _lock:
        state = _read_state()

        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        state["review_cases"] = review_cases

        _write_state(state)

        return state


def save_review_decisions(
    review_decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Persist human-review decisions.
    """

    with _lock:
        state = _read_state()

        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        state["review_decisions"] = review_decisions

        _write_state(state)

        return state


def save_audit_records(
    audit_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Persist audit records.
    """

    with _lock:
        state = _read_state()

        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        state["audit_records"] = audit_records

        _write_state(state)

        return state