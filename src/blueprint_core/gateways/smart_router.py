"""Hybrid Cloud-to-Local LLM Router with Contract-First validation and FinOps guardrails."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

from blueprint_core.observability.telemetry import ExecutionTracer, TraceEvent
from blueprint_core.resilience.budget_guard import BudgetExceededError, BudgetGuard

T = TypeVar("T", bound=BaseModel)


class StructuredExecutor(Protocol):
    """Protocol for any LLM provider capable of fulfilling a Pydantic contract."""

    def __call__(self, prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        """Execute prompt and return (validated_model, input_tokens, output_tokens)."""
        ...


class SmartRouter:
    """Resilient gateway that routes structured LLM calls with automatic local failover."""

    def __init__(
        self,
        budget_guard: BudgetGuard,
        tracer: ExecutionTracer,
        primary_model: str = "gpt-4o-mini",
        fallback_model: str = "llama3.2",
        cloud_executor: StructuredExecutor | None = None,
        local_executor: StructuredExecutor | None = None,
    ) -> None:
        self.budget_guard = budget_guard
        self.tracer = tracer
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self._cloud_executor = cloud_executor
        self._local_executor = local_executor

    def execute_structured(self, prompt: str, response_model: type[T]) -> T:
        """Execute a prompt enforcing a Pydantic contract, failing over to local on cloud error."""
        start_time = self.tracer.start_timer()

        try:
            self.budget_guard.check_can_spend()
            if self._cloud_executor is None:
                raise RuntimeError("Cloud executor is not configured.")

            result, in_tokens, out_tokens = self._cloud_executor(prompt, response_model)
            cost = self.budget_guard.record_usage(self.primary_model, in_tokens, out_tokens)

            self.tracer.record(
                TraceEvent(
                    operation="structured_extraction",
                    provider="cloud_primary",
                    model=self.primary_model,
                    latency_ms=self.tracer.elapsed_ms(start_time),
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    cost_usd=cost,
                    fallback_triggered=False,
                    success=True,
                )
            )
            return result

        except (BudgetExceededError, Exception) as primary_err:
            fallback_start = self.tracer.start_timer()
            if self._local_executor is None:
                self.tracer.record(
                    TraceEvent(
                        operation="structured_extraction",
                        provider="cloud_primary",
                        model=self.primary_model,
                        latency_ms=self.tracer.elapsed_ms(start_time),
                        input_tokens=0,
                        output_tokens=0,
                        cost_usd=0.0,
                        fallback_triggered=False,
                        success=False,
                        error_message=str(primary_err),
                    )
                )
                raise

            result, in_tokens, out_tokens = self._local_executor(prompt, response_model)
            cost = self.budget_guard.record_usage(self.fallback_model, in_tokens, out_tokens)

            self.tracer.record(
                TraceEvent(
                    operation="structured_extraction",
                    provider="local_fallback",
                    model=self.fallback_model,
                    latency_ms=self.tracer.elapsed_ms(fallback_start),
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    cost_usd=cost,
                    fallback_triggered=True,
                    success=True,
                    error_message=f"Primary failed: {primary_err}",
                )
            )
            return result
