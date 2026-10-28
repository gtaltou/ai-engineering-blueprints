# AI Engineering Blueprints

[![CI Quality Gate](https://github.com/RostaneF/ai-engineering-blueprints/actions/workflows/ci.yml/badge.svg)](https://github.com/RostaneF/ai-engineering-blueprints/actions/workflows/ci.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)
![Mypy](https://img.shields.io/badge/types-mypy%20strict-blue.svg)

Production-grade architectural patterns for resilient, observable, and cost-controlled LLM systems.

Rather than notebook prototypes or fragile prompt wrappers, this repository provides **Contract-First**, **FinOps-aware**, and **fault-tolerant** reference architectures designed for production AI engineering.

---

## Core Architectural Pillars

Every blueprint in this repository is built atop a shared, strictly typed foundational kernel (`src/blueprint_core/`):

1. **Contract-First Execution (`contracts/`)**: All LLM outputs are strictly validated against Pydantic v2 schemas (`extra="forbid"`). Raw unvalidated strings never cross module boundaries.
2. **Hybrid Cloud-to-Local Failover (`gateways/smart_router.py`)**: Primary cloud models automatically fail over to zero-cost local inference (e.g., Ollama) upon API timeouts, rate limits, or budget exhaustion.
3. **FinOps Circuit Breakers (`resilience/budget_guard.py`)**: Real-time token spend tracking halts or reroutes execution before runaway loops or traffic spikes breach hard USD limits.
4. **Structured Telemetry (`observability/telemetry.py`)**: Every inference call emits structured latency, token usage, cost, and routing state metrics.

---

## Repository Structure

```text
ai-engineering-blueprints/
├── blueprints/
│   ├── 01_structured_web_ingestion/   # HTML sanitization & structured extraction
│   └── 02_hybrid_rag_reranking/       # Hybrid RRF retrieval & citation verification
├── docs/
│   └── adr/                           # Architecture Decision Records
│       ├── 001-hybrid-cloud-local-routing.md
│       └── 002-hybrid-rag-rrf-and-citation-grounding.md
├── src/
│   └── blueprint_core/                # Shared resilient AI kernel
│       ├── contracts/                 # Strict Pydantic v2 schemas (Web, RAG)
│       ├── gateways/                  # SmartRouter (Cloud -> Local failover)
│       ├── observability/             # ExecutionTracer & structured logs
│       ├── resilience/                # BudgetGuard FinOps circuit breaker
│       └── retrieval/                 # Hybrid RRF index & grounded RAG pipeline
└── tests/
    └── unit/                          # Deterministic, zero-network unit test suite
```

---

## Blueprint Catalog

| Blueprint | Architectural Focus | Key Patterns | Status |
| :--- | :--- | :--- | :--- |
| **`01_structured_web_ingestion`** | Noise-reduction & schema-enforced extraction | HTML Sanitization, Contract-First Extraction, FinOps Guard | ✅ Production-Ready |
| **`02_hybrid_rag_reranking`** | Hallucination-free technical retrieval & QA | Lexical + Dense RRF Fusion, Post-Generation Citation Guardrail | ✅ Production-Ready |

---

## Quick Start

### 1. Environment Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\tasks.ps1 install
```

### 2. Run the Quality Gate (Lint + Format + Strict Types + Tests)

```powershell
.\tasks.ps1 check
```

### 3. Execute Blueprint Demos

**Blueprint 01 — Structured Web Ingestion:**
```powershell
python blueprints/01_structured_web_ingestion/pipeline.py
```

**Blueprint 02 — Hybrid RAG & Citation Verification:**
```powershell
python blueprints/02_hybrid_rag_reranking/pipeline.py
```

---

## Architecture Decision Records (ADRs)

* **[ADR-001: Hybrid Cloud-to-Local LLM Routing with FinOps Budget Circuit Breaker](docs/adr/001-hybrid-cloud-local-routing.md)**
* **[ADR-002: Hybrid RAG with Reciprocal Rank Fusion (RRF) and Post-Generation Citation Verification](docs/adr/002-hybrid-rag-rrf-and-citation-grounding.md)**
