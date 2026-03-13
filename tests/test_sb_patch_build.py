"""Tests for golden_scripts.tools.sb_patch_build."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.sb_patch_build import (
    build_sb_patch,
    validate_sb_patch,
)


class TestBuildSbPatch:
    @pytest.fixture
    def mock_sb_elements(self):
        return {
            "small_beams": [
                {"x1": 0, "y1": 2.85, "x2": 8.4, "y2": 2.85,
                 "section": "SB30X50", "floors": ["2F", "3F"],
                 "page_num": 3, "direction": "X"},
                {"x1": 0, "y1": 4.5, "x2": 8.4, "y2": 4.5,
                 "section": "SB25X45", "floors": ["2F"],
                 "page_num": 3, "direction": "X"},
            ],
        }

    @pytest.fixture
    def mock_config(self):
        return {
            "stories": [
                {"name": "1F", "height": 4.2},
                {"name": "2F", "height": 3.2},
                {"name": "3F", "height": 3.2},
                {"name": "RF", "height": 3.2},
            ],
        }

    def test_basic_extraction(self, mock_sb_elements, mock_config):
        patch, warnings = build_sb_patch(mock_sb_elements, mock_config)
        assert len(patch["small_beams"]) == 2
        assert "SB30X50" in patch["sections"]["frame"]
        assert "SB25X45" in patch["sections"]["frame"]

    def test_strips_page_num_and_direction(self, mock_sb_elements, mock_config):
        patch, _ = build_sb_patch(mock_sb_elements, mock_config)
        for sb in patch["small_beams"]:
            assert "page_num" not in sb
            assert "direction" not in sb

    def test_preserves_coordinates(self, mock_sb_elements, mock_config):
        patch, _ = build_sb_patch(mock_sb_elements, mock_config)
        assert patch["small_beams"][0]["x1"] == 0
        assert patch["small_beams"][0]["y1"] == 2.85
        assert patch["small_beams"][0]["x2"] == 8.4

    def test_empty_input(self, mock_config):
        patch, warnings = build_sb_patch({"small_beams": []}, mock_config)
        assert patch["small_beams"] == []
        assert patch["sections"]["frame"] == []

    def test_rooftop_replication(self):
        sb_elements = {
            "small_beams": [
                {"x1": 6, "y1": 10, "x2": 14, "y2": 10,
                 "section": "SB30X50", "floors": ["2F", "RF"],
                 "page_num": 3},
            ],
        }
        config = {
            "stories": [
                {"name": "1F", "height": 4.2},
                {"name": "2F", "height": 3.2},
                {"name": "RF", "height": 3.2},
                {"name": "R1F", "height": 3.2},
                {"name": "R2F", "height": 3.2},
                {"name": "PRF", "height": 1.5},
            ],
            "core_grid_area": {"x_range": [5, 15], "y_range": [5, 15]},
        }
        patch, _ = build_sb_patch(sb_elements, config)
        assert "R2F" in patch["small_beams"][0]["floors"]
        assert "PRF" in patch["small_beams"][0]["floors"]

    def test_no_rooftop_without_r2f(self):
        sb_elements = {
            "small_beams": [
                {"x1": 6, "y1": 10, "x2": 14, "y2": 10,
                 "section": "SB30X50", "floors": ["2F", "RF"]},
            ],
        }
        config = {
            "stories": [
                {"name": "1F", "height": 4.2},
                {"name": "2F", "height": 3.2},
                {"name": "RF", "height": 3.2},
                {"name": "R1F", "height": 3.2},
                {"name": "PRF", "height": 1.5},
            ],
            "core_grid_area": {"x_range": [5, 15], "y_range": [5, 15]},
        }
        patch, _ = build_sb_patch(sb_elements, config)
        # No R2F story → no replication
        assert "PRF" not in patch["small_beams"][0]["floors"]

    def test_empty_section_warning(self, mock_config):
        sb_elements = {
            "small_beams": [
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0,
                 "section": "", "floors": ["2F"]},
            ],
        }
        patch, warnings = build_sb_patch(sb_elements, mock_config)
        assert any("empty section" in w for w in warnings)

    def test_sections_sorted(self, mock_sb_elements, mock_config):
        patch, _ = build_sb_patch(mock_sb_elements, mock_config)
        assert patch["sections"]["frame"] == sorted(patch["sections"]["frame"])


class TestValidateSbPatch:
    def test_valid_patch(self):
        patch = {
            "small_beams": [
                {"x1": 0, "y1": 2.85, "x2": 8.4, "y2": 2.85,
                 "section": "SB30X50", "floors": ["2F"]},
            ],
            "sections": {"frame": ["SB30X50"]},
        }
        errors, warnings = validate_sb_patch(patch, {"1F", "2F", "3F"})
        assert len(errors) == 0

    def test_invalid_section_name(self):
        patch = {
            "small_beams": [
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0,
                 "section": "INVALID", "floors": ["2F"]},
            ],
            "sections": {"frame": ["INVALID"]},
        }
        errors, _ = validate_sb_patch(patch, {"2F"})
        assert any("invalid name" in e for e in errors)

    def test_zero_length_beam(self):
        patch = {
            "small_beams": [
                {"x1": 5, "y1": 5, "x2": 5, "y2": 5,
                 "section": "SB30X50", "floors": ["2F"]},
            ],
            "sections": {"frame": ["SB30X50"]},
        }
        errors, _ = validate_sb_patch(patch, {"2F"})
        assert any("zero-length" in e for e in errors)

    def test_invalid_floor(self):
        patch = {
            "small_beams": [
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0,
                 "section": "SB30X50", "floors": ["99F"]},
            ],
            "sections": {"frame": ["SB30X50"]},
        }
        errors, _ = validate_sb_patch(patch, {"1F", "2F"})
        assert any("not in stories" in e for e in errors)

    def test_string_coordinate(self):
        patch = {
            "small_beams": [
                {"x1": "0", "y1": 0, "x2": 10, "y2": 0,
                 "section": "SB30X50", "floors": ["2F"]},
            ],
            "sections": {"frame": ["SB30X50"]},
        }
        errors, _ = validate_sb_patch(patch, {"2F"})
        assert any("expected number" in e for e in errors)

    def test_section_not_in_frame(self):
        patch = {
            "small_beams": [
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0,
                 "section": "SB30X50", "floors": ["2F"]},
            ],
            "sections": {"frame": ["SB25X45"]},
        }
        errors, _ = validate_sb_patch(patch, {"2F"})
        assert any("not in sections.frame" in e for e in errors)

    def test_fsb_section_valid(self):
        patch = {
            "small_beams": [
                {"x1": 0, "y1": 0, "x2": 10, "y2": 0,
                 "section": "FSB40X80", "floors": ["B3F"]},
            ],
            "sections": {"frame": ["FSB40X80"]},
        }
        errors, _ = validate_sb_patch(patch, {"B3F"})
        assert len(errors) == 0

    def test_empty_patch(self):
        patch = {"small_beams": [], "sections": {"frame": []}}
        errors, _ = validate_sb_patch(patch, {"1F"})
        assert len(errors) == 0
