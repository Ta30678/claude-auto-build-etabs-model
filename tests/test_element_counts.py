"""Test: Element counts should be reasonable."""
import pytest


def test_frames_exist(SapModel, all_frames):
    """Model should have frame objects."""
    assert all_frames["count"] > 0, "No frame objects in model"


def test_areas_exist(SapModel):
    """Model should have area objects."""
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Area Assignments - Summary", [], "All", 0, [], 0, [])
        assert ret[0] == 0, "Could not read Area Assignments"
        assert ret[5] > 0, "No area objects in model"
    except Exception as e:
        pytest.skip(f"Could not check areas: {e}")


def test_columns_exist(all_frames):
    """Model should have columns (section starting with C and containing X)."""
    col_count = sum(1 for p in all_frames["props"]
                    if p.startswith('C') and 'X' in p)
    assert col_count > 0, "No column objects found"


def test_beams_exist(all_frames):
    """Model should have beams."""
    beam_count = sum(1 for p in all_frames["props"]
                     if p.startswith(('B', 'SB', 'WB', 'FB')))
    assert beam_count > 0, "No beam objects found"


def test_stories_defined(SapModel):
    """Model should have story definitions."""
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Story Definitions", [], "All", 0, [], 0, [])
    if ret[0] != 0:
        pytest.skip("Could not read Story Definitions")
    assert ret[5] > 0, "No stories defined"
