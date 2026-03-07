"""Test: Stiffness modifiers are correctly assigned.

Beam:   [1, 1, 1, 0.0001, 0.7, 0.7, 0.8, 0.8]
Column: [1, 1, 1, 0.0001, 0.7, 0.7, 0.95, 0.95]
"""
import pytest


BEAM_EXPECTED = {3: 0.0001, 4: 0.7, 5: 0.7, 6: 0.8, 7: 0.8}
COL_EXPECTED  = {3: 0.0001, 4: 0.7, 5: 0.7, 6: 0.95, 7: 0.95}


def test_frame_modifiers(SapModel, all_frames):
    """Spot-check frame modifiers on first 50 frames."""
    if all_frames["count"] == 0:
        pytest.skip("No frames in model")

    names = all_frames["names"]
    props = all_frames["props"]
    errors = []
    checked = 0

    for i in range(min(50, len(names))):
        mod_ret = SapModel.FrameObj.GetModifiers(names[i], [])
        if mod_ret[0] != 0:
            continue

        mods = list(mod_ret[1])
        is_col = (props[i].startswith('C') and 'X' in props[i]
                  and not props[i].startswith('CB'))

        expected = COL_EXPECTED if is_col else BEAM_EXPECTED
        for idx, exp_val in expected.items():
            if abs(mods[idx] - exp_val) > 0.01:
                errors.append(
                    f"{names[i]} ({props[i]}): mods[{idx}]={mods[idx]}, expected {exp_val}")
                break
        checked += 1

    assert len(errors) == 0, (
        f"Modifier errors in {len(errors)}/{checked} frames:\n"
        + "\n".join(errors[:20])
    )


def test_area_modifiers(SapModel):
    """Check area section property modifiers."""
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Area Section Properties", [], "All", 0, [], 0, [])
    if ret[0] != 0:
        pytest.skip("Could not read Area Section Properties")

    fields = list(ret[4])
    data = list(ret[6])
    nf = len(fields)
    name_idx = fields.index("Name")

    errors = []
    for i in range(ret[5]):
        row = data[i*nf:(i+1)*nf]
        sec_name = row[name_idx]

        mod_ret = SapModel.PropArea.GetModifiers(sec_name, [])
        if mod_ret[0] != 0:
            continue

        mods = list(mod_ret[1])
        is_raft = sec_name.startswith("FS")

        # Check f11 (membrane modifier)
        if abs(mods[0] - 0.4) > 0.01:
            errors.append(f"{sec_name}: f11={mods[0]}, expected 0.4")
            continue

        # Check m11 (bending modifier)
        if is_raft and abs(mods[3] - 0.7) > 0.01:
            errors.append(f"{sec_name}: m11={mods[3]}, expected 0.7 (raft)")
        elif not is_raft and abs(mods[3] - 1.0) > 0.01:
            errors.append(f"{sec_name}: m11={mods[3]}, expected 1.0 (slab/wall)")

    assert len(errors) == 0, (
        f"Area modifier errors:\n" + "\n".join(errors[:20])
    )
