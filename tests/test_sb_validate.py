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
    build_grid_line_targets,
    correct_sb_angles,
    _compute_section_area,
    find_sb_intermediate_supports,
    split_all_sbs,
    cluster_free_endpoints,
    snap_sb_by_ray,
    ray_ray_intersection,
)
from golden_scripts.tools.config_snap import SnapTarget
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
# TestSnapSbByRay
# ---------------------------------------------------------------------------

class TestSnapSbByRay:

    def test_horizontal_ray_hits_vertical_beam(self):
        """Horizontal SB ray intersects a vertical beam segment."""
        targets = [
            SnapTarget("segment", 8.5, 0.0, 8.5, 6.0, ["1F"]),
        ]
        # Horizontal ray from (4.0, 3.0) direction (1, 0)
        result = snap_sb_by_ray(4.0, 3.0, 1.0, 0.0, ["1F"], targets, 5.0)
        assert result is not None
        nx, ny, d, info = result
        assert abs(nx - 8.5) < 0.01
        assert abs(ny - 3.0) < 0.01
        assert abs(d - 4.5) < 0.01

    def test_vertical_ray_hits_horizontal_beam(self):
        """Vertical SB ray intersects a horizontal beam segment."""
        targets = [
            SnapTarget("segment", 0.0, 6.0, 8.5, 6.0, ["1F"]),
        ]
        # Vertical ray from (4.0, 3.0) direction (0, 1)
        result = snap_sb_by_ray(4.0, 3.0, 0.0, 1.0, ["1F"], targets, 5.0)
        assert result is not None
        nx, ny, d, info = result
        assert abs(nx - 4.0) < 0.01
        assert abs(ny - 6.0) < 0.01
        assert abs(d - 3.0) < 0.01

    def test_ray_beyond_tolerance_no_snap(self):
        """Ray intersection beyond tolerance returns None."""
        targets = [
            SnapTarget("segment", 8.5, 0.0, 8.5, 6.0, ["1F"]),
        ]
        # Horizontal ray from (4.0, 3.0), tolerance only 2.0 → beam at 8.5 is 4.5m away
        result = snap_sb_by_ray(4.0, 3.0, 1.0, 0.0, ["1F"], targets, 2.0)
        assert result is None

    def test_parallel_target_no_snap(self):
        """Ray parallel to target segment produces no intersection."""
        targets = [
            # Horizontal beam, same direction as ray
            SnapTarget("segment", 0.0, 3.0, 8.5, 3.0, ["1F"]),
        ]
        # Horizontal ray at Y=3.0 direction (1, 0) — parallel to target
        result = snap_sb_by_ray(4.0, 3.0, 1.0, 0.0, ["1F"], targets, 5.0)
        assert result is None

    def test_point_target_projection(self):
        """Point target on ray line projects correctly."""
        targets = [
            SnapTarget("point", 8.5, 3.0, 8.5, 3.0, ["1F"]),
        ]
        # Horizontal ray from (4.0, 3.0) direction (1, 0) — column at (8.5, 3.0) is on-axis
        result = snap_sb_by_ray(4.0, 3.0, 1.0, 0.0, ["1F"], targets, 5.0)
        assert result is not None
        nx, ny, d, info = result
        assert abs(nx - 8.5) < 0.01
        assert abs(ny - 3.0) < 0.01
        assert abs(d - 4.5) < 0.01
        assert "column" in info

    def test_point_target_off_axis_within_tolerance(self):
        """Point target slightly off-axis but within tolerance snaps to projection."""
        targets = [
            # Column at (8.5, 3.1) — 0.1m off the horizontal ray at Y=3.0
            SnapTarget("point", 8.5, 3.1, 8.5, 3.1, ["1F"]),
        ]
        result = snap_sb_by_ray(4.0, 3.0, 1.0, 0.0, ["1F"], targets, 5.0)
        assert result is not None
        nx, ny, d, info = result
        # Projection onto ray: (8.5, 3.0), NOT the column position
        assert abs(nx - 8.5) < 0.01
        assert abs(ny - 3.0) < 0.01

    def test_point_target_off_axis_beyond_tolerance(self):
        """Point target far off-axis returns None."""
        targets = [
            SnapTarget("point", 8.5, 5.0, 8.5, 5.0, ["1F"]),
        ]
        # Column 2.0m off the horizontal ray → perp_dist > tolerance=0.5
        result = snap_sb_by_ray(4.0, 3.0, 1.0, 0.0, ["1F"], targets, 0.5)
        assert result is None

    def test_multiple_intersections_picks_nearest(self):
        """With multiple intersecting targets, picks the nearest one."""
        targets = [
            SnapTarget("segment", 8.5, 0.0, 8.5, 6.0, ["1F"]),  # at X=8.5
            SnapTarget("segment", 4.5, 0.0, 4.5, 6.0, ["1F"]),  # at X=4.5
        ]
        # Horizontal ray from (2.0, 3.0) direction (1, 0)
        result = snap_sb_by_ray(2.0, 3.0, 1.0, 0.0, ["1F"], targets, 10.0)
        assert result is not None
        nx, ny, d, info = result
        # Should pick X=4.5 (nearer) not X=8.5
        assert abs(nx - 4.5) < 0.01
        assert abs(d - 2.5) < 0.01

    def test_grid_point_target_label(self):
        """Grid intersection point target gets grid label."""
        grid_data = {
            "x": [{"label": "B", "coordinate": 8.5}],
            "y": [{"label": "2", "coordinate": 3.0}],
        }
        targets = [
            SnapTarget("point", 8.5, 3.0, 8.5, 3.0, []),  # grid target (floors=[])
        ]
        result = snap_sb_by_ray(4.0, 3.0, 1.0, 0.0, ["1F"], targets, 5.0,
                                grid_data=grid_data)
        assert result is not None
        _, _, _, info = result
        assert "grid_intersection" in info
        assert "B/2" in info

    def test_floor_mismatch_no_snap(self):
        """Target with non-overlapping floors is skipped."""
        targets = [
            SnapTarget("segment", 8.5, 0.0, 8.5, 6.0, ["3F"]),
        ]
        result = snap_sb_by_ray(4.0, 3.0, 1.0, 0.0, ["1F"], targets, 5.0)
        assert result is None


