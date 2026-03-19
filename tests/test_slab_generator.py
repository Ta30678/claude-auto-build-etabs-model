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
    parse_slide_floor_ranges,
    filter_segments_by_range,
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
             "floors": ["2F"], "area": 15.0},
            {"corners": [[0, 0], [5, 0], [5, 3], [0, 3]],
             "floors": ["B3F"], "area": 15.0},
        ]
        entries, sections = generate_slab_config(
            slabs, slab_thickness=15, raft_thickness=100,
            foundation_floor="B3F")
        assert len(entries) == 2
        assert entries[0]["section"] == "S15"
        assert entries[1]["section"] == "FS100"
        assert sections["slab"] == [15]
        assert sections["raft"] == [100]

    def test_fs_only_at_foundation_floor(self):
        """FS should only be assigned to the foundation floor (B3F),
        not to other B*F floors like B2F or B1F."""
        slabs = [
            {"corners": [[0, 0], [5, 0], [5, 3], [0, 3]],
             "floors": ["B3F", "B2F", "B1F"], "area": 15.0},
        ]
        entries, sections = generate_slab_config(
            slabs, slab_thickness=15, raft_thickness=100,
            foundation_floor="B3F")
        # Should split into FS at B3F + S at B2F, B1F
        assert len(entries) == 2
        fs_entries = [e for e in entries if e["section"].startswith("FS")]
        s_entries = [e for e in entries if e["section"].startswith("S")]
        assert len(fs_entries) == 1
        assert fs_entries[0]["floors"] == ["B3F"]
        assert len(s_entries) == 1
        assert set(s_entries[0]["floors"]) == {"B2F", "B1F"}


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

    def test_single_rectangle_not_filtered(self):
        """A single rectangle > 100 m² should NOT be filtered out."""
        config = {
            "beams": [
                {"x1": 0, "y1": 0, "x2": 20, "y2": 0,
                 "section": "B55X80", "floors": ["2F"]},
                {"x1": 20, "y1": 0, "x2": 20, "y2": 8,
                 "section": "B55X80", "floors": ["2F"]},
                {"x1": 20, "y1": 8, "x2": 0, "y2": 8,
                 "section": "B55X80", "floors": ["2F"]},
                {"x1": 0, "y1": 8, "x2": 0, "y2": 0,
                 "section": "B55X80", "floors": ["2F"]},
            ],
            "small_beams": [],
            "columns": [],
            "walls": [],
            "stories": [{"name": "2F", "height": 3.3}],
            "sections": {"frame": ["B55X80"]},
        }
        # Area = 20 * 8 = 160 m² (> 100)
        updated, stats = generate_slabs(config, slab_thickness=15)
        slabs = updated.get("slabs", [])
        assert len(slabs) == 1
        assert slabs[0]["section"] == "S15"

    def test_substructure_extension_slabs(self):
        """Extension area (substructure wider than superstructure) must have slabs."""
        config = {
            "beams": [
                # Tower (0-10, 0-6) — all floors
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0,
                 "section": "B55X80", "floors": ["B3F", "B2F", "B1F", "1F", "2F"]},
                {"x1": 10, "y1": 0, "x2": 10, "y2": 6,
                 "section": "B55X80", "floors": ["B3F", "B2F", "B1F", "1F", "2F"]},
                {"x1": 10, "y1": 6, "x2": 0, "y2": 6,
                 "section": "B55X80", "floors": ["B3F", "B2F", "B1F", "1F", "2F"]},
                {"x1": 0, "y1": 6, "x2": 0, "y2": 0,
                 "section": "B55X80", "floors": ["B3F", "B2F", "B1F", "1F", "2F"]},
                # Extension (0-10, -5 to 0) — only B*F
                {"x1": 0, "y1": -5, "x2": 10, "y2": -5,
                 "section": "FB55X120", "floors": ["B3F", "B2F", "B1F"]},
                {"x1": 10, "y1": -5, "x2": 10, "y2": 0,
                 "section": "FB55X120", "floors": ["B3F", "B2F", "B1F"]},
                {"x1": 0, "y1": -5, "x2": 0, "y2": 0,
                 "section": "FB55X120", "floors": ["B3F", "B2F", "B1F"]},
            ],
            "small_beams": [],
            "columns": [],
            "walls": [],
            "stories": [
                {"name": "B3F", "height": 4.0},
                {"name": "B2F", "height": 4.0},
                {"name": "B1F", "height": 4.0},
                {"name": "1F", "height": 4.2},
                {"name": "2F", "height": 3.3},
            ],
            "sections": {"frame": ["B55X80", "FB55X120"]},
        }
        updated, stats = generate_slabs(config, slab_thickness=15, raft_thickness=100)
        slabs = updated.get("slabs", [])

        # Extension area slabs must exist
        ext_slabs = []
        for s in slabs:
            for cx, cy in s["corners"]:
                if cy < -0.1:
                    ext_slabs.append(s)
                    break
        assert len(ext_slabs) >= 1, "Extension area should have at least 1 slab"

        # FS only at B3F
        fs_slabs = [s for s in slabs if s["section"].startswith("FS")]
        for fs in fs_slabs:
            assert fs["floors"] == ["B3F"], \
                f"FS slab should only be at B3F, got {fs['floors']}"

        # B2F and B1F should have S sections, not FS
        for s in slabs:
            if s["section"].startswith("FS"):
                assert "B2F" not in s["floors"]
                assert "B1F" not in s["floors"]

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


