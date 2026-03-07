"""Test: Load patterns and assignments."""
import pytest


REQUIRED_PATTERNS = ["DL", "LL", "EQXP", "EQXN", "EQYP", "EQYN"]


def test_load_patterns_exist(SapModel):
    """Required load patterns must be defined."""
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Load Pattern Definitions", [], "All", 0, [], 0, [])
    assert ret[0] == 0, "Could not read Load Pattern Definitions"

    fields = list(ret[4])
    data = list(ret[6])
    nf = len(fields)
    name_idx = fields.index("Name")

    pattern_names = set()
    for i in range(ret[5]):
        row = data[i*nf:(i+1)*nf]
        pattern_names.add(row[name_idx])

    missing = [p for p in REQUIRED_PATTERNS if p not in pattern_names]
    assert len(missing) == 0, f"Missing load patterns: {missing}"


def test_no_sdl_pattern(SapModel):
    """SDL pattern should NOT exist unless explicitly requested."""
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Load Pattern Definitions", [], "All", 0, [], 0, [])
    if ret[0] != 0:
        pytest.skip("Could not read Load Pattern Definitions")

    fields = list(ret[4])
    data = list(ret[6])
    nf = len(fields)
    name_idx = fields.index("Name")

    for i in range(ret[5]):
        row = data[i*nf:(i+1)*nf]
        assert row[name_idx] != "SDL", "SDL pattern exists but should not (unless requested)"


def test_area_loads_assigned(SapModel):
    """Area uniform loads should be assigned."""
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Area Loads - Uniform", [], "All", 0, [], 0, [])
    if ret[0] != 0:
        pytest.skip("Could not read area loads table")
    assert ret[5] > 0, "No area uniform loads assigned"


def test_dl_self_weight(SapModel):
    """DL pattern should have self-weight multiplier = 1."""
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Load Pattern Definitions", [], "All", 0, [], 0, [])
    if ret[0] != 0:
        pytest.skip("Could not read Load Pattern Definitions")

    fields = list(ret[4])
    data = list(ret[6])
    nf = len(fields)
    name_idx = fields.index("Name")
    sw_idx = fields.index("SelfWtMult") if "SelfWtMult" in fields else -1

    if sw_idx < 0:
        pytest.skip("SelfWtMult field not in table")

    for i in range(ret[5]):
        row = data[i*nf:(i+1)*nf]
        if row[name_idx] == "DL":
            sw = float(row[sw_idx])
            assert abs(sw - 1.0) < 0.01, f"DL self-weight={sw}, expected 1.0"
            return

    pytest.fail("DL pattern not found")
