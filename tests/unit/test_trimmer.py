"""
DataShuddi -- Unit Tests: Context Trimmer (trim-1 protocol).

Verifies verbatim line preservation, omission markers, and error sifting.
Follows the AAA (Arrange, Act, Assert) testing pattern.
"""
from src.utils.trimmer import trim_context, trim_validation_evidence


class TestContextTrimmer:
    """Unit tests for trim-1 context compression logic."""

    def test_blank_query_returns_unchanged(self) -> None:
        """Arrange: Valid context, blank query. Act: trim_context. Assert: Context unchanged."""
        context = "Line 1\nLine 2\nLine 3\n" * 50
        res = trim_context(context, "")
        assert res.unchanged is True
        assert res.output == context

    def test_short_context_under_minimum_chars_returns_unchanged(self) -> None:
        """Arrange: Context < 300 chars. Act: trim_context. Assert: Kept unchanged."""
        context = "Short log output.\nError occurred."
        res = trim_context(context, "Error")
        assert res.unchanged is True
        assert res.output == context

    def test_verbatim_extraction_with_omission_markers(self) -> None:
        """Arrange: 100-line document with a single targeted failure line. Act: trim. Assert: Sifted with markers."""
        lines = [f"Normal transaction logging event number {i:03d}." for i in range(100)]
        lines[42] = "CRITICAL: Residual SSN detected in payroll record 42."
        context = "\n".join(lines)

        res = trim_context(context, "Residual SSN", point="conservative")

        assert res.unchanged is False
        assert res.removed_lines > 50
        assert "CRITICAL: Residual SSN detected in payroll record 42." in res.output
        assert "[... " in res.output
        assert "lines omitted ...]" in res.output

    def test_verbatim_exactness_no_modification(self) -> None:
        """Arrange: Text with specific casing, tabs, and symbols. Act: trim. Assert: Matched lines are exact bytes."""
        prefix = "    # Tabbed comment block header\n" + ("Irrelevant filler line.\n" * 30)
        target = "    def process_sensitive_doc(doc_id: str) -> None:\n        # Target failure point\n"
        suffix = "Irrelevant trailing line.\n" * 30
        context = prefix + target + suffix

        res = trim_context(context, "process_sensitive_doc failure", point="conservative")

        assert res.unchanged is False
        assert target in res.output

    def test_trim_validation_evidence_helper_fallback(self) -> None:
        """Arrange: Empty or non-matching inputs. Act: trim_validation_evidence. Assert: Safe string return."""
        # Empty text
        assert trim_validation_evidence("", ["Some error"]) == ""

        # Empty errors
        sample = "Line of text.\n" * 40
        assert trim_validation_evidence(sample, []) == sample[:2500]

        # Valid error sifting
        doc = ("Filler paragraph text.\n" * 40) + "Residual pattern US_SSN at offset 120.\n" + ("Filler line.\n" * 40)
        evidence = trim_validation_evidence(doc, ["Residual pattern US_SSN"])
        assert "Residual pattern US_SSN at offset 120." in evidence
        assert len(evidence) < len(doc)
