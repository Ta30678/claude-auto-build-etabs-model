"""Tests for golden_scripts.tools.elements_merge."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from golden_scripts.tools.elements_merge import (
    merge_elements,
    dedup_elements,
    merge_sections,
    check_section_coverage,
    normalize_per_slide_input,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_elements(columns=None, beams=None, walls=None, small_beams=None,
                  frame_sections=None, wall_sections=None):
    return {
        "columns": columns or [],
        "beams": beams or [],
        "walls": walls or [],
        "small_beams": small_beams or [],
        "sections": {
            "frame": frame_sections or [],
            "wall": wall_sections or [],
        },
        "_metadata": {
            "input_file": "test.pptx",
            "phase": "phase1",
            "per_page_stats": {},
            "page_floors": {},
            "totals": {},
            "warnings": [],
        },
    }


def make_column(grid_x, grid_y, section, floors):
    return {"grid_x": grid_x, "grid_y": grid_y, "section": section, "floors": floors}


def make_beam(x1, y1, x2, y2, section, floors):
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "section": section, "floors": floors}


def make_wall(x1, y1, x2, y2, section, floors):
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "section": section, "floors": floors}


def make_sb(x1, y1, x2, y2, section, floors):
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "section": section, "floors": floors}


# ---------------------------------------------------------------------------
# TestDedup
# ---------------------------------------------------------------------------

class TestDedup:
    def test_dedup_columns_exact_match(self):
        col = make_column("A", "1", "C90X90", ["1F", "2F"])
        result, removed = dedup_elements([col, col.copy()], "columns")
        assert len(result) == 1
        assert removed == 1

    def test_dedup_columns_different_floors(self):
        c1 = make_column("A", "1", "C90X90", ["1F", "2F"])
        c2 = make_column("A", "1", "C90X90", ["3F", "4F"])
        result, removed = dedup_elements([c1, c2], "columns")
        assert len(result) == 2
        assert removed == 0

    def test_dedup_beams_exact(self):
        b = make_beam(0, 0, 6.0, 0, "B55X80", ["1F", "2F"])
        result, removed = dedup_elements([b, b.copy()], "beams")
        assert len(result) == 1
        assert removed == 1

    def test_dedup_no_duplicates(self):
        b1 = make_beam(0, 0, 6.0, 0, "B55X80", ["1F"])
        b2 = make_beam(0, 0, 6.0, 0, "B40X70", ["1F"])
        result, removed = dedup_elements([b1, b2], "beams")
        assert len(result) == 2
        assert removed == 0


# ---------------------------------------------------------------------------
# TestMergeSections
# ---------------------------------------------------------------------------

class TestMergeSections:
    def test_union_frame(self):
        s_a = {"frame": ["C90X90", "B55X80"], "wall": []}
        s_b = {"frame": ["B55X80", "B40X70"], "wall": []}
        merged = merge_sections([s_a, s_b])
        assert merged["frame"] == ["B40X70", "B55X80", "C90X90"]

    def test_union_wall(self):
        s_a = {"frame": [], "wall": [25]}
        s_b = {"frame": [], "wall": [25, 30]}
        merged = merge_sections([s_a, s_b])
        assert merged["wall"] == [25, 30]

    def test_empty_sections(self):
        s_a = {"frame": [], "wall": []}
        s_b = {"frame": [], "wall": []}
        merged = merge_sections([s_a, s_b])
        assert merged["frame"] == []
        assert merged["wall"] == []


# ---------------------------------------------------------------------------
# TestMergeElements
# ---------------------------------------------------------------------------

class TestMergeElements:
    def test_basic_merge(self):
        file_a = make_elements(
            columns=[
                make_column("A", "1", "C90X90", ["1F"]),
                make_column("B", "1", "C80X80", ["1F"]),
            ],
            beams=[make_beam(0, 0, 6, 0, "B55X80", ["1F"])],
        )
        file_b = make_elements(
            columns=[make_column("C", "1", "C70X70", ["1F"])],
            beams=[
                make_beam(0, 0, 0, 6, "B40X70", ["1F"]),
                make_beam(6, 0, 6, 6, "B40X70", ["1F"]),
            ],
        )
        merged, stats = merge_elements(file_a, file_b)
        assert len(merged["columns"]) == 3
        assert len(merged["beams"]) == 3
        assert stats["columns"]["deduped"] == 3
        assert stats["beams"]["deduped"] == 3

    def test_dedup_across_files(self):
        beam = make_beam(0, 0, 6, 0, "B55X80", ["1F", "2F"])
        file_a = make_elements(beams=[beam])
        file_b = make_elements(beams=[beam.copy()])
        merged, stats = merge_elements(file_a, file_b)
        assert len(merged["beams"]) == 1
        assert stats["beams"]["total"] == 2
        assert stats["beams"]["deduped"] == 1

    def test_sections_merged(self):
        file_a = make_elements(
            frame_sections=["C90X90", "B55X80"],
            wall_sections=[25],
        )
        file_b = make_elements(
            frame_sections=["B40X70"],
            wall_sections=[25, 30],
        )
        merged, stats = merge_elements(file_a, file_b)
        assert merged["sections"]["frame"] == ["B40X70", "B55X80", "C90X90"]
        assert merged["sections"]["wall"] == [25, 30]

    def test_three_files(self):
        f1 = make_elements(columns=[make_column("A", "1", "C90X90", ["1F"])])
        f2 = make_elements(columns=[make_column("B", "1", "C80X80", ["1F"])])
        f3 = make_elements(columns=[make_column("C", "1", "C70X70", ["1F"])])
        merged, stats = merge_elements(f1, f2, f3)
        assert len(merged["columns"]) == 3
        assert stats["input_count"] == 3


# ---------------------------------------------------------------------------
# TestCheckSectionCoverage
# ---------------------------------------------------------------------------

class TestCheckSectionCoverage:
    def test_all_sections_present(self):
        merged = make_elements(
            columns=[make_column("A", "1", "C90X90", ["1F"])],
            beams=[make_beam(0, 0, 6, 0, "B55X80", ["1F"])],
        )
        stats = {"empty_section_count": 0, "empty_section_details": []}
        assert check_section_coverage(merged, stats) is True

    def test_some_empty_below_threshold(self, capsys):
        cols = [make_column("A", str(i), "C90X90", ["1F"]) for i in range(9)]
        cols.append(make_column("A", "9", "", ["1F"]))
        merged = make_elements(columns=cols)
        stats = {
            "empty_section_count": 1,
            "empty_section_details": [
                {"type": "column", "index": 9, "coords": "(A, 9)", "floors": ["1F"]},
            ],
        }
        result = check_section_coverage(merged, stats)
        assert result is True
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_over_threshold(self, capsys):
        cols = [make_column("A", str(i), "C90X90", ["1F"]) for i in range(6)]
        empty_cols = [make_column("A", str(i), "", ["1F"]) for i in range(6, 10)]
        merged = make_elements(columns=cols + empty_cols)
        details = [
            {"type": "column", "index": i, "coords": f"(A, {i})", "floors": ["1F"]}
            for i in range(6, 10)
        ]
        stats = {"empty_section_count": 4, "empty_section_details": details}
        result = check_section_coverage(merged, stats)
        assert result is False
        captured = capsys.readouterr()
        assert "ERROR" in captured.out

    def test_empty_elements(self):
        merged = make_elements()
        stats = {"empty_section_count": 0, "empty_section_details": []}
        assert check_section_coverage(merged, stats) is True


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_merge_empty_files(self):
        f1 = make_elements()
        f2 = make_elements()
        merged, stats = merge_elements(f1, f2)
        assert merged["columns"] == []
        assert merged["beams"] == []
        assert merged["walls"] == []
        assert merged["small_beams"] == []
        assert stats["columns"]["deduped"] == 0
        assert stats["beams"]["deduped"] == 0

    def test_merge_single_file(self):
        col = make_column("A", "1", "C90X90", ["1F", "2F"])
        beam = make_beam(0, 0, 6, 0, "B55X80", ["1F"])
        f1 = make_elements(
            columns=[col],
            beams=[beam],
            frame_sections=["C90X90", "B55X80"],
        )
        merged, stats = merge_elements(f1)
        assert len(merged["columns"]) == 1
        assert len(merged["beams"]) == 1
        assert merged["sections"]["frame"] == ["B55X80", "C90X90"]
        assert stats["input_count"] == 1


# ---------------------------------------------------------------------------
# TestNormalizePerSlideInput
# ---------------------------------------------------------------------------

class TestNormalizePerSlideInput:
    def test_per_slide_format(self):
        """Per-slide JSON (with slide_num) should be normalized."""
        slide_data = {
            "_metadata": {
                "slide_num": 3,
                "floors": ["1F", "2F"],
                "floor_label": "1F~2F",
                "stats": {"beams": 2, "columns": 1},
            },
            "columns": [
                {"grid_x": 0, "grid_y": 0, "section": "C80X80",
                 "floors": ["1F", "2F"], "element_type": "column"},
            ],
            "beams": [
                {"x1": 0, "y1": 0, "x2": 6, "y2": 0, "section": "B55X80",
                 "floors": ["1F"], "element_type": "beam"},
                {"x1": 0, "y1": 0, "x2": 0, "y2": 8, "section": "B40X70",
                 "floors": ["2F"], "element_type": "beam"},
            ],
            "walls": [
                {"x1": 0, "y1": 0, "x2": 0, "y2": 5, "section": "W25",
                 "floors": ["1F"], "element_type": "wall"},
            ],
            "small_beams": [],
        }
        result = normalize_per_slide_input(slide_data)
        assert len(result["columns"]) == 1
        assert len(result["beams"]) == 2
        assert len(result["walls"]) == 1
        assert "B55X80" in result["sections"]["frame"]
        assert "C80X80" in result["sections"]["frame"]
        assert 25 in result["sections"]["wall"]
        assert result["_metadata"]["phase"] == "phase1"

    def test_standard_format_passthrough(self):
        """Standard format (no slide_num) should pass through unchanged."""
        standard = make_elements(
            columns=[make_column("A", "1", "C90X90", ["1F"])],
            frame_sections=["C90X90"],
        )
        result = normalize_per_slide_input(standard)
        assert result is standard  # same object, not a copy

    def test_merge_per_slide_inputs(self):
        """Merge two per-slide JSONs into one unified output."""
        slide_a = {
            "_metadata": {"slide_num": 3, "floors": ["1F"], "floor_label": "1F"},
            "columns": [
                {"grid_x": 0, "grid_y": 0, "section": "C80X80", "floors": ["1F"]},
            ],
            "beams": [
                {"x1": 0, "y1": 0, "x2": 6, "y2": 0, "section": "B55X80",
                 "floors": ["1F"]},
            ],
            "walls": [],
            "small_beams": [],
        }
        slide_b = {
            "_metadata": {"slide_num": 4, "floors": ["2F"], "floor_label": "2F"},
            "columns": [
                {"grid_x": 0, "grid_y": 0, "section": "C80X80", "floors": ["2F"]},
            ],
            "beams": [],
            "walls": [],
            "small_beams": [],
        }
        norm_a = normalize_per_slide_input(slide_a)
        norm_b = normalize_per_slide_input(slide_b)
        merged, stats = merge_elements(norm_a, norm_b)
        assert len(merged["columns"]) == 2  # different floors, not deduped
        assert len(merged["beams"]) == 1
        assert stats["input_count"] == 2


# ---------------------------------------------------------------------------
# TestInputsDirSubfolderGlob
# ---------------------------------------------------------------------------

class TestInputsDirSubfolderGlob:
    """Test that --inputs-dir correctly globs */elements.json in subdirectory structure."""

    def test_subfolder_glob(self, tmp_path):
        """Subdirectory structure: calibrated/{floor}/elements.json"""
        import json

        # Create subdirectory structure
        for fl, col_grid in [("1F~2F", "A"), ("3F~14F", "B")]:
            sub = tmp_path / fl
            sub.mkdir()
            data = make_elements(
                columns=[make_column(col_grid, "1", "C90X90", [fl.split("~")[0]])],
            )
            with open(sub / "elements.json", "w") as f:
                json.dump(data, f)

        # Simulate what --inputs-dir does: glob */elements.json
        from pathlib import Path
        dir_path = Path(tmp_path)
        json_files = sorted(dir_path.glob("*/elements.json"))
        assert len(json_files) == 2
        assert all(f.name == "elements.json" for f in json_files)

    def test_subfolder_fallback_to_flat(self, tmp_path):
        """Flat structure fallback: calibrated/*.json"""
        import json

        # Create flat structure (no subdirectories)
        for fl in ["1F~2F", "3F~14F"]:
            data = make_elements(
                columns=[make_column("A", "1", "C90X90", [fl.split("~")[0]])],
            )
            with open(tmp_path / f"{fl}.json", "w") as f:
                json.dump(data, f)

        # Simulate fallback: */elements.json finds nothing, falls back to *.json
        from pathlib import Path
        dir_path = Path(tmp_path)
        json_files = sorted(dir_path.glob("*/elements.json"))
        assert len(json_files) == 0  # no subfolder match
        json_files = sorted(dir_path.glob("*.json"))
        assert len(json_files) == 2  # flat fallback works
