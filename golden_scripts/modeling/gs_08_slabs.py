"""
Golden Script 08: Slab Placement

- Places slabs from config (defined by corner coordinates)
- Regular slabs (S) use Membrane shell type
- Raft slabs (FS) use ShellThick shell type
- Every beam-enclosed region must have a slab (ensured by config completeness)
"""
import json
import sys
import os

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)                      # modeling/ (sibling imports)
sys.path.insert(0, os.path.dirname(_dir))      # golden_scripts/ (constants)
from constants import build_strength_lookup


def place_slabs(SapModel, config, elev_map, strength_lookup):
    """Place all slabs from config.

    Slabs are placed at plan floor elevation.
    Config must include ALL slab regions (beam-cut slabs already defined by CONFIG-BUILDER).
    """
    slabs = config.get("slabs", [])
    if not slabs:
        print("  No slabs in config.")
        return []

    created = []
    failed = 0

    for slab in slabs:
        corners = slab["corners"]  # list of [x, y]
        base_sec = slab["section"]  # e.g. "S15" or "FS100"
        is_raft = base_sec.startswith("FS")

        n_pts = len(corners)
        X = [c[0] for c in corners]
        Y = [c[1] for c in corners]

        for plan_floor in slab["floors"]:
            z = elev_map.get(plan_floor, None)
            if z is None:
                print(f"  WARN: Unknown floor {plan_floor}, skipping slab {base_sec}")
                failed += 1
                continue

            elem_type = "slab"
            fc = strength_lookup.get((plan_floor, elem_type), 280)
            sec_name = f"{base_sec}C{fc}"

            # FS 2x2 subdivision: split each FS slab into 4 sub-slabs
            if is_raft and n_pts == 4:
                min_x, max_x = min(X), max(X)
                min_y, max_y = min(Y), max(Y)
                mid_x = (min_x + max_x) / 2
                mid_y = (min_y + max_y) / 2
                sub_corners_list = [
                    ([min_x, mid_x, mid_x, min_x], [min_y, min_y, mid_y, mid_y]),
                    ([mid_x, max_x, max_x, mid_x], [min_y, min_y, mid_y, mid_y]),
                    ([min_x, mid_x, mid_x, min_x], [mid_y, mid_y, max_y, max_y]),
                    ([mid_x, max_x, max_x, mid_x], [mid_y, mid_y, max_y, max_y]),
                ]
                for sub_x, sub_y in sub_corners_list:
                    sub_z = [z] * 4
                    ret = SapModel.AreaObj.AddByCoord(4, sub_x, sub_y, sub_z, "", sec_name)
                    if ret[0] == 0:
                        created.append(ret[1])
                    else:
                        print(f"  WARN: Failed FS sub-slab {sec_name} at {plan_floor}")
                        failed += 1
            else:
                Z = [z] * n_pts
                name = ""
                ret = SapModel.AreaObj.AddByCoord(n_pts, X, Y, Z, name, sec_name)
                if ret[0] == 0:
                    created.append(ret[1])
                else:
                    print(f"  WARN: Failed slab {sec_name} at {plan_floor}")
                    failed += 1

    print(f"  Slabs created: {len(created)} (failed: {failed})")
    return created


def run(SapModel, config, elev_map=None, strength_lookup=None):
    """Execute step 08: slab placement."""
    print("=" * 60)
    print("STEP 08: Slab Placement (S, FS)")
    print("=" * 60)

    if elev_map is None:
        from gs_03_grid_stories import define_stories
        elev_map = define_stories(SapModel, config)

    if strength_lookup is None:
        all_stories = [s["name"] for s in config.get("stories", [])]
        strength_lookup = build_strength_lookup(
            config.get("strength_map", {}), all_stories)

    created = place_slabs(SapModel, config, elev_map, strength_lookup)

    SapModel.View.RefreshView(0, False)
    print("Step 08 complete.\n")
    return created


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "model_config.json"
    with open(config_path) as f:
        config = json.load(f)
    from gs_01_init import connect_etabs
    SapModel = connect_etabs(config)
    run(SapModel, config)
