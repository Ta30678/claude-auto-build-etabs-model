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


def test_rooftop_ll_value(SapModel, request):
    """Rooftop floors (R1F~PRF) should have LL=0.3 if they have area loads."""
    import re

    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Area Loads - Uniform", [], "All", 0, [], 0, [])
    if ret[0] != 0 or ret[5] == 0:
        pytest.skip("No area loads table or no loads assigned")

    fields = list(ret[4])
    data = list(ret[6])
    nf = len(fields)

    story_idx = fields.index("Story") if "Story" in fields else -1
    pattern_idx = fields.index("Pattern") if "Pattern" in fields else -1
    value_idx = fields.index("Load") if "Load" in fields else -1

    if story_idx < 0 or pattern_idx < 0 or value_idx < 0:
        pytest.skip("Required fields not in area loads table")

    rooftop_ll_values = []
    for i in range(ret[5]):
        row = data[i*nf:(i+1)*nf]
        story = row[story_idx]
        pattern = row[pattern_idx]
        is_rooftop = bool(re.match(r'^R\d*F$', story) or story == "PRF")
        if is_rooftop and pattern == "LL":
            rooftop_ll_values.append((story, abs(float(row[value_idx]))))

    if not rooftop_ll_values:
        pytest.skip("No rooftop LL loads found (model may not have rooftop floors)")

    for story, ll_val in rooftop_ll_values:
        assert abs(ll_val - 0.3) < 0.05, (
            f"Rooftop {story} LL={ll_val}, expected 0.3")


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
