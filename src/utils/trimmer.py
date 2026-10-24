"""
trim_context -- Context Compression & Verbatim Line Filtering.

Implements the trim-1 GBDT-inspired verbatim line sifting protocol for DataShuddi.
Filters masked document text to extract exact lines surrounding schema validation
failures in milliseconds, preventing prompt bloat and eliminating CPU latency
in the Reflector node without hallucinations or PII leakage.
"""
import re
from collections.abc import Sequence
from typing import NamedTuple


class TrimResult(NamedTuple):
    """Result data structure for context trimming."""

    output: str
    kept_lines: int
    removed_lines: int
    unchanged: bool
    reason: str


# Operating Point Policies
_POLICIES = {
    "conservative": {
        "floor": 0.05,
        "context": 2,
        "gap": 3,
        "min_chars": 300,
        "min_cut": 0.10,
    },
    "balanced": {
        "floor": 0.15,
        "context": 1,
        "gap": 2,
        "min_chars": 300,
        "min_cut": 0.10,
    },
    "aggressive": {
        "floor": 0.35,
        "context": 0,
        "gap": 1,
        "min_chars": 300,
        "min_cut": 0.10,
    },
}

_ERROR_INDICATORS = {
    "error", "exception", "traceback", "failed", "fatal", "panic",
    "assertionerror", "typeerror", "valueerror", "residual", "ssn",
    "email", "length", "chars", "boundary", "short", "critical"
}

_HEADER_PATTERNS = [
    re.compile(r"^#+\s+"),                     # Markdown heading
    re.compile(r"^(def|class|async def)\s+"),  # Python function/class
    re.compile(r"^(function|class|export)\s+"),# JS/TS header
    re.compile(r"^\[.*\]$"),                   # Bracketed section
]


def _tokenize(text: str) -> list[str]:
    """Tokenize string into alphanumeric search tokens."""
    return [w.lower() for w in re.findall(r"\b\w{2,}\b", text)]


def _score_line(line: str, query_tokens: set[str]) -> float:
    """Compute relevance score for an individual document line."""
    stripped = line.strip()
    if not stripped:
        return 0.0

    lower = stripped.lower()
    line_tokens = set(_tokenize(stripped))

    # 1. Lexical token overlap (BM25 surrogate)
    overlap = len(line_tokens & query_tokens)
    lexical_score = (overlap / max(1, len(query_tokens))) * 1.5

    # 2. Structural error token matching
    error_bonus = 0.0
    for err in _ERROR_INDICATORS:
        if err in lower:
            error_bonus += 0.8
            break

    # 3. Stack trace & line number detection
    stack_bonus = 0.0
    if re.search(r"\b(?:line\s+\d+|character\s+\d+)\b", lower):
        stack_bonus += 1.0

    # 4. Heading & structural signature bonus
    header_bonus = 0.0
    for pat in _HEADER_PATTERNS:
        if pat.search(stripped):
            header_bonus += 0.3
            break

    return lexical_score + error_bonus + stack_bonus + header_bonus


def trim_context(context: str, query: str, point: str = "conservative") -> TrimResult:
    """
    Sift context to retain only verbatim lines relevant to the given query.

    Args:
        context: Raw or masked document string to be compressed.
        query: Query string containing target keywords or validation errors.
        point: Operating policy point ('conservative', 'balanced', or 'aggressive').

    Returns:
        TrimResult containing the pruned text and compression statistics.
    """
    if not query or not query.strip():
        return TrimResult(context, 0, 0, True, "blank query")

    policy = _POLICIES.get(point, _POLICIES["conservative"])

    if len(context) < policy["min_chars"]:
        return TrimResult(context, 0, 0, True, "context under minimum size")

    if "[... " in context and "lines omitted ...]" in context:
        return TrimResult(context, 0, 0, True, "context already has omission markers")

    lines = context.splitlines(keepends=True)
    n_lines = len(lines)
    if n_lines == 0:
        return TrimResult(context, 0, 0, True, "empty context")

    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return TrimResult(context, 0, 0, True, "no valid query tokens")

    scores = [_score_line(line, query_tokens) for line in lines]
    max_score = max(scores) if scores else 0.0

    if max_score <= 0.0:
        return TrimResult(context, 0, 0, True, "no relevant matches found")

    threshold = max_score * policy["floor"]
    kept_indices: set[int] = set()

    for i, s in enumerate(scores):
        if s >= threshold:
            kept_indices.add(i)
            ctx_radius = int(policy["context"])
            for offset in range(-ctx_radius, ctx_radius + 1):
                idx = i + offset
                if 0 <= idx < n_lines:
                    kept_indices.add(idx)

    # Fill small gaps between matched regions
    sorted_kept = sorted(kept_indices)
    max_gap = int(policy["gap"])
    for k in range(len(sorted_kept) - 1):
        gap_size = sorted_kept[k + 1] - sorted_kept[k] - 1
        if 0 < gap_size <= max_gap:
            for fill_idx in range(sorted_kept[k] + 1, sorted_kept[k + 1]):
                kept_indices.add(fill_idx)

    kept_count = len(kept_indices)
    removed_count = n_lines - kept_count
    cut_ratio = removed_count / max(1, n_lines)

    if cut_ratio < policy["min_cut"]:
        return TrimResult(context, n_lines, 0, True, "cut below min_cut threshold (<10%)")

    output_parts: list[str] = []
    omitted_count = 0

    for i, line in enumerate(lines):
        if i in kept_indices:
            if omitted_count > 0:
                output_parts.append(f"\n[... {omitted_count} lines omitted ...]\n\n")
                omitted_count = 0
            output_parts.append(line)
        else:
            omitted_count += 1

    if omitted_count > 0:
        output_parts.append(f"\n[... {omitted_count} lines omitted ...]\n")

    return TrimResult("".join(output_parts), kept_count, removed_count, False, "")


def trim_validation_evidence(
    masked_text: str,
    validation_errors: Sequence[str],
    max_chars: int = 2500,
) -> str:
    """
    Extract verbatim evidence lines relevant to validation errors for Reflector critique.

    Operates strictly on post-masked text to ensure zero PII leakage.

    Args:
        masked_text: Anonymized document text from Node 4.
        validation_errors: List of validation error strings emitted by Node 5.
        max_chars: Upper bound character budget for the returned evidence snippet.

    Returns:
        Pruned verbatim text snippet with omission markers.
    """
    if not masked_text or not validation_errors:
        return masked_text[:max_chars]

    query = " ".join(validation_errors)
    res = trim_context(masked_text, query, point="conservative")

    if res.unchanged or not res.output.strip():
        return masked_text[:max_chars]

    return res.output[:max_chars]
