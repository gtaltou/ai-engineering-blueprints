"""Unit tests for SmartRouter, BudgetGuard, and WebPageIntelligence schemas."""

from typing import TypeVar

import pytest
from pydantic import BaseModel, HttpUrl

from blueprint_core.contracts.web_schemas import (
    ContentCategory,
    ExtractedInsight,
    WebPageIntelligence,
)
from blueprint_core.gateways.smart_router import SmartRouter
from blueprint_core.observability.telemetry import ExecutionTracer
from blueprint_core.resilience.budget_guard import BudgetGuard

T = TypeVar("T", bound=BaseModel)


def _build_mock_intelligence(model_name: str) -> WebPageIntelligence:
    return WebPageIntelligence(
        source_url=HttpUrl("https://example.com/architecture"),
        title="Resilient AI Systems",
        category=ContentCategory.TECHNICAL_ARTICLE,
        executive_summary="A comprehensive guide on building fault-tolerant LLM gateways.",
        key_insights=[
            ExtractedInsight(
                topic="Circuit Breaking",
                summary="Hard FinOps caps prevent runaway cloud API costs in production.",
                confidence_score=0.95,
            )
        ],
        entities_mentioned=["Pydantic", "OpenAI", "Ollama", "Pydantic"],
        model_used=model_name,
    )


def test_schema_entity_normalization() -> None:
    """Ensure duplicate entities are deduplicated and sorted alphabetically."""
    item = _build_mock_intelligence("gpt-4o-mini")
    assert item.entities_mentioned == ["Ollama", "OpenAI", "Pydantic"]


def test_smart_router_primary_cloud_success() -> None:
    """Verify normal execution path when cloud provider succeeds within budget."""
    guard = BudgetGuard(max_budget_usd=1.00)
    tracer = ExecutionTracer()

    def cloud_ok(prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        payload = _build_mock_intelligence("gpt-4o-mini").model_dump()
        return response_model.model_validate(payload), 1000, 500

    router = SmartRouter(
        budget_guard=guard,
        tracer=tracer,
        cloud_executor=cloud_ok,
    )

    response = router.execute_structured("Analyze page", WebPageIntelligence)
    assert response.model_used == "gpt-4o-mini"
    assert guard.current_spend_usd > 0.0
    assert len(tracer.events) == 1
    assert tracer.events[0].fallback_triggered is False
    assert tracer.events[0].provider == "cloud_primary"


def test_smart_router_failover_on_budget_exceeded() -> None:
    """Verify automatic failover to local model when FinOps budget cap is exceeded."""
    guard = BudgetGuard(max_budget_usd=0.0)
    tracer = ExecutionTracer()

    def cloud_should_not_run(prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        pytest.fail("Cloud executor should not be called when budget is exhausted.")

    def local_fallback(prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        payload = _build_mock_intelligence("llama3.2").model_dump()
        return response_model.model_validate(payload), 1200, 600

    router = SmartRouter(
        budget_guard=guard,
        tracer=tracer,
        cloud_executor=cloud_should_not_run,
        local_executor=local_fallback,
    )

    response = router.execute_structured("Analyze page", WebPageIntelligence)
    assert response.model_used == "llama3.2"
    assert guard.current_spend_usd == 0.0
    assert len(tracer.events) == 1
    assert tracer.events[0].fallback_triggered is True
    assert tracer.events[0].provider == "local_fallback"
