from rag_hybrid_search.storage.repositories.hashing import chunk_hash, simhash, simhash_bands


def _hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def test_chunk_hash_is_stable_and_normalizes_whitespace():
    assert chunk_hash("hello world") == chunk_hash("hello world")
    assert chunk_hash("hello world") == chunk_hash("  hello world  \n")


def test_chunk_hash_differs_for_different_text():
    assert chunk_hash("hello world") != chunk_hash("hello word")


def test_simhash_identical_text_produces_identical_fingerprint():
    text = "The quick brown fox jumps over the lazy dog"
    assert simhash(text) == simhash(text)


def test_simhash_near_duplicate_text_has_smaller_hamming_distance_than_unrelated():
    original = "The quick brown fox jumps over the lazy dog in the park every single morning without fail"
    near_dup = "The quick brown fox jumps over the lazy dog at the park every single morning without fail"  # one word changed
    unrelated = "This is a completely unrelated sentence about baking sourdough bread at home this weekend"

    dist_near = _hamming_distance(simhash(original), simhash(near_dup))
    dist_unrelated = _hamming_distance(simhash(original), simhash(unrelated))

    assert dist_near < dist_unrelated


def test_simhash_bands_share_at_least_one_band_for_near_duplicates():
    """This is the property LSH candidate narrowing depends on: two
    fingerprints close in Hamming distance should collide on at least one
    band most of the time (probabilistic, not guaranteed for every pair --
    true for these single-word-edit examples with the default 8x8 banding;
    see the module docstring for why 4x16 bands failed this same check)."""
    original = simhash("The quick brown fox jumps over the lazy dog in the park every single morning without fail")
    near_dup = simhash("The quick brown fox jumps over the lazy dog at the park every single morning without fail")

    bands_a = set(simhash_bands(original))
    bands_b = set(simhash_bands(near_dup))

    assert bands_a & bands_b, "expected at least one shared band for a near-duplicate pair"


def test_simhash_bands_returns_requested_count_and_width():
    bands = simhash_bands(0xFF00_FF00_FF00_FF00, num_bands=8, band_bits=8)
    assert len(bands) == 8
    assert bands == [0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF]


def test_simhash_empty_text_is_zero():
    assert simhash("") == 0
    assert simhash("   ") == 0
