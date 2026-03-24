"""
Golden Script 10: Load Patterns and Assignments

- Defines standard load patterns (DL, LL, EQXP, EQXN, EQYP, EQYN)
- Assigns slab uniform loads by zone
- Assigns exterior wall line loads (gravity direction, positive value)
- Configures seismic parameters (User Coefficient)
- Imports response spectrum from file
- Assigns foundation springs and restraints
"""
import json
import re
import sys
import os

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)                      # modeling/ (sibling imports)
sys.path.insert(0, os.path.dirname(_dir))      # golden_scripts/ (constants)
from constants import (
    STANDARD_LOAD_PATTERNS, DEFAULT_LOADS, BASE_RESTRAINT,
    EXT_WALL_THICKNESS, EXT_WALL_UNIT_WEIGHT, EXT_WALL_OPENING_FACTOR,
    is_substructure_story, normalize_stories_order,
    parse_frame_section, get_frame_dimensions,
)


def _is_rooftop_story(story_name):
    """Check if a story is a rooftop story (R1F, R2F, R3F, PRF, etc.)."""
    return bool(re.match(r'^R\d*F$', story_name) or story_name == "PRF")


def define_load_patterns(SapModel, config):
    """Define standard load patterns."""
    count = 0
    for name, lp_type, sw_mult in STANDARD_LOAD_PATTERNS:
        ret = SapModel.LoadPatterns.Add(name, lp_type, sw_mult)
        retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
        if retcode == 0:
            count += 1
            print(f"  {name} (type={lp_type}, SW={sw_mult})")
        else:
            print(f"  {name} already exists or returned {retcode}")
    return count


def assign_slab_loads(SapModel, config, elev_map):
    """Assign DL and LL uniform loads to slabs by zone."""
    loads = config.get("loads", {})
    zone_defaults = loads.get("zone_defaults", DEFAULT_LOADS)
    count = 0

    # Apply loads to area objects in ETABS
    # Need to get actual area object names from the model
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Area Assignments - Summary", [], "All", 0, [], 0, [])
        if ret[5] == 0 and ret[3] > 0:
            fields = list(ret[2])
            data = list(ret[4])
            nf = len(fields)
            name_idx = fields.index("UniqueName") if "UniqueName" in fields else 0
            story_idx = fields.index("Story") if "Story" in fields else -1
            sec_idx = fields.index("SectProp") if "SectProp" in fields else (fields.index("Section") if "Section" in fields else -1)

            for i in range(ret[3]):
                row = data[i*nf:(i+1)*nf]
                area_name = row[name_idx]
                story = row[story_idx] if story_idx >= 0 else ""
                section = row[sec_idx] if sec_idx >= 0 else ""

                # Determine zone from section name and story
                is_raft = section.startswith("FS")
                if is_raft:
                    zone = "FS"
                elif _is_rooftop_story(story):
                    zone = "rooftop"
                elif story == "1F":
                    zone = "1F_indoor"
                elif story.startswith("B"):
                    zone = "substructure"
                else:
                    zone = "superstructure"

                zone_loads = zone_defaults.get(zone, {"DL": 0.45, "LL": 0.2})
                dl = zone_loads.get("DL", 0)
                ll = zone_loads.get("LL", 0)

                # Apply loads: negative Z direction (Dir=6=Global-Z, negative value = downward)
                if dl > 0:
                    SapModel.AreaObj.SetLoadUniform(area_name, "DL", -dl, 6)
                    count += 1
                if ll > 0:
                    SapModel.AreaObj.SetLoadUniform(area_name, "LL", -ll, 6)
                    count += 1

            print(f"  Slab loads assigned: {count} load assignments")
        else:
            print("  No area objects found for load assignment.")
    except Exception as e:
        print(f"  WARNING: Could not assign slab loads via database: {e}")
        print("  Slab loads will need to be assigned after elements are created.")


