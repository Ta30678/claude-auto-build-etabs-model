"""
QC Phase 1: Verify ETABS model against model_config.json

Checks after /bts-structure (steps 1-6):
  1. Units = TON/M (12)
  2. Story count & heights
  3. Grid count & coordinates
  4. Column count (config vs ETABS)
  5. Wall count (config vs ETABS)
  6. Beam count — B/WB/FB/FWB only (config vs ETABS)
  7. Section definitions completeness
  8. No small beams / no slabs (Phase 2 not yet run)

Usage:
    python -m golden_scripts.qc.qc_phase1 --config model_config.json
"""
import json
import sys
import os
import re
import argparse

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_dir, ".."))  # golden_scripts/


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _connect():
    """Connect to running ETABS, return SapModel."""
    try:
        from find_etabs import find_etabs
        etabs, filename = find_etabs(run=False, backup=False)
        SapModel = etabs.SapModel
    except (ImportError, ModuleNotFoundError):
        import comtypes.client
        etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        SapModel = etabs.SapModel
    SapModel.SetPresentUnits(12)  # TON/M
    return SapModel


def _get_all_frames(SapModel):
    """Return dict with count, names, props, stories."""
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [], [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])
    if isinstance(ret[0], int) and ret[0] > 0:
        return {
            "count": ret[0],
            "names": list(ret[1]),
            "props": list(ret[2]),
            "stories": list(ret[3]),
        }
    return {"count": 0, "names": [], "props": [], "stories": []}


def _read_table(SapModel, table_key):
    """Read a DatabaseTable, return list of dicts (one per record)."""
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        table_key, [], "All", 0, [], 0, [])
    if ret[0] != 0:
        return []
    fields = list(ret[4])
    n_fields = len(fields)
    n_records = ret[5]
    data = list(ret[6])
    rows = []
    for i in range(n_records):
        row = data[i * n_fields: (i + 1) * n_fields]
        rows.append(dict(zip(fields, row)))
    return rows


# ---------------------------------------------------------------------------
# Individual checks — each returns (pass: bool, details: list[str])
# ---------------------------------------------------------------------------

def check_units(SapModel):
    """1. Units = TON/M (12)."""
    units = SapModel.GetPresentUnits()
    ok = units == 12
    details = [f"Units = {units} {'(TON/M)' if ok else '(expected 12)'}"]
    return ok, details


def check_stories(SapModel, config):
    """2. Story names and heights match config."""
    cfg_stories = config.get("stories", [])
    if not cfg_stories:
        return False, ["No stories in config"]

    rows = _read_table(SapModel, "Story Definitions")
    if not rows:
        return False, ["Cannot read Story Definitions table from ETABS"]

    # ETABS table has Name, Height — filter out "Base"
    etabs_stories = {}
    for r in rows:
        name = r.get("Name", "")
        if name.upper() == "BASE":
            continue
        try:
            etabs_stories[name] = float(r.get("Height", 0))
        except (ValueError, TypeError):
            etabs_stories[name] = 0.0

    cfg_names = [s["name"] for s in cfg_stories]
    etabs_names = list(etabs_stories.keys())

    details = []
    ok = True

    # Count
    if len(cfg_names) != len(etabs_names):
        details.append(f"Story count: config={len(cfg_names)}, ETABS={len(etabs_names)}")
        ok = False

    # Name + height comparison
    for s in cfg_stories:
        name = s["name"]
        cfg_h = s["height"]
        if name not in etabs_stories:
            details.append(f"  MISSING in ETABS: {name}")
            ok = False
        else:
            etabs_h = etabs_stories[name]
            if abs(cfg_h - etabs_h) > 0.01:
                details.append(f"  {name}: height config={cfg_h}m, ETABS={etabs_h}m")
                ok = False

    # Extra stories in ETABS
    extra = set(etabs_names) - set(cfg_names)
    if extra:
        details.append(f"  Extra in ETABS: {sorted(extra)}")
        ok = False

    if ok:
        details = [f"Stories: {len(cfg_names)} matched"]

    return ok, details


