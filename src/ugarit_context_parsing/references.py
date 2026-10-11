from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .annotations import BurnsTextualStatus
from .identifiers import normalize_cuc_tablet

MAX_REFERENCE_RANGE_SPAN = 200


class BurnsReferenceStatus(str, Enum):
    PARSED = "parsed"
    NON_TEXTUAL = "non_textual"
    INVALID_KTU = "invalid_ktu"
    UNSUPPORTED = "unsupported"
    MALFORMED = "malformed"


class BurnsReferenceReason(str, Enum):
    NONE = "none"
    NON_TEXTUAL = "non_textual"
    INVALID_KTU = "invalid_ktu"
    UNSUPPORTED_WORDING = "unsupported_wording"
    UNCERTAIN_MARKER = "uncertain_marker"
    UNSUPPORTED_PUNCTUATION = "unsupported_punctuation"
    MALFORMED_STRUCTURE = "malformed_structure"
    REVERSED_RANGE = "reversed_range"
    RANGE_TOO_LARGE = "range_too_large"
    DUPLICATE_TARGET = "duplicate_target"


@dataclass(frozen=True)
class BurnsTarget:
    tablet: str
    column: str | None
    line: int | None


@dataclass(frozen=True)
class ParsedBurnsReference:
    original_ktu: str
    original_reference: str
    status: BurnsReferenceStatus
    reason: BurnsReferenceReason
    targets: tuple[BurnsTarget, ...]


_ROMAN = r"[IVXLCDM]+"
_COLUMN_PREFIX_RE = re.compile(rf"^({_ROMAN})\s*\.\s*(.*)$")
_CANONICAL_ROMAN_RE = re.compile(
    r"^(?=[IVXLCDM]+$)"
    r"M{0,3}"
    r"(?:CM|CD|D?C{0,3})"
    r"(?:XC|XL|L?X{0,3})"
    r"(?:IX|IV|V?I{0,3})$"
)
_RANGE_RE = re.compile(r"^(\d+)\s*-\s*(\d+)$")
_LINE_RE = re.compile(r"^\d+$")
_ALPHA_RE = re.compile(r"[A-Za-z]+")
_ALLOWED_RE = re.compile(r"^[0-9IVXLCDM.,;\-\s]+$")


def _result(
    original_ktu: str,
    original_reference: str,
    status: BurnsReferenceStatus,
    reason: BurnsReferenceReason,
    targets: tuple[BurnsTarget, ...] = (),
) -> ParsedBurnsReference:
    return ParsedBurnsReference(
        original_ktu=original_ktu,
        original_reference=original_reference,
        status=status,
        reason=reason,
        targets=targets,
    )


def _reject(
    original_ktu: str,
    original_reference: str,
    status: BurnsReferenceStatus,
    reason: BurnsReferenceReason,
) -> ParsedBurnsReference:
    return _result(original_ktu, original_reference, status, reason, ())


def _classify_unsupported(text: str) -> tuple[BurnsReferenceStatus, BurnsReferenceReason] | None:
    if "?" in text:
        return BurnsReferenceStatus.UNSUPPORTED, BurnsReferenceReason.UNCERTAIN_MARKER

    words = _ALPHA_RE.findall(text)
    if words:
        # Lower-case Roman-looking text is structurally close enough to the
        # documented syntax to report malformed rather than prose, but it is
        # never normalized silently: Burns' documented column notation is
        # uppercase Roman numerals.
        if all(word.upper() == word and re.fullmatch(_ROMAN, word) for word in words):
            pass
        elif all(re.fullmatch(_ROMAN, word.upper()) for word in words):
            return BurnsReferenceStatus.MALFORMED, BurnsReferenceReason.MALFORMED_STRUCTURE
        else:
            return BurnsReferenceStatus.UNSUPPORTED, BurnsReferenceReason.UNSUPPORTED_WORDING

    if not _ALLOWED_RE.fullmatch(text):
        return BurnsReferenceStatus.UNSUPPORTED, BurnsReferenceReason.UNSUPPORTED_PUNCTUATION
    return None


