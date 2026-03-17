"""
Golden Script 04: Column Placement

- Places columns from config at grid intersections
- +1 floor rule BUILT IN: columns on plan NF span from NF to (N+1)F elevation
- Concrete grade from strength_map per floor
- Section name = base_section + "C" + fc_grade
"""
import json
import sys
import os
import re

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)                      # modeling/ (sibling imports)
sys.path.insert(0, os.path.dirname(_dir))      # golden_scripts/ (constants)
from constants import next_story, build_strength_lookup


def _get_frame_sections(SapModel):
    """Query ETABS for all defined frame section names."""
    ret = SapModel.PropFrame.GetNameList(0, [])
    names = set()
    for item in ret:
        if isinstance(item, (list, tuple)):
            for s in item:
                if isinstance(s, str):
                    names.add(s)
    return names


def place_columns(SapModel, config, elev_map, strength_lookup, all_stories=None):
    """Place all columns from config.

    +1 rule: a column on plan floor NF is placed from elevation(NF) to elevation(next_story(NF)).
    """
    columns = config.get("columns", [])
    if not columns:
        print("  No columns in config.")
        return []

    available_sections = _get_frame_sections(SapModel)
    created = []
    failed = 0
    fail_details = []

    for col in columns:
        x = col["grid_x"]
        y = col["grid_y"]
        base_sec = col["section"]  # e.g. "C90X90" or "C90X90C350"

        for plan_floor in col["floors"]:
            # +1 rule: column bottom at plan_floor, top at next story
            z_bot = elev_map.get(plan_floor, None)
            target_story = next_story(plan_floor, all_stories)
            z_top = elev_map.get(target_story, None)

            if z_bot is None or z_top is None:
                print(f"  WARN: Unknown floor {plan_floor}->{target_story}, skipping column at ({x},{y})")
                failed += 1
                continue

            # Section full name compatibility
            if re.search(r'C\d+$', base_sec):
                sec_name = base_sec
            else:
                fc = strength_lookup.get((plan_floor, "column"), 350)
                sec_name = f"{base_sec}C{fc}"

            name = ""
            ret = SapModel.FrameObj.AddByCoord(x, y, z_bot, x, y, z_top, name, sec_name)
            if ret[-1] == 0:
                created.append(ret[0])
            else:
                if sec_name not in available_sections:
                    base = re.sub(r'C\d+$', '', sec_name)
                    similar = sorted([s for s in available_sections if s.startswith(base)])[:5]
                    print(f"  ERROR: Section '{sec_name}' not in ETABS. Available: {similar}. Check sections.frame or strength_map.")
                else:
                    print(f"  WARN: Failed column {sec_name} at ({x},{y}) {plan_floor}")
                fail_details.append((sec_name, plan_floor, f"({x},{y})"))
                failed += 1

    total = len(created) + failed
    print(f"  Columns created: {len(created)} (failed: {failed})")
    if fail_details:
        print(f"  Failed columns:")
        for sec, fl, coord in fail_details[:10]:
            print(f"    {sec} at {fl} {coord}")
        if len(fail_details) > 10:
            print(f"    ... and {len(fail_details) - 10} more")
    if total > 0 and failed / total > 0.5:
        raise RuntimeError(f"gs_04: {failed}/{total} columns failed (>50%). Aborting.")
    return created


def run(SapModel, config, elev_map=None, strength_lookup=None):
    """Execute step 04: column placement."""
    print("=" * 60)
    print("STEP 04: Column Placement (+1 rule)")
    print("=" * 60)

    if elev_map is None:
        from gs_03_grid_stories import define_stories
        elev_map = define_stories(SapModel, config)

    all_stories = [s["name"] for s in reversed(config.get("stories", []))]

    if strength_lookup is None:
        strength_lookup = build_strength_lookup(
            config.get("strength_map", {}), all_stories)

    created = place_columns(SapModel, config, elev_map, strength_lookup, all_stories)

    SapModel.View.RefreshView(0, False)
    print("Step 04 complete.\n")
    return created


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "model_config.json"
    with open(config_path) as f:
        config = json.load(f)
    from gs_01_init import connect_etabs
    SapModel = connect_etabs(config)
    run(SapModel, config)
