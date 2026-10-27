# AI Engineering Blueprints

Production-grade architectural blueprints for building resilient, contract-first, and cost-controlled AI systems.

## Architectural Posture

Unlike prototype notebooks, every blueprint in this repository enforces four core engineering invariants:

1. **Contract-First Boundaries**: All LLM outputs are strictly validated against Pydantic v2 schemas (`src/blueprint_core/contracts/`). Malformed responses never leak into downstream business logic.
2. **FinOps Circuit Breaking**: Deterministic token-cost tracking (`BudgetGuard`) halts or reroutes execution before runaway cloud API spend occurs.
3. **Hybrid Cloud-to-Local Failover**: The `SmartRouter` gateway automatically fails over from primary cloud models (`gpt-4o-mini`) to local open-weights inference (`llama3.2` via Ollama) on timeout, rate-limit, or budget exhaustion.
4. **Structured Observability**: Every gateway invocation emits an immutable `TraceEvent` recording latency, token usage, USD cost, and failover status.

## Repository Structure

- `blueprints/01_structured_web_ingestion/`: Slice 1 - HTML sanitization and structured extraction
- `docs/adr/001-hybrid-cloud-local-routing.md`: Architectural trade-off documentation
- `src/blueprint_core/`: Shared resilient kernel (Contracts, FinOps, Observability, Gateways)
- `tests/unit/`: Offline deterministic test suite
- `tasks.ps1` & `Makefile`: Cross-platform quality gate automation

## Quickstart (Windows PowerShell)

1. Install package and development dependencies: `.\tasks.ps1 install`
2. Run the full quality gate (Ruff + Mypy --strict + Pytest): `.\tasks.ps1 check`
3. Execute Blueprint 01 demo: `python blueprints/01_structured_web_ingestion/pipeline.py`

## Blueprint Catalog

| Blueprint | Architectural Focus | Status |
| :--- | :--- | :--- |
| [01 - Structured Web Ingestion](blueprints/01_structured_web_ingestion/README.md) | HTML sanitization, Pydantic v2 contract enforcement, FinOps guardrails, and hybrid routing | Production Ready |

## Architecture Decision Records (ADRs)

- [ADR-001: Hybrid Cloud-to-Local LLM Routing with Hard FinOps Circuit Breaker](docs/adr/001-hybrid-cloud-local-routing.md)
