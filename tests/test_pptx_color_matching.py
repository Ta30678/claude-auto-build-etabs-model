"""Tests for pptx_to_elements.py color matching improvements.

Tests the fuzzy color matching, fill-priority, and dual-color fallback logic.
These tests use the internal functions directly with mock legend data.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.pptx_to_elements import (
    _fuzzy_color_match,
    _resolve_pptx_legend,
    LegendEntry,
)


def _make_entry(element_type="beam", section="B55X80", color="FF0000"):
    return LegendEntry(
        element_type=element_type,
        section=section,
        color_name=color,
        color_rgb=[int(color[i:i+2], 16) for i in (0, 2, 4)],
        specificity=2,
        is_diaphragm=False,
        prefix="B",
        label=section,
    )


class TestFuzzyColorMatch:
    """Test _fuzzy_color_match with ±15 default tolerance."""

    def test_exact_match(self):
        legend = {"FF0000": [_make_entry()]}
        result = _fuzzy_color_match("FF0000", legend)
        assert result is not None
        assert result[0].section == "B55X80"

    def test_fuzzy_within_15(self):
        """Color off by 10 per channel should match with tolerance=15."""
        legend = {"FF0000": [_make_entry()]}
        # F50A00 = (245, 10, 0) vs (255, 0, 0) — max diff = 10
        result = _fuzzy_color_match("F50A00", legend)
        assert result is not None

    def test_fuzzy_at_boundary_15(self):
        """Color off by exactly 15 should still match."""
        legend = {"FF0000": [_make_entry()]}
        # F00F00 = (240, 15, 0) vs (255, 0, 0) — max diff = 15
        result = _fuzzy_color_match("F00F00", legend)
        assert result is not None

    def test_fuzzy_beyond_15(self):
        """Color off by 16 should NOT match with default tolerance."""
        legend = {"FF0000": [_make_entry()]}
        # EF1100 = (239, 17, 0) vs (255, 0, 0) — max diff = 17
        result = _fuzzy_color_match("EF1100", legend)
        assert result is None

    def test_old_tolerance_5_would_miss(self):
        """Colors that old ±5 tolerance would miss but ±15 catches."""
        legend = {"FF0000": [_make_entry()]}
        # F80800 = (248, 8, 0) vs (255, 0, 0) — max diff = 8
        result = _fuzzy_color_match("F80800", legend)
        assert result is not None

    def test_picks_closest_match(self):
        """When multiple legend colors are within tolerance, pick closest."""
        legend = {
            "FF0000": [_make_entry(section="B55X80", color="FF0000")],
            "F00000": [_make_entry(section="B40X70", color="F00000")],
        }
        # FE0000 is closer to FF0000 (diff=1) than F00000 (diff=14)
        result = _fuzzy_color_match("FE0000", legend)
        assert result is not None
        assert result[0].section == "B55X80"

    def test_custom_tolerance(self):
        """Explicit tolerance overrides default."""
        legend = {"FF0000": [_make_entry()]}
        # Off by 10 — should fail with tolerance=5
        result = _fuzzy_color_match("F50A00", legend, tolerance=5)
        assert result is None

    def test_no_legend_entries(self):
        result = _fuzzy_color_match("FF0000", {})
        assert result is None


class TestResolvePptxLegend:
    """Test _resolve_pptx_legend with geometry type filtering."""

    def test_line_matches_beam(self):
        legend = {"FF0000": [_make_entry(element_type="beam")]}
        entry = _resolve_pptx_legend("FF0000", "line", legend)
        assert entry is not None
        assert entry.element_type == "beam"

    def test_rectangle_matches_column(self):
        legend = {"00FF00": [_make_entry(element_type="column", section="C90X90")]}
        entry = _resolve_pptx_legend("00FF00", "rectangle", legend)
        assert entry is not None
        assert entry.element_type == "column"

    def test_fuzzy_resolve(self):
        """Resolve with fuzzy color match (±15)."""
        legend = {"FF0000": [_make_entry(element_type="beam")]}
        # Off by 8 — within ±15
        entry = _resolve_pptx_legend("F70800", "line", legend)
        assert entry is not None

    def test_no_match_returns_none(self):
        legend = {"FF0000": [_make_entry(element_type="beam")]}
        entry = _resolve_pptx_legend("0000FF", "line", legend)
        assert entry is None


class TestDualColorFallback:
    """Test that shape classification tries alternate color on failure.

    These test the concept — the actual implementation is in
    extract_and_classify_shapes which requires PPT shapes.
    We test the underlying resolve logic that enables the fallback.
    """

    def test_fill_color_in_legend_line_not(self):
        """If fill_color is in legend but line_color is not, fill should work."""
        legend = {"FF0000": [_make_entry(element_type="beam")]}
        # Primary (line_color) = 000000 (black, not in legend)
        entry = _resolve_pptx_legend("000000", "line", legend)
        assert entry is None
        # Fallback (fill_color) = FF0000 (red, in legend)
        entry = _resolve_pptx_legend("FF0000", "line", legend)
        assert entry is not None

    def test_line_color_in_legend_fill_not(self):
        """If line_color is in legend but fill_color is not, line should work."""
        legend = {"0000FF": [_make_entry(element_type="column", section="C90X90")]}
        # Primary (fill_color) = 000000 (not in legend)
        entry = _resolve_pptx_legend("000000", "rectangle", legend)
        assert entry is None
        # Fallback (line_color) = 0000FF (in legend)
        entry = _resolve_pptx_legend("0000FF", "rectangle", legend)
        assert entry is not None
