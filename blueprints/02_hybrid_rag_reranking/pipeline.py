"""Executable reference demo for Blueprint 02: Hybrid RAG with RRF and Citation Grounding."""

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
from blueprint_core.retrieval.hybrid_rag import GroundedRAGPipeline, HybridRRFIndex

T = TypeVar("T", bound=BaseModel)


def demo_embedder(text: str) -> list[float]:
    """Deterministic lightweight embedding projection for offline reproducibility."""
    lowered = text.lower()
    return [
        1.0 if ("failover" in lowered or "local" in lowered or "resilience" in lowered) else 0.1,
        1.0 if ("budget" in lowered or "finops" in lowered or "cost" in lowered) else 0.1,
        1.0 if ("err-9042" in lowered or "rate-limit" in lowered) else 0.1,
    ]


def simulated_cloud_rag_executor(
    prompt: str,
    response_model: type[T],
) -> tuple[T, int, int]:
    """Simulate a cloud LLM synthesizing a grounded answer with verifiable citations."""
    _ = prompt
    mock_payload = GroundedAnswer(
        answer=(
            "When error ERR-9042 occurs due to upstream cloud rate-limiting, the SmartRouter "
            "automatically fails over to the local Ollama model while the FinOps BudgetGuard "
            "enforces a strict session spending cap."
        ),
        citations=[
            GroundedCitation(
                chunk_id="runbook-err-9042",
                supporting_quote=(
                    "Error ERR-9042 signals primary cloud API rate-limit exhaustion."
                ),
            ),
            GroundedCitation(
                chunk_id="adr-001-failover",
                supporting_quote=(
                    "SmartRouter transitions execution to local Ollama inference upon failure."
                ),
            ),
        ],
        confidence_score=0.95,
        has_sufficient_context=True,
    )
    return response_model.model_validate(mock_payload.model_dump()), 220, 75


def run_demo() -> None:
    """Run the end-to-end Hybrid RRF + Citation Verification demonstration."""
    knowledge_base = [
        DocumentChunk(
            chunk_id="runbook-err-9042",
            source_uri="docs/runbooks/errors.md",
            content="Error ERR-9042 signals primary cloud API rate-limit exhaustion.",
        ),
        DocumentChunk(
            chunk_id="adr-001-failover",
            source_uri="docs/adr/001-hybrid-cloud-local-routing.md",
            content="SmartRouter transitions execution to local Ollama inference upon failure.",
        ),
        DocumentChunk(
            chunk_id="policy-finops-01",
            source_uri="docs/policies/finops.md",
            content="BudgetGuard halts paid API calls when cumulative spend exceeds the cap.",
        ),
    ]

    index = HybridRRFIndex(embed_fn=demo_embedder, rrf_k=60)
    index.index_chunks(knowledge_base)

    budget_guard = BudgetGuard(max_budget_usd=0.05)
    tracer = ExecutionTracer()
    router = SmartRouter(
        budget_guard=budget_guard,
        tracer=tracer,
        cloud_executor=simulated_cloud_rag_executor,
        local_executor=simulated_cloud_rag_executor,
    )

    rag_pipeline = GroundedRAGPipeline(index=index, router=router, top_k=2)
    query = "How does the architecture handle ERR-9042 and maintain resilience?"
    answer, retrieved = rag_pipeline.answer_query(query)

    print("=== Hybrid RRF Retrieved Chunks ===")
    for item in retrieved:
        print(
            f"- {item.chunk.chunk_id} | RRF={item.rrf_score:.5f} "
            f"(lexical_rank={item.lexical_rank}, semantic_rank={item.semantic_rank})"
        )

    print("\n=== Grounded RAG Answer (Pydantic Verified) ===")
    print(answer.model_dump_json(indent=2))

    print("\n=== FinOps & Telemetry Ledger ===")
    print(f"Remaining Budget: ${budget_guard.remaining_budget_usd:.6f} USD")
    for event in tracer.events:
        print(event)


if __name__ == "__main__":
    run_demo()
