"""Hybrid Retrieval-Augmented Generation (RAG) with RRF and citation verification."""

from __future__ import annotations

import math
import re
from collections.abc import Callable

from blueprint_core.contracts.rag_schemas import (
    DocumentChunk,
    GroundedAnswer,
    RetrievedChunk,
)
from blueprint_core.gateways.smart_router import SmartRouter

EmbeddingFunction = Callable[[str], list[float]]


class CitationHallucinationError(ValueError):
    """Raised when an LLM cites a chunk_id that was not in the retrieved context."""


class HybridRRFIndex:
    """In-memory hybrid index combining lexical scoring and dense vectors via RRF."""

    def __init__(self, embed_fn: EmbeddingFunction, rrf_k: int = 60) -> None:
        if rrf_k < 1:
            raise ValueError("rrf_k must be a positive integer.")
        self._embed_fn = embed_fn
        self._rrf_k = rrf_k
        self._chunks: list[DocumentChunk] = []
        self._embeddings: list[list[float]] = []
        self._tokenized_corpus: list[set[str]] = []
        self._idf: dict[str, float] = {}

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Extract normalized alphanumeric and hyphenated technical tokens."""
        return set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower()))

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two dense vectors."""
        if len(vec_a) != len(vec_b) or not vec_a:
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(0.0, dot / (norm_a * norm_b))

    def index_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Index document chunks for both lexical IDF overlap and dense vector search."""
        self._chunks = list(chunks)
        self._embeddings = [self._embed_fn(c.content) for c in self._chunks]
        self._tokenized_corpus = [self._tokenize(c.content) for c in self._chunks]

        num_docs = len(self._chunks)
        doc_freq: dict[str, int] = {}
        for tokens in self._tokenized_corpus:
            for token in tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        self._idf = {
            token: math.log((1.0 + num_docs) / (1.0 + df)) + 1.0
            for token, df in doc_freq.items()
        }

    def search(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        """Retrieve top_k chunks ranked by Reciprocal Rank Fusion (RRF)."""
        if not self._chunks:
            return []

        query_tokens = self._tokenize(query)
        query_embedding = self._embed_fn(query)

        lexical_scores: list[tuple[int, float]] = []
        semantic_scores: list[tuple[int, float]] = []

        for idx, doc_tokens in enumerate(self._tokenized_corpus):
            overlap = query_tokens.intersection(doc_tokens)
            lex_score = sum(self._idf.get(tok, 1.0) for tok in overlap)
            lexical_scores.append((idx, lex_score))

            sem_score = self._cosine_similarity(query_embedding, self._embeddings[idx])
            semantic_scores.append((idx, sem_score))

        lexical_sorted = sorted(lexical_scores, key=lambda item: item[1], reverse=True)
        semantic_sorted = sorted(semantic_scores, key=lambda item: item[1], reverse=True)

        lexical_ranks = {
            doc_idx: rank for rank, (doc_idx, _) in enumerate(lexical_sorted, start=1)
        }
        semantic_ranks = {
            doc_idx: rank for rank, (doc_idx, _) in enumerate(semantic_sorted, start=1)
        }

        fused_results: list[RetrievedChunk] = []
        for idx, chunk in enumerate(self._chunks):
            lex_rank = lexical_ranks[idx]
            sem_rank = semantic_ranks[idx]
            rrf_score = (1.0 / (self._rrf_k + lex_rank)) + (
                1.0 / (self._rrf_k + sem_rank)
            )
            fused_results.append(
                RetrievedChunk(
                    chunk=chunk,
                    lexical_rank=lex_rank,
                    semantic_rank=sem_rank,
                    rrf_score=round(rrf_score, 6),
                )
            )

        fused_results.sort(
            key=lambda item: (item.rrf_score, -item.lexical_rank),
            reverse=True,
        )
        return fused_results[:top_k]


class GroundedRAGPipeline:
    """End-to-end RAG pipeline enforcing retrieval grounding and citation verification."""

    def __init__(
        self,
        index: HybridRRFIndex,
        router: SmartRouter,
        top_k: int = 3,
    ) -> None:
        self._index = index
        self._router = router
        self._top_k = top_k

    @staticmethod
    def build_grounded_prompt(query: str, retrieved: list[RetrievedChunk]) -> str:
        """Format retrieved chunks with explicit IDs for strict citation grounding."""
        context_blocks = [
            f"[{item.chunk.chunk_id}] (source: {item.chunk.source_uri})\n{item.chunk.content}"
            for item in retrieved
        ]
        joined_context = "\n\n".join(context_blocks)
        return (
            "You are a precision engineering assistant. Answer the query strictly using "
            "the provided context blocks. Every claim must cite a valid chunk_id.\n\n"
            f"CONTEXT:\n{joined_context}\n\n"
            f"QUERY: {query}"
        )

    def answer_query(self, query: str) -> tuple[GroundedAnswer, list[RetrievedChunk]]:
        """Retrieve hybrid context, generate a structured answer, and verify citations."""
        retrieved = self._index.search(query=query, top_k=self._top_k)
        allowed_chunk_ids = {item.chunk.chunk_id for item in retrieved}

        prompt = self.build_grounded_prompt(query=query, retrieved=retrieved)
        answer = self._router.execute_structured(
            prompt=prompt,
            response_model=GroundedAnswer,
        )

        for citation in answer.citations:
            if citation.chunk_id not in allowed_chunk_ids:
                raise CitationHallucinationError(
                    f"Hallucinated citation chunk_id '{citation.chunk_id}' is not in "
                    f"retrieved context: {sorted(allowed_chunk_ids)}"
                )

        return answer, retrieved
