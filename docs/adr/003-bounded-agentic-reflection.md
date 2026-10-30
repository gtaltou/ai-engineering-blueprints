# ADR-003: Bounded Agentic Reflection and Deterministic Tool Allow-Listing

- **Status:** Accepted
- **Date:** 2026-10-30
- **Deciders:** Principal AI Systems Architecture

## Context

Autonomous LLM agents that rely on unconstrained `while True` ReAct loops or dynamic code execution introduce three severe production risks:
1. **Runaway Token Spend & Infinite Loops:** Models can get stuck repeating failed tool calls or oscillating between thoughts, exhausting API budgets and SLAs.
2. **Tool Hallucination & Privilege Escalation:** Models may invent tool names, pass malformed arguments, or attempt to invoke unapproved system operations.
3. **Unverified Final Outputs:** Self-reflection performed purely inside a single prompt lacks deterministic enforcement, allowing policy-violating answers to reach end users.

## Decision

We implement a **Bounded Generator-Verifier State Machine** (`ReflectiveAgentRunner`) backed by three strict engineering guardrails:

1. **Contract-First Step Decisions (`AgentStepDecision`):** Every reasoning step is validated via Pydantic v2 invariants (`CALL_TOOL` vs `FINAL_ANSWER` mutual exclusivity) before any side effect occurs.
2. **Deterministic Tool Allow-Listing (`ToolRegistry`):** The agent can only invoke explicitly registered callables. Any attempt to call an unregistered tool raises a hard `ToolHallucinationError` immediately.
3. **Bounded Reflection Loop (`MaxAgentStepsExceededError`):** Candidate final answers are evaluated by an external deterministic `AnswerVerifier`. If verification fails, structured feedback is injected into the next step's prompt, strictly capped by `max_steps` and guarded by `BudgetGuard`.

## Consequences

- **Positive:** Predictable upper-bound latency and FinOps cost per agent invocation (`max_steps * step_cost`). Zero tolerance for hallucinated tool execution.
- **Negative:** Complex open-ended exploratory tasks that genuinely require dozens of unconstrained steps will hit `MaxAgentStepsExceededError` and must be decomposed into smaller deterministic workflows.
