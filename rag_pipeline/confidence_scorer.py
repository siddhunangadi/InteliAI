import math

from rag_hybrid_search.models import RetrievedChunk
from rag_pipeline.models import ConfidenceScores, PromptContext, VerificationReport

RETRIEVAL_WEIGHT = 0.4
CITATION_WEIGHT = 0.4
COVERAGE_WEIGHT = 0.2


def score_confidence(
    retrieved_chunks: list[RetrievedChunk],
    verification: VerificationReport,
    context: PromptContext,
) -> ConfidenceScores:
    retrieval = _retrieval_score(retrieved_chunks)
    citations = _citation_score(verification)
    coverage = _coverage_score(verification, context)
    overall = (
        RETRIEVAL_WEIGHT * retrieval
        + CITATION_WEIGHT * citations
        + COVERAGE_WEIGHT * coverage
    )
    return ConfidenceScores(
        retrieval=retrieval, citations=citations, coverage=coverage, overall=overall
    )


def _retrieval_score(retrieved_chunks: list[RetrievedChunk]) -> float:
    if not retrieved_chunks:
        return 0.0
    top = min(retrieved_chunks, key=lambda r: r.final_rank)
    if top.rerank_score is not None:
        # rerank_score is a raw cross-encoder/NVIDIA-rerank logit -- an
        # unbounded real number, negative logits included (a negative
        # logit is a completely normal "somewhat relevant" result, not a
        # bad match). Clamping directly via max(0, min(1, score)) treated
        # every negative logit as exactly 0.0 confidence regardless of how
        # close to 0 it was, which is what a min-max-normalized [0,1]
        # reranker (e.g. CrossEncoderReranker) actually returns. Sigmoid
        # maps any real logit into (0, 1) instead of collapsing negatives.
        return 1.0 / (1.0 + math.exp(-top.rerank_score))
    # rrf_score is an unbounded raw RRF value (max ~1/(rrf_k+1)), not a 0-1
    # confidence -- using it directly understates confidence by orders of
    # magnitude whenever no scored reranker ran (e.g. PassthroughReranker,
    # the default on memory-constrained deployments). Fall back to a
    # rank-based score instead, always in (0, 1].
    return 1.0 / top.final_rank if top.final_rank > 0 else 0.0


def _citation_score(verification: VerificationReport) -> float:
    if verification.total_claims == 0:
        return 1.0
    return verification.verified_claims / verification.total_claims


def _coverage_score(
    verification: VerificationReport, context: PromptContext
) -> float:
    if not context.doc_id_map:
        return 0.0
    cited_doc_ids: set[str] = set()
    for result in verification.claim_results:
        if result.doc_ids_valid:
            cited_doc_ids.update(result.claim.citation_ids)
    return len(cited_doc_ids) / len(context.doc_id_map)
