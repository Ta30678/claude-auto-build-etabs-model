"""
Tests for gs_12_iterate pure logic functions.
No ETABS connection required.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "golden_scripts"))
from design.gs_12_iterate import (
    compute_column_ratio,
    compute_beam_ratio,
    propose_column_resize,
    propose_beam_resize,
    enforce_column_constraints,
    make_section_name,
    is_rooftop_ordinary,
)


# ── compute_column_ratio ──────────────────────────────────

class TestComputeColumnRatio:
    def test_basic(self):
        # 90x90cm column, PMMArea = 0.0081 m2 -> ratio = 0.0081 / 0.81 = 0.01
        assert compute_column_ratio(0.0081, 90, 90) == pytest.approx(0.01)

    def test_large_ratio(self):
        # 60x60cm column, PMMArea = 0.018 m2 -> ratio = 0.018 / 0.36 = 0.05
        assert compute_column_ratio(0.018, 60, 60) == pytest.approx(0.05)

    def test_rectangular(self):
        # 80x120cm column, PMMArea = 0.0192 m2 -> ratio = 0.0192 / 0.96 = 0.02
        assert compute_column_ratio(0.0192, 80, 120) == pytest.approx(0.02)

    def test_zero_area(self):
        assert compute_column_ratio(0, 90, 90) == 0

    def test_zero_dims(self):
        assert compute_column_ratio(0.01, 0, 90) == 0


# ── compute_beam_ratio ────────────────────────────────────

class TestComputeBeamRatio:
    def test_basic(self):
        # 55x80cm beam, cover=9cm, d_eff=71cm=0.71m, w=0.55m
        # area=0.55*0.71 = 0.3905, rebar=0.003905 -> ratio = 0.01
        expected_denom = 0.55 * 0.71
        ratio = compute_beam_ratio(expected_denom * 0.01, 55, 80, 0.09)
        assert ratio == pytest.approx(0.01)

    def test_high_ratio(self):
        # 40x60cm beam, cover=9cm, d_eff=51cm=0.51m, w=0.40m
        denom = 0.40 * 0.51
        ratio = compute_beam_ratio(denom * 0.03, 40, 60, 0.09)
        assert ratio == pytest.approx(0.03)

    def test_zero_rebar(self):
        assert compute_beam_ratio(0, 55, 80, 0.09) == 0


# ── propose_column_resize ─────────────────────────────────

class TestProposeColumnResize:
    def test_upsize_above_max(self):
        # ratio 5% > 4% -> upsize +10cm
        result = propose_column_resize(0.05, 80, 80)
        assert result == (90, 90, "up")

    def test_downsize_at_minimum(self):
        # ratio exactly 1% (== threshold) -> downsize
        result = propose_column_resize(0.01, 90, 90)
        assert result == (80, 80, "down")

    def test_no_change_in_range(self):
        # ratio 2% -> within range, no change
        result = propose_column_resize(0.02, 80, 80)
        assert result is None

    def test_downsize_clamped_to_min(self):
        # ratio 0.5% -> downsize, but 30cm is minimum
        result = propose_column_resize(0.005, 30, 30)
        assert result is None  # already at minimum

    def test_downsize_partial_clamp(self):
        # ratio 0.5% -> downsize from 35x40
        result = propose_column_resize(0.005, 35, 40, step=10, min_dim=30)
        assert result == (30, 30, "down")

    def test_just_above_downsize_threshold(self):
        # ratio 1.1% -> no downsize (> threshold)
        result = propose_column_resize(0.011, 90, 90)
        assert result is None

    def test_at_upsize_threshold(self):
        # ratio exactly 4% -> no upsize (not >)
        result = propose_column_resize(0.04, 80, 80)
        assert result is None


# ── propose_beam_resize ───────────────────────────────────

class TestProposeBeamResize:
    def test_width_first_upsize(self):
        # ratio 2.5% > 2% -> upsize width first
        result = propose_beam_resize(0.025, 40, 60)
        assert result == (45, 60, "up")

    def test_switch_to_depth(self):
        # W=70, D=60 -> W/D=1.17, (70+5)/60=1.25 > 1.2 -> depth increase
        result = propose_beam_resize(0.025, 70, 60)
        assert result == (70, 65, "up")

    def test_downsize_width(self):
        # ratio 0.5% < 1% -> downsize width
        result = propose_beam_resize(0.005, 55, 80)
        assert result == (50, 80, "down")

    def test_downsize_depth_when_width_at_min(self):
        # ratio 0.5% < 1%, width at min 25 -> try depth
        result = propose_beam_resize(0.005, 25, 50)
        assert result == (25, 45, "down")

    def test_no_change_in_range(self):
        # ratio 1.5% -> within 1%~2%, no change
        result = propose_beam_resize(0.015, 55, 80)
        assert result is None

    def test_at_min_dims_no_downsize(self):
        result = propose_beam_resize(0.005, 25, 40)
        assert result is None  # both at minimums

    def test_at_downsize_threshold(self):
        # ratio exactly 1% -> no downsize (not <)
        result = propose_beam_resize(0.01, 55, 80)
        assert result is None

    def test_at_upsize_threshold(self):
        # ratio exactly 2% -> no upsize (not >)
        result = propose_beam_resize(0.02, 55, 80)
        assert result is None


# ── enforce_column_constraints ────────────────────────────

class TestEnforceColumnConstraints:
    def _make_story_order(self):
        return ["B3F", "B2F", "B1F", "1F", "2F", "3F", "4F", "5F",
                "6F", "7F", "8F", "9F", "10F", "11F", "12F", "RF", "PRF"]

    def _make_strength_lookup(self):
        lookup = {}
        for s in ["B3F", "B2F", "B1F", "1F"]:
            lookup[(s, "column")] = 490
        for s in ["2F", "3F", "4F", "5F", "6F", "7F"]:
            lookup[(s, "column")] = 420
        for s in ["8F", "9F", "10F", "11F", "12F", "RF", "PRF"]:
            lookup[(s, "column")] = 350
        return lookup

    def test_monotonic_enforcement(self):
        """Lower floors must be >= upper floors."""
        positions = {
            (0.0, 0.0): [
                {"story": "2F", "w": 70, "d": 70, "fc": 420, "frame": "1"},
                {"story": "3F", "w": 80, "d": 80, "fc": 420, "frame": "2"},
                {"story": "4F", "w": 60, "d": 60, "fc": 420, "frame": "3"},
            ]
        }
        enforce_column_constraints(
            positions, self._make_strength_lookup(), self._make_story_order())
        cols = positions[(0.0, 0.0)]
        # sorted bottom-to-top: 2F, 3F, 4F
        # 2F must be >= 3F >= 4F
        assert cols[0]["w"] == 80  # 2F: max(70, 80) = 80
        assert cols[1]["w"] == 80  # 3F: stays 80
        assert cols[2]["w"] == 60  # 4F: stays 60

    def test_strength_boundary_equalization(self):
        """At fc change boundaries, sizes must be equal."""
        positions = {
            (0.0, 0.0): [
                {"story": "7F", "w": 70, "d": 70, "fc": 420, "frame": "1"},
                {"story": "8F", "w": 60, "d": 60, "fc": 350, "frame": "2"},
            ]
        }
        enforce_column_constraints(
            positions, self._make_strength_lookup(), self._make_story_order())
        cols = positions[(0.0, 0.0)]
        # Boundary between 420 and 350: equalize to max(70, 60) = 70
        assert cols[0]["w"] == 70
        assert cols[1]["w"] == 70

    def test_combined_boundary_and_monotonic(self):
        """Boundary equalization cascades into monotonic adjustment."""
        positions = {
            (0.0, 0.0): [
                {"story": "B2F", "w": 60, "d": 60, "fc": 490, "frame": "1"},
                {"story": "1F",  "w": 50, "d": 50, "fc": 490, "frame": "2"},
                {"story": "2F",  "w": 80, "d": 80, "fc": 420, "frame": "3"},
                {"story": "7F",  "w": 70, "d": 70, "fc": 420, "frame": "4"},
                {"story": "8F",  "w": 90, "d": 90, "fc": 350, "frame": "5"},
            ]
        }
        enforce_column_constraints(
            positions, self._make_strength_lookup(), self._make_story_order())
        cols = positions[(0.0, 0.0)]
        # After boundary 1F/2F: max(50,80)=80 -> 1F=80, 2F=80
        # After boundary 7F/8F: max(70,90)=90 -> 7F=90, 8F=90
        # Monotonic: B2F=max(60,80)=80, 1F=80, 2F=max(80,90)=90, 7F=90, 8F=90
        # Second pass boundary: 1F/2F: max(80,90)=90, 7F/8F: max(90,90)=90
        # Monotonic: B2F=max(80,90)=90, 1F=90
        # Result: all 90
        for col in cols:
            assert col["w"] == 90
            assert col["d"] == 90

    def test_already_valid(self):
        """No changes when already valid."""
        positions = {
            (0.0, 0.0): [
                {"story": "2F", "w": 90, "d": 90, "fc": 420, "frame": "1"},
                {"story": "3F", "w": 80, "d": 80, "fc": 420, "frame": "2"},
                {"story": "4F", "w": 70, "d": 70, "fc": 420, "frame": "3"},
            ]
        }
        enforce_column_constraints(
            positions, self._make_strength_lookup(), self._make_story_order())
        cols = positions[(0.0, 0.0)]
        assert cols[0]["w"] == 90
        assert cols[1]["w"] == 80
        assert cols[2]["w"] == 70

    def test_single_story(self):
        """Single-story column should be unchanged."""
        positions = {
            (5.0, 5.0): [
                {"story": "2F", "w": 80, "d": 80, "fc": 420, "frame": "1"},
            ]
        }
        enforce_column_constraints(
            positions, self._make_strength_lookup(), self._make_story_order())
        assert positions[(5.0, 5.0)][0]["w"] == 80


# ── make_section_name ─────────────────────────────────────

class TestMakeSectionName:
    def test_column(self):
        assert make_section_name("C", 90, 90, 420) == "C90X90C420"

    def test_beam(self):
        assert make_section_name("B", 55, 80, 350) == "B55X80C350"

    def test_small_beam(self):
        assert make_section_name("SB", 30, 50, 280) == "SB30X50C280"

    def test_wall_beam(self):
        assert make_section_name("WB", 50, 70, 350) == "WB50X70C350"


# ── is_rooftop_ordinary ──────────────────────────────────

class TestIsRooftopOrdinary:
    def test_prf(self):
        assert is_rooftop_ordinary("PRF") is True

    def test_r2f(self):
        assert is_rooftop_ordinary("R2F") is True

    def test_r3f(self):
        assert is_rooftop_ordinary("R3F") is True

    def test_r1f_not_ordinary(self):
        assert is_rooftop_ordinary("R1F") is False

    def test_rf_not_ordinary(self):
        assert is_rooftop_ordinary("RF") is False

    def test_regular_floor(self):
        assert is_rooftop_ordinary("5F") is False

    def test_basement(self):
        assert is_rooftop_ordinary("B2F") is False
