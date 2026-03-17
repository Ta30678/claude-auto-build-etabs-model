"""Tests for golden_scripts.tools.slab_generator."""

import math
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.slab_generator import (
    _coord_key,
    _project_point_on_segment,
    compute_intersections,
    build_beam_segments,
    build_point_adjacency,
    walk_slab_polygons,
    face_area_signed,
    face_centroid,
    filter_slabs,
    point_in_polygon,
    generate_slabs,
    generate_slab_config,
    group_segments_by_floor,
)


# ---------------------------------------------------------------------------
# Coord key
# ---------------------------------------------------------------------------

class TestCoordKey:
    def test_deterministic(self):
        k1 = _coord_key(1.00001, 2.00002)
        k2 = _coord_key(1.00001, 2.00002)
        assert k1 == k2

    def test_insertion_order_independent(self):
        """Same coordinates from different computation paths give same key."""
        k1 = _coord_key(5.0, 3.0)
        k2 = _coord_key(2.5 + 2.5, 1.5 * 2)
        assert k1 == k2

    def test_distinct_for_1mm_difference(self):
        k1 = _coord_key(0.0, 0.0)
        k2 = _coord_key(0.001, 0.001)
        assert k1 != k2  # 1mm apart should be distinct

    def test_merge_sub_0_05mm(self):
        """Points differing by <0.05mm merge (below rounding threshold)."""
        k1 = _coord_key(5.00001, 3.00002)
        k2 = _coord_key(5.00003, 3.00004)
        assert k1 == k2  # both round to (5.0, 3.0)


# ---------------------------------------------------------------------------
# Exact intersections
# ---------------------------------------------------------------------------

class TestExactIntersections:
    def test_crossing(self):
        """Two perpendicular segments crossing at center."""
        segments = [
            (0, 0, 10, 0, {"2F"}),
            (5, -5, 5, 5, {"2F"}),
        ]
        seg_points = compute_intersections(segments)
        # Segment 0 should have: start + intersection + end
        pts_0 = seg_points[0]
        assert len(pts_0) == 3
        assert abs(pts_0[1][1] - 5.0) < 0.001
        assert abs(pts_0[1][2] - 0.0) < 0.001

    def test_t_junction_exact(self):
        """T-junction: vertical segment ends exactly at horizontal interior."""
        segments = [
            (0, 0, 10, 0, {"2F"}),
            (5, -5, 5, 0, {"2F"}),  # ends at (5,0) on seg 0
        ]
        seg_points = compute_intersections(segments)
        pts_0 = seg_points[0]
        assert len(pts_0) == 3  # split at (5, 0)
        assert abs(pts_0[1][1] - 5.0) < 0.001
        assert abs(pts_0[1][2] - 0.0) < 0.001

    def test_t_junction_near(self):
        """T-junction: short segment ends 10cm from horizontal, not crossing it."""
        # Segment 1 goes from (5, 0.1) upward — does NOT cross seg 0
        segments = [
            (0, 0, 10, 0, {"2F"}),
            (5, 0.1, 5, 5, {"2F"}),  # starts 10cm above seg 0, goes up
        ]
        seg_points = compute_intersections(segments)
        # Segment 0 should be split at (5, 0) — projection of (5, 0.1)
        pts_0 = seg_points[0]
        assert len(pts_0) == 3
        assert abs(pts_0[1][1] - 5.0) < 0.001
        assert abs(pts_0[1][2] - 0.0) < 0.001
        # Segment 1 start should be snapped to (5, 0)
        pts_1 = seg_points[1]
        assert abs(pts_1[0][1] - 5.0) < 0.001
        assert abs(pts_1[0][2] - 0.0) < 0.001

    def test_no_intersection_parallel(self):
        """Non-intersecting parallel segments."""
        segments = [
            (0, 0, 10, 0, {"2F"}),
            (0, 1, 10, 1, {"2F"}),
        ]
        seg_points = compute_intersections(segments)
        assert len(seg_points[0]) == 2  # only endpoints
        assert len(seg_points[1]) == 2

    def test_near_endpoint_crossing(self):
        """Crossing very near an endpoint should be detected."""
        segments = [
            (0, 0, 10, 0, {"2F"}),
            (0.05, -5, 0.05, 5, {"2F"}),  # crosses near x=0 of seg 0
        ]
        seg_points = compute_intersections(segments)
        pts_0 = seg_points[0]
        # Should have a split near x=0.05
        assert len(pts_0) >= 3
        interior_pts = [p for p in pts_0 if 0.001 < p[0] < 0.999]
        assert len(interior_pts) >= 1
        assert abs(interior_pts[0][1] - 0.05) < 0.001


