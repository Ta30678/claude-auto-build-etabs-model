"""
Golden Script 02: Batch Section Generation

- Expands base sections +-20cm/5cm across all concrete grades
- Creates frame sections with CORRECT D/B mapping (T3=Depth, T2=Width)
- Creates area sections (Slab=Membrane, Wall=Membrane, Raft=ShellThick)
- Assigns rebar to all frame section properties
- Assigns area modifiers to section properties

D/B swap is IMPOSSIBLE here: parsing logic is hardcoded.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from constants import (
    CONCRETE_GRADES, EXPAND_RANGE, EXPAND_STEP,
    MIN_BEAM_W, MIN_BEAM_D, MIN_COL_DIM,
    SHELL_MEMBRANE, SHELL_THICK,
    SLAB_WALL_MODIFIERS, RAFT_MODIFIERS,
    BEAM_COVER_TOP, BEAM_COVER_BOT, FB_COVER_TOP, FB_COVER_BOT,
    COL_COVER, COL_CORNER_BARS, COL_TIE_SPACING,
    COL_REBAR_SIZE, COL_TIE_SIZE, COL_NUM_2DIR_TIE, COL_NUM_3DIR_TIE,
    parse_frame_section, parse_area_section, is_foundation_beam,
    calc_column_bar_distribution,
)


def expand_frame_sections(prefix, base_w, base_d):
    """Expand one base section into all size+grade combinations.
    Returns list of (name, mat_name, depth_m, width_m).

    CRITICAL: depth_m goes to T3, width_m goes to T2.
    Name format is {PREFIX}{WIDTH}X{DEPTH}, API is SetRectangle(name, mat, T3=depth, T2=width).
    """
    results = []
    min_w = MIN_COL_DIM if prefix == 'C' else MIN_BEAM_W
    min_d = MIN_COL_DIM if prefix == 'C' else MIN_BEAM_D

    for w in range(max(base_w - EXPAND_RANGE, min_w),
                   base_w + EXPAND_RANGE + 1, EXPAND_STEP):
        for d in range(max(base_d - EXPAND_RANGE, min_d),
                       base_d + EXPAND_RANGE + 1, EXPAND_STEP):
            for fc in CONCRETE_GRADES:
                name = f"{prefix}{w}X{d}C{fc}"
                mat = f"C{fc}"
                depth_m = d / 100.0  # T3
                width_m = w / 100.0  # T2
                results.append((name, mat, depth_m, width_m))
    return results


def expand_area_sections(prefix, thickness_cm):
    """Expand area section across all grades.
    Returns list of (name, mat_name, thickness_m, shell_type).
    """
    results = []
    for fc in CONCRETE_GRADES:
        mat = f"C{fc}"
        t_m = thickness_cm / 100.0
        if prefix == "FS":
            shell_type = SHELL_THICK
        else:
            shell_type = SHELL_MEMBRANE
        name = f"{prefix}{thickness_cm}C{fc}"
        results.append((name, mat, t_m, shell_type))
    return results


def create_frame_sections(SapModel, sections_list):
    """Create frame sections in ETABS.
    sections_list: list of (name, mat_name, depth_m, width_m)
    """
    count = 0
    for name, mat, depth_m, width_m in sections_list:
        ret = SapModel.PropFrame.SetRectangle(name, mat, depth_m, width_m)
        if ret == 0:
            count += 1
    return count


def create_area_sections(SapModel, sections_list):
    """Create area sections in ETABS.
    sections_list: list of (name, mat_name, thickness_m, shell_type)
    """
    count = 0
    for name, mat, t_m, shell_type in sections_list:
        if name.startswith("W") and not name.startswith("WB"):
            ret = SapModel.PropArea.SetWall(name, 0, shell_type, mat, t_m)
        else:
            ret = SapModel.PropArea.SetSlab(name, 0, shell_type, mat, t_m)
        if ret == 0:
            count += 1
    return count


def assign_all_rebar(SapModel, frame_sections):
    """Assign rebar configuration to all created frame sections."""
    beam_count, col_count = 0, 0

    for name, mat, depth_m, width_m in frame_sections:
        prefix, w_cm, d_cm, fc = parse_frame_section(name)
        if not prefix:
            continue

        if prefix == "C":
            num_r2, num_r3 = calc_column_bar_distribution(w_cm, d_cm)
            ret = SapModel.PropFrame.SetRebarColumn(
                name, "SD420", "SD420",
                1,                    # Pattern: Rectangular
                1,                    # ConfineType: Ties
                COL_COVER,
                COL_CORNER_BARS,
                num_r3,               # bars along depth (T3)
                num_r2,               # bars along width (T2)
                COL_REBAR_SIZE,
                COL_TIE_SIZE,
                COL_TIE_SPACING,
                COL_NUM_2DIR_TIE,
                COL_NUM_3DIR_TIE,
                True                  # ToBeDesigned
            )
            if ret == 0:
                col_count += 1
        else:
            is_fb = is_foundation_beam(prefix)
            cover_top = FB_COVER_TOP if is_fb else BEAM_COVER_TOP
            cover_bot = FB_COVER_BOT if is_fb else BEAM_COVER_BOT
            ret = SapModel.PropFrame.SetRebarBeam(
                name, "SD420", "SD420",
                cover_top, cover_bot,
                0, 0, 0, 0,          # Area values (0 = design mode)
                True                  # ToBeDesigned
            )
            if ret == 0:
                beam_count += 1

    print(f"  Rebar assigned: {beam_count} beams, {col_count} columns")
    return beam_count, col_count


def assign_area_modifiers(SapModel, area_sections):
    """Set stiffness modifiers on area section properties."""
    count = 0
    for name, mat, t_m, shell_type in area_sections:
        prefix, _, _ = parse_area_section(name)
        if not prefix:
            continue
        mods = RAFT_MODIFIERS if prefix == "FS" else SLAB_WALL_MODIFIERS
        ret = SapModel.PropArea.SetModifiers(name, mods)
        if ret == 0:
            count += 1
    print(f"  Area modifiers assigned: {count}")
    return count


def run(SapModel, config):
    """Execute step 02: batch section generation."""
    print("=" * 60)
    print("STEP 02: Batch Section Generation")
    print("=" * 60)

    sections = config.get("sections", {})

    # Expand frame sections
    all_frame = []
    for sec_name in sections.get("frame", []):
        prefix, w, d, _ = parse_frame_section(sec_name)
        if prefix:
            expanded = expand_frame_sections(prefix, w, d)
            all_frame.extend(expanded)
            print(f"  {sec_name} -> {len(expanded)} combinations")

    # Expand area sections
    all_area = []
    for t in sections.get("slab", []):
        expanded = expand_area_sections("S", t)
        all_area.extend(expanded)
        print(f"  Slab t={t}cm -> {len(expanded)}")

    for t in sections.get("wall", []):
        expanded = expand_area_sections("W", t)
        all_area.extend(expanded)
        print(f"  Wall t={t}cm -> {len(expanded)}")

    for t in sections.get("raft", []):
        expanded = expand_area_sections("FS", t)
        all_area.extend(expanded)
        print(f"  Raft t={t}cm -> {len(expanded)}")

    # Deduplicate
    frame_unique = list({s[0]: s for s in all_frame}.values())
    area_unique = list({s[0]: s for s in all_area}.values())

    print(f"\nTotal unique frame sections: {len(frame_unique)}")
    print(f"Total unique area sections: {len(area_unique)}")

    # Create in ETABS
    print("\n--- Creating frame sections ---")
    n_frame = create_frame_sections(SapModel, frame_unique)
    print(f"  Created {n_frame} frame sections")

    print("\n--- Creating area sections ---")
    n_area = create_area_sections(SapModel, area_unique)
    print(f"  Created {n_area} area sections")

    # Assign rebar to all frame sections
    print("\n--- Assigning rebar ---")
    assign_all_rebar(SapModel, frame_unique)

    # Assign area modifiers
    print("\n--- Assigning area modifiers ---")
    assign_area_modifiers(SapModel, area_unique)

    SapModel.View.RefreshView(0, False)
    print("Step 02 complete.\n")

    return frame_unique, area_unique


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "model_config.json"
    with open(config_path) as f:
        config = json.load(f)
    from gs_01_init import connect_etabs
    SapModel = connect_etabs(config)
    run(SapModel, config)