# ---------------------------------------------------------------------------
# parse_slide_floor_ranges
# ---------------------------------------------------------------------------

class TestParseSlideFloorRanges:
    def test_single_floor(self):
        result = parse_slide_floor_ranges("B3F")
        assert len(result) == 1
        assert result[0] == ("B3F", frozenset({"B3F"}))

    def test_multi_range(self):
        result = parse_slide_floor_ranges("B3F; B2F~B1F; 1F~2F; 3F~14F; R1F~R3F")
        assert len(result) == 5
        assert result[0] == ("B3F", frozenset({"B3F"}))
        assert result[1] == ("B2F~B1F", frozenset({"B2F", "B1F"}))
        assert result[2] == ("1F~2F", frozenset({"1F", "2F"}))
        assert result[3][0] == "3F~14F"
        assert len(result[3][1]) == 12  # 3F through 14F
        assert result[4] == ("R1F~R3F", frozenset({"R1F", "R2F", "R3F"}))

    def test_whitespace_handling(self):
        result = parse_slide_floor_ranges("  B3F ;  1F~2F  ")
        assert len(result) == 2
        assert result[0][1] == frozenset({"B3F"})
        assert result[1][1] == frozenset({"1F", "2F"})

    def test_empty_string(self):
        result = parse_slide_floor_ranges("")
        assert result == []

    def test_none_input(self):
        result = parse_slide_floor_ranges(None)
        assert result == []

    def test_overlapping_detection(self):
        with pytest.raises(ValueError, match="overlap"):
            parse_slide_floor_ranges("1F~3F; 2F~5F")


# ---------------------------------------------------------------------------
# filter_segments_by_range
# ---------------------------------------------------------------------------

class TestFilterSegmentsByRange:
    def test_exact_match(self):
        segments = [
            (0, 0, 10, 0, {"1F", "2F"}),
            (0, 0, 0, 6, {"3F"}),
        ]
        result = filter_segments_by_range(segments, frozenset({"1F", "2F"}))
        assert len(result) == 1
        assert result[0][4] == {"1F", "2F"}

    def test_partial_overlap(self):
        """Segment floors = {1F, 2F, 3F}, filter = {2F, 3F} → floors narrowed."""
        segments = [
            (0, 0, 10, 0, {"1F", "2F", "3F"}),
        ]
        result = filter_segments_by_range(segments, frozenset({"2F", "3F"}))
        assert len(result) == 1
        assert result[0][4] == {"2F", "3F"}

    def test_no_overlap(self):
        segments = [
            (0, 0, 10, 0, {"1F"}),
            (0, 0, 0, 6, {"2F"}),
        ]
        result = filter_segments_by_range(segments, frozenset({"3F"}))
        assert len(result) == 0

    def test_mixed(self):
        """Some segments match, some don't."""
        segments = [
            (0, 0, 10, 0, {"B3F", "B2F", "B1F", "1F", "2F"}),
            (0, 3, 10, 3, {"2F"}),
            (5, 0, 5, 6, {"3F"}),
        ]
        result = filter_segments_by_range(segments, frozenset({"1F", "2F"}))
        assert len(result) == 2
        # First: {B3F,B2F,B1F,1F,2F} ∩ {1F,2F} = {1F,2F}
        assert result[0][4] == {"1F", "2F"}
        # Second: {2F} ∩ {1F,2F} = {2F}
        assert result[1][4] == {"2F"}


# ---------------------------------------------------------------------------
# Per-range slab generation (integration)
# ---------------------------------------------------------------------------

