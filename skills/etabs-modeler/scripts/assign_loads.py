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
    """Define standard load patterns using company-internal naming.

    Internal naming convention:
        DL   = Dead Load (self-weight multiplier = 1)
        LL   = Live Load
        EQXP = Seismic +X
        EQXN = Seismic -X
        EQYP = Seismic +Y
        EQYN = Seismic -Y

    SDL is NOT created by default. Only add if user explicitly requests it.

    eLoadPatternType: Dead=1, SuperDead=2, Live=3, ReduceLive=4, Quake=5, Wind=6
    """
    if patterns is None:
        patterns = [
            ("DL",   1, 1),    # Dead with self-weight = 1
            ("LL",   3, 0),    # Live
            ("EQXP", 5, 0),    # Seismic +X
            ("EQXN", 5, 0),    # Seismic -X
            ("EQYP", 5, 0),    # Seismic +Y
            ("EQYN", 5, 0),    # Seismic -Y
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


# ── Seismic Load Pattern Configuration ──────────────────────

def configure_seismic_patterns(SapModel, base_shear_c, top_story="PRF", bottom_story="1F"):
    """Configure User Coefficient seismic parameters for EQXP/EQXN/EQYP/EQYN.

    Args:
        base_shear_c: Base Shear Coefficient C (ask user or read from EQ_PARAMS.txt)
        top_story: Top story for seismic load (default "PRF")
        bottom_story: Bottom story for seismic load (default "1F")

    Each pattern gets:
        - ECC RATIO = 0.05
        - Building Height Exp. K = 1
        - Base Shear Coefficient C = user-provided value
        - Top/Bottom Story = PRF/1F
        - Direction and sign per pattern name
    """
    eq_configs = [
        ("EQXP", 1, 1),   # X direction, positive
        ("EQXN", 1, -1),  # X direction, negative
        ("EQYP", 2, 1),   # Y direction, positive
        ("EQYN", 2, -1),  # Y direction, negative
    ]

    for name, direction, sign in eq_configs:
        try:
            # Set auto seismic user coefficient
            # Direction: 1=X, 2=Y
            # Ecc ratio = 0.05
            SapModel.LoadPatterns.AutoSeismic.SetUserCoefficient(
                name,
                direction,          # Direction: 1=X, 2=Y
                0.05,               # Ecc ratio
                sign * base_shear_c,  # C value (negative for negative direction)
                1,                  # Building Height Exp. K
                top_story,          # Top story
                bottom_story        # Bottom story
            )
            print(f"  Seismic config: {name} (dir={direction}, C={sign*base_shear_c}, ecc=0.05, K=1)")
        except Exception as e:
            print(f"  WARNING: Failed to configure {name}: {e}")
            print(f"  You may need to set seismic parameters manually in ETABS.")


# ── Default Load Values by Zone ──────────────────────────────

DEFAULT_LOADS = {
    "superstructure": {"DL": 0.45, "LL": 0.2},   # 上構 2F~RF
    "substructure":   {"DL": 0.15, "LL": 0.5},   # 下構 B_F~1F
    "1F_indoor":      {"DL": 0.3,  "LL": 0.5},   # 1F 室內
    "1F_outdoor":     {"DL": 0.6,  "LL": 1.0},   # 1F 室外
    "FS":             {"DL": 0.63, "LL": 0},      # 基礎版
}


# ── Slab Uniform Loads ───────────────────────────────────────

def assign_slab_loads(SapModel, slab_names, dl_value, ll_value):
    """Assign DL and LL uniform loads to slabs.

    Args:
        slab_names: list of area object names
        dl_value: DL load in ton/m2 (positive value, applied as negative Z)
        ll_value: LL load in ton/m2 (positive value, applied as negative Z)
    """
    count = 0
    for slab in slab_names:
        if dl_value > 0:
            ret = SapModel.AreaObj.SetLoadUniform(slab, "DL", -dl_value, 6)
            if ret == 0:
                count += 1
        if ll_value > 0:
            ret = SapModel.AreaObj.SetLoadUniform(slab, "LL", -ll_value, 6)
            if ret == 0:
                count += 1

    print(f"  Slab loads assigned: {count} (DL={dl_value}, LL={ll_value} ton/m2)")
    return count


# ── Beam Line Loads (Exterior Wall Weight) ──────────────────

def calculate_exterior_wall_load(story_height_m, beam_depth_above_m,
                                  wall_thickness=0.15, unit_weight=2.4, factor=0.6):
    """Calculate exterior wall line load on a beam.

    RULE: Only assign when the floor ABOVE has a beam at the same position.
    Formula: w = unit_weight * wall_thickness * factor * (story_height - beam_depth_above)

    Args:
        story_height_m: height of the current story (m)
        beam_depth_above_m: depth of the beam on the floor ABOVE (m)
        wall_thickness: wall thickness (m), default 0.15
        unit_weight: concrete unit weight (ton/m3), default 2.4
        factor: opening reduction factor, default 0.6

    Returns: line load in ton/m
    """
    clear_height = story_height_m - beam_depth_above_m
    if clear_height <= 0:
        return 0
    return unit_weight * wall_thickness * factor * clear_height


def assign_exterior_wall_loads(SapModel, exterior_beams, beams_above_map, story_heights):
    """Assign DL line loads to exterior beams (wall weight).

    IMPORTANT: Only assign where the floor above has a beam at the same grid position.
    Direction 11 = Projected Gravity: positive value = downward (gravity direction).

    Args:
        exterior_beams: list of (beam_name, story_name, grid_position)
        beams_above_map: dict mapping (story_above, grid_position) -> beam_depth_m
            Example: {("3F", "GridA/1~2"): 0.80, ...}
        story_heights: dict mapping story_name -> height (m)
    """
    count = 0
    skipped = 0
    for beam_name, story, grid_pos in exterior_beams:
        # Determine the story above
        story_above = get_story_above(story)
        if story_above is None:
            skipped += 1
            continue

        # Check if beam exists above at same grid position
        key = (story_above, grid_pos)
        if key not in beams_above_map:
            skipped += 1
            continue

        beam_depth_above = beams_above_map[key]
        h = story_heights.get(story, 3.2)
        w = calculate_exterior_wall_load(h, beam_depth_above)
        if w > 0:
            ret = SapModel.FrameObj.SetLoadDistributed(
                beam_name, "DL",
                1,    # Type: 1=Force
                11,   # Dir: 11=Projected Gravity
                0, 1, # Dist1=0, Dist2=1 (full length)
                w, w  # positive = gravity (downward), negative = upward (WRONG!)
            )
            if ret == 0:
                count += 1

    print(f"  Exterior wall loads assigned: {count} (skipped {skipped} - no beam above)")
    return count


def get_story_above(story_name):
    """Get the story name above a given story.
    This is a simplified version - the agent should use actual story data.
    """
    import re
    m = re.match(r'^(\d+)F$', story_name)
    if m:
        n = int(m.group(1))
        return f"{n+1}F"
    m = re.match(r'^B(\d+)F$', story_name)
    if m:
        n = int(m.group(1))
        if n == 1:
            return "1F"
        return f"B{n-1}F"
    # For RF, PRF, etc. - no story above
    return None


# ── Response Spectrum ────────────────────────────────────────

def load_spectrum_file(filepath):
    """Load response spectrum from text file.

    Expected format: two columns (Period, Sa/Value) separated by spaces/tabs.
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


def import_spectrum_function(SapModel, func_name, filepath, damping=0.05):
    """Import response spectrum function FROM FILE.

    This creates a user-defined RS function from Period-Value data in SPECTRUM.TXT.
    Equivalent to: DEFINE > Functions > Response Spectrum > Add New Function > FROM FILE

    Args:
        func_name: name for the spectrum function (e.g., "SPEC_FUNC")
        filepath: path to SPECTRUM.TXT (Period vs Value format)
        damping: damping ratio (default 0.05 = 5%)
    """
    periods, sa_values = load_spectrum_file(filepath)
    if not periods:
        print(f"  ERROR: No spectrum data in {filepath}")
        return False

    try:
        ret = SapModel.Func.FuncRS.SetUser(func_name, len(periods), periods, sa_values, damping)
        if ret == 0:
            print(f"  RS function '{func_name}' created ({len(periods)} points)")
            return True
    except Exception as e:
        print(f"  FuncRS.SetUser failed: {e}")

    print(f"  WARNING: Could not create RS function automatically.")
    print(f"  Import '{func_name}' manually via ETABS > Define > Functions > Response Spectrum > From File")
    return False


def configure_existing_spectrum_cases(SapModel, spec_func_name="SPEC_FUNC",
                                       modal_case="Modal"):
    """Modify EXISTING 0SPECX and 0SPECXY load cases to use the imported spectrum.

    IMPORTANT: Do NOT create new RSX/RSY. Modify existing 0SPECX and 0SPECXY.

    Settings for each:
        - Load Type = Acceleration
        - Load Name = U1
        - Function = spec_func_name (imported from file)
        - Scale Factor = 1
        - Eccentricity = 0.05
    """
    cases = [
        ("0SPECX",  "U1", 0),    # X direction
        ("0SPECXY", "U1", 0),    # XY direction (same settings)
    ]

    for case_name, load_name, angle in cases:
        try:
            # Modify existing case loads
            SapModel.LoadCases.ResponseSpectrum.SetLoads(
                case_name, 1, [load_name], [spec_func_name],
                [1.0], ["Global"], [angle])  # Scale Factor = 1
            SapModel.LoadCases.ResponseSpectrum.SetModalCase(case_name, modal_case)
            SapModel.LoadCases.ResponseSpectrum.SetEccentricity(case_name, 0.05)
            print(f"  RS case '{case_name}' modified (func={spec_func_name}, SF=1, ecc=5%)")
        except Exception as e:
            print(f"  WARNING: Failed to modify RS case '{case_name}': {e}")
            print(f"  This case may not exist yet. Check ETABS load cases.")


# ── EQ Parameters File ──────────────────────────────────────

def read_eq_params(model_folder):
    """Read earthquake parameters from EQ_PARAMS.txt in model folder.

    Expected format:
        BASE_SHEAR_C=0.072
        EQV_SCALE_FACTOR=4.5

    Returns: dict with keys 'BASE_SHEAR_C' and 'EQV_SCALE_FACTOR', or None if file missing.
    """
    filepath = os.path.join(model_folder, "EQ_PARAMS.txt")
    if not os.path.exists(filepath):
        return None

    params = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                try:
                    params[key.strip()] = float(val.strip())
                except ValueError:
                    pass

    print(f"  EQ params loaded: {params}")
    return params if params else None


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

def assign_all_loads(SapModel, slab_names, exterior_beams,
                     beams_above_map, story_heights,
                     dl_value, ll_value,
                     model_folder=None,
                     base_shear_c=None,
                     base_points=None,
                     raft_points=None, kv=None,
                     edge_beams=None, kw=None):
    """Run all load assignments in sequence.

    Args:
        dl_value: DL load in ton/m2 (use DEFAULT_LOADS for zone-specific defaults)
        ll_value: LL load in ton/m2 (use DEFAULT_LOADS for zone-specific defaults)
    """

    print("=== Defining Load Patterns ===")
    define_load_patterns(SapModel)

    # Read EQ params from file if available
    eq_params = None
    if model_folder:
        eq_params = read_eq_params(model_folder)

    if base_shear_c is None and eq_params and 'BASE_SHEAR_C' in eq_params:
        base_shear_c = eq_params['BASE_SHEAR_C']

    if base_shear_c is not None:
        print("\n=== Configuring Seismic Patterns ===")
        configure_seismic_patterns(SapModel, base_shear_c)
    else:
        print("\n  WARNING: Base Shear Coefficient C not provided.")
        print("  Please configure EQXP/EQXN/EQYP/EQYN manually or provide EQ_PARAMS.txt")

    print("\n=== Assigning Slab Loads ===")
    assign_slab_loads(SapModel, slab_names, dl_value, ll_value)

    print("\n=== Assigning Exterior Wall Loads ===")
    if exterior_beams and beams_above_map:
        assign_exterior_wall_loads(SapModel, exterior_beams, beams_above_map, story_heights)
    else:
        print("  No exterior beam data provided - skipping wall loads")

    # Response spectrum from SPECTRUM.TXT
    if model_folder:
        spectrum_file = os.path.join(model_folder, "SPECTRUM.TXT")
        if os.path.exists(spectrum_file):
            print("\n=== Response Spectrum (FROM FILE) ===")
            if import_spectrum_function(SapModel, "SPEC_FUNC", spectrum_file):
                configure_existing_spectrum_cases(SapModel, "SPEC_FUNC")
        else:
            print(f"\n  WARNING: SPECTRUM.TXT not found in {model_folder}")

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
