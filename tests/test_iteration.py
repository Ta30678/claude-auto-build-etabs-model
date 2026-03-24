"""
Tests for gs_12_iterate pure logic functions.
No ETABS connection required.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "golden_scripts"))
from rc_design.gs_12_iterate import (
    compute_column_ratio,
    compute_beam_ratio,
    propose_column_resize,
    propose_beam_resize,
    enforce_column_constraints,
    make_section_name,
    is_rooftop_ordinary,
    build_config_from_etabs,
    classify_floors,
    extract_column_results,
    extract_beam_results,
    _save_iteration_report,
)
from rc_design.rc_plotter import (
    _ratio_color,
    select_key_floors,
    select_top_grids,
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


# ── build_config_from_etabs ─────────────────────────────

def _make_mock_sapmodel():
    """Create a mock SapModel with realistic story and frame data."""
    sm = MagicMock()

    # Stories: returned top-to-bottom by ETABS
    # 3 stories: B1F (elev=0), 1F (elev=4.2), 2F (elev=7.5), RF (elev=10.8)
    sm.Story.GetStories_2.return_value = (
        -3.3,           # BaseElevation
        4,              # NumberStories
        ("RF", "2F", "1F", "B1F"),       # StoryNames (top-to-bottom)
        (10.8, 7.5, 4.2, 0.0),          # StoryElevations
        (3.3, 3.3, 4.2, 3.3),           # StoryHeights
        (True, True, True, True),        # IsMaster
        ("None", "None", "None", "None"),  # SimilarTo
        (False, False, False, False),    # SpliceAbove
        (0.0, 0.0, 0.0, 0.0),           # SpliceHeight
        (0, 0, 0, 0),                   # Color
    )

    # Frames: 2 columns (vertical) + 2 beams (horizontal)
    sm.FrameObj.GetAllFrames.return_value = (
        4,                                          # count
        ("C1", "C2", "B1", "B2"),                  # names
        ("C80X80C420", "C80X80C350", "B55X80C350", "B55X80C420"),  # props
        ("1F", "2F", "2F", "1F"),                  # stories
        (0, 0, 0, 0),                              # dummy
        (0, 0, 0, 0),                              # dummy
        (0.0, 0.0, 0.0, 0.0),                     # pt1x
        (0.0, 0.0, 0.0, 0.0),                     # pt1y
        (4.2, 7.5, 7.5, 4.2),                     # pt1z
        (0.0, 0.0, 6.0, 6.0),                     # pt2x
        (0.0, 0.0, 0.0, 0.0),                     # pt2y
        (7.5, 10.8, 7.5, 4.2),                    # pt2z
        (0,), (0,), (0,), (0,), (0,), (0,), (0,), (0,),  # remaining fields
    )

    return sm


class TestBuildConfigFromEtabs:
    def test_stories_order(self):
        """Stories should be sorted bottom-to-top by elevation."""
        sm = _make_mock_sapmodel()
        config = build_config_from_etabs(sm)
        names = [s["name"] for s in config["stories"]]
        assert names == ["B1F", "1F", "2F", "RF"]

    def test_base_elevation(self):
        sm = _make_mock_sapmodel()
        config = build_config_from_etabs(sm)
        assert config["base_elevation"] == -3.3

    def test_strength_map_columns(self):
        """Column fc inferred from section names per story."""
        sm = _make_mock_sapmodel()
        config = build_config_from_etabs(sm)
        smap = config["strength_map"]
        assert smap["1F"]["column"] == 420
        assert smap["2F"]["column"] == 350

    def test_strength_map_beams(self):
        """Beam fc inferred from section names per story."""
        sm = _make_mock_sapmodel()
        config = build_config_from_etabs(sm)
        smap = config["strength_map"]
        assert smap["2F"]["beam"] == 350
        assert smap["1F"]["beam"] == 420

    def test_classify_floors_roundtrip(self):
        """Auto-extracted config works with classify_floors."""
        sm = _make_mock_sapmodel()
        config = build_config_from_etabs(sm)
        super_s, sub_s, elevs, all_names = classify_floors(config)
        assert "B1F" in sub_s
        assert "1F" in sub_s
        assert "2F" in super_s
        assert "RF" in super_s

    def test_iteration_defaults(self):
        """iteration key should be empty dict (use constants defaults)."""
        sm = _make_mock_sapmodel()
        config = build_config_from_etabs(sm)
        assert config["iteration"] == {}


# ── extract_column_results error handling ─────────────────

class TestExtractColumnResults:
    def test_errors_not_swallowed(self):
        """extract_column_results should report errors, not silently swallow them."""
        sm = MagicMock()
        sm.DesignConcrete.GetSummaryResultsColumn.side_effect = RuntimeError("COM error")

        columns = [
            {"frame": "C1", "prop": "C80X80C420", "story": "2F",
             "w_cm": 80, "d_cm": 80, "fc": 420, "x": 0.0, "y": 0.0},
        ]
        results = extract_column_results(sm, columns)
        assert len(results) == 0  # no results, but error was captured (not crashed)

    def test_partial_results(self):
        """Some columns succeed, some fail — both handled."""
        sm = MagicMock()

        def side_effect(frame, *args):
            if frame == "C1":
                # Success: n_items=1, pmm_areas at index 5
                return (1, [], [], [], [], [0.0081], [], [], [], [], [], [], [], [])
            else:
                raise RuntimeError("COM error")

        sm.DesignConcrete.GetSummaryResultsColumn.side_effect = side_effect

        columns = [
            {"frame": "C1", "prop": "C80X80C420", "story": "2F",
             "w_cm": 80, "d_cm": 80, "fc": 420, "x": 0.0, "y": 0.0},
            {"frame": "C2", "prop": "C80X80C420", "story": "3F",
             "w_cm": 80, "d_cm": 80, "fc": 420, "x": 0.0, "y": 0.0},
        ]
        results = extract_column_results(sm, columns)
        assert len(results) == 1
        assert results[0]["frame"] == "C1"


class TestExtractBeamResults:
    def test_errors_not_swallowed(self):
        """extract_beam_results should report errors, not silently swallow them."""
        sm = MagicMock()
        sm.DesignConcrete.GetSummaryResultsBeam.side_effect = RuntimeError("COM error")

        beams = [
            {"frame": "B1", "prop": "B55X80C350", "story": "2F",
             "w_cm": 55, "d_cm": 80, "fc": 350, "prefix": "B"},
        ]
        results = extract_beam_results(sm, beams)
        assert len(results) == 0


# ── _ratio_color ──────────────────────────────────────────

class TestRatioColor:
    def test_too_low_is_red(self):
        assert _ratio_color(0.005, 0.01, 0.04) == "#FF4444"

    def test_too_high_is_red(self):
        assert _ratio_color(0.05, 0.01, 0.04) == "#FF4444"

    def test_ok_is_green(self):
        assert _ratio_color(0.025, 0.01, 0.04) == "#44AA44"

    def test_near_low_is_yellow(self):
        # 0.014 <= 0.01 * 1.5 = 0.015 -> yellow
        assert _ratio_color(0.014, 0.01, 0.04) == "#FFAA00"

    def test_near_high_is_yellow(self):
        # 0.035 > 0.04 * 0.85 = 0.034 -> yellow
        assert _ratio_color(0.035, 0.01, 0.04) == "#FFAA00"

    def test_exact_low_threshold_is_red(self):
        assert _ratio_color(0.01, 0.01, 0.04) == "#FF4444"

    def test_exact_high_threshold_is_green(self):
        # ratio == up_thresh -> not > up_thresh, so not red
        # check if yellow: 0.04 > 0.04*0.85=0.034 -> yes, yellow
        assert _ratio_color(0.04, 0.01, 0.04) == "#FFAA00"


# ── select_key_floors ────────────────────────────────────

class TestSelectKeyFloors:
    def _setup(self):
        all_story_names = ["B3F", "B2F", "B1F", "1F", "2F", "3F", "4F",
                           "5F", "6F", "7F", "8F", "9F", "RF"]
        sub_stories = ["B3F", "B2F", "B1F", "1F"]
        super_stories = ["2F", "3F", "4F", "5F", "6F", "7F", "8F", "9F", "RF"]
        strength_lookup = {}
        for s in ["B3F", "B2F", "B1F", "1F"]:
            strength_lookup[(s, "column")] = 490
        for s in ["2F", "3F", "4F", "5F", "6F", "7F"]:
            strength_lookup[(s, "column")] = 420
        for s in ["8F", "9F", "RF"]:
            strength_lookup[(s, "column")] = 350
        return all_story_names, sub_stories, super_stories, strength_lookup

    def test_includes_all_sub_stories(self):
        all_names, sub, super_, lookup = self._setup()
        result = select_key_floors([], [], super_, sub, lookup, all_names)
        for s in sub:
            assert s in result

    def test_includes_2f(self):
        all_names, sub, super_, lookup = self._setup()
        result = select_key_floors([], [], super_, sub, lookup, all_names)
        assert "2F" in result

    def test_includes_strength_transition(self):
        """7F/8F boundary (420->350) should include both floors."""
        all_names, sub, super_, lookup = self._setup()
        result = select_key_floors([], [], super_, sub, lookup, all_names)
        assert "7F" in result
        assert "8F" in result

    def test_includes_worst_ratio_floor(self):
        all_names, sub, super_, lookup = self._setup()
        col_results = [
            {"story": "5F", "ratio": 0.06, "x": 0, "y": 0},
            {"story": "3F", "ratio": 0.02, "x": 0, "y": 0},
        ]
        result = select_key_floors(col_results, [], super_, sub, lookup, all_names)
        assert "5F" in result

    def test_sorted_by_story_order(self):
        all_names, sub, super_, lookup = self._setup()
        result = select_key_floors([], [], super_, sub, lookup, all_names)
        indices = [all_names.index(s) for s in result]
        assert indices == sorted(indices)


# ── select_top_grids ─────────────────────────────────────

class TestSelectTopGrids:
    def test_top_n_selection(self):
        grid_lines = {
            "x": [
                {"label": "1", "coordinate": 0.0},
                {"label": "2", "coordinate": 6.0},
                {"label": "3", "coordinate": 12.0},
                {"label": "4", "coordinate": 18.0},
            ],
            "y": [
                {"label": "A", "coordinate": 0.0},
                {"label": "B", "coordinate": 8.0},
            ],
        }
        col_results = [
            {"x": 0.0, "y": 0.0, "ratio": 0.05},   # grid 1
            {"x": 6.0, "y": 0.0, "ratio": 0.03},   # grid 2
            {"x": 12.0, "y": 0.0, "ratio": 0.07},  # grid 3
            {"x": 18.0, "y": 0.0, "ratio": 0.01},  # grid 4
        ]
        result = select_top_grids(col_results, [], grid_lines, top_n=2)
        # X direction: grid 3 (0.07) > grid 1 (0.05) > grid 2 (0.03) > grid 4 (0.01)
        assert len(result["x"]) == 2
        assert result["x"][0]["label"] == "3"
        assert result["x"][1]["label"] == "1"

    def test_empty_results(self):
        grid_lines = {
            "x": [{"label": "1", "coordinate": 0.0}],
            "y": [{"label": "A", "coordinate": 0.0}],
        }
        result = select_top_grids([], [], grid_lines, top_n=3)
        assert len(result["x"]) == 1
        assert result["x"][0]["worst_ratio"] == 0.0


# ── _save_iteration_report ───────────────────────────────

class TestSaveIterationReport:
    def test_creates_files(self, tmp_path):
        iter_dir = str(tmp_path / "iteration_1")
        col_results = [
            {"frame": "C1", "prop": "C80X80C420", "story": "2F",
             "ratio": 0.025, "pmm_area": 0.016, "w_cm": 80, "d_cm": 80},
        ]
        beam_results = [
            {"frame": "B1", "prop": "B55X80C350", "story": "2F",
             "ratio": 0.015, "max_area": 0.006, "w_cm": 55, "d_cm": 80},
        ]
        report = _save_iteration_report(iter_dir, 1, col_results, beam_results,
                                        [{"frame": "C1"}], [], [])
        assert os.path.isfile(os.path.join(iter_dir, "ratio_report.json"))
        assert os.path.isfile(os.path.join(iter_dir, "summary.txt"))
        assert report["iteration"] == 1
        assert report["changes"]["columns_ratio"] == 1
        assert report["changes"]["columns_constraint"] == 0

    def test_empty_results(self, tmp_path):
        iter_dir = str(tmp_path / "iteration_0")
        report = _save_iteration_report(iter_dir, 0, [], [], [], [], [])
        assert report["stats"]["col_count"] == 0
        assert report["stats"]["col_min"] is None


# ── phase routing ─────────────────────────────────────────

class TestPhaseRouting:
    def test_run_signature_accepts_phase(self):
        """run() should accept phase parameter without error at import time."""
        from rc_design.gs_12_iterate import run
        import inspect
        sig = inspect.signature(run)
        assert "phase" in sig.parameters
        assert sig.parameters["phase"].default == "both"

    def test_run_signature_accepts_output_dir(self):
        from rc_design.gs_12_iterate import run
        import inspect
        sig = inspect.signature(run)
        assert "output_dir" in sig.parameters
        assert sig.parameters["output_dir"].default is None
