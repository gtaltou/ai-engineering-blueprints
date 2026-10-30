# AI Engineering Blueprints

[![CI Quality Gate](https://github.com/gtaltou/ai-engineering-blueprints/actions/workflows/ci.yml/badge.svg)](https://github.com/gtaltou/ai-engineering-blueprints/actions/workflows/ci.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)
![Mypy Strict](https://img.shields.io/badge/mypy-strict-brightgreen.svg)
![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)

Production-grade architectural patterns for building **resilient**, **contract-first**, and **cost-bounded** AI systems in Python.

Unlike notebook-driven prototypes, every blueprint in this repository enforces strict **Pydantic v2 data contracts**, **hybrid Cloud-to-Local failover**, **FinOps circuit breakers**, and **100% deterministic unit testing** (`mypy --strict`, `ruff`, `pytest`).

---

## Core Architectural Pillars (`src/blueprint_core/`)

| Module | Responsibility | Key Engineering Pattern |
| :--- | :--- | :--- |
| `contracts/` | Input/Output schema enforcement | Strict Pydantic v2 models (`extra="forbid"`, cross-field validators) |
| `gateways/` | Model execution & routing | `SmartRouter` with automatic Cloud -> Local failover |
| `resilience/` | FinOps cost governance | `BudgetGuard` hard-cap circuit breaker before token execution |
| `retrieval/` | Hybrid search & grounding | `HybridRRFIndex` (Lexical IDF + Dense Cosine) & citation verification |
| `agents/` | Bounded autonomous loops | `ReflectiveAgentRunner` with `ToolRegistry` allow-listing & verifier feedback |
| `observability/` | Structured telemetry | `ExecutionTracer` capturing latency, token usage, and fallback events |

---

## Architectural Blueprints Catalog

| Blueprint | Focus Area | Key Guardrails | Status |
| :--- | :--- | :--- | :--- |
| **`01_structured_web_ingestion`** | Unstructured HTML -> Validated Domain Entities | Pre-LLM HTML sanitization, entity normalization, FinOps budget cap | Production Ready |
| **`02_hybrid_rag_reranking`** | Hybrid Retrieval (RRF) & Citation Grounding | Reciprocal Rank Fusion (`k=60`), post-generation `CitationHallucinationError` | Production Ready |
| **`03_agentic_tool_use_and_reflection`** | Bounded Agentic State Machine (`Reason -> Act -> Verify`) | Allow-listed `ToolRegistry`, `ToolHallucinationError`, `MaxAgentStepsExceededError` | Production Ready |

---

## Architecture Decision Records (ADRs)

- **[ADR-001: Hybrid Cloud-to-Local LLM Routing & FinOps Circuit Breaking](docs/adr/001-hybrid-cloud-local-routing.md)**
- **[ADR-002: Hybrid RRF Retrieval and Deterministic Citation Verification](docs/adr/002-hybrid-rag-and-citation-verification.md)**
- **[ADR-003: Bounded Agentic Reflection and Deterministic Tool Allow-Listing](docs/adr/003-bounded-agentic-reflection.md)**

---

## Quick Start & Quality Gate

1. **Install dependencies:** `.\tasks.ps1 install`
2. **Run full quality gate (`ruff` + `mypy --strict` + `pytest`):** `.\tasks.ps1 check`
3. **Run Blueprint 01 Demo:** `python blueprints/01_structured_web_ingestion/pipeline.py`
4. **Run Blueprint 02 Demo:** `python blueprints/02_hybrid_rag_reranking/pipeline.py`
5. **Run Blueprint 03 Demo:** `python blueprints/03_agentic_tool_use_and_reflection/pipeline.py`