class TestPerRangeSlabGeneration:
    """Test per-slide-range slab generation (no cross-range merge)."""

    @pytest.fixture
    def shared_sub_config(self):
        """共構 case: B*F beams cover full site (0-10, -5 to 6),
        upper beams cover tower only (0-10, 0-6)."""
        return {
            "beams": [
                # Tower beams (all floors)
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0,
                 "section": "B55X80", "floors": ["B3F", "B2F", "B1F", "1F", "2F"]},
                {"x1": 10, "y1": 0, "x2": 10, "y2": 6,
                 "section": "B55X80", "floors": ["B3F", "B2F", "B1F", "1F", "2F"]},
                {"x1": 10, "y1": 6, "x2": 0, "y2": 6,
                 "section": "B55X80", "floors": ["B3F", "B2F", "B1F", "1F", "2F"]},
                {"x1": 0, "y1": 6, "x2": 0, "y2": 0,
                 "section": "B55X80", "floors": ["B3F", "B2F", "B1F", "1F", "2F"]},
                # Extension beams (B*F only)
                {"x1": 0, "y1": -5, "x2": 10, "y2": -5,
                 "section": "FB55X120", "floors": ["B3F", "B2F", "B1F"]},
                {"x1": 10, "y1": -5, "x2": 10, "y2": 0,
                 "section": "FB55X120", "floors": ["B3F", "B2F", "B1F"]},
                {"x1": 0, "y1": -5, "x2": 0, "y2": 0,
                 "section": "FB55X120", "floors": ["B3F", "B2F", "B1F"]},
            ],
            "small_beams": [],
            "columns": [],
            "walls": [],
            "stories": [
                {"name": "B3F", "height": 4.0},
                {"name": "B2F", "height": 4.0},
                {"name": "B1F", "height": 4.0},
                {"name": "1F", "height": 4.2},
                {"name": "2F", "height": 3.3},
            ],
            "sections": {"frame": ["B55X80", "FB55X120"]},
        }

    def test_no_cross_range_merge(self, shared_sub_config):
        """With slide_floor_ranges, B*F slabs cover full site, upper slabs cover tower only."""
        ranges = parse_slide_floor_ranges("B3F; B2F~B1F; 1F~2F")
        updated, stats = generate_slabs(
            shared_sub_config, slab_thickness=15, raft_thickness=100,
            slide_floor_ranges=ranges)
        slabs = updated["slabs"]

        # B3F should have slabs in the extension area (y < 0)
        b3f_slabs = [s for s in slabs if "B3F" in s["floors"]]
        b3f_has_extension = any(
            any(c[1] < -0.1 for c in s["corners"])
            for s in b3f_slabs
        )
        assert b3f_has_extension, \
            "B3F slabs should cover extension area (full site)"

        # Upper floors (1F, 2F) should NOT have extension area slabs
        upper_slabs = [s for s in slabs
                       if ("1F" in s["floors"] or "2F" in s["floors"])
                       and "B3F" not in s["floors"]]
        upper_has_extension = any(
            any(c[1] < -0.1 for c in s["corners"])
            for s in upper_slabs
        )
        assert not upper_has_extension, \
            "Upper floor slabs should not extend into B*F-only area"

    def test_extension_area_in_own_range(self, shared_sub_config):
        """B*F range sees extension segments, produces FS at B3F."""
        ranges = parse_slide_floor_ranges("B3F; B2F~B1F; 1F~2F")
        updated, stats = generate_slabs(
            shared_sub_config, slab_thickness=15, raft_thickness=100,
            slide_floor_ranges=ranges)
        slabs = updated["slabs"]

        fs_slabs = [s for s in slabs if s["section"].startswith("FS")]
        assert len(fs_slabs) >= 1, "Should have at least 1 FS slab"
        for fs in fs_slabs:
            assert fs["floors"] == ["B3F"], \
                f"FS should only be at B3F, got {fs['floors']}"

    def test_no_mixed_sub_super_floors(self, shared_sub_config):
        """No slab should have floors spanning sub and superstructure."""
        ranges = parse_slide_floor_ranges("B3F; B2F~B1F; 1F~2F")
        updated, stats = generate_slabs(
            shared_sub_config, slab_thickness=15, raft_thickness=100,
            slide_floor_ranges=ranges)
        slabs = updated["slabs"]

        for s in slabs:
            floors = set(s["floors"])
            has_sub = any(f.startswith("B") for f in floors)
            has_super = any(not f.startswith("B") for f in floors)
            if s["section"].startswith("FS"):
                continue  # FS split is handled by generate_slab_config
            assert not (has_sub and has_super), \
                f"Slab should not mix sub/super floors: {s['floors']}"

    def test_fallback_without_ranges(self, shared_sub_config):
        """Without slide_floor_ranges, uses legacy grouping (backward compatible)."""
        updated, stats = generate_slabs(
            shared_sub_config, slab_thickness=15, raft_thickness=100)
        slabs = updated["slabs"]
        # Should still produce slabs (legacy behavior)
        assert len(slabs) > 0
        assert stats["floor_groups"] >= 1
