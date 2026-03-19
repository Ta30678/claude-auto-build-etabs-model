"""Tests for golden_scripts.tools.plot_elements."""
import json
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.plot_elements import (
    _build_color_map,
    _parse_frame_dims,
    _parse_wall_thickness,
    plot_elements,
)


# ---------------------------------------------------------------------------
# _build_color_map tests
# ---------------------------------------------------------------------------

class TestBuildColorMap:
    def test_basic_legend(self):
        legend = {
            "FF0000": [{"element_type": "beam", "section": "B55X80", "label": "B55X80"}],
            "2F5597": [{"element_type": "column", "section": "C60X60", "label": "C60X60"}],
        }
        cmap = _build_color_map(legend)
        assert cmap[("beam", "B55X80")] == "#FF0000"
        assert cmap[("column", "C60X60")] == "#2F5597"

    def test_multiple_entries_same_color(self):
        legend = {
            "C00000": [
                {"element_type": "beam", "section": "WB50X70", "label": "WB50X70"},
                {"element_type": "beam", "section": "B40X60", "label": "B40X60"},
            ],
        }
        cmap = _build_color_map(legend)
        assert cmap[("beam", "WB50X70")] == "#C00000"
        assert cmap[("beam", "B40X60")] == "#C00000"

    def test_empty_legend(self):
        assert _build_color_map({}) == {}

    def test_missing_fields_skipped(self):
        legend = {
            "FF0000": [{"element_type": "", "section": "B55X80"}],
            "00FF00": [{"element_type": "beam", "section": ""}],
        }
        cmap = _build_color_map(legend)
        assert len(cmap) == 0


# ---------------------------------------------------------------------------
# _parse_frame_dims tests
# ---------------------------------------------------------------------------

class TestParseFrameDims:
    def test_column(self):
        assert _parse_frame_dims("C70X100") == (0.70, 1.00)

    def test_column_with_fc(self):
        assert _parse_frame_dims("C90X90C420") == (0.90, 0.90)

    def test_beam(self):
        assert _parse_frame_dims("B55X80") == (0.55, 0.80)

    def test_small_beam(self):
        assert _parse_frame_dims("SB25X50") == (0.25, 0.50)

    def test_wall_beam(self):
        assert _parse_frame_dims("WB50X70") == (0.50, 0.70)

    def test_foundation_beam(self):
        assert _parse_frame_dims("FB80X200") == (0.80, 2.00)

    def test_invalid(self):
        assert _parse_frame_dims("W25") is None
        assert _parse_frame_dims("S15") is None
        assert _parse_frame_dims("unknown") is None


# ---------------------------------------------------------------------------
# _parse_wall_thickness tests
# ---------------------------------------------------------------------------

class TestParseWallThickness:
    def test_basic(self):
        assert _parse_wall_thickness("W25") == 0.25

    def test_with_fc(self):
        assert _parse_wall_thickness("W30C280") == 0.30

    def test_non_wall(self):
        assert _parse_wall_thickness("C70X100") is None
        assert _parse_wall_thickness("B55X80") is None


# ---------------------------------------------------------------------------
# plot_elements integration tests
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_elements(tmp_path):
    """Create a sample element JSON for testing."""
    data = {
        "_metadata": {
            "floor_label": "1F",
            "legend": {
                "2F5597": [{"element_type": "column", "section": "C60X60", "label": "C60X60"}],
                "C00000": [{"element_type": "beam", "section": "B55X80", "label": "B55X80"}],
                "00B050": [{"element_type": "wall", "section": "W25", "label": "W25"}],
                "0066CC": [{"element_type": "small_beam", "section": "SB25X50", "label": "SB25X50"}],
            },
            "stats": {"beams": 2, "columns": 3, "walls": 1, "small_beams": 1},
        },
        "columns": [
            {"element_type": "column", "x1": 0, "y1": 0, "x2": 0, "y2": 0, "section": "C60X60"},
            {"element_type": "column", "x1": 8.5, "y1": 0, "x2": 8.5, "y2": 0, "section": "C60X60"},
            {"element_type": "column", "x1": 0, "y1": 8.0, "x2": 0, "y2": 8.0, "section": "C60X60"},
        ],
        "beams": [
            {"element_type": "beam", "x1": 0, "y1": 0, "x2": 8.5, "y2": 0, "section": "B55X80"},
            {"element_type": "beam", "x1": 0, "y1": 0, "x2": 0, "y2": 8.0, "section": "B55X80"},
        ],
        "walls": [
            {"element_type": "wall", "x1": 3, "y1": 3, "x2": 6, "y2": 3, "section": "W25"},
        ],
        "small_beams": [
            {"element_type": "small_beam", "x1": 2, "y1": 0, "x2": 2, "y2": 4, "section": "SB25X50"},
        ],
    }
    path = tmp_path / "elements.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


@pytest.fixture
def sample_grid_data(tmp_path):
    """Create a sample grid_data.json for testing."""
    data = {
        "grids": {
            "x": [
                {"label": "A", "coordinate": 0.0},
                {"label": "B", "coordinate": 8.5},
            ],
            "y": [
                {"label": "1", "coordinate": 0.0},
                {"label": "2", "coordinate": 8.0},
            ],
            "x_bubble": "End",
            "y_bubble": "Start",
        }
    }
    path = tmp_path / "grid_data.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


class TestPlotElements:
    def test_plot_without_grid(self, sample_elements, tmp_path):
        output = tmp_path / "test_no_grid.png"
        result = plot_elements(sample_elements, output)
        assert output.exists()
        assert output.stat().st_size > 1000  # non-trivial PNG

    def test_plot_with_grid(self, sample_elements, sample_grid_data, tmp_path):
        output = tmp_path / "test_with_grid.png"
        result = plot_elements(sample_elements, output, grid_data_path=sample_grid_data)
        assert output.exists()
        assert output.stat().st_size > 1000

    def test_plot_no_labels(self, sample_elements, tmp_path):
        output = tmp_path / "test_no_labels.png"
        result = plot_elements(sample_elements, output, show_labels=False)
        assert output.exists()

    def test_plot_custom_title(self, sample_elements, tmp_path):
        output = tmp_path / "test_title.png"
        result = plot_elements(sample_elements, output, title="Custom Title")
        assert output.exists()

    def test_plot_creates_parent_dirs(self, sample_elements, tmp_path):
        output = tmp_path / "sub" / "dir" / "test.png"
        result = plot_elements(sample_elements, output)
        assert output.exists()

    def test_plot_empty_elements(self, tmp_path):
        """Plot with no elements should not crash."""
        data = {
            "_metadata": {"floor_label": "empty", "legend": {}, "stats": {}},
            "columns": [], "beams": [], "walls": [], "small_beams": [],
        }
        elem_path = tmp_path / "empty.json"
        with open(elem_path, "w") as f:
            json.dump(data, f)
        output = tmp_path / "empty.png"
        plot_elements(elem_path, output)
        # Should not create file since there are no elements
        # (the function prints a warning and returns)

    def test_plot_low_dpi(self, sample_elements, tmp_path):
        output_hi = tmp_path / "hi.png"
        output_lo = tmp_path / "lo.png"
        plot_elements(sample_elements, output_hi, dpi=300)
        plot_elements(sample_elements, output_lo, dpi=72)
        assert output_hi.stat().st_size > output_lo.stat().st_size
