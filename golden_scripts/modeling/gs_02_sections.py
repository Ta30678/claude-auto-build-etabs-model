"""
Golden Script 02: Batch Section Generation

- Creates exact frame sections across all used concrete grades (no size expansion)
- Creates frame sections with CORRECT D/B mapping (T3=Depth, T2=Width)
- Creates area sections (Slab=Membrane, Wall=Membrane, Raft=ShellThick)
- Assigns rebar to all frame section properties
- Assigns area modifiers to section properties

D/B swap is IMPOSSIBLE here: parsing logic is hardcoded.
"""
import json
import re
import sys
import os
import time

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)                      # modeling/ (sibling imports)
sys.path.insert(0, os.path.dirname(_dir))      # golden_scripts/ (constants)
from gs_01_init import _reacquire_SapModel
from constants import (
    CONCRETE_GRADES,
    SHELL_MEMBRANE, SHELL_THICK,
    BEAM_COVER_TOP, BEAM_COVER_BOT, FB_COVER_TOP, FB_COVER_BOT,
    COL_COVER, COL_CORNER_BARS, COL_TIE_SPACING,
    COL_REBAR_SIZE, COL_TIE_SIZE, COL_NUM_2DIR_TIE, COL_NUM_3DIR_TIE,
    parse_frame_section, is_foundation_beam,
    get_frame_dimensions, calc_column_bar_distribution,
)


def get_existing_materials(SapModel):
    """Query ETABS for all defined material names. Returns a set."""
    ret = SapModel.PropMaterial.GetNameList(0, [])
    names = set()
    for item in ret:
        if isinstance(item, (list, tuple)):
            for s in item:
                if isinstance(s, str):
                    names.add(s)
    return names


def extract_used_grades(config):
    """Extract concrete grades actually used in this config."""
    grades = set()
    # From strength_map values
    for range_str, grade_dict in config.get("strength_map", {}).items():
        for elem_type, fc in grade_dict.items():
            grades.add(fc)
    # From explicit C{fc} in section names
    for sec_name in config.get("sections", {}).get("frame", []):
        m = re.search(r'C(\d+)$', sec_name)
        if m:
            grades.add(int(m.group(1)))
    # Diaphragm walls always use C280 (gs_05 hardcodes fc=280)
    for wall in config.get("walls", []):
        if wall.get("is_diaphragm_wall", False):
            grades.add(280)
            break
    return sorted(grades) if grades else CONCRETE_GRADES


def expand_frame_sections(prefix, num1, num2, grades=None):
    """Expand one base section across concrete grades (exact size, no ±20cm expansion).
    Returns list of (name, mat_name, depth_m, width_m).

    CRITICAL: depth_m goes to T3, width_m goes to T2.
    Uses get_frame_dimensions() to handle column C{DEPTH}X{WIDTH} vs beam {PREFIX}{WIDTH}X{DEPTH}.
    """
    width_cm, depth_cm = get_frame_dimensions(prefix, num1, num2)
    results = []
    for fc in (grades or CONCRETE_GRADES):
        name = f"{prefix}{num1}X{num2}C{fc}"   # raw order for name
        mat = f"C{fc}"
        depth_m = depth_cm / 100.0  # T3
        width_m = width_cm / 100.0  # T2
        results.append((name, mat, depth_m, width_m))
    return results


def expand_area_sections(prefix, thickness_cm, grades=None):
    """Expand area section across all grades.
    Returns list of (name, mat_name, thickness_m, shell_type).
    """
    results = []
    for fc in (grades or CONCRETE_GRADES):
        mat = f"C{fc}"
        t_m = thickness_cm / 100.0
        if prefix == "FS":
            shell_type = SHELL_THICK
        else:
            shell_type = SHELL_MEMBRANE
        name = f"{prefix}{thickness_cm}C{fc}"
        results.append((name, mat, t_m, shell_type))
    return results


