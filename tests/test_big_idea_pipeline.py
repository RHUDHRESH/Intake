"""Tests for the Big Idea pipeline and LangGraph workflow."""

from frameworks.big_idea_pipeline import (
    BigIdeaPipeline,
    BigIdeaRequest,
    OpenAIEmbeddingService,
)
from graphs import compile_big_idea_graph


def _sample_request() -> BigIdeaRequest:
    return BigIdeaRequest(
        brand="Boostly Ads",
        positioning_statement=(
            "We help local restaurants fill tables with reliable digital campaigns."
        ),
        audience="Local restaurant owners in tier-1 Indian cities",
        benefit="generate more leads",
        emotional_hook="committed to making a difference",
    )


def test_big_idea_pipeline_generates_headlines() -> None:
    pipeline = BigIdeaPipeline(embedding_service=OpenAIEmbeddingService(api_key=None))
    result = pipeline.run(_sample_request())

    headlines = result["headlines"]
    assert len(headlines) == 3
    for item in headlines:
        assert item["headline"], "Each generated item should include a headline"
        clarity = item["clarity"]
        assert "word_count" in clarity and clarity["word_count"] > 0
        assert "power_word_density" in clarity

    kb_meta = result["knowledge_base"]
    assert kb_meta["embedding_model"] == "text-embedding-3-large"
    assert kb_meta["size"] >= 5


def test_big_idea_graph_runs_end_to_end() -> None:
    graph = compile_big_idea_graph()
    result = graph.invoke(
        {
            "request": {
                "brand": "Boostly Ads",
                "positioning_statement": (
                    "We help local restaurants fill tables with reliable digital campaigns."
                ),
                "audience": "Local restaurant owners in tier-1 Indian cities",
                "benefit": "generate more leads",
                "emotional_hook": "committed to making a difference",
            }
        }
    )

    dashboard = result["dashboard"]
    assert dashboard["brand"] == "Boostly Ads"
    assert len(dashboard["headlines"]) == 3
    first = dashboard["headlines"][0]
    assert first["headline"], "Headline text should be present"
    assert "clarity" in first and "mockup" in first and "claim_validation" in first
