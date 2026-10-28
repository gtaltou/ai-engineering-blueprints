# ADR-002: Hybrid Retrieval with Reciprocal Rank Fusion (RRF) and Deterministic Citation Verification

* **Status:** Accepted
* **Date:** 2026-10-28
* **Scope:** `blueprint_core.retrieval`, `blueprint_core.contracts.rag_schemas`, Blueprint #02

## Context

Pure dense vector search excels at capturing conceptual similarity but frequently fails on exact token matches such as error codes (`ERR-9042`), product SKUs, version identifiers, or configuration keys. Conversely, pure lexical search (BM25/TF-IDF) misses paraphrased or semantically equivalent queries.

Additionally, even when relevant chunks are retrieved, Large Language Models can hallucinate citations—referencing non-existent document IDs or attributing claims to chunks that were never present in the context window.

## Decision

1. **Hybrid Retrieval via Reciprocal Rank Fusion (RRF):**
   We combine IDF-weighted lexical scoring and cosine semantic similarity using Reciprocal Rank Fusion:
   $$\text{RRF}(d) = \frac{1}{k + r_{\text{lexical}}(d)} + \frac{1}{k + r_{\text{semantic}}(d)}$$
   with smoothing constant $k = 60$. RRF requires no score normalization across incompatible distributions and avoids tuning brittle linear combination weights.

2. **Contract-First Grounding (`GroundedAnswer`):**
   Every RAG synthesis call must conform to `GroundedAnswer`, which enforces via a Pydantic `@model_validator` that any response claiming `has_sufficient_context=True` includes at least one `GroundedCitation` (`chunk_id` + verbatim `supporting_quote`).

3. **Post-Generation Citation Guardrail (`CitationHallucinationError`):**
   Before returning the structured response to the caller, `GroundedRAGPipeline` deterministically verifies that every cited `chunk_id` belongs to the exact top-$k$ retrieved set for that query. Any mismatch raises `CitationHallucinationError`.

## Consequences

* **Positive:** High recall on both exact technical identifiers and conceptual queries without score-calibration drift; zero tolerance for fabricated citation IDs.
* **Negative:** Slightly higher indexing and query memory footprint due to maintaining both lexical inverted statistics and dense vectors.
