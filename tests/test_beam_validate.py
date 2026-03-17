"""Tests for golden_scripts.tools.beam_validate.

All tests use mock data — no ETABS connection required.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.beam_validate import (
    validate_beams,
    build_beam_targets,
    _find_nearest_grid_value,
    _normalize_grid_data_for_bv,
    correct_angles,
    segment_intersection,
    find_intermediate_supports,
    split_beam,
    split_all_beams,
    split_all_walls,
    snap_walls_to_beams,
)


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
def empty_elements():
    return {"columns": [], "walls": [], "beams": []}


# ---------------------------------------------------------------------------
# TestBuildBeamTargets
# ---------------------------------------------------------------------------

class TestBuildBeamTargets:

    def test_grid_intersections_count(self):
        """2 x-grids x 3 y-grids = 6 grid targets."""
        grid_data = {
            "x": [
                {"label": "A", "coordinate": 0.0},
                {"label": "B", "coordinate": 8.50},
            ],
            "y": [
                {"label": "1", "coordinate": 0.0},
                {"label": "2", "coordinate": 6.00},
                {"label": "3", "coordinate": 12.00},
            ],
        }
        elements = {"columns": [], "walls": [], "beams": []}
        grid_targets, element_targets = build_beam_targets(elements, grid_data)
        assert len(grid_targets) == 6
        assert len(element_targets) == 0
        # All grid targets should have empty floors
        for t in grid_targets:
            assert t.floors == []

    def test_column_targets(self):
        """1 column produces 1 point target."""
        grid_data = {"x": [], "y": []}
        elements = {
            "columns": [{"grid_x": 8.50, "grid_y": 6.00, "floors": ["1F", "2F"]}],
            "walls": [],
            "beams": [],
        }
        grid_targets, element_targets = build_beam_targets(elements, grid_data)
        assert len(grid_targets) == 0
        assert len(element_targets) == 1
        t = element_targets[0]
        assert t.kind == "point"
        assert t.x1 == 8.50
        assert t.y1 == 6.00
        assert t.floors == ["1F", "2F"]

    def test_wall_targets(self):
        """1 wall produces 1 segment target."""
        grid_data = {"x": [], "y": []}
        elements = {
            "columns": [],
            "walls": [{"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 10.0,
                        "floors": ["B3F", "B2F"]}],
            "beams": [],
        }
        grid_targets, element_targets = build_beam_targets(elements, grid_data)
        assert len(element_targets) == 1
        t = element_targets[0]
        assert t.kind == "segment"
        assert t.x1 == 0.0 and t.y1 == 0.0
        assert t.x2 == 0.0 and t.y2 == 10.0


# ---------------------------------------------------------------------------
# TestSnapToGrid
# ---------------------------------------------------------------------------

class TestSnapToGrid:

    def test_beam_snaps_to_grid_intersection(self, simple_grid_data):
        """Beam endpoint slightly off grid (8.52, 3.21) snaps to (8.50, 0.0)
        or nearest grid intersection within tolerance."""
        elements = {
            "columns": [],
            "walls": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0,
                 "x2": 8.52, "y2": 0.02,
                 "section": "B50X80", "floors": ["1F", "2F"]},
            ],
        }
        validated, report = validate_beams(elements, simple_grid_data, tolerance=1.5)
        # The end point (8.52, 0.02) should snap to grid (8.50, 0.0)
        beam = validated["beams"][0]
        assert beam["x2"] == 8.50
        assert beam["y2"] == 0.0
        assert report["snapped_endpoints"] >= 1

    def test_beam_beyond_tolerance_gets_warning(self, simple_grid_data):
        """Beam endpoint 2m from nearest target with tolerance=1.0 produces warning."""
        elements = {
            "columns": [],
            "walls": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0,
                 "x2": 4.25, "y2": 3.00,
                 "section": "B40X60", "floors": ["1F"]},
            ],
        }
        # Nearest grid intersection to (4.25, 3.00) is (0.0, 0.0) at ~5.2m
        # or (8.50, 0.0) at ~5.1m or (0.0, 6.0) at ~5.2m or (8.50, 6.0) at ~5.1m
        validated, report = validate_beams(elements, simple_grid_data, tolerance=1.0)
        assert report["warning_endpoints"] >= 1
        # Check warning structure
        w = [w for w in report["warnings"]
             if w.get("message", "").startswith("No target")]
        assert len(w) >= 1


# ---------------------------------------------------------------------------
# TestSnapToColumn
# ---------------------------------------------------------------------------

class TestSnapToColumn:

    def test_beam_snaps_to_column_with_floor_overlap(self, simple_grid_data):
        """Beam shares floor '1F' with column, should snap to column."""
        elements = {
            "columns": [
                {"grid_x": 8.40, "grid_y": 3.20, "floors": ["1F", "2F"]},
            ],
            "walls": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0,
                 "x2": 8.42, "y2": 3.18,
                 "section": "B40X60", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(elements, simple_grid_data, tolerance=1.5)
        beam = validated["beams"][0]
        # End point should snap to column at (8.40, 3.20)
        assert beam["x2"] == 8.40
        assert beam["y2"] == 3.20

    def test_beam_no_snap_without_floor_overlap(self, simple_grid_data):
        """Beam has floors ['3F'], column has ['1F']. Column target skipped
        but grid intersection (floors=[]) still available."""
        elements = {
            "columns": [
                {"grid_x": 4.25, "grid_y": 3.00, "floors": ["1F"]},
            ],
            "walls": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0,
                 "x2": 4.23, "y2": 2.98,
                 "section": "B40X60", "floors": ["3F"]},
            ],
        }
        validated, report = validate_beams(elements, simple_grid_data, tolerance=1.5)
        # Column at (4.25, 3.00) has floors ["1F"], beam has ["3F"] -> no overlap.
        # But grid intersections have floors=[] -> skip floor check.
        # Nearest grid intersection to (4.23, 2.98) is (0, 0) at ~5.2m > 1.5m
        # so this endpoint should NOT snap to the column.
        # It may snap to grid or remain unsnapped depending on distance.
        beam = validated["beams"][0]
        # The column should NOT be the snap target
        assert not (beam["x2"] == 4.25 and beam["y2"] == 3.00)


# ---------------------------------------------------------------------------
# TestSnapToWall
# ---------------------------------------------------------------------------

class TestSnapToWall:

    def test_beam_snaps_to_wall_segment(self, simple_grid_data):
        """Beam endpoint near mid-point of wall segment snaps to nearest point on wall."""
        elements = {
            "columns": [],
            "walls": [
                {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 6.00,
                 "floors": ["1F", "2F"]},
            ],
            "beams": [
                {"x1": 8.50, "y1": 0.0,
                 "x2": 0.08, "y2": 3.05,
                 "section": "B40X60", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(elements, simple_grid_data, tolerance=1.5)
        beam = validated["beams"][0]
        # End point (0.08, 3.05) should snap to wall at (0.0, 3.05)
        assert beam["x2"] == 0.0
        assert abs(beam["y2"] - 3.05) < 0.01


# ---------------------------------------------------------------------------
# TestSnapToBeam (T-junction / chain snap)
# ---------------------------------------------------------------------------

class TestSnapToBeam:

    def test_beam_snaps_to_another_beam(self, simple_grid_data):
        """Beam A snapped in round 1, Beam B endpoint near Beam A mid-segment
        snaps in round 2."""
        elements = {
            "columns": [],
            "walls": [],
            "beams": [
                # Beam A: spans grid A/1 to B/1 (clean grid endpoints)
                {"x1": 0.0, "y1": 0.0,
                 "x2": 8.50, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
                # Beam B: starts at grid A/2, ends near mid-point of Beam A
                {"x1": 0.0, "y1": 6.00,
                 "x2": 4.22, "y2": 0.05,
                 "section": "B30X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(elements, simple_grid_data, tolerance=1.5)
        beam_b = validated["beams"][1]
        # Beam B end (4.22, 0.05) should snap to Beam A segment at (4.22, 0.0)
        assert abs(beam_b["y2"] - 0.0) < 0.01

    def test_chain_snap(self, grid_3x3):
        """Beam A -> column, Beam B -> grid, Beam C -> Beam B: multi-round chain.

        After snap + split, beams may be split at crossing points. We verify
        that the snapped coordinates exist somewhere in the output beams.
        """
        elements = {
            "columns": [
                {"grid_x": 0.0, "grid_y": 0.0, "floors": ["1F"]},
                {"grid_x": 17.00, "grid_y": 0.0, "floors": ["1F"]},
            ],
            "walls": [],
            "beams": [
                # Beam A: spans column to grid B/1 (snaps round 1)
                {"x1": 0.02, "y1": 0.01,
                 "x2": 8.48, "y2": 0.03,
                 "section": "B50X80", "floors": ["1F"]},
                # Beam B: from grid B/1 to C/1
                {"x1": 8.52, "y1": 0.02,
                 "x2": 16.98, "y2": 0.03,
                 "section": "B50X80", "floors": ["1F"]},
                # Beam C: starts at grid A/2, ends near mid-point of Beam B
                {"x1": 0.0, "y1": 6.00,
                 "x2": 12.75, "y2": 0.08,
                 "section": "B30X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(elements, grid_3x3, tolerance=1.5)
        all_beams = validated["beams"]
        # Verify key snapped coordinates exist in the output
        # Beam A endpoints: (0,0) and (8.5,0)
        b50_beams = [b for b in all_beams if b["section"] == "B50X80"]
        start_at_origin = any(b["x1"] == 0.0 and b["y1"] == 0.0 for b in b50_beams)
        end_at_c1 = any(b["x2"] == 17.0 and b["y2"] == 0.0 for b in b50_beams)
        assert start_at_origin, "Should have a B50X80 beam starting at (0,0)"
        assert end_at_c1, "Should have a B50X80 beam ending at (17,0)"
        # Beam C end should snap near y=0
        b30_beams = [b for b in all_beams if b["section"] == "B30X50"]
        assert any(abs(b["y2"] - 0.0) < 0.01 or abs(b["y1"] - 0.0) < 0.01
                    for b in b30_beams), "Beam C should have an endpoint at y≈0"


# ---------------------------------------------------------------------------
# TestFloorOverlap
# ---------------------------------------------------------------------------

class TestFloorOverlap:
    """Tests for floor overlap logic used within validation."""

    def test_overlapping_floors(self, simple_grid_data):
        """Beam and column share floor '2F' -> column is valid snap target."""
        elements = {
            "columns": [
                {"grid_x": 4.25, "grid_y": 3.00, "floors": ["2F", "3F"]},
            ],
            "walls": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0,
                 "x2": 4.27, "y2": 3.02,
                 "section": "B40X60", "floors": ["1F", "2F"]},
            ],
        }
        validated, report = validate_beams(elements, simple_grid_data, tolerance=1.5)
        beam = validated["beams"][0]
        # Should snap to column (floor overlap on 2F)
        assert beam["x2"] == 4.25
        assert beam["y2"] == 3.00

    def test_no_overlap(self, simple_grid_data):
        """Beam has ['1F'], column has ['3F'] -> no overlap, column not used."""
        elements = {
            "columns": [
                {"grid_x": 4.25, "grid_y": 3.00, "floors": ["3F"]},
            ],
            "walls": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0,
                 "x2": 4.27, "y2": 3.02,
                 "section": "B40X60", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(elements, simple_grid_data, tolerance=1.5)
        beam = validated["beams"][0]
        # Column has no floor overlap -> should NOT snap to column
        assert not (beam["x2"] == 4.25 and beam["y2"] == 3.00)


# ---------------------------------------------------------------------------
# TestReport
# ---------------------------------------------------------------------------

class TestReport:

    def test_report_structure(self, simple_grid_data):
        """Verify report has all required keys including angle + split + wall_split."""
        elements = {
            "columns": [],
            "walls": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 8.52, "y2": 0.03,
                 "section": "B50X80", "floors": ["1F"]},
            ],
        }
        _, report = validate_beams(elements, simple_grid_data, tolerance=1.5)
        required_keys = [
            "total_beams", "total_endpoints", "snapped_endpoints",
            "warning_endpoints", "max_snap_distance", "avg_snap_distance",
            "corrections", "warnings",
            "angle_corrections", "angle_corrected_beams", "angle_corrected_walls",
            "split_beams", "new_beams_from_split", "total_beams_after_split",
            "split_details",
            "wall_split_walls", "wall_new_from_split", "wall_total_after_split",
            "wall_split_details",
        ]
        for key in required_keys:
            assert key in report, f"Missing key: {key}"

    def test_no_corrections_needed(self, simple_grid_data):
        """Beams already at exact grid intersections -> 0 corrections."""
        elements = {
            "columns": [],
            "walls": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 8.50, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(elements, simple_grid_data, tolerance=1.5)
        # Both endpoints are exactly at grid intersections — snap distance 0
        # The snap function will fire but with d=0, which is within tolerance.
        # Depending on implementation, d=0 may or may not be recorded.
        # At minimum, no warnings should be generated.
        assert report["warning_endpoints"] == 0
        beam = validated["beams"][0]
        assert beam["x1"] == 0.0 and beam["y1"] == 0.0
        assert beam["x2"] == 8.50 and beam["y2"] == 0.0

    def test_corrections_recorded(self, simple_grid_data):
        """Beam slightly off grid -> correction recorded with all fields."""
        elements = {
            "columns": [],
            "walls": [],
            "beams": [
                {"x1": 0.03, "y1": 0.02, "x2": 8.50, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
        }
        _, report = validate_beams(elements, simple_grid_data, tolerance=1.5)
        assert report["snapped_endpoints"] >= 1
        c = report["corrections"][0]
        required_fields = [
            "beam_index", "original_x1", "original_y1",
            "original_x2", "original_y2", "section", "floors",
            "endpoint", "original_coord", "corrected_coord",
            "snap_distance", "target_type", "target_label",
        ]
        for field in required_fields:
            assert field in c, f"Correction missing field: {field}"
        assert c["snap_distance"] > 0


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_beams(self, simple_grid_data):
        """Elements with no beams -> report with 0 everything."""
        elements = {"columns": [], "walls": [], "beams": []}
        validated, report = validate_beams(elements, simple_grid_data, tolerance=1.5)
        assert report["total_beams"] == 0
        assert report["total_endpoints"] == 0
        assert report["snapped_endpoints"] == 0
        assert report["warning_endpoints"] == 0
        assert report["max_snap_distance"] == 0
        assert report["avg_snap_distance"] == 0
        assert report["corrections"] == []
        assert report["warnings"] == []

    def test_zero_length_after_snap_warning(self, simple_grid_data):
        """Two beam endpoints snap to same grid point -> zero-length warning."""
        elements = {
            "columns": [],
            "walls": [],
            "beams": [
                # Both endpoints very close to grid A/1 (0.0, 0.0)
                {"x1": 0.01, "y1": 0.02, "x2": 0.03, "y2": 0.01,
                 "section": "B30X50", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(elements, simple_grid_data, tolerance=1.5)
        # Both endpoints should snap to (0.0, 0.0)
        beam = validated["beams"][0]
        assert beam["x1"] == 0.0 and beam["y1"] == 0.0
        assert beam["x2"] == 0.0 and beam["y2"] == 0.0
        # Should have a zero-length warning
        zero_warnings = [w for w in report["warnings"]
                         if "Zero-length" in w.get("message", "")]
        assert len(zero_warnings) == 1


# ---------------------------------------------------------------------------
# TestFindNearestGridValue
# ---------------------------------------------------------------------------

class TestFindNearestGridValue:

    def test_normal_lookup(self):
        """Find nearest grid line to a coordinate."""
        grids = [
            {"label": "A", "coordinate": 0.0},
            {"label": "B", "coordinate": 8.50},
            {"label": "C", "coordinate": 17.00},
        ]
        coord, dist, label = _find_nearest_grid_value(8.6, grids)
        assert coord == 8.50
        assert label == "B"
        assert abs(dist - 0.1) < 0.001

    def test_empty_grid(self):
        """No grid lines -> (None, inf, None)."""
        coord, dist, label = _find_nearest_grid_value(5.0, [])
        assert coord is None
        assert dist == float("inf")
        assert label is None

    def test_multiple_close(self):
        """Multiple grid lines, picks closest."""
        grids = [
            {"label": "1", "coordinate": 0.0},
            {"label": "2", "coordinate": 6.00},
            {"label": "3", "coordinate": 12.00},
        ]
        coord, dist, label = _find_nearest_grid_value(5.5, grids)
        assert coord == 6.0
        assert label == "2"


# ---------------------------------------------------------------------------
# TestCorrectAngles
# ---------------------------------------------------------------------------

class TestCorrectAngles:

    def test_near_horizontal_corrects_to_grid(self):
        """Beam tilted ~1° from horizontal aligns Y to nearest grid line."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0},
                   {"label": "B", "coordinate": 8.50}],
            "y": [{"label": "1", "coordinate": 0.0},
                   {"label": "2", "coordinate": 6.00}],
        }
        elements = {
            "beams": [
                # ~1° tilt: dy/dx = 0.15/8.5 ≈ 0.018 → ~1.0°
                {"x1": 0.0, "y1": 5.92, "x2": 8.5, "y2": 6.07,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [], "columns": [],
        }
        elements, angle_report = correct_angles(elements, grid_data)
        beam = elements["beams"][0]
        # Both Y should be snapped to grid "2" at 6.00
        assert beam["y1"] == 6.0
        assert beam["y2"] == 6.0
        assert len(angle_report) == 1
        assert angle_report[0]["correction_axis"] == "Y"
        assert angle_report[0]["target_grid_label"] == "2"

    def test_near_vertical_corrects_to_grid(self):
        """Beam tilted ~1.5° from vertical aligns X to nearest grid line."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0},
                   {"label": "B", "coordinate": 8.50}],
            "y": [{"label": "1", "coordinate": 0.0},
                   {"label": "2", "coordinate": 6.00}],
        }
        elements = {
            "beams": [
                # ~1.5° tilt from vertical: dx/dy = 0.16/6.0 ≈ 0.027 → ~1.5°
                {"x1": 8.42, "y1": 0.0, "x2": 8.58, "y2": 6.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [], "columns": [],
        }
        elements, angle_report = correct_angles(elements, grid_data)
        beam = elements["beams"][0]
        assert beam["x1"] == 8.5
        assert beam["x2"] == 8.5
        assert angle_report[0]["correction_axis"] == "X"

    def test_true_diagonal_not_corrected(self):
        """Beam at 30° is not corrected."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0}],
            "y": [{"label": "1", "coordinate": 0.0}],
        }
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 8.0, "y2": 4.62,
                 "section": "B30X50", "floors": ["1F"]},
            ],
            "walls": [], "columns": [],
        }
        elements, angle_report = correct_angles(elements, grid_data)
        assert len(angle_report) == 0
        beam = elements["beams"][0]
        assert beam["x2"] == 8.0
        assert beam["y2"] == 4.62

    def test_3deg_not_corrected_with_default_threshold(self):
        """Beam at ~3° is NOT corrected with default 2° threshold."""
        import math
        dy = 10.0 * math.tan(math.radians(3.0))
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0}],
            "y": [{"label": "1", "coordinate": 0.0}],
        }
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": dy,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [], "columns": [],
        }
        elements, angle_report = correct_angles(elements, grid_data)
        # 3° > 2° default threshold → not corrected
        assert len(angle_report) == 0

    def test_zero_length_skipped(self):
        """Zero-length beam is skipped."""
        grid_data = {"x": [], "y": []}
        elements = {
            "beams": [
                {"x1": 5.0, "y1": 5.0, "x2": 5.0, "y2": 5.0,
                 "section": "B30X50", "floors": ["1F"]},
            ],
            "walls": [], "columns": [],
        }
        elements, angle_report = correct_angles(elements, grid_data)
        assert len(angle_report) == 0

    def test_wall_also_corrected(self):
        """Walls are also angle-corrected."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0}],
            "y": [{"label": "1", "coordinate": 0.0},
                   {"label": "2", "coordinate": 10.0}],
        }
        elements = {
            "beams": [],
            "walls": [
                # ~0.7° tilt: dx/dy = 0.12/10.0 → ~0.7°
                {"x1": 0.06, "y1": 0.0, "x2": -0.06, "y2": 10.0,
                 "section": "W30", "floors": ["1F"]},
            ],
            "columns": [],
        }
        elements, angle_report = correct_angles(elements, grid_data)
        wall = elements["walls"][0]
        assert wall["x1"] == 0.0
        assert wall["x2"] == 0.0
        assert angle_report[0]["element_type"] == "wall"

    def test_fallback_to_average(self):
        """When no grid line is close, use average of endpoints."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 100.0}],  # very far
            "y": [{"label": "1", "coordinate": 100.0}],   # very far
        }
        elements = {
            "beams": [
                # ~0.7° tilt
                {"x1": 0.0, "y1": 5.05, "x2": 8.0, "y2": 4.95,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [], "columns": [],
        }
        elements, angle_report = correct_angles(elements, grid_data)
        beam = elements["beams"][0]
        assert beam["y1"] == beam["y2"] == 5.0
        assert angle_report[0]["target_grid_label"] == "average"

    def test_threshold_boundary(self):
        """Angle exactly at threshold (2°) should be corrected."""
        import math
        # 2° = tan(2°) ≈ 0.0349, for length 10m → dy ≈ 0.349
        dy = 10.0 * math.tan(math.radians(2.0))
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0}],
            "y": [{"label": "1", "coordinate": 0.0}],
        }
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": dy,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [], "columns": [],
        }
        elements, angle_report = correct_angles(elements, grid_data)
        # At exactly 2° threshold, should be corrected (≤ threshold)
        assert len(angle_report) == 1

    def test_explicit_5deg_threshold(self):
        """Angle correction with explicit 5° threshold still works."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0},
                   {"label": "B", "coordinate": 8.50}],
            "y": [{"label": "1", "coordinate": 0.0},
                   {"label": "2", "coordinate": 6.00}],
        }
        elements = {
            "beams": [
                # ~1.6° tilt
                {"x1": 0.0, "y1": 5.88, "x2": 8.5, "y2": 6.12,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [], "columns": [],
        }
        elements, angle_report = correct_angles(elements, grid_data, 5.0)
        beam = elements["beams"][0]
        assert beam["y1"] == 6.0
        assert beam["y2"] == 6.0


# ---------------------------------------------------------------------------
# TestSegmentIntersection
# ---------------------------------------------------------------------------

class TestSegmentIntersection:

    def test_perpendicular_crossing(self):
        """Two perpendicular segments crossing at (5, 5)."""
        result = segment_intersection(0, 5, 10, 5, 5, 0, 5, 10)
        assert result is not None
        x, y, ta, tb = result
        assert abs(x - 5.0) < 0.001
        assert abs(y - 5.0) < 0.001
        assert abs(ta - 0.5) < 0.001
        assert abs(tb - 0.5) < 0.001

    def test_parallel_no_intersection(self):
        """Two parallel horizontal segments."""
        result = segment_intersection(0, 0, 10, 0, 0, 5, 10, 5)
        assert result is None

    def test_non_overlapping(self):
        """Two segments that don't overlap."""
        result = segment_intersection(0, 0, 5, 0, 6, 1, 6, 10)
        assert result is None

    def test_t_junction(self):
        """Segment B ends on segment A (T-junction)."""
        result = segment_intersection(0, 0, 10, 0, 5, -3, 5, 0)
        assert result is not None
        x, y, ta, tb = result
        assert abs(x - 5.0) < 0.001
        assert abs(y - 0.0) < 0.001


