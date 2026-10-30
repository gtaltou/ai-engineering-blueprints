"""Blueprint 02: Hybrid RAG with Reciprocal Rank Fusion (RRF) and Citation Grounding."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from blueprint_core.contracts.rag_schemas import (
    DocumentChunk,
    GroundedAnswer,
    GroundedCitation,
)
from blueprint_core.gateways.smart_router import SmartRouter
from blueprint_core.observability.telemetry import ExecutionTracer
from blueprint_core.resilience.budget_guard import BudgetGuard
from blueprint_core.retrieval.hybrid_rag import (
    GroundedRAGPipeline,
    HybridRRFIndex,
)

T = TypeVar("T", bound=BaseModel)


def _demo_embedder(text: str) -> list[float]:
    """Deterministic 3D keyword-density embedding function for reproducible execution."""
    lowered = text.lower()
    err_score = 1.0 if ("err-9042" in lowered or "pool" in lowered) else 0.1
    failover_score = 1.0 if ("failover" in lowered or "ollama" in lowered) else 0.1
    budget_score = 1.0 if ("budget" in lowered or "finops" in lowered) else 0.1
    return [err_score, failover_score, budget_score]


def _mock_rag_cloud_executor(prompt: str, response_model: type[T]) -> tuple[T, int, int]:
    """Deterministic structured generator returning grounded citations."""
    payload = GroundedAnswer(
        answer=(
            "To resolve error ERR-9042, drain stale replicas and reset the Redis pool "
            "while enforcing the FinOps hard budget cap on all gateway retries."
        ),
        citations=[
            GroundedCitation(
                chunk_id="runbook-err-9042",
                source_uri="kb://runbooks/redis-err-9042",
                supporting_quote="Mitigation for ERR-9042: drain stale replicas and reset pool.",
            ),
            GroundedCitation(
                chunk_id="policy-finops-01",
                source_uri="kb://policies/finops-budget",
                supporting_quote="BudgetGuard blocks cloud calls once spend hits max_budget_usd.",
            ),
        ],
        confidence_score=0.96,
        has_sufficient_context=True,
    )
    validated = response_model.model_validate(payload.model_dump())
    return validated, 240, 110


def run_demo() -> None:
    """Execute the end-to-end Hybrid RRF + Citation Verification RAG pipeline."""
    index = HybridRRFIndex(embedder=_demo_embedder, rrf_k=60)
    index.add_chunks(
        [
            DocumentChunk(
                chunk_id="runbook-err-9042",
                source_uri="kb://runbooks/redis-err-9042",
                content=(
                    "Incident Runbook ERR-9042: Connection pool exhausted on primary cluster. "
                    "Mitigation for ERR-9042: drain stale replicas and reset pool."
                ),
            ),
            DocumentChunk(
                chunk_id="adr-001-failover",
                source_uri="kb://architecture/adr-001",
                content=(
                    "Architecture Decision: When cloud latency spikes or errors occur, "
                    "SmartRouter automatically executes failover to local Ollama models."
                ),
            ),
            DocumentChunk(
                chunk_id="policy-finops-01",
                source_uri="kb://policies/finops-budget",
                content=(
                    "FinOps Governance Policy: BudgetGuard blocks cloud calls once spend "
                    "hits max_budget_usd."
                ),
            ),
        ]
    )

    budget = BudgetGuard(max_budget_usd=0.05)
    tracer = ExecutionTracer()
    router = SmartRouter(
        cloud_executor=_mock_rag_cloud_executor,
        local_executor=_mock_rag_cloud_executor,
        budget_guard=budget,
        tracer=tracer,
    )

    rag_pipeline = GroundedRAGPipeline(index=index, router=router, top_k=2)
    query = "How do we mitigate ERR-9042 under FinOps budget rules?"
    answer, retrieved = rag_pipeline.answer_query(query)

    print("=== Hybrid RRF Retrieved Context ===")
    for item in retrieved:
        print(
            f"- {item.chunk.chunk_id} | RRF={item.rrf_score:.5f} "
            f"(lex_rank={item.lexical_rank}, sem_rank={item.semantic_rank})"
        )

    print("\n=== Verified Grounded Answer ===")
    print(answer.model_dump_json(indent=2))


if __name__ == "__main__":
    run_demo()
