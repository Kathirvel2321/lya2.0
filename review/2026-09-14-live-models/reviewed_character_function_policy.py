def first_non_repeated(s: str) -> str | None:
    """
    Return the first character that appears exactly once in *s*,
    preserving the original case.  If no such character exists
    (or the string is empty) return None.
    """
    # Count occurrences while preserving order
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1

    # Scan again to find the first with count == 1
    for ch in s:
        if counts[ch] == 1:
            return ch
    return None

def _run_tests():
    assert first_non_repeated("") is None
    assert first_non_repeated("a") == "a"
    assert first_non_repeated("aa") is None
    assert first_non_repeated("ab") == "a"
    assert first_non_repeated("aab") == "b"
    assert first_non_repeated("aabbc") == "c"
    # Preserve case
    assert first_non_repeated("AaBbA") == "b"
    # Later characters may be the first non‑repeated
    assert first_non_repeated("stress") == "t"
    print("All tests passed.")

if __name__ == "__main__":
    _run_tests()
