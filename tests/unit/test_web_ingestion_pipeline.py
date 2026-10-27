"""Unit tests for Blueprint 01 WebIngestionPipeline."""

import importlib.util
from pathlib import Path
from typing import Any, TypeVar

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


def _load_pipeline_module() -> Any:
    module_path = (
        Path(__file__).resolve().parents[2]
        / "blueprints"
        / "01_structured_web_ingestion"
        / "pipeline.py"
    )
    spec = importlib.util.spec_from_file_location("web_ingestion_pipeline", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_html_sanitization_strips_scripts_and_tags() -> None:
    """Ensure scripts, styles, and HTML tags are cleanly removed before LLM ingestion."""
    mod = _load_pipeline_module()
    raw = (
        "<html><script>alert(1)</script><style>body{}</style>"
        "<body><h1>Title</h1><p>Clean &amp; clear.</p></body></html>"
    )
    cleaned = mod.WebIngestionPipeline.sanitize_content(raw)
    assert cleaned == "Title Clean & clear."


def test_pipeline_rejects_empty_or_short_documents() -> None:
    """Verify pipeline raises ValueError before calling LLM if content is too short."""
    mod = _load_pipeline_module()
    router = SmartRouter(budget_guard=BudgetGuard(), tracer=ExecutionTracer())
    pipeline = mod.WebIngestionPipeline(router=router)
    short_doc = mod.RawWebDocument(
        url="https://example.com",
        raw_html_or_text="<p>Too short</p>",
    )

    with pytest.raises(ValueError, match="too short"):
        pipeline.run(short_doc)


def test_pipeline_end_to_end_extraction() -> None:
    """Verify full pipeline execution from raw HTML to validated WebPageIntelligence."""
    mod = _load_pipeline_module()
    guard = BudgetGuard(max_budget_usd=0.50)
    tracer = ExecutionTracer()

    def mock_cloud(prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        assert "Clean architectural content" in prompt
        payload = WebPageIntelligence(
            source_url=HttpUrl("https://example.com/post"),
            title="Architectural Post",
            category=ContentCategory.DOCUMENTATION,
            executive_summary="Detailed documentation on resilient ingestion pipelines.",
            key_insights=[
                ExtractedInsight(
                    topic="Sanitization",
                    summary="Removing HTML tags reduces input token costs significantly.",
                    confidence_score=0.92,
                )
            ],
            entities_mentioned=["Python", "Pydantic"],
            model_used="gpt-4o-mini",
        ).model_dump()
        return response_model.model_validate(payload), 400, 200

    router = SmartRouter(budget_guard=guard, tracer=tracer, cloud_executor=mock_cloud)
    pipeline = mod.WebIngestionPipeline(router=router)
    doc = mod.RawWebDocument(
        url="https://example.com/post",
        raw_html_or_text=(
            "<div><h1>Architectural Post</h1>"
            "<p>Clean architectural content for extraction.</p></div>"
        ),
    )

    result = pipeline.run(doc)
    assert result.title == "Architectural Post"
    assert result.category == ContentCategory.DOCUMENTATION
    assert len(tracer.events) == 1
