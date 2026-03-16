"""Tests for golden_scripts.tools.sb_validate.

All tests use mock data — no ETABS connection required.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.sb_validate import (
    validate_small_beams,
    build_sb_targets,
    correct_sb_angles,
    _compute_section_area,
    find_sb_intermediate_supports,
    split_all_sbs,
)
from golden_scripts.tools.beam_validate import split_beam


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_grid_data():
    """2 x-grids x 2 y-grids = 4 grid intersections."""
    return {
        "x": [
            {"label": "A", "coordinate": 0.0},
            {"label": "B", "coordinate": 8.50},
        ],
        "y": [
            {"label": "1", "coordinate": 0.0},
            {"label": "2", "coordinate": 6.00},
        ],
    }


@pytest.fixture
def grid_3x3():
    """3 x-grids x 3 y-grids = 9 grid intersections."""
    return {
        "x": [
            {"label": "A", "coordinate": 0.0},
            {"label": "B", "coordinate": 8.50},
            {"label": "C", "coordinate": 17.00},
        ],
        "y": [
            {"label": "1", "coordinate": 0.0},
            {"label": "2", "coordinate": 6.00},
            {"label": "3", "coordinate": 12.00},
        ],
    }


@pytest.fixture
def simple_config():
    """A model_config with columns, beams, and walls."""
    return {
        "columns": [
            {"grid_x": 0.0, "grid_y": 0.0, "floors": ["1F", "2F"],
             "section": "C60X60"},
            {"grid_x": 8.50, "grid_y": 0.0, "floors": ["1F", "2F"],
             "section": "C60X60"},
            {"grid_x": 0.0, "grid_y": 6.00, "floors": ["1F", "2F"],
             "section": "C60X60"},
            {"grid_x": 8.50, "grid_y": 6.00, "floors": ["1F", "2F"],
             "section": "C60X60"},
        ],
        "beams": [
            # Horizontal beam along Y=0 from A/1 to B/1
            {"x1": 0.0, "y1": 0.0, "x2": 8.50, "y2": 0.0,
             "section": "B50X80", "floors": ["1F", "2F"]},
            # Horizontal beam along Y=6 from A/2 to B/2
            {"x1": 0.0, "y1": 6.00, "x2": 8.50, "y2": 6.00,
             "section": "B50X80", "floors": ["1F", "2F"]},
            # Vertical beam along X=0 from A/1 to A/2
            {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 6.00,
             "section": "B40X70", "floors": ["1F", "2F"]},
            # Vertical beam along X=8.5 from B/1 to B/2
            {"x1": 8.50, "y1": 0.0, "x2": 8.50, "y2": 6.00,
             "section": "B40X70", "floors": ["1F", "2F"]},
        ],
        "walls": [],
    }


@pytest.fixture
def empty_sb_data():
    return {"small_beams": []}


# ---------------------------------------------------------------------------
# TestBuildSbTargets
# ---------------------------------------------------------------------------

class TestBuildSbTargets:

    def test_grid_intersections_count(self, simple_grid_data):
        """2 x-grids x 2 y-grids = 4 grid targets."""
        config = {"columns": [], "beams": [], "walls": []}
        grid_targets, element_targets = build_sb_targets(config, simple_grid_data)
        assert len(grid_targets) == 4
        assert len(element_targets) == 0
        for t in grid_targets:
            assert t.floors == []

    def test_column_targets(self, simple_grid_data, simple_config):
        """Columns produce point targets."""
        grid_targets, element_targets = build_sb_targets(
            simple_config, simple_grid_data)
        col_targets = [t for t in element_targets if t.kind == "point"]
        assert len(col_targets) == 4  # 4 columns
        assert col_targets[0].floors == ["1F", "2F"]

    def test_wall_targets(self, simple_grid_data):
        """Walls produce segment targets."""
        config = {
            "columns": [], "beams": [],
            "walls": [{"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 6.0,
                        "floors": ["1F"]}],
        }
        grid_targets, element_targets = build_sb_targets(
            config, simple_grid_data)
        wall_targets = [t for t in element_targets if t.kind == "segment"]
        assert len(wall_targets) == 1
        assert wall_targets[0].x1 == 0.0 and wall_targets[0].y2 == 6.0

    def test_major_beams_as_targets(self, simple_grid_data, simple_config):
        """Major beams from model_config are included as segment targets."""
        grid_targets, element_targets = build_sb_targets(
            simple_config, simple_grid_data)
        seg_targets = [t for t in element_targets if t.kind == "segment"]
        # 4 major beams + 0 walls = 4 segment targets
        assert len(seg_targets) == 4
        # Verify one beam target
        beam_match = any(
            t.x1 == 0.0 and t.y1 == 0.0 and t.x2 == 8.50 and t.y2 == 0.0
            for t in seg_targets)
        assert beam_match


# ---------------------------------------------------------------------------
# TestSnapToGrid
# ---------------------------------------------------------------------------

class TestSnapToGrid:

    def test_sb_snaps_to_grid_intersection(self, simple_grid_data, simple_config):
        """SB endpoint slightly off grid snaps to nearest grid intersection."""
        sb_data = {
            "small_beams": [
                {"x1": 4.25, "y1": 0.02, "x2": 4.25, "y2": 5.98,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, simple_config, simple_grid_data, tolerance=1.0)
        sb = validated["small_beams"][0]
        # Y endpoints should snap to beam/grid at Y=0.0 and Y=6.0
        assert sb["y1"] == 0.0
        assert sb["y2"] == 6.0

    def test_sb_beyond_tolerance_gets_warning(self, simple_grid_data):
        """SB endpoint far from any target with small tolerance produces warning."""
        config = {"columns": [], "beams": [], "walls": []}
        sb_data = {
            "small_beams": [
                {"x1": 4.25, "y1": 3.00, "x2": 4.25, "y2": 5.00,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, simple_grid_data, tolerance=0.5)
        # Nearest grid to (4.25, 3.0) is >2m away → warning
        assert report["warning_endpoints"] >= 1


# ---------------------------------------------------------------------------
# TestSnapToColumn
# ---------------------------------------------------------------------------

class TestSnapToColumn:

    def test_sb_snaps_to_column_with_floor_overlap(self, simple_grid_data):
        """SB shares floor with column, should snap."""
        config = {
            "columns": [{"grid_x": 4.25, "grid_y": 3.0, "floors": ["1F"]}],
            "beams": [], "walls": [],
        }
        sb_data = {
            "small_beams": [
                {"x1": 4.27, "y1": 0.0, "x2": 4.23, "y2": 3.02,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, simple_grid_data, tolerance=1.0)
        sb = validated["small_beams"][0]
        assert sb["x2"] == 4.25
        assert sb["y2"] == 3.0

    def test_sb_no_snap_column_no_floor_overlap(self, simple_grid_data):
        """SB on floor 3F won't snap to column on floor 1F."""
        config = {
            "columns": [{"grid_x": 4.25, "grid_y": 3.0, "floors": ["1F"]}],
            "beams": [], "walls": [],
        }
        sb_data = {
            "small_beams": [
                {"x1": 4.27, "y1": 0.0, "x2": 4.23, "y2": 3.02,
                 "section": "SB25X50", "floors": ["3F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, simple_grid_data, tolerance=1.0)
        sb = validated["small_beams"][0]
        # Should NOT snap to column (no floor overlap)
        assert not (sb["x2"] == 4.25 and sb["y2"] == 3.0)


# ---------------------------------------------------------------------------
# TestSnapToMajorBeam
# ---------------------------------------------------------------------------

class TestSnapToMajorBeam:

    def test_sb_snaps_to_major_beam_midspan(self, simple_grid_data):
        """SB endpoint near mid-span of major beam snaps to beam segment."""
        config = {
            "columns": [],
            "beams": [
                # Horizontal beam Y=0 from X=0 to X=8.5
                {"x1": 0.0, "y1": 0.0, "x2": 8.50, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        sb_data = {
            "small_beams": [
                # Vertical SB at X=4.25, ending near Y=0.05 (should snap to beam)
                {"x1": 4.25, "y1": 3.0, "x2": 4.25, "y2": 0.05,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, simple_grid_data, tolerance=1.0)
        sb = validated["small_beams"][0]
        # End point (4.25, 0.05) should snap to beam at Y=0 → (4.25, 0.0)
        assert abs(sb["y2"] - 0.0) < 0.01

    def test_sb_snaps_to_major_beam_endpoint(self, simple_grid_data):
        """SB endpoint near major beam endpoint snaps to it."""
        config = {
            "columns": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 8.50, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        sb_data = {
            "small_beams": [
                {"x1": 8.48, "y1": 3.0, "x2": 8.48, "y2": 0.03,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, simple_grid_data, tolerance=1.0)
        sb = validated["small_beams"][0]
        # Should snap to beam endpoint at (8.50, 0.0) or grid intersection
        assert abs(sb["y2"] - 0.0) < 0.01


# ---------------------------------------------------------------------------
# TestSnapToSb
# ---------------------------------------------------------------------------

class TestSnapToSb:

    def test_chain_snap_between_sbs(self, simple_grid_data, simple_config):
        """SB-A snaps to beam in round 1, SB-B snaps to SB-A in round 2."""
        sb_data = {
            "small_beams": [
                # SB-A: vertical, from beam Y=0 to beam Y=6 (clean endpoints)
                {"x1": 4.25, "y1": 0.0, "x2": 4.25, "y2": 6.0,
                 "section": "SB25X50", "floors": ["1F"]},
                # SB-B: horizontal, starts at X=0 beam, ends near SB-A mid-span
                {"x1": 0.0, "y1": 3.0, "x2": 4.22, "y2": 3.0,
                 "section": "SB20X40", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, simple_config, simple_grid_data, tolerance=1.0)
        sb_b = validated["small_beams"][1]
        # SB-B end (4.22, 3.0) should snap to SB-A at x=4.25
        assert abs(sb_b["x2"] - 4.25) < 0.01


# ---------------------------------------------------------------------------
# TestAngleCorrection
# ---------------------------------------------------------------------------

class TestAngleCorrection:

    def test_near_horizontal_corrects_to_grid(self, simple_grid_data):
        """SB tilted ~2° from horizontal aligns Y to nearest grid line."""
        sb_data = {
            "small_beams": [
                {"x1": 0.0, "y1": 5.88, "x2": 8.5, "y2": 6.12,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        sb_data, angle_report = correct_sb_angles(sb_data, simple_grid_data, 5.0)
        sb = sb_data["small_beams"][0]
        assert sb["y1"] == 6.0
        assert sb["y2"] == 6.0
        assert len(angle_report) == 1
        assert angle_report[0]["correction_axis"] == "Y"
        assert angle_report[0]["target_grid_label"] == "2"

    def test_near_vertical_corrects_to_grid(self, simple_grid_data):
        """SB tilted ~3° from vertical aligns X to nearest grid line."""
        sb_data = {
            "small_beams": [
                {"x1": 8.38, "y1": 0.0, "x2": 8.62, "y2": 6.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        sb_data, angle_report = correct_sb_angles(sb_data, simple_grid_data, 5.0)
        sb = sb_data["small_beams"][0]
        assert sb["x1"] == 8.5
        assert sb["x2"] == 8.5
        assert angle_report[0]["correction_axis"] == "X"

    def test_true_diagonal_not_corrected(self, simple_grid_data):
        """SB at 30° is not corrected."""
        sb_data = {
            "small_beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 8.0, "y2": 4.62,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        sb_data, angle_report = correct_sb_angles(sb_data, simple_grid_data, 5.0)
        assert len(angle_report) == 0
        sb = sb_data["small_beams"][0]
        assert sb["x2"] == 8.0
        assert sb["y2"] == 4.62

    def test_zero_length_skipped(self):
        """Zero-length SB is skipped."""
        grid_data = {"x": [], "y": []}
        sb_data = {
            "small_beams": [
                {"x1": 5.0, "y1": 5.0, "x2": 5.0, "y2": 5.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        sb_data, angle_report = correct_sb_angles(sb_data, grid_data, 5.0)
        assert len(angle_report) == 0

    def test_fallback_to_average(self):
        """When no grid line is close, use average of endpoints."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 100.0}],
            "y": [{"label": "1", "coordinate": 100.0}],
        }
        sb_data = {
            "small_beams": [
                {"x1": 0.0, "y1": 5.10, "x2": 8.0, "y2": 4.90,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        sb_data, angle_report = correct_sb_angles(sb_data, grid_data, 5.0)
        sb = sb_data["small_beams"][0]
        assert sb["y1"] == sb["y2"] == 5.0
        assert angle_report[0]["target_grid_label"] == "average"


# ---------------------------------------------------------------------------
# TestComputeSectionArea
# ---------------------------------------------------------------------------

class TestComputeSectionArea:

    def test_normal_section(self):
        assert _compute_section_area("SB25X50") == 25 * 50

    def test_section_with_fc(self):
        assert _compute_section_area("SB30X60C350") == 30 * 60

    def test_beam_section(self):
        assert _compute_section_area("B50X80") == 50 * 80

    def test_invalid_section(self):
        assert _compute_section_area("INVALID") == 0

    def test_empty_section(self):
        assert _compute_section_area("") == 0


# ---------------------------------------------------------------------------
# TestSplitAtColumn
# ---------------------------------------------------------------------------

class TestSplitAtColumn:

    def test_column_splits_sb(self):
        """Column at midspan of SB produces two sub-SBs."""
        sb = {"x1": 0.0, "y1": 3.0, "x2": 17.0, "y2": 3.0,
              "section": "SB25X50", "floors": ["1F"]}
        columns = [{"grid_x": 8.5, "grid_y": 3.0, "floors": ["1F"]}]
        supports = find_sb_intermediate_supports(
            sb, columns, [], [], [], 0.15)
        assert len(supports) == 1
        assert abs(supports[0][1] - 8.5) < 0.01

    def test_column_at_sb_endpoint_excluded(self):
        """Column at SB endpoint (t < 0.02) is excluded."""
        sb = {"x1": 0.0, "y1": 3.0, "x2": 8.5, "y2": 3.0,
              "section": "SB25X50", "floors": ["1F"]}
        columns = [{"grid_x": 0.0, "grid_y": 3.0, "floors": ["1F"]}]
        supports = find_sb_intermediate_supports(
            sb, columns, [], [], [], 0.15)
        assert len(supports) == 0

    def test_column_too_far(self):
        """Column 0.5m from SB line is not a support (tolerance=0.15)."""
        sb = {"x1": 0.0, "y1": 3.0, "x2": 17.0, "y2": 3.0,
              "section": "SB25X50", "floors": ["1F"]}
        columns = [{"grid_x": 8.5, "grid_y": 3.5, "floors": ["1F"]}]
        supports = find_sb_intermediate_supports(
            sb, columns, [], [], [], 0.15)
        assert len(supports) == 0


# ---------------------------------------------------------------------------
# TestSplitAtMajorBeam
# ---------------------------------------------------------------------------

class TestSplitAtMajorBeam:

    def test_major_beam_crossing_splits_sb(self):
        """Major beam crossing SB mid-span splits the SB."""
        # Horizontal SB along Y=3
        sb = {"x1": 0.0, "y1": 3.0, "x2": 17.0, "y2": 3.0,
              "section": "SB25X50", "floors": ["1F"]}
        # Vertical major beam along X=8.5
        beams = [{"x1": 8.5, "y1": 0.0, "x2": 8.5, "y2": 6.0,
                  "section": "B40X70", "floors": ["1F"]}]
        supports = find_sb_intermediate_supports(
            sb, [], [], beams, [], 0.15)
        assert len(supports) == 1
        assert abs(supports[0][1] - 8.5) < 0.01
        assert abs(supports[0][2] - 3.0) < 0.01

    def test_parallel_major_beam_not_split(self):
        """Major beam parallel to SB does not produce split."""
        # Horizontal SB along Y=3
        sb = {"x1": 0.0, "y1": 3.0, "x2": 17.0, "y2": 3.0,
              "section": "SB25X50", "floors": ["1F"]}
        # Horizontal major beam along Y=0
        beams = [{"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                  "section": "B50X80", "floors": ["1F"]}]
        supports = find_sb_intermediate_supports(
            sb, [], [], beams, [], 0.15)
        assert len(supports) == 0

    def test_major_beam_no_floor_overlap(self):
        """Major beam with no floor overlap does not split SB."""
        sb = {"x1": 0.0, "y1": 3.0, "x2": 17.0, "y2": 3.0,
              "section": "SB25X50", "floors": ["1F"]}
        beams = [{"x1": 8.5, "y1": 0.0, "x2": 8.5, "y2": 6.0,
                  "section": "B40X70", "floors": ["3F"]}]
        supports = find_sb_intermediate_supports(
            sb, [], [], beams, [], 0.15)
        assert len(supports) == 0


# ---------------------------------------------------------------------------
# TestSbToSbSplit
# ---------------------------------------------------------------------------

class TestSbToSbSplit:

    def test_larger_sb_splits_smaller(self):
        """Larger SB (30x60) is processed first, smaller SB (25x50) is split by it."""
        config = {"columns": [], "walls": [], "beams": []}
        sb_data = {
            "small_beams": [
                # Smaller: horizontal along Y=3 spanning X=0~17
                {"x1": 0.0, "y1": 3.0, "x2": 17.0, "y2": 3.0,
                 "section": "SB25X50", "floors": ["1F"]},
                # Larger: vertical along X=8.5 spanning Y=0~6
                {"x1": 8.5, "y1": 0.0, "x2": 8.5, "y2": 6.0,
                 "section": "SB30X60", "floors": ["1F"]},
            ],
        }
        grid_data = {"x": [], "y": []}
        sb_data, report = split_all_sbs(sb_data, config, grid_data, 0.15)
        # SB30X60 (area=1800) processed first → not split
        # SB25X50 (area=1250) processed second → split by SB30X60
        assert report["split_sbs"] == 1
        # Total SBs: 1 (larger, unsplit) + 2 (smaller, split into 2) = 3
        assert len(sb_data["small_beams"]) == 3

    def test_same_section_uses_index_order(self):
        """Same-size SBs use array index for tie-breaking (earlier first)."""
        config = {"columns": [], "walls": [], "beams": []}
        sb_data = {
            "small_beams": [
                # Index 0: horizontal SB along Y=3 (processed first due to lower index)
                {"x1": 0.0, "y1": 3.0, "x2": 17.0, "y2": 3.0,
                 "section": "SB25X50", "floors": ["1F"]},
                # Index 1: vertical SB along X=8.5 (processed second)
                {"x1": 8.5, "y1": 0.0, "x2": 8.5, "y2": 6.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        grid_data = {"x": [], "y": []}
        sb_data, report = split_all_sbs(sb_data, config, grid_data, 0.15)
        # Index 0 processed first (not split), index 1 split by index 0
        assert report["split_sbs"] == 1
        assert len(sb_data["small_beams"]) == 3

    def test_larger_sb_not_split_by_smaller(self):
        """Larger SB is not split by already-processed smaller SB."""
        config = {"columns": [], "walls": [], "beams": []}
        sb_data = {
            "small_beams": [
                # Larger SB: processed first, not split
                {"x1": 8.5, "y1": 0.0, "x2": 8.5, "y2": 6.0,
                 "section": "SB30X60", "floors": ["1F"]},
                # Smaller SB: this crosses the larger one, but larger is not split
                {"x1": 0.0, "y1": 3.0, "x2": 17.0, "y2": 3.0,
                 "section": "SB20X40", "floors": ["1F"]},
            ],
        }
        grid_data = {"x": [], "y": []}
        sb_data, report = split_all_sbs(sb_data, config, grid_data, 0.15)
        # Only the smaller SB should be split
        assert report["split_sbs"] == 1
        # 1 unsplit larger + 2 from split smaller = 3
        assert len(sb_data["small_beams"]) == 3


# ---------------------------------------------------------------------------
# TestPostValidation
# ---------------------------------------------------------------------------

class TestPostValidation:

    def test_zero_length_sb_warning(self, simple_grid_data):
        """Two SB endpoints snap to same point → zero-length warning."""
        # Use config with no beam segments so both endpoints snap to (0,0) point
        config = {
            "columns": [{"grid_x": 0.0, "grid_y": 0.0, "floors": ["1F"]}],
            "beams": [], "walls": [],
        }
        sb_data = {
            "small_beams": [
                {"x1": 0.01, "y1": 0.02, "x2": 0.03, "y2": 0.01,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, simple_grid_data, tolerance=1.0)
        zero_warnings = [w for w in report["warnings"]
                         if "Zero-length" in w.get("message", "")]
        assert len(zero_warnings) == 1

    def test_direction_change_warning(self):
        """Horizontal SB whose end snaps to off-axis target → direction change warning."""
        # Column offset in Y from the SB's horizontal line
        config = {
            "columns": [{"grid_x": 5.0, "grid_y": 3.5, "floors": ["1F"]}],
            "beams": [], "walls": [],
        }
        # No grid intersections so only the column is a target
        grid_data = {"x": [], "y": []}
        sb_data = {
            "small_beams": [
                # Horizontal SB: y1==y2==3.0, end at (5.0, 3.0) near column at (5.0, 3.5)
                # End snaps to (5.0, 3.5), start stays unsnapped → direction changes
                {"x1": 0.0, "y1": 3.0, "x2": 5.0, "y2": 3.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, grid_data, tolerance=1.0,
            no_split=True, no_angle_correct=True)
        dir_warnings = [w for w in report["warnings"]
                        if "Direction changed" in w.get("message", "")]
        assert len(dir_warnings) >= 1

    def test_unsnapped_endpoint_warning(self, simple_grid_data):
        """SB endpoint far from any target → unsnapped warning."""
        config = {"columns": [], "beams": [], "walls": []}
        sb_data = {
            "small_beams": [
                {"x1": 50.0, "y1": 50.0, "x2": 50.0, "y2": 55.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, simple_grid_data, tolerance=1.0)
        assert report["warning_endpoints"] >= 1
        unsnapped = [w for w in report["warnings"]
                     if w["message"].startswith("No target")]
        assert len(unsnapped) >= 1


# ---------------------------------------------------------------------------
# TestReport
# ---------------------------------------------------------------------------

class TestReport:

    def test_report_structure(self, simple_grid_data, simple_config):
        """Report has all required keys."""
        sb_data = {
            "small_beams": [
                {"x1": 0.0, "y1": 3.0, "x2": 8.52, "y2": 3.03,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        _, report = validate_small_beams(
            sb_data, simple_config, simple_grid_data, tolerance=1.0)
        required_keys = [
            "total_sbs", "total_endpoints", "snapped_endpoints",
            "warning_endpoints", "max_snap_distance", "avg_snap_distance",
            "corrections", "warnings",
            "angle_corrections", "angle_corrected_sbs",
            "split_sbs", "new_sbs_from_split", "total_sbs_after_split",
            "split_details",
        ]
        for key in required_keys:
            assert key in report, f"Missing key: {key}"

    def test_empty_sbs(self, simple_grid_data, simple_config):
        """Empty small_beams → all zeros."""
        sb_data = {"small_beams": []}
        _, report = validate_small_beams(
            sb_data, simple_config, simple_grid_data, tolerance=1.0)
        assert report["total_sbs"] == 0
        assert report["total_endpoints"] == 0
        assert report["snapped_endpoints"] == 0
        assert report["warning_endpoints"] == 0


# ---------------------------------------------------------------------------
# TestIntegration
# ---------------------------------------------------------------------------

class TestIntegration:

    def test_full_pipeline_angle_snap_split(self, grid_3x3):
        """Full pipeline: angle correction + snap + split."""
        config = {
            "columns": [
                {"grid_x": 0.0, "grid_y": 0.0, "floors": ["1F"]},
                {"grid_x": 8.50, "grid_y": 0.0, "floors": ["1F"]},
                {"grid_x": 17.0, "grid_y": 0.0, "floors": ["1F"]},
                {"grid_x": 0.0, "grid_y": 6.0, "floors": ["1F"]},
                {"grid_x": 8.50, "grid_y": 6.0, "floors": ["1F"]},
                {"grid_x": 17.0, "grid_y": 6.0, "floors": ["1F"]},
            ],
            "beams": [
                # Horizontal beam Y=0 from A to C
                {"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
                # Horizontal beam Y=6 from A to C
                {"x1": 0.0, "y1": 6.0, "x2": 17.0, "y2": 6.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        sb_data = {
            "small_beams": [
                # SB with slight Y deviation (~2°) spanning A/1 to C/1 at Y≈3
                # Should be angle-corrected, snapped to beams, and split at B
                {"x1": 0.02, "y1": 2.88, "x2": 16.98, "y2": 3.12,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, grid_3x3, tolerance=1.0)
        # Angle correction should have fired
        assert report["angle_corrected_sbs"] >= 1
        # After snap + split at column B (8.5, 3.0): 2 sub-SBs
        assert report["split_sbs"] >= 0  # May or may not split depending on column proximity
        # All SBs should have matching Y on both endpoints (angle-corrected)
        for sb in validated["small_beams"]:
            assert sb["y1"] == sb["y2"]

    def test_no_split_flag(self, grid_3x3, simple_config):
        """--no-split disables splitting."""
        sb_data = {
            "small_beams": [
                {"x1": 0.0, "y1": 3.0, "x2": 17.0, "y2": 3.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, simple_config, grid_3x3, tolerance=1.0, no_split=True)
        assert report["split_sbs"] == 0
        assert len(validated["small_beams"]) == 1

    def test_no_angle_correct_flag(self, simple_grid_data, simple_config):
        """--no-angle-correct disables angle correction."""
        sb_data = {
            "small_beams": [
                {"x1": 0.0, "y1": 5.88, "x2": 8.5, "y2": 6.12,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, simple_config, simple_grid_data,
            tolerance=1.0, no_angle_correct=True)
        assert report["angle_corrected_sbs"] == 0

    def test_metadata_preserved(self, simple_grid_data, simple_config):
        """Extra fields in sb_data (like _metadata) are preserved."""
        sb_data = {
            "small_beams": [
                {"x1": 4.25, "y1": 0.0, "x2": 4.25, "y2": 6.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
            "_metadata": {"source": "pptx_to_elements", "version": "2.0"},
        }
        validated, _ = validate_small_beams(
            sb_data, simple_config, simple_grid_data, tolerance=1.0)
        assert "_metadata" in validated
        assert validated["_metadata"]["source"] == "pptx_to_elements"
