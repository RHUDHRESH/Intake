import json

from research.position_generator import PositionGeneratorAgent


class StubLLM:
    def __call__(self, prompt: str) -> str:
        return json.dumps(
            [
                "We help SaaS teams unlock onboarding clarity in 30 days.",
                "Our Switch6 lab crushes churn with guided activation sprints.",
                "Your RevOps tribe wins loyalty through signal-driven playbooks.",
            ]
        )


def test_position_generator_ranking_deterministic():
    agent = PositionGeneratorAgent(llm=StubLLM())
    context = {
        "user_type": "startup_founder",
        "what_you_do": "AI onboarding assistant",
        "main_challenge": "Customers churn before onboarding completes",
        "position_statement": "We activate users with human-led AI sequences",
    }
    result = agent.execute(context, count=3)

    assert result["alternative_count"] == 3
    scores = [item["ranking_score"] for item in result["alternatives"]]
    assert scores == sorted(scores, reverse=True)
    for alt in result["alternatives"]:
        assert alt["statement"]
        assert 0.5 <= alt["opportunity_score"] <= 1.0
        assert 0.0 <= alt["fit_score"] <= 1.0
        assert "validation" in alt
        assert "rationale" in alt
