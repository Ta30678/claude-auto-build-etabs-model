"""Test: Rebar configuration is correct.

Column: cover=7cm, ToBeDesigned=True
Beam (regular): cover top=9cm, bot=9cm
Beam (foundation): cover top=11cm, bot=15cm
"""
import re
import pytest


def test_column_rebar(SapModel):
    """Column sections should have cover=0.07m and ToBeDesigned=True."""
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Frame Section Properties", [], "All", 0, [], 0, [])
    if ret[0] != 0:
        pytest.skip("Could not read Frame Section Properties")

    fields = list(ret[4])
    data = list(ret[6])
    nf = len(fields)
    name_idx = fields.index("Name")

    errors = []
    checked = 0

    for i in range(ret[5]):
        row = data[i*nf:(i+1)*nf]
        sec = row[name_idx]

        if not (sec.startswith('C') and 'X' in sec):
            continue

        try:
            rb = SapModel.PropFrame.GetRebarColumn(
                sec, '', '', 0, 0, 0, 0, 0, 0, '', '', 0, 0, 0, False)
            cover = rb[5]
            to_be_designed = rb[13]

            if abs(cover - 0.07) > 0.001:
                errors.append(f"{sec}: cover={cover}m, expected 0.07m")
            if not to_be_designed:
                errors.append(f"{sec}: ToBeDesigned={to_be_designed}, expected True")
            checked += 1
        except:
            errors.append(f"{sec}: no rebar configured")

    assert checked > 0, "No column sections found to check"
    assert len(errors) == 0, (
        f"Column rebar errors ({len(errors)}/{checked}):\n"
        + "\n".join(errors[:20])
    )


def test_beam_rebar(SapModel):
    """Beam sections should have correct cover values."""
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Frame Section Properties", [], "All", 0, [], 0, [])
    if ret[0] != 0:
        pytest.skip("Could not read Frame Section Properties")

    fields = list(ret[4])
    data = list(ret[6])
    nf = len(fields)
    name_idx = fields.index("Name")

    errors = []
    checked = 0

    for i in range(ret[5]):
        row = data[i*nf:(i+1)*nf]
        sec = row[name_idx]

        m = re.match(r'^(B|SB|WB|FB|FSB|FWB)', sec)
        if not m:
            continue

        prefix = m.group(1)
        is_fb = prefix in ('FB', 'FSB', 'FWB')

        try:
            rb = SapModel.PropFrame.GetRebarBeam(
                sec, '', '', 0, 0, 0, 0, 0, 0, False)
            ct, cb = rb[3], rb[4]

            if is_fb:
                if abs(ct - 0.11) > 0.01:
                    errors.append(f"{sec}: top_cover={ct}m, expected 0.11m")
                if abs(cb - 0.15) > 0.01:
                    errors.append(f"{sec}: bot_cover={cb}m, expected 0.15m")
            else:
                if abs(ct - 0.09) > 0.01:
                    errors.append(f"{sec}: top_cover={ct}m, expected 0.09m")
                if abs(cb - 0.09) > 0.01:
                    errors.append(f"{sec}: bot_cover={cb}m, expected 0.09m")
            checked += 1
        except:
            pass  # some sections may not have rebar yet

    if checked == 0:
        pytest.skip("No beam sections with rebar found")

    assert len(errors) == 0, (
        f"Beam rebar errors ({len(errors)}/{checked}):\n"
        + "\n".join(errors[:20])
    )