def _parse_item(
    item: str,
) -> tuple[tuple[int, ...] | None, BurnsReferenceReason | None]:
    if _LINE_RE.fullmatch(item):
        return (int(item),), None

    match = _RANGE_RE.fullmatch(item)
    if match is None:
        return None, BurnsReferenceReason.MALFORMED_STRUCTURE

    start = int(match.group(1))
    end = int(match.group(2))
    if end < start:
        return None, BurnsReferenceReason.REVERSED_RANGE
    if end - start > MAX_REFERENCE_RANGE_SPAN:
        return None, BurnsReferenceReason.RANGE_TOO_LARGE
    return tuple(range(start, end + 1)), None


def parse_burns_reference(
    *,
    ktu: str,
    reference: str,
    textual_status: BurnsTextualStatus,
) -> ParsedBurnsReference:
    """Parse one normalized Burns KTU + Column-C locator conservatively.

    The function is intentionally syntax-only. A syntactically valid tablet is
    not looked up in CUC here; membership and anchor selection belong to the
    later alignment layer.
    """

    original_ktu = ktu
    original_reference = reference

    if textual_status is BurnsTextualStatus.NON_TEXTUAL_NOT_ATTESTED:
        return _reject(
            original_ktu,
            original_reference,
            BurnsReferenceStatus.NON_TEXTUAL,
            BurnsReferenceReason.NON_TEXTUAL,
        )

    tablet = normalize_cuc_tablet(ktu)
    if not tablet:
        return _reject(
            original_ktu,
            original_reference,
            BurnsReferenceStatus.INVALID_KTU,
            BurnsReferenceReason.INVALID_KTU,
        )

    text = reference.strip()
    if not text:
        return _result(
            original_ktu,
            original_reference,
            BurnsReferenceStatus.PARSED,
            BurnsReferenceReason.NONE,
            (BurnsTarget(tablet, None, None),),
        )

    unsupported = _classify_unsupported(text)
    if unsupported is not None:
        status, reason = unsupported
        return _reject(original_ktu, original_reference, status, reason)

    groups = text.split(";")
    if not groups or any(not group.strip() for group in groups):
        return _reject(
            original_ktu,
            original_reference,
            BurnsReferenceStatus.MALFORMED,
            BurnsReferenceReason.MALFORMED_STRUCTURE,
        )

    targets: list[BurnsTarget] = []
    seen: set[BurnsTarget] = set()

    for raw_group in groups:
        group = raw_group.strip()
        column: str | None = None

        items = group.split(",")
        if any(not item.strip() for item in items):
            return _reject(
                original_ktu,
                original_reference,
                BurnsReferenceStatus.MALFORMED,
                BurnsReferenceReason.MALFORMED_STRUCTURE,
            )

        for raw_item in items:
            item = raw_item.strip()
            prefix = _COLUMN_PREFIX_RE.fullmatch(item)
            if prefix is not None:
                column = prefix.group(1)
                if _CANONICAL_ROMAN_RE.fullmatch(column) is None:
                    return _reject(
                        original_ktu,
                        original_reference,
                        BurnsReferenceStatus.MALFORMED,
                        BurnsReferenceReason.MALFORMED_STRUCTURE,
                    )
                item = prefix.group(2).strip()
                if not item:
                    return _reject(
                        original_ktu,
                        original_reference,
                        BurnsReferenceStatus.MALFORMED,
                        BurnsReferenceReason.MALFORMED_STRUCTURE,
                    )
            elif _ALPHA_RE.search(item):
                return _reject(
                    original_ktu,
                    original_reference,
                    BurnsReferenceStatus.MALFORMED,
                    BurnsReferenceReason.MALFORMED_STRUCTURE,
                )

            lines, error = _parse_item(item)
            if error is not None or lines is None:
                return _reject(
                    original_ktu,
                    original_reference,
                    BurnsReferenceStatus.MALFORMED,
                    error or BurnsReferenceReason.MALFORMED_STRUCTURE,
                )

            for line in lines:
                target = BurnsTarget(tablet, column, line)
                if target in seen:
                    return _reject(
                        original_ktu,
                        original_reference,
                        BurnsReferenceStatus.MALFORMED,
                        BurnsReferenceReason.DUPLICATE_TARGET,
                    )
                seen.add(target)
                targets.append(target)

    return _result(
        original_ktu,
        original_reference,
        BurnsReferenceStatus.PARSED,
        BurnsReferenceReason.NONE,
        tuple(targets),
    )
