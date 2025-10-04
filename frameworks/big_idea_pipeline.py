"""Big Idea pipeline orchestrating knowledge base retrieval and generation."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore

LOGGER = logging.getLogger(__name__)

POWER_WORDS = {
    "double",
    "triple",
    "boost",
    "unlock",
    "discover",
    "explosive",
    "ultimate",
    "effortless",
    "secret",
    "transform",
    "instant",
    "guaranteed",
}


@dataclass
class BigIdeaRequest:
    """Payload describing the request for new Big Idea headlines."""

    brand: str
    positioning_statement: str
    audience: str
    benefit: str
    emotional_hook: Optional[str] = None
    product: Optional[str] = None
    benchmarks: Optional[List[Dict[str, Any]]] = None
    brand_voice: Optional[str] = None
    style: Optional[str] = None


class OpenAIEmbeddingService:
    """Wrapper around OpenAI embeddings with deterministic fallbacks."""

    def __init__(
        self,
        *,
        model: str = "text-embedding-3-large",
        api_key: Optional[str] = None,
        client: Optional[Any] = None,
        embedding_dim: int = 64,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.embedding_dim = embedding_dim
        self._client = client or self._init_client()

    def _init_client(self) -> Optional[Any]:
        if self.api_key and OpenAI is not None:
            try:
                return OpenAI(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover - network/runtime errors
                LOGGER.warning("Falling back to offline embeddings: %s", exc)
        return None

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        if self._client is not None:
            try:
                response = self._client.embeddings.create(model=self.model, input=list(texts))
                return [item.embedding for item in response.data]
            except Exception as exc:  # pragma: no cover - API fallback
                LOGGER.warning("OpenAI embeddings failed, using deterministic fallback: %s", exc)
        return [self._fallback_embedding(text) for text in texts]

    def _fallback_embedding(self, text: str) -> List[float]:
        seed_hex = hashlib.sha256(text.encode("utf-8")).hexdigest()
        seed = int(seed_hex[:16], 16)
        rng = random.Random(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(self.embedding_dim)]


class BigIdeaKnowledgeBase:
    """Manages corpus storage and retrieval using OpenAI embeddings."""

    def __init__(
        self,
        *,
        corpus_path: Optional[Path] = None,
        embedding_service: Optional[OpenAIEmbeddingService] = None,
    ) -> None:
        self.corpus_path = Path(corpus_path) if corpus_path else Path("data/big_idea_corpus.json")
        self.embedding_service = embedding_service or OpenAIEmbeddingService()
        self._records: List[Dict[str, Any]] = []
        self._embeddings: List[List[float]] = []
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        records = self._read_corpus()
        self._records = records
        texts = [self._record_to_text(record) for record in self._records]
        self._embeddings = self.embedding_service.embed_texts(texts)
        self._loaded = True

    def _read_corpus(self) -> List[Dict[str, Any]]:
        if self.corpus_path.is_file():
            try:
                data = json.loads(self.corpus_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception as exc:  # pragma: no cover - corrupt file
                LOGGER.warning("Failed to read corpus %s, using default: %s", self.corpus_path, exc)
        return self._default_corpus()

    def _record_to_text(self, record: Dict[str, Any]) -> str:
        parts = [record.get("headline", ""), record.get("campaign", ""), record.get("angle", "")]
        return " ".join(part for part in parts if part)

    def retrieve(self, query: str, *, top_k: int = 5) -> List[Dict[str, Any]]:
        self.load()
        if not query:
            return self._records[:top_k]
        query_embedding = self.embedding_service.embed_texts([query])[0]
        scored: List[Dict[str, Any]] = []
        for record, embedding in zip(self._records, self._embeddings):
            score = cosine_similarity(query_embedding, embedding)
            payload = {
                **record,
                "score": round(score, 4),
                "source": record.get("source", "ogilvy_corpus"),
            }
            scored.append(payload)
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[: top_k or 5]

    def _default_corpus(self) -> List[Dict[str, Any]]:
        return [
            {
                "headline": "At 60 miles an hour the loudest noise in this Rolls-Royce comes from the electric clock.",
                "campaign": "Rolls-Royce Silence Campaign",
                "angle": "Precision engineering and luxury serenity",
                "metrics": {"ctr": 0.12, "roi": 5.4},
                "source": "ogilvy_archive",
            },
            {
                "headline": "Only Dove is one-quarter moisturizing cream.",
                "campaign": "Dove Moisture Proof",
                "angle": "Unique product formulation",
                "metrics": {"ctr": 0.18, "roi": 4.7},
                "source": "ogilvy_archive",
            },
            {
                "headline": "How many engineers does it take to double your plant's output?",
                "campaign": "Industrial Efficiency Study",
                "angle": "Quantified performance promise",
                "metrics": {"ctr": 0.09, "roi": 3.1},
                "source": "industry_case",
            },
            {
                "headline": "The man in the Hathaway shirt.",
                "campaign": "Hathaway Shirt Eye Patch",
                "angle": "Character-driven storytelling",
                "metrics": {"ctr": 0.16, "roi": 6.0},
                "source": "ogilvy_archive",
            },
            {
                "headline": "They laughed when I sat down at the piano?but when I started to play!",
                "campaign": "Correspondence Course Propulsion",
                "angle": "Narrative transformation",
                "metrics": {"ctr": 0.2, "roi": 5.9},
                "source": "classic_dr",
            },
            {
                "headline": "Shave minutes off every flight without buying new aircraft.",
                "campaign": "Airline Operations Breakthrough",
                "angle": "Operational efficiency promise",
                "metrics": {"ctr": 0.11, "roi": 4.2},
                "source": "aviation_case",
            },
        ]


class BigIdeaPromptBuilder:
    """Assemble the Ogilvy-inspired prompt template."""

    def build(self, request: BigIdeaRequest, inspirations: Sequence[Dict[str, Any]]) -> str:
        lines = [
            "You are channeling David Ogilvy's direct-response craftsmanship.",
            f"Brand positioning: {request.positioning_statement}",
            f"Audience: {request.audience}",
            f"Primary benefit: {request.benefit}",
        ]
        if request.emotional_hook:
            lines.append(f"Emotional hook: {request.emotional_hook}")
        lines.append("Here are proven headlines for inspiration:")
        for idx, inspiration in enumerate(inspirations, 1):
            headline = inspiration.get("headline", "").strip()
            campaign = inspiration.get("campaign", "Unknown Campaign")
            lines.append(f"{idx}. {headline} ({campaign})")
        lines.append("Generate three concise, Ogilvy-grade Big Idea headlines.")
        if request.brand_voice:
            lines.append(f"Tone to mimic: {request.brand_voice}")
        if request.style:
            lines.append(f"Style notes: {request.style}")
        return "\n".join(lines)


class GPT5NanoClient:
    """Calls GPT-5 Nano when available, otherwise uses heuristics."""

    def __init__(self, *, openai_client: Optional[Any] = None, model: str = "gpt-5-nano") -> None:
        self.model = model
        if openai_client is not None:
            self._client = openai_client
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key and OpenAI is not None:
                try:
                    self._client = OpenAI(api_key=api_key)
                except Exception as exc:  # pragma: no cover
                    LOGGER.warning("Falling back to heuristic headline generation: %s", exc)
                    self._client = None
            else:
                self._client = None

    def generate(self, prompt: str, *, count: int = 3) -> List[str]:
        if self._client is not None:
            try:
                completion = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You write persuasive direct-response headlines."},
                        {"role": "user", "content": prompt},
                    ],
                    n=count,
                    temperature=0.7,
                )
                candidates = [
                    choice.message.content.strip()
                    for choice in completion.choices
                    if getattr(choice, "message", None) and choice.message.content
                ]
                filtered = [cand.splitlines()[0] for cand in candidates if cand]
                if filtered:
                    return filtered[:count]
            except Exception as exc:  # pragma: no cover - API fallback
                LOGGER.warning("GPT-5 Nano generation failed, using heuristic fallback: %s", exc)
        return self._fallback(prompt, count=count)

    def _fallback(self, prompt: str, *, count: int) -> List[str]:
        audience_match = re.search(r"Audience:\s*(.*)", prompt)
        benefit_match = re.search(r"Primary benefit:\s*(.*)", prompt)
        audience = audience_match.group(1).strip() if audience_match else "Customers"
        benefit = benefit_match.group(1).strip() if benefit_match else "Results"
        templates = [
            "How {audience} {verb} {benefit} Without {obstacle}",
            "{audience}: {verb} {benefit} In {timeframe}",
            "The {adjective} Shortcut to {benefit}",
            "Finally, {benefit} That {audience} Trust",
        ]
        verbs = ["Unlock", "Double", "Ignite", "Accelerate"]
        obstacles = ["guesswork", "wasted ad spend", "burnout"]
        timeframes = ["30 Days", "This Quarter", "Weeks"]
        adjectives = ["Proven", "Effortless", "Ogilvy-Tested", "High-Impact"]
        outputs: List[str] = []
        for idx in range(count):
            template = templates[idx % len(templates)]
            headline = template.format(
                audience=audience,
                benefit=benefit,
                verb=verbs[idx % len(verbs)],
                obstacle=obstacles[idx % len(obstacles)],
                timeframe=timeframes[idx % len(timeframes)],
                adjective=adjectives[idx % len(adjectives)],
            )
            outputs.append(headline)
        return outputs[:count]


class HeadlineClarityAnalyzer:
    """Scores headlines for clarity, length, and power language."""

    def __init__(self, *, ideal_word_range: Sequence[int] = (7, 12)) -> None:
        self.min_words, self.max_words = ideal_word_range

    def evaluate(self, headline: str) -> Dict[str, Any]:
        words = headline.split()
        word_count = len(words)
        syllables = sum(self._estimate_syllables(word) for word in words) or 1
        sentences = max(1, headline.count(".") + headline.count("!") + headline.count("?"))
        readability = 206.835 - 1.015 * (word_count / sentences) - 84.6 * (syllables / word_count)
        readability = max(0.0, min(120.0, readability))
        power_word_hits = [word for word in words if word.lower().strip(",.!?") in POWER_WORDS]
        density = len(power_word_hits) / word_count if word_count else 0.0
        suggestions: List[str] = []
        if word_count > self.max_words:
            suggestions.append("Trim to keep the headline punchy (aim for 10-15 words).")
        if word_count < self.min_words:
            suggestions.append("Add a detail so the promise feels tangible.")
        if readability < 45:
            suggestions.append("Simplify phrasing to boost readability.")
        if density < 0.1:
            suggestions.append("Add one bold action verb or power word.")
        return {
            "word_count": word_count,
            "readability": round(readability, 2),
            "power_word_density": round(density, 3),
            "power_words": power_word_hits,
            "suggestions": suggestions,
        }

    def _estimate_syllables(self, word: str) -> int:
        cleaned = re.sub(r"[^a-z]", "", word.lower())
        if not cleaned:
            return 1
        vowels = "aeiouy"
        count = 0
        prev_is_vowel = False
        for char in cleaned:
            is_vowel = char in vowels
            if is_vowel and not prev_is_vowel:
                count += 1
            prev_is_vowel = is_vowel
        if cleaned.endswith("e") and count > 1:
            count -= 1
        return max(count, 1)


class DesignMockupService:
    """Produces references to visual mockups for generated headlines."""

    def __init__(self, *, bucket: str = "ogilvy-big-ideas") -> None:
        self.bucket = bucket

    def generate(self, headline: str, request: BigIdeaRequest) -> Dict[str, Any]:
        slug = self._slugify(headline)[:48]
        uri = f"gs://{self.bucket}/mockups/{slug}.png"
        return {
            "headline": headline,
            "gcs_uri": uri,
            "preview_text": f"{headline} | {request.brand}",
        }

    def _slugify(self, text: str) -> str:
        clean = re.sub(r"[^a-z0-9]+", "-", text.lower())
        return clean.strip("-") or "headline"


class ClaimValidationEngine:
    """Applies the double-your-sales heuristic with simple realism checks."""

    CLAIM_PATTERNS = [
        re.compile(r"double", re.I),
        re.compile(r"triple", re.I),
        re.compile(r"\d+%"),
        re.compile(r"\d+x", re.I),
    ]

    def validate(self, headline: str, benchmarks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        needs_proof = any(pattern.search(headline) for pattern in self.CLAIM_PATTERNS)
        if not needs_proof:
            return {"status": "pass", "reason": "No quantified promise detected."}
        benchmark = self._select_benchmark(benchmarks)
        realism = self._heuristic_realism_check(headline, benchmark)
        status = "warn" if realism < 0.5 else "pass"
        return {
            "status": status,
            "reason": "Quantified claim requires validation.",
            "benchmark": benchmark,
            "realism_score": round(realism, 2),
        }

    def _select_benchmark(self, benchmarks: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        if benchmarks:
            return max(benchmarks, key=lambda item: item.get("confidence", 0.0))
        return {
            "source": "default_benchmark",
            "confidence": 0.35,
            "notes": "No campaign history provided; using conservative defaults.",
            "expected_roi": 1.6,
        }

    def _heuristic_realism_check(self, headline: str, benchmark: Dict[str, Any]) -> float:
        multiplier = 1.0
        lowered = headline.lower()
        if "double" in lowered:
            multiplier = 2.0
        elif "triple" in lowered:
            multiplier = 3.0
        elif match := re.search(r"(\d+)%", lowered):
            multiplier = 1 + int(match.group(1)) / 100
        elif match := re.search(r"(\d+)x", lowered):
            multiplier = int(match.group(1))
        baseline = benchmark.get("expected_roi", 1.5)
        return min(1.0, baseline / multiplier if multiplier else 0.0)


class FeedbackLoopManager:
    """Captures live campaign feedback to enrich the corpus."""

    def __init__(self, knowledge_base: BigIdeaKnowledgeBase) -> None:
        self._knowledge_base = knowledge_base

    def ingest(self, results: Iterable[Dict[str, Any]]) -> None:
        results = list(results)
        if not results:
            return
        self._knowledge_base.load()
        for result in results:
            headline = result.get("headline")
            if not headline:
                continue
            record = {
                "headline": headline,
                "campaign": result.get("campaign", "live_campaign"),
                "angle": result.get("angle", "performance_feedback"),
                "metrics": result.get("metrics", {}),
                "source": "campaign_feedback",
            }
            self._knowledge_base._records.append(record)
            text = self._knowledge_base._record_to_text(record)
            embedding = self._knowledge_base.embedding_service.embed_texts([text])[0]
            self._knowledge_base._embeddings.append(embedding)


class BigIdeaPipeline:
    """End-to-end coordinator for the Ogilvy Big Idea workflow."""

    def __init__(
        self,
        *,
        knowledge_base: Optional[BigIdeaKnowledgeBase] = None,
        embedding_service: Optional[OpenAIEmbeddingService] = None,
        headline_generator: Optional[GPT5NanoClient] = None,
        clarity_analyzer: Optional[HeadlineClarityAnalyzer] = None,
        mockup_service: Optional[DesignMockupService] = None,
        claim_validator: Optional[ClaimValidationEngine] = None,
    ) -> None:
        embedding_service = embedding_service or OpenAIEmbeddingService()
        self.knowledge_base = knowledge_base or BigIdeaKnowledgeBase(embedding_service=embedding_service)
        self.generator = headline_generator or GPT5NanoClient()
        self.prompt_builder = BigIdeaPromptBuilder()
        self.clarity_analyzer = clarity_analyzer or HeadlineClarityAnalyzer()
        self.mockup_service = mockup_service or DesignMockupService()
        self.claim_validator = claim_validator or ClaimValidationEngine()
        self.feedback_loop = FeedbackLoopManager(self.knowledge_base)

    def run(self, request: BigIdeaRequest) -> Dict[str, Any]:
        inspirations = self.knowledge_base.retrieve(
            f"{request.positioning_statement} {request.benefit}",
            top_k=5,
        )
        prompt = self.prompt_builder.build(request, inspirations)
        generated = self.generator.generate(prompt, count=3)
        headline_payloads: List[Dict[str, Any]] = []
        for headline in generated:
            clarity = self.clarity_analyzer.evaluate(headline)
            mockup = self.mockup_service.generate(headline, request)
            validation = self.claim_validator.validate(headline, request.benchmarks)
            headline_payloads.append(
                {
                    "headline": headline,
                    "clarity": clarity,
                    "mockup": mockup,
                    "claim_validation": validation,
                }
            )
        dashboard = {
            "brand": request.brand,
            "positioning": request.positioning_statement,
            "headlines": headline_payloads,
            "inspirations": inspirations,
        }
        return {
            "knowledge_base": {
                "size": len(self.knowledge_base._records),
                "embedding_model": self.knowledge_base.embedding_service.model,
            },
            "prompt": prompt,
            "inspirations": inspirations,
            "headlines": headline_payloads,
            "dashboard": dashboard,
        }

    def ingest_feedback(self, campaign_results: Iterable[Dict[str, Any]]) -> None:
        self.feedback_loop.ingest(campaign_results)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    a_slice = list(a[:length])
    b_slice = list(b[:length])
    dot = sum(x * y for x, y in zip(a_slice, b_slice))
    norm_a = math.sqrt(sum(x * x for x in a_slice))
    norm_b = math.sqrt(sum(y * y for y in b_slice))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


__all__ = [
    "BigIdeaRequest",
    "OpenAIEmbeddingService",
    "BigIdeaKnowledgeBase",
    "BigIdeaPipeline",
    "HeadlineClarityAnalyzer",
    "DesignMockupService",
    "ClaimValidationEngine",
]
