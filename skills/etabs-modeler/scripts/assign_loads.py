"""
Assign loads to ETABS model elements.
Covers: load patterns, slab uniform loads, beam line loads, response spectrum.

Usage: Called by the agent after elements and properties are assigned.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))


# ── Load Pattern Definitions ─────────────────────────────────

def define_load_patterns(SapModel, patterns=None):
    """Define standard load patterns.

    patterns: list of (name, type_code, sw_mult) or None for defaults.
    eLoadPatternType: Dead=1, SuperDead=2, Live=3, ReduceLive=4, Quake=5, Wind=6
    """
    if patterns is None:
        patterns = [
            ("Dead", 1, 1),    # Dead with self-weight multiplier = 1
            ("SDL",  2, 0),    # Super dead (no self-weight)
            ("Live", 3, 0),    # Live
            ("EQX",  5, 0),    # Seismic X
            ("EQY",  5, 0),    # Seismic Y
        ]

    count = 0
    for name, lp_type, sw_mult in patterns:
        ret = SapModel.LoadPatterns.Add(name, lp_type, sw_mult)
        if ret == 0:
            count += 1
            print(f"  Load pattern: {name} (type={lp_type}, SW={sw_mult})")
        else:
            print(f"  Load pattern '{name}' may already exist (ret={ret})")
    return count


# ── Slab Uniform Loads ───────────────────────────────────────

def assign_slab_loads(SapModel, slab_names, sdl_value, live_value):
    """Assign SDL and Live uniform loads to slabs.

    Args:
        slab_names: list of area object names
        sdl_value: SDL load in ton/m2 (positive value, applied as negative Z)
        live_value: Live load in ton/m2 (positive value, applied as negative Z)
    """
    count = 0
    for slab in slab_names:
        if sdl_value > 0:
            ret = SapModel.AreaObj.SetLoadUniform(slab, "SDL", -sdl_value, 6)
            if ret == 0:
                count += 1
        if live_value > 0:
            ret = SapModel.AreaObj.SetLoadUniform(slab, "Live", -live_value, 6)
            if ret == 0:
                count += 1

    print(f"  Slab loads assigned: {count} (SDL={sdl_value}, Live={live_value} ton/m2)")
    return count


# ── Beam Line Loads (Wall Weight) ────────────────────────────

def calculate_beam_line_load(story_height_m, beam_depth_m,
                             wall_thickness=0.15, unit_weight=2.4, factor=0.6):
    """Calculate beam line load from wall weight above.

    Formula: w = unit_weight * wall_thickness * factor * (story_height - beam_depth)

    Args:
        story_height_m: height of the story above (m)
        beam_depth_m: beam depth (m)
        wall_thickness: wall thickness (m), default 0.15
        unit_weight: concrete unit weight (ton/m3), default 2.4
        factor: reduction factor, default 0.6

    Returns: line load in ton/m
    """
    clear_height = story_height_m - beam_depth_m
    if clear_height <= 0:
        return 0
    return unit_weight * wall_thickness * factor * clear_height


def assign_beam_line_loads(SapModel, beams_with_depth, story_heights):
    """Assign SDL line loads to beams (wall weight).

    beams_with_depth: list of (beam_name, beam_depth_m, story_name)
    story_heights: dict mapping story_name -> height (m)
    """
    count = 0
    for beam_name, depth_m, story in beams_with_depth:
        h = story_heights.get(story, 3.2)
        w = calculate_beam_line_load(h, depth_m)
        if w > 0:
            ret = SapModel.FrameObj.SetLoadDistributed(
                beam_name, "SDL",
                1,    # Type: 1=Force
                11,   # Dir: 11=Projected Gravity
                0, 1, # Dist1=0, Dist2=1 (full length)
                -w, -w  # uniform load
            )
            if ret == 0:
                count += 1

    print(f"  Beam line loads assigned: {count}/{len(beams_with_depth)}")
    return count


# ── Response Spectrum ────────────────────────────────────────

def load_spectrum_file(filepath):
    """Load response spectrum from text file.

    Expected format: two columns (Period, Sa) separated by spaces/tabs.
    Lines starting with # are comments.

    Returns: (periods_list, sa_list)
    """
    periods, sa_values = [], []
    with open(filepath, 'r') as f:
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
    print(f"  Loaded spectrum: {len(periods)} points from {filepath}")
    return periods, sa_values


def define_response_spectrum_function(SapModel, func_name, periods, sa_values, damping=0.05):
    """Define a response spectrum function from period-Sa data.

    Uses DatabaseTables to create the function, or falls back to
    SapModel.Func.FuncRS.SetUser method.
    """
    n = len(periods)
    # Try using the RS function API
    try:
        ret = SapModel.Func.FuncRS.SetUser(func_name, n, periods, sa_values, damping)
        if ret == 0:
            print(f"  RS function '{func_name}' created ({n} points)")
            return True
    except Exception as e:
        print(f"  FuncRS.SetUser failed: {e}")

    print(f"  WARNING: Could not create RS function automatically.")
    print(f"  Import '{func_name}' manually via ETABS > Define > Functions > Response Spectrum")
    return False


def define_response_spectrum_cases(SapModel, spec_func_name="UserRS",
                                    modal_case="Modal"):
    """Define RSX and RSY response spectrum load cases."""
    cases = [
        ("RSX", "U1", 0),    # X direction
        ("RSY", "U2", 90),   # Y direction
    ]

    for case_name, load_dir, angle in cases:
        try:
            SapModel.LoadCases.ResponseSpectrum.SetCase(case_name)
            SapModel.LoadCases.ResponseSpectrum.SetLoads(
                case_name, 1, [load_dir], [spec_func_name],
                [9.81], ["Global"], [angle])
            SapModel.LoadCases.ResponseSpectrum.SetModalCase(case_name, modal_case)
            SapModel.LoadCases.ResponseSpectrum.SetEccentricity(case_name, 0.05)
            print(f"  RS case '{case_name}' created (dir={load_dir}, ecc=5%)")
        except Exception as e:
            print(f"  WARNING: Failed to create RS case '{case_name}': {e}")


# ── Foundation Springs ───────────────────────────────────────

def assign_foundation_point_springs(SapModel, point_names, kv):
    """Assign vertical point springs (Kv) to foundation slab points.

    kv: spring stiffness in vertical direction (ton/m per point, or as specified)
    """
    springs = [0, 0, kv, 0, 0, 0]  # K1=0, K2=0, K3=Kv, KR1=0, KR2=0, KR3=0
    count = 0
    for pt in point_names:
        ret = SapModel.PointObj.SetSpring(pt, springs)
        if ret == 0:
            count += 1
    print(f"  Foundation point springs: {count}/{len(point_names)} (Kv={kv})")
    return count


def assign_foundation_restraints(SapModel, base_points):
    """Assign base restraints: lock UX, UY only (NOT full fixed).

    base_points: list of point names at foundation level
    """
    restraint = [True, True, False, False, False, False]  # UX, UY only
    count = 0
    for pt in base_points:
        ret = SapModel.PointObj.SetRestraint(pt, restraint)
        if ret == 0:
            count += 1
    print(f"  Base restraints (UX,UY): {count}/{len(base_points)}")
    return count


def assign_edge_beam_line_springs(SapModel, edge_beam_names, kw):
    """Assign line springs (Kw) to edge foundation beams.

    kw: lateral spring stiffness (ton/m/m)
    """
    # Define line spring property
    spring_prop = "EdgeSpring"
    try:
        SapModel.PropLineSpring.SetLineSpringProp(
            spring_prop, 0, kw, 0, 0, 0, 0)
        print(f"  Line spring property '{spring_prop}' created (Kw={kw})")
    except Exception as e:
        print(f"  WARNING: Could not create line spring property: {e}")
        return 0

    count = 0
    for beam in edge_beam_names:
        try:
            ret = SapModel.FrameObj.SetSpringAssignment(beam, spring_prop)
            if ret == 0:
                count += 1
        except:
            pass
    print(f"  Edge beam line springs: {count}/{len(edge_beam_names)}")
    return count


# ── Master Load Assignment ───────────────────────────────────

def assign_all_loads(SapModel, slab_names, beams_with_depth,
                     story_heights, sdl_value, live_value,
                     spectrum_file=None, base_points=None,
                     raft_points=None, kv=None,
                     edge_beams=None, kw=None):
    """Run all load assignments in sequence."""

    print("=== Defining Load Patterns ===")
    define_load_patterns(SapModel)

    print("\n=== Assigning Slab Loads ===")
    assign_slab_loads(SapModel, slab_names, sdl_value, live_value)

    print("\n=== Assigning Beam Line Loads ===")
    assign_beam_line_loads(SapModel, beams_with_depth, story_heights)

    if spectrum_file and os.path.exists(spectrum_file):
        print("\n=== Response Spectrum ===")
        periods, sa = load_spectrum_file(spectrum_file)
        if periods:
            define_response_spectrum_function(SapModel, "UserRS", periods, sa)
            define_response_spectrum_cases(SapModel, "UserRS")

    if base_points:
        print("\n=== Foundation Restraints ===")
        assign_foundation_restraints(SapModel, base_points)

    if raft_points and kv:
        print("\n=== Foundation Springs ===")
        assign_foundation_point_springs(SapModel, raft_points, kv)

    if edge_beams and kw:
        print("\n=== Edge Beam Springs ===")
        assign_edge_beam_line_springs(SapModel, edge_beams, kw)

    SapModel.View.RefreshView(0, False)
    print("\nAll loads assigned.")
