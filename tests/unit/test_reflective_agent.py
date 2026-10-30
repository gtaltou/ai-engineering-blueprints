"""Unit tests for the bounded ReflectiveAgentRunner and ToolRegistry."""

from __future__ import annotations

from typing import TypeVar

import pytest
from pydantic import BaseModel

from blueprint_core.agents.reflective_runner import (
    MaxAgentStepsExceededError,
    ReflectiveAgentRunner,
    ToolHallucinationError,
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


class SequenceAgentExecutor:
    """Replays a deterministic sequence of AgentStepDecision objects."""

    def __init__(self, decisions: list[AgentStepDecision]) -> None:
        self._decisions = decisions
        self._idx = 0

    def __call__(self, prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        decision = self._decisions[min(self._idx, len(self._decisions) - 1)]
        self._idx += 1
        parsed = response_model.model_validate(decision.model_dump())
        return parsed, 150, 60


def _build_router(decisions: list[AgentStepDecision]) -> SmartRouter:
    executor = SequenceAgentExecutor(decisions)
    return SmartRouter(
        cloud_executor=executor,
        local_executor=executor,
        budget_guard=BudgetGuard(max_budget_usd=1.0),
        tracer=ExecutionTracer(),
    )


def test_reflective_agent_executes_tool_and_self_corrects() -> None:
    """Agent should call a tool, fail verification once, and self-correct on step 3."""
    decisions = [
        AgentStepDecision(
            thought="Call metrics tool first.",
            action_type=AgentActionType.CALL_TOOL,
            tool_call=ToolCallRequest(
                tool_name="get_status",
                arguments={"cluster": "eu-1"},
                rationale="Check cluster health.",
            ),
        ),
        AgentStepDecision(
            thought="Drafting answer without ticket code.",
            action_type=AgentActionType.FINAL_ANSWER,
            final_answer="Cluster eu-1 is degraded.",
        ),
        AgentStepDecision(
            thought="Adding required RUNBOOK reference after verifier feedback.",
            action_type=AgentActionType.FINAL_ANSWER,
            final_answer="Cluster eu-1 is degraded. Follow RUNBOOK-101.",
        ),
    ]
    registry = ToolRegistry()
    registry.register("get_status", lambda args: f"{args['cluster']}: degraded")

    runner = ReflectiveAgentRunner(
        router=_build_router(decisions),
        tool_registry=registry,
        verifier=lambda ans: VerificationResult(
            is_valid="RUNBOOK-" in ans,
            feedback="Missing RUNBOOK reference.",
        ),
        max_steps=4,
    )

    result = runner.run("Check cluster eu-1")
    assert result.steps_taken == 3
    assert len(result.tool_History) == 1
    assert "RUNBOOK-101" in result.final_answer


def test_tool_registry_blocks_hallucinated_tool() -> None:
    """Agent must fail fast with ToolHallucinationError if an unknown tool is requested."""
    decisions = [
        AgentStepDecision(
            thought="Attempt to run unapproved shell tool.",
            action_type=AgentActionType.CALL_TOOL,
            tool_call=ToolCallRequest(
                tool_name="exec_root_shell",
                arguments={"cmd": "rm -rf /"},
                rationale="Unapproved action.",
            ),
        )
    ]
    registry = ToolRegistry()
    registry.register("safe_lookup", lambda _: "ok")

    runner = ReflectiveAgentRunner(
        router=_build_router(decisions),
        tool_registry=registry,
        max_steps=3,
    )

    with pytest.raises(ToolHallucinationError, match="exec_root_shell"):
        runner.run("Run diagnostics")


def test_agent_enforces_max_steps_circuit_breaker() -> None:
    """Agent must raise MaxAgentStepsExceededError when stuck in a tool or reflection loop."""
    decisions = [
        AgentStepDecision(
            thought="Keep calling tool forever.",
            action_type=AgentActionType.CALL_TOOL,
            tool_call=ToolCallRequest(
                tool_name="ping",
                arguments={},
                rationale="Ping check.",
            ),
        )
    ]
    registry = ToolRegistry()
    registry.register("ping", lambda _: "pong")

    runner = ReflectiveAgentRunner(
        router=_build_router(decisions),
        tool_registry=registry,
        max_steps=2,
    )

    with pytest.raises(MaxAgentStepsExceededError, match="within 2 steps"):
        runner.run("Infinite loop task")
