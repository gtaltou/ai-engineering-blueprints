"""Bounded agentic runner with strict tool registry and generator-verifier reflection."""

from __future__ import annotations

from collections.abc import Callable

from blueprint_core.contracts.agent_schemas import (
    AgentActionType,
    AgentExecutionResult,
    AgentStepDecision,
    ToolCallRequest,
    ToolObservation,
    VerificationResult,
)
from blueprint_core.gateways.smart_router import SmartRouter

ToolCallable = Callable[[dict[str, str | int | float | bool]], str]
AnswerVerifier = Callable[[str], VerificationResult]


class ToolHallucinationError(RuntimeError):
    """Raised when the model attempts to invoke an unregistered tool."""


class MaxAgentStepsExceededError(RuntimeError):
    """Raised when the agent loop reaches max_steps without a verified answer."""


class ToolRegistry:
    """Allow-listed registry of deterministic tools exposed to the agent."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolCallable] = {}

    def register(self, name: str, func: ToolCallable) -> None:
        """Register a named tool callable."""
        if not name or not name.strip():
            raise ValueError("Tool name must not be empty.")
        self._tools[name.strip()] = func

    @property
    def registered_tools(self) -> list[str]:
        """Return sorted list of registered tool names."""
        return sorted(self._tools.keys())

    def execute(self, request: ToolCallRequest) -> ToolObservation:
        """Execute a validated tool request or raise ToolHallucinationError."""
        if request.tool_name not in self._tools:
            allowed = ", ".join(self.registered_tools) or "none"
            raise ToolHallucinationError(
                f"Hallucinated tool '{request.tool_name}'. Allowed tools: [{allowed}]"
            )
        tool_fn = self._tools[request.tool_name]
        try:
            output = tool_fn(request.arguments)
            return ToolObservation(
                tool_name=request.tool_name,
                output=str(output),
                is_error=False,
            )
        except Exception as exc:  # noqa: BLE001
            return ToolObservation(
                tool_name=request.tool_name,
                output=f"ToolExecutionError: {exc}",
                is_error=True,
            )


class ReflectiveAgentRunner:
    """Executes a bounded Reason -> Act -> Verify/Reflect state machine."""

    def __init__(
        self,
        router: SmartRouter,
        tool_registry: ToolRegistry,
        verifier: AnswerVerifier | None = None,
        max_steps: int = 4,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")
        self._router = router
        self._tools = tool_registry
        self._verifier = verifier
        self._max_steps = max_steps

    def run(self, task: str) -> AgentExecutionResult:
        """Run the bounded reflective loop until verified completion or step cap."""
        if not task or not task.strip():
            raise ValueError("Agent task must not be empty.")

        observations: list[ToolObservation] = []
        reflection_feedback: list[str] = []

        for step_idx in range(1, self._max_steps + 1):
            prompt = self._build_step_prompt(
                task=task,
                step_idx=step_idx,
                observations=observations,
                reflection_feedback=reflection_feedback,
            )
            decision = self._router.execute_structured(
                prompt=prompt,
                response_model=AgentStepDecision,
            )

            if decision.action_type == AgentActionType.CALL_TOOL:
                assert decision.tool_call is not None
                observation = self._tools.execute(decision.tool_call)
                observations.append(observation)
                continue

            candidate_answer = decision.final_answer or ""
            if self._verifier is not None:
                verification = self._verifier(candidate_answer)
                if not verification.is_valid:
                    reflection_feedback.append(
                        f"Step {step_idx} verification failed: {verification.feedback}"
                    )
                    continue

            return AgentExecutionResult(
                task=task,
                final_answer=candidate_answer,
                steps_taken=step_idx,
                tool_History=observations,
            )

        raise MaxAgentStepsExceededError(
            f"Agent failed to produce a verified answer within {self._max_steps} steps."
        )

    def _build_step_prompt(
        self,
        task: str,
        step_idx: int,
        observations: list[ToolObservation],
        reflection_feedback: list[str],
    ) -> str:
        tools_str = ", ".join(self._tools.registered_tools) or "none"
        obs_lines = [
            f"- [{obs.tool_name}] (error={obs.is_error}): {obs.output}" for obs in observations
        ]
        obs_block = "\n".join(obs_lines) if obs_lines else "None"
        feedback_block = "\n".join(reflection_feedback) if reflection_feedback else "None"
        return (
            f"Task: {task}\n"
            f"Step: {step_idx}/{self._max_steps}\n"
            f"Allowed Tools: [{tools_str}]\n"
            f"Tool Observations:\n{obs_block}\n"
            f"Verifier Reflection Feedback:\n{feedback_block}\n"
        )
