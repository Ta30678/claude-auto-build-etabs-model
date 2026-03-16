"""Tests for affine_calibrate.py grid mode (Phase 1)."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.affine_calibrate import (
    compute_grid_transform,
    apply_transform_to_slide,
    apply_affine,
)


# ---------------------------------------------------------------------------
# compute_grid_transform
# ---------------------------------------------------------------------------

class TestComputeGridTransform:
    def test_basic_linear(self):
        """Two X + two Y anchors → exact linear transform."""
        grid_data = {
            "x_grids": [
                {"name": "1", "coordinate": 0.0},
                {"name": "5", "coordinate": 24.0},
            ],
            "y_grids": [
                {"name": "A", "coordinate": 0.0},
                {"name": "G", "coordinate": 36.0},
            ],
        }
        grid_anchors = {
            "anchors": [
                {"grid_name": "1", "direction": "X", "ppt_x": 2.0},
                {"grid_name": "5", "direction": "X", "ppt_x": 26.0},
                {"grid_name": "A", "direction": "Y", "ppt_y": 1.0},
                {"grid_name": "G", "direction": "Y", "ppt_y": 37.0},
            ]
        }
        t = compute_grid_transform(grid_anchors, grid_data)
        assert t is not None
        assert t["n_x_anchors"] == 2
        assert t["n_y_anchors"] == 2
        # grid_x = 1.0 * ppt_x - 2.0
        assert abs(t["sx"] - 1.0) < 1e-6
        assert abs(t["ox"] - (-2.0)) < 1e-6
        # grid_y = 1.0 * ppt_y - 1.0
        assert abs(t["sy"] - 1.0) < 1e-6
        assert abs(t["oy"] - (-1.0)) < 1e-6

    def test_with_scale(self):
        """Grid anchors with non-unity scale."""
        grid_data = {
            "x_grids": [
                {"name": "A", "coordinate": 0.0},
                {"name": "B", "coordinate": 10.0},
            ],
            "y_grids": [
                {"name": "1", "coordinate": 0.0},
                {"name": "2", "coordinate": 8.0},
            ],
        }
        grid_anchors = {
            "anchors": [
                {"grid_name": "A", "direction": "X", "ppt_x": 0.0},
                {"grid_name": "B", "direction": "X", "ppt_x": 5.0},   # scale 2x
                {"grid_name": "1", "direction": "Y", "ppt_y": 0.0},
                {"grid_name": "2", "direction": "Y", "ppt_y": 4.0},   # scale 2x
            ]
        }
        t = compute_grid_transform(grid_anchors, grid_data)
        assert t is not None
        assert abs(t["sx"] - 2.0) < 1e-6
        assert abs(t["sy"] - 2.0) < 1e-6
        assert abs(t["ox"]) < 1e-6
        assert abs(t["oy"]) < 1e-6

    def test_insufficient_anchors(self):
        """Only 1 X + 1 Y anchor → should still work (with scale=1)."""
        grid_data = {
            "x_grids": [{"name": "1", "coordinate": 5.0}],
            "y_grids": [{"name": "A", "coordinate": 3.0}],
        }
        grid_anchors = {
            "anchors": [
                {"grid_name": "1", "direction": "X", "ppt_x": 10.0},
                {"grid_name": "A", "direction": "Y", "ppt_y": 7.0},
            ]
        }
        # 1 per axis: returns None (need >= 2 per axis)
        t = compute_grid_transform(grid_anchors, grid_data)
        assert t is None

    def test_missing_grid_name(self):
        """Anchor references non-existent grid name → ignored.
        With 2 X + 1 Y, still computes (X has enough, Y uses single-point fallback)."""
        grid_data = {
            "x_grids": [
                {"name": "1", "coordinate": 0.0},
                {"name": "2", "coordinate": 10.0},
            ],
            "y_grids": [
                {"name": "A", "coordinate": 0.0},
                {"name": "B", "coordinate": 8.0},
            ],
        }
        grid_anchors = {
            "anchors": [
                {"grid_name": "1", "direction": "X", "ppt_x": 1.0},
                {"grid_name": "2", "direction": "X", "ppt_x": 11.0},
                {"grid_name": "A", "direction": "Y", "ppt_y": 2.0},
                {"grid_name": "Z", "direction": "Y", "ppt_y": 50.0},  # Z doesn't exist
            ]
        }
        # 2 X anchors + 1 Y anchor → still computes (at least one axis has >= 2)
        t = compute_grid_transform(grid_anchors, grid_data)
        assert t is not None
        assert t["n_x_anchors"] == 2
        assert t["n_y_anchors"] == 1

    def test_empty_anchors(self):
        grid_data = {"x_grids": [], "y_grids": []}
        grid_anchors = {"anchors": []}
        t = compute_grid_transform(grid_anchors, grid_data)
        assert t is None


# ---------------------------------------------------------------------------
# apply_transform_to_slide
# ---------------------------------------------------------------------------

class TestApplyTransformToSlide:
    def test_transforms_all_elements(self):
        slide_data = {
            "_metadata": {"slide_num": 3, "floor_label": "1F~2F"},
            "columns": [
                {"grid_x": 5.0, "grid_y": 3.0, "x1": 5.0, "y1": 3.0,
                 "section": "C80X80", "floors": ["1F"]},
            ],
            "beams": [
                {"x1": 5.0, "y1": 3.0, "x2": 15.0, "y2": 3.0,
                 "section": "B55X80", "floors": ["1F"]},
            ],
            "walls": [
                {"x1": 5.0, "y1": 3.0, "x2": 5.0, "y2": 13.0,
                 "section": "W25", "floors": ["1F"]},
            ],
            "small_beams": [],
        }
        transform = {
            "sx": 1.0, "ox": -5.0,
            "sy": 1.0, "oy": -3.0,
            "n_points": 4, "max_residual": 0.01, "mean_residual": 0.005,
        }
        result = apply_transform_to_slide(slide_data, transform)

        # Column
        col = result["columns"][0]
        assert col["grid_x"] == 0.0
        assert col["grid_y"] == 0.0

        # Beam
        beam = result["beams"][0]
        assert beam["x1"] == 0.0
        assert beam["y1"] == 0.0
        assert beam["x2"] == 10.0
        assert beam["y2"] == 0.0

        # Wall
        wall = result["walls"][0]
        assert wall["x1"] == 0.0
        assert wall["y1"] == 0.0
        assert wall["x2"] == 0.0
        assert wall["y2"] == 10.0

        # Metadata should include calibration info
        assert "grid_calibration" in result["_metadata"]

    def test_no_mutation_of_original(self):
        """Original slide_data should not be modified."""
        slide_data = {
            "columns": [{"grid_x": 5.0, "grid_y": 3.0}],
            "beams": [],
            "walls": [],
            "small_beams": [],
        }
        transform = {
            "sx": 1.0, "ox": -5.0,
            "sy": 1.0, "oy": -3.0,
            "n_points": 2, "max_residual": 0.0, "mean_residual": 0.0,
        }
        result = apply_transform_to_slide(slide_data, transform)
        assert slide_data["columns"][0]["grid_x"] == 5.0  # unchanged
        assert result["columns"][0]["grid_x"] == 0.0
