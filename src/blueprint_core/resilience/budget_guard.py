"""FinOps budget enforcement and token cost calculation."""

from dataclasses import dataclass, field


class BudgetExceededError(RuntimeError):
    """Raised when a requested operation exceeds the configured USD session budget."""


@dataclass
class ModelPricing:
    """Cost per 1,000,000 tokens in USD."""

    input_per_million: float
    output_per_million: float


DEFAULT_PRICING_TABLE: dict[str, ModelPricing] = {
    "gpt-4o-mini": ModelPricing(input_per_million=0.15, output_per_million=0.60),
    "gpt-4o": ModelPricing(input_per_million=2.50, output_per_million=10.00),
    "llama3.2": ModelPricing(input_per_million=0.0, output_per_million=0.0),
}


@dataclass
class BudgetGuard:
    """Tracks cumulative LLM spend and enforces hard FinOps circuit breaking."""

    max_budget_usd: float = 1.00
    pricing_table: dict[str, ModelPricing] = field(
        default_factory=lambda: dict(DEFAULT_PRICING_TABLE)
    )
    current_spend_usd: float = field(default=0.0, init=False)

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate the USD cost for a specific model and token usage."""
        pricing = self.pricing_table.get(model, ModelPricing(0.0, 0.0))
        input_cost = (max(0, input_tokens) / 1_000_000) * pricing.input_per_million
        output_cost = (max(0, output_tokens) / 1_000_000) * pricing.output_per_million
        return round(input_cost + output_cost, 8)

    def check_can_spend(self, projected_cost_usd: float = 0.0) -> None:
        """Raise BudgetExceededError if budget is exhausted or projected spend exceeds limit."""
        if (
            self.current_spend_usd >= self.max_budget_usd
            or (self.current_spend_usd + projected_cost_usd) > self.max_budget_usd
        ):
            raise BudgetExceededError(
                f"FinOps Circuit Breaker triggered: spend ${self.current_spend_usd:.6f} "
                f"+ projected ${projected_cost_usd:.6f} reaches/exceeds limit "
                f"${self.max_budget_usd:.6f}."
            )

    def record_usage(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Record token consumption, update cumulative spend, and return call cost in USD."""
        cost = self.estimate_cost(model, input_tokens, output_tokens)
        self.current_spend_usd = round(self.current_spend_usd + cost, 8)
        return cost

    @property
    def remaining_budget_usd(self) -> float:
        """Return remaining available budget in USD."""
        return max(0.0, round(self.max_budget_usd - self.current_spend_usd, 8))
