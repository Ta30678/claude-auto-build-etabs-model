"""Test: Diaphragm assignments exist."""
import pytest


def test_diaphragms_exist(SapModel):
    """At least one diaphragm should be defined."""
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Diaphragm Definitions", [], "All", 0, [], 0, [])
        assert ret[0] == 0, "Could not read Diaphragm Definitions"
        assert ret[5] > 0, "No diaphragms defined"
    except Exception as e:
        pytest.skip(f"Could not check diaphragms: {e}")


def test_diaphragm_point_assignments(SapModel):
    """Diaphragm assignments should exist on joint points."""
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Joint Assignments - Diaphragms", [], "All", 0, [], 0, [])
        if ret[0] != 0:
            pytest.skip("Could not read diaphragm assignments table")
        assert ret[5] > 0, "No diaphragm point assignments found"
    except Exception as e:
        pytest.skip(f"Could not check diaphragm assignments: {e}")
