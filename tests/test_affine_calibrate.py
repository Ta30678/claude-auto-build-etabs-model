"""Tests for golden_scripts.tools.affine_calibrate."""

import math
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.affine_calibrate import (
    solve_affine_1d,
    compute_affine,
    apply_affine,
    collect_correspondences,
    align_sb_elements,
    find_fallback_transform,
    _normalize_grid_data_for_affine,
    compute_grid_transform,
)


# ---------------------------------------------------------------------------
# solve_affine_1d
# ---------------------------------------------------------------------------

class TestSolveAffine1D:
    def test_identity(self):
        """If pptx == grid, scale=1 offset=0."""
        pptx = [0.0, 1.0, 2.0, 3.0]
        grid = [0.0, 1.0, 2.0, 3.0]
        s, o, res = solve_affine_1d(pptx, grid)
        assert abs(s - 1.0) < 1e-6
        assert abs(o) < 1e-6
        assert all(r < 1e-6 for r in res)

    def test_pure_offset(self):
        """grid = pptx + 10."""
        pptx = [0.0, 5.0, 10.0]
        grid = [10.0, 15.0, 20.0]
        s, o, res = solve_affine_1d(pptx, grid)
        assert abs(s - 1.0) < 1e-6
        assert abs(o - 10.0) < 1e-6
        assert all(r < 1e-6 for r in res)

    def test_scale_and_offset(self):
        """grid = 2 * pptx + 3."""
        pptx = [0.0, 1.0, 2.0, 3.0]
        grid = [3.0, 5.0, 7.0, 9.0]
        s, o, res = solve_affine_1d(pptx, grid)
        assert abs(s - 2.0) < 1e-6
        assert abs(o - 3.0) < 1e-6

    def test_single_point(self):
        """Single point: scale=1, offset from point."""
        s, o, res = solve_affine_1d([5.0], [15.0])
        assert abs(s - 1.0) < 1e-6
        assert abs(o - 10.0) < 1e-6

    def test_empty(self):
        """Empty input: identity."""
        s, o, res = solve_affine_1d([], [])
        assert s == 1.0
        assert o == 0.0

    def test_noisy_data(self):
        """Slight noise in data should still give reasonable fit."""
        pptx = [0.0, 1.0, 2.0, 3.0]
        grid = [0.01, 1.02, 1.99, 3.01]  # ~identity with noise
        s, o, res = solve_affine_1d(pptx, grid)
        assert abs(s - 1.0) < 0.05
        assert abs(o) < 0.05


# ---------------------------------------------------------------------------
# compute_affine
# ---------------------------------------------------------------------------

class TestComputeAffine:
    def test_identity_transform(self):
        corr = [(0, 0, 0, 0), (10, 0, 10, 0), (0, 8, 0, 8), (10, 8, 10, 8)]
        t = compute_affine(corr)
        assert t is not None
        assert abs(t["sx"] - 1.0) < 1e-6
        assert abs(t["sy"] - 1.0) < 1e-6
        assert abs(t["ox"]) < 1e-6
        assert abs(t["oy"]) < 1e-6

    def test_offset_transform(self):
        """PPTX origin shifted by (5, 3) from grid origin."""
        corr = [(5, 3, 0, 0), (15, 3, 10, 0), (5, 11, 0, 8)]
        t = compute_affine(corr)
        assert t is not None
        assert abs(t["sx"] - 1.0) < 1e-6
        assert abs(t["sy"] - 1.0) < 1e-6
        assert abs(t["ox"] - (-5.0)) < 1e-6
        assert abs(t["oy"] - (-3.0)) < 1e-6

    def test_empty(self):
        assert compute_affine([]) is None


# ---------------------------------------------------------------------------
# apply_affine
# ---------------------------------------------------------------------------

class TestApplyAffine:
    def test_basic(self):
        t = {"sx": 1.0, "ox": -5.0, "sy": 1.0, "oy": -3.0}
        x, y = apply_affine(5.0, 3.0, t)
        assert x == 0.0
        assert y == 0.0

    def test_with_scale(self):
        t = {"sx": 2.0, "ox": 1.0, "sy": 0.5, "oy": 2.0}
        x, y = apply_affine(3.0, 4.0, t)
        assert x == 7.0   # 2*3+1
        assert y == 4.0   # 0.5*4+2


# ---------------------------------------------------------------------------
# collect_correspondences
# ---------------------------------------------------------------------------

class TestCollectCorrespondences:
    def test_beam_match(self):
        """Beams with same section + direction should match."""
        elements_page = [
            {"x1": 5.0, "y1": 3.0, "x2": 15.0, "y2": 3.0,
             "section": "B55X80", "direction": "X", "floors": ["2F"]},
        ]
        config = {
            "beams": [
                {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0,
                 "section": "B55X80", "floors": ["2F"]},
            ],
            "columns": [],
        }
        corr = collect_correspondences(elements_page, config, "beams")
        assert len(corr) == 2  # Two endpoints

    def test_no_match(self):
        """Different sections should not match."""
        elements_page = [
            {"x1": 0, "y1": 0, "x2": 10, "y2": 0,
             "section": "B55X80", "direction": "X", "floors": ["2F"]},
        ]
        config = {
            "beams": [
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0,
                 "section": "B40X60", "floors": ["2F"]},
            ],
            "columns": [],
        }
        corr = collect_correspondences(elements_page, config, "beams")
        assert len(corr) == 0


