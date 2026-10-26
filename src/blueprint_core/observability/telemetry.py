"""Structured telemetry and execution tracing for LLM gateways."""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class TraceEvent:
    """Immutable telemetry record for a single LLM gateway invocation."""

    operation: str
    provider: str
    model: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    fallback_triggered: bool
    success: bool
    error_message: str | None = None
    timestamp_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionTracer:
    """Collects structured execution traces across pipeline runs."""

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    def record(self, event: TraceEvent) -> None:
        """Append a verified TraceEvent to the in-memory ledger."""
        self._events.append(event)

    @property
    def events(self) -> list[TraceEvent]:
        """Return a defensive copy of recorded trace events."""
        return list(self._events)

    @staticmethod
    def start_timer() -> float:
        """Return high-resolution performance counter timestamp."""
        return time.perf_counter()

    @staticmethod
    def elapsed_ms(start_time: float) -> float:
        """Calculate elapsed milliseconds since start_time."""
        return round((time.perf_counter() - start_time) * 1000.0, 2)
