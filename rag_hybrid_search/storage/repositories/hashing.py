import hashlib


def chunk_hash(text: str) -> str:
    """SHA256 of chunk text, normalized (stripped) so trailing-whitespace
    differences from re-parsing the same document don't defeat exact-dup
    detection. Shared by the pipeline (computes hashes to check) and every
    ChunkRepository implementation (stores/matches on them)."""
    return hashlib.sha256(text.strip().encode()).hexdigest()
