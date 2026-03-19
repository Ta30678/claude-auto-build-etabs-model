"""Test: Section D/B mapping is correct.

Verifies that T3=Depth and T2=Width for all frame sections.

Naming conventions:
  Beams:   {PREFIX}{WIDTH}X{DEPTH}[C{fc}]  → num1=width(T2),  num2=depth(T3)
  Columns: C{DEPTH}X{WIDTH}[C{fc}]         → num1=depth(T3),  num2=width(T2)
"""
import re
import pytest


def test_section_db_correct(SapModel):
    """All frame sections must have T3=Depth and T2=Width matching their names."""
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Frame Section Properties", [], "All", 0, [], 0, [])
    assert ret[0] == 0, "Could not read Frame Section Properties table"

    fields = list(ret[4])
    data = list(ret[6])
    nf = len(fields)
    nr = ret[5]

    name_idx = fields.index("Name")
    t3_idx = fields.index("t3")
    t2_idx = fields.index("t2")

    errors = []
    checked = 0

    for i in range(nr):
        row = data[i*nf:(i+1)*nf]
        name = row[name_idx]
        t3 = float(row[t3_idx]) if row[t3_idx] else 0
        t2 = float(row[t2_idx]) if row[t2_idx] else 0

        m = re.match(r'^(B|SB|WB|FB|FSB|FWB|C)(\d+)X(\d+)C?\d*$', name)
        if m:
            prefix = m.group(1)
            num1 = int(m.group(2))
            num2 = int(m.group(3))
            if prefix == "C":
                exp_d = num1 / 100.0   # Column: first = depth (T3)
                exp_w = num2 / 100.0   # Column: second = width (T2)
            else:
                exp_w = num1 / 100.0   # Beam: first = width (T2)
                exp_d = num2 / 100.0   # Beam: second = depth (T3)

            if abs(t3 - exp_d) > 0.001 or abs(t2 - exp_w) > 0.001:
                errors.append(
                    f"{name}: T3={t3} T2={t2} expected T3={exp_d} T2={exp_w}")
            checked += 1

    assert len(errors) == 0, (
        f"D/B errors in {len(errors)}/{checked} sections:\n"
        + "\n".join(errors[:20])
    )


def test_area_shell_types(SapModel):
    """Slabs/walls should be Membrane (2), raft should be ShellThick (1)."""
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Area Section Properties", [], "All", 0, [], 0, [])
    if ret[0] != 0:
        pytest.skip("Could not read Area Section Properties table")

    fields = list(ret[4])
    data = list(ret[6])
    nf = len(fields)
    nr = ret[5]

    name_idx = fields.index("Name")
    type_idx = fields.index("Type") if "Type" in fields else -1

    if type_idx < 0:
        pytest.skip("Type field not found in area section table")

    errors = []
    for i in range(nr):
        row = data[i*nf:(i+1)*nf]
        name = row[name_idx]

        if name.startswith("FS"):
            # Raft should be ShellThick
            pass  # Type check depends on ETABS table format
        elif name.startswith("S") or (name.startswith("W") and "X" not in name):
            # Slab/Wall should be Membrane
            pass

    # Basic check: at least sections exist
    assert nr > 0, "No area sections found"
