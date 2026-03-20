"""Tests for gs_05_walls wall splitting logic.

All tests use mock data — no ETABS connection required.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.modeling.gs_05_walls import (
    _segment_intersection,
    _point_on_segment_t,
    split_wall_at_intersections,
)


# ---------------------------------------------------------------------------
# _segment_intersection
# ---------------------------------------------------------------------------

class TestSegmentIntersection:

    def test_perpendicular_crossing(self):
        """Two perpendicular segments crossing at (5, 5)."""
        result = _segment_intersection(0, 5, 10, 5, 5, 0, 5, 10)
        assert result is not None
        x, y, t_a, t_b = result
        assert abs(x - 5.0) < 1e-6
        assert abs(y - 5.0) < 1e-6
        assert abs(t_a - 0.5) < 1e-6
        assert abs(t_b - 0.5) < 1e-6

    def test_parallel_no_intersection(self):
        """Two parallel segments → None."""
        result = _segment_intersection(0, 0, 10, 0, 0, 1, 10, 1)
        assert result is None

    def test_t_junction(self):
        """Perpendicular beam ending at wall midpoint."""
        result = _segment_intersection(0, 5, 10, 5, 5, 0, 5, 5)
        assert result is not None
        x, y, t_a, t_b = result
        assert abs(x - 5.0) < 1e-6
        assert abs(y - 5.0) < 1e-6

    def test_no_overlap(self):
        """Segments that don't reach each other → None."""
        result = _segment_intersection(0, 0, 3, 0, 5, -2, 5, 2)
        assert result is None

    def test_endpoint_intersection(self):
        """Segments meeting at endpoint."""
        result = _segment_intersection(0, 0, 5, 0, 5, 0, 5, 10)
        assert result is not None
        x, y, _, _ = result
        assert abs(x - 5.0) < 1e-6
        assert abs(y - 0.0) < 1e-6


# ---------------------------------------------------------------------------
# _point_on_segment_t
# ---------------------------------------------------------------------------

class TestPointOnSegmentT:

    def test_midpoint(self):
        """Point at midpoint of horizontal segment."""
        t = _point_on_segment_t(5.0, 0.0, 0.0, 0.0, 10.0, 0.0)
        assert t is not None
        assert abs(t - 0.5) < 1e-6

    def test_point_near_segment(self):
        """Point 0.1m from segment → returns t."""
        t = _point_on_segment_t(5.0, 0.1, 0.0, 0.0, 10.0, 0.0)
        assert t is not None
        assert abs(t - 0.5) < 1e-6

    def test_point_too_far(self):
        """Point 0.3m from segment with 0.15 tolerance → None."""
        t = _point_on_segment_t(5.0, 0.3, 0.0, 0.0, 10.0, 0.0, perp_tol=0.15)
        assert t is None

    def test_point_beyond_segment(self):
        """Point beyond segment endpoint → None."""
        t = _point_on_segment_t(12.0, 0.0, 0.0, 0.0, 10.0, 0.0)
        assert t is None

    def test_zero_length_segment(self):
        """Zero-length segment → None."""
        t = _point_on_segment_t(5.0, 0.0, 5.0, 0.0, 5.0, 0.0)
        assert t is None


# ---------------------------------------------------------------------------
# split_wall_at_intersections
# ---------------------------------------------------------------------------