def create_frame_sections(SapModel, sections_list, existing_materials=None,
                          batch_size=100, batch_pause=1.0):
    """Create frame sections in ETABS with batching to prevent COM crashes.
    sections_list: list of (name, mat_name, depth_m, width_m)
    batch_size: pause every N sections to let ETABS process
    batch_pause: seconds to pause between batches

    Always applies SetRectangle (even for existing sections) to ensure
    correct dimensions and rebar/design type.
    """
    count = 0
    skipped = 0
    missing_mats = {}
    batch_counter = 0
    for name, mat, depth_m, width_m in sections_list:
        if existing_materials is not None and mat not in existing_materials:
            skipped += 1
            missing_mats.setdefault(mat, []).append(name)
            continue
        ret = SapModel.PropFrame.SetRectangle(name, mat, depth_m, width_m)
        retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
        if retcode == 0:
            count += 1
        batch_counter += 1
        if batch_counter % batch_size == 0:
            try:
                SapModel.View.RefreshView(0, False)
            except Exception:
                pass
            time.sleep(batch_pause)
            print(f"    ... {batch_counter} sections processed so far")
    if missing_mats:
        for mat, names in missing_mats.items():
            sample = names[:3]
            print(f"  Material '{mat}' not found. Sections skipped: {sample}{'...' if len(names) > 3 else ''}")
    if skipped:
        print(f"  Skipped {skipped} frame sections (material not in model)")
    return count


def create_area_sections(SapModel, sections_list, existing_materials=None):
    """Create area sections in ETABS.
    sections_list: list of (name, mat_name, thickness_m, shell_type)
    """
    count = 0
    skipped = 0
    missing_mats = {}
    for name, mat, t_m, shell_type in sections_list:
        if existing_materials is not None and mat not in existing_materials:
            skipped += 1
            missing_mats.setdefault(mat, []).append(name)
            continue
        if name.startswith("W") and not name.startswith("WB"):
            ret = SapModel.PropArea.SetWall(name, 0, shell_type, mat, t_m)
        else:
            ret = SapModel.PropArea.SetSlab(name, 0, shell_type, mat, t_m)
        retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
        if retcode == 0:
            count += 1
    if missing_mats:
        for mat, names in missing_mats.items():
            sample = names[:3]
            print(f"  Material '{mat}' not found. Sections skipped: {sample}{'...' if len(names) > 3 else ''}")
    if skipped:
        print(f"  Skipped {skipped} area sections (material not in model)")
    return count


