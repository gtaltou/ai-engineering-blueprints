"""Strict Pydantic v2 contracts for bounded agentic tool use and reflection."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentActionType(str, Enum):
    """Allowed transitions in the bounded agent state machine."""

    CALL_TOOL = "call_tool"
    FINAL_ANSWER = "final_answer"


class ToolCallRequest(BaseModel):
    """Structured tool invocation requested by the reasoning model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: str = Field(..., min_length=1, max_length=64)
    arguments: dict[str, str | int | float | bool] = Field(default_factory=dict)
    rationale: str = Field(..., min_length=5, max_length=500)


class ToolObservation(BaseModel):
    """Deterministic record of a tool execution result or error."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: str = Field(..., min_length=1, max_length=64)
    output: str = Field(..., min_length=1)
    is_error: bool = Field(default=False)


class AgentStepDecision(BaseModel):
    """Single step output produced by the LLM inside the reflective loop."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    thought: str = Field(..., min_length=5, max_length=1000)
    action_type: AgentActionType
    tool_call: ToolCallRequest | None = None
    final_answer: str | None = None
    self_critique_passed: bool = Field(
        default=True,
        description="Whether the agent verified its own output against constraints.",
    )

    @model_validator(mode="after")
    def validate_state_transition(self) -> AgentStepDecision:
        """Enforce mutually exclusive and complete state transitions."""
        if self.action_type == AgentActionType.CALL_TOOL and self.tool_call is None:
            raise ValueError("tool_call must be provided when action_type is 'call_tool'.")
        if self.action_type == AgentActionType.FINAL_ANSWER:
            if not self.final_answer or not self.final_answer.strip():
                raise ValueError(
                    "final_answer must be non-empty when action_type is 'final_answer'."
                )
            if not self.self_critique_passed:
                raise ValueError("Cannot emit final_answer when self_critique_passed is False.")
        return self


class VerificationResult(BaseModel):
    """Outcome of the deterministic verifier gate on a proposed final answer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_valid: bool
    feedback: str = Field(default="")


class AgentExecutionResult(BaseModel):
    """Final envelope returned by the bounded ReflectiveAgentRunner."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task: str
    final_answer: str
    steps_taken: int = Field(..., ge=1)
    tool_History: list[ToolObservation] = Field(default_factory=list)
