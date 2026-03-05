"""
Add Floor Elements to ETABS Model
Creates columns, beams, walls, and slabs for each floor based on plan-reader output.

Usage: Called by the agent with specific floor data. Not standalone.

Key rules:
  - Columns/Walls: plan NF -> ETABS (N+1)F  (placed between NF and (N+1)F elevation)
  - Beams/Slabs: plan NF -> ETABS NF (placed at NF elevation)
  - Units: TON/M (eUnits=12)
  - Section names include concrete grade suffix: B55X80C350, C90X90C420, etc.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))


def add_columns(SapModel, columns_data, story_elevations, strength_map):
    """Add columns for one floor.

    Args:
        SapModel: ETABS SapModel object
        columns_data: list of dicts with keys:
            - grid_x: X coordinate (m)
            - grid_y: Y coordinate (m)
            - section: base section name e.g. "C90X90"
            - plan_floor: plan floor label e.g. "3F"
        story_elevations: dict mapping story name -> elevation (m)
        strength_map: dict mapping (story, element_type) -> concrete grade e.g. 420

    Returns: list of created column names
    """
    created = []
    for col in columns_data:
        x = col["grid_x"]
        y = col["grid_y"]
        base_sec = col["section"]
        plan_floor = col["plan_floor"]

        # +1 rule: columns on plan NF go from NF elevation to (N+1)F elevation
        z_bot = story_elevations.get(plan_floor, 0)
        # Determine the floor above
        etabs_story = _next_story(plan_floor)
        z_top = story_elevations.get(etabs_story, z_bot + 3.2)  # default 3.2m

        # Get concrete grade for this story
        fc = strength_map.get((plan_floor, "column"), 350)
        sec_name = f"{base_sec}C{fc}"

        name = ""
        ret = SapModel.FrameObj.AddByCoord(x, y, z_bot, x, y, z_top, name, sec_name)
        if ret[0] == 0:
            created.append(ret[1])
        else:
            print(f"  WARN: Failed column at ({x},{y}) {plan_floor}")

    return created


def add_beams(SapModel, beams_data, story_elevations, strength_map):
    """Add beams for one floor.

    Args:
        SapModel: ETABS SapModel object
        beams_data: list of dicts with keys:
            - x1, y1: start point (m)
            - x2, y2: end point (m)
            - section: base section name e.g. "B55X80"
            - plan_floor: plan floor label e.g. "3F"
        story_elevations: dict mapping story name -> elevation (m)
        strength_map: dict mapping (story, element_type) -> concrete grade

    Returns: list of created beam names
    """
    created = []
    for bm in beams_data:
        plan_floor = bm["plan_floor"]
        z = story_elevations.get(plan_floor, 0)

        fc = strength_map.get((plan_floor, "beam"), 350)
        base_sec = bm["section"]
        sec_name = f"{base_sec}C{fc}"

        name = ""
        ret = SapModel.FrameObj.AddByCoord(
            bm["x1"], bm["y1"], z,
            bm["x2"], bm["y2"], z,
            name, sec_name)
        if ret[0] == 0:
            created.append(ret[1])
        else:
            print(f"  WARN: Failed beam {base_sec} at floor {plan_floor}")

    return created


def add_small_beams(SapModel, sb_data, story_elevations, strength_map):
    """Add small beams (SB) based on span subdivision rules.

    sb_data entries have additional keys:
        - position: "mid" | "1/3" | "2/3" | float (fraction along span)
        - span_start: (x, y) of span start
        - span_end: (x, y) of span end
        - direction: "X" or "Y" (beam runs along this axis)
    """
    created = []
    for sb in sb_data:
        plan_floor = sb["plan_floor"]
        z = story_elevations.get(plan_floor, 0)
        fc = strength_map.get((plan_floor, "beam"), 350)
        sec_name = f"{sb['section']}C{fc}"

        # Calculate position along span
        sx, sy = sb["span_start"]
        ex, ey = sb["span_end"]

        pos = sb.get("position", "mid")
        if pos == "mid":
            fractions = [0.5]
        elif pos == "1/3":
            fractions = [1/3]
        elif pos == "2/3":
            fractions = [2/3]
        elif isinstance(pos, str) and "/" in pos:
            fractions = [eval(pos)]
        else:
            fractions = [float(pos)]

        for frac in fractions:
            if sb["direction"] == "X":
                # SB runs along X, positioned at fraction of Y span
                bx1, by1 = sx, sy + (ey - sy) * frac
                bx2, by2 = ex, sy + (ey - sy) * frac
            else:
                # SB runs along Y, positioned at fraction of X span
                bx1, by1 = sx + (ex - sx) * frac, sy
                bx2, by2 = sx + (ex - sx) * frac, ey

            name = ""
            ret = SapModel.FrameObj.AddByCoord(bx1, by1, z, bx2, by2, z, name, sec_name)
            if ret[0] == 0:
                created.append(ret[1])

    return created


def add_walls(SapModel, walls_data, story_elevations, strength_map):
    """Add shear walls for one floor.

    walls_data entries:
        - x1, y1, x2, y2: wall endpoints (m)
        - section: base section e.g. "W20"
        - plan_floor: plan floor label

    +1 rule applies: wall on plan NF spans from NF to (N+1)F elevation.
    """
    created = []
    for wall in walls_data:
        plan_floor = wall["plan_floor"]
        z_bot = story_elevations.get(plan_floor, 0)
        etabs_story = _next_story(plan_floor)
        z_top = story_elevations.get(etabs_story, z_bot + 3.2)

        fc = strength_map.get((plan_floor, "wall"), 350)
        sec_name = f"{wall['section']}C{fc}"

        x1, y1 = wall["x1"], wall["y1"]
        x2, y2 = wall["x2"], wall["y2"]

        # 4-point area: bottom-left, bottom-right, top-right, top-left
        X = [x1, x2, x2, x1]
        Y = [y1, y2, y2, y1]
        Z = [z_bot, z_bot, z_top, z_top]

        name = ""
        ret = SapModel.AreaObj.AddByCoord(4, X, Y, Z, name, sec_name)
        if ret[0] == 0:
            created.append(ret[1])
        else:
            print(f"  WARN: Failed wall at floor {plan_floor}")

    return created


def add_slabs(SapModel, slabs_data, story_elevations, strength_map):
    """Add floor slabs for one floor.

    IMPORTANT: Every beam-enclosed region must have a slab. Do not skip any.

    slabs_data entries:
        - corners: list of (x, y) coordinates defining slab boundary
        - section: base section e.g. "S15" or "FS100"
        - plan_floor: plan floor label
    """
    created = []
    for slab in slabs_data:
        plan_floor = slab["plan_floor"]
        z = story_elevations.get(plan_floor, 0)

        fc = strength_map.get((plan_floor, "slab"), 280)
        sec_name = f"{slab['section']}C{fc}"

        corners = slab["corners"]
        n_pts = len(corners)
        X = [c[0] for c in corners]
        Y = [c[1] for c in corners]
        Z = [z] * n_pts

        name = ""
        ret = SapModel.AreaObj.AddByCoord(n_pts, X, Y, Z, name, sec_name)
        if ret[0] == 0:
            created.append(ret[1])
        else:
            print(f"  WARN: Failed slab at floor {plan_floor}")

    return created


def _next_story(floor_label):
    """Get the next story above a given floor label.
    Examples: '1F'->'2F', 'B1F'->'1F', '3F'->'4F', 'RF'->'PRF'
    """
    import re
    # Basement floors: B3F -> B2F -> B1F -> 1F
    m = re.match(r'^B(\d+)F$', floor_label)
    if m:
        n = int(m.group(1))
        return "1F" if n == 1 else f"B{n-1}F"

    # Regular floors: 1F -> 2F -> ... -> RF -> PRF
    m = re.match(r'^(\d+)F$', floor_label)
    if m:
        n = int(m.group(1))
        return f"{n+1}F"

    if floor_label == "RF":
        return "PRF"

    return floor_label  # fallback


def build_floor(SapModel, floor_data, story_elevations, strength_map):
    """Build all elements for one floor.

    floor_data: dict with keys 'columns', 'beams', 'small_beams', 'walls', 'slabs'
    Returns: summary dict with element counts
    """
    summary = {}

    if "columns" in floor_data:
        cols = add_columns(SapModel, floor_data["columns"],
                          story_elevations, strength_map)
        summary["columns"] = len(cols)
        print(f"  Columns: {len(cols)}")

    if "beams" in floor_data:
        bms = add_beams(SapModel, floor_data["beams"],
                       story_elevations, strength_map)
        summary["beams"] = len(bms)
        print(f"  Beams: {len(bms)}")

    if "small_beams" in floor_data:
        sbs = add_small_beams(SapModel, floor_data["small_beams"],
                             story_elevations, strength_map)
        summary["small_beams"] = len(sbs)
        print(f"  Small beams: {len(sbs)}")

    if "walls" in floor_data:
        wls = add_walls(SapModel, floor_data["walls"],
                       story_elevations, strength_map)
        summary["walls"] = len(wls)
        print(f"  Walls: {len(wls)}")

    if "slabs" in floor_data:
        slbs = add_slabs(SapModel, floor_data["slabs"],
                        story_elevations, strength_map)
        summary["slabs"] = len(slbs)
        print(f"  Slabs: {len(slbs)}")

    return summary