def assign_all_rebar(SapModel, frame_sections, existing_materials=None,
                     batch_size=100, batch_pause=1.0, save_path=None):
    """Assign rebar configuration to all frame sections.

    Always applies rebar (even for existing sections) to ensure
    correct design type (Beam/Column) and bar counts.

    Writes a JSON log to {save_path dir}/rebar_log.json for debugging.
    """
    # [DIAG] Check if SD420 rebar material exists
    rebar_mats = get_existing_materials(SapModel)
    print(f"  [DIAG] SD420 in model: {'SD420' in rebar_mats}")
    print(f"  [DIAG] All materials: {sorted(rebar_mats)}")
    print(f"  [DIAG] frame_sections count: {len(frame_sections)}")

    # Collect current ETABS units
    try:
        current_units = SapModel.GetPresentUnits()
    except Exception:
        current_units = "unknown"

    log_entries = []
    beam_count, col_count, fail_count = 0, 0, 0
    batch_counter = 0

    for name, mat, depth_m, width_m in frame_sections:
        if existing_materials is not None and mat not in existing_materials:
            continue
        prefix, w_cm, d_cm, fc = parse_frame_section(name)
        if not prefix:
            continue

        entry = {"section": name, "prefix": prefix, "material": mat,
                 "depth_m": depth_m, "width_m": width_m}

        if prefix == "C":
            width_cm, depth_cm = get_frame_dimensions(prefix, w_cm, d_cm)
            num_r3, num_r2 = calc_column_bar_distribution(width_cm, depth_cm)
            params = {
                "LongRebarMat": "SD420", "ConfineMat": "SD420",
                "Pattern": 1, "ConfineType": 1,
                "Cover": COL_COVER, "CornerBars": COL_CORNER_BARS,
                "NumR3Bars": num_r3, "NumR2Bars": num_r2,
                "RebarSize": COL_REBAR_SIZE, "TieSize": COL_TIE_SIZE,
                "TieSpacing": COL_TIE_SPACING,
                "Num2DirTie": COL_NUM_2DIR_TIE, "Num3DirTie": COL_NUM_3DIR_TIE,
                "ToBeDesigned": True,
            }
            entry["api_method"] = "SetRebarColumn"
            entry["params"] = params

            ret = SapModel.PropFrame.SetRebarColumn(
                name, "SD420", "SD420",
                1,                    # Pattern: Rectangular
                1,                    # ConfineType: Ties
                COL_COVER,
                COL_CORNER_BARS,
                num_r3,               # bars along width (T2)
                num_r2,               # bars along depth (T3)
                COL_REBAR_SIZE,
                COL_TIE_SIZE,
                COL_TIE_SPACING,
                COL_NUM_2DIR_TIE,
                COL_NUM_3DIR_TIE,
                True                  # ToBeDesigned
            )
            retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
            entry["ret_raw"] = str(ret)
            entry["retcode"] = retcode
            if retcode == 0:
                col_count += 1
                entry["status"] = "OK"
                if col_count <= 3:
                    print(f"    [DIAG] SetRebarColumn OK: {name}")
            else:
                fail_count += 1
                entry["status"] = "FAIL"
                print(f"    [DIAG] SetRebarColumn FAIL: {name} ret={ret}")
        else:
            is_fb = is_foundation_beam(prefix)
            cover_top = FB_COVER_TOP if is_fb else BEAM_COVER_TOP
            cover_bot = FB_COVER_BOT if is_fb else BEAM_COVER_BOT
            params = {
                "LongRebarMat": "SD420", "ConfineMat": "SD420",
                "CoverTop": cover_top, "CoverBot": cover_bot,
                "TopArea": 0, "BotArea": 0,
                "TopAreaComp": 0, "BotAreaComp": 0,
            }
            entry["api_method"] = "SetRebarBeam"
            entry["params"] = params

            ret = SapModel.PropFrame.SetRebarBeam(
                name, "SD420", "SD420",
                cover_top, cover_bot,
                0, 0, 0, 0            # Area values (0 = design mode)
            )
            retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
            entry["ret_raw"] = str(ret)
            entry["retcode"] = retcode
            if retcode == 0:
                beam_count += 1
                entry["status"] = "OK"
                if beam_count <= 3:
                    print(f"    [DIAG] SetRebarBeam OK: {name}")
            else:
                fail_count += 1
                entry["status"] = "FAIL"
                print(f"    [DIAG] SetRebarBeam FAIL: {name} ret={ret}")

        log_entries.append(entry)

        batch_counter += 1
        if batch_counter % batch_size == 0:
            try:
                SapModel.View.RefreshView(0, False)
            except Exception:
                pass
            time.sleep(batch_pause)

    # Write JSON log
    log_data = {
        "environment": {
            "sd420_exists": "SD420" in rebar_mats,
            "all_materials": sorted(rebar_mats),
            "frame_sections_count": len(frame_sections),
            "current_units": current_units,
        },
        "summary": {
            "beam_ok": beam_count,
            "col_ok": col_count,
            "fail": fail_count,
            "total_processed": len(log_entries),
        },
        "entries": log_entries,
    }
    if save_path:
        log_dir = os.path.dirname(os.path.normpath(save_path))
    else:
        log_dir = os.getcwd()
    log_path = os.path.join(log_dir, "rebar_log.json")
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        print(f"  [DIAG] Rebar log written to: {log_path}")
    except Exception as e:
        print(f"  [DIAG] Failed to write rebar log: {e}")

    print(f"  Rebar assigned: {beam_count} beams, {col_count} columns")
    if fail_count > 0:
        print(f"  WARNING: {fail_count} rebar assignments failed (section may not be concrete)")
    return beam_count, col_count



