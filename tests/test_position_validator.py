from position_validator import (
    AdaptScoringModule,
    GodinScoringModule,
    OgilvyScoringModule,
    PositionValidatorEngine,
    Switch6ScoringModule,
)
from position_validator.engine import ModuleConfig


def test_position_validator_weighted_scores():
    engine = PositionValidatorEngine(
        [
            AdaptScoringModule(),
            Switch6ScoringModule(),
            OgilvyScoringModule(),
            GodinScoringModule(),
        ]
    )
    overrides = {
        "ogilvy": ModuleConfig(name="ogilvy", weight=2.0),
        "godin": ModuleConfig(name="godin", enabled=False),
    }
    result = engine.score("We help growth teams escape churn with proof-backed onboarding", module_overrides=overrides)
    assert 0 <= result["score"] <= 1
    enabled_modules = {item["module"] for item in result["module_results"]}
    assert "godin" not in enabled_modules
    assert result["feedback"]
