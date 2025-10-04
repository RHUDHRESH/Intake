# Strategic Marketing Intake System

## Overview

A next-generation marketing intake system built with LangGraph, LangChain, and adaptive intelligence for strategic lead qualification and market intelligence gathering.

## Vision

This system will replace legacy agent-based architectures with:

- **Adaptive Questioning**: Dynamic intake forms that adapt based on user type, industry, and responses
- **Market Intelligence Integration**: Real-time market data from ADAPT/Switch 6 for intelligent ICP generation
- **Strategic Orchestration**: LangGraph-powered workflows for intelligent lead qualification
- **Position Validation**: Automated validation of positioning and messaging fit

## Architecture

### Core Technologies
- **LangGraph**: Advanced workflow orchestration and state management
- **LangChain**: Intelligent agent coordination and tool integration
- **Adaptive Intake Engine**: Dynamic form generation based on context
- **Market Intelligence API**: Real-time market data integration
- **Strategic Validation**: Automated positioning and ICP analysis

### Key Features
- Dynamic questionnaire adaptation
- Real-time market intelligence integration
- Intelligent lead scoring and qualification
- Automated positioning validation
- Strategic workflow orchestration
- Context-aware agent coordination


## Ogilvy Big Idea Pipeline

- `OpenAIEmbeddingService` encodes the Ogilvy corpus with `text-embedding-3-large` and provides deterministic fallbacks when the OpenAI API is unavailable.
- `BigIdeaKnowledgeBase` reads from `data/big_idea_corpus.json` to supply historically proven headline inspiration.
- `BigIdeaPipeline` retrieves inspirations, prompts GPT-5 Nano heuristics, scores clarity, assembles mockups, and guards claims via the double-your-sales heuristic.
- `graphs.big_idea_graph` exposes LangGraph nodes (`retrieve_examples`, `generate_big_ideas`, `clarity_check`, `design_mockup`, `claim_validation`, `output_dashboard`) so the workflow can run with retries/timeouts.
- Run `python -m pytest tests/test_big_idea_pipeline.py` to validate the pipeline and graph offline.

## Switch 6 Research Engine

The Switch 6 engine now runs a complete research pipeline for six stages (segment ? wound ? reframe ? offer ? action ? cash):

- **Segmentation enrichment** with LinkedIn/Crunchbase prospect stubs, enrichment heuristics, email deliverability scoring, CSV export, and Chroma traceability.
- **Pain-point quantification** using review scraping fallbacks, LDA topic modelling, sentiment scoring, business-impact estimation, and Markdown-ready footnotes.
- **Market reframing** via Google Trends comparisons, competitor feature/price snapshots, and LLM-generated reframes ranked for clarity and creativity.
- **Offer packaging** that produces tiered bundles, differentiator summaries, and margin analytics.
- **Action planning** with CTA variants, CTR benchmarks, UTM suggestions, and analytics tags.
- **Cash flow projections** including payment link stubs, CAC-aware revenue projections, and Plotly dashboards (expected vs. actual funnel plus pain bar chart).
- Every stage emits a `research_confidence` score and inline citations; the full run aggregates them into `framework_completion_score` and a citation appendix.

### Manual workflows

```bash
# Refresh research for one or many profiles
python scripts/switch6_refresh.py --config my_switch6_profiles.json --output-dir reports/switch6

# Preview the latest segment CSV and open dashboards
python scripts/switch6_review_dashboard.py --segment-csv data/switch6_segment.csv --open
```

- `scripts/switch6_refresh.py` accepts `--refresh-every <minutes>` to loop continuously—ideal for cron/Task Scheduler.
- `scripts/generate_switch6_sample.py` produces a sample JSON artifact under `data/examples/` (requires pandas/numpy wheel support).

## Testing

Run the Switch 6 integration test with mocked external services:

```bash
python -m pytest Intake/tests/test_switch6_engine.py
```

> The test module skips automatically if optional scientific dependencies (pandas/numpy) are missing or incompatible. Install the project requirements inside `.venv` for deterministic results.

## Legacy Notice

This repository previously contained basic agent orchestration and web crawling functionality. That legacy system has been completely removed to make way for the strategic rebuild with modern LangGraph/LangChain architecture.

## Next Steps

1. Implement LangGraph orchestration framework
2. Build adaptive intake engine
3. Integrate market intelligence APIs
4. Develop strategic validation algorithms
5. Create intelligent agent coordination system

## Market Research Agent

- Modular interfaces (`PageFetcher`, `HTMLParser`, `NLPAnalyzer`, `StorageAdapter`) enable dependency injection and straightforward test doubles.
- Configurable discovery/analysis sub-graphs split crawling from NLP indexing, each guarded with circuit breakers, bulkheads, and conditional skip edges for resilience.
- Structured telemetry (Prometheus metrics + JSON logs) and optional OpenTelemetry spans make runs observable end-to-end.
- CLI (`python scripts/mra_cli.py`) scaffolds configs, validates YAML/JSON, runs ad-hoc analyses, and inspects positioning scores.

## Position Validator Engine

- Scoring modules are now pluggable (`Adapt`, `Switch6`, `Ogilvy`, `Godin`, `Hybrid`) and weighted via config, with explainable feedback (severity + text) per evidence.
- Dual-mode readiness: heuristics run locally; LLM feedback kicks in automatically when `OPENAI_API_KEY` is present.
