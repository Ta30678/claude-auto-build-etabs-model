"""
ETABS Model Verification Script
Checks element counts, section D/B, modifiers, rebar, releases, springs, diaphragms.

Usage: python verify_model.py
"""
import sys
import os
import re
sys.path.insert(0, os.path.dirname(__file__))


def verify_units(SapModel):
    """Check that units are TON/M (12)."""
    units = SapModel.GetPresentUnits()
    ok = (units == 12)
    print(f"[{'OK' if ok else 'FAIL'}] Units = {units} (expected 12=TON/M)")
    return ok


def verify_element_counts(SapModel):
    """Count frames and areas per story."""
    print("\n=== Element Counts by Story ===")

    # Get all frames
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [], [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])

    if isinstance(ret[0], int) and ret[0] > 0:
        num_frames = ret[0]
        story_names = ret[3]
        # Count per story
        story_count = {}
        for s in story_names:
            story_count[s] = story_count.get(s, 0) + 1
        for story, count in sorted(story_count.items()):
            print(f"  {story}: {count} frames")
        print(f"  TOTAL: {num_frames} frames")
    else:
        print("  WARNING: Could not retrieve frames")
        num_frames = 0

    # Count areas via DatabaseTables
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Area Assignments - Summary", [], "All", 0, [], 0, [])
        if ret[0] == 0:
            num_areas = ret[5]
            print(f"  TOTAL: {num_areas} areas")
        else:
            num_areas = 0
    except:
        num_areas = 0

    return num_frames, num_areas


def verify_section_db(SapModel, section_names=None):
    """Verify T3(depth) > T2(width) for beam sections,
    and that D/B mapping is correct.
    """
    print("\n=== Section D/B Verification ===")
    errors = []

    # Get all frame sections from database
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Frame Section Properties", [], "All", 0, [], 0, [])
        if ret[0] != 0:
            print("  WARNING: Could not read Frame Section Properties table")
            return errors

        fields = list(ret[4])
        n_records = ret[5]
        data = list(ret[6])
        n_fields = len(fields)

        t3_idx = fields.index("t3") if "t3" in fields else -1
        t2_idx = fields.index("t2") if "t2" in fields else -1
        name_idx = fields.index("Name") if "Name" in fields else 0

        if t3_idx < 0 or t2_idx < 0:
            print("  WARNING: t3/t2 fields not found in table")
            return errors

        for i in range(n_records):
            row = data[i * n_fields: (i + 1) * n_fields]
            sec_name = row[name_idx]
            t3 = float(row[t3_idx]) if row[t3_idx] else 0
            t2 = float(row[t2_idx]) if row[t2_idx] else 0

            # Parse expected values from name
            m = re.match(r'^(B|SB|WB|FB|FSB|FWB|C)(\d+)X(\d+)C?\d*$', sec_name)
            if m:
                exp_w = int(m.group(2)) / 100.0  # width in m
                exp_d = int(m.group(3)) / 100.0  # depth in m

                # T3 should be depth, T2 should be width
                if abs(t3 - exp_d) > 0.001 or abs(t2 - exp_w) > 0.001:
                    errors.append(f"  {sec_name}: T3={t3}, T2={t2} "
                                  f"(expected T3={exp_d}, T2={exp_w}) - D/B SWAPPED?")
    except Exception as e:
        print(f"  Error reading sections: {e}")

    if errors:
        print(f"  FAIL: {len(errors)} sections with D/B issues:")
        for e in errors[:10]:
            print(e)
        if len(errors) > 10:
            print(f"  ... and {len(errors)-10} more")
    else:
        print("  [OK] All sections D/B correct")
    return errors


