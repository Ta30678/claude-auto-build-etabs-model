"""
Golden Script 05: Wall Placement

- Places shear walls from config
- +1 floor rule BUILT IN: walls on plan NF span from NF to (N+1)F elevation
- Diaphragm walls always use C280 regardless of strength_map
- Wall section = "W{thickness}C{fc}"
"""
import json
import sys
import os

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)                      # modeling/ (sibling imports)
sys.path.insert(0, os.path.dirname(_dir))      # golden_scripts/ (constants)
from constants import next_story, build_strength_lookup


def place_walls(SapModel, config, elev_map, strength_lookup, all_stories=None):
    """Place all walls from config.

    +1 rule: wall on plan NF spans from NF elevation to (N+1)F elevation.
    Diaphragm walls override concrete grade to C280.
    """
    walls = config.get("walls", [])
    if not walls:
        print("  No walls in config.")
        return []

    created = []
    failed = 0

    for wall in walls:
        x1, y1 = wall["x1"], wall["y1"]
        x2, y2 = wall["x2"], wall["y2"]
        base_sec = wall["section"]  # e.g. "W20"
        is_diaphragm = wall.get("is_diaphragm_wall", False)

        for plan_floor in wall["floors"]:
            z_bot = elev_map.get(plan_floor, None)
            target_story = next_story(plan_floor, all_stories)
            z_top = elev_map.get(target_story, None)

            if z_bot is None or z_top is None:
                print(f"  WARN: Unknown floor {plan_floor}->{target_story}, skipping wall")
                failed += 1
                continue

            # Diaphragm walls use C280; otherwise use strength_map
            if is_diaphragm:
                fc = 280
            else:
                fc = strength_lookup.get((plan_floor, "wall"), 350)

            sec_name = f"{base_sec}C{fc}"

            # 4-point area: bottom-left, bottom-right, top-right, top-left
            X = [x1, x2, x2, x1]
            Y = [y1, y2, y2, y1]
            Z = [z_bot, z_bot, z_top, z_top]

            name = ""
            ret = SapModel.AreaObj.AddByCoord(4, X, Y, Z, name, sec_name)
            if ret[-1] == 0:
                created.append(ret[0])
            else:
                print(f"  WARN: Failed wall {sec_name} at {plan_floor}")
                failed += 1

    print(f"  Walls created: {len(created)} (failed: {failed})")
    return created


def run(SapModel, config, elev_map=None, strength_lookup=None):
    """Execute step 05: wall placement."""
    print("=" * 60)
    print("STEP 05: Wall Placement (+1 rule)")
    print("=" * 60)

    if elev_map is None:
        from gs_03_grid_stories import define_stories
        elev_map = define_stories(SapModel, config)

    all_stories = [s["name"] for s in config.get("stories", [])]

    if strength_lookup is None:
        strength_lookup = build_strength_lookup(
            config.get("strength_map", {}), all_stories)

    created = place_walls(SapModel, config, elev_map, strength_lookup, all_stories)

    SapModel.View.RefreshView(0, False)
    print("Step 05 complete.\n")
    return created


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "model_config.json"
    with open(config_path) as f:
        config = json.load(f)
    from gs_01_init import connect_etabs
    SapModel = connect_etabs(config)
    run(SapModel, config)
