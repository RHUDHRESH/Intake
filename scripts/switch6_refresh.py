"""Switch 6 research refresh utility.

Run this script manually or schedule it with cron/Windows Task Scheduler to keep
segmentation, market signals, and pricing intelligence current.

Example:
    python scripts/switch6_refresh.py --config intake_targets.json --output-dir data/switch6_runs
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from frameworks.switch6_engine import Switch6FrameworkEngine  # noqa: E402


def _load_config(path: Path) -> List[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError("Config must be a dict or list of dicts")


def _write_result(result: dict, output_dir: Path, tag: str | None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    business = result.get("stages", {}).get("segment", {}).get("seed_keywords", ["business"])
    slug = "-".join(keyword.replace(" ", "_") for keyword in business[:2]) or "business"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if tag:
        filename = f"switch6_{slug}_{tag}_{timestamp}.json"
    else:
        filename = f"switch6_{slug}_{timestamp}.json"
    output_path = output_dir / filename
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return output_path


def _summarise(result: dict) -> str:
    stages = result.get("stages", {})
    summaries = []
    for name, payload in stages.items():
        confidence = payload.get("research_confidence", 0)
        summaries.append(f"{name}: conf={confidence}")
    return ", ".join(summaries)


def _run_once(engine: Switch6FrameworkEngine, profiles: Iterable[dict], output_dir: Path, dry_run: bool, tag: str | None) -> None:
    for profile in profiles:
        result = engine.execute_full_framework(profile)
        if dry_run:
            print(f"[DRY RUN] {profile.get('business_industry', 'business')} -> { _summarise(result)}")
            continue
        output_path = _write_result(result, output_dir, tag)
        print(f"Saved Switch6 research -> {output_path} :: {_summarise(result)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Switch 6 market intelligence.")
    parser.add_argument("--config", type=Path, required=True, help="Path to JSON file containing one or more business profiles.")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/switch6"), help="Directory to write results.")
    parser.add_argument("--tag", help="Optional tag appended to output filenames.")
    parser.add_argument("--dry-run", action="store_true", help="Calculate results without writing artifacts.")
    parser.add_argument(
        "--refresh-every",
        type=int,
        default=0,
        help="Minutes between automatic refresh runs (e.g., 60 = refresh every hour). 0 runs once and exits.",
    )
    args = parser.parse_args()

    profiles = _load_config(args.config)
    engine = Switch6FrameworkEngine()

    interval = max(args.refresh_every, 0)
    iteration = 0
    while True:
        iteration += 1
        print(f"\n=== Switch6 refresh iteration {iteration} ({datetime.now().isoformat(timespec='seconds')}) ===")
        _run_once(engine, profiles, args.output_dir, args.dry_run, args.tag)
        if interval == 0:
            break
        time.sleep(interval * 60)


if __name__ == "__main__":
    main()
