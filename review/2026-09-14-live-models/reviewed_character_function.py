def first_non_repeated(s: str):
    """Return the first character that appears exactly once in *s*,
    preserving case. Return None for an empty string or if no such
    character exists."""
    if not s:
        return None
    # Count occurrences
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    # Find first with count 1
    for ch in s:
        if counts[ch] == 1:
            return ch
    return None


# ---------- simple tests ----------
assert first_non_repeated("") is None
assert first_non_repeated("a") == "a"
assert first_non_repeated("abacabad") == "c"
assert first_non_repeated("AaBbCc") == "A"   # case‑sensitive
assert first_non_repeated("aabbcc") is None
assert first_non_repeated("swiss") == "w"
print("All tests passed.")