# ---------------------------------------------------------------------------
# TestFindIntermediateSupports
# ---------------------------------------------------------------------------

class TestFindIntermediateSupports:

    def test_column_on_beam_midspan(self):
        """Column at midspan of beam produces one support point."""
        beam = {"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                "section": "B50X80", "floors": ["1F"]}
        columns = [{"grid_x": 8.5, "grid_y": 0.0, "floors": ["1F"]}]
        supports = find_intermediate_supports(beam, columns, [], 0.15)
        assert len(supports) == 1
        assert abs(supports[0][1] - 8.5) < 0.01
        assert abs(supports[0][2] - 0.0) < 0.01

    def test_column_too_far_from_beam(self):
        """Column 0.5m from beam line → not a support (tolerance=0.15)."""
        beam = {"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                "section": "B50X80", "floors": ["1F"]}
        columns = [{"grid_x": 8.5, "grid_y": 0.5, "floors": ["1F"]}]
        supports = find_intermediate_supports(beam, columns, [], 0.15)
        assert len(supports) == 0

    def test_column_at_endpoint(self):
        """Column at beam endpoint (t < 0.02) is excluded."""
        beam = {"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                "section": "B50X80", "floors": ["1F"]}
        columns = [{"grid_x": 0.0, "grid_y": 0.0, "floors": ["1F"]}]
        supports = find_intermediate_supports(beam, columns, [], 0.15)
        assert len(supports) == 0

    def test_no_floor_overlap_excluded(self):
        """Column with no floor overlap is excluded."""
        beam = {"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                "section": "B50X80", "floors": ["1F"]}
        columns = [{"grid_x": 8.5, "grid_y": 0.0, "floors": ["3F"]}]
        supports = find_intermediate_supports(beam, columns, [], 0.15)
        assert len(supports) == 0

    def test_wall_crossing(self):
        """Wall crossing beam mid-span produces support point."""
        beam = {"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                "section": "B50X80", "floors": ["1F"]}
        walls = [{"x1": 8.5, "y1": -3.0, "x2": 8.5, "y2": 3.0,
                  "floors": ["1F"]}]
        supports = find_intermediate_supports(beam, [], walls, 0.15)
        assert len(supports) == 1
        assert abs(supports[0][1] - 8.5) < 0.01

    def test_parallel_wall_excluded(self):
        """Wall parallel to beam is excluded (dot > 0.95)."""
        beam = {"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                "section": "B50X80", "floors": ["1F"]}
        walls = [{"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                  "floors": ["1F"]}]
        supports = find_intermediate_supports(beam, [], walls, 0.15)
        assert len(supports) == 0

    def test_multiple_supports_sorted(self):
        """Multiple columns on beam, sorted by t."""
        beam = {"x1": 0.0, "y1": 0.0, "x2": 24.0, "y2": 0.0,
                "section": "B50X80", "floors": ["1F"]}
        columns = [
            {"grid_x": 16.0, "grid_y": 0.0, "floors": ["1F"]},
            {"grid_x": 8.0, "grid_y": 0.0, "floors": ["1F"]},
        ]
        supports = find_intermediate_supports(beam, columns, [], 0.15)
        assert len(supports) == 2
        # Should be sorted by t: 8.0 first, then 16.0
        assert supports[0][1] < supports[1][1]


# ---------------------------------------------------------------------------
# TestSplitBeam
# ---------------------------------------------------------------------------

class TestSplitBeam:

    def test_single_split(self):
        """One support point → 2 sub-beams."""
        beam = {"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                "section": "B50X80", "floors": ["1F", "2F"]}
        supports = [(0.5, 8.5, 0.0, "column at (8.5,0.0)")]
        result = split_beam(beam, supports)
        assert len(result) == 2
        assert result[0]["x1"] == 0.0 and result[0]["x2"] == 8.5
        assert result[1]["x1"] == 8.5 and result[1]["x2"] == 17.0
        # Inherited fields
        assert result[0]["section"] == "B50X80"
        assert result[0]["floors"] == ["1F", "2F"]

    def test_double_split(self):
        """Two support points → 3 sub-beams."""
        beam = {"x1": 0.0, "y1": 0.0, "x2": 24.0, "y2": 0.0,
                "section": "B50X80", "floors": ["1F"]}
        supports = [
            (1/3, 8.0, 0.0, "column at (8.0,0.0)"),
            (2/3, 16.0, 0.0, "column at (16.0,0.0)"),
        ]
        result = split_beam(beam, supports)
        assert len(result) == 3
        assert result[0]["x2"] == 8.0
        assert result[1]["x1"] == 8.0 and result[1]["x2"] == 16.0
        assert result[2]["x1"] == 16.0

    def test_extra_fields_preserved(self):
        """Extra fields (like 'color') are inherited."""
        beam = {"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                "section": "B50X80", "floors": ["1F"], "color": "blue"}
        supports = [(0.5, 8.5, 0.0, "col")]
        result = split_beam(beam, supports)
        for sub in result:
            assert sub["color"] == "blue"


# ---------------------------------------------------------------------------
# TestSplitAllBeams
# ---------------------------------------------------------------------------

class TestSplitAllBeams:

    def test_no_split_needed(self):
        """No intermediate supports → no splitting."""
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 8.5, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "columns": [
                {"grid_x": 0.0, "grid_y": 0.0, "floors": ["1F"]},
                {"grid_x": 8.5, "grid_y": 0.0, "floors": ["1F"]},
            ],
            "walls": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_beams(elements, grid_data, 0.15)
        assert report["split_beams"] == 0
        assert len(elements["beams"]) == 1

    def test_beam_across_two_spans(self):
        """Beam from A to C with column at B → split into 2."""
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "columns": [
                {"grid_x": 0.0, "grid_y": 0.0, "floors": ["1F"]},
                {"grid_x": 8.5, "grid_y": 0.0, "floors": ["1F"]},
                {"grid_x": 17.0, "grid_y": 0.0, "floors": ["1F"]},
            ],
            "walls": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_beams(elements, grid_data, 0.15)
        assert report["split_beams"] == 1
        assert len(elements["beams"]) == 2
        assert elements["beams"][0]["x2"] == 8.5
        assert elements["beams"][1]["x1"] == 8.5

    def test_diagonal_beam_split(self):
        """Diagonal beam split at wall crossing."""
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 10.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "columns": [],
            "walls": [
                {"x1": 5.0, "y1": 0.0, "x2": 5.0, "y2": 10.0,
                 "floors": ["1F"]},
            ],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_beams(elements, grid_data, 0.15)
        assert report["split_beams"] == 1
        assert len(elements["beams"]) == 2


# ---------------------------------------------------------------------------
# TestSnapAndSplit (integration)
# ---------------------------------------------------------------------------

class TestSnapAndSplit:

    def test_snap_split_angle_integration(self, grid_3x3):
        """Full pipeline: snap → split → angle correction (new order)."""
        elements = {
            "columns": [
                {"grid_x": 0.0, "grid_y": 0.0, "floors": ["1F"]},
                {"grid_x": 8.5, "grid_y": 0.0, "floors": ["1F"]},
                {"grid_x": 17.0, "grid_y": 0.0, "floors": ["1F"]},
            ],
            "walls": [],
            "beams": [
                # Beam from A/1 to C/1 with slight Y deviation (~0.7°)
                # → snap to grid → split at B/1 → angle correction aligns Y
                {"x1": 0.02, "y1": 0.12, "x2": 16.98, "y2": -0.08,
                 "section": "B50X80", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(elements, grid_3x3, tolerance=1.5)
        # After snap + split at column B + angle correction
        assert report["split_beams"] == 1
        assert len(validated["beams"]) == 2
        # Both sub-beams should have Y=0 (snap handles it, angle correction confirms)
        for b in validated["beams"]:
            assert b["y1"] == 0.0
            assert b["y2"] == 0.0

    def test_no_split_flag(self, grid_3x3):
        """--no-split disables splitting."""
        elements = {
            "columns": [
                {"grid_x": 0.0, "grid_y": 0.0, "floors": ["1F"]},
                {"grid_x": 8.5, "grid_y": 0.0, "floors": ["1F"]},
                {"grid_x": 17.0, "grid_y": 0.0, "floors": ["1F"]},
            ],
            "walls": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 17.0, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(
            elements, grid_3x3, tolerance=1.5, no_split=True)
        assert report["split_beams"] == 0
        assert len(validated["beams"]) == 1

    def test_no_angle_correct_flag(self, grid_3x3):
        """--no-angle-correct disables angle correction."""
        elements = {
            "columns": [],
            "walls": [],
            "beams": [
                {"x1": 0.0, "y1": 0.12, "x2": 17.0, "y2": -0.08,
                 "section": "B50X80", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(
            elements, grid_3x3, tolerance=1.5, no_angle_correct=True)
        assert report["angle_corrected_beams"] == 0
        assert len(report["angle_corrections"]) == 0


# ---------------------------------------------------------------------------
# TestNormalizeGridData
# ---------------------------------------------------------------------------

class TestNormalizeGridData:

    def test_canonical_format(self):
        """read_grid.py output: {grids: {x: [{label}], y: [{label}]}}."""
        raw = {
            "grids": {
                "x": [{"label": "A", "coordinate": 0.0}, {"label": "B", "coordinate": 8.5}],
                "y": [{"label": "1", "coordinate": 0.0}, {"label": "2", "coordinate": 6.0}],
                "x_bubble": "End",
                "y_bubble": "Start",
            }
        }
        result = _normalize_grid_data_for_bv(raw)
        assert "x" in result and "y" in result
        assert len(result["x"]) == 2
        assert result["x"][0]["label"] == "A"
        assert result["x"][0]["coordinate"] == 0.0
        assert result["y"][1]["label"] == "2"

    def test_affine_format(self):
        """affine_calibrate format: {x_grids: [{name}], y_grids: [{name}]}."""
        raw = {
            "x_grids": [{"name": "A", "coordinate": 0.0}, {"name": "B", "coordinate": 8.5}],
            "y_grids": [{"name": "1", "coordinate": 0.0}],
        }
        result = _normalize_grid_data_for_bv(raw)
        assert result["x"][0]["label"] == "A"
        assert result["x"][1]["coordinate"] == 8.5
        assert result["y"][0]["label"] == "1"

    def test_flat_passthrough(self):
        """Already flat format: {x: [{label}], y: [{label}]} — pass through."""
        raw = {
            "x": [{"label": "A", "coordinate": 0.0}],
            "y": [{"label": "1", "coordinate": 0.0}],
        }
        result = _normalize_grid_data_for_bv(raw)
        assert result is raw  # same object, no conversion

    def test_canonical_works_with_validate_beams(self):
        """End-to-end: canonical grid_data format works with validate_beams."""
        grid_data = {
            "grids": {
                "x": [{"label": "A", "coordinate": 0.0}, {"label": "B", "coordinate": 8.5}],
                "y": [{"label": "1", "coordinate": 0.0}, {"label": "2", "coordinate": 6.0}],
            }
        }
        normalized = _normalize_grid_data_for_bv(grid_data)
        elements = {
            "columns": [],
            "walls": [],
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 8.52, "y2": 0.02,
                 "section": "B50X80", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(elements, normalized, tolerance=1.5)
        beam = validated["beams"][0]
        assert beam["x2"] == 8.50
        assert beam["y2"] == 0.0


# ---------------------------------------------------------------------------
# TestBeamBeamSplit
# ---------------------------------------------------------------------------

class TestBeamBeamSplit:
    """Tests for beam-beam cross splitting (new feature)."""

    def test_two_beams_crossing(self):
        """Two beams crossing at (5,5) → each split into 2."""
        elements = {
            "beams": [
                # Horizontal beam
                {"x1": 0.0, "y1": 5.0, "x2": 10.0, "y2": 5.0,
                 "section": "B50X80", "floors": ["1F"]},
                # Vertical beam
                {"x1": 5.0, "y1": 0.0, "x2": 5.0, "y2": 10.0,
                 "section": "B40X60", "floors": ["1F"]},
            ],
            "columns": [],
            "walls": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_beams(elements, grid_data, 0.15)
        assert report["split_beams"] == 2
        assert len(elements["beams"]) == 4

    def test_beam_beam_no_floor_overlap(self):
        """Beams on different floors don't split each other."""
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 5.0, "x2": 10.0, "y2": 5.0,
                 "section": "B50X80", "floors": ["1F"]},
                {"x1": 5.0, "y1": 0.0, "x2": 5.0, "y2": 10.0,
                 "section": "B40X60", "floors": ["3F"]},
            ],
            "columns": [],
            "walls": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_beams(elements, grid_data, 0.15)
        assert report["split_beams"] == 0
        assert len(elements["beams"]) == 2

    def test_parallel_beams_no_split(self):
        """Parallel beams don't split each other."""
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
                {"x1": 0.0, "y1": 3.0, "x2": 10.0, "y2": 3.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "columns": [],
            "walls": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_beams(elements, grid_data, 0.15)
        assert report["split_beams"] == 0

    def test_beam_at_endpoint_no_split(self):
        """Beam ending at another beam's endpoint (T-junction at end) → no split."""
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0,
                 "section": "B50X80", "floors": ["1F"]},
                # Touches the first beam's start
                {"x1": 0.0, "y1": -5.0, "x2": 0.0, "y2": 0.0,
                 "section": "B40X60", "floors": ["1F"]},
            ],
            "columns": [],
            "walls": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_beams(elements, grid_data, 0.15)
        # The second beam meets the first at its endpoint (t=0.0), should not split
        assert report["split_beams"] == 0


# ---------------------------------------------------------------------------
# TestSplitAllWalls
# ---------------------------------------------------------------------------

class TestSplitAllWalls:
    """Tests for wall splitting at beams/columns/other walls."""

    def test_wall_split_at_beam_crossing(self):
        """Wall crossed by a beam → wall split into 2."""
        elements = {
            "walls": [
                # Vertical wall
                {"x1": 5.0, "y1": 0.0, "x2": 5.0, "y2": 10.0,
                 "section": "W25", "floors": ["1F"]},
            ],
            "beams": [
                # Horizontal beam crossing the wall at y=5
                {"x1": 0.0, "y1": 5.0, "x2": 10.0, "y2": 5.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "columns": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_walls(elements, grid_data, 0.15)
        assert report["wall_split_walls"] == 1
        assert len(elements["walls"]) == 2
        # Sub-walls should split at y=5
        coords_y = sorted([elements["walls"][0]["y2"], elements["walls"][1]["y1"]])
        assert abs(coords_y[0] - 5.0) < 0.01 or abs(coords_y[1] - 5.0) < 0.01

    def test_wall_split_at_column(self):
        """Wall with column on its midspan → wall split into 2."""
        elements = {
            "walls": [
                {"x1": 0.0, "y1": 5.0, "x2": 10.0, "y2": 5.0,
                 "section": "W30", "floors": ["1F"]},
            ],
            "beams": [],
            "columns": [
                {"grid_x": 5.0, "grid_y": 5.0, "floors": ["1F"]},
            ],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_walls(elements, grid_data, 0.15)
        assert report["wall_split_walls"] == 1
        assert len(elements["walls"]) == 2

    def test_wall_split_at_other_wall(self):
        """Two perpendicular walls crossing → each split."""
        elements = {
            "walls": [
                {"x1": 0.0, "y1": 5.0, "x2": 10.0, "y2": 5.0,
                 "section": "W30", "floors": ["1F"]},
                {"x1": 5.0, "y1": 0.0, "x2": 5.0, "y2": 10.0,
                 "section": "W25", "floors": ["1F"]},
            ],
            "beams": [],
            "columns": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_walls(elements, grid_data, 0.15)
        assert report["wall_split_walls"] == 2
        assert len(elements["walls"]) == 4

    def test_wall_no_split_no_floor_overlap(self):
        """Wall and beam on different floors → no split."""
        elements = {
            "walls": [
                {"x1": 5.0, "y1": 0.0, "x2": 5.0, "y2": 10.0,
                 "section": "W25", "floors": ["1F"]},
            ],
            "beams": [
                {"x1": 0.0, "y1": 5.0, "x2": 10.0, "y2": 5.0,
                 "section": "B50X80", "floors": ["3F"]},
            ],
            "columns": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_walls(elements, grid_data, 0.15)
        assert report["wall_split_walls"] == 0
        assert len(elements["walls"]) == 1

    def test_wall_split_at_parallel_beam_endpoint(self):
        """FWB beam runs parallel along a wall → wall split at FWB endpoints.

        Mimics A21: Wall at y=35.35 from x=-5 to x=40.
        FWB segment at y=35.35 from x=0 to x=8.5 (parallel to wall).
        Segment intersection finds nothing (parallel filter, dot>0.95).
        Endpoint projection should split wall at x=0 and x=8.5.
        """
        elements = {
            "walls": [
                {"x1": -5.0, "y1": 35.35, "x2": 40.0, "y2": 35.35,
                 "section": "W100", "floors": ["B3F"]},
            ],
            "beams": [
                # FWB running parallel along the wall
                {"x1": 0.0, "y1": 35.35, "x2": 8.5, "y2": 35.35,
                 "section": "FWB80X200", "floors": ["B3F"]},
            ],
            "columns": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_walls(elements, grid_data, 0.15)
        # Wall should be split at x=0 and x=8.5 → 3 sub-walls
        assert report["wall_split_walls"] == 1
        assert len(elements["walls"]) == 3
        # Verify sub-wall x1/x2 coordinates cover original range
        x_coords = sorted(
            set(w["x1"] for w in elements["walls"])
            | set(w["x2"] for w in elements["walls"])
        )
        assert abs(x_coords[0] - (-5.0)) < 0.01
        assert abs(x_coords[-1] - 40.0) < 0.01
        # Split points at 0 and 8.5
        assert any(abs(x - 0.0) < 0.01 for x in x_coords)
        assert any(abs(x - 8.5) < 0.01 for x in x_coords)

    def test_wall_split_at_perpendicular_beam_endpoint(self):
        """Perpendicular beam endpoint is ON the wall → wall split.

        Beam from (5, 0) to (5, 10). Wall from (0, 10) to (10, 10).
        Beam endpoint (5, 10) is at t_seg=1.0 for the beam (skipped by
        segment intersection), but projects onto wall at t=0.5.
        """
        elements = {
            "walls": [
                {"x1": 0.0, "y1": 10.0, "x2": 10.0, "y2": 10.0,
                 "section": "W25", "floors": ["1F"]},
            ],
            "beams": [
                {"x1": 5.0, "y1": 0.0, "x2": 5.0, "y2": 10.0,
                 "section": "B40X60", "floors": ["1F"]},
            ],
            "columns": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_walls(elements, grid_data, 0.15)
        assert report["wall_split_walls"] == 1
        assert len(elements["walls"]) == 2

    def test_wall_no_split_beam_endpoint_far(self):
        """Beam endpoint is >split_tolerance from wall → no split."""
        elements = {
            "walls": [
                {"x1": 0.0, "y1": 5.0, "x2": 10.0, "y2": 5.0,
                 "section": "W25", "floors": ["1F"]},
            ],
            "beams": [
                # Beam endpoint at (5, 4.5) — 0.5m from wall, > 0.15 tolerance
                {"x1": 5.0, "y1": 0.0, "x2": 5.0, "y2": 4.5,
                 "section": "B40X60", "floors": ["1F"]},
            ],
            "columns": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_walls(elements, grid_data, 0.15)
        assert report["wall_split_walls"] == 0
        assert len(elements["walls"]) == 1

    def test_wall_no_split_beam_endpoint_at_wall_end(self):
        """Beam endpoint projects near wall's own endpoint (t ≤ 0.02) → no split."""
        elements = {
            "walls": [
                # Wall from x=0 to x=10
                {"x1": 0.0, "y1": 5.0, "x2": 10.0, "y2": 5.0,
                 "section": "W25", "floors": ["1F"]},
            ],
            "beams": [
                # Beam endpoint at (0.1, 5) → t = 0.01 ≤ 0.02 → skip
                {"x1": 0.1, "y1": 0.0, "x2": 0.1, "y2": 5.0,
                 "section": "B40X60", "floors": ["1F"]},
            ],
            "columns": [],
        }
        grid_data = {"x": [], "y": []}
        elements, report = split_all_walls(elements, grid_data, 0.15)
        assert report["wall_split_walls"] == 0
        assert len(elements["walls"]) == 1


# ---------------------------------------------------------------------------
# TestNewPipelineOrder
# ---------------------------------------------------------------------------

class TestNewPipelineOrder:
    """Verify the new pipeline order (snap → split → angle) produces
    correct results that the old order (angle → snap → split) would get wrong."""

    def test_snap_before_angle_prevents_wrong_target(self):
        """Old pipeline: angle correction first would move beam Y away from
        the correct snap target. New pipeline: snap first locks the endpoint,
        then angle correction only fine-tunes post-split sub-beams.

        Scenario: beam endpoint is near a column at (8.5, 3.2). The beam
        has a slight tilt (~1.5°). Old pipeline would align Y to a grid line
        first, moving it away from the column. New pipeline snaps to column
        first, then angle correction only affects sub-beams if needed.
        """
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0},
                   {"label": "B", "coordinate": 8.50}],
            "y": [{"label": "1", "coordinate": 0.0},
                   {"label": "2", "coordinate": 6.00}],
        }
        elements = {
            "columns": [
                {"grid_x": 0.0, "grid_y": 3.2, "floors": ["1F"]},
                {"grid_x": 8.5, "grid_y": 3.2, "floors": ["1F"]},
            ],
            "walls": [],
            "beams": [
                # Beam connecting two columns at y=3.2, slight tilt
                {"x1": 0.02, "y1": 3.18, "x2": 8.48, "y2": 3.22,
                 "section": "B50X80", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(elements, grid_data, tolerance=1.5)
        beam = validated["beams"][0]
        # Should snap to columns at y=3.2, NOT angle-correct to grid y=0 or y=6
        assert beam["x1"] == 0.0
        assert beam["y1"] == 3.2
        assert beam["x2"] == 8.5
        assert beam["y2"] == 3.2

    def test_direction_x_skips_angle_correction(self):
        """Beam with direction='X' should NOT be angle-corrected even with deviation."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0},
                   {"label": "B", "coordinate": 8.50}],
            "y": [{"label": "1", "coordinate": 0.0},
                   {"label": "2", "coordinate": 6.00}],
        }
        elements = {
            "beams": [
                # ~1° deviation from horizontal, but direction="X"
                {"x1": 0.0, "y1": 5.90, "x2": 8.5, "y2": 6.10,
                 "section": "B50X80", "floors": ["1F"], "direction": "X"},
            ],
            "walls": [],
        }
        elements, angle_report = correct_angles(elements, grid_data, 2.0)
        assert len(angle_report) == 0
        # Coordinates unchanged
        assert elements["beams"][0]["y1"] == 5.90
        assert elements["beams"][0]["y2"] == 6.10

    def test_direction_y_skips_angle_correction(self):
        """Wall with direction='Y' should NOT be angle-corrected."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0}],
            "y": [{"label": "1", "coordinate": 0.0}],
        }
        elements = {
            "beams": [],
            "walls": [
                {"x1": 0.10, "y1": 0.0, "x2": -0.10, "y2": 6.0,
                 "section": "W25", "floors": ["1F"], "direction": "Y"},
            ],
        }
        elements, angle_report = correct_angles(elements, grid_data, 2.0)
        assert len(angle_report) == 0
        assert elements["walls"][0]["x1"] == 0.10

    def test_direction_empty_gets_corrected(self):
        """Beam with direction='' is corrected (same as before)."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0},
                   {"label": "B", "coordinate": 8.50}],
            "y": [{"label": "1", "coordinate": 0.0},
                   {"label": "2", "coordinate": 6.00}],
        }
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 5.90, "x2": 8.5, "y2": 6.10,
                 "section": "B50X80", "floors": ["1F"], "direction": ""},
            ],
            "walls": [],
        }
        elements, angle_report = correct_angles(elements, grid_data, 2.0)
        assert len(angle_report) == 1
        assert elements["beams"][0]["y1"] == 6.0
        assert elements["beams"][0]["y2"] == 6.0

    def test_direction_missing_gets_corrected(self):
        """Beam with no direction field is corrected (backward compat)."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0},
                   {"label": "B", "coordinate": 8.50}],
            "y": [{"label": "1", "coordinate": 0.0},
                   {"label": "2", "coordinate": 6.00}],
        }
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 5.90, "x2": 8.5, "y2": 6.10,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        elements, angle_report = correct_angles(elements, grid_data, 2.0)
        assert len(angle_report) == 1
        assert elements["beams"][0]["y1"] == 6.0

    def test_wall_split_in_pipeline(self):
        """Full pipeline includes wall splitting."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0},
                   {"label": "B", "coordinate": 8.50}],
            "y": [{"label": "1", "coordinate": 0.0},
                   {"label": "2", "coordinate": 6.00}],
        }
        elements = {
            "columns": [],
            "walls": [
                # Vertical wall
                {"x1": 4.0, "y1": 0.0, "x2": 4.0, "y2": 6.0,
                 "section": "W25", "floors": ["1F"]},
            ],
            "beams": [
                # Horizontal beam crossing the wall at x=4
                {"x1": 0.0, "y1": 3.0, "x2": 8.50, "y2": 3.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(elements, grid_data, tolerance=1.5)
        # Wall should be split at the beam crossing point
        assert report["wall_split_walls"] == 1
        assert len(validated["walls"]) == 2
        # Beam should also be split at the wall
        assert report["split_beams"] == 1
        assert len(validated["beams"]) == 2


class TestSnapWallsToBeams:
    """Tests for wall-to-beam snap (Step 4)."""

    def test_x_wall_snaps_to_x_beam(self):
        """X-direction wall offset 0.3m from X-direction beam → should snap."""
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 6.0, "x2": 8.5, "y2": 6.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [
                # Wall parallel to beam but offset 0.3m in Y
                {"x1": 0.0, "y1": 6.3, "x2": 8.5, "y2": 6.3,
                 "section": "W25", "floors": ["1F"]},
            ],
            "columns": [],
        }
        result, details = snap_walls_to_beams(elements, tolerance=1.0)
        assert len(details) == 1
        assert details[0]["distance"] == 0.3
        assert details[0]["direction"] == "X"
        assert details[0]["target_beam_section"] == "B50X80"
        # Wall Y should now match beam Y
        assert result["walls"][0]["y1"] == 6.0
        assert result["walls"][0]["y2"] == 6.0

    def test_y_wall_snaps_to_y_beam(self):
        """Y-direction wall offset 0.8m from Y-direction beam → should snap."""
        elements = {
            "beams": [
                {"x1": 8.5, "y1": 0.0, "x2": 8.5, "y2": 12.0,
                 "section": "B55X90", "floors": ["2F"]},
            ],
            "walls": [
                # Wall parallel to beam but offset 0.8m in X
                {"x1": 9.3, "y1": 0.0, "x2": 9.3, "y2": 12.0,
                 "section": "W30", "floors": ["2F"]},
            ],
            "columns": [],
        }
        result, details = snap_walls_to_beams(elements, tolerance=1.0)
        assert len(details) == 1
        assert details[0]["distance"] == 0.8
        assert details[0]["direction"] == "Y"
        # Wall X should now match beam X
        assert result["walls"][0]["x1"] == 8.5
        assert result["walls"][0]["x2"] == 8.5

    def test_no_variable_axis_overlap(self):
        """Wall with no overlapping beam in variable-axis → should NOT snap."""
        elements = {
            "beams": [
                # Beam from x=0 to x=8.5
                {"x1": 0.0, "y1": 6.0, "x2": 8.5, "y2": 6.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [
                # Wall from x=10 to x=15 — no overlap in X range
                {"x1": 10.0, "y1": 6.3, "x2": 15.0, "y2": 6.3,
                 "section": "W25", "floors": ["1F"]},
            ],
            "columns": [],
        }
        result, details = snap_walls_to_beams(elements, tolerance=1.0)
        assert len(details) == 0
        # Wall unchanged
        assert result["walls"][0]["y1"] == 6.3

    def test_wall_too_far_from_beam(self):
        """Wall > 1.0m from any beam → should NOT snap."""
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 6.0, "x2": 8.5, "y2": 6.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [
                # Wall 1.5m away — exceeds tolerance
                {"x1": 0.0, "y1": 7.5, "x2": 8.5, "y2": 7.5,
                 "section": "W25", "floors": ["1F"]},
            ],
            "columns": [],
        }
        result, details = snap_walls_to_beams(elements, tolerance=1.0)
        assert len(details) == 0
        assert result["walls"][0]["y1"] == 7.5

    def test_no_floor_overlap(self):
        """Wall with no floor overlap with any beam → should NOT snap."""
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 6.0, "x2": 8.5, "y2": 6.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [
                # Same position but different floor
                {"x1": 0.0, "y1": 6.3, "x2": 8.5, "y2": 6.3,
                 "section": "W25", "floors": ["3F"]},
            ],
            "columns": [],
        }
        result, details = snap_walls_to_beams(elements, tolerance=1.0)
        assert len(details) == 0
        assert result["walls"][0]["y1"] == 6.3

    def test_wall_already_aligned(self):
        """Wall within 0.01m of beam (already aligned) → should NOT snap."""
        elements = {
            "beams": [
                {"x1": 0.0, "y1": 6.0, "x2": 8.5, "y2": 6.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [
                {"x1": 0.0, "y1": 6.005, "x2": 8.5, "y2": 6.005,
                 "section": "W25", "floors": ["1F"]},
            ],
            "columns": [],
        }
        result, details = snap_walls_to_beams(elements, tolerance=1.0)
        assert len(details) == 0

    def test_perpendicular_wall_not_snapped(self):
        """Y-direction wall should NOT snap to X-direction beam."""
        elements = {
            "beams": [
                # Horizontal beam
                {"x1": 0.0, "y1": 6.0, "x2": 8.5, "y2": 6.0,
                 "section": "B50X80", "floors": ["1F"]},
            ],
            "walls": [
                # Vertical wall
                {"x1": 4.3, "y1": 0.0, "x2": 4.3, "y2": 12.0,
                 "section": "W25", "floors": ["1F"]},
            ],
            "columns": [],
        }
        result, details = snap_walls_to_beams(elements, tolerance=1.0)
        assert len(details) == 0

    def test_wall_beam_snap_in_full_pipeline(self):
        """Wall-beam snap integrates into validate_beams report."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0},
                   {"label": "B", "coordinate": 8.50}],
            "y": [{"label": "1", "coordinate": 0.0},
                   {"label": "2", "coordinate": 12.00}],
        }
        elements = {
            "columns": [
                {"grid_x": 0.0, "grid_y": 3.5, "floors": ["1F"]},
                {"grid_x": 8.5, "grid_y": 3.5, "floors": ["1F"]},
            ],
            "walls": [
                # Wall offset 0.3m from beam at y=3.5 (not on grid line)
                # Grid snap won't fix this because nearest grid is y=0 (3.5m away)
                # or y=12 (8.5m away) — both beyond useful snap
                {"x1": 0.0, "y1": 3.8, "x2": 8.5, "y2": 3.8,
                 "section": "W25", "floors": ["1F"]},
            ],
            "beams": [
                # Beam at y=3.5 connecting the two columns
                {"x1": 0.0, "y1": 3.5, "x2": 8.5, "y2": 3.5,
                 "section": "B50X80", "floors": ["1F"]},
            ],
        }
        validated, report = validate_beams(elements, grid_data, tolerance=1.5)
        assert "wall_beam_snaps" in report
        assert report["wall_beam_snaps"] == 1
        assert len(report["wall_beam_snap_details"]) == 1
        # Wall should be aligned to beam at y=3.5
        wall = validated["walls"][0]
        assert wall["y1"] == 3.5
        assert wall["y2"] == 3.5