# ---------------------------------------------------------------------------
# Walk slab polygons
# ---------------------------------------------------------------------------

class TestWalkSlabPolygons:
    def test_simple_rectangle(self):
        """Simple rectangle → 1 inner slab + 1 outer face."""
        segments = [
            (0, 0, 10, 0, {"2F"}),
            (10, 0, 10, 6, {"2F"}),
            (10, 6, 0, 6, {"2F"}),
            (0, 6, 0, 0, {"2F"}),
        ]
        seg_points = compute_intersections(segments)
        beam_segs = build_beam_segments(segments, seg_points)
        adj, _ = build_point_adjacency(beam_segs)
        polygons = walk_slab_polygons(adj)

        ccw = [p for p in polygons if face_area_signed(p) > 0]
        assert len(ccw) == 1
        assert abs(abs(face_area_signed(ccw[0])) - 60.0) < 0.1

    def test_grid_with_sb(self):
        """Rectangle + 1 horizontal SB → 2 inner slabs."""
        segments = [
            (0, 0, 10, 0, {"2F"}),
            (10, 0, 10, 6, {"2F"}),
            (10, 6, 0, 6, {"2F"}),
            (0, 6, 0, 0, {"2F"}),
            (0, 3, 10, 3, {"2F"}),
        ]
        seg_points = compute_intersections(segments)
        beam_segs = build_beam_segments(segments, seg_points)
        adj, _ = build_point_adjacency(beam_segs)
        polygons = walk_slab_polygons(adj)

        ccw = [p for p in polygons if face_area_signed(p) > 0]
        assert len(ccw) == 2
        areas = sorted(abs(face_area_signed(p)) for p in ccw)
        assert abs(areas[0] - 30.0) < 0.1
        assert abs(areas[1] - 30.0) < 0.1

    def test_cross_beams_4_slabs(self):
        """Rectangle + H + V SBs → 4 inner slabs."""
        segments = [
            (0, 0, 10, 0, {"2F"}),
            (10, 0, 10, 8, {"2F"}),
            (10, 8, 0, 8, {"2F"}),
            (0, 8, 0, 0, {"2F"}),
            (0, 4, 10, 4, {"2F"}),
            (5, 0, 5, 8, {"2F"}),
        ]
        seg_points = compute_intersections(segments)
        beam_segs = build_beam_segments(segments, seg_points)
        adj, _ = build_point_adjacency(beam_segs)
        polygons = walk_slab_polygons(adj)

        ccw = [p for p in polygons if face_area_signed(p) > 0]
        assert len(ccw) == 4
        areas = sorted(abs(face_area_signed(p)) for p in ccw)
        for a in areas:
            assert abs(a - 20.0) < 0.1  # each quadrant = 5*4 = 20


# ---------------------------------------------------------------------------
# Corner precision
# ---------------------------------------------------------------------------

class TestCornerPrecision:
    def test_corners_within_1mm(self):
        """All slab corners should be within 1mm of exact beam intersections."""
        config = {
            "beams": [
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0, "section": "B55X80", "floors": ["2F"]},
                {"x1": 10, "y1": 0, "x2": 10, "y2": 6, "section": "B55X80", "floors": ["2F"]},
                {"x1": 10, "y1": 6, "x2": 0, "y2": 6, "section": "B55X80", "floors": ["2F"]},
                {"x1": 0, "y1": 6, "x2": 0, "y2": 0, "section": "B55X80", "floors": ["2F"]},
            ],
            "small_beams": [
                {"x1": 0, "y1": 3, "x2": 10, "y2": 3, "section": "SB30X50", "floors": ["2F"]},
            ],
            "columns": [],
            "walls": [],
            "stories": [{"name": "2F", "height": 3.3}],
            "sections": {},
        }
        updated, stats = generate_slabs(config)
        slabs = updated["slabs"]

        expected_corners = {
            (0, 0), (10, 0), (0, 3), (10, 3), (0, 6), (10, 6)
        }

        for slab in slabs:
            for cx, cy in slab["corners"]:
                min_dist = min(
                    math.hypot(cx - ex, cy - ey)
                    for ex, ey in expected_corners
                )
                assert min_dist < 0.001, \
                    f"Corner ({cx}, {cy}) is {min_dist*1000:.1f}mm from nearest expected"


# ---------------------------------------------------------------------------
# Diagonal beam
# ---------------------------------------------------------------------------

