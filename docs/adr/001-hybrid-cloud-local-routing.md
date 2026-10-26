# ADR 001: Hybrid Cloud-to-Local LLM Routing with Contract-First Validation

## Status
Accepted

## Context
Production AI systems relying on a single commercial cloud LLM API are vulnerable to rate limits (HTTP 429), upstream outages (5xx), and unbounded token spend. Furthermore, consuming unvalidated raw text responses leads to brittle downstream parsing.

## Decision
We implement a unified `SmartRouter` gateway combining three architectural invariants:
1. **Contract-First Outputs**: Every gateway call requires a strict Pydantic `BaseModel` schema (`WebPageIntelligence`).
2. **FinOps Circuit Breaking**: A `BudgetGuard` inspects cumulative spend prior to cloud invocation and immediately trips when the session cap is reached.
3. **Zero-Cost Local Failover**: When the primary cloud provider raises an exception or trips the FinOps circuit breaker, execution seamlessly fails over to a local Ollama instance (`llama3.2`) enforcing the identical Pydantic contract.

## Consequences
* **Positive**: High availability, predictable cloud cost ceiling, deterministic data structures across providers, and full observability via `ExecutionTracer`.
* **Negative / Trade-offs**: Local quantized models exhibit lower reasoning accuracy on complex schemas and require local compute resources (RAM/VRAM).
