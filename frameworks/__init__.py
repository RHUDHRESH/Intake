from .adapt_engine import ADAPTFrameworkEngine

try:  # pragma: no cover - optional heavy dependency
    from .switch6_engine import Switch6FrameworkEngine
except Exception:  # pragma: no cover
    Switch6FrameworkEngine = None  # type: ignore

from .big_idea_pipeline import BigIdeaPipeline, BigIdeaRequest

__all__ = [
    "ADAPTFrameworkEngine",
    "BigIdeaPipeline",
    "BigIdeaRequest",
]

if Switch6FrameworkEngine is not None:
    __all__.append("Switch6FrameworkEngine")
