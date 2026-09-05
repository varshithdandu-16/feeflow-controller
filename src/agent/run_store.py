from __future__ import annotations

import json
from copy import deepcopy
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from threading import Lock
from typing import (
    Any,
    Dict,
    List,
    Optional,
)


RUNS_FILE = Path(
    "data/agent_runs.json"
)

_lock = Lock()


def _utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _ensure_storage() -> None:
    RUNS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not RUNS_FILE.exists():
        RUNS_FILE.write_text(
            "[]",
            encoding="utf-8",
        )


def _read_runs() -> List[
    Dict[str, Any]
]:
    _ensure_storage()

    content = RUNS_FILE.read_text(
        encoding="utf-8"
    )

    if not content.strip():
        return []

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Agent run storage contains invalid JSON."
        ) from exc

    if not isinstance(data, list):
        raise ValueError(
            "Agent run storage must contain a JSON list."
        )

    return data


def _write_runs(
    runs: List[Dict[str, Any]]
) -> None:
    _ensure_storage()

    temp_file = RUNS_FILE.with_suffix(
        ".tmp"
    )

    temp_file.write_text(
        json.dumps(
            runs,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    temp_file.replace(
        RUNS_FILE
    )


def save_agent_run(
    result: Any,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:

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
            "Agent run_id is required."
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

        value = getattr(
            action,
            "value",
            str(action),
        )

        if value == "CLEAR":
            summary["clear"] += 1

        elif value == "MONITOR":
            summary["monitor"] += 1

        elif value == "HUMAN_REVIEW":
            summary["human_review"] += 1

        elif value == "BLOCKED":
            summary["blocked"] += 1

    def serialize(items):
        return [
            item.to_dict()
            if hasattr(item, "to_dict")
            else (
                item.__dict__
                if hasattr(item, "__dict__")
                else item
            )
            for item in items
        ]

    record = {
        "run_id":
            resolved_run_id,

        "created_at":
            _utc_now(),

        "status":
            getattr(
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

        "cases_processed":
            len(assessments),

        "summary":
            summary,

        "assessments":
            serialize(assessments),

        "investigations":
            serialize(investigations),

        "review_cases":
            serialize(review_cases),

        "review_decisions":
            serialize(review_decisions),

        "human_review_packets":
            serialize(
                human_review_packets
            ),

        "human_decisions":
            [],

        "audit_records":
            serialize(audit_records),
    }

    with _lock:
        runs = _read_runs()

        runs = [
            run
            for run in runs
            if run.get("run_id")
            != resolved_run_id
        ]

        runs.append(record)

        _write_runs(runs)

    return record


def list_agent_runs() -> List[
    Dict[str, Any]
]:
    with _lock:
        runs = _read_runs()

    return sorted(
        runs,
        key=lambda item:
            item.get(
                "created_at",
                "",
            ),
        reverse=True,
    )


def get_latest_agent_run():
    runs = list_agent_runs()

    return (
        deepcopy(runs[0])
        if runs
        else None
    )


def get_agent_run(
    run_id: str,
):
    if not run_id or not run_id.strip():
        raise ValueError(
            "run_id cannot be empty."
        )

    for run in list_agent_runs():
        if run.get("run_id") == run_id:
            return deepcopy(run)

    return None


def _find_case_in_run(
    run: Dict[str, Any],
    case_id: str,
):
    for case in run.get(
        "review_cases",
        [],
    ):
        if case.get("case_id") == case_id:
            return case

    for packet in run.get(
        "human_review_packets",
        [],
    ):
        if packet.get("case_id") == case_id:
            return packet

    return None


def get_review_queue() -> List[
    Dict[str, Any]
]:
    queue = []
    seen_case_ids = set()

    for run in list_agent_runs():

        raw_cases = run.get(
            "review_cases",
            [],
        )

        if not raw_cases:
            raw_cases = run.get(
                "human_review_packets",
                [],
            )

        for case in raw_cases:
            case_id = case.get(
                "case_id"
            )

            if not case_id:
                continue

            if case_id in seen_case_ids:
                continue

            seen_case_ids.add(case_id)

            status = str(
                case.get(
                    "status",
                    "OPEN",
                )
            ).upper()

            if status != "OPEN":
                continue

            queue.append(
                {
                    "run_id":
                        run.get("run_id"),

                    "created_at":
                        run.get("created_at"),

                    "case_id":
                        case_id,

                    "finding":
                        case.get("finding"),

                    "risk":
                        case.get("risk"),

                    "explanation":
                        case.get("explanation"),

                    "evidence":
                        case.get(
                            "evidence",
                            {},
                        ),

                    "recommendation":
                        case.get(
                            "recommendation"
                        ),

                    "confidence":
                        case.get(
                            "confidence"
                        ),

                    "status":
                        "OPEN",
                }
            )

    return queue


def record_human_decision(
    case_id: str,
    decision: str,
    reason: str,
    reviewer: str,
    decided_at: str,
):
    if not case_id.strip():
        raise ValueError(
            "case_id cannot be empty."
        )

    with _lock:
        runs = _read_runs()

        ordered_indices = sorted(
            range(len(runs)),
            key=lambda index:
                runs[index].get(
                    "created_at",
                    "",
                ),
            reverse=True,
        )

        target_run = None
        target_case = None

        for index in ordered_indices:
            case = _find_case_in_run(
                runs[index],
                case_id,
            )

            if case is None:
                continue

            if str(
                case.get(
                    "status",
                    "OPEN",
                )
            ).upper() != "OPEN":
                continue

            target_run = runs[index]
            target_case = case
            break

        if target_run is None:
            raise ValueError(
                f"Open review case {case_id} was not found."
            )

        target_case["status"] = "RESOLVED"

        decision_record = {
            "case_id":
                case_id,
            "decision":
                decision,
            "reason":
                reason,
            "reviewer":
                reviewer,
            "decided_at":
                decided_at,
            "status":
                "RESOLVED",
        }

        target_run.setdefault(
            "human_decisions",
            [],
        ).append(
            decision_record
        )

        target_run.setdefault(
            "review_decisions",
            [],
        ).append(
            decision_record
        )

        target_run.setdefault(
            "audit_records",
            [],
        ).append(
            {
                "event":
                    "HUMAN_REVIEW_DECISION",

                "case_id":
                    case_id,

                "timestamp":
                    decided_at,

                "decision":
                    decision,

                "reviewer":
                    reviewer,

                "reason":
                    reason,

                "status":
                    "RESOLVED",

                "financial_transaction_modified":
                    False,
            }
        )

        _write_runs(runs)

        return deepcopy(
            decision_record
        )


def get_audit_records(
    run_id: Optional[str] = None,
):
    if run_id:
        run = get_agent_run(
            run_id
        )

        return (
            run.get(
                "audit_records",
                [],
            )
            if run
            else []
        )

    records = []

    for run in list_agent_runs():
        records.extend(
            run.get(
                "audit_records",
                [],
            )
        )

        for decision in run.get(
            "human_decisions",
            [],
        ):
            if not any(
                record.get(
                    "event"
                )
                == "HUMAN_REVIEW_DECISION"
                and record.get(
                    "case_id"
                )
                == decision.get(
                    "case_id"
                )
                and record.get(
                    "timestamp"
                )
                == decision.get(
                    "decided_at"
                )
                for record in records
            ):
                records.append(
                    {
                        "event":
                            "HUMAN_REVIEW_DECISION",

                        "case_id":
                            decision.get(
                                "case_id"
                            ),

                        "timestamp":
                            decision.get(
                                "decided_at"
                            ),

                        "decision":
                            decision.get(
                                "decision"
                            ),

                        "reviewer":
                            decision.get(
                                "reviewer"
                            ),

                        "reason":
                            decision.get(
                                "reason"
                            ),

                        "status":
                            "RESOLVED",

                        "financial_transaction_modified":
                            False,
                    }
                )

    return sorted(
        records,
        key=lambda record:
            record.get(
                "timestamp",
                "",
            ),
        reverse=True,
    )