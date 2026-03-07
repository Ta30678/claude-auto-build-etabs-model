"""
Golden Script 06: Beam Placement (Major beams, Wall beams, Foundation beams)

- Places beams from config at plan floor elevation
- Section name = base_section + "C" + fc_grade from strength_map
- Beams are horizontal: z1 = z2 = story elevation
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from constants import build_strength_lookup


def place_beams(SapModel, config, elev_map, strength_lookup):
    """Place all beams (B, WB, FB) from config.

    Beams are placed at the plan floor elevation (no +1 rule for beams).
    """
    beams = config.get("beams", [])
    if not beams:
        print("  No beams in config.")
        return []

    created = []
    failed = 0

    for bm in beams:
        x1, y1 = bm["x1"], bm["y1"]
        x2, y2 = bm["x2"], bm["y2"]
        base_sec = bm["section"]  # e.g. "B55X80", "WB50X70", "FB90X230"

        for plan_floor in bm["floors"]:
            z = elev_map.get(plan_floor, None)
            if z is None:
                print(f"  WARN: Unknown floor {plan_floor}, skipping beam {base_sec}")
                failed += 1
                continue

            fc = strength_lookup.get((plan_floor, "beam"), 350)
            sec_name = f"{base_sec}C{fc}"

            name = ""
            ret = SapModel.FrameObj.AddByCoord(x1, y1, z, x2, y2, z, name, sec_name)
            if ret[0] == 0:
                created.append(ret[1])
            else:
                print(f"  WARN: Failed beam {sec_name} at {plan_floor}")
                failed += 1

    print(f"  Beams created: {len(created)} (failed: {failed})")
    return created


def run(SapModel, config, elev_map=None, strength_lookup=None):
    """Execute step 06: beam placement."""
    print("=" * 60)
    print("STEP 06: Beam Placement (B, WB, FB)")
    print("=" * 60)

    if elev_map is None:
        from gs_03_grid_stories import define_stories
        elev_map = define_stories(SapModel, config)

    if strength_lookup is None:
        all_stories = [s["name"] for s in config.get("stories", [])]
        strength_lookup = build_strength_lookup(
            config.get("strength_map", {}), all_stories)

    created = place_beams(SapModel, config, elev_map, strength_lookup)

    SapModel.View.RefreshView(0, False)
    print("Step 06 complete.\n")
    return created


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "model_config.json"
    with open(config_path) as f:
        config = json.load(f)
    from gs_01_init import connect_etabs
    SapModel = connect_etabs(config)
    run(SapModel, config)
