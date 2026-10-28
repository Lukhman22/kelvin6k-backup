"""
Retrieval over the ingested documentation.

Returns source-aware results and, critically, says plainly when nothing relevant
was found so the assistant can answer "that isn't in the documentation" instead
of inventing an answer.
"""

from typing import Any, Dict, List, Optional

from agent import config
from agent.logging_setup import get_logger
from agent.rag.embeddings import (
    GeminiEmbedder,
    LexicalEmbedder,
    _STOPWORDS,
    get_embedder,
    tokenize,
)
from agent.rag.store import DocumentStore

log = get_logger("RAG")

_store_cache: Optional[DocumentStore] = None
_cached_dir: Optional[str] = None


def get_store(index_dir: Optional[str] = None, refresh: bool = False) -> DocumentStore:
    global _store_cache, _cached_dir
    directory = index_dir or config.RAG_INDEX_DIR
    if refresh or _store_cache is None or _cached_dir != directory:
        _store_cache = DocumentStore.load(directory)
        _cached_dir = directory
    return _store_cache


def search_documentation(
    query: str,
    top_k: Optional[int] = None,
    index_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Searches the ingested manuals/SOPs/troubleshooting documents.

    Use this for questions about procedures, specifications, error codes,
    maintenance steps or anything documented -- NOT for live machine values.

    Returns {"found": bool, "results": [{text, source, score, ...}], "message": str}.
    When `found` is False the answer must say the information is not in the
    available documentation.
    """
    store = get_store(index_dir)
    limit = top_k or config.RAG_TOP_K

    if len(store) == 0:
        return {
            "found": False,
            "results": [],
            "message": (
                "No documentation has been ingested yet. Add documents with: "
                "python ingest_docs.py <file-or-folder>"
            ),
        }

    lexical_scores = LexicalEmbedder().score(query, store.texts)
    scores: List[float] = []
    search_mode = "lexical"

    if store.is_semantic and any(c.embedding for c in store.chunks):
        embedder = get_embedder()
        query_vector = embedder.embed_query(query) if isinstance(embedder, GeminiEmbedder) else None
        if query_vector is not None:
            semantic_scores = [
                GeminiEmbedder.cosine(query_vector, c.embedding) if c.embedding else 0.0
                for c in store.chunks
            ]
            # Hybrid fusion: linear combination of semantic similarity and BM25 relevance
            scores = [
                0.6 * sem + 0.4 * lex
                for sem, lex in zip(semantic_scores, lexical_scores)
            ]
            search_mode = "hybrid"

    if not scores:
        # Offline / fallback path: deterministic lexical scoring.
        scores = lexical_scores

    # --- Exact identifier & fault code protection ---
    # Detect exact codes like E136.1, E137.1, H0D11 to prevent cross-code drift
    import re
    query_codes = [c.upper() for c in re.findall(r"\b(?:E\d{2,3}(?:\.\d+)?|H0D11)\b", query, re.IGNORECASE)]

    boosted_scores: List[float] = []
    for chunk, s in zip(store.chunks, scores):
        chunk_upper = chunk.text.upper()
        curr_score = float(s)
        if query_codes:
            # Check if this chunk explicitly contains any requested code
            has_queried_code = any(qc in chunk_upper for qc in query_codes)
            # Check if this chunk contains competing fault codes not in the query
            has_competing_code = any(
                comp in chunk_upper
                for comp in ("E136.1", "E137.1", "H0D11", "E08.5")
                if comp not in query_codes
            )
            if has_queried_code:
                curr_score += 1.0  # Dominant boost for exact code match
            elif has_competing_code:
                curr_score *= 0.1  # Strongly demote competing codes
        boosted_scores.append(curr_score)

    ranked = sorted(zip(store.chunks, boosted_scores), key=lambda pair: pair[1], reverse=True)
    hits = [(c, s) for c, s in ranked[:limit] if s >= config.RAG_MIN_SCORE]

    # Grounding check: when a query contains specific informative terms,
    # reject spurious hits that do not actually mention the core subject.
    # For queries with >= 3 informative tokens, candidate chunks must cover
    # at least 50% of the query's terms (exempting exact code matches).
    informative_query_terms = [
        t for t in tokenize(query, expand_synonyms=True) if t not in _STOPWORDS
    ]
    if len(informative_query_terms) >= 3:
        grounded_hits = []
        for c, s in hits:
            chunk_upper = c.text.upper()
            if query_codes and any(qc in chunk_upper for qc in query_codes):
                grounded_hits.append((c, s))
                continue
            chunk_tokens = set(tokenize(c.text))
            matched = [t for t in informative_query_terms if t in chunk_tokens]
            if len(matched) >= len(informative_query_terms) * 0.5:
                grounded_hits.append((c, s))
        hits = grounded_hits

    # --- Dual Representation: Integrate structured SQLite knowledge records ---
    structured_records = []
    try:
        from agent import knowledge_store
        # 1. Exact fault code lookup
        if query_codes:
            for qc in query_codes:
                exact_rec = knowledge_store.get_exact_fault_record(qc)
                if exact_rec:
                    structured_records.append(exact_rec)
        # 2. Semantic/token lookup in structured knowledge
        if not structured_records:
            structured_records = knowledge_store.search_knowledge_records(query, limit=2)
    except Exception as k_exc:
        log.warning("Knowledge store query error: %s", k_exc)

    formatted_results = []
    seen_texts = set()

    # Format matched documentation chunks
    for chunk, score in hits:
        if chunk.text[:80] in seen_texts:
            continue
        seen_texts.add(chunk.text[:80])
        grade = _grade_evidence(chunk.text, chunk.doc_type)
        formatted_results.append({
            "text": chunk.text,
            "source": chunk.citation(),
            "score": round(float(score), 3),
            "evidence_grade": grade,
            **chunk.metadata(),
        })

    if not formatted_results:
        return {
            "found": False,
            "results": [],
            "structured_knowledge": structured_records if query_codes else [],
            "message": (
                "That information was not found in the available documentation. "
                f"({len(store)} chunks searched across {len(store.files())} document(s).)"
            ),
        }

    return {
        "found": True,
        "results": formatted_results[:limit],
        "structured_knowledge": structured_records,
        "message": f"{len(formatted_results)} relevant passage(s) found.",
        "search_mode": "dual_hybrid" if structured_records else search_mode,
    }


def _grade_evidence(text: str, default_type: str = "document") -> str:
    """Classifies the evidence into standard industrial confidence grades."""
    text_upper = text.upper()
    if "UNAPPROVED WORKAROUND" in text_upper or "DO NOT USE" in text_upper:
        return "Unverified Workaround"
    if "CONFLICT" in text_upper or "CONFLICTING" in text_upper:
        return "Conflicting Evidence"
    if "REQUIRES AUTHORIZATION" in text_upper or "SAFETY REVIEW REQUIRED" in text_upper:
        return "Requires Authorization"
    if "OPERATOR REPORTED" in text_upper or "HANDWRITTEN NOTE" in text_upper:
        return "Operator-reported"
    if "POSSIBLE" in text_upper or "NOT CONFIRMED" in text_upper:
        return "Possible Cause"
    if default_type in ("specification", "manual") or "VERIFIED" in text_upper:
        return "Verified"
    return "Documented"


def index_summary(index_dir: Optional[str] = None) -> Dict[str, Any]:
    store = get_store(index_dir, refresh=True)
    return {
        "chunks": len(store),
        "documents": store.files(),
        "embedder": store.embedder_name or "none",
        "semantic": store.is_semantic,
    }
