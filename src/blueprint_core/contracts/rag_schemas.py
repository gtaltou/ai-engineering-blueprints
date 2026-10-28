"""Pydantic v2 contracts for Hybrid RAG retrieval and citation-grounded generation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DocumentChunk(BaseModel):
    """Immutable representation of an indexed knowledge chunk."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(..., min_length=1, description="Unique identifier of the chunk.")
    source_uri: str = Field(..., min_length=1, description="Origin document URI or path.")
    content: str = Field(..., min_length=1, description="Raw text content of the chunk.")


class RetrievedChunk(BaseModel):
    """Chunk enriched with hybrid Reciprocal Rank Fusion (RRF) ranking metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk: DocumentChunk
    lexical_rank: int = Field(..., ge=1, description="1-based rank from lexical scoring.")
    semantic_rank: int = Field(..., ge=1, description="1-based rank from dense vector scoring.")
    rrf_score: float = Field(..., ge=0.0, description="Combined Reciprocal Rank Fusion score.")


class GroundedCitation(BaseModel):
    """Verifiable reference linking a generated claim to a specific retrieved chunk."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(
        ...,
        min_length=1,
        description="Exact chunk_id from the retrieved context.",
    )
    supporting_quote: str = Field(
        ...,
        min_length=5,
        description="Direct excerpt from the chunk supporting the claim.",
    )


class GroundedAnswer(BaseModel):
    """Contract-first RAG response enforcing non-empty citations when context is sufficient."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    answer: str = Field(..., min_length=10, description="Synthesized answer to the user query.")
    citations: list[GroundedCitation] = Field(
        default_factory=list,
        description="List of supporting citations from retrieved chunks.",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Calibrated confidence score between 0.0 and 1.0.",
    )
    has_sufficient_context: bool = Field(
        ...,
        description="True if the provided chunks contained enough evidence to answer.",
    )

    @model_validator(mode="after")
    def _enforce_citations_when_confident(self) -> GroundedAnswer:
        if self.has_sufficient_context and not self.citations:
            raise ValueError(
                "citations cannot be empty when has_sufficient_context is True."
            )
        return self
