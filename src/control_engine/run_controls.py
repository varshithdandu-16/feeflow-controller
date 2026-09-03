import pandas as pd

from src.control_engine.decision import evaluate_case


INPUT_FILE = "data/expected/reconciliation_ground_truth.csv"
OUTPUT_FILE = "data/expected/control_decisions.csv"


def main():
    df = pd.read_csv(INPUT_FILE)

    decisions = []

    for _, row in df.iterrows():
        decision = evaluate_case(
            case_id=row["case_id"],
            status=row["expected_reconciliation_status"],
            exception_code=row["exception_code"]
        )

        decisions.append({
            "case_id": decision.case_id,
            "status": decision.status,
            "exception_code": decision.exception_code,
            "severity": decision.severity.value,
            "action": decision.action.value,
            "reason": decision.reason,
        })

    result = pd.DataFrame(decisions)

    result.to_csv(OUTPUT_FILE, index=False)

    print("\nFeeFlow Controller - Control Decisions")
    print("=" * 45)

    print(f"Cases processed : {len(result)}")
    print(f"Auto clear      : {(result['action'] == 'AUTO_CLEAR').sum()}")
    print(f"Human review    : {(result['action'] == 'HUMAN_REVIEW').sum()}")
    print(f"Blocked         : {(result['action'] == 'BLOCK').sum()}")

    print("\nSeverity:")
    print(result["severity"].value_counts())

    print("\nException types:")
    print(result["exception_code"].value_counts())

    print(f"\nOutput written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()