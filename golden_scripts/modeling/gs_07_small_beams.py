"""
Golden Script 07: Small Beam Placement

- Places small beams (SB) from config
- Coordinates are explicit (from SB-READER pixel measurement)
- No guessing or interpolation by AI at runtime
"""
import json
import sys
import os

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)                      # modeling/ (sibling imports)
sys.path.insert(0, os.path.dirname(_dir))      # golden_scripts/ (constants)
from constants import build_strength_lookup


def place_small_beams(SapModel, config, elev_map, strength_lookup):
    """Place all small beams from config.

    Small beams have explicit x1,y1,x2,y2 coordinates from SB-READER.
    They are placed at plan floor elevation (no +1 rule).
    """
    small_beams = config.get("small_beams", [])
    if not small_beams:
        print("  No small beams in config.")
        return []

    created = []
    failed = 0

    for sb in small_beams:
        x1, y1 = sb["x1"], sb["y1"]
        x2, y2 = sb["x2"], sb["y2"]
        base_sec = sb["section"]  # e.g. "SB30X50"

        for plan_floor in sb["floors"]:
            z = elev_map.get(plan_floor, None)
            if z is None:
                print(f"  WARN: Unknown floor {plan_floor}, skipping SB {base_sec}")
                failed += 1
                continue

            fc = strength_lookup.get((plan_floor, "beam"), 280)
            sec_name = f"{base_sec}C{fc}"

            name = ""
            ret = SapModel.FrameObj.AddByCoord(x1, y1, z, x2, y2, z, name, sec_name)
            if ret[0] == 0:
                created.append(ret[1])
            else:
                print(f"  WARN: Failed SB {sec_name} at {plan_floor}")
                failed += 1

    print(f"  Small beams created: {len(created)} (failed: {failed})")
    return created


def run(SapModel, config, elev_map=None, strength_lookup=None):
    """Execute step 07: small beam placement."""
    print("=" * 60)
    print("STEP 07: Small Beam Placement (SB)")
    print("=" * 60)

    if elev_map is None:
        from gs_03_grid_stories import define_stories
        elev_map = define_stories(SapModel, config)

    if strength_lookup is None:
        all_stories = [s["name"] for s in config.get("stories", [])]
        strength_lookup = build_strength_lookup(
            config.get("strength_map", {}), all_stories)

    created = place_small_beams(SapModel, config, elev_map, strength_lookup)

    SapModel.View.RefreshView(0, False)
    print("Step 07 complete.\n")
    return created


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "model_config.json"
    with open(config_path) as f:
        config = json.load(f)
    from gs_01_init import connect_etabs
    SapModel = connect_etabs(config)
    run(SapModel, config)
