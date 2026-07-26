import hashlib
import re

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def chunk_hash(text: str) -> str:
    """SHA256 of chunk text, normalized (stripped) so trailing-whitespace
    differences from re-parsing the same document don't defeat exact-dup
    detection. Shared by the pipeline (computes hashes to check) and every
    ChunkRepository implementation (stores/matches on them)."""
    return hashlib.sha256(text.strip().encode()).hexdigest()


def simhash(text: str, num_bits: int = 64) -> int:
    """64-bit SimHash over word shingles -- a fingerprint where similar
    text produces fingerprints with small Hamming distance, unlike
    chunk_hash() (SHA256), where a single-character edit produces a
    completely different digest.

    Standard SimHash construction: hash each feature (here, word
    3-shingles, so word order/local context matters, not just a bag of
    words), then for each bit position, sum +weight if that feature's hash
    has the bit set, -weight otherwise; the final fingerprint's bit is 1
    wherever the sum is positive. Near-duplicate chunks share most bits.

    Used only to narrow near-duplicate candidates via LSH banding (see
    storage/repositories/postgres/chunk_repository.py) -- not a security
    hash, collisions across unrelated text are expected and fine.
    """
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        return 0
    shingle_size = 3
    shingles = (
        [" ".join(tokens[i : i + shingle_size]) for i in range(len(tokens) - shingle_size + 1)]
        if len(tokens) >= shingle_size
        else [" ".join(tokens)]
    )
    bit_weights = [0] * num_bits
    for shingle in shingles:
        digest = int.from_bytes(hashlib.sha256(shingle.encode()).digest()[:8], "big")
        for bit in range(num_bits):
            bit_weights[bit] += 1 if (digest >> bit) & 1 else -1
    fingerprint = 0
    for bit in range(num_bits):
        if bit_weights[bit] > 0:
            fingerprint |= 1 << bit
    return fingerprint


def simhash_bands(value: int, num_bands: int = 8, band_bits: int = 8) -> list[int]:
    """Split a simhash into num_bands non-overlapping chunks of band_bits
    each, for LSH banding: two fingerprints that agree on *any* band are
    stored as candidates for each other, giving an indexed (not full-scan)
    way to find likely-near-duplicates. Smaller bands = more candidates
    (higher recall, more near-dup pairs found) but more false positives
    filtered out later by the real cosine/text similarity check.

    8x8 bits, not the more obvious 4x16: measured against this module's
    own simhash() on realistic single-word-edit near-duplicates, 4x16
    bands produced a Hamming distance of ~11/64 bits spread across the
    fingerprint -- wide enough that a full 16-bit band matching by chance
    was rare, so pairs that should have been flagged as candidates got
    zero shared bands (see tests/storage/test_hashing.py). 8x8 catches
    them; still not a tuned constant, revisit against real corpus near-dup
    rates if recall proves insufficient at scale."""
    mask = (1 << band_bits) - 1
    return [(value >> (band_bits * i)) & mask for i in range(num_bands)]
