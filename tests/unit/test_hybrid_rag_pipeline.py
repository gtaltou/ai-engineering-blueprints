"""Unit tests for Blueprint 02: Hybrid RAG with RRF and Citation Verification."""

from __future__ import annotations

from typing import TypeVar

import pytest
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
    CitationHallucinationError,
    GroundedRAGPipeline,
    HybridRRFIndex,
)

T = TypeVar("T", bound=BaseModel)


def _deterministic_embedder(text: str) -> list[float]:
    """Deterministic toy embedding function mapping domain themes to orthogonal axes."""
    lowered = text.lower()
    return [
        1.0 if ("failover" in lowered or "resilience" in lowered or "backup" in lowered) else 0.1,
        1.0 if ("finops" in lowered or "budget" in lowered or "cost" in lowered) else 0.1,
        1.0 if ("error" in lowered or "code" in lowered or "err-" in lowered) else 0.1,
    ]


@pytest.fixture
def sample_chunks() -> list[DocumentChunk]:
    """Provide a small knowledge base covering exact error codes and semantic concepts."""
    return [
        DocumentChunk(
            chunk_id="doc-err-9042",
            source_uri="runbooks/gateway_errors.md",
            content=(
                "Error code ERR-9042 indicates an upstream rate-limit exhaustion "
                "on the primary cloud endpoint."
            ),
        ),
        DocumentChunk(
            chunk_id="doc-arch-failover",
            source_uri="docs/adr/001-routing.md",
            content=(
                "System resilience is guaranteed by automatic backup routing "
                "to local inference when cloud endpoints fail."
            ),
        ),
        DocumentChunk(
            chunk_id="doc-finops-cap",
            source_uri="docs/finops_policy.md",
            content=(
                "The FinOps circuit breaker halts cloud token spending "
                "when the session budget cap is reached."
            ),
        ),
    ]


def test_hybrid_rrf_surfaces_exact_sku_and_semantic_matches(
    sample_chunks: list[DocumentChunk],
) -> None:
    """Verify RRF ranks both exact identifier matches and semantic matches at the top."""
    index = HybridRRFIndex(embed_fn=_deterministic_embedder, rrf_k=60)
    index.index_chunks(sample_chunks)

    sku_results = index.search("What does ERR-9042 mean?", top_k=2)
    assert len(sku_results) == 2
    assert sku_results[0].chunk.chunk_id == "doc-err-9042"
    assert sku_results[0].lexical_rank == 1

    semantic_results = index.search(
        "How do we ensure resilience with backup routing?",
        top_k=2,
    )
    assert len(semantic_results) == 2
    assert semantic_results[0].chunk.chunk_id == "doc-arch-failover"


def test_grounded_rag_pipeline_returns_verified_answer_and_records_telemetry(
    sample_chunks: list[DocumentChunk],
) -> None:
    """Verify end-to-end grounded RAG execution with valid citations and FinOps tracking."""
    index = HybridRRFIndex(embed_fn=_deterministic_embedder)
    index.index_chunks(sample_chunks)

    def _valid_executor(prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        assert "doc-err-9042" in prompt
        answer = GroundedAnswer(
            answer="ERR-9042 indicates rate-limit exhaustion on the primary cloud endpoint.",
            citations=[
                GroundedCitation(
                    chunk_id="doc-err-9042",
                    supporting_quote=(
                        "Error code ERR-9042 indicates an upstream rate-limit exhaustion"
                    ),
                )
            ],
            confidence_score=0.96,
            has_sufficient_context=True,
        )
        return response_model.model_validate(answer.model_dump()), 140, 45

    budget_guard = BudgetGuard(max_budget_usd=1.00)
    tracer = ExecutionTracer()
    router = SmartRouter(
        budget_guard=budget_guard,
        tracer=tracer,
        cloud_executor=_valid_executor,
        local_executor=_valid_executor,
    )

    pipeline = GroundedRAGPipeline(index=index, router=router, top_k=2)
    response, retrieved = pipeline.answer_query("Explain error ERR-9042")

    assert response.has_sufficient_context is True
    assert response.citations[0].chunk_id == "doc-err-9042"
    assert len(retrieved) == 2
    assert len(tracer.events) == 1
    assert tracer.events[0].success is True


def test_grounded_rag_pipeline_blocks_hallucinated_chunk_id(
    sample_chunks: list[DocumentChunk],
) -> None:
    """Verify post-generation guardrail raises CitationHallucinationError on bad IDs."""
    index = HybridRRFIndex(embed_fn=_deterministic_embedder)
    index.index_chunks(sample_chunks)

    def _hallucinating_executor(
        prompt: str,
        response_model: type[T],
    ) -> tuple[T, int, int]:
        _ = prompt
        hallucinated = GroundedAnswer(
            answer="ERR-9042 is a database deadlock error.",
            citations=[
                GroundedCitation(
                    chunk_id="doc-invented-999",
                    supporting_quote="Invented quote from non-existent chunk.",
                )
            ],
            confidence_score=0.88,
            has_sufficient_context=True,
        )
        return response_model.model_validate(hallucinated.model_dump()), 110, 35

    router = SmartRouter(
        budget_guard=BudgetGuard(max_budget_usd=1.00),
        tracer=ExecutionTracer(),
        cloud_executor=_hallucinating_executor,
        local_executor=_hallucinating_executor,
    )

    pipeline = GroundedRAGPipeline(index=index, router=router, top_k=2)

    with pytest.raises(CitationHallucinationError, match="doc-invented-999"):
        pipeline.answer_query("Explain error ERR-9042")
