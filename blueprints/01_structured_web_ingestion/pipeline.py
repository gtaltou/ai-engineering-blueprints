"""Blueprint 01: End-to-End Structured Web Intelligence Ingestion Pipeline."""

import html
import re
from dataclasses import dataclass

from pydantic import HttpUrl

from blueprint_core.contracts.web_schemas import (
    ContentCategory,
    ExtractedInsight,
    WebPageIntelligence,
)
from blueprint_core.gateways.smart_router import SmartRouter
from blueprint_core.observability.telemetry import ExecutionTracer
from blueprint_core.resilience.budget_guard import BudgetGuard


@dataclass(frozen=True)
class RawWebDocument:
    """Raw web payload prior to HTML sanitization and structured LLM extraction."""

    url: str
    raw_html_or_text: str


class WebIngestionPipeline:
    """Sanitizes raw web content and extracts strictly typed intelligence via SmartRouter."""

    def __init__(self, router: SmartRouter) -> None:
        self.router = router

    @staticmethod
    def sanitize_content(raw_content: str, max_chars: int = 8000) -> str:
        """Strip script/style tags, HTML markup, and normalize whitespace."""
        no_scripts = re.sub(
            r"<(script|style)[^>]*>.*?</\1>",
            " ",
            raw_content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        no_tags = re.sub(r"<[^>]+>", " ", no_scripts)
        unescaped = html.unescape(no_tags)
        normalized = re.sub(r"\s+", " ", unescaped).strip()
        return normalized[:max_chars]

    @staticmethod
    def build_extraction_prompt(url: str, clean_text: str) -> str:
        """Construct a deterministic system/user prompt for contract extraction."""
        return (
            f"Analyze the following web document from URL: {url}\n"
            "Extract the structured intelligence strictly adhering to the output schema.\n"
            "Ground all insights in the provided text without hallucinating external facts.\n\n"
            f"--- DOCUMENT CONTENT ---\n{clean_text}"
        )

    def run(self, document: RawWebDocument) -> WebPageIntelligence:
        """Execute sanitization and resilient structured extraction."""
        clean_text = self.sanitize_content(document.raw_html_or_text)
        if len(clean_text) < 20:
            raise ValueError("Sanitized document content is too short for meaningful extraction.")

        prompt = self.build_extraction_prompt(document.url, clean_text)
        return self.router.execute_structured(prompt, WebPageIntelligence)


def run_demo() -> None:
    """Run a self-contained demonstration of the pipeline with simulated execution."""
    guard = BudgetGuard(max_budget_usd=0.05)
    tracer = ExecutionTracer()

    def simulated_cloud_executor(
        prompt: str, response_model: type[WebPageIntelligence]
    ) -> tuple[WebPageIntelligence, int, int]:
        result = WebPageIntelligence(
            source_url=HttpUrl("https://engineering.example.com/llm-gateways"),
            title="Production LLM Gateways: FinOps and Failover Patterns",
            category=ContentCategory.TECHNICAL_ARTICLE,
            executive_summary=(
                "An architectural deep-dive into building resilient AI gateways that combine "
                "strict schema enforcement with deterministic budget circuit breakers."
            ),
            key_insights=[
                ExtractedInsight(
                    topic="Contract-First Output Validation",
                    summary=(
                        "Pydantic validation at the gateway boundary eliminates "
                        "malformed JSON downstream."
                    ),
                    confidence_score=0.98,
                ),
                ExtractedInsight(
                    topic="Hybrid Local Failover",
                    summary=(
                        "Routing to local open-weights models preserves uptime "
                        "during cloud outages."
                    ),
                    confidence_score=0.94,
                ),
            ],
            entities_mentioned=["Pydantic", "OpenAI", "Ollama", "FinOps"],
            model_used="gpt-4o-mini",
        )
        return response_model.model_validate(result.model_dump()), 850, 320

    router = SmartRouter(
        budget_guard=guard,
        tracer=tracer,
        cloud_executor=simulated_cloud_executor,  # type: ignore[arg-type]
    )
    pipeline = WebIngestionPipeline(router=router)

    sample_doc = RawWebDocument(
        url="https://engineering.example.com/llm-gateways",
        raw_html_or_text=(
            "<html><head><script>console.log('tracking');</script></head>"
            "<body><h1>Production LLM Gateways: FinOps and Failover Patterns</h1>"
            "<p>Building resilient AI gateways requires combining strict Pydantic schema "
            "enforcement with deterministic FinOps budget circuit breakers and local "
            "Ollama failover.</p></body></html>"
        ),
    )

    intelligence = pipeline.run(sample_doc)
    trace = tracer.events[-1]

    print("=== Structured Web Intelligence Output ===")
    print(intelligence.model_dump_json(indent=2))
    print("\n=== Execution Telemetry & FinOps Ledger ===")
    print(
        f"Provider: {trace.provider} | Model: {trace.model} | "
        f"Latency: {trace.latency_ms}ms | Cost: ${trace.cost_usd:.6f} | "
        f"Remaining Budget: ${guard.remaining_budget_usd:.6f}"
    )


if __name__ == "__main__":
    run_demo()