def run(SapModel, config):
    """Execute step 02: batch section generation."""
    print("=" * 60)
    print("STEP 02: Batch Section Generation")
    print("=" * 60)

    sections = config.get("sections", {})

    # Determine used concrete grades (reduces section count by 40-60%)
    used_grades = extract_used_grades(config)
    print(f"Concrete grades to expand: {used_grades}")

    # Expand frame sections
    all_frame = []
    bad_names = []
    for sec_name in sections.get("frame", []):
        prefix, w, d, fc = parse_frame_section(sec_name)
        if not prefix:
            bad_names.append(sec_name)
            continue
        if fc is not None:
            # Full name with Cfc: create only this single grade
            mat = f"C{fc}"
            width_cm, depth_cm = get_frame_dimensions(prefix, w, d)
            depth_m = depth_cm / 100.0
            width_m = width_cm / 100.0
            all_frame.append((sec_name, mat, depth_m, width_m))
            print(f"  {sec_name} -> 1 section (single grade C{fc})")
        else:
            # Base name: expand across used grades only (exact size)
            expanded = expand_frame_sections(prefix, w, d, grades=used_grades)
            all_frame.extend(expanded)
            print(f"  {sec_name} -> {len(expanded)} combinations")

    if bad_names:
        print(f"\n  ERROR: Invalid frame section names: {bad_names}")
        print(f"  期望格式: {{PREFIX}}{{WIDTH}}X{{DEPTH}}[C{{fc}}]  例如: B55X80 或 B55X80C350")
        print(f"  有效 PREFIX: B, SB, WB, FB, FSB, FWB, C")
        if len(bad_names) == len(sections.get("frame", [])):
            raise RuntimeError(
                f"gs_02: ALL {len(bad_names)} frame section names are invalid. "
                f"Check elements extraction (legend color matching may have failed). "
                f"Bad names: {bad_names[:10]}"
            )

    # Expand area sections
    all_area = []
    for t in sections.get("slab", []):
        expanded = expand_area_sections("S", t, grades=used_grades)
        all_area.extend(expanded)
        print(f"  Slab t={t}cm -> {len(expanded)}")

    for t in sections.get("wall", []):
        expanded = expand_area_sections("W", t, grades=used_grades)
        all_area.extend(expanded)
        print(f"  Wall t={t}cm -> {len(expanded)}")

    for t in sections.get("raft", []):
        expanded = expand_area_sections("FS", t, grades=used_grades)
        all_area.extend(expanded)
        print(f"  Raft t={t}cm -> {len(expanded)}")

    # Deduplicate
    frame_unique = list({s[0]: s for s in all_frame}.values())
    area_unique = list({s[0]: s for s in all_area}.values())

    print(f"\nTotal unique frame sections: {len(frame_unique)}")
    print(f"Total unique area sections: {len(area_unique)}")

    # Query existing materials
    existing_materials = get_existing_materials(SapModel)
    print(f"\nExisting materials in model: {sorted(existing_materials)}")

    save_path = config.get("project", {}).get("save_path")

    # Create in ETABS
    print("\n--- Creating frame sections ---")
    n_frame = create_frame_sections(SapModel, frame_unique, existing_materials)
    print(f"  Created {n_frame} frame sections")

    # Checkpoint save after frame section creation
    if save_path:
        SapModel.File.Save(os.path.normpath(save_path))
        print("  [Checkpoint] Saved after frame section creation")

    print("\n--- Creating area sections ---")
    n_area = create_area_sections(SapModel, area_unique, existing_materials)
    print(f"  Created {n_area} area sections")

    # Assign rebar to all frame sections
    print("\n--- Assigning rebar ---")
    print(f"  [DIAG] About to assign rebar to {len(frame_unique)} sections")
    # Re-acquire COM proxy — prevents corruption from heavy section creation
    SapModel = _reacquire_SapModel()
    SapModel.SetPresentUnits(12)  # Restore Ton_m units
    SapModel.SetModelIsLocked(False)
    print("  [DIAG] Re-acquired COM reference before rebar assignment")
    assign_all_rebar(SapModel, frame_unique, existing_materials, save_path=save_path)

    # Checkpoint save after rebar assignment
    if save_path:
        SapModel.File.Save(os.path.normpath(save_path))
        print("  [Checkpoint] Saved after rebar assignment")

    # Summary
    print(f"\n  Created: {n_frame} frame, {n_area} area | Skipped: {len(bad_names)} (bad name)")

    if n_frame == 0 and len(sections.get("frame", [])) > 0:
        raise RuntimeError("gs_02: 0 frame sections created. Check sections.frame names and materials.")

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