class TestSplitWallAtIntersections:

    def test_wall_split_by_perpendicular_beam(self):
        """Horizontal wall split by vertical beam at midpoint."""
        wall = {"x1": 0, "y1": 5, "x2": 10, "y2": 5, "floors": ["1F"]}
        beams = [
            {"x1": 5, "y1": 0, "x2": 5, "y2": 10,
             "section": "B50X80", "floors": ["1F"]},
        ]
        segs = split_wall_at_intersections(wall, beams, [], [])
        assert len(segs) == 2
        # First segment: (0,5) → (5,5)
        assert abs(segs[0][0] - 0.0) < 1e-4
        assert abs(segs[0][2] - 5.0) < 1e-4
        # Second segment: (5,5) → (10,5)
        assert abs(segs[1][0] - 5.0) < 1e-4
        assert abs(segs[1][2] - 10.0) < 1e-4

    def test_wall_split_by_column(self):
        """Horizontal wall split at column center."""
        wall = {"x1": 0, "y1": 5, "x2": 10, "y2": 5, "floors": ["1F"]}
        columns = [
            {"x1": 4.7, "y1": 4.7, "x2": 5.3, "y2": 5.3, "floors": ["1F"]},
        ]
        segs = split_wall_at_intersections(wall, [], columns, [])
        assert len(segs) == 2
        # Cut at column center x=5.0
        assert abs(segs[0][2] - 5.0) < 1e-4
        assert abs(segs[1][0] - 5.0) < 1e-4

    def test_wall_split_by_other_wall(self):
        """Horizontal wall split by perpendicular wall."""
        wall = {"x1": 0, "y1": 5, "x2": 10, "y2": 5, "floors": ["1F"]}
        other_walls = [
            {"x1": 3, "y1": 0, "x2": 3, "y2": 10, "floors": ["1F"]},
        ]
        segs = split_wall_at_intersections(wall, [], [], other_walls)
        assert len(segs) == 2
        assert abs(segs[0][2] - 3.0) < 1e-4

    def test_wall_no_split_no_intersections(self):
        """Wall with no intersecting elements → single segment."""
        wall = {"x1": 0, "y1": 5, "x2": 10, "y2": 5, "floors": ["1F"]}
        segs = split_wall_at_intersections(wall, [], [], [])
        assert len(segs) == 1
        assert abs(segs[0][0] - 0.0) < 1e-4
        assert abs(segs[0][2] - 10.0) < 1e-4

    def test_wall_no_split_different_floors(self):
        """Beam on different floor → no cut."""
        wall = {"x1": 0, "y1": 5, "x2": 10, "y2": 5, "floors": ["1F"]}
        beams = [
            {"x1": 5, "y1": 0, "x2": 5, "y2": 10,
             "section": "B50X80", "floors": ["3F"]},
        ]
        segs = split_wall_at_intersections(wall, beams, [], [])
        assert len(segs) == 1

    def test_wall_multiple_cuts(self):
        """Wall split at 3 points → 4 segments."""
        wall = {"x1": 0, "y1": 5, "x2": 12, "y2": 5, "floors": ["1F"]}
        beams = [
            {"x1": 3, "y1": 0, "x2": 3, "y2": 10,
             "section": "B40X60", "floors": ["1F"]},
            {"x1": 6, "y1": 0, "x2": 6, "y2": 10,
             "section": "B40X60", "floors": ["1F"]},
            {"x1": 9, "y1": 0, "x2": 9, "y2": 10,
             "section": "B40X60", "floors": ["1F"]},
        ]
        segs = split_wall_at_intersections(wall, beams, [], [])
        assert len(segs) == 4
        # Check cut points
        assert abs(segs[0][2] - 3.0) < 1e-4
        assert abs(segs[1][2] - 6.0) < 1e-4
        assert abs(segs[2][2] - 9.0) < 1e-4

    def test_wall_cut_near_endpoint_ignored(self):
        """Cut within T_MIN of wall endpoint → not applied (avoid zero-length)."""
        wall = {"x1": 0, "y1": 5, "x2": 10, "y2": 5, "floors": ["1F"]}
        beams = [
            # Beam at x=0.05 — within 1% of wall start → ignored
            {"x1": 0.05, "y1": 0, "x2": 0.05, "y2": 10,
             "section": "B40X60", "floors": ["1F"]},
            # Beam at x=5 — valid cut
            {"x1": 5, "y1": 0, "x2": 5, "y2": 10,
             "section": "B40X60", "floors": ["1F"]},
        ]
        segs = split_wall_at_intersections(wall, beams, [], [])
        # Only the x=5 cut applies
        assert len(segs) == 2

    def test_wall_split_by_parallel_beam_endpoint(self):
        """Parallel beam endpoint projects onto wall → cut at that point."""
        wall = {"x1": 0, "y1": 5, "x2": 10, "y2": 5, "floors": ["1F"]}
        beams = [
            # Parallel beam ending at x=4 on same axis
            {"x1": 0, "y1": 5, "x2": 4, "y2": 5,
             "section": "B40X60", "floors": ["1F"]},
        ]
        segs = split_wall_at_intersections(wall, beams, [], [])
        # x=4 is a valid cut, x=0 is at wall start → ignored
        assert len(segs) == 2
        assert abs(segs[0][2] - 4.0) < 1e-4

    def test_vertical_wall_split(self):
        """Vertical wall split by horizontal beam."""
        wall = {"x1": 5, "y1": 0, "x2": 5, "y2": 12, "floors": ["2F"]}
        beams = [
            {"x1": 0, "y1": 6, "x2": 10, "y2": 6,
             "section": "B50X80", "floors": ["2F"]},
        ]
        segs = split_wall_at_intersections(wall, beams, [], [])
        assert len(segs) == 2
        # Cut at y=6
        assert abs(segs[0][3] - 6.0) < 1e-4
        assert abs(segs[1][1] - 6.0) < 1e-4

    def test_zero_length_wall(self):
        """Zero-length wall → returned as-is."""
        wall = {"x1": 5, "y1": 5, "x2": 5, "y2": 5, "floors": ["1F"]}
        segs = split_wall_at_intersections(wall, [], [], [])
        assert len(segs) == 1

    def test_duplicate_cuts_deduplicated(self):
        """Multiple elements at same point → single cut."""
        wall = {"x1": 0, "y1": 5, "x2": 10, "y2": 5, "floors": ["1F"]}
        beams = [
            # Two beams both crossing at x=5
            {"x1": 5, "y1": 0, "x2": 5, "y2": 10,
             "section": "B40X60", "floors": ["1F"]},
        ]
        columns = [
            # Column also at x=5
            {"x1": 4.7, "y1": 4.7, "x2": 5.3, "y2": 5.3, "floors": ["1F"]},
        ]
        segs = split_wall_at_intersections(wall, beams, columns, [])
        # Both produce cut at t=0.5 → deduplicated → 2 segments
        assert len(segs) == 2
