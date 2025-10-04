from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from frameworks.switch6_engine import Switch6FrameworkEngine  # noqa: E402


class InMemoryRepository:
    def __init__(self) -> None:
        self.records = {}

    def store(self, stage: str, content: str, metadata: dict | None = None) -> str:
        doc_id = f"{stage}-{len(self.records) + 1}"
        self.records[doc_id] = {"content": content, "metadata": metadata or {}}
        return doc_id


def main() -> None:
    engine = Switch6FrameworkEngine(repository=InMemoryRepository())
    sample_profile = {
        "user_type": "startup_founder",
        "business_industry": "SaaS",
        "primary_goal": "Accelerate onboarding",
        "main_challenge": "Revenue churn during activation",
        "what_you_do": "AI onboarding co-pilot",
        "competitors": ["FlowLoop", "ActivateHQ", "Onboardly"],
        "customer_lifetime_value": "$1800",
        "base_price": 1500,
    }
    result = engine.execute_full_framework(sample_profile)
    output_dir = Path("data/examples")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "switch6_sample.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Sample Switch 6 output written to {output_path}")


if __name__ == "__main__":
    main()
