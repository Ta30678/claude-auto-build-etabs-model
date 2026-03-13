"""Tests for golden_scripts.tools.beam_validate.

All tests use mock data — no ETABS connection required.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.beam_validate import validate_beams, build_beam_targets


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
        """Beam A -> column, Beam B -> Beam A, Beam C -> Beam B: multi-round chain."""
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
                # Beam B: from grid B/1 to mid-span of A, roughly at (4.25, 0.05)
                # Actually let's make B span grid B/1 to C/1
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
        # Beam A should snap to (0.0, 0.0) and (8.50, 0.0)
        a = validated["beams"][0]
        assert a["x1"] == 0.0 and a["y1"] == 0.0
        assert a["x2"] == 8.50 and a["y2"] == 0.0
        # Beam B should snap to (8.50, 0.0) and (17.00, 0.0)
        b = validated["beams"][1]
        assert b["x1"] == 8.50 and b["y1"] == 0.0
        assert b["x2"] == 17.00 and b["y2"] == 0.0
        # Beam C end (12.75, 0.08) should snap to Beam B segment at y=0.0
        c = validated["beams"][2]
        assert abs(c["y2"] - 0.0) < 0.01


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
        """Verify report has all required keys."""
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
