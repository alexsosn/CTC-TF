"""Conservative Burns headword-expression parsing.

Only syntax classes supported by real cited-line evidence are interpreted here.
Unsupported or mixed syntax falls back to the historical literal tokenization so
alignment fails closed rather than guessing.
"""
from __future__ import annotations

import unicodedata

EDITORIAL_MARKERS = "*†!?"


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def literal_headword_tokens(headword: str) -> tuple[str, ...]:
    """Historical exact-match tokenization: NFC + whitespace + trailing markers."""

    tokens: list[str] = []
    for raw in nfc(headword).split():
        token = raw.rstrip(EDITORIAL_MARKERS)
        if token:
            tokens.append(token)
    return tuple(tokens)


def _delimiter_balance(value: str, opener: str, closer: str) -> tuple[bool, int, int]:
    depth = 0
    max_depth = 0
    openers = 0
    unbalanced = False
    for char in value:
        if char == opener:
            openers += 1
            depth += 1
            max_depth = max(max_depth, depth)
        elif char == closer:
            if depth == 0:
                unbalanced = True
            else:
                depth -= 1
    if depth:
        unbalanced = True
    return unbalanced, openers, max_depth


def simple_parenthesis_candidate_tokens(
    headword: str,
) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    """Return (core, expanded) for one evidenced simple parenthesized group.

    This parser is deliberately structural. It rejects nested/multiple,
    unbalanced, token-internal parentheses and expressions mixed with slash or
    square brackets.
    """

    text = nfc(headword or "")
    if "/" in text or "[" in text or "]" in text:
        return None
    unbalanced, openers, max_depth = _delimiter_balance(text, "(", ")")
    if unbalanced or openers != 1 or max_depth != 1 or text.count(")") != 1:
        return None

    start = text.index("(")
    end = text.index(")", start + 1)
    if start > 0 and not text[start - 1].isspace():
        return None
    if end + 1 < len(text) and not text[end + 1].isspace():
        return None

    before = text[:start].strip()
    inside = text[start + 1 : end].strip()
    after = text[end + 1 :].strip()
    if not inside:
        return None

    core_text = " ".join(part for part in (before, after) if part)
    expanded_text = " ".join(part for part in (before, inside, after) if part)
    core = literal_headword_tokens(core_text)
    expanded = literal_headword_tokens(expanded_text)
    if not core or not expanded or core == expanded:
        return None
    return core, expanded


def simple_token_slash_candidate_tokens(
    headword: str,
) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    """Return exact left/right candidates for one token-internal slash."""

    text = nfc(headword or "")
    if any(char in text for char in "()[]"):
        return None
    raw_tokens = text.split()
    slash_positions = [
        index for index, token in enumerate(raw_tokens) if "/" in token
    ]
    if len(slash_positions) != 1:
        return None

    index = slash_positions[0]
    token = raw_tokens[index]
    if token.count("/") != 1 or token == "/":
        return None
    left_raw, right_raw = token.split("/", 1)
    if not left_raw or not right_raw:
        return None

    left_tokens = list(raw_tokens)
    right_tokens = list(raw_tokens)
    left_tokens[index] = left_raw
    right_tokens[index] = right_raw
    left = literal_headword_tokens(" ".join(left_tokens))
    right = literal_headword_tokens(" ".join(right_tokens))
    if not left or not right or left == right:
        return None
    return left, right


def headword_candidates(
    headword: str,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return ordered (match_rule, tokens) candidates authorized by evidence."""

    parenthesis = simple_parenthesis_candidate_tokens(headword)
    if parenthesis is not None:
        core, _expanded = parenthesis
        return (("parenthesis_core", core),)

    slash = simple_token_slash_candidate_tokens(headword)
    if slash is not None:
        left, right = slash
        return (
            ("slash_left", left),
            ("slash_right", right),
        )

    return (("literal", literal_headword_tokens(headword)),)


def headword_candidate_token_sets(headword: str) -> tuple[tuple[str, ...], ...]:
    """Compatibility projection of :func:`headword_candidates` token tuples."""

    return tuple(tokens for _rule, tokens in headword_candidates(headword))
