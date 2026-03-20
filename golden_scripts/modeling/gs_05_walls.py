"""
Golden Script 05: Wall Placement

- Places shear walls from config
- +1 floor rule BUILT IN: walls on plan NF span from NF to (N+1)F elevation
- Diaphragm walls always use C280 regardless of strength_map
- Wall section = "W{thickness}C{fc}"
- Walls are split at beam/column/wall intersections before placement
"""
import json
import math
import sys
import os
import re

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)                      # modeling/ (sibling imports)
sys.path.insert(0, os.path.dirname(_dir))      # golden_scripts/ (constants)
from constants import next_story, build_strength_lookup, normalize_stories_order

# Wall-split constants
EPS = 0.001    # 1mm floating-point epsilon
T_MIN = 0.01   # skip cuts within 1% of wall endpoints (avoid zero-length segments)


def _get_area_sections(SapModel):
    """Query ETABS for all defined area section names."""
    ret = SapModel.PropArea.GetNameList(0, [])
    names = set()
    for item in ret:
        if isinstance(item, (list, tuple)):
            for s in item:
                if isinstance(s, str):
                    names.add(s)
    return names


def _segment_intersection(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
    """Compute intersection point of two line segments.

    Returns (x, y, t_a, t_b) where t_a and t_b are parameter values [0,1]
    on segment A and B respectively, or None if no intersection.
    """
    dax = ax2 - ax1
    day = ay2 - ay1
    dbx = bx2 - bx1
    dby = by2 - by1

    denom = dax * dby - day * dbx
    if abs(denom) < 1e-12:
        return None  # parallel or coincident

    t_a = ((bx1 - ax1) * dby - (by1 - ay1) * dbx) / denom
    t_b = ((bx1 - ax1) * day - (by1 - ay1) * dax) / denom

    if t_a < -1e-9 or t_a > 1 + 1e-9 or t_b < -1e-9 or t_b > 1 + 1e-9:
        return None  # no intersection within segments

    x = ax1 + t_a * dax
    y = ay1 + t_a * day
    return x, y, t_a, t_b


def _point_on_segment_t(px, py, sx1, sy1, sx2, sy2, perp_tol=0.15):
    """Project point onto segment and return parameter t if close enough.

    Returns t in [0, 1] if the point is within perp_tol perpendicular
    distance of the segment, or None otherwise.
    """
    dx = sx2 - sx1
    dy = sy2 - sy1
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < EPS * EPS:
        return None
    t = ((px - sx1) * dx + (py - sy1) * dy) / seg_len_sq
    if t < -1e-9 or t > 1 + 1e-9:
        return None
    # Perpendicular distance
    proj_x = sx1 + t * dx
    proj_y = sy1 + t * dy
    perp_dist = math.hypot(px - proj_x, py - proj_y)
    if perp_dist > perp_tol:
        return None
    return max(0.0, min(1.0, t))


def split_wall_at_intersections(wall, beams, columns, other_walls):
    """Split a wall at beam/column/wall intersection points.

    Cut-point sources:
      - Perpendicular beams: segment intersection
      - Parallel beam endpoints: point-on-segment projection
      - Columns: point-on-segment projection
      - Other walls: segment intersection + endpoint projection

    All sources require floor overlap with the wall.

    Returns list of (x1, y1, x2, y2) sub-wall segments, sorted along
    the wall direction. Returns the original wall if no cuts are found.
    """
    wx1, wy1, wx2, wy2 = wall["x1"], wall["y1"], wall["x2"], wall["y2"]
    w_floors = set(wall.get("floors", []))

    wall_len = math.hypot(wx2 - wx1, wy2 - wy1)
    if wall_len < EPS:
        return [(wx1, wy1, wx2, wy2)]

    # Determine wall direction
    wdx = abs(wx2 - wx1)
    wdy = abs(wy2 - wy1)
    w_dir = "X" if wdx >= wdy else "Y"

    cut_ts = []  # parameter t values along the wall [0, 1]

    # --- Perpendicular beams: segment intersection ---
    for beam in beams:
        b_floors = set(beam.get("floors", []))
        if not (w_floors & b_floors):
            continue
        bdx = abs(beam["x2"] - beam["x1"])
        bdy = abs(beam["y2"] - beam["y1"])
        b_dir = "X" if bdx >= bdy else "Y"

        if b_dir == w_dir:
            # Parallel beam: snap beam endpoints onto wall
            for bpx, bpy in [(beam["x1"], beam["y1"]), (beam["x2"], beam["y2"])]:
                t = _point_on_segment_t(bpx, bpy, wx1, wy1, wx2, wy2)
                if t is not None:
                    cut_ts.append(t)
        else:
            # Perpendicular beam: segment intersection
            result = _segment_intersection(
                wx1, wy1, wx2, wy2,
                beam["x1"], beam["y1"], beam["x2"], beam["y2"])
            if result is not None:
                _, _, t_wall, _ = result
                cut_ts.append(t_wall)

    # --- Columns: point-on-segment projection ---
    for col in columns:
        c_floors = set(col.get("floors", []))
        if not (w_floors & c_floors):
            continue
        cx = col.get("grid_x", col.get("x1", 0))
        cy = col.get("grid_y", col.get("y1", 0))
        t = _point_on_segment_t(cx, cy, wx1, wy1, wx2, wy2)
        if t is not None:
            cut_ts.append(t)

    # --- Other walls: segment intersection + endpoint projection ---
    for ow in other_walls:
        o_floors = set(ow.get("floors", []))
        if not (w_floors & o_floors):
            continue
        # Segment intersection
        result = _segment_intersection(
            wx1, wy1, wx2, wy2,
            ow["x1"], ow["y1"], ow["x2"], ow["y2"])
        if result is not None:
            _, _, t_wall, _ = result
            cut_ts.append(t_wall)
        # Endpoint projection
        for opx, opy in [(ow["x1"], ow["y1"]), (ow["x2"], ow["y2"])]:
            t = _point_on_segment_t(opx, opy, wx1, wy1, wx2, wy2)
            if t is not None:
                cut_ts.append(t)

    # --- Filter and sort cut points ---
    # Remove cuts too close to wall endpoints (avoid zero-length segments)
    cut_ts = [t for t in cut_ts if T_MIN < t < 1.0 - T_MIN]
    if not cut_ts:
        return [(wx1, wy1, wx2, wy2)]

    # Deduplicate (merge cuts within EPS)
    cut_ts.sort()
    deduped = [cut_ts[0]]
    for t in cut_ts[1:]:
        if t - deduped[-1] > EPS:
            deduped.append(t)
    cut_ts = deduped

    # --- Build sub-wall segments ---
    t_points = [0.0] + cut_ts + [1.0]
    segments = []
    for i in range(len(t_points) - 1):
        t0 = t_points[i]
        t1 = t_points[i + 1]
        sx1 = wx1 + t0 * (wx2 - wx1)
        sy1 = wy1 + t0 * (wy2 - wy1)
        sx2 = wx1 + t1 * (wx2 - wx1)
        sy2 = wy1 + t1 * (wy2 - wy1)
        seg_len = math.hypot(sx2 - sx1, sy2 - sy1)
        if seg_len > EPS:
            segments.append((
                round(sx1, 6), round(sy1, 6),
                round(sx2, 6), round(sy2, 6),
            ))

    return segments if segments else [(wx1, wy1, wx2, wy2)]


def place_walls(SapModel, config, elev_map, strength_lookup, all_stories=None):
    """Place all walls from config, splitting at intersections.

    +1 rule: wall on plan NF spans from NF elevation to (N+1)F elevation.
    Diaphragm walls override concrete grade to C280.
    Walls are split at beam/column/wall intersections before placement.
    """
    walls = config.get("walls", [])
    if not walls:
        print("  No walls in config.")
        return []

    beams = config.get("beams", []) + config.get("small_beams", [])
    columns = config.get("columns", [])

    available_sections = _get_area_sections(SapModel)
    created = []
    failed = 0
    fail_details = []
    total_sub_walls = 0

    for i, wall in enumerate(walls):
        base_sec = wall["section"]  # e.g. "W20" or "W20C350"
        is_diaphragm = wall.get("is_diaphragm_wall", False)

        # Split wall at intersections
        other_walls = walls[:i] + walls[i + 1:]
        sub_walls = split_wall_at_intersections(wall, beams, columns, other_walls)
        total_sub_walls += len(sub_walls)

        for sx1, sy1, sx2, sy2 in sub_walls:
            for plan_floor in wall["floors"]:
                z_bot = elev_map.get(plan_floor, None)
                target_story = next_story(plan_floor, all_stories)
                z_top = elev_map.get(target_story, None)

                if z_bot is None or z_top is None:
                    print(f"  WARN: Unknown floor {plan_floor}->{target_story}, skipping wall")
                    failed += 1
                    continue

                # Section full name compatibility
                if re.search(r'C\d+$', base_sec):
                    sec_name = base_sec
                else:
                    # Diaphragm walls use C280; otherwise use strength_map
                    if is_diaphragm:
                        fc = 280
                    else:
                        fc = strength_lookup.get((plan_floor, "wall"), 350)
                    sec_name = f"{base_sec}C{fc}"

                # 4-point area: bottom-left, bottom-right, top-right, top-left
                X = [sx1, sx2, sx2, sx1]
                Y = [sy1, sy2, sy2, sy1]
                Z = [z_bot, z_bot, z_top, z_top]

                name = ""
                ret = SapModel.AreaObj.AddByCoord(4, X, Y, Z, name, sec_name)
                if ret[-1] == 0:
                    created.append(ret[0])
                else:
                    if sec_name not in available_sections:
                        base = re.sub(r'C\d+$', '', sec_name)
                        similar = sorted([s for s in available_sections if s.startswith(base)])[:5]
                        print(f"  ERROR: Section '{sec_name}' not in ETABS. Available: {similar}. Check sections.wall or strength_map.")
                    else:
                        print(f"  WARN: Failed wall {sec_name} at {plan_floor}")
                    fail_details.append((sec_name, plan_floor, f"({sx1},{sy1})->({sx2},{sy2})"))
                    failed += 1

    total = len(created) + failed
    split_count = total_sub_walls - len(walls)
    if split_count > 0:
        print(f"  Wall split: {len(walls)} walls → {total_sub_walls} sub-walls (+{split_count} from splitting)")
    print(f"  Walls created: {len(created)} (failed: {failed})")
    if fail_details:
        print(f"  Failed walls:")
        for sec, fl, coord in fail_details[:10]:
            print(f"    {sec} at {fl} {coord}")
        if len(fail_details) > 10:
            print(f"    ... and {len(fail_details) - 10} more")
    if total > 0 and failed / total > 0.5:
        raise RuntimeError(f"gs_05: {failed}/{total} walls failed (>50%). Aborting.")
    return created


def run(SapModel, config, elev_map=None, strength_lookup=None):
    """Execute step 05: wall placement."""
    print("=" * 60)
    print("STEP 05: Wall Placement (+1 rule)")
    print("=" * 60)

    if elev_map is None:
        from gs_03_grid_stories import define_stories
        elev_map = define_stories(SapModel, config)

    all_stories = [s["name"] for s in normalize_stories_order(config.get("stories", []))]

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
