"""
Batch Section Generator for ETABS
Reads plan-reader output sections, expands +-20cm/5cm step across all concrete strengths,
then creates all frame/area sections in ETABS.

Usage:
    python generate_sections.py [--dry-run]

Requires: connect_etabs.py in same directory, ETABS running.
"""
import sys
import os
import re
import json
import argparse

# ── Configuration ──────────────────────────────────────────────
CONCRETE_GRADES = [280, 315, 350, 420, 490]  # kgf/cm2
EXPAND_RANGE = 20   # cm
EXPAND_STEP = 5     # cm
MIN_BEAM_W = 25     # cm minimum beam width
MIN_BEAM_D = 40     # cm minimum beam depth
MIN_COL_DIM = 30    # cm minimum column dimension

# Material properties (TON/M units)
# E in ton/m2, Poisson, thermal coeff
CONCRETE_PROPS = {
    280: {"E": 2.50e6, "nu": 0.2, "fc": 280, "wt": 2.4},
    315: {"E": 2.65e6, "nu": 0.2, "fc": 315, "wt": 2.4},
    350: {"E": 2.80e6, "nu": 0.2, "fc": 350, "wt": 2.4},
    420: {"E": 3.06e6, "nu": 0.2, "fc": 420, "wt": 2.4},
    490: {"E": 3.31e6, "nu": 0.2, "fc": 490, "wt": 2.4},
}
REBAR_PROPS = {
    "SD420": {"E": 2.04e7, "Fy": 4200, "Fu": 6300},
    "SD490": {"E": 2.04e7, "Fy": 4900, "Fu": 7350},
}


def parse_section_name(name):
    """Parse section name into (prefix, width_cm, depth_cm).

    Naming: {PREFIX}{WIDTH}X{DEPTH}  (width first, then depth)
    Examples: B55X80 -> ('B', 55, 80)
              C90X90 -> ('C', 90, 90)
              WB50X70 -> ('WB', 50, 70)
              SB35X65 -> ('SB', 35, 65)
              FB90X230 -> ('FB', 90, 230)
    """
    m = re.match(r'^(B|SB|WB|FB|FSB|FWB|C)(\d+)X(\d+)$', name, re.IGNORECASE)
    if m:
        prefix = m.group(1).upper()
        width = int(m.group(2))
        depth = int(m.group(3))
        return prefix, width, depth
    return None, None, None


def expand_frame_sections(prefix, base_w, base_d):
    """Expand a single frame section into +-20cm/5cm combinations x all grades.
    Returns list of (name, mat_name, depth_m, width_m).
    """
    results = []
    min_w = MIN_COL_DIM if prefix == 'C' else MIN_BEAM_W
    min_d = MIN_COL_DIM if prefix == 'C' else MIN_BEAM_D

    w_range = range(max(base_w - EXPAND_RANGE, min_w),
                    base_w + EXPAND_RANGE + 1, EXPAND_STEP)
    d_range = range(max(base_d - EXPAND_RANGE, min_d),
                    base_d + EXPAND_RANGE + 1, EXPAND_STEP)

    for w in w_range:
        for d in d_range:
            for fc in CONCRETE_GRADES:
                name = f"{prefix}{w}X{d}C{fc}"
                mat = f"C{fc}"
                depth_m = d / 100.0
                width_m = w / 100.0
                results.append((name, mat, depth_m, width_m))
    return results


def expand_area_sections(prefix, thickness_cm):
    """Expand area section (slab/wall/FS) across all concrete grades.
    Returns list of (name, mat_name, thickness_m, shell_type).
    """
    results = []
    for fc in CONCRETE_GRADES:
        mat = f"C{fc}"
        t_m = thickness_cm / 100.0
        if prefix == "FS":
            name = f"FS{thickness_cm}C{fc}"
            shell_type = 1  # ShellThick (has bending)
        elif prefix == "W":
            name = f"W{thickness_cm}C{fc}"
            shell_type = 2  # Membrane
        else:  # S (slab)
            name = f"S{thickness_cm}C{fc}"
            shell_type = 2  # Membrane
        results.append((name, mat, t_m, shell_type))
    return results


def define_materials(SapModel):
    """Define all concrete grades and rebar materials."""
    count = 0
    for fc, props in CONCRETE_PROPS.items():
        mat_name = f"C{fc}"
        try:
            ret = SapModel.PropMaterial.AddMaterial(mat_name, 2, "", "", "")
        except:
            pass  # material may already exist
        SapModel.PropMaterial.SetMPIsotropic(mat_name, props["E"], props["nu"], 1e-5)
        SapModel.PropMaterial.SetWeightAndMass(mat_name, 1, props["wt"])
        # Set concrete design properties (fc in ton/m2)
        fc_tonm2 = fc * 10  # kgf/cm2 -> ton/m2 (approx: 1 kgf/cm2 = 10 ton/m2)
        SapModel.PropMaterial.SetOConcrete_1(
            mat_name, fc_tonm2, False, 1, 2, 1, 0.002, 0.005, -0.1, 0, 0)
        count += 1
        print(f"  Material: {mat_name} (fc={fc} kgf/cm2, E={props['E']:.2e} ton/m2)")

    for rb_name, rb_props in REBAR_PROPS.items():
        try:
            ret = SapModel.PropMaterial.AddMaterial(rb_name, 5, "", "", "")
        except:
            pass
        SapModel.PropMaterial.SetMPIsotropic(rb_name, rb_props["E"], 0.3, 1e-5)
        fy_tonm2 = rb_props["Fy"] * 10
        fu_tonm2 = rb_props["Fu"] * 10
        SapModel.PropMaterial.SetORebar_1(
            rb_name, fy_tonm2, fu_tonm2, fy_tonm2, fu_tonm2, 1, 1, 0.01, 0.09, False)
        count += 1
        print(f"  Material: {rb_name} (Fy={rb_props['Fy']} kgf/cm2)")

    print(f"Total materials defined: {count}")
    return count


