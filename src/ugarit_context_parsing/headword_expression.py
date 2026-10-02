"""Parse Burns headword grouping syntax into bounded exact surface candidates.

This layer is deliberately narrow. It preserves the verbatim source headword and
only expands constructs whose operational alignment semantics are supported by
the pinned real-Workbooks audit in issue #78.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

_EDITORIAL_MARKERS = "*†!?"


@dataclass(frozen=True)
class BurnsHeadwordCandidate:
    label: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class BurnsHeadwordExpression:
    verbatim: str
    rule: str
    candidates: tuple[BurnsHeadwordCandidate, ...]


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def headword_tokens(value: str) -> tuple[str, ...]:
    """Preserve historical exact-token semantics for one candidate string."""

    tokens: list[str] = []
    for raw in _nfc(value).split():
        token = raw.rstrip(_EDITORIAL_MARKERS)
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


def _simple_parenthesis_omit(value: str) -> tuple[str, ...] | None:
    """Return the evidenced omit-group candidate for one simple group."""

    if "[" in value or "]" in value or "/" in value:
        return None
    unbalanced, openers, max_depth = _delimiter_balance(value, "(", ")")
    if unbalanced or openers != 1 or max_depth != 1:
        return None
    start = value.find("(")
    end = value.find(")", start + 1)
    if start < 0 or end < 0:
        return None

    candidate = headword_tokens(" ".join((value[:start], value[end + 1 :])))
    return candidate or None


def _simple_slash_candidates(
    value: str,
) -> tuple[BurnsHeadwordCandidate, BurnsHeadwordCandidate] | None:
    """Return two branch candidates for one inline slash token."""

    if any(char in value for char in "()[]"):
        return None
    raw_tokens = value.split()
    slash_indexes = [index for index, token in enumerate(raw_tokens) if "/" in token]
    if len(slash_indexes) != 1 or value.count("/") != 1:
        return None

    index = slash_indexes[0]
    token = raw_tokens[index]
    if token == "/":
        return None
    left, right = token.split("/", 1)
    if not left or not right:
        return None

    left_tokens = list(raw_tokens)
    left_tokens[index] = left
    right_tokens = list(raw_tokens)
    right_tokens[index] = right
    left_candidate = headword_tokens(" ".join(left_tokens))
    right_candidate = headword_tokens(" ".join(right_tokens))
    if not left_candidate or not right_candidate:
        return None
    return (
        BurnsHeadwordCandidate("slash_left", left_candidate),
        BurnsHeadwordCandidate("slash_right", right_candidate),
    )


def parse_headword_expression(headword: str) -> BurnsHeadwordExpression:
    """Return the bounded exact candidates licensed by current source research.

    Supported production rules:
    - one balanced, non-nested parenthesized group, with no slash/brackets:
      omit the complete group;
    - exactly one inline slash in one token, with no parentheses/brackets:
      test both branches.

    Everything else retains the historical literal-token behavior. This keeps
    square-bracket restoration, nested/multiple parentheses, standalone slash,
    and multi-slash syntax fail-closed for their dedicated research tickets.
    """

    text = _nfc(headword or "")

    if "(" in text or ")" in text:
        omitted = _simple_parenthesis_omit(text)
        if omitted is not None:
            return BurnsHeadwordExpression(
                verbatim=headword,
                rule="parenthesis_omit",
                candidates=(BurnsHeadwordCandidate("parenthesis_omit", omitted),),
            )

    if "/" in text:
        slash = _simple_slash_candidates(text)
        if slash is not None:
            return BurnsHeadwordExpression(
                verbatim=headword,
                rule="slash_alternatives",
                candidates=slash,
            )

    return BurnsHeadwordExpression(
        verbatim=headword,
        rule="literal",
        candidates=(BurnsHeadwordCandidate("literal", headword_tokens(text)),),
    )