# ---------------------------------------------------------------------------
# align_sb_elements
# ---------------------------------------------------------------------------

class TestAlignSbElements:
    def test_applies_transform(self):
        sb_json = {
            "small_beams": [
                {"x1": 5.0, "y1": 3.0, "x2": 15.0, "y2": 3.0,
                 "section": "SB30X50", "floors": ["2F"], "page_num": 3},
            ],
        }
        transforms = {
            3: {"sx": 1.0, "ox": -5.0, "sy": 1.0, "oy": -3.0,
                "n_points": 10, "max_residual": 0.01, "mean_residual": 0.005,
                "residuals_x": [], "residuals_y": []},
        }
        aligned, stats = align_sb_elements(sb_json, transforms)
        sb = aligned["small_beams"][0]
        assert sb["x1"] == 0.0
        assert sb["y1"] == 0.0
        assert sb["x2"] == 10.0
        assert sb["y2"] == 0.0
        assert stats["transformed"] == 1

    def test_fallback_transform(self):
        sb_json = {
            "small_beams": [
                {"x1": 5.0, "y1": 3.0, "x2": 15.0, "y2": 3.0,
                 "section": "SB30X50", "floors": ["2F"], "page_num": 4},
            ],
        }
        # Only have transform for slide 3, not 4
        transforms = {
            3: {"sx": 1.0, "ox": -5.0, "sy": 1.0, "oy": -3.0,
                "n_points": 10, "max_residual": 0.01, "mean_residual": 0.005,
                "residuals_x": [], "residuals_y": []},
        }
        aligned, stats = align_sb_elements(sb_json, transforms)
        assert stats["fallback"] == 1
        assert stats["transformed"] == 1

    def test_no_page_num(self):
        sb_json = {
            "small_beams": [
                {"x1": 5.0, "y1": 3.0, "x2": 15.0, "y2": 3.0,
                 "section": "SB30X50", "floors": ["2F"]},  # no page_num
            ],
        }
        transforms = {}
        aligned, stats = align_sb_elements(sb_json, transforms)
        assert stats["identity"] == 1
        # Coords unchanged
        assert aligned["small_beams"][0]["x1"] == 5.0


# ---------------------------------------------------------------------------
# find_fallback_transform
# ---------------------------------------------------------------------------

class TestFindFallback:
    def test_nearest(self):
        transforms = {
            3: {"sx": 1.0}, 5: {"sx": 2.0},
        }
        assert find_fallback_transform(transforms, 4)["sx"] == 1.0  # slide 3 is closer
        assert find_fallback_transform(transforms, 6)["sx"] == 2.0  # slide 5 is closer

    def test_empty(self):
        assert find_fallback_transform({}, 3) is None


# ---------------------------------------------------------------------------
# _normalize_grid_data_for_affine
# ---------------------------------------------------------------------------

class TestNormalizeGridDataForAffine:

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
        result = _normalize_grid_data_for_affine(raw)
        assert "x_grids" in result and "y_grids" in result
        assert len(result["x_grids"]) == 2
        assert result["x_grids"][0]["name"] == "A"
        assert result["x_grids"][0]["coordinate"] == 0.0
        assert result["y_grids"][1]["name"] == "2"
        assert result["y_grids"][1]["coordinate"] == 6.0

    def test_flat_format(self):
        """Flat format: {x: [{label}], y: [{label}]}."""
        raw = {
            "x": [{"label": "A", "coordinate": 0.0}, {"label": "B", "coordinate": 8.5}],
            "y": [{"label": "1", "coordinate": 0.0}],
        }
        result = _normalize_grid_data_for_affine(raw)
        assert result["x_grids"][0]["name"] == "A"
        assert result["x_grids"][1]["coordinate"] == 8.5
        assert result["y_grids"][0]["name"] == "1"

    def test_affine_passthrough(self):
        """Already affine format: {x_grids: [{name}], y_grids: [{name}]} — pass through."""
        raw = {
            "x_grids": [{"name": "A", "coordinate": 0.0}],
            "y_grids": [{"name": "1", "coordinate": 0.0}],
        }
        result = _normalize_grid_data_for_affine(raw)
        assert result is raw  # same object, no conversion

    def test_canonical_works_with_compute_grid_transform(self):
        """End-to-end: canonical grid_data format works with compute_grid_transform."""
        grid_data = {
            "grids": {
                "x": [{"label": "A", "coordinate": 0.0}, {"label": "B", "coordinate": 8.5}],
                "y": [{"label": "1", "coordinate": 0.0}, {"label": "2", "coordinate": 6.0}],
            }
        }
        anchors = {
            "anchors": [
                {"grid_name": "A", "direction": "X", "ppt_x": 2.0},
                {"grid_name": "B", "direction": "X", "ppt_x": 10.5},
                {"grid_name": "1", "direction": "Y", "ppt_y": 1.0},
                {"grid_name": "2", "direction": "Y", "ppt_y": 7.0},
            ]
        }
        transform = compute_grid_transform(anchors, grid_data)
        assert transform is not None
        assert transform["n_x_anchors"] == 2
        assert transform["n_y_anchors"] == 2