def check_grids(SapModel, config):
    """3. Grid lines count and coordinates match config."""
    grids_cfg = config.get("grids", {})
    x_cfg = grids_cfg.get("x", [])
    y_cfg = grids_cfg.get("y", [])
    if not x_cfg and not y_cfg:
        return False, ["No grids in config"]

    rows = _read_table(SapModel, "Grid Definitions - Grid Lines")
    if not rows:
        return False, ["Cannot read Grid Definitions table from ETABS"]

    # Parse ETABS grids
    etabs_x = {}  # label -> coordinate
    etabs_y = {}
    for r in rows:
        gtype = r.get("Grid Line Type", "")
        label = r.get("ID", "")
        try:
            coord = float(r.get("Ordinate", 0))
        except (ValueError, TypeError):
            coord = 0.0
        if "X" in gtype:
            etabs_x[label] = coord
        elif "Y" in gtype:
            etabs_y[label] = coord

    details = []
    ok = True

    # X grids
    if len(x_cfg) != len(etabs_x):
        details.append(f"X grids: config={len(x_cfg)}, ETABS={len(etabs_x)}")
        ok = False
    for g in x_cfg:
        label, coord = g["label"], g["coordinate"]
        if label not in etabs_x:
            details.append(f"  X grid MISSING: {label}")
            ok = False
        elif abs(coord - etabs_x[label]) > 0.01:
            details.append(f"  X grid {label}: config={coord}m, ETABS={etabs_x[label]}m")
            ok = False

    # Y grids
    if len(y_cfg) != len(etabs_y):
        details.append(f"Y grids: config={len(y_cfg)}, ETABS={len(etabs_y)}")
        ok = False
    for g in y_cfg:
        label, coord = g["label"], g["coordinate"]
        if label not in etabs_y:
            details.append(f"  Y grid MISSING: {label}")
            ok = False
        elif abs(coord - etabs_y[label]) > 0.01:
            details.append(f"  Y grid {label}: config={coord}m, ETABS={etabs_y[label]}m")
            ok = False

    if ok:
        details = [f"Grids: {len(x_cfg)}X + {len(y_cfg)}Y matched"]

    return ok, details


def check_columns(SapModel, config, all_frames):
    """4. Column count — config (expanded by floors) vs ETABS."""
    cfg_cols = config.get("columns", [])
    expected = sum(len(c.get("floors", [])) for c in cfg_cols)

    actual = sum(1 for p in all_frames["props"]
                 if p.startswith("C") and "X" in p)

    ok = expected == actual
    details = [f"Columns: config={expected}, ETABS={actual}"]
    if not ok:
        details.append(f"  Diff = {actual - expected:+d}")
    return ok, details


def check_walls(SapModel, config):
    """5. Wall count — config (expanded by floors) vs ETABS."""
    cfg_walls = config.get("walls", [])
    expected = sum(len(w.get("floors", [])) for w in cfg_walls)

    # Walls are area objects with W-prefix sections
    rows = _read_table(SapModel, "Area Assignments - Summary")
    actual = 0
    for r in rows:
        sec = r.get("Section", "")
        if re.match(r"^W\d+", sec):
            actual += 1

    ok = expected == actual
    details = [f"Walls: config={expected}, ETABS={actual}"]
    if not ok:
        details.append(f"  Diff = {actual - expected:+d}")
    return ok, details


def check_beams(SapModel, config, all_frames):
    """6. Beam count (B/WB/FB/FWB only, no SB/FSB) — config vs ETABS."""
    cfg_beams = config.get("beams", [])
    expected = sum(len(b.get("floors", [])) for b in cfg_beams)

    # Match B/WB/FB/FWB but NOT SB/FSB
    beam_re = re.compile(r"^(B|WB|FB|FWB)\d+X\d+")
    actual = sum(1 for p in all_frames["props"] if beam_re.match(p))

    ok = expected == actual
    details = [f"Beams (B/WB/FB/FWB): config={expected}, ETABS={actual}"]
    if not ok:
        details.append(f"  Diff = {actual - expected:+d}")
    return ok, details


