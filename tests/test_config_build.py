"""Tests for golden_scripts.tools.config_build."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.config_build import (
    point_in_polygon,
    point_to_segment_distance,
    point_in_or_near_polygon,
    polygon_area,
    is_non_rectangular,
    strip_columns,
    strip_beams,
    strip_walls,
    filter_by_outline,
    has_r2f_or_above,
    replicate_rooftop,
    replicate_rooftop_sb_slabs,
    build_config,
)


# ── Geometry ───────────────────────────────────────────────────

class TestPointInPolygon:
    def test_inside_square(self):
        poly = [[0, 0], [10, 0], [10, 10], [0, 10]]
        assert point_in_polygon(5, 5, poly) is True

    def test_outside_square(self):
        poly = [[0, 0], [10, 0], [10, 10], [0, 10]]
        assert point_in_polygon(15, 5, poly) is False

    def test_inside_l_shape(self):
        poly = [[0, 0], [10, 0], [10, 10], [5, 10], [5, 20], [0, 20]]
        assert point_in_polygon(3, 15, poly) is True
        assert point_in_polygon(8, 5, poly) is True

    def test_outside_l_shape_notch(self):
        poly = [[0, 0], [10, 0], [10, 10], [5, 10], [5, 20], [0, 20]]
        assert point_in_polygon(8, 15, poly) is False


class TestPointToSegmentDistance:
    def test_point_on_segment(self):
        assert point_to_segment_distance(5, 0, 0, 0, 10, 0) < 1e-10

    def test_point_perpendicular(self):
        d = point_to_segment_distance(5, 3, 0, 0, 10, 0)
        assert abs(d - 3.0) < 1e-10

    def test_point_beyond_endpoint(self):
        d = point_to_segment_distance(12, 0, 0, 0, 10, 0)
        assert abs(d - 2.0) < 1e-10

    def test_zero_length_segment(self):
        d = point_to_segment_distance(3, 4, 0, 0, 0, 0)
        assert abs(d - 5.0) < 1e-10


class TestPointInOrNearPolygon:
    def test_inside(self):
        poly = [[0, 0], [10, 0], [10, 10], [0, 10]]
        assert point_in_or_near_polygon(5, 5, poly) is True

    def test_on_edge(self):
        poly = [[0, 0], [10, 0], [10, 10], [0, 10]]
        assert point_in_or_near_polygon(5, 0, poly, tolerance=0.01) is True

    def test_near_edge(self):
        poly = [[0, 0], [10, 0], [10, 10], [0, 10]]
        assert point_in_or_near_polygon(5, -0.005, poly, tolerance=0.01) is True

    def test_far_outside(self):
        poly = [[0, 0], [10, 0], [10, 10], [0, 10]]
        assert point_in_or_near_polygon(20, 20, poly, tolerance=0.01) is False


class TestPolygonArea:
    def test_unit_square(self):
        poly = [[0, 0], [1, 0], [1, 1], [0, 1]]
        assert abs(polygon_area(poly) - 1.0) < 1e-10

    def test_rectangle(self):
        poly = [[0, 0], [10, 0], [10, 5], [0, 5]]
        assert abs(polygon_area(poly) - 50.0) < 1e-10

    def test_l_shape(self):
        # Bottom 10x10 + top 5x10 = 100 + 50 = 150
        poly = [[0, 0], [10, 0], [10, 10], [5, 10], [5, 20], [0, 20]]
        assert abs(polygon_area(poly) - 150.0) < 1e-10


class TestIsNonRectangular:
    def test_rectangle(self):
        poly = [[0, 0], [10, 0], [10, 5], [0, 5]]
        assert is_non_rectangular(poly) is False

    def test_l_shape(self):
        poly = [[0, 0], [10, 0], [10, 10], [5, 10], [5, 20], [0, 20]]
        assert is_non_rectangular(poly) is True

    def test_empty(self):
        assert is_non_rectangular([]) is False
        assert is_non_rectangular(None) is False


# ── Element Stripping ──────────────────────────────────────────

class TestStripElements:
    def test_strip_columns(self):
        cols = [{"grid_x": 0, "grid_y": 0, "section": "C90X90",
                 "floors": ["B3F", "1F"], "page_num": 3}]
        result, dropped = strip_columns(cols)
        assert dropped == 0
        assert len(result) == 1
        assert "page_num" not in result[0]
        assert result[0]["section"] == "C90X90"
        assert result[0]["floors"] == ["B3F", "1F"]

    def test_strip_columns_preserves_offgrid(self):
        """Off-grid columns (間柱) should pass through without coordinate modification."""
        cols = [
            {"grid_x": 4.2, "grid_y": 7.35, "section": "C60X60",
             "floors": ["1F", "2F"]},
        ]
        grid_info = {
            "grids": {
                "x": [{"label": "1", "coordinate": 0},
                      {"label": "2", "coordinate": 8.4}],
                "y": [{"label": "A", "coordinate": 0},
                      {"label": "B", "coordinate": 6.0}],
            },
        }
        result, dropped = strip_columns(cols, grid_info)
        assert dropped == 0
        assert len(result) == 1
        assert result[0]["grid_x"] == 4.2
        assert result[0]["grid_y"] == 7.35

    def test_strip_columns_normalizes_fields(self):
        """x1/y1 keys should be normalized to grid_x/grid_y."""
        cols = [
            {"x1": 3.456, "y1": 8.789, "section": "C50X50",
             "floors": ["1F"], "page_num": 2},
        ]
        result, dropped = strip_columns(cols)
        assert dropped == 0
        assert len(result) == 1
        assert result[0]["grid_x"] == 3.46  # rounded to 2 decimals
        assert result[0]["grid_y"] == 8.79
        assert result[0]["section"] == "C50X50"
        assert "page_num" not in result[0]
        assert "x1" not in result[0]
        assert "y1" not in result[0]

    def test_strip_beams(self):
        beams = [{"x1": 0, "y1": 0, "x2": 10, "y2": 0,
                  "section": "B55X80", "floors": ["1F"],
                  "page_num": 3, "direction": "X"}]
        result = strip_beams(beams)
        assert len(result) == 1
        assert "page_num" not in result[0]
        assert "direction" not in result[0]
        assert result[0]["section"] == "B55X80"

    def test_strip_walls_preserves_diaphragm(self):
        walls = [{"x1": 0, "y1": 0, "x2": 0, "y2": 10,
                  "section": "W25", "floors": ["B3F"],
                  "is_diaphragm_wall": True, "page_num": 1, "direction": "Y"}]
        result = strip_walls(walls)
        assert result[0]["is_diaphragm_wall"] is True
        assert "page_num" not in result[0]
        assert "direction" not in result[0]

    def test_strip_walls_no_diaphragm(self):
        walls = [{"x1": 0, "y1": 0, "x2": 0, "y2": 10,
                  "section": "W25", "floors": ["1F"], "page_num": 1}]
        result = strip_walls(walls)
        assert "is_diaphragm_wall" not in result[0]

    def test_floors_are_copies(self):
        """Stripping should create independent copies of floors lists."""
        cols = [{"grid_x": 0, "grid_y": 0, "section": "C90X90",
                 "floors": ["1F", "2F"]}]
        result, _ = strip_columns(cols)
        result[0]["floors"].append("3F")
        assert "3F" not in cols[0]["floors"]


# ── Building Outline Filtering ─────────────────────────────────

class TestFilterByOutline:
    def test_rectangular_outline_no_filtering(self):
        cols = [{"grid_x": 5, "grid_y": 5, "section": "C90X90", "floors": ["1F"]}]
        outline = [[0, 0], [10, 0], [10, 10], [0, 10]]
        fc, fb, fw, warns = filter_by_outline(cols, [], [], outline)
        assert len(fc) == 1
        assert len(warns) == 0

    def test_l_shape_removes_column_in_notch(self):
        outline = [[0, 0], [10, 0], [10, 10], [5, 10], [5, 20], [0, 20]]
        cols = [
            {"grid_x": 3, "grid_y": 5, "section": "C90X90", "floors": ["1F"]},
            {"grid_x": 8, "grid_y": 15, "section": "C90X90", "floors": ["1F"]},
        ]
        fc, fb, fw, warns = filter_by_outline(cols, [], [], outline)
        assert len(fc) == 1
        assert fc[0]["grid_x"] == 3
        assert len(warns) == 1

    def test_beam_both_outside_removed(self):
        outline = [[0, 0], [10, 0], [10, 10], [5, 10], [5, 20], [0, 20]]
        beams = [
            {"x1": 8, "y1": 12, "x2": 8, "y2": 18,
             "section": "B55X80", "floors": ["1F"]},
        ]
        fc, fb, fw, warns = filter_by_outline([], beams, [], outline)
        assert len(fb) == 0
        assert len(warns) == 1

    def test_beam_one_inside_kept(self):
        outline = [[0, 0], [10, 0], [10, 10], [5, 10], [5, 20], [0, 20]]
        beams = [
            {"x1": 3, "y1": 15, "x2": 8, "y2": 15,
             "section": "B55X80", "floors": ["1F"]},
        ]
        fc, fb, fw, warns = filter_by_outline([], beams, [], outline)
        assert len(fb) == 1

    def test_no_outline(self):
        cols = [{"grid_x": 5, "grid_y": 5, "section": "C90X90", "floors": ["1F"]}]
        fc, fb, fw, warns = filter_by_outline(cols, [], [], None)
        assert len(fc) == 1


# ── Rooftop Replication ────────────────────────────────────────

class TestRooftopReplication:
    @pytest.fixture
    def stories_with_rooftop(self):
        return [
            {"name": "B3F", "height": 3.6},
            {"name": "1F", "height": 4.2},
            {"name": "2F", "height": 3.2},
            {"name": "RF", "height": 3.2},
            {"name": "R1F", "height": 3.2},
            {"name": "R2F", "height": 3.2},
            {"name": "R3F", "height": 3.2},
            {"name": "PRF", "height": 1.5},
        ]

    @pytest.fixture
    def core_area(self):
        return {"x_range": [5, 15], "y_range": [5, 15]}

    def test_has_r2f(self, stories_with_rooftop):
        assert has_r2f_or_above(stories_with_rooftop) is True

    def test_no_r2f(self):
        stories = [
            {"name": "1F", "height": 4.2},
            {"name": "RF", "height": 3.2},
            {"name": "R1F", "height": 3.2},
            {"name": "PRF", "height": 1.5},
        ]
        assert has_r2f_or_above(stories) is False

    def test_column_in_core_gets_rooftop(self, stories_with_rooftop, core_area):
        """Core column: Phase A gives R1F, Phase B gives R2F+R3F (not PRF)."""
        cols = [{"grid_x": 10, "grid_y": 10, "section": "C90X90",
                 "floors": ["B3F", "1F", "2F", "RF"]}]
        replicate_rooftop(cols, [], [], stories_with_rooftop, core_area)
        assert "R1F" in cols[0]["floors"]
        assert "R2F" in cols[0]["floors"]
        assert "R3F" in cols[0]["floors"]
        assert "PRF" not in cols[0]["floors"]

    def test_column_outside_core_gets_no_rooftop(self, stories_with_rooftop, core_area):
        """Non-core column: Phase A skips R1F (column extends above via +1 rule)."""
        cols = [{"grid_x": 1, "grid_y": 1, "section": "C90X90",
                 "floors": ["B3F", "1F", "2F", "RF"]}]
        replicate_rooftop(cols, [], [], stories_with_rooftop, core_area)
        assert "R1F" not in cols[0]["floors"]
        assert "R2F" not in cols[0]["floors"]
        assert "R3F" not in cols[0]["floors"]
        assert "PRF" not in cols[0]["floors"]

    def test_beam_in_core_gets_rooftop(self, stories_with_rooftop, core_area):
        """Core beam: Phase A gives R1F, Phase B gives R2F+R3F+PRF."""
        beams = [{"x1": 6, "y1": 10, "x2": 14, "y2": 10,
                  "section": "B55X80", "floors": ["1F", "2F", "RF"]}]
        replicate_rooftop([], beams, [], stories_with_rooftop, core_area)
        assert "R1F" in beams[0]["floors"]
        assert "R2F" in beams[0]["floors"]
        assert "R3F" in beams[0]["floors"]
        assert "PRF" in beams[0]["floors"]

    def test_wall_in_core_gets_rooftop(self, stories_with_rooftop, core_area):
        """Core wall: Phase A gives R1F, Phase B gives R2F+R3F (not PRF)."""
        walls = [{"x1": 10, "y1": 6, "x2": 10, "y2": 14,
                  "section": "W25", "floors": ["1F", "2F", "RF"]}]
        replicate_rooftop([], [], walls, stories_with_rooftop, core_area)
        assert "R1F" in walls[0]["floors"]
        assert "R2F" in walls[0]["floors"]
        assert "R3F" in walls[0]["floors"]
        assert "PRF" not in walls[0]["floors"]

    def test_wall_outside_core_no_r1f(self, stories_with_rooftop, core_area):
        """Non-core wall: Phase A skips R1F (wall extends above via +1 rule)."""
        walls = [{"x1": 1, "y1": 1, "x2": 1, "y2": 3,
                  "section": "W25", "floors": ["1F", "2F", "RF"]}]
        replicate_rooftop([], [], walls, stories_with_rooftop, core_area)
        assert "R1F" not in walls[0]["floors"]
        assert "R2F" not in walls[0]["floors"]

    def test_small_beam_in_core_gets_rooftop(self, stories_with_rooftop, core_area):
        """Core SB: Phase A gives R1F, Phase B gives R2F+R3F+PRF."""
        sbs = [{"x1": 6, "y1": 10, "x2": 14, "y2": 10,
                "section": "SB30X50", "floors": ["2F", "RF"]}]
        replicate_rooftop_sb_slabs(sbs, None, stories_with_rooftop, core_area)
        assert "R1F" in sbs[0]["floors"]
        assert "R2F" in sbs[0]["floors"]
        assert "R3F" in sbs[0]["floors"]
        assert "PRF" in sbs[0]["floors"]

    def test_sb_without_top_floor_no_rooftop_phase_b(self, stories_with_rooftop, core_area):
        """Core SB at 1F only (not top_floor=2F) → Phase B should NOT add R2F+."""
        sbs = [{"x1": 6, "y1": 10, "x2": 14, "y2": 10,
                "section": "SB30X50", "floors": ["1F"]}]
        replicate_rooftop_sb_slabs(sbs, None, stories_with_rooftop, core_area)
        # Phase A: 1F ≠ top_floor (2F), so no R1F
        assert "R1F" not in sbs[0]["floors"]
        # Phase B: top_floor not in floors → skip
        assert "R2F" not in sbs[0]["floors"]
        assert "R3F" not in sbs[0]["floors"]
        assert "PRF" not in sbs[0]["floors"]

    def test_foundation_sb_no_rooftop(self, stories_with_rooftop, core_area):
        """Foundation SB (B3F only) should NOT get rooftop floors."""
        sbs = [{"x1": 6, "y1": 10, "x2": 14, "y2": 10,
                "section": "FSB30X50", "floors": ["B3F"]}]
        replicate_rooftop_sb_slabs(sbs, None, stories_with_rooftop, core_area)
        assert "R1F" not in sbs[0]["floors"]
        assert "R2F" not in sbs[0]["floors"]
        assert "PRF" not in sbs[0]["floors"]

    def test_no_duplicate_floors(self, stories_with_rooftop, core_area):
        cols = [{"grid_x": 10, "grid_y": 10, "section": "C90X90",
                 "floors": ["B3F", "1F", "2F", "RF", "R1F"]}]
        replicate_rooftop(cols, [], [], stories_with_rooftop, core_area)
        assert cols[0]["floors"].count("R1F") == 1

    def test_beam_one_endpoint_outside_core_gets_r1f(self, stories_with_rooftop, core_area):
        """Non-core beam: Phase A gives R1F, Phase B skips (one endpoint outside)."""
        beams = [{"x1": 1, "y1": 1, "x2": 10, "y2": 10,
                  "section": "B55X80", "floors": ["1F", "2F", "RF"]}]
        replicate_rooftop([], beams, [], stories_with_rooftop, core_area)
        assert "R1F" in beams[0]["floors"]
        assert "R2F" not in beams[0]["floors"]
        assert "R3F" not in beams[0]["floors"]
        assert "PRF" not in beams[0]["floors"]

    def test_non_core_column_no_r1f(self, stories_with_rooftop, core_area):
        """Non-core column with top_floor → no R1F (column extends above via +1 rule)."""
        cols = [{"grid_x": 1, "grid_y": 1, "section": "C60X60",
                 "floors": ["1F", "2F"]}]
        replicate_rooftop(cols, [], [], stories_with_rooftop, core_area)
        assert "R1F" not in cols[0]["floors"]
        assert "R2F" not in cols[0]["floors"]
        assert "R3F" not in cols[0]["floors"]

    def test_r1f_full_copy_beam(self, stories_with_rooftop, core_area):
        """Non-core beam with top_floor → gets R1F only, not R2F+."""
        beams = [{"x1": 1, "y1": 1, "x2": 3, "y2": 1,
                  "section": "B40X60", "floors": ["1F", "2F"]}]
        replicate_rooftop([], beams, [], stories_with_rooftop, core_area)
        assert "R1F" in beams[0]["floors"]
        assert "R2F" not in beams[0]["floors"]
        assert "PRF" not in beams[0]["floors"]

    def test_no_r1f_in_stories(self):
        """Stories without R1F → no R1F replication."""
        stories = [
            {"name": "1F", "height": 4.2},
            {"name": "2F", "height": 3.2},
            {"name": "RF", "height": 3.2},
            {"name": "R2F", "height": 3.2},
            {"name": "PRF", "height": 1.5},
        ]
        core = {"x_range": [0, 20], "y_range": [0, 20]}
        cols = [{"grid_x": 10, "grid_y": 10, "section": "C90X90",
                 "floors": ["1F", "2F"]}]
        replicate_rooftop(cols, [], [], stories, core)
        assert "R1F" not in cols[0]["floors"]

    def test_r1f_only_no_r2f(self):
        """Stories with R1F but no R2F+ → R1F full copy still happens."""
        stories = [
            {"name": "1F", "height": 4.2},
            {"name": "2F", "height": 3.2},
            {"name": "RF", "height": 3.2},
            {"name": "R1F", "height": 3.2},
            {"name": "PRF", "height": 1.5},
        ]
        cols = [{"grid_x": 1, "grid_y": 1, "section": "C90X90",
                 "floors": ["1F", "2F"]}]
        replicate_rooftop(cols, [], [], stories, None)
        assert "R1F" in cols[0]["floors"]
        assert "PRF" not in cols[0]["floors"]


# ── Build Config ───────────────────────────────────────────────

class TestBuildConfig:
    @pytest.fixture
    def mock_elements(self):
        return {
            "columns": [
                {"grid_x": 0, "grid_y": 0, "section": "C90X90",
                 "floors": ["B3F", "1F"], "page_num": 3},
            ],
            "beams": [
                {"x1": 0, "y1": 0, "x2": 8.4, "y2": 0,
                 "section": "B55X80", "floors": ["1F"],
                 "page_num": 3, "direction": "X"},
            ],
            "walls": [
                {"x1": 0, "y1": 0, "x2": 0, "y2": 6.0,
                 "section": "W25", "floors": ["B3F"],
                 "is_diaphragm_wall": True, "page_num": 1, "direction": "Y"},
            ],
            "small_beams": [],
            "sections": {
                "frame": ["C90X90", "B55X80"],
                "wall": [25],
            },
        }

    @pytest.fixture
    def mock_grid_info(self):
        return {
            "grids": {
                "x": [{"label": "1", "coordinate": 0},
                      {"label": "2", "coordinate": 8.4}],
                "y": [{"label": "A", "coordinate": 0},
                      {"label": "B", "coordinate": 6.0}],
            },
            "stories": [
                {"name": "B3F", "height": 3.6},
                {"name": "1F", "height": 4.2},
                {"name": "2F", "height": 3.2},
            ],
            "base_elevation": -3.6,
            "strength_map": {
                "B3F~1F": {"column": 490, "beam": 420, "wall": 420, "slab": 350},
                "2F": {"column": 350, "beam": 280, "wall": 280, "slab": 280},
            },
        }

    def test_basic_merge(self, mock_elements, mock_grid_info):
        config, warnings = build_config(
            mock_elements, mock_grid_info, "Test", "C:/test.EDB")
        assert config["project"]["name"] == "Test"
        assert config["project"]["units"] == 12
        assert config["project"]["skip_materials"] is False
        assert len(config["columns"]) == 1
        assert len(config["beams"]) == 1
        assert len(config["walls"]) == 1
        assert config["small_beams"] == []
        assert config["slabs"] == []
        assert config["sections"]["slab"] == []
        assert config["sections"]["raft"] == []

    def test_strips_page_num(self, mock_elements, mock_grid_info):
        config, _ = build_config(
            mock_elements, mock_grid_info, "Test", "C:/test.EDB")
        assert "page_num" not in config["columns"][0]
        assert "page_num" not in config["beams"][0]
        assert "direction" not in config["beams"][0]
        assert "page_num" not in config["walls"][0]

    def test_preserves_diaphragm_wall(self, mock_elements, mock_grid_info):
        config, _ = build_config(
            mock_elements, mock_grid_info, "Test", "C:/test.EDB")
        assert config["walls"][0]["is_diaphragm_wall"] is True

    def test_copies_grid_info_fields(self, mock_elements, mock_grid_info):
        mock_grid_info["building_outline"] = [[0, 0], [10, 0], [10, 10], [0, 10]]
        mock_grid_info["core_grid_area"] = {"x_range": [3, 7], "y_range": [3, 7]}
        config, _ = build_config(
            mock_elements, mock_grid_info, "Test", "C:/test.EDB")
        assert config["building_outline"] == [[0, 0], [10, 0], [10, 10], [0, 10]]
        assert "core_grid_area" in config

    def test_slab_region_matrix_not_copied(self, mock_elements, mock_grid_info):
        """slab_region_matrix moved to Phase 2 SB-READER — should NOT be in config."""
        mock_grid_info["slab_region_matrix"] = {"1F": {"1~2/A~B": True}}
        config, _ = build_config(
            mock_elements, mock_grid_info, "Test", "C:/test.EDB")
        assert "slab_region_matrix" not in config

    def test_empty_section_warning(self, mock_elements, mock_grid_info):
        mock_elements["columns"][0]["section"] = ""
        config, warnings = build_config(
            mock_elements, mock_grid_info, "Test", "C:/test.EDB")
        assert any("empty section" in w for w in warnings)

    def test_empty_elements(self, mock_grid_info):
        elements = {
            "columns": [], "beams": [], "walls": [], "small_beams": [],
            "sections": {"frame": [], "wall": []},
        }
        config, warnings = build_config(
            elements, mock_grid_info, "Test", "C:/test.EDB")
        assert config["columns"] == []
        assert config["beams"] == []
        assert config["walls"] == []

    def test_strength_map_preserved(self, mock_elements, mock_grid_info):
        config, _ = build_config(
            mock_elements, mock_grid_info, "Test", "C:/test.EDB")
        assert "B3F~1F" in config["strength_map"]
        assert config["strength_map"]["B3F~1F"]["column"] == 490

    def test_substructure_outline_copied(self, mock_elements, mock_grid_info):
        mock_grid_info["substructure_outline"] = [[0, 0], [30, 0], [30, 28], [0, 28]]
        config, _ = build_config(
            mock_elements, mock_grid_info, "Test", "C:/test.EDB")
        assert config["substructure_outline"] == [[0, 0], [30, 0], [30, 28], [0, 28]]
