"""Blueprint 02: Hybrid RAG with Reciprocal Rank Fusion (RRF) and Citation Grounding."""

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


def _demo_embedder(text: str) -> list[float]:
    """Deterministic toy embedding function for self-contained demonstration."""
    lowered = text.lower()
    return [
        1.0 if "err-9042" in lowered or "timeout" in lowered else 0.1,
        1.0 if "redis" in lowered or "pool" in lowered else 0.1,
        1.0 if "billing" in lowered or "invoice" in lowered else 0.1,
    ]


class _DemoGroundedExecutor:
    """Mock structured executor returning a strictly grounded answer."""

    def __call__(
        self,
        prompt: str,
        response_model: type[T],
    ) -> tuple[T, int, int]:
        _ = prompt
        answer = GroundedAnswer(
            answer=(
                "Error ERR-9042 is caused by Redis connection pool exhaustion under high "
                "concurrency. Increase max_connections from 10 to 50 to resolve it."
            ),
            has_sufficient_context=True,
            citations=[
                GroundedCitation(
                    chunk_id="doc-err-9042",
                    supporting_quote=(
                        "ERR-9042 occurs when the Redis connection pool is exhausted."
                    ),
                )
            ],
            confidence_score=0.96,
        )
        return response_model.model_validate(answer.model_dump()), 210, 85


def run_demo() -> None:
    """Execute the Hybrid RAG Blueprint demonstration."""
    chunks = [
        DocumentChunk(
            chunk_id="doc-billing-01",
            source_uri="kb://policies/billing",
            content="Invoices are generated on the 1st of every month in USD.",
        ),
        DocumentChunk(
            chunk_id="doc-err-9042",
            source_uri="kb://runbooks/redis-err-9042",
            content=(
                "Incident Runbook: ERR-9042 occurs when the Redis connection pool is "
                "exhausted. Remediation: increase max_connections from 10 to 50."
            ),
        ),
    ]

    index = HybridRRFIndex(embed_fn=_demo_embedder)
    index.index_chunks(chunks)

    budget_guard = BudgetGuard(max_budget_usd=1.00)
    tracer = ExecutionTracer()
    executor = _DemoGroundedExecutor()

    router = SmartRouter(
        cloud_executor=executor,
        local_executor=executor,
        budget_guard=budget_guard,
        tracer=tracer,
    )

    pipeline = GroundedRAGPipeline(index=index, router=router, top_k=2)
    query = "How do I fix ERR-9042 timeout in Redis?"
    answer, retrieved = pipeline.answer_query(query)

    print("=== Blueprint 02: Hybrid RAG & Citation Verification ===")
    print(f"Query: {query}")
    print(f"Top Retrieved Chunk: {retrieved[0].chunk.chunk_id} (RRF={retrieved[0].rrf_score:.4f})")
    print(f"Grounded Answer: {answer.answer}")
    print(f"Verified Citations: {[c.chunk_id for c in answer.citations]}")
    print(f"FinOps Spend (USD): ${budget_guard.current_spend_usd:.6f}")


if __name__ == "__main__":
    run_demo()