def create_frame_sections(SapModel, sections_list):
    """Create frame sections in ETABS.
    sections_list: list of (name, mat_name, depth_m, width_m)
    """
    count = 0
    for name, mat, depth_m, width_m in sections_list:
        # PropFrame.SetRectangle(Name, MatProp, T3=Depth, T2=Width)
        ret = SapModel.PropFrame.SetRectangle(name, mat, depth_m, width_m)
        if ret == 0:
            count += 1
        else:
            print(f"  WARNING: Failed to create frame section {name}")
    return count


def create_area_sections(SapModel, sections_list):
    """Create area sections in ETABS.
    sections_list: list of (name, mat_name, thickness_m, shell_type)
    """
    count = 0
    for name, mat, t_m, shell_type in sections_list:
        if name.startswith("W"):
            ret = SapModel.PropArea.SetWall(name, 0, shell_type, mat, t_m)
        else:
            ret = SapModel.PropArea.SetSlab(name, 0, shell_type, mat, t_m)
        if ret == 0:
            count += 1
        else:
            print(f"  WARNING: Failed to create area section {name}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Batch generate ETABS sections")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print sections without creating in ETABS")
    parser.add_argument("--input", type=str, default=None,
                        help="JSON file with plan-reader section list")
    args = parser.parse_args()

    # Example plan-reader sections (replace with actual input)
    # Format: list of base section names from plan-reader output
    example_sections = {
        "frame": ["B55X80", "B50X70", "SB35X65", "WB50X70",
                   "FB90X230", "C90X90", "C60X90", "C150X130"],
        "slab": [15],          # thickness in cm
        "wall": [20, 25, 30],  # thickness in cm
        "raft": [100],         # thickness in cm
    }

    if args.input and os.path.exists(args.input):
        with open(args.input) as f:
            sections_input = json.load(f)
    else:
        sections_input = example_sections
        print("Using example sections (no --input file provided)")

    # Expand frame sections
    all_frame = []
    for sec_name in sections_input.get("frame", []):
        prefix, w, d = parse_section_name(sec_name)
        if prefix:
            expanded = expand_frame_sections(prefix, w, d)
            all_frame.extend(expanded)
            print(f"  {sec_name} -> {len(expanded)} combinations")
        else:
            print(f"  WARNING: Cannot parse section name '{sec_name}'")

    # Expand area sections
    all_area = []
    for t in sections_input.get("slab", []):
        expanded = expand_area_sections("S", t)
        all_area.extend(expanded)
        print(f"  Slab t={t}cm -> {len(expanded)} combinations")

    for t in sections_input.get("wall", []):
        expanded = expand_area_sections("W", t)
        all_area.extend(expanded)
        print(f"  Wall t={t}cm -> {len(expanded)} combinations")

    for t in sections_input.get("raft", []):
        expanded = expand_area_sections("FS", t)
        all_area.extend(expanded)
        print(f"  Raft t={t}cm -> {len(expanded)} combinations")

    # Deduplicate
    frame_unique = list({s[0]: s for s in all_frame}.values())
    area_unique = list({s[0]: s for s in all_area}.values())

    print(f"\nTotal unique frame sections: {len(frame_unique)}")
    print(f"Total unique area sections: {len(area_unique)}")

    if args.dry_run:
        print("\n[DRY RUN] Frame sections:")
        for name, mat, d, w in sorted(frame_unique)[:20]:
            print(f"  {name}: mat={mat}, T3(depth)={d}m, T2(width)={w}m")
        if len(frame_unique) > 20:
            print(f"  ... and {len(frame_unique)-20} more")
        print("\n[DRY RUN] Area sections:")
        for name, mat, t, st in sorted(area_unique):
            print(f"  {name}: mat={mat}, t={t}m, shellType={st}")
        return

    # Connect to ETABS
    sys.path.insert(0, os.path.dirname(__file__))
    from connect_etabs import get_etabs
    SapModel = get_etabs()

    # Define materials first
    print("\n=== Defining Materials ===")
    define_materials(SapModel)

    # Create frame sections
    print(f"\n=== Creating {len(frame_unique)} Frame Sections ===")
    n_frame = create_frame_sections(SapModel, frame_unique)
    print(f"Created {n_frame} frame sections")

    # Create area sections
    print(f"\n=== Creating {len(area_unique)} Area Sections ===")
    n_area = create_area_sections(SapModel, area_unique)
    print(f"Created {n_area} area sections")

    SapModel.View.RefreshView(0, False)
    print("\nDone.")


if __name__ == "__main__":
    main()