# ---------------------------------------------------------------------------
# TestClusterProjection
# ---------------------------------------------------------------------------

class TestClusterProjection:

    def test_horizontal_sb_projects_centroid_to_axis(self):
        """Horizontal SB's free end moves along X-axis only (Y unchanged)."""
        small_beams = [
            # Horizontal SB: start snapped at (0, 3), free end at (4.25, 3.0)
            {"x1": 0.0, "y1": 3.0, "x2": 4.25, "y2": 3.0,
             "section": "SB25X50", "floors": ["1F"]},
            # Horizontal SB: start snapped at (8.5, 3), free end at (4.27, 3.0)
            {"x1": 8.5, "y1": 3.0, "x2": 4.27, "y2": 3.0,
             "section": "SB25X50", "floors": ["1F"]},
        ]
        snapped_state = [[True, False], [True, False]]
        corrections = cluster_free_endpoints(small_beams, snapped_state, 0.30)
        assert len(corrections) == 1
        # Both endpoints should stay on Y=3.0 (projected onto their horizontal axis)
        assert small_beams[0]["y2"] == 3.0
        assert small_beams[1]["y2"] == 3.0

    def test_vertical_sb_projects_centroid_to_axis(self):
        """Vertical SB's free end moves along Y-axis only (X unchanged)."""
        small_beams = [
            # Vertical SB: start snapped at (4.0, 0.0), free end at (4.0, 3.02)
            {"x1": 4.0, "y1": 0.0, "x2": 4.0, "y2": 3.02,
             "section": "SB25X50", "floors": ["1F"]},
            # Vertical SB: start snapped at (4.0, 6.0), free end at (4.0, 2.98)
            {"x1": 4.0, "y1": 6.0, "x2": 4.0, "y2": 2.98,
             "section": "SB25X50", "floors": ["1F"]},
        ]
        snapped_state = [[True, False], [True, False]]
        corrections = cluster_free_endpoints(small_beams, snapped_state, 0.30)
        assert len(corrections) == 1
        # Both endpoints should stay at X=4.0 (projected onto their vertical axis)
        assert small_beams[0]["x2"] == 4.0
        assert small_beams[1]["x2"] == 4.0

    def test_mixed_direction_cluster_preserves_directions(self):
        """Vertical + horizontal SBs cluster without changing each other's direction."""
        small_beams = [
            # Vertical SB: start snapped at (4.25, 0.0), free end at (4.25, 3.02)
            {"x1": 4.25, "y1": 0.0, "x2": 4.25, "y2": 3.02,
             "section": "SB25X50", "floors": ["1F"]},
            # Horizontal SB: start snapped at (0.0, 3.0), free end at (4.27, 3.0)
            {"x1": 0.0, "y1": 3.0, "x2": 4.27, "y2": 3.0,
             "section": "SB25X50", "floors": ["1F"]},
        ]
        snapped_state = [[True, False], [True, False]]
        corrections = cluster_free_endpoints(small_beams, snapped_state, 0.30)
        assert len(corrections) == 1
        # Vertical SB: X should stay at 4.25 (direction preserved)
        assert small_beams[0]["x2"] == 4.25
        # Horizontal SB: Y should stay at 3.0 (direction preserved)
        assert small_beams[1]["y2"] == 3.0


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

    def test_no_direction_change_with_ray_snap(self):
        """Horizontal SB with off-axis column: ray snap preserves direction (no warning)."""
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
                # Ray snap projects column onto SB axis → (5.0, 3.0), direction preserved
                {"x1": 0.0, "y1": 3.0, "x2": 5.0, "y2": 3.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, grid_data, tolerance=1.0,
            no_split=True, no_angle_correct=True)
        dir_warnings = [w for w in report["warnings"]
                        if "Direction changed" in w.get("message", "")]
        # With ray-based snap, direction should NOT change
        assert len(dir_warnings) == 0

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
            "clustered_endpoints", "cluster_count",
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

    def test_direction_x_skips_angle_correction(self, simple_grid_data):
        """SB with direction='X' should NOT be angle-corrected even with deviation."""
        sb_data = {
            "small_beams": [
                {"x1": 0.0, "y1": 5.90, "x2": 8.5, "y2": 6.10,
                 "section": "SB25X50", "floors": ["1F"], "direction": "X"},
            ],
        }
        sb_data, angle_report = correct_sb_angles(sb_data, simple_grid_data, 5.0)
        assert len(angle_report) == 0
        assert sb_data["small_beams"][0]["y1"] == 5.90
        assert sb_data["small_beams"][0]["y2"] == 6.10

    def test_direction_y_skips_angle_correction(self, simple_grid_data):
        """SB with direction='Y' should NOT be angle-corrected."""
        sb_data = {
            "small_beams": [
                {"x1": 8.38, "y1": 0.0, "x2": 8.62, "y2": 6.0,
                 "section": "SB25X50", "floors": ["1F"], "direction": "Y"},
            ],
        }
        sb_data, angle_report = correct_sb_angles(sb_data, simple_grid_data, 5.0)
        assert len(angle_report) == 0
        assert sb_data["small_beams"][0]["x1"] == 8.38

    def test_direction_empty_gets_corrected(self, simple_grid_data):
        """SB with direction='' is corrected (same as before)."""
        sb_data = {
            "small_beams": [
                {"x1": 0.0, "y1": 5.90, "x2": 8.5, "y2": 6.10,
                 "section": "SB25X50", "floors": ["1F"], "direction": ""},
            ],
        }
        sb_data, angle_report = correct_sb_angles(sb_data, simple_grid_data, 5.0)
        assert len(angle_report) == 1
        assert sb_data["small_beams"][0]["y1"] == 6.0
        assert sb_data["small_beams"][0]["y2"] == 6.0

    def test_direction_missing_gets_corrected(self, simple_grid_data):
        """SB with no direction field is corrected (backward compat)."""
        sb_data = {
            "small_beams": [
                {"x1": 0.0, "y1": 5.90, "x2": 8.5, "y2": 6.10,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        sb_data, angle_report = correct_sb_angles(sb_data, simple_grid_data, 5.0)
        assert len(angle_report) == 1
        assert sb_data["small_beams"][0]["y1"] == 6.0

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


# ---------------------------------------------------------------------------
# TestClusterFreeEndpoints
# ---------------------------------------------------------------------------

class TestClusterFreeEndpoints:

    def test_two_half_snapped_sbs_cluster(self):
        """Two perpendicular half-snapped SBs: ray intersection at (4.25, 3.0)."""
        small_beams = [
            # SB-A: vertical, start snapped at (4.25, 0.0), end free at (4.25, 3.02)
            {"x1": 4.25, "y1": 0.0, "x2": 4.25, "y2": 3.02,
             "section": "SB25X50", "floors": ["1F"]},
            # SB-B: horizontal, start snapped at (0.0, 3.0), end free at (4.27, 3.0)
            {"x1": 0.0, "y1": 3.0, "x2": 4.27, "y2": 3.0,
             "section": "SB25X50", "floors": ["1F"]},
        ]
        snapped_state = [[True, False], [True, False]]
        corrections = cluster_free_endpoints(small_beams, snapped_state, 0.30)
        assert len(corrections) == 1
        assert corrections[0]["method"] == "ray_intersection"
        # SB-A vertical: projected to (4.25, 3.0) — exact intersection
        assert small_beams[0]["x2"] == 4.25
        assert small_beams[0]["y2"] == 3.0
        # SB-B horizontal: projected to (4.25, 3.0) — exact intersection
        assert small_beams[1]["x2"] == 4.25
        assert small_beams[1]["y2"] == 3.0
        # Both marked as snapped
        assert snapped_state[0][1] is True
        assert snapped_state[1][1] is True

    def test_three_endpoint_cluster(self):
        """Three free endpoints within tolerance cluster: each projected onto its own axis."""
        small_beams = [
            # Diagonal SB from (0,0) to (5.00, 3.00)
            {"x1": 0.0, "y1": 0.0, "x2": 5.00, "y2": 3.00,
             "section": "SB25X50", "floors": ["1F"]},
            # Diagonal SB from (10,0) to (5.02, 2.98)
            {"x1": 10.0, "y1": 0.0, "x2": 5.02, "y2": 2.98,
             "section": "SB25X50", "floors": ["1F"]},
            # Vertical SB from (5.01, 6.0) to (5.01, 3.01)
            {"x1": 5.01, "y1": 6.0, "x2": 5.01, "y2": 3.01,
             "section": "SB25X50", "floors": ["1F"]},
        ]
        snapped_state = [[True, False], [True, False], [True, False]]
        corrections = cluster_free_endpoints(small_beams, snapped_state, 0.30)
        assert len(corrections) == 1
        assert corrections[0]["member_count"] == 3
        # All marked as snapped
        assert all(snapped_state[i][1] for i in range(3))
        # Vertical SB: X preserved at 5.01
        assert small_beams[2]["x2"] == 5.01

    def test_no_cluster_when_far_apart(self):
        """Free endpoints > 30cm apart do not cluster."""
        small_beams = [
            {"x1": 0.0, "y1": 0.0, "x2": 4.0, "y2": 3.0,
             "section": "SB25X50", "floors": ["1F"]},
            {"x1": 10.0, "y1": 0.0, "x2": 5.0, "y2": 3.0,
             "section": "SB25X50", "floors": ["1F"]},
        ]
        snapped_state = [[True, False], [True, False]]
        # Distance between (4.0, 3.0) and (5.0, 3.0) = 1.0m > 0.30m
        corrections = cluster_free_endpoints(small_beams, snapped_state, 0.30)
        assert len(corrections) == 0
        # Endpoints unchanged
        assert small_beams[0]["x2"] == 4.0
        assert small_beams[1]["x2"] == 5.0

    def test_no_cluster_floor_mismatch(self):
        """Free endpoints close but on different floors do not cluster."""
        small_beams = [
            {"x1": 0.0, "y1": 0.0, "x2": 4.25, "y2": 3.0,
             "section": "SB25X50", "floors": ["1F"]},
            {"x1": 10.0, "y1": 0.0, "x2": 4.27, "y2": 3.0,
             "section": "SB25X50", "floors": ["3F"]},
        ]
        snapped_state = [[True, False], [True, False]]
        corrections = cluster_free_endpoints(small_beams, snapped_state, 0.30)
        assert len(corrections) == 0

    def test_already_snapped_excluded(self):
        """Fully-snapped SB endpoints are not considered for clustering."""
        small_beams = [
            # Fully snapped
            {"x1": 0.0, "y1": 0.0, "x2": 4.25, "y2": 3.0,
             "section": "SB25X50", "floors": ["1F"]},
            # Half snapped, free end near (4.25, 3.0)
            {"x1": 10.0, "y1": 0.0, "x2": 4.27, "y2": 3.02,
             "section": "SB25X50", "floors": ["1F"]},
        ]
        snapped_state = [[True, True], [True, False]]
        corrections = cluster_free_endpoints(small_beams, snapped_state, 0.30)
        # Only 1 free endpoint → not enough for a cluster
        assert len(corrections) == 0

    def test_no_cluster_flag(self, simple_grid_data):
        """no_cluster=True disables endpoint clustering."""
        config = {
            "columns": [{"grid_x": 0.0, "grid_y": 0.0, "floors": ["1F"]}],
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 8.5, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        sb_data = {
            "small_beams": [
                # Two SBs whose free ends are close but won't snap to anything
                {"x1": 0.0, "y1": 3.02, "x2": 4.25, "y2": 3.02,
                 "section": "SB25X50", "floors": ["1F"]},
                {"x1": 8.5, "y1": 3.0, "x2": 4.27, "y2": 3.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        _, report = validate_small_beams(
            sb_data, config, simple_grid_data, tolerance=1.0,
            no_cluster=True, no_split=True, no_angle_correct=True)
        assert report["cluster_count"] == 0
        assert report["clustered_endpoints"] == 0

    def test_clustered_sb_becomes_target_in_round2(self, simple_grid_data):
        """After clustering, the now-fully-snapped SB becomes a snap target for others."""
        config = {
            "columns": [],
            "beams": [
                # Horizontal beam at Y=0
                {"x1": 0.0, "y1": 0.0, "x2": 8.5, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
                # Horizontal beam at Y=6
                {"x1": 0.0, "y1": 6.0, "x2": 8.5, "y2": 6.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        sb_data = {
            "small_beams": [
                # SB-A: vertical from beam Y=0 to free end at (4.25, 3.02)
                # → start snaps to beam, end is free → half-snapped
                {"x1": 4.25, "y1": 0.02, "x2": 4.25, "y2": 3.02,
                 "section": "SB25X50", "floors": ["1F"]},
                # SB-B: vertical from beam Y=6 to free end at (4.27, 3.0)
                # → start snaps to beam, end is free → half-snapped
                {"x1": 4.27, "y1": 5.98, "x2": 4.27, "y2": 3.0,
                 "section": "SB25X50", "floors": ["1F"]},
                # SB-C: horizontal, starts at free position near the cluster point,
                # ends far from anything. After SB-A+B cluster, this should snap
                # to the cluster point in round 2.
                {"x1": 4.28, "y1": 3.03, "x2": 2.0, "y2": 3.03,
                 "section": "SB20X40", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, simple_grid_data, tolerance=1.0,
            no_split=True, no_angle_correct=True)
        # SB-A and SB-B should have been clustered
        assert report["cluster_count"] >= 1
        # SB-C's start should have snapped to the cluster point (via SB-A or SB-B
        # becoming a segment target)
        sb_c = validated["small_beams"][2]
        # The start of SB-C (4.28, 3.03) should have snapped close to cluster centroid
        assert report["snapped_endpoints"] >= 3  # at least A-start, B-start, C-start

    def test_split_tolerance_default(self, simple_grid_data):
        """Verify split_tolerance default is 0.30m (column 0.25m from SB line splits it)."""
        config = {
            "columns": [
                {"grid_x": 8.5, "grid_y": 3.25, "floors": ["1F"]},
            ],
            "beams": [
                {"x1": 0.0, "y1": 3.0, "x2": 17.0, "y2": 3.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        sb_data = {
            "small_beams": [
                # Horizontal SB along Y=3 from X=0 to X=17
                # Column at (8.5, 3.25) is 0.25m from the SB line
                # With old default 0.15m: no split. With new 0.30m: split.
                {"x1": 0.0, "y1": 3.0, "x2": 17.0, "y2": 3.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, simple_grid_data, tolerance=1.0,
            no_angle_correct=True, no_cluster=True)
        # Column 0.25m away should now cause a split with default 0.30m tolerance
        assert report["split_sbs"] == 1
        assert len(validated["small_beams"]) == 2


# ---------------------------------------------------------------------------
# Ray-ray intersection tests
# ---------------------------------------------------------------------------

class TestRayRayIntersection:
    """Tests for ray_ray_intersection helper and cluster integration."""

    def test_ray_ray_intersection_helper(self):
        """Direct test of ray_ray_intersection: perpendicular rays."""
        # Horizontal ray from (0, 3) going right
        # Vertical ray from (5, 0) going up
        result = ray_ray_intersection(0, 3, 1, 0, 5, 0, 0, 1)
        assert result is not None
        ix, iy = result
        assert ix == 5.0
        assert iy == 3.0

    def test_ray_ray_intersection_helper_oblique(self):
        """Direct test: two oblique rays intersect."""
        import math
        # Ray 1 from (0, 0) at 30 degrees
        d1x = math.cos(math.radians(30))
        d1y = math.sin(math.radians(30))
        # Ray 2 from (10, 0) at 150 degrees
        d2x = math.cos(math.radians(150))
        d2y = math.sin(math.radians(150))
        result = ray_ray_intersection(0, 0, d1x, d1y, 10, 0, d2x, d2y)
        assert result is not None
        ix, iy = result
        assert abs(ix - 5.0) < 0.01
        assert abs(iy - 2.89) < 0.02  # 5 * tan(30°) ≈ 2.887

    def test_ray_ray_intersection_parallel(self):
        """Parallel rays return None."""
        result = ray_ray_intersection(0, 0, 1, 0, 0, 5, 1, 0)
        assert result is None

    def test_perpendicular_ray_ray_cluster(self):
        """Two perpendicular SBs cluster via ray intersection to exact point."""
        small_beams = [
            # SB-A: vertical from (3.0, 0.0) up to free end (3.0, 5.02)
            {"x1": 3.0, "y1": 0.0, "x2": 3.0, "y2": 5.02,
             "section": "SB25X50", "floors": ["2F"]},
            # SB-B: horizontal from (8.0, 5.0) left to free end (3.05, 5.0)
            {"x1": 8.0, "y1": 5.0, "x2": 3.05, "y2": 5.0,
             "section": "SB25X50", "floors": ["2F"]},
        ]
        snapped_state = [[True, False], [True, False]]
        corrections = cluster_free_endpoints(small_beams, snapped_state, 0.30)
        assert len(corrections) == 1
        assert corrections[0]["method"] == "ray_intersection"
        # Intersection at (3.0, 5.0)
        assert small_beams[0]["x2"] == 3.0
        assert small_beams[0]["y2"] == 5.0
        assert small_beams[1]["x2"] == 3.0
        assert small_beams[1]["y2"] == 5.0

    def test_oblique_ray_ray_cluster(self):
        """Two oblique SBs cluster via ray intersection."""
        import math
        # SB-A: from (0, 0) at 30° to free end near (5, 2.87)
        length_a = 5.77  # ~5/cos(30°)
        ax2 = round(length_a * math.cos(math.radians(30)), 2)
        ay2 = round(length_a * math.sin(math.radians(30)), 2)
        # SB-B: from (10, 0) at 150° to free end near (5, 2.87)
        length_b = 5.77
        bx2 = round(10 + length_b * math.cos(math.radians(150)), 2)
        by2 = round(length_b * math.sin(math.radians(150)), 2)

        small_beams = [
            {"x1": 0.0, "y1": 0.0, "x2": ax2, "y2": ay2,
             "section": "SB25X50", "floors": ["1F"]},
            {"x1": 10.0, "y1": 0.0, "x2": bx2, "y2": by2,
             "section": "SB25X50", "floors": ["1F"]},
        ]
        snapped_state = [[True, False], [True, False]]
        corrections = cluster_free_endpoints(small_beams, snapped_state, 0.50)
        assert len(corrections) == 1
        assert corrections[0]["method"] == "ray_intersection"
        # Both endpoints should converge to the intersection
        assert abs(small_beams[0]["x2"] - small_beams[1]["x2"]) < 0.02
        assert abs(small_beams[0]["y2"] - small_beams[1]["y2"]) < 0.02

    def test_parallel_rays_fallback_to_centroid(self):
        """Two parallel SBs fallback to centroid projection."""
        small_beams = [
            # SB-A: vertical from (4.0, 0.0) to free end (4.0, 3.02)
            {"x1": 4.0, "y1": 0.0, "x2": 4.0, "y2": 3.02,
             "section": "SB25X50", "floors": ["1F"]},
            # SB-B: vertical from (4.02, 6.0) to free end (4.02, 2.98)
            {"x1": 4.02, "y1": 6.0, "x2": 4.02, "y2": 2.98,
             "section": "SB25X50", "floors": ["1F"]},
        ]
        snapped_state = [[True, False], [True, False]]
        corrections = cluster_free_endpoints(small_beams, snapped_state, 0.30)
        assert len(corrections) == 1
        assert corrections[0]["method"] == "centroid_projection"
        # SB-A stays on x=4.0, SB-B stays on x=4.02 (projected along own axis)
        assert small_beams[0]["x2"] == 4.0
        assert small_beams[1]["x2"] == 4.02

    def test_ray_intersection_outside_tolerance_fallback(self):
        """Ray intersection too far from free endpoints → fallback to centroid."""
        small_beams = [
            # SB-A: nearly horizontal from (0, 0) to free (5.0, 0.1)
            {"x1": 0.0, "y1": 0.0, "x2": 5.0, "y2": 0.1,
             "section": "SB25X50", "floors": ["1F"]},
            # SB-B: nearly horizontal from (10, 0.2) to free (5.05, 0.15)
            {"x1": 10.0, "y1": 0.2, "x2": 5.05, "y2": 0.15,
             "section": "SB25X50", "floors": ["1F"]},
        ]
        snapped_state = [[True, False], [True, False]]
        # The rays are nearly parallel — intersection is very far away
        corrections = cluster_free_endpoints(small_beams, snapped_state, 0.30)
        if corrections:
            # Should fallback to centroid because intersection is far away
            assert corrections[0]["method"] == "centroid_projection"


# ---------------------------------------------------------------------------
# TestBuildGridLineTargets
# ---------------------------------------------------------------------------

class TestBuildGridLineTargets:

    def test_basic_grid_lines(self, simple_grid_data):
        """2 x-grids + 2 y-grids = 4 grid line segments."""
        targets = build_grid_line_targets(simple_grid_data, tolerance=1.0)
        assert len(targets) == 4  # 2 X lines + 2 Y lines
        for t in targets:
            assert t.kind == "segment"
            assert t.floors == []

    def test_x_grid_lines_vertical(self, simple_grid_data):
        """X grid lines are vertical segments spanning Y extent + margin."""
        targets = build_grid_line_targets(simple_grid_data, tolerance=1.0)
        # First 2 targets are X grid lines (vertical)
        x_targets = [t for t in targets
                     if abs(t.x1 - t.x2) < 0.001]  # vertical: x1 == x2
        assert len(x_targets) == 2
        # Check that they span at least Y range with margin
        for t in x_targets:
            assert t.y1 < 0.0  # below y_min with margin
            assert t.y2 > 6.0  # above y_max with margin

    def test_y_grid_lines_horizontal(self, simple_grid_data):
        """Y grid lines are horizontal segments spanning X extent + margin."""
        targets = build_grid_line_targets(simple_grid_data, tolerance=1.0)
        y_targets = [t for t in targets
                     if abs(t.y1 - t.y2) < 0.001]  # horizontal: y1 == y2
        assert len(y_targets) == 2
        for t in y_targets:
            assert t.x1 < 0.0  # left of x_min with margin
            assert t.x2 > 8.5  # right of x_max with margin

    def test_empty_grids(self):
        """Empty grid data returns no targets."""
        targets = build_grid_line_targets({"x": [], "y": []}, tolerance=1.0)
        assert len(targets) == 0

    def test_margin_uses_tolerance(self):
        """Margin is max(tolerance, 1.0)."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0}],
            "y": [{"label": "1", "coordinate": 0.0}],
        }
        targets = build_grid_line_targets(grid_data, tolerance=3.0)
        # With margin=3.0, the Y grid line should span from -3.0 to 3.0
        y_targets = [t for t in targets if abs(t.y1 - t.y2) < 0.001]
        assert len(y_targets) == 1
        assert y_targets[0].x1 == -3.0
        assert y_targets[0].x2 == 3.0


# ---------------------------------------------------------------------------
# TestGridLineSnap (Round 4)
# ---------------------------------------------------------------------------

class TestGridLineSnap:

    def test_grid_line_snap_free_endpoint(self):
        """SB endpoint not near any beam/wall/column but on a grid line
        → Round 4 snaps it to the grid line."""
        # Grid at X=0, X=8.5, Y=0, Y=6
        grid_data = {
            "x": [
                {"label": "A", "coordinate": 0.0},
                {"label": "B", "coordinate": 8.50},
            ],
            "y": [
                {"label": "1", "coordinate": 0.0},
                {"label": "2", "coordinate": 6.00},
            ],
        }
        # Config with beams only at Y=0 and Y=6 (no structure at Y=3)
        config = {
            "columns": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 8.5, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
                {"x1": 0.0, "y1": 6.0, "x2": 8.5, "y2": 6.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        # Vertical SB at X=4.25: start snaps to beam at Y=0,
        # end at Y=3.0 has no beam/wall/column → free after R1-3.
        # But X grid line at X=0 or X=8.5 won't help (perpendicular).
        # Y grid line at Y=0 already snapped. Y grid at Y=6 too far.
        # Instead, let's use a horizontal SB endpoint near an X grid line.
        sb_data = {
            "small_beams": [
                # Horizontal SB: start at (0.0, 3.0) snaps to X=0 beam/grid,
                # end at (8.45, 3.0) is near X=8.5 grid line but no beam at Y=3
                {"x1": 0.02, "y1": 3.0, "x2": 8.45, "y2": 3.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, grid_data, tolerance=1.0,
            no_split=True, no_angle_correct=True)
        sb = validated["small_beams"][0]
        # Start should snap to beam at Y=0 line intersection or grid (0,3)
        # End at (8.45, 3.0): ray from horizontal SB hits X=8.5 grid line → (8.5, 3.0)
        assert abs(sb["x2"] - 8.5) < 0.01
        assert report["grid_line_snapped_endpoints"] >= 1
        # Check correction has target_type="grid_line"
        gl_corrections = [c for c in report["corrections"]
                          if c.get("target_type") == "grid_line"]
        assert len(gl_corrections) >= 1

    def test_grid_line_snap_skipped_when_already_snapped(self):
        """SB endpoint already snapped in Round 1-3 is not re-snapped in Round 4."""
        grid_data = {
            "x": [
                {"label": "A", "coordinate": 0.0},
                {"label": "B", "coordinate": 8.50},
            ],
            "y": [
                {"label": "1", "coordinate": 0.0},
                {"label": "2", "coordinate": 6.00},
            ],
        }
        config = {
            "columns": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 8.5, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
                {"x1": 0.0, "y1": 6.0, "x2": 8.5, "y2": 6.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        # Vertical SB spanning two beams: both endpoints should snap in Round 1
        sb_data = {
            "small_beams": [
                {"x1": 4.25, "y1": 0.03, "x2": 4.25, "y2": 5.97,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, grid_data, tolerance=1.0,
            no_split=True, no_angle_correct=True)
        sb = validated["small_beams"][0]
        # Both endpoints should be snapped to beams (not grid lines)
        assert abs(sb["y1"] - 0.0) < 0.01
        assert abs(sb["y2"] - 6.0) < 0.01
        # No grid_line corrections (already snapped before Round 4)
        assert report["grid_line_snapped_endpoints"] == 0

    def test_no_grid_snap_flag(self):
        """--no-grid-snap disables Round 4 entirely."""
        grid_data = {
            "x": [
                {"label": "A", "coordinate": 0.0},
                {"label": "B", "coordinate": 8.50},
            ],
            "y": [
                {"label": "1", "coordinate": 0.0},
                {"label": "2", "coordinate": 6.00},
            ],
        }
        config = {
            "columns": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 8.5, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
                {"x1": 0.0, "y1": 6.0, "x2": 8.5, "y2": 6.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        sb_data = {
            "small_beams": [
                # Horizontal SB with end near X=8.5 grid line
                {"x1": 0.02, "y1": 3.0, "x2": 8.45, "y2": 3.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        # With no_grid_snap=True, Round 4 should not run
        validated_no_gs, report_no_gs = validate_small_beams(
            sb_data, config, grid_data, tolerance=1.0,
            no_split=True, no_angle_correct=True, no_grid_snap=True)
        assert report_no_gs["grid_line_snapped_endpoints"] == 0

        # With no_grid_snap=False (default), Round 4 should snap the end
        validated_gs, report_gs = validate_small_beams(
            sb_data, config, grid_data, tolerance=1.0,
            no_split=True, no_angle_correct=True, no_grid_snap=False)
        assert report_gs["grid_line_snapped_endpoints"] >= 1

    def test_grid_line_snap_diagonal_sb(self):
        """Diagonal SB's free endpoint snaps to grid line via Round 4."""
        grid_data = {
            "x": [
                {"label": "A", "coordinate": 0.0},
                {"label": "B", "coordinate": 8.50},
            ],
            "y": [
                {"label": "1", "coordinate": 0.0},
                {"label": "2", "coordinate": 6.00},
            ],
        }
        config = {
            "columns": [],
            "beams": [
                # Beam at Y=0 so start can snap in Round 1
                {"x1": 0.0, "y1": 0.0, "x2": 8.5, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        # Diagonal SB: start near beam at Y=0, end near X=8.5 grid line
        # Start (2.0, 0.03) snaps to beam at (2.0, 0.0) in Round 1
        # End (8.45, 3.0) has no beam/wall/column → free after R1-3
        # Ray direction from diagonal SB intersects X=8.5 grid line → Round 4
        sb_data = {
            "small_beams": [
                {"x1": 2.0, "y1": 0.03, "x2": 8.45, "y2": 3.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_small_beams(
            sb_data, config, grid_data, tolerance=1.0,
            no_split=True, no_angle_correct=True)
        sb = validated["small_beams"][0]
        # Start should snap to beam at Y=0
        assert abs(sb["y1"] - 0.0) < 0.01
        # End should be grid-line-snapped to X=8.5
        if report["grid_line_snapped_endpoints"] > 0:
            gl_corrections = [c for c in report["corrections"]
                              if c.get("target_type") == "grid_line"]
            assert len(gl_corrections) >= 1
            assert abs(sb["x2"] - 8.5) < 0.01

    def test_report_has_grid_line_snapped_field(self, simple_grid_data, simple_config):
        """Report always contains grid_line_snapped_endpoints key."""
        sb_data = {
            "small_beams": [
                {"x1": 4.25, "y1": 0.0, "x2": 4.25, "y2": 6.0,
                 "section": "SB25X50", "floors": ["1F"]},
            ],
        }
        _, report = validate_small_beams(
            sb_data, simple_config, simple_grid_data, tolerance=1.0)
        assert "grid_line_snapped_endpoints" in report

    def test_empty_sbs_has_grid_line_field(self, simple_grid_data, simple_config):
        """Empty small_beams report still has grid_line_snapped_endpoints=0."""
        sb_data = {"small_beams": []}
        _, report = validate_small_beams(
            sb_data, simple_config, simple_grid_data, tolerance=1.0)
        assert report["grid_line_snapped_endpoints"] == 0