class TestDiagonalBeam:
    def test_diagonal_creates_triangles(self):
        """A diagonal beam in a rectangle creates 2 triangular slabs."""
        segments = [
            (0, 0, 10, 0, {"2F"}),
            (10, 0, 10, 6, {"2F"}),
            (10, 6, 0, 6, {"2F"}),
            (0, 6, 0, 0, {"2F"}),
            (0, 0, 10, 6, {"2F"}),  # diagonal
        ]
        seg_points = compute_intersections(segments)
        beam_segs = build_beam_segments(segments, seg_points)
        adj, _ = build_point_adjacency(beam_segs)
        polygons = walk_slab_polygons(adj)

        ccw = [p for p in polygons if face_area_signed(p) > 0]
        assert len(ccw) == 2
        # Total area = 60 m²
        total = sum(abs(face_area_signed(p)) for p in ccw)
        assert abs(total - 60.0) < 0.1
        # Both are triangles
        corner_counts = sorted(len(p) for p in ccw)
        assert corner_counts == [3, 3]


# ---------------------------------------------------------------------------
# Simple 2x2 grid test (integration, via generate_slabs)
# ---------------------------------------------------------------------------

class TestSimple2x2Grid:
    """A simple 2x2 grid with one SB should produce 2 slab faces."""

    @pytest.fixture
    def config_2x2(self):
        return {
            "beams": [
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0, "section": "B55X80", "floors": ["2F"]},
                {"x1": 10, "y1": 0, "x2": 10, "y2": 6, "section": "B55X80", "floors": ["2F"]},
                {"x1": 10, "y1": 6, "x2": 0, "y2": 6, "section": "B55X80", "floors": ["2F"]},
                {"x1": 0, "y1": 6, "x2": 0, "y2": 0, "section": "B55X80", "floors": ["2F"]},
            ],
            "small_beams": [
                {"x1": 0, "y1": 3, "x2": 10, "y2": 3, "section": "SB30X50", "floors": ["2F"]},
            ],
            "columns": [
                {"grid_x": 0, "grid_y": 0, "section": "C80X80", "floors": ["2F"]},
                {"grid_x": 10, "grid_y": 0, "section": "C80X80", "floors": ["2F"]},
                {"grid_x": 0, "grid_y": 6, "section": "C80X80", "floors": ["2F"]},
                {"grid_x": 10, "grid_y": 6, "section": "C80X80", "floors": ["2F"]},
            ],
            "walls": [],
            "stories": [{"name": "2F", "height": 3.3}],
            "sections": {"frame": ["B55X80", "SB30X50", "C80X80"]},
        }

    def test_generates_2_slabs(self, config_2x2):
        updated, stats = generate_slabs(config_2x2, slab_thickness=15)
        slabs = updated.get("slabs", [])
        assert stats["total_slabs"] == 2
        assert len(slabs) == 2

        for s in slabs:
            assert len(s["corners"]) >= 3
            assert s["section"] == "S15"
            assert s["floors"] == ["2F"]


# ---------------------------------------------------------------------------
# 2x2 grid with cross SB → 4 faces
# ---------------------------------------------------------------------------

class TestCrossBeams:
    """A rectangle with one H and one V SB should produce 4 slab faces."""

    @pytest.fixture
    def config_cross(self):
        return {
            "beams": [
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0, "section": "B55X80", "floors": ["2F"]},
                {"x1": 10, "y1": 0, "x2": 10, "y2": 8, "section": "B55X80", "floors": ["2F"]},
                {"x1": 10, "y1": 8, "x2": 0, "y2": 8, "section": "B55X80", "floors": ["2F"]},
                {"x1": 0, "y1": 8, "x2": 0, "y2": 0, "section": "B55X80", "floors": ["2F"]},
            ],
            "small_beams": [
                {"x1": 0, "y1": 4, "x2": 10, "y2": 4, "section": "SB30X50", "floors": ["2F"]},
                {"x1": 5, "y1": 0, "x2": 5, "y2": 8, "section": "SB30X50", "floors": ["2F"]},
            ],
            "columns": [],
            "walls": [],
            "stories": [{"name": "2F", "height": 3.3}],
            "sections": {"frame": ["B55X80", "SB30X50"]},
        }

    def test_generates_4_slabs(self, config_cross):
        updated, stats = generate_slabs(config_cross, slab_thickness=15)
        slabs = updated.get("slabs", [])
        assert stats["total_slabs"] == 4


# ---------------------------------------------------------------------------
# point_in_polygon
# ---------------------------------------------------------------------------

