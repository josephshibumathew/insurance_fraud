"""Simple benchmark regression gate used in CI."""

from __future__ import annotations

import json
from pathlib import Path

BASELINE_FILE = Path("tests/performance/baseline_metrics.json")
CURRENT_FILE = Path("tests/performance/current_metrics.json")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    baseline = load_json(BASELINE_FILE)
    current = load_json(CURRENT_FILE)

    if not baseline or not current:
        print("Benchmark regression check skipped (baseline/current metrics not found).")
        return 0

    failures = []
    for key, baseline_value in baseline.items():
        current_value = current.get(key)
        if current_value is None:
            continue
        if current_value > baseline_value * 1.20:
            failures.append((key, baseline_value, current_value))

    if failures:
        for key, b, c in failures:
            print(f"Regression detected for {key}: baseline={b} current={c}")
        return 1

    print("No significant benchmark regressions detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
