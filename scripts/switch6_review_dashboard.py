"""Utility to inspect Switch 6 segment and pain dashboards before activation."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path
from typing import Iterable

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional dependency fallback
    pd = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


def _print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def _display_segment(segment_csv: Path, limit: int) -> None:
    if pd is None:
        print("pandas is not available; unable to render segment preview.")
        return
    if not segment_csv.exists():
        print(f"Segment CSV not found at {segment_csv}")
        return
    df = pd.read_csv(segment_csv)
    _print_header(f"Segment Preview ({min(limit, len(df))} rows)")
    print(df.head(limit).to_string(index=False))


def _collect_dashboards(paths: Iterable[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def _open_dashboards(paths: Iterable[Path]) -> None:
    for path in paths:
        print(f"Opening {path}")
        webbrowser.open(path.resolve().as_uri())


def main() -> None:
    parser = argparse.ArgumentParser(description="Review Switch 6 research dashboards.")
    parser.add_argument("--segment-csv", type=Path, default=Path("data/switch6_segment.csv"))
    parser.add_argument(
        "--dashboard-dir",
        type=Path,
        default=Path("dashboards"),
        help="Directory containing switch6_funnel.html and switch6_pain_scores.html",
    )
    parser.add_argument("--limit", type=int, default=10, help="Rows of the segment CSV to display")
    parser.add_argument("--open", action="store_true", help="Open funnel and pain dashboards in the browser")
    args = parser.parse_args()

    _display_segment(args.segment_csv, args.limit)

    funnel = args.dashboard_dir / "switch6_funnel.html"
    pain = args.dashboard_dir / "switch6_pain_scores.html"
    dashboards = _collect_dashboards([funnel, pain])
    if not dashboards:
        print(f"No dashboards found under {args.dashboard_dir}")
    else:
        _print_header("Available dashboards")
        for path in dashboards:
            print(f" - {path}")
        if args.open:
            _open_dashboards(dashboards)


if __name__ == "__main__":
    main()
