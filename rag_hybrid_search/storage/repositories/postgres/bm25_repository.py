"""Incremental BM25, scored entirely in Postgres.

Write path (record_many): tokenize each new chunk, upsert its term
postings and doc length, then apply one incremental UPDATE to the
corpus-wide aggregate (total_chunks, total_length, avg_doc_length) --
O(new chunks x avg terms/chunk), never touches existing postings or
re-tokenizes the corpus. This is what makes BM25 "no full rebuild on
upload" possible: postings for chunk A are written once, at ingest time,
and never revisited by ingesting chunk B.

Read path (search): classic Okapi BM25, computed as one SQL query --
indexed postings lookup per query term (bm25_postings(organization_id,
term)), not a scan of every chunk. Cost is O(query terms x postings per
term), independent of total corpus size.
"""

from typing import Callable, Iterator

from rag_hybrid_search.models import Chunk
from rag_hybrid_search.storage.bm25_index import tokenize
from rag_hybrid_search.storage.repositories.postgres.connection import ConnectionProvider

_K1 = 1.5
_B = 0.75


class PostgresBM25Repository:
    def __init__(self, connection_provider: ConnectionProvider, organization_id: str):
        self._connections = connection_provider
        self._organization_id = organization_id

    def record_many(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        posting_rows = []
        doc_stat_rows = []
        total_new_length = 0
        for chunk in chunks:
            tokens = tokenize(chunk.text)
            doc_stat_rows.append((self._organization_id, chunk.chunk_id, len(tokens)))
            total_new_length += len(tokens)
            term_counts: dict[str, int] = {}
            for token in tokens:
                term_counts[token] = term_counts.get(token, 0) + 1
            posting_rows.extend(
                (self._organization_id, term, chunk.chunk_id, count)
                for term, count in term_counts.items()
            )

        with self._connections.connection() as conn, conn.cursor() as cur:
            if posting_rows:
                cur.executemany(
                    """
                    insert into bm25_postings (organization_id, term, chunk_id, term_frequency)
                    values (%s, %s, %s, %s)
                    on conflict (organization_id, term, chunk_id) do update
                        set term_frequency = excluded.term_frequency
                    """,
                    posting_rows,
                )
            cur.executemany(
                """
                insert into bm25_doc_stats (organization_id, chunk_id, doc_length)
                values (%s, %s, %s)
                on conflict (organization_id, chunk_id) do update
                    set doc_length = excluded.doc_length
                """,
                doc_stat_rows,
            )
            conn.execute(
                """
                insert into bm25_corpus_stats (organization_id, total_chunks, total_length, avg_doc_length, updated_at)
                values (%s, %s, %s, %s, now())
                on conflict (organization_id) do update
                    set total_chunks = bm25_corpus_stats.total_chunks + excluded.total_chunks,
                        total_length = bm25_corpus_stats.total_length + excluded.total_length,
                        avg_doc_length = (bm25_corpus_stats.total_length + excluded.total_length)::float
                            / nullif(bm25_corpus_stats.total_chunks + excluded.total_chunks, 0),
                        updated_at = now()
                """,
                (
                    self._organization_id, len(chunks), total_new_length,
                    total_new_length / len(chunks) if chunks else 0.0,
                ),
            )

    def remove_chunks(self, chunk_ids: list[str]) -> None:
        if not chunk_ids:
            return
        with self._connections.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select coalesce(sum(doc_length), 0) from bm25_doc_stats "
                    "where organization_id = %s and chunk_id = any(%s)",
                    (self._organization_id, chunk_ids),
                )
                removed_length = cur.fetchone()[0]
            conn.execute(
                "delete from bm25_postings where organization_id = %s and chunk_id = any(%s)",
                (self._organization_id, chunk_ids),
            )
            conn.execute(
                "delete from bm25_doc_stats where organization_id = %s and chunk_id = any(%s)",
                (self._organization_id, chunk_ids),
            )
            conn.execute(
                """
                update bm25_corpus_stats
                set total_chunks = greatest(total_chunks - %s, 0),
                    total_length = greatest(total_length - %s, 0),
                    avg_doc_length = case when total_chunks - %s <= 0 then 0
                        else (total_length - %s)::float / (total_chunks - %s) end,
                    updated_at = now()
                where organization_id = %s
                """,
                (len(chunk_ids), removed_length, len(chunk_ids), removed_length, len(chunk_ids), self._organization_id),
            )

    def rebuild_full(self, get_chunks: Callable[[], Iterator[Chunk]]) -> None:
        """No-op: record_many()/remove_chunks() already keep postings
        current incrementally, so IndexManager.rebuild_bm25_index() calling
        this on every ingest (rebuild_bm25=True is the default) needs to do
        nothing here -- and deliberately never calls get_chunks(), so no
        full-corpus fetch happens just to discard it. Use
        force_rebuild_from(chunks) directly (not through this Protocol
        method) for admin/backfill/drift-reconciliation."""
        pass

    def force_rebuild_from(self, chunks: list[Chunk]) -> None:
        """Truncates and rewrites the whole index from a full chunk list.
        Admin/backfill/drift-reconciliation only -- not part of
        BM25Repository, not called anywhere in the normal ingest path."""
        with self._connections.connection() as conn:
            conn.execute("delete from bm25_postings where organization_id = %s", (self._organization_id,))
            conn.execute("delete from bm25_doc_stats where organization_id = %s", (self._organization_id,))
            conn.execute("delete from bm25_corpus_stats where organization_id = %s", (self._organization_id,))
        self.record_many(chunks)

    def search(self, query: str, k: int) -> list[tuple[str, float]]:
        query_terms = list(dict.fromkeys(tokenize(query)))  # dedup, preserve order
        if not query_terms:
            return []
        with self._connections.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select total_chunks, avg_doc_length from bm25_corpus_stats where organization_id = %s",
                    (self._organization_id,),
                )
                corpus_row = cur.fetchone()
                if corpus_row is None or corpus_row[0] == 0:
                    return []
                total_chunks, avg_doc_length = corpus_row

                rows = cur.execute(
                    """
                    with term_df as (
                        select term, count(*) as df
                        from bm25_postings
                        where organization_id = %s and term = any(%s)
                        group by term
                    )
                    select p.chunk_id,
                        sum(
                            ln((%s - td.df + 0.5) / (td.df + 0.5) + 1)
                            * (p.term_frequency * (%s + 1))
                            / (p.term_frequency + %s * (1 - %s + %s * ds.doc_length / nullif(%s, 0)))
                        ) as score
                    from bm25_postings p
                    join term_df td on td.term = p.term
                    join bm25_doc_stats ds on ds.chunk_id = p.chunk_id and ds.organization_id = p.organization_id
                    where p.organization_id = %s and p.term = any(%s)
                    group by p.chunk_id
                    order by score desc
                    limit %s
                    """,
                    (
                        self._organization_id, query_terms,
                        total_chunks, _K1, _K1, _B, _B, avg_doc_length,
                        self._organization_id, query_terms,
                        k,
                    ),
                ).fetchall()
        return [(str(chunk_id), float(score)) for chunk_id, score in rows]