class TestPointInPolygon:
    def test_inside(self):
        poly = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert point_in_polygon(5, 5, poly)

    def test_outside(self):
        poly = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert not point_in_polygon(15, 5, poly)

    def test_l_shape(self):
        poly = [(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)]
        assert point_in_polygon(2, 2, poly)   # inside
        assert not point_in_polygon(8, 8, poly)  # in the cutout


# ---------------------------------------------------------------------------
# face_area_signed
# ---------------------------------------------------------------------------

class TestFaceArea:
    def test_unit_square_ccw(self):
        polygon = [(0, 0), (1, 0), (1, 1), (0, 1)]
        area = face_area_signed(polygon)
        assert abs(area - 1.0) < 1e-6

    def test_unit_square_cw(self):
        polygon = [(0, 1), (1, 1), (1, 0), (0, 0)]
        area = face_area_signed(polygon)
        assert abs(area - (-1.0)) < 1e-6


# ---------------------------------------------------------------------------
# Generate slab config
# ---------------------------------------------------------------------------

class TestGenerateSlabConfig:
    def test_basic(self):
        slabs = [
            {"corners": [[0, 0], [5, 0], [5, 3], [0, 3]],
             "floors": ["2F"], "is_foundation": False, "area": 15.0},
            {"corners": [[0, 0], [5, 0], [5, 3], [0, 3]],
             "floors": ["B3F"], "is_foundation": True, "area": 15.0},
        ]
        entries, sections = generate_slab_config(slabs, slab_thickness=15, raft_thickness=100)
        assert len(entries) == 2
        assert entries[0]["section"] == "S15"
        assert entries[1]["section"] == "FS100"
        assert sections["slab"] == [15]
        assert sections["raft"] == [100]


# ---------------------------------------------------------------------------
# Floor grouping
# ---------------------------------------------------------------------------

class TestGroupSegmentsByFloor:
    def test_single_floor(self):
        """All segments on same floor → 1 group."""
        segments = [
            (0, 0, 10, 0, {"2F"}),
            (10, 0, 10, 6, {"2F"}),
            (10, 6, 0, 6, {"2F"}),
            (0, 6, 0, 0, {"2F"}),
        ]
        groups = group_segments_by_floor(segments)
        assert len(groups) == 1
        assert frozenset({"2F"}) in [g[0] for g in groups]

    def test_two_floors_same_segments(self):
        """Two floors with identical segments → 1 group with both floors."""
        segments = [
            (0, 0, 10, 0, {"1F", "2F"}),
            (10, 0, 10, 6, {"1F", "2F"}),
            (10, 6, 0, 6, {"1F", "2F"}),
            (0, 6, 0, 0, {"1F", "2F"}),
        ]
        groups = group_segments_by_floor(segments)
        assert len(groups) == 1
        assert "1F" in groups[0][0] and "2F" in groups[0][0]

    def test_two_floors_different_sbs(self):
        """Two floors with different SBs → 2 groups."""
        segments = [
            (0, 0, 10, 0, {"1F", "2F"}),  # shared beam
            (10, 0, 10, 6, {"1F", "2F"}),
            (10, 6, 0, 6, {"1F", "2F"}),
            (0, 6, 0, 0, {"1F", "2F"}),
            (0, 3, 10, 3, {"2F"}),  # SB only on 2F
        ]
        groups = group_segments_by_floor(segments)
        assert len(groups) == 2
        floor_sets = {g[0] for g in groups}
        assert frozenset({"1F"}) in floor_sets
        assert frozenset({"2F"}) in floor_sets


# ---------------------------------------------------------------------------
# Per-floor slab generation (integration)
# ---------------------------------------------------------------------------