def verify_modifiers(SapModel):
    """Spot-check frame and area modifiers."""
    print("\n=== Modifier Verification (spot check) ===")

    # Check a few frames
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [], [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])

    if isinstance(ret[0], int) and ret[0] > 0:
        names = ret[1]
        props = ret[2]
        checked = 0
        issues = 0
        for i in range(min(20, len(names))):
            name = names[i]
            prop = props[i]
            mod_ret = SapModel.FrameObj.GetModifiers(name, [])
            if mod_ret[0] == 0:
                mods = list(mod_ret[1])
                # Check torsion modifier
                if len(mods) >= 4 and abs(mods[3] - 0.0001) > 0.001:
                    if mods[3] == 1.0:  # default, not yet assigned
                        issues += 1
                checked += 1
        print(f"  Checked {checked} frames, {issues} with default modifiers (not assigned)")
    else:
        print("  WARNING: No frames to check")


def verify_rebar(SapModel):
    """Verify column rebar configuration."""
    print("\n=== Rebar Verification (spot check) ===")
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Frame Section Properties", [], "All", 0, [], 0, [])
        if ret[0] == 0:
            fields = list(ret[4])
            data = list(ret[6])
            n_fields = len(fields)
            n_records = ret[5]
            name_idx = fields.index("Name") if "Name" in fields else 0

            col_sections = []
            for i in range(n_records):
                row = data[i * n_fields: (i + 1) * n_fields]
                sec_name = row[name_idx]
                if sec_name.startswith("C") and "X" in sec_name:
                    col_sections.append(sec_name)

            print(f"  Found {len(col_sections)} column sections")
            if col_sections:
                print(f"  Sample: {col_sections[:5]}")
    except Exception as e:
        print(f"  Error: {e}")


def verify_diaphragms(SapModel):
    """Check diaphragm assignments."""
    print("\n=== Diaphragm Verification ===")
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Joint Assignments - Diaphragms", [], "All", 0, [], 0, [])
        if ret[0] == 0:
            n_records = ret[5]
            print(f"  Diaphragm assignments: {n_records} joints")
        else:
            print("  No diaphragm assignments found")
    except:
        print("  Could not check diaphragms")


def verify_releases(SapModel):
    """Check end release assignments."""
    print("\n=== End Release Verification ===")
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Frame Assignments - End Releases", [], "All", 0, [], 0, [])
        if ret[0] == 0:
            n_records = ret[5]
            print(f"  End release assignments: {n_records} frames")
        else:
            print("  No end release assignments found (may use different table name)")
    except:
        print("  Could not check releases")


def verify_springs(SapModel):
    """Check spring assignments."""
    print("\n=== Spring Verification ===")
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Joint Assignments - Springs", [], "All", 0, [], 0, [])
        if ret[0] == 0:
            n_records = ret[5]
            print(f"  Point spring assignments: {n_records} joints")
        else:
            print("  No point spring assignments found")
    except:
        print("  Could not check springs")


def verify_loads(SapModel):
    """Check load assignments."""
    print("\n=== Load Verification ===")
    # Check load patterns
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Load Pattern Definitions", [], "All", 0, [], 0, [])
        if ret[0] == 0:
            fields = list(ret[4])
            data = list(ret[6])
            n_fields = len(fields)
            n_records = ret[5]
            name_idx = fields.index("Name") if "Name" in fields else 0
            for i in range(n_records):
                row = data[i * n_fields: (i + 1) * n_fields]
                print(f"  Load pattern: {row[name_idx]}")
    except:
        print("  Could not check load patterns")


def run_full_verification(SapModel):
    """Run all verification checks."""
    print("=" * 60)
    print("ETABS MODEL VERIFICATION REPORT")
    print("=" * 60)

    verify_units(SapModel)
    verify_element_counts(SapModel)
    verify_section_db(SapModel)
    verify_modifiers(SapModel)
    verify_rebar(SapModel)
    verify_diaphragms(SapModel)
    verify_releases(SapModel)
    verify_springs(SapModel)
    verify_loads(SapModel)

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    from connect_etabs import get_etabs
    SapModel = get_etabs()
    run_full_verification(SapModel)
