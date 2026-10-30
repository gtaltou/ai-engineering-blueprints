"""Blueprint 03: Bounded Agentic Tool Use and Generator-Verifier Reflection."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from blueprint_core.agents.reflective_runner import (
    ReflectiveAgentRunner,
    ToolRegistry,
)
from blueprint_core.contracts.agent_schemas import (
    AgentActionType,
    AgentStepDecision,
    ToolCallRequest,
    VerificationResult,
)
from blueprint_core.gateways.smart_router import SmartRouter
from blueprint_core.observability.telemetry import ExecutionTracer
from blueprint_core.resilience.budget_guard import BudgetGuard

T = TypeVar("T", bound=BaseModel)


class DeterministicAgentExecutor:
    """Simulates a 3-step Tool -> Failed Verification -> Self-Corrected Answer flow."""

    def __init__(self) -> None:
        self._call_count = 0

    def __call__(self, prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        self._call_count += 1

        if self._call_count == 1:
            decision = AgentStepDecision(
                thought="Need to inspect live metrics for payments-eu-west first.",
                action_type=AgentActionType.CALL_TOOL,
                tool_call=ToolCallRequest(
                    tool_name="query_service_metrics",
                    arguments={"service": "payments-eu-west"},
                    rationale="Fetch p99 latency and connection pool saturation.",
                ),
            )
        elif self._call_count == 2:
            decision = AgentStepDecision(
                thought="Metrics show DB pool saturation at 98%. Proposing mitigation.",
                action_type=AgentActionType.FINAL_ANSWER,
                final_answer=(
                    "Root cause: DB connection pool saturation (98%) on payments-eu-west. "
                    "Action: Drain stale replicas and increase pool cap to 250."
                ),
                self_critique_passed=True,
            )
        else:
            decision = AgentStepDecision(
                thought="Verifier rejected previous draft due to missing runbook ID. Fixing.",
                action_type=AgentActionType.FINAL_ANSWER,
                final_answer=(
                    "Root cause: DB connection pool saturation (98%) on payments-eu-west. "
                    "Action: Drain stale replicas per [RUNBOOK-PLAT-402]."
                ),
                self_critique_passed=True,
            )

        parsed = response_model.model_validate(decision.model_dump())
        return parsed, 210, 95


def run_demo() -> None:
    """Execute the Blueprint 03 reflective agent demonstration."""
    tracer = ExecutionTracer()
    budget = BudgetGuard(max_budget_usd=0.05)
    executor = DeterministicAgentExecutor()

    router = SmartRouter(
        cloud_executor=executor,
        local_executor=executor,
        budget_guard=budget,
        tracer=tracer,
    )

    registry = ToolRegistry()
    registry.register(
        "query_service_metrics",
        lambda args: (
            f"service={args.get('service')} | p99_ms=1840 | db_pool_saturation=98% | "
            "recommended_runbook=RUNBOOK-PLAT-402"
        ),
    )

    def require_runbook_verifier(answer: str) -> VerificationResult:
        if "RUNBOOK-" not in answer:
            return VerificationResult(
                is_valid=False,
                feedback="Final answer must cite an official 'RUNBOOK-XXXX' identifier.",
            )
        return VerificationResult(is_valid=True, feedback="Verified.")

    runner = ReflectiveAgentRunner(
        router=router,
        tool_registry=registry,
        verifier=require_runbook_verifier,
        max_steps=4,
    )

    result = runner.run(task="Diagnose high latency on payments-eu-west and provide remediation.")

    print("=== Blueprint 03: Reflective Agent Result ===")
    print(f"Steps Taken : {result.steps_taken} (includes 1 self-correction cycle)")
    print(f"Tools Used  : {[obs.tool_name for obs in result.tool_History]}")
    print(f"Final Answer: {result.final_answer}")
    print(f"Total Spend : ${budget.current_spend_usd:.6f} / ${budget.max_budget_usd:.2f}")


if __name__ == "__main__":
    run_demo()