def check_sections(SapModel, config):
    """7. All config sections defined in ETABS."""
    cfg_sections = config.get("sections", {})
    cfg_frame = set(cfg_sections.get("frame", []))
    cfg_wall = set(cfg_sections.get("wall", []))

    # Read ETABS frame sections
    frame_rows = _read_table(SapModel, "Frame Section Properties")
    etabs_frame = {r.get("Name", "") for r in frame_rows}

    # Read ETABS area sections
    area_rows = _read_table(SapModel, "Area Section Properties")
    etabs_area = {r.get("Name", "") for r in area_rows}

    details = []
    ok = True

    # Frame sections — config lists base names, ETABS has Cfc variants too
    # Check that every config frame section (or its Cfc variants) exists
    from constants import build_strength_lookup, normalize_stories_order
    strength_map = config.get("strength_map", {})
    all_stories = [s["name"] for s in normalize_stories_order(config.get("stories", []))]
    strength_lookup = build_strength_lookup(strength_map, all_stories)
    fc_values = sorted(set(strength_lookup.values())) if strength_lookup else []

    missing_frame = []
    for base_sec in cfg_frame:
        # The section may exist as base or as base + Cfc variants
        found = base_sec in etabs_frame
        if not found:
            # Check Cfc variants
            for fc in fc_values:
                if f"{base_sec}C{fc}" in etabs_frame:
                    found = True
                    break
        if not found:
            missing_frame.append(base_sec)

    if missing_frame:
        details.append(f"  Missing frame sections: {missing_frame}")
        ok = False

    # Wall sections — format W{thickness} → config has thickness as int (e.g. 20)
    missing_wall = []
    for thickness in cfg_wall:
        sec_name = f"W{thickness}"
        # Check base or Cfc variants
        found = sec_name in etabs_area
        if not found:
            for fc in fc_values:
                if f"{sec_name}C{fc}" in etabs_area:
                    found = True
                    break
        if not found:
            missing_wall.append(sec_name)

    if missing_wall:
        details.append(f"  Missing wall sections: {missing_wall}")
        ok = False

    if ok:
        details = [f"Sections: {len(cfg_frame)} frame + {len(cfg_wall)} wall — all defined"]

    return ok, details


def check_no_sb_slabs(SapModel, all_frames):
    """8. No small beams or slabs should exist after Phase 1."""
    sb_re = re.compile(r"^(SB|FSB)\d+X\d+")
    sb_count = sum(1 for p in all_frames["props"] if sb_re.match(p))

    # Slabs = area objects with S or FS prefix (but not W)
    rows = _read_table(SapModel, "Area Assignments - Summary")
    slab_count = 0
    for r in rows:
        sec = r.get("Section", "")
        if re.match(r"^(S|FS)\d+", sec):
            slab_count += 1

    ok = sb_count == 0 and slab_count == 0
    details = []
    if sb_count > 0:
        details.append(f"  Found {sb_count} small beams (SB/FSB) — should be 0 after Phase 1")
    if slab_count > 0:
        details.append(f"  Found {slab_count} slabs (S/FS) — should be 0 after Phase 1")
    if ok:
        details = ["No SB/slabs found (correct for Phase 1)"]

    return ok, details


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    ("1. Units",            check_units),
    ("2. Stories",          check_stories),
    ("3. Grids",            check_grids),
    ("4. Columns",          check_columns),
    ("5. Walls",            check_walls),
    ("6. Beams",            check_beams),
    ("7. Sections",         check_sections),
    ("8. No SB/Slabs",      check_no_sb_slabs),
]


def run_qc(config_path):
    """Run all Phase 1 QC checks. Returns (passed, failed, total)."""
    print("=" * 60)
    print("  QC PHASE 1: Post /bts-structure Verification")
    print("=" * 60)

    # Load config
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    print(f"  Config: {config_path}")

    # Connect
    SapModel = _connect()
    print(f"  ETABS: {SapModel.GetModelFilename()}\n")

    # Cache shared data
    all_frames = _get_all_frames(SapModel)

    passed = 0
    failed = 0

    for label, fn in ALL_CHECKS:
        # Dispatch with appropriate args
        if fn in (check_units,):
            ok, details = fn(SapModel)
        elif fn in (check_stories, check_grids, check_sections):
            ok, details = fn(SapModel, config)
        elif fn in (check_columns, check_beams):
            ok, details = fn(SapModel, config, all_frames)
        elif fn == check_walls:
            ok, details = fn(SapModel, config)
        elif fn == check_no_sb_slabs:
            ok, details = fn(SapModel, all_frames)
        else:
            ok, details = False, ["Unknown check"]

        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {label}")
        for d in details:
            print(f"       {d}")
        print()

        if ok:
            passed += 1
        else:
            failed += 1

    total = passed + failed
    print("=" * 60)
    print(f"  RESULT: {passed}/{total} passed, {failed} failed")
    print("=" * 60)

    return passed, failed, total


def main():
    parser = argparse.ArgumentParser(description="QC Phase 1 — verify ETABS vs config")
    parser.add_argument("--config", required=True, help="Path to model_config.json")
    args = parser.parse_args()
    _passed, failed, _total = run_qc(args.config)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
