import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

try:
    import pandas as pd
except Exception as import_error:  # pragma: no cover - environment specific
    pytest.skip(f"pandas import failed: {import_error}", allow_module_level=True)

from frameworks.switch6_engine import (
    ProspectRecord,
    Switch6FrameworkEngine,
    RevenueModeler,
)


class FakeProspectClient:
    def fetch(self, keyword: str, limit: int):
        return [
            ProspectRecord(
                email=f"{keyword.replace(' ', '_')}@example.com",
                full_name=f"{keyword.title()} Owner",
                job_title="Operations Lead",
                company=f"{keyword.title()} Labs",
                company_size="51-200",
                industry="SaaS",
                source="fake_linkedin",
                location="Remote",
            ),
            ProspectRecord(
                email=f"{keyword.replace(' ', '_')}_2@example.com",
                full_name=f"{keyword.title()} Director",
                job_title="Growth Director",
                company=f"{keyword.title()} Studio",
                company_size="201-500",
                industry="SaaS",
                source="fake_crunchbase",
                location="Austin",
            ),
        ]


class FakeReviewScraper:
    def scrape(self, keyword, sources=None):
        timestamp = datetime.now(timezone.utc).isoformat()
        return [
            {
                "url": "https://example.com/review-1",
                "content": f"{keyword} churn and onboarding friction",
                "fetched_at": timestamp,
            },
            {
                "url": "https://example.com/review-2",
                "content": f"Teams mention {keyword} causing manual ops",
                "fetched_at": timestamp,
            },
        ]


class FakeTopicModeler:
    def model(self, documents):
        return [
            ("churn onboarding", 0.82),
            ("manual operations", 0.61),
            ("slow integration", 0.44),
        ]


class FakeGoogleTrendsClient:
    def compare_terms(self, primary_term, competitor_terms):
        idx = pd.date_range(end=datetime.now(), periods=3, freq="M")
        data = {primary_term: [60, 64, 67]}
        for competitor in competitor_terms:
            data[competitor] = [45, 48, 50]
        return pd.DataFrame(data, index=idx)


class FakeCompetitorFetcher:
    def fetch(self, competitors):
        return [
            {
                "name": competitor,
                "base_price": 999 + idx * 200,
                "features": ["Onboarding support", "Analytics", "Live training"],
                "url": f"https://example.com/{competitor}",
            }
            for idx, competitor in enumerate(competitors)
        ]


class FakeLLMReframer:
    def generate(self, brief, count=5):
        return [f"{brief} alternative #{i}" for i in range(count)]

    def rank(self, statements):
        scored = []
        for idx, statement in enumerate(statements):
            scored.append(
                {
                    "statement": statement,
                    "creativity": 0.6 + idx * 0.05,
                    "clarity": 0.9,
                    "composite": round(0.75 + idx * 0.04, 3),
                }
            )
        return scored


class InMemoryRepository:
    def __init__(self):
        self.records = {}

    def store(self, stage, content, metadata=None):
        doc_id = f"{stage}-{len(self.records) + 1}"
        self.records[doc_id] = {"content": content, "metadata": metadata or {}}
        return doc_id


class FakeDashboardBuilder:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def build(self, segment_csv: str, pain_points):
        funnel = self.base_dir / "funnel.html"
        pain = self.base_dir / "pain.html"
        funnel.write_text("funnel-dashboard")
        pain.write_text(json.dumps(pain_points, default=str))
        return {"funnel": str(funnel), "pain": str(pain)}


def test_switch6_engine_full_flow(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    repository = InMemoryRepository()
    engine = Switch6FrameworkEngine(
        prospect_clients=[FakeProspectClient()],
        review_scraper=FakeReviewScraper(),
        topic_modeler=FakeTopicModeler(),
        trends_client=FakeGoogleTrendsClient(),
        competitor_fetcher=FakeCompetitorFetcher(),
        llm_reframer=FakeLLMReframer(),
        repository=repository,
        dashboard_builder=FakeDashboardBuilder(tmp_path / "dashboards"),
        revenue_modeler=RevenueModeler(export_dir=tmp_path / "projections"),
    )

    data = {
        "user_type": "startup_founder",
        "what_you_do": "AI onboarding assistant",
        "business_industry": "SaaS",
        "primary_goal": "Improve retention",
        "main_challenge": "Customers churn before onboarding completes",
        "customer_lifetime_value": "$1200",
        "competitors": ["Contender One", "Contender Two", "Contender Three"],
    }

    result = engine.execute_full_framework(data)

    assert result["framework"] == "Switch 6"
    assert 0 < result["framework_completion_score"] <= 1
    assert result["citations"]

    segment_stage = result["stages"]["segment"]
    assert segment_stage["prospect_count"] >= 2
    assert Path(segment_stage["csv_file"]).exists()
    assert Path(segment_stage["preview_dashboard"]).exists()

    wound_stage = result["stages"]["wound"]
    assert len(wound_stage["pain_points"]) == 3
    assert any("estimated_monthly_loss" in pain for pain in wound_stage["pain_points"])

    reframe_stage = result["stages"]["reframe"]
    assert len(reframe_stage["reframe_statements"]) == 5
    assert reframe_stage["top_trend_terms"]

    offer_stage = result["stages"]["offer"]
    assert offer_stage["differentiators"]["unique_benefits"]

    action_stage = result["stages"]["action"]
    assert action_stage["benchmark_source"]
    assert len(action_stage["cta_variants"]) == 3

    cash_stage = result["stages"]["cash"]
    assert cash_stage["dashboard_paths"]["funnel"].endswith("funnel.html")
    assert cash_stage["payment_links"]["stripe"]

    assert len(repository.records) >= 5

