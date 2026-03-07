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

sys.path.insert(0, os.path.dirname(__file__))
from constants import (
    STANDARD_LOAD_PATTERNS, DEFAULT_LOADS, BASE_RESTRAINT,
    EXT_WALL_THICKNESS, EXT_WALL_UNIT_WEIGHT, EXT_WALL_OPENING_FACTOR,
)


def _is_rooftop_story(story_name):
    """Check if a story is a rooftop story (R1F, R2F, R3F, PRF, etc.)."""
    return bool(re.match(r'^R\d*F$', story_name) or story_name == "PRF")


def define_load_patterns(SapModel, config):
    """Define standard load patterns."""
    count = 0
    for name, lp_type, sw_mult in STANDARD_LOAD_PATTERNS:
        ret = SapModel.LoadPatterns.Add(name, lp_type, sw_mult)
        if ret == 0:
            count += 1
            print(f"  {name} (type={lp_type}, SW={sw_mult})")
        else:
            print(f"  {name} may already exist")
    return count


def configure_seismic(SapModel, config):
    """Configure seismic load patterns using User Coefficient method."""
    loads = config.get("loads", {})
    seismic = loads.get("seismic", {})

    c_value = seismic.get("base_shear_c")
    if c_value is None:
        print("  No base_shear_c in config, skipping seismic configuration.")
        return

    top = seismic.get("top_story", "PRF")
    bot = seismic.get("bottom_story", "1F")
    ecc = seismic.get("ecc_ratio", 0.05)
    k = seismic.get("k_exponent", 1)

    eq_configs = [
        ("EQXP", 1, 1),
        ("EQXN", 1, -1),
        ("EQYP", 2, 1),
        ("EQYN", 2, -1),
    ]

    for name, direction, sign in eq_configs:
        try:
            SapModel.LoadPatterns.AutoSeismic.SetUserCoefficient(
                name, direction, ecc, sign * c_value, k, top, bot)
            print(f"  {name}: dir={direction}, C={sign*c_value}, ecc={ecc}, K={k}")
        except Exception as e:
            print(f"  WARNING: Failed {name}: {e}")


def assign_slab_loads(SapModel, config, elev_map):
    """Assign DL and LL uniform loads to slabs by zone."""
    slabs = config.get("slabs", [])
    loads = config.get("loads", {})
    zone_defaults = loads.get("zone_defaults", DEFAULT_LOADS)

    if not slabs:
        print("  No slabs to assign loads to.")
        return

    # Get all area objects to find slab names
    count = 0
    stories = config.get("stories", [])
    story_names = [s["name"] for s in stories]

    # Determine zone for each floor
    for slab in slabs:
        base_sec = slab["section"]
        is_raft = base_sec.startswith("FS")

        for plan_floor in slab["floors"]:
            if is_raft:
                zone = "FS"
            elif _is_rooftop_story(plan_floor):
                zone = "rooftop"
            elif plan_floor == "1F":
                zone = "1F_indoor"
            elif plan_floor.startswith("B"):
                zone = "substructure"
            else:
                zone = "superstructure"

            zone_loads = zone_defaults.get(zone, {"DL": 0.45, "LL": 0.2})
            dl = zone_loads.get("DL", 0)
            ll = zone_loads.get("LL", 0)
            # Loads will be applied after slabs are created
            # Store for reference
            slab.setdefault("_zone_loads", {})[plan_floor] = {"DL": dl, "LL": ll, "zone": zone}

    # Apply loads to area objects in ETABS
    # Need to get actual area object names from the model
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Area Assignments - Summary", [], "All", 0, [], 0, [])
        if ret[0] == 0 and ret[5] > 0:
            fields = list(ret[4])
            data = list(ret[6])
            nf = len(fields)
            name_idx = fields.index("UniqueName") if "UniqueName" in fields else 0
            story_idx = fields.index("Story") if "Story" in fields else -1
            sec_idx = fields.index("Section") if "Section" in fields else -1

            for i in range(ret[5]):
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
    try:
        ret = SapModel.Func.FuncRS.SetUser(func_name, len(periods), periods, sa_values, 0.05)
        if ret == 0:
            print(f"  RS function '{func_name}' created ({len(periods)} points)")

            # Modify existing 0SPECX and 0SPECXY
            for case_name in ["0SPECX", "0SPECXY"]:
                try:
                    SapModel.LoadCases.ResponseSpectrum.SetLoads(
                        case_name, 1, ["U1"], [func_name], [1.0], ["Global"], [0])
                    SapModel.LoadCases.ResponseSpectrum.SetModalCase(case_name, "Modal")
                    SapModel.LoadCases.ResponseSpectrum.SetEccentricity(case_name, 0.05)
                    print(f"  RS case '{case_name}' modified")
                except Exception as e:
                    print(f"  WARNING: Could not modify RS case '{case_name}': {e}")
    except Exception as e:
        print(f"  WARNING: Could not create RS function: {e}")


def assign_foundation(SapModel, config):
    """Assign foundation springs and restraints."""
    foundation = config.get("foundation", {})
    if not foundation:
        print("  No foundation config, skipping.")
        return

    kv = foundation.get("kv")
    kw = foundation.get("kw")
    restraint_floor = foundation.get("restraint_floor")

    # Get foundation level points
    if restraint_floor or kv:
        try:
            # Get all points at the foundation level and assign restraints/springs
            ret = SapModel.DatabaseTables.GetTableForDisplayArray(
                "Joint Coordinates", [], "All", 0, [], 0, [])
            if ret[0] == 0 and ret[5] > 0:
                fields = list(ret[4])
                data = list(ret[6])
                nf = len(fields)
                name_idx = fields.index("UniqueName") if "UniqueName" in fields else 0
                story_idx = fields.index("Story") if "Story" in fields else -1

                foundation_points = []
                for i in range(ret[5]):
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
                        if r == 0:
                            r_count += 1
                    print(f"  Base restraints (UX,UY): {r_count}/{len(foundation_points)}")

                    # Assign vertical springs
                    if kv:
                        springs = [0, 0, kv, 0, 0, 0]
                        s_count = 0
                        for pt in foundation_points:
                            r = SapModel.PointObj.SetSpring(pt, springs)
                            if r == 0:
                                s_count += 1
                        print(f"  Point springs (Kv={kv}): {s_count}/{len(foundation_points)}")
        except Exception as e:
            print(f"  WARNING: Foundation assignment failed: {e}")

    # Edge beam line springs
    if kw:
        edge_beams = foundation.get("edge_beams", [])
        if edge_beams:
            try:
                spring_prop = "EdgeSpring"
                SapModel.PropLineSpring.SetLineSpringProp(spring_prop, 0, kw, 0, 0, 0, 0)
                s_count = 0
                for beam in edge_beams:
                    r = SapModel.FrameObj.SetSpringAssignment(beam, spring_prop)
                    if r == 0:
                        s_count += 1
                print(f"  Edge beam springs (Kw={kw}): {s_count}/{len(edge_beams)}")
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

    print("\n--- Seismic Configuration ---")
    configure_seismic(SapModel, config)

    print("\n--- Slab Loads ---")
    assign_slab_loads(SapModel, config, elev_map)

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