class TestPerFloorSlabGeneration:
    """Different floors with different SB layouts produce different slabs."""

    def test_floor_specific_sbs(self):
        """1F: no SB → 1 slab, 2F: 1 SB → 2 slabs."""
        config = {
            "beams": [
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0,
                 "section": "B55X80", "floors": ["1F", "2F"]},
                {"x1": 10, "y1": 0, "x2": 10, "y2": 6,
                 "section": "B55X80", "floors": ["1F", "2F"]},
                {"x1": 10, "y1": 6, "x2": 0, "y2": 6,
                 "section": "B55X80", "floors": ["1F", "2F"]},
                {"x1": 0, "y1": 6, "x2": 0, "y2": 0,
                 "section": "B55X80", "floors": ["1F", "2F"]},
            ],
            "small_beams": [
                {"x1": 0, "y1": 3, "x2": 10, "y2": 3,
                 "section": "SB30X50", "floors": ["2F"]},
            ],
            "columns": [],
            "walls": [],
            "stories": [
                {"name": "1F", "height": 4.2},
                {"name": "2F", "height": 3.2},
            ],
            "sections": {"frame": ["B55X80", "SB30X50"]},
        }
        updated, stats = generate_slabs(config, slab_thickness=15)
        slabs = updated["slabs"]

        # 1F: 1 slab (full rectangle), 2F: 2 slabs (split by SB)
        # Total: 3 slab entries
        assert stats["total_slabs"] == 3
        assert stats["floor_groups"] == 2

        slabs_1f = [s for s in slabs
                     if "1F" in s["floors"] and "2F" not in s["floors"]]
        slabs_2f = [s for s in slabs
                     if "2F" in s["floors"] and "1F" not in s["floors"]]

        assert len(slabs_1f) == 1  # One full rectangle
        assert len(slabs_2f) == 2  # Two halves split by SB

        # 1F slab has 4 corners (rectangle), 2F slabs have 4 corners each
        assert len(slabs_1f[0]["corners"]) == 4
        for s in slabs_2f:
            assert len(s["corners"]) == 4

    def test_no_all_floors_fallback(self):
        """No slab should get ALL floors when segments are floor-specific."""
        config = {
            "beams": [
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0,
                 "section": "B55X80", "floors": ["1F", "2F", "3F"]},
                {"x1": 10, "y1": 0, "x2": 10, "y2": 6,
                 "section": "B55X80", "floors": ["1F", "2F", "3F"]},
                {"x1": 10, "y1": 6, "x2": 0, "y2": 6,
                 "section": "B55X80", "floors": ["1F", "2F", "3F"]},
                {"x1": 0, "y1": 6, "x2": 0, "y2": 0,
                 "section": "B55X80", "floors": ["1F", "2F", "3F"]},
            ],
            "small_beams": [
                {"x1": 0, "y1": 3, "x2": 10, "y2": 3,
                 "section": "SB30X50", "floors": ["2F"]},
                {"x1": 5, "y1": 0, "x2": 5, "y2": 6,
                 "section": "SB30X50", "floors": ["3F"]},
            ],
            "columns": [],
            "walls": [],
            "stories": [
                {"name": "1F", "height": 4.2},
                {"name": "2F", "height": 3.2},
                {"name": "3F", "height": 3.2},
            ],
            "sections": {"frame": ["B55X80", "SB30X50"]},
        }
        updated, stats = generate_slabs(config, slab_thickness=15)
        slabs = updated["slabs"]

        all_story_names = {"1F", "2F", "3F"}
        for slab in slabs:
            assert set(slab["floors"]) != all_story_names, \
                f"Slab should not have ALL floors: {slab['floors']}"

        # 3 groups: {1F}, {2F}, {3F} — each with different SB layout
        assert stats["floor_groups"] == 3

    def test_shared_floors_same_layout(self):
        """Floors sharing identical layout are grouped and share slabs."""
        config = {
            "beams": [
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0,
                 "section": "B55X80", "floors": ["3F", "4F", "5F"]},
                {"x1": 10, "y1": 0, "x2": 10, "y2": 6,
                 "section": "B55X80", "floors": ["3F", "4F", "5F"]},
                {"x1": 10, "y1": 6, "x2": 0, "y2": 6,
                 "section": "B55X80", "floors": ["3F", "4F", "5F"]},
                {"x1": 0, "y1": 6, "x2": 0, "y2": 0,
                 "section": "B55X80", "floors": ["3F", "4F", "5F"]},
            ],
            "small_beams": [
                {"x1": 0, "y1": 3, "x2": 10, "y2": 3,
                 "section": "SB30X50", "floors": ["3F", "4F", "5F"]},
            ],
            "columns": [],
            "walls": [],
            "stories": [
                {"name": "3F", "height": 3.2},
                {"name": "4F", "height": 3.2},
                {"name": "5F", "height": 3.2},
            ],
            "sections": {"frame": ["B55X80", "SB30X50"]},
        }
        updated, stats = generate_slabs(config, slab_thickness=15)
        slabs = updated["slabs"]

        # All 3 floors see identical segments → 1 group
        assert stats["floor_groups"] == 1
        # 2 slabs, each with floors=["3F", "4F", "5F"]
        assert stats["total_slabs"] == 2
        for s in slabs:
            assert set(s["floors"]) == {"3F", "4F", "5F"}
