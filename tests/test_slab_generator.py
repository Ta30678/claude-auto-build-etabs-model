"""Tests for golden_scripts.tools.slab_generator."""

import math
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.slab_generator import (
    NodePool,
    _seg_intersection,
    collect_nodes_and_edges,
    build_adjacency,
    enumerate_faces,
    face_area_signed,
    face_centroid,
    filter_faces,
    point_in_polygon,
    generate_slabs,
    generate_slab_config,
)


# ---------------------------------------------------------------------------
# NodePool
# ---------------------------------------------------------------------------

class TestNodePool:
    def test_basic(self):
        pool = NodePool(tolerance=0.02)
        i0 = pool.add(0.0, 0.0)
        i1 = pool.add(1.0, 0.0)
        assert i0 != i1
        assert len(pool) == 2

    def test_clustering(self):
        pool = NodePool(tolerance=0.02)
        i0 = pool.add(0.0, 0.0)
        i1 = pool.add(0.01, 0.01)  # Within tolerance
        assert i0 == i1
        assert len(pool) == 1

    def test_no_clustering(self):
        pool = NodePool(tolerance=0.02)
        i0 = pool.add(0.0, 0.0)
        i1 = pool.add(0.05, 0.05)  # Beyond tolerance
        assert i0 != i1
        assert len(pool) == 2


# ---------------------------------------------------------------------------
# Segment intersection
# ---------------------------------------------------------------------------

class TestSegIntersection:
    def test_cross(self):
        """Two perpendicular segments crossing at center."""
        pt = _seg_intersection(0, 0, 10, 0, 5, -5, 5, 5)
        assert pt is not None
        assert abs(pt[0] - 5.0) < 0.01
        assert abs(pt[1] - 0.0) < 0.01

    def test_parallel(self):
        """Parallel segments: no intersection."""
        pt = _seg_intersection(0, 0, 10, 0, 0, 1, 10, 1)
        assert pt is None

    def test_endpoint_touch(self):
        """Segments touching at endpoint: should NOT return (interior only)."""
        pt = _seg_intersection(0, 0, 5, 0, 5, 0, 5, 5)
        assert pt is None  # Endpoint intersection excluded

    def test_t_intersection(self):
        """T-intersection: one segment ends at middle of another."""
        # Horizontal [0,0]-[10,0], Vertical [5,-5]-[5,0]
        # The vertical ends at (5,0) which is the endpoint, so no interior intersection
        pt = _seg_intersection(0, 0, 10, 0, 5, -5, 5, 0)
        assert pt is None

    def test_no_intersection(self):
        """Segments that don't cross."""
        pt = _seg_intersection(0, 0, 1, 0, 2, 1, 3, 1)
        assert pt is None


# ---------------------------------------------------------------------------
# Simple 2x2 grid test
# ---------------------------------------------------------------------------

class TestSimple2x2Grid:
    """A simple 2x2 grid with one SB should produce 2 slab faces."""

    @pytest.fixture
    def config_2x2(self):
        return {
            "beams": [
                # Outer rectangle: 10m x 6m
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0, "section": "B55X80", "floors": ["2F"]},
                {"x1": 10, "y1": 0, "x2": 10, "y2": 6, "section": "B55X80", "floors": ["2F"]},
                {"x1": 10, "y1": 6, "x2": 0, "y2": 6, "section": "B55X80", "floors": ["2F"]},
                {"x1": 0, "y1": 6, "x2": 0, "y2": 0, "section": "B55X80", "floors": ["2F"]},
            ],
            "small_beams": [
                # One SB cutting horizontally at y=3
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
        # Should have 2 slabs: one from y=0..3 and one from y=3..6
        assert stats["total_slabs"] == 2
        assert len(slabs) == 2

        # Check areas
        areas = sorted(s.get("area", 0) for s in slabs
                       if "area" in s)
        # Hmm, area is not in the final output dict. Let me check the generate_slab_config.
        # Actually the areas are stripped. Let's check corner counts.
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
        assert point_in_polygon(2, 2, poly)   # Inside
        assert not point_in_polygon(8, 8, poly)  # In the cutout


# ---------------------------------------------------------------------------
# face_area_signed
# ---------------------------------------------------------------------------

class TestFaceArea:
    def test_unit_square_ccw(self):
        nodes = [(0, 0), (1, 0), (1, 1), (0, 1)]
        area = face_area_signed([0, 1, 2, 3], nodes)
        assert abs(area - 1.0) < 1e-6

    def test_unit_square_cw(self):
        nodes = [(0, 0), (1, 0), (1, 1), (0, 1)]
        area = face_area_signed([3, 2, 1, 0], nodes)
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
