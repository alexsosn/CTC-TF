#!/usr/bin/env python3
"""Audit Burns→CUC alignment locally without exposing source content by default.

The default stdout payload contains aggregate counts only. A full alignment
report, which necessarily contains Burns-derived source provenance and reference
text, is written only when the caller explicitly supplies ``--report``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sources import WORKBOOKS, ensure  # noqa: E402
from ugarit_context_parsing.alignment import (  # noqa: E402
    BurnsAlignmentConfidence,
    BurnsAlignmentDisposition,
    BurnsAlignmentReason,
    BurnsAnchorKind,
    BurnsAnnotationAlignment,
    _candidate_spans,
    _headword_tokens,
    align_burns_source,
    alignment_report_json,
)
from ugarit_context_parsing.annotations import (  # noqa: E402
    NormalizedBurnsSource,
    normalize_workbook_records,
)
from ugarit_context_parsing.cuc_index import ReviewedCucIndex, build_reviewed_cuc_index  # noqa: E402
from ugarit_context_parsing.headword_expression import (  # noqa: E402
    SquareBracketMask,
    literal_headword_tokens,
    nfc,
    parse_square_bracket_mask,
    simple_parenthesis_candidate_tokens,
    simple_token_slash_candidate_tokens,
)
from ugarit_context_parsing.pdf_source import load_pdf_directory  # noqa: E402


def _counter_payload(counter: Counter[str | int]) -> dict[str, int]:
    return {
        str(key): value
        for key, value in sorted(counter.items(), key=lambda item: str(item[0]))
    }


_SAFE_PUNCTUATION = frozenset(".,;:-/?+()[]")


def _source_safe_shape(value: str) -> str:
    """Mask source text while retaining coarse reference syntax for aggregate audit."""

    text = " ".join((value or "").split())
    parts: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char.isdigit():
            end = index + 1
            while end < len(text) and text[end].isdigit():
                end += 1
            parts.append("N")
            index = end
            continue
        if char.isalpha():
            end = index + 1
            while end < len(text) and text[end].isalpha():
                end += 1
            run = text[index:end]
            if run and all(item in "IVXLCDM" for item in run):
                parts.append("R")
            elif run and all(item in "ivxlcdm" for item in run):
                parts.append("r")
            else:
                parts.append("A")
            index = end
            continue
        if char.isspace():
            parts.append(" ")
        elif char in _SAFE_PUNCTUATION:
            parts.append(char)
        else:
            parts.append("P")
        index += 1
    return "".join(parts).strip()


def _candidate_count_bucket(count: int) -> str:
    if count <= 0:
        return "0"
    if count == 1:
        return "1"
    return "2+"



_EDITORIAL_MARKERS = "*†!?"
_HEADWORD_AUDIT_OUTCOMES = ("ambiguous_span", "matched", "not_found")


def _delimiter_balance(value: str, opener: str, closer: str) -> tuple[bool, int, int]:
    """Return (unbalanced, opener_count, max_depth) for one delimiter pair."""

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


def _parenthesis_shape(value: str) -> str:
    has_parenthesis = "(" in value or ")" in value
    if not has_parenthesis:
        return "none"

    unbalanced, openers, max_depth = _delimiter_balance(value, "(", ")")
    if unbalanced:
        return "unbalanced"
    if openers > 1 or max_depth > 1:
        return "multiple_or_nested"

    text = value.strip()
    start = text.find("(")
    end = text.rfind(")")
    if start == 0 and end == len(text) - 1:
        return "whole_expression"
    if start == 0:
        return "leading"
    if end == len(text) - 1:
        return "trailing"
    return "medial"


def _trailing_editorial_markers(value: str) -> str:
    """Return the distinct documented trailing markers in canonical order."""

    seen: set[str] = set()
    for raw in value.split():
        token = raw
        while token and token[-1] in _EDITORIAL_MARKERS:
            seen.add(token[-1])
            token = token[:-1]
    return "".join(marker for marker in _EDITORIAL_MARKERS if marker in seen)


def classify_headword_expression(headword: str) -> dict[str, object]:
    """Classify authored headword punctuation without interpreting its semantics."""

    text = unicodedata.normalize("NFC", headword or "")
    parentheses = "(" in text or ")" in text
    square_brackets = "[" in text or "]" in text
    slash = "/" in text
    trailing_editorial_markers = _trailing_editorial_markers(text)
    trailing_editorial_marker = bool(trailing_editorial_markers)
    unbalanced_parentheses, _, _ = _delimiter_balance(text, "(", ")")
    unbalanced_square_brackets, _, _ = _delimiter_balance(text, "[", "]")

    if parentheses:
        exclusive_class = "parentheses"
    elif square_brackets:
        exclusive_class = "square_brackets"
    elif slash:
        exclusive_class = "slash"
    elif trailing_editorial_marker:
        exclusive_class = "marker_only"
    else:
        exclusive_class = "clean"

    return {
        "parentheses": parentheses,
        "square_brackets": square_brackets,
        "slash": slash,
        "trailing_editorial_marker": trailing_editorial_marker,
        "trailing_editorial_markers": trailing_editorial_markers,
        "unbalanced_parentheses": unbalanced_parentheses,
        "unbalanced_square_brackets": unbalanced_square_brackets,
        "parenthesis_shape": _parenthesis_shape(text),
        "exclusive_class": exclusive_class,
    }



@dataclass(frozen=True)
class ParenthesisBracketCore:
    tokens: tuple[str, ...]
    restored_positions: tuple[tuple[int, ...], ...]
    brackets_omitted_with_parenthesis: bool


def _balanced_square_segment(value: str) -> bool:
    depth = 0
    group_chars = 0
    for char in value:
        if char == "[":
            if depth:
                return False
            depth = 1
            group_chars = 0
        elif char == "]":
            if not depth or group_chars == 0:
                return False
            depth = 0
        elif depth and not char.isspace() and char not in _EDITORIAL_MARKERS:
            group_chars += 1
    return depth == 0


def parenthesis_core_with_bracket_mask(
    headword: str,
) -> ParenthesisBracketCore | None:
    """Research one simple parenthesis core while preserving surviving brackets."""

    text = nfc(headword or "")
    if "/" in text or "[" not in text and "]" not in text:
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

    # A bracket group may not cross the boundary of material that the reviewed
    # parenthesis-core rule removes.
    if not all(_balanced_square_segment(part) for part in (before, inside, after)):
        return None

    core_text = " ".join(part for part in (before, after) if part)
    if not core_text:
        return None
    brackets_in_core = "[" in core_text or "]" in core_text
    brackets_in_omitted = "[" in inside or "]" in inside

    if brackets_in_core:
        parsed = parse_square_bracket_mask(core_text)
        if parsed is None:
            return None
        return ParenthesisBracketCore(
            tokens=parsed.tokens,
            restored_positions=parsed.restored_positions,
            brackets_omitted_with_parenthesis=False,
        )

    if not brackets_in_omitted:
        return None
    tokens = literal_headword_tokens(core_text)
    if not tokens:
        return None
    return ParenthesisBracketCore(
        tokens=tokens,
        restored_positions=tuple(() for _ in tokens),
        brackets_omitted_with_parenthesis=True,
    )


def opaque_parenthesis_core_with_inner_brackets(
    headword: str,
) -> tuple[str, ...] | None:
    """Research a simple parenthesis core when all bracket/slash markup is omitted.

    The inner group's syntax is deliberately opaque: if every square bracket and
    every slash lies inside the one parenthesized group, none of it contributes
    characters to the lexical core selected by the reviewed #78 rule.
    """

    text = nfc(headword or "")
    if "[" not in text and "]" not in text:
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
    inside = text[start + 1 : end]
    after = text[end + 1 :].strip()
    outside = f"{before} {after}"
    if any(char in outside for char in "[]/"):
        return None
    if "[" not in inside and "]" not in inside:
        return None

    tokens = literal_headword_tokens(" ".join(part for part in (before, after) if part))
    return tokens or None


def compare_cuc_restoration_mask(
    *,
    candidate_tokens: tuple[str, ...],
    restored_positions: tuple[tuple[int, ...], ...],
    span: tuple[int, ...],
    index: ReviewedCucIndex,
    sign_values: dict[int, str],
    sign_emen: dict[int, str],
    sign_cert: dict[int, str],
    sign_alt: dict[int, str],
) -> dict[str, object]:
    """Compare Burns restoration positions with exact CUC sign-level evidence."""

    if len(candidate_tokens) != len(restored_positions) or len(span) != len(candidate_tokens):
        return {
            "restoration": "sign_mapping_mismatch",
            "missing_count": 0,
            "extra_count": 0,
            "cert_values": {},
            "alt_values": {},
        }

    expected_slots: set[int] = set()
    all_slots: list[int] = []
    for token, positions, word in zip(
        candidate_tokens, restored_positions, span, strict=True
    ):
        slots = tuple(index.word_slots.get(word, ()))
        if len(slots) != len(token):
            return {
                "restoration": "sign_mapping_mismatch",
                "missing_count": 0,
                "extra_count": 0,
                "cert_values": {},
                "alt_values": {},
            }
        try:
            signs = tuple(nfc(sign_values[slot]) for slot in slots)
        except KeyError:
            return {
                "restoration": "sign_mapping_mismatch",
                "missing_count": 0,
                "extra_count": 0,
                "cert_values": {},
                "alt_values": {},
            }
        if "".join(signs) != nfc(token):
            return {
                "restoration": "sign_mapping_mismatch",
                "missing_count": 0,
                "extra_count": 0,
                "cert_values": {},
                "alt_values": {},
            }
        if any(position < 0 or position >= len(slots) for position in positions):
            return {
                "restoration": "sign_mapping_mismatch",
                "missing_count": 0,
                "extra_count": 0,
                "cert_values": {},
                "alt_values": {},
            }
        expected_slots.update(slots[position] for position in positions)
        all_slots.extend(slots)

    actual_restored = {
        slot for slot in all_slots if sign_emen.get(slot) == "restored"
    }
    missing = expected_slots - actual_restored
    extra = actual_restored - expected_slots
    if missing and extra:
        restoration = "missing_and_extra"
    elif missing:
        restoration = "missing"
    elif extra:
        restoration = "extra"
    else:
        restoration = "exact"

    cert_counter = Counter(
        value for slot in all_slots if (value := sign_cert.get(slot))
    )
    alt_counter = Counter(
        value for slot in all_slots if (value := sign_alt.get(slot))
    )
    return {
        "restoration": restoration,
        "missing_count": len(missing),
        "extra_count": len(extra),
        "cert_values": dict(sorted(cert_counter.items())),
        "alt_values": dict(sorted(alt_counter.items())),
    }


def aggregate_bracket_restoration_research(
    *,
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
    sign_values: dict[int, str],
    sign_emen: dict[int, str],
    sign_cert: dict[int, str],
    sign_alt: dict[int, str],
) -> dict[str, object]:
    """Audit bracketed lexical misses against exact CUC sign editorial evidence."""

    annotations = {item.annotation_id: item for item in source.annotations}
    if len(annotations) != len(source.annotations):
        raise ValueError("duplicate annotation id in bracket restoration research")

    occurrences = 0
    syntax_classes: Counter[str] = Counter()
    lexical_outcomes: Counter[str] = Counter()
    restoration_outcomes: Counter[str] = Counter()
    cert_exact: Counter[str] = Counter()
    alt_exact: Counter[str] = Counter()
    omitted_unique = 0

    for alignment in alignments:
        annotation = annotations.get(alignment.annotation_id)
        if annotation is None:
            raise ValueError(
                "alignment references unknown annotation in bracket restoration research"
            )
        headword = annotation.headword
        if "[" not in headword and "]" not in headword:
            continue

        for occurrence in alignment.occurrences:
            if occurrence.reason is not BurnsAlignmentReason.HEADWORD_NOT_FOUND:
                continue
            line_node = occurrence.context_line_node
            if line_node is None or line_node not in index.line_words:
                raise ValueError(
                    "bracketed HEADWORD_NOT_FOUND occurrence lacks indexed context line"
                )
            occurrences += 1

            candidate_tokens: tuple[str, ...] | None = None
            restored_positions: tuple[tuple[int, ...], ...] | None = None
            omitted = False

            if "(" in headword or ")" in headword:
                parenthesis = parenthesis_core_with_bracket_mask(headword)
                if parenthesis is not None:
                    candidate_tokens = parenthesis.tokens
                    restored_positions = parenthesis.restored_positions
                    omitted = parenthesis.brackets_omitted_with_parenthesis
                    syntax_class = (
                        "parenthesis_core_brackets_omitted"
                        if omitted
                        else "parenthesis_core_brackets_survive"
                    )
                else:
                    syntax_class = "unsupported"
            elif "/" in headword:
                syntax_class = "unsupported"
            else:
                parsed = parse_square_bracket_mask(headword)
                if parsed is not None:
                    candidate_tokens = parsed.tokens
                    restored_positions = parsed.restored_positions
                    syntax_class = "literal_bracket"
                else:
                    syntax_class = "unsupported"

            syntax_classes[syntax_class] += 1
            if candidate_tokens is None or restored_positions is None:
                opaque_core = opaque_parenthesis_core_with_inner_brackets(headword)
                if opaque_core is None:
                    lexical_outcomes["unsupported"] += 1
                    continue
                syntax_classes[syntax_class] -= 1
                if syntax_classes[syntax_class] == 0:
                    del syntax_classes[syntax_class]
                syntax_class = "parenthesis_core_opaque_bracketed_group"
                syntax_classes[syntax_class] += 1
                candidate_tokens = opaque_core
                restored_positions = tuple(() for _ in candidate_tokens)
                omitted = True

            spans = _candidate_spans(candidate_tokens, line_node, index)
            if not spans:
                lexical_outcomes["no_match"] += 1
                continue
            if len(spans) > 1:
                lexical_outcomes["ambiguous"] += 1
                continue

            lexical_outcomes["unique"] += 1
            if omitted:
                omitted_unique += 1
                continue

            evidence = compare_cuc_restoration_mask(
                candidate_tokens=candidate_tokens,
                restored_positions=restored_positions,
                span=spans[0],
                index=index,
                sign_values=sign_values,
                sign_emen=sign_emen,
                sign_cert=sign_cert,
                sign_alt=sign_alt,
            )
            restoration = str(evidence["restoration"])
            restoration_outcomes[restoration] += 1
            if restoration == "exact":
                cert_exact.update(
                    {
                        str(key): int(value)
                        for key, value in dict(evidence["cert_values"]).items()
                    }
                )
                alt_exact.update(
                    {
                        str(key): int(value)
                        for key, value in dict(evidence["alt_values"]).items()
                    }
                )

    return {
        "occurrences": occurrences,
        "syntax_classes": _counter_payload(syntax_classes),
        "lexical_outcomes": _counter_payload(lexical_outcomes),
        "restoration_outcomes": _counter_payload(restoration_outcomes),
        "omitted_bracket_group_unique_matches": omitted_unique,
        "cert_values_on_exact_restoration": _counter_payload(cert_exact),
        "alt_values_on_exact_restoration": _counter_payload(alt_exact),
    }


_CANDIDATE_RESEARCH_PARENTHESES = (
    "ambiguous",
    "core_and_expanded",
    "core_only",
    "expanded_only",
    "no_match",
)
_CANDIDATE_RESEARCH_SLASH = (
    "ambiguous",
    "both_branches",
    "left_only",
    "no_match",
    "right_only",
)


def _candidate_research_payload(
    eligible: int,
    counter: Counter[str],
    outcomes: tuple[str, ...],
) -> dict[str, object]:
    return {
        "eligible_occurrences": eligible,
        "outcomes": {name: counter.get(name, 0) for name in outcomes},
    }


def aggregate_headword_candidate_research(
    *,
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
) -> dict[str, object]:
    """Measure narrow candidate interpretations without changing alignment.

    Resolved-line lexical occurrences enter the audit regardless of whether
    production currently resolves them, keeping the evidence counterfactual and
    stable across matcher improvements. The payload is aggregate-only and contains no source
    strings, identifiers, locators or node ids.
    """

    annotations = {item.annotation_id: item for item in source.annotations}
    if len(annotations) != len(source.annotations):
        raise ValueError("duplicate annotation id in headword candidate research")

    parenthesis_outcomes: Counter[str] = Counter()
    parenthesis_core_cardinality: Counter[str] = Counter()
    parenthesis_expanded_cardinality: Counter[str] = Counter()
    slash_outcomes: Counter[str] = Counter()
    slash_left_cardinality: Counter[str] = Counter()
    slash_right_cardinality: Counter[str] = Counter()
    parenthesis_eligible = 0
    slash_eligible = 0
    excluded = 0

    for alignment in alignments:
        annotation = annotations.get(alignment.annotation_id)
        if annotation is None:
            raise ValueError(
                "alignment references unknown annotation in headword candidate research"
            )
        parenthesis_candidates = simple_parenthesis_candidate_tokens(
            annotation.headword
        )
        slash_candidates = simple_token_slash_candidate_tokens(annotation.headword)
        syntax_relevant = any(char in annotation.headword for char in "()/")

        for occurrence in alignment.occurrences:
            line_node = occurrence.context_line_node
            if line_node is None:
                continue
            if occurrence.reason not in {
                BurnsAlignmentReason.NONE,
                BurnsAlignmentReason.HEADWORD_NOT_FOUND,
                BurnsAlignmentReason.AMBIGUOUS_HEADWORD_SPAN,
            }:
                continue
            if line_node not in index.line_words:
                raise ValueError(
                    "headword candidate research occurrence lacks indexed context line"
                )

            if parenthesis_candidates is not None:
                parenthesis_eligible += 1
                core, expanded = parenthesis_candidates
                core_spans = _candidate_spans(core, line_node, index)
                expanded_spans = _candidate_spans(expanded, line_node, index)
                parenthesis_core_cardinality[
                    _candidate_count_bucket(len(core_spans))
                ] += 1
                parenthesis_expanded_cardinality[
                    _candidate_count_bucket(len(expanded_spans))
                ] += 1
                if len(core_spans) > 1 or len(expanded_spans) > 1:
                    parenthesis_outcomes["ambiguous"] += 1
                elif core_spans and expanded_spans:
                    parenthesis_outcomes["core_and_expanded"] += 1
                elif core_spans:
                    parenthesis_outcomes["core_only"] += 1
                elif expanded_spans:
                    parenthesis_outcomes["expanded_only"] += 1
                else:
                    parenthesis_outcomes["no_match"] += 1
                continue

            if slash_candidates is not None:
                slash_eligible += 1
                left, right = slash_candidates
                left_spans = _candidate_spans(left, line_node, index)
                right_spans = _candidate_spans(right, line_node, index)
                slash_left_cardinality[
                    _candidate_count_bucket(len(left_spans))
                ] += 1
                slash_right_cardinality[
                    _candidate_count_bucket(len(right_spans))
                ] += 1
                if len(left_spans) > 1 or len(right_spans) > 1:
                    slash_outcomes["ambiguous"] += 1
                elif left_spans and right_spans:
                    slash_outcomes["both_branches"] += 1
                elif left_spans:
                    slash_outcomes["left_only"] += 1
                elif right_spans:
                    slash_outcomes["right_only"] += 1
                else:
                    slash_outcomes["no_match"] += 1
                continue

            if syntax_relevant or "[" in annotation.headword or "]" in annotation.headword:
                excluded += 1

    return {
        "parentheses": {
            **_candidate_research_payload(
                parenthesis_eligible,
                parenthesis_outcomes,
                _CANDIDATE_RESEARCH_PARENTHESES,
            ),
            "core_span_cardinality": _counter_payload(parenthesis_core_cardinality),
            "expanded_span_cardinality": _counter_payload(parenthesis_expanded_cardinality),
        },
        "token_internal_slash": {
            **_candidate_research_payload(
                slash_eligible,
                slash_outcomes,
                _CANDIDATE_RESEARCH_SLASH,
            ),
            "left_span_cardinality": _counter_payload(slash_left_cardinality),
            "right_span_cardinality": _counter_payload(slash_right_cardinality),
        },
        "excluded_mixed_or_unsupported": excluded,
    }


def _headword_audit_outcome(occurrence) -> str | None:
    """Return a lexical-expression outcome only for an exactly resolved line context."""

    if occurrence.context_line_node is None:
        return None
    if (
        occurrence.anchor_kind is BurnsAnchorKind.WORD_SPAN
        and occurrence.confidence is BurnsAlignmentConfidence.EXACT_LEXICAL
        and occurrence.reason is BurnsAlignmentReason.NONE
    ):
        return "matched"
    if (
        occurrence.anchor_kind is BurnsAnchorKind.LINE
        and occurrence.reason is BurnsAlignmentReason.HEADWORD_NOT_FOUND
    ):
        return "not_found"
    if (
        occurrence.anchor_kind is BurnsAnchorKind.LINE
        and occurrence.reason is BurnsAlignmentReason.AMBIGUOUS_HEADWORD_SPAN
    ):
        return "ambiguous_span"
    return None


def _headword_audit_bucket(counter: Counter[str]) -> dict[str, int]:
    return {
        **{name: counter.get(name, 0) for name in _HEADWORD_AUDIT_OUTCOMES},
        "occurrences": sum(counter.values()),
    }


def aggregate_headword_expression_stats(
    *,
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
) -> dict[str, object]:
    """Cross-tab authored headword shapes against current exact lexical outcomes.

    The payload contains only static shape labels and counts. It intentionally
    omits Burns strings, locators, ids, source provenance, and CUC line content.
    """

    annotations = {item.annotation_id: item for item in source.annotations}
    if len(annotations) != len(source.annotations):
        raise ValueError("duplicate annotation id in headword-expression audit source")

    outcomes: Counter[str] = Counter()
    flag_buckets: dict[str, Counter[str]] = defaultdict(Counter)
    exclusive_buckets: dict[str, Counter[str]] = defaultdict(Counter)
    parenthesis_buckets: dict[str, Counter[str]] = defaultdict(Counter)
    syntax_signature_buckets: dict[str, Counter[str]] = defaultdict(Counter)
    marker_signature_buckets: dict[str, Counter[str]] = defaultdict(Counter)

    boolean_flags = (
        "parentheses",
        "square_brackets",
        "slash",
        "trailing_editorial_marker",
        "unbalanced_parentheses",
        "unbalanced_square_brackets",
    )

    for alignment in alignments:
        annotation = annotations.get(alignment.annotation_id)
        if annotation is None:
            raise ValueError(
                "alignment references unknown annotation in headword-expression audit"
            )
        shape = classify_headword_expression(annotation.headword)
        for occurrence in alignment.occurrences:
            outcome = _headword_audit_outcome(occurrence)
            if outcome is None:
                continue
            outcomes[outcome] += 1
            exclusive_buckets[str(shape["exclusive_class"])][outcome] += 1

            signature_parts = [
                label
                for flag, label in (
                    ("parentheses", "parentheses"),
                    ("square_brackets", "square_brackets"),
                    ("slash", "slash"),
                    ("trailing_editorial_marker", "marker"),
                )
                if bool(shape[flag])
            ]
            syntax_signature = "+".join(signature_parts) if signature_parts else "clean"
            syntax_signature_buckets[syntax_signature][outcome] += 1

            marker_signature = str(shape["trailing_editorial_markers"])
            if marker_signature:
                marker_signature_buckets[marker_signature][outcome] += 1

            for flag in boolean_flags:
                if bool(shape[flag]):
                    flag_buckets[flag][outcome] += 1
            parenthesis_shape = str(shape["parenthesis_shape"])
            if parenthesis_shape != "none":
                parenthesis_buckets[parenthesis_shape][outcome] += 1

    return {
        "eligible_occurrences": sum(outcomes.values()),
        "outcomes": _counter_payload(outcomes),
        "exclusive_classes": {
            key: _headword_audit_bucket(counter)
            for key, counter in sorted(exclusive_buckets.items())
        },
        "flags": {
            key: _headword_audit_bucket(counter)
            for key, counter in sorted(flag_buckets.items())
        },
        "parenthesis_shapes": {
            key: _headword_audit_bucket(counter)
            for key, counter in sorted(parenthesis_buckets.items())
        },
        "syntax_signatures": {
            key: _headword_audit_bucket(counter)
            for key, counter in sorted(syntax_signature_buckets.items())
        },
        "editorial_marker_signatures": {
            key: _headword_audit_bucket(counter)
            for key, counter in sorted(marker_signature_buckets.items())
        },
    }


_LINE_DRIFT_OFFSETS = (-2, -1, 1, 2)
_LINE_DRIFT_OUTCOMES = (
    "ambiguous_neighbor_span",
    "multi_neighbor",
    "no_neighbor_match",
    "unique_neighbor",
)


def _offset_label(offset: int) -> str:
    return f"{offset:+d}"


def _line_drift_bucket(counter: Counter[str]) -> dict[str, int]:
    return {
        **{name: counter.get(name, 0) for name in _LINE_DRIFT_OUTCOMES},
        "occurrences": sum(counter.values()),
    }


def aggregate_feature_only_lane_stats(
    *,
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
) -> dict[str, object]:
    """Measure exact-occurrence multiplicity for a start-word lane schema.

    The returned payload contains aggregate counts only. It never emits source
    strings, identifiers, CUC node ids, or locators.
    """

    annotations = {item.annotation_id: item for item in source.annotations}
    if len(annotations) != len(source.annotations):
        raise ValueError("duplicate annotation id in feature-only lane audit source")

    by_start: dict[int, list[tuple[tuple[object, ...], tuple[int, ...], int, str]]] = defaultdict(list)
    span_lengths: Counter[int] = Counter()
    occurrences = 0

    for alignment in alignments:
        annotation = annotations.get(alignment.annotation_id)
        if annotation is None:
            raise ValueError("alignment references unknown annotation in feature-only lane audit")
        for occurrence in alignment.occurrences:
            if not (
                occurrence.disposition is BurnsAlignmentDisposition.ALIGNED
                and occurrence.confidence is BurnsAlignmentConfidence.EXACT_LEXICAL
                and occurrence.anchor_kind is BurnsAnchorKind.WORD_SPAN
                and occurrence.anchor_nodes
            ):
                continue

            span = tuple(occurrence.anchor_nodes)
            if any(node not in index.word_g_cons for node in span):
                raise ValueError("exact Burns lexical span contains a non-word CUC node")
            if len(set(span)) != len(span):
                raise ValueError("exact Burns lexical span contains duplicate word nodes")

            start = span[0]
            identity = (
                alignment.annotation_id,
                occurrence.target_ordinal,
                occurrence.occurrence_id,
            )
            by_start[start].append(
                (
                    identity,
                    span,
                    annotation.workbook_number,
                    annotation.semantic_status.value,
                )
            )
            span_lengths[len(span)] += 1
            occurrences += 1

    lanes_per_start: Counter[int] = Counter()
    identical_span_groups: Counter[int] = Counter()
    starts_with_multiple_distinct_spans = 0
    starts_with_multiple_categories = 0
    starts_with_multiple_statuses = 0
    max_lane = 0

    for entries in by_start.values():
        ordered = sorted(entries, key=lambda item: item[0])
        lane_count = len(ordered)
        lanes_per_start[lane_count] += 1
        max_lane = max(max_lane, lane_count)

        spans = Counter(item[1] for item in ordered)
        for multiplicity in spans.values():
            identical_span_groups[multiplicity] += 1
        if len(spans) > 1:
            starts_with_multiple_distinct_spans += 1
        if len({item[2] for item in ordered}) > 1:
            starts_with_multiple_categories += 1
        if len({item[3] for item in ordered}) > 1:
            starts_with_multiple_statuses += 1

    return {
        "occurrences": occurrences,
        "start_words": len(by_start),
        "max_lane": max_lane,
        "lanes_per_start": _counter_payload(lanes_per_start),
        "span_lengths": _counter_payload(span_lengths),
        "identical_span_multiplicity": _counter_payload(identical_span_groups),
        "starts_with_multiple_distinct_spans": starts_with_multiple_distinct_spans,
        "starts_with_multiple_categories": starts_with_multiple_categories,
        "starts_with_multiple_statuses": starts_with_multiple_statuses,
    }


def aggregate_line_address_drift_stats(
    *,
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
) -> dict[str, object]:
    """Audit exact neighboring-line rescues for HEADWORD_NOT_FOUND occurrences.

    This is diagnostic only. It never changes an occurrence anchor or treats a
    neighboring lexical coincidence as an address correction.
    """

    annotations = {item.annotation_id: item for item in source.annotations}
    if len(annotations) != len(source.annotations):
        raise ValueError("duplicate annotation id in line-drift audit source")

    reverse_lines: dict[int, tuple[str, str, int]] = {}
    for key, node in index.line_nodes.items():
        if node in reverse_lines:
            raise ValueError("CUC line node has multiple structural identities")
        reverse_lines[node] = key

    occurrences = 0
    outcomes: Counter[str] = Counter()
    available_offsets: Counter[str] = Counter()
    matched_offsets: Counter[str] = Counter()
    unique_offsets: Counter[str] = Counter()
    syntax_buckets: dict[str, Counter[str]] = defaultdict(Counter)
    unique_rescue_lines: dict[tuple[str, str, int], list[int]] = defaultdict(list)

    for alignment in alignments:
        annotation = annotations.get(alignment.annotation_id)
        if annotation is None:
            raise ValueError("alignment references unknown annotation in line-drift audit")
        syntax_class = str(classify_headword_expression(annotation.headword)["exclusive_class"])
        tokens = _headword_tokens(annotation.headword)

        for occurrence in alignment.occurrences:
            if occurrence.reason is not BurnsAlignmentReason.HEADWORD_NOT_FOUND:
                continue
            line_node = occurrence.context_line_node
            if line_node is None:
                raise ValueError("HEADWORD_NOT_FOUND occurrence lacks context line")
            identity = reverse_lines.get(line_node)
            if identity is None:
                raise ValueError(
                    "HEADWORD_NOT_FOUND context line has no unique CUC structural identity"
                )
            tablet, column, line = identity
            occurrences += 1

            matched: dict[int, int] = {}
            for offset in _LINE_DRIFT_OFFSETS:
                neighbor = index.line_nodes.get((tablet, column, line + offset))
                if neighbor is None:
                    continue
                label = _offset_label(offset)
                available_offsets[label] += 1
                spans = _candidate_spans(tokens, neighbor, index)
                if spans:
                    matched_offsets[label] += 1
                    matched[offset] = len(spans)

            if not matched:
                outcome = "no_neighbor_match"
            elif len(matched) > 1:
                outcome = "multi_neighbor"
            else:
                offset, span_count = next(iter(matched.items()))
                if span_count == 1:
                    outcome = "unique_neighbor"
                    label = _offset_label(offset)
                    unique_offsets[label] += 1
                    unique_rescue_lines[(tablet, column, offset)].append(line)
                else:
                    outcome = "ambiguous_neighbor_span"

            outcomes[outcome] += 1
            syntax_buckets[syntax_class][outcome] += 1

    run_histograms: dict[str, Counter[int]] = defaultdict(Counter)
    for (_, _, offset), lines in unique_rescue_lines.items():
        ordered = sorted(set(lines))
        if not ordered:
            continue
        run_length = 1
        previous = ordered[0]
        for line in ordered[1:]:
            if line == previous + 1:
                run_length += 1
            else:
                run_histograms[_offset_label(offset)][run_length] += 1
                run_length = 1
            previous = line
        run_histograms[_offset_label(offset)][run_length] += 1

    return {
        "occurrences": occurrences,
        "outcomes": _counter_payload(outcomes),
        "available_neighbor_offsets": dict(sorted(available_offsets.items())),
        "matched_neighbor_offsets": dict(sorted(matched_offsets.items())),
        "unique_rescue_offsets": dict(sorted(unique_offsets.items())),
        "unique_rescue_run_lengths": {
            label: _counter_payload(counter)
            for label, counter in sorted(run_histograms.items())
        },
        "syntax_classes": {
            key: _line_drift_bucket(counter)
            for key, counter in sorted(syntax_buckets.items())
        },
    }


def aggregate_lexical_gap_stats(
    *,
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
    index: ReviewedCucIndex,
) -> dict[str, object]:
    """Characterize HEADWORD_NOT_FOUND structurally without source strings."""

    annotations = {item.annotation_id: item for item in source.annotations}
    if len(annotations) != len(source.annotations):
        raise ValueError("duplicate annotation id in lexical-gap audit source")

    occurrence_count = 0
    headword_token_counts: Counter[int] = Counter()
    line_word_counts: Counter[int] = Counter()
    overlap_counts: Counter[str] = Counter()
    prefix_candidates: Counter[str] = Counter()
    suffix_candidates: Counter[str] = Counter()
    contains_candidates: Counter[str] = Counter()

    for alignment in alignments:
        annotation = annotations.get(alignment.annotation_id)
        if annotation is None:
            raise ValueError("alignment references unknown annotation in lexical-gap audit")
        for occurrence in alignment.occurrences:
            if occurrence.reason is not BurnsAlignmentReason.HEADWORD_NOT_FOUND:
                continue
            line_node = occurrence.context_line_node
            if line_node is None or line_node not in index.line_words:
                raise ValueError("HEADWORD_NOT_FOUND occurrence lacks indexed context line")
            words = index.line_words[line_node]
            try:
                values = tuple(index.word_g_cons[word] for word in words)
            except KeyError as exc:
                raise ValueError("lexical-gap audit line references word without g_cons") from exc

            tokens = _headword_tokens(annotation.headword)
            occurrence_count += 1
            headword_token_counts[len(tokens)] += 1
            line_word_counts[len(values)] += 1

            wanted = Counter(tokens)
            available = Counter(values)
            exact_hits = sum(min(count, available[token]) for token, count in wanted.items())
            if exact_hits == 0:
                overlap_counts["none"] += 1
            elif exact_hits == sum(wanted.values()):
                overlap_counts["all_present_noncontiguous_or_reordered"] += 1
            else:
                overlap_counts["partial"] += 1

            if len(tokens) == 1:
                token = tokens[0]
                prefix = sum(value != token and value.startswith(token) for value in values)
                suffix = sum(value != token and value.endswith(token) for value in values)
                contains = sum(value != token and token in value for value in values)
                prefix_candidates[_candidate_count_bucket(prefix)] += 1
                suffix_candidates[_candidate_count_bucket(suffix)] += 1
                contains_candidates[_candidate_count_bucket(contains)] += 1

    return {
        "occurrences": occurrence_count,
        "headword_token_counts": _counter_payload(headword_token_counts),
        "line_word_counts": _counter_payload(line_word_counts),
        "exact_token_overlap": _counter_payload(overlap_counts),
        "single_token_prefix_candidates": _counter_payload(prefix_candidates),
        "single_token_suffix_candidates": _counter_payload(suffix_candidates),
        "single_token_contains_candidates": _counter_payload(contains_candidates),
    }


def aggregate_alignment_stats(
    *,
    file_count: int,
    source: NormalizedBurnsSource,
    alignments: tuple[BurnsAnnotationAlignment, ...],
) -> dict[str, object]:
    """Return source-safe aggregate statistics from completed alignments."""

    annotation_dispositions: Counter[str] = Counter()
    reference_statuses: Counter[str] = Counter()
    reference_failure_reasons: Counter[str] = Counter()
    reference_failure_shapes: Counter[str] = Counter()
    occurrence_dispositions: Counter[str] = Counter()
    occurrence_reasons: Counter[str] = Counter()
    anchor_kinds: Counter[str] = Counter()
    word_span_lengths: Counter[int] = Counter()
    node_annotations: dict[int, set[str]] = defaultdict(set)

    for alignment in alignments:
        annotation_dispositions[alignment.disposition.value] += 1
        reference_statuses[alignment.parsed_reference.status.value] += 1
        if alignment.reason is BurnsAlignmentReason.REFERENCE_PARSE_FAILED:
            reason = alignment.parsed_reference.reason.value
            reference_failure_reasons[reason] += 1
            reference_failure_shapes[
                f"{reason}|ktu={_source_safe_shape(alignment.parsed_reference.original_ktu)}"
                f"|ref={_source_safe_shape(alignment.parsed_reference.original_reference)}"
            ] += 1
        for occurrence in alignment.occurrences:
            occurrence_dispositions[occurrence.disposition.value] += 1
            occurrence_reasons[occurrence.reason.value] += 1
            if occurrence.anchor_kind is not None:
                anchor_kinds[occurrence.anchor_kind.value] += 1
            if occurrence.anchor_kind is BurnsAnchorKind.WORD_SPAN:
                word_span_lengths[len(occurrence.anchor_nodes)] += 1
            for node in occurrence.anchor_nodes:
                node_annotations[node].add(alignment.annotation_id)

    annotation_multiplicities = tuple(len(ids) for ids in node_annotations.values())
    return {
        "source": {
            "files": file_count,
            "records": len(source.records),
            "annotations": len(source.annotations),
        },
        "annotation_dispositions": _counter_payload(annotation_dispositions),
        "reference_statuses": _counter_payload(reference_statuses),
        "reference_failure_reasons": _counter_payload(reference_failure_reasons),
        "reference_failure_shapes": _counter_payload(reference_failure_shapes),
        "occurrence_dispositions": _counter_payload(occurrence_dispositions),
        "occurrence_reasons": _counter_payload(occurrence_reasons),
        "anchor_kinds": _counter_payload(anchor_kinds),
        "word_span_lengths": _counter_payload(word_span_lengths),
        "selected_anchor_node_multiplicity": {
            "nodes_with_multiple_annotations": sum(
                1 for count in annotation_multiplicities if count > 1
            ),
            "max_annotations_per_node": max(annotation_multiplicities, default=0),
        },
    }


def _write_private_report(path: Path, payload: str) -> None:
    """Atomically publish an explicitly requested local report as owner-only."""

    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    staged: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            staged = handle.name
            os.chmod(staged, 0o600)
            handle.write(payload)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, path)
        staged = None
        os.chmod(path, 0o600)
    finally:
        if staged is not None:
            try:
                os.unlink(staged)
            except FileNotFoundError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit Burns→CUC alignment; stdout is aggregate-only by default."
    )
    parser.add_argument(
        "--cuc",
        required=True,
        type=Path,
        help="path to the reviewed CUC 0.2.8 Text-Fabric directory",
    )
    parser.add_argument(
        "--workbooks",
        type=Path,
        help="local Workbooks directory; omit to fetch/verify the pinned deposit",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="explicit local path for the full Burns-derived alignment report",
    )
    args = parser.parse_args(argv)

    workbooks_path = (
        args.workbooks.expanduser()
        if args.workbooks is not None
        else ensure(WORKBOOKS, root=ROOT)
    )
    workbook_source = load_pdf_directory(workbooks_path)
    normalized = normalize_workbook_records(workbook_source.records)
    index = build_reviewed_cuc_index(args.cuc.expanduser())
    alignments = align_burns_source(normalized, index)

    stats = aggregate_alignment_stats(
        file_count=len(workbook_source.files),
        source=normalized,
        alignments=alignments,
    )
    print(
        json.dumps(
            stats,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )

    if args.report is not None:
        _write_private_report(
            args.report,
            alignment_report_json(normalized, alignments, index),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
