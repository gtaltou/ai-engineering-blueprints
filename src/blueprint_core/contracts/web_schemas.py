"""Contract-First Pydantic schemas for Web Intelligence ingestion."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ContentCategory(str, Enum):
    """Standardized taxonomy for ingested web pages."""

    TECHNICAL_ARTICLE = "technical_article"
    DOCUMENTATION = "documentation"
    RELEASE_NOTES = "release_notes"
    NEWS = "news"
    OTHER = "other"


class ExtractedInsight(BaseModel):
    """A single verifiable technical claim or takeaway extracted from the source."""

    topic: str = Field(
        ...,
        min_length=3,
        max_length=120,
        description="Concise subject of the insight.",
    )
    summary: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Factual explanation grounded strictly in the source text.",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence in the factual accuracy of the extraction (0.0 to 1.0).",
    )


class WebPageIntelligence(BaseModel):
    """Strict output contract for structured web page analysis."""

    source_url: HttpUrl = Field(..., description="Original URL of the analyzed document.")
    title: str = Field(..., min_length=1, max_length=300, description="Document title.")
    category: ContentCategory = Field(..., description="Primary classification of the page.")
    executive_summary: str = Field(
        ...,
        min_length=20,
        max_length=1500,
        description="High-level synthesis of the document's core value.",
    )
    key_insights: list[ExtractedInsight] = Field(
        default_factory=list,
        description="Structured list of technical insights found in the document.",
    )
    entities_mentioned: list[str] = Field(
        default_factory=list,
        description="Key technologies, organizations, or standards referenced.",
    )
    ingested_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the extraction occurred.",
    )
    model_used: str | None = Field(
        default=None,
        description="Identifier of the LLM provider/model that fulfilled the contract.",
    )

    @field_validator("entities_mentioned")
    @classmethod
    def normalize_entities(cls, v: list[str]) -> list[str]:
        """Deduplicate and strip whitespace from extracted entity names."""
        cleaned = {item.strip() for item in v if item.strip()}
        return sorted(cleaned)
