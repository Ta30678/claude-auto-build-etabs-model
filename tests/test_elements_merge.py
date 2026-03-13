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
