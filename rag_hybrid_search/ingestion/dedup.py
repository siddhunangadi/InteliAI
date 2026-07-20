from difflib import SequenceMatcher

import numpy as np

from rag_hybrid_search.models import Chunk
from rag_hybrid_search.similarity import cosine_similarity


def _text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(a=a, b=b).ratio()


def is_duplicate(
    candidate: Chunk,
    candidate_embedding: list[float],
    existing: list[tuple[Chunk, list[float]]],
    cosine_threshold: float,
    text_threshold: float,
) -> bool:
    for existing_chunk, existing_embedding in existing:
        cosine_sim = cosine_similarity(candidate_embedding, existing_embedding)
        if cosine_sim <= cosine_threshold:
            continue
        text_sim = _text_similarity(candidate.text, existing_chunk.text)
        if text_sim > text_threshold:
            return True
    return False


def find_duplicates(
    candidates: list[Chunk],
    candidate_embeddings: list[list[float]],
    existing: list[tuple[Chunk, list[float]]],
    cosine_threshold: float,
    text_threshold: float,
) -> list[bool]:
    """Vectorized equivalent of calling ``is_duplicate`` once per candidate.

    ``is_duplicate``'s cosine_similarity() is pure-Python (zip+sum), called
    len(candidates) * len(existing) times -- at real batch-ingestion scale
    (a single large document's chunks compared against every chunk already
    ingested this batch) that's tens of millions of Python-level dot
    products, which in practice means the batch never finishes. Compute
    every candidate-vs-existing cosine similarity as one numpy matmul
    instead, and only run the expensive SequenceMatcher text comparison on
    pairs that already cleared the cheap cosine threshold.
    """
    if not existing or not candidates:
        return [False] * len(candidates)

    cand_matrix = np.asarray(candidate_embeddings, dtype=np.float32)
    exist_matrix = np.asarray([embedding for _, embedding in existing], dtype=np.float32)

    cand_norms = np.linalg.norm(cand_matrix, axis=1, keepdims=True)
    exist_norms = np.linalg.norm(exist_matrix, axis=1, keepdims=True)
    cand_norms[cand_norms == 0] = 1.0
    exist_norms[exist_norms == 0] = 1.0

    similarities = (cand_matrix / cand_norms) @ (exist_matrix / exist_norms).T

    results = []
    for i, candidate in enumerate(candidates):
        is_dup = False
        for j in np.flatnonzero(similarities[i] > cosine_threshold):
            if _text_similarity(candidate.text, existing[j][0].text) > text_threshold:
                is_dup = True
                break
        results.append(is_dup)
    return results


def find_within_batch_duplicates(
    candidates: list[Chunk],
    candidate_embeddings: list[list[float]],
    cosine_threshold: float,
    text_threshold: float,
) -> list[bool]:
    """Like ``find_duplicates``, but each candidate is checked against
    earlier candidates in the same list (self-similarity) instead of an
    external ``existing`` corpus -- a single large document's own chunk
    count can itself be in the thousands (see ``find_duplicates``'s
    docstring for why an O(n^2) Python loop doesn't scale there)."""
    n = len(candidates)
    if n < 2:
        return [False] * n

    matrix = np.asarray(candidate_embeddings, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = matrix / norms
    similarities = normalized @ normalized.T

    results = [False] * n
    for i in range(1, n):
        for j in np.flatnonzero(similarities[i, :i] > cosine_threshold):
            if results[j]:
                continue  # already-dropped earlier chunk isn't a valid duplicate target
            if _text_similarity(candidates[i].text, candidates[j].text) > text_threshold:
                results[i] = True
                break
    return results