def import_spectrum(SapModel, config):
    """Import response spectrum function from file."""
    loads = config.get("loads", {})
    spectrum_file = loads.get("spectrum_file")

    if not spectrum_file or not os.path.exists(spectrum_file):
        print("  No spectrum file specified or file not found, skipping.")
        return

    periods, sa_values = [], []
    with open(spectrum_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    periods.append(float(parts[0]))
                    sa_values.append(float(parts[1]))
                except ValueError:
                    continue

    if not periods:
        print(f"  No valid spectrum data in {spectrum_file}")
        return

    func_name = "SPEC_FUNC"
    eqv_sf = loads.get("eqv_scale_factor", 1.0)
    try:
        ret = SapModel.Func.FuncRS.SetUser(func_name, len(periods), periods, sa_values, 0.05)
        retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
        if retcode == 0:
            print(f"  RS function '{func_name}' created ({len(periods)} points)")
            if eqv_sf != 1.0:
                print(f"  RS scale factor: {eqv_sf}")

            # Modify existing 0SPECX and 0SPECXY
            for case_name in ["0SPECX", "0SPECXY"]:
                try:
                    SapModel.LoadCases.ResponseSpectrum.SetLoads(
                        case_name, 1, ["U1"], [func_name], [eqv_sf], ["Global"], [0])
                    SapModel.LoadCases.ResponseSpectrum.SetModalCase(case_name, "Modal")
                    SapModel.LoadCases.ResponseSpectrum.SetEccentricity(case_name, 0.05)
                    print(f"  RS case '{case_name}' modified")
                except Exception as e:
                    print(f"  WARNING: Could not modify RS case '{case_name}': {e}")
    except Exception as e:
        print(f"  WARNING: Could not create RS function: {e}")


def _auto_detect_restraint_floor(config):
    """Auto-detect foundation floor (first B*F above BASE)."""
    stories = normalize_stories_order(config.get("stories", []))
    for s in stories:
        name = s["name"]
        if name != "BASE" and is_substructure_story(name):
            return name
    return None


def _point_on_segment(px, py, ax, ay, bx, by, tol=0.3):
    """Check if point (px,py) lies on segment (ax,ay)-(bx,by) within tolerance."""
    abx, aby = bx - ax, by - ay
    ab_len = (abx**2 + aby**2) ** 0.5
    if ab_len < 1e-9:
        return ((px - ax)**2 + (py - ay)**2) ** 0.5 < tol
    t = ((px - ax) * abx + (py - ay) * aby) / (ab_len**2)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * abx, ay + t * aby
    dist = ((px - cx)**2 + (py - cy)**2) ** 0.5
    return dist < tol


def assign_exterior_wall_loads(SapModel, config, elev_map):
    """Assign exterior wall line loads to edge beams on DL pattern.

    w = t * gamma * (H_story - d_beam) * f_opening
    Applied to beams whose both endpoints lie on the exterior_wall outline.
    Outline fallback: config["building_outline"] if loads.exterior_wall.outline absent.
    Floors: all above-ground (1F + superstructure + rooftop); rooftop filtered by outline check.
    """
    loads_cfg = config.get("loads", {})
    ext_wall = loads_cfg.get("exterior_wall", {})
    outline = ext_wall.get("outline")
    if not outline:
        outline = config.get("building_outline")

    if not outline or len(outline) < 3:
        print("  No exterior_wall.outline in config, skipping.")
        return

    t = ext_wall.get("thickness", EXT_WALL_THICKNESS)
    gamma = ext_wall.get("unit_weight", EXT_WALL_UNIT_WEIGHT)
    f_open = ext_wall.get("opening_factor", EXT_WALL_OPENING_FACTOR)

    # Build outline segments (closed polygon)
    n_pts = len(outline)
    segments = [(outline[i], outline[(i + 1) % n_pts]) for i in range(n_pts)]

    # Build story_height_above from elev_map: height from this story to next
    if not elev_map:
        print("  No elev_map available, skipping exterior wall loads.")
        return
    sorted_stories = sorted(elev_map.items(), key=lambda x: x[1])
    story_height_above = {}
    for i in range(len(sorted_stories) - 1):
        s_name, s_elev = sorted_stories[i]
        _, next_elev = sorted_stories[i + 1]
        story_height_above[s_name] = next_elev - s_elev

    # Get all frames from ETABS
    try:
        ret = SapModel.FrameObj.GetAllFrames(
            0, [], [], [], [], [], [], [], [], [], [], [],
            [], [], [], [], [], [], [], [])
    except Exception as e:
        print(f"  WARNING: GetAllFrames failed: {e}")
        return

    if not isinstance(ret[0], int) or ret[0] <= 0:
        print("  No frame objects found.")
        return

    num = ret[0]
    names = ret[1]
    props = ret[2]
    frame_stories = ret[3]
    x1s, y1s = ret[6], ret[7]
    x2s, y2s = ret[9], ret[10]

    count = 0
    for i in range(num):
        story = frame_stories[i]

        # Skip only basement levels (B*F and BASE); rooftop handled by outline check
        if story == "BASE" or re.match(r'^B\d+F$', story):
            continue

        # Parse section — skip columns and non-beam sections
        prefix, num1, num2, _ = parse_frame_section(props[i])
        if prefix is None or prefix == "C":
            continue

        # Check both endpoints on outline
        p1_on = any(_point_on_segment(x1s[i], y1s[i], *seg[0], *seg[1])
                     for seg in segments)
        p2_on = any(_point_on_segment(x2s[i], y2s[i], *seg[0], *seg[1])
                     for seg in segments)
        if not (p1_on and p2_on):
            continue

        # Compute wall load
        h_story = story_height_above.get(story, 0)
        if h_story <= 0:
            continue
        _, depth_cm = get_frame_dimensions(prefix, num1, num2)
        d_beam = depth_cm / 100.0  # cm -> m
        h_net = h_story - d_beam
        if h_net <= 0:
            continue

        w = t * gamma * h_net * f_open
        SapModel.FrameObj.SetLoadDistributed(
            names[i], "DL", 1, 10, 0, 1, w, w)
        count += 1

    print(f"  Exterior wall loads: {count} edge beams"
          f" (t={t}, gamma={gamma}, opening={f_open})")


def assign_foundation(SapModel, config):
    """Assign foundation springs and restraints."""
    foundation = config.get("foundation", {})
    if not foundation:
        print("  No foundation config, skipping.")
        return

    kv = foundation.get("kv")
    kw = foundation.get("kw")
    restraint_floor = foundation.get("restraint_floor")
    if not restraint_floor:
        restraint_floor = _auto_detect_restraint_floor(config)
        if restraint_floor:
            print(f"  Auto-detected restraint_floor: {restraint_floor}")

    # Get foundation level points
    if restraint_floor or kv:
        try:
            # Get all points at the foundation level and assign restraints/springs
            ret = SapModel.DatabaseTables.GetTableForDisplayArray(
                "Point Object Connectivity", [], "All", 0, [], 0, [])
            if ret[5] == 0 and ret[3] > 0:
                fields = list(ret[2])
                data = list(ret[4])
                nf = len(fields)
                name_idx = fields.index("UniqueName") if "UniqueName" in fields else 0
                story_idx = fields.index("Story") if "Story" in fields else -1

                foundation_points = []
                for i in range(ret[3]):
                    row = data[i*nf:(i+1)*nf]
                    pt_name = row[name_idx]
                    pt_story = row[story_idx] if story_idx >= 0 else ""

                    if pt_story == restraint_floor:
                        foundation_points.append(pt_name)

                if foundation_points:
                    # Assign restraints (UX, UY only)
                    r_count = 0
                    for pt in foundation_points:
                        r = SapModel.PointObj.SetRestraint(pt, BASE_RESTRAINT)
                        rc = r[-1] if isinstance(r, (list, tuple)) else r
                        if rc == 0:
                            r_count += 1
                    print(f"  Base restraints (UX,UY): {r_count}/{len(foundation_points)}")

        except Exception as e:
            print(f"  WARNING: Foundation assignment failed: {e}")

    # Area springs (Kv) on FS foundation slabs
    if kv:
        try:
            spring_prop = "FS_Kv"
            SapModel.PropAreaSpring.SetAreaSpringProp(
                spring_prop, 0, 0, kv, 0)

            ret = SapModel.DatabaseTables.GetTableForDisplayArray(
                "Area Assignments - Summary", [], "All", 0, [], 0, [])
            if ret[5] == 0 and ret[3] > 0:
                fields = list(ret[2])
                data = list(ret[4])
                nf = len(fields)
                name_idx = fields.index("UniqueName")
                sec_idx = (fields.index("SectProp")
                           if "SectProp" in fields
                           else fields.index("Section"))
                fs_names = []
                for i in range(ret[3]):
                    row = data[i * nf:(i + 1) * nf]
                    if row[sec_idx].startswith("FS"):
                        fs_names.append(row[name_idx])

                s_count = 0
                for name in fs_names:
                    r = SapModel.AreaObj.SetSpringAssignment(name, spring_prop)
                    rc = r[-1] if isinstance(r, (list, tuple)) else r
                    if rc == 0:
                        s_count += 1
                print(f"  FS area springs (Kv={kv}): {s_count}/{len(fs_names)}")
            else:
                print("  No area objects found for FS spring assignment.")
        except Exception as e:
            print(f"  WARNING: FS area spring assignment failed: {e}")

    # Edge beam line springs — auto-detect FWB (基礎壁梁) beams
    if kw:
        try:
            ret = SapModel.FrameObj.GetAllFrames(
                0, [], [], [], [], [], [], [], [], [], [], [],
                [], [], [], [], [], [], [], [])
            if isinstance(ret[0], int) and ret[0] > 0:
                num = ret[0]
                names = ret[1]
                props = ret[2]
                fwb_names = [names[i] for i in range(num) if props[i].startswith("FWB")]
                if fwb_names:
                    spring_prop = "EdgeSpring"
                    SapModel.PropLineSpring.SetLineSpringProp(spring_prop, 0, kw, 0, 0, 0, 0)
                    s_count = 0
                    for name in fwb_names:
                        r = SapModel.FrameObj.SetSpringAssignment(name, spring_prop)
                        if r == 0:
                            s_count += 1
                    print(f"  Edge beam springs (Kw={kw}): {s_count}/{len(fwb_names)} FWB beams")
                else:
                    print("  No FWB beams found for Kw springs.")
        except Exception as e:
            print(f"  WARNING: Edge beam springs failed: {e}")


def run(SapModel, config, elev_map=None):
    """Execute step 10: loads."""
    print("=" * 60)
    print("STEP 10: Load Patterns & Assignments")
    print("=" * 60)

    if elev_map is None:
        elev_map = {}

    print("\n--- Load Patterns ---")
    define_load_patterns(SapModel, config)

    print("\n--- Slab Loads ---")
    assign_slab_loads(SapModel, config, elev_map)

    print("\n--- Exterior Wall Loads ---")
    assign_exterior_wall_loads(SapModel, config, elev_map)

    print("\n--- Response Spectrum ---")
    import_spectrum(SapModel, config)

    print("\n--- Foundation ---")
    assign_foundation(SapModel, config)

    SapModel.View.RefreshView(0, False)
    print("Step 10 complete.\n")


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "model_config.json"
    with open(config_path) as f:
        config = json.load(f)
    from gs_01_init import connect_etabs
    SapModel = connect_etabs(config)
    run(SapModel, config)
