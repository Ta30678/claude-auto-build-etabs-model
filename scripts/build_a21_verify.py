"""
A21 Model Build - Final Verification
Checks stories, grids, materials, sections, columns, modifiers, rebar.
"""
import comtypes.client
import sys

def connect_etabs():
    try:
        etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        sm = etabs.SapModel
        return etabs, sm
    except Exception as e:
        print(f"[ERROR] Cannot connect to ETABS: {e}")
        sys.exit(1)

def main():
    etabs, sm = connect_etabs()
    sm.SetPresentUnits(12)
    print("=" * 60)
    print("A21 MODEL VERIFICATION REPORT")
    print("=" * 60)

    # 1. Units
    units = sm.GetPresentUnits()
    print(f"\n1. Units: {units} (expected 12=TON_M) -> {'OK' if units == 12 else 'FAIL'}")

    # 2. Stories
    r = sm.Story.GetStories_2(0.0, 0, [], [], [], [], [], [], [], [])
    base_elev = r[0]
    num_stories = r[1]
    story_names = list(r[2])
    story_elevs = list(r[3])
    story_heights = list(r[4])

    print(f"\n2. Stories: {num_stories} stories (expected 21)")
    expected_stories = ["B3F","B2F","B1F","1F","2F","3F","4F","5F","6F","7F","8F","9F","10F",
                        "11F","12F","13F","14F","R1F","R2F","R3F","PRF"]
    if story_names == expected_stories:
        print(f"   Story names: OK")
    else:
        print(f"   Story names MISMATCH!")
        print(f"   Got:      {story_names}")
        print(f"   Expected: {expected_stories}")

    print(f"   Base elevation: {base_elev:.1f} m (expected -10.2)")
    print(f"   Story elevations (top):")
    for name, elev, h in zip(story_names, story_elevs, story_heights):
        print(f"     {name:>4s}: elev={elev:7.1f}m, height={h:.1f}m")

    # 3. Grid
    ret = sm.DatabaseTables.GetTableForDisplayArray(
        "Grid Definitions - Grid Lines", [], "", 0, [], 0, []
    )
    num_grids = ret[3]
    print(f"\n3. Grid Lines: {num_grids} (expected 12 = 6X + 6Y)")
    if num_grids > 0:
        fields = list(ret[2])
        data = list(ret[4])
        nf = len(fields)
        x_count = 0
        y_count = 0
        for i in range(num_grids):
            row = data[i*nf:(i+1)*nf]
            line_type = row[1] if len(row) > 1 else "?"
            grid_id = row[2] if len(row) > 2 else "?"
            ordinate = row[3] if len(row) > 3 else "?"
            if "X" in line_type:
                x_count += 1
            elif "Y" in line_type:
                y_count += 1
            print(f"     {line_type}: {grid_id} = {ordinate} m")
        print(f"   X grids: {x_count}, Y grids: {y_count}")

    # 4. Materials
    mat = sm.PropMaterial.GetNameList(0, [])
    mat_names = list(mat[1])
    print(f"\n4. Materials: {mat[0]} total")
    required_mats = ["C280", "C315", "C350", "C420", "C490", "SD420", "SD490"]
    for m in required_mats:
        status = "OK" if m in mat_names else "MISSING"
        print(f"   {m}: {status}")

    # 5. Frame Sections
    fs = sm.PropFrame.GetNameList(0, [])
    fs_names = list(fs[1])
    print(f"\n5. Frame Sections: {fs[0]} total")
    required_sections = [
        "C120X180C350", "C120X150C350", "C120X150C280", "C120X120C280", "C100X100C280",
        "B50X70C350", "B90X120C280", "B85X100C280", "B70X95C280",
        "SB45X65C280", "SB45X65C350", "SB30X60C280", "SB30X60C350",
        "SB25X50C280", "SB25X50C350", "WB50X70C350"
    ]
    for s in required_sections:
        status = "OK" if s in fs_names else "MISSING"
        print(f"   {s}: {status}")

    # Verify section dimensions (T3=depth, T2=width)
    print("\n   Section dimension check (T3=depth, T2=width):")
    section_dims = {
        "C120X180C350": (1.8, 1.2),   # depth=180=1.8, width=120=1.2
        "C120X150C350": (1.5, 1.2),
        "C120X120C280": (1.2, 1.2),
        "C100X100C280": (1.0, 1.0),
        "B85X100C280":  (1.0, 0.85),  # depth=100=1.0, width=85=0.85
        "B50X70C350":   (0.7, 0.5),
    }
    for sec_name, (exp_t3, exp_t2) in section_dims.items():
        ret = sm.PropFrame.GetRectangle(sec_name, "", 0.0, 0.0)
        # ret format: (mat, t3, t2, color, notes, guid, retval)
        # Need to figure out exact return format
        if isinstance(ret, (list, tuple)):
            # Try to find T3 and T2 in the return
            t3 = ret[1] if len(ret) > 1 else None
            t2 = ret[2] if len(ret) > 2 else None
            if isinstance(t3, (int, float)) and isinstance(t2, (int, float)):
                t3_ok = abs(t3 - exp_t3) < 0.01
                t2_ok = abs(t2 - exp_t2) < 0.01
                status = "OK" if (t3_ok and t2_ok) else f"FAIL(T3={t3}, T2={t2})"
                print(f"   {sec_name}: T3={t3:.2f}(exp {exp_t3}), T2={t2:.2f}(exp {exp_t2}) -> {status}")
            else:
                print(f"   {sec_name}: ret={ret}")
        else:
            print(f"   {sec_name}: ret={ret}")

    # 6. Area Sections
    asec = sm.PropArea.GetNameList(0, [])
    asec_names = list(asec[1])
    print(f"\n6. Area Sections: {asec[0]} total")
    required_area = ["S15C280", "S20C280", "S15C350"]
    for s in required_area:
        status = "OK" if s in asec_names else "MISSING"
        print(f"   {s}: {status}")

    # 7. Frame Objects (Columns)
    fr = sm.FrameObj.GetAllFrames(0, [], [], [], [], [], [], [], [], [], [], [],
                                   [], [], [], [], [], [], [], [])
    num_frames = fr[0]
    frame_names = list(fr[1])
    frame_sections = list(fr[2])
    frame_stories = list(fr[3])
    pt1x = list(fr[6])
    pt1y = list(fr[7])
    pt1z = list(fr[8])
    pt2x = list(fr[9])
    pt2y = list(fr[10])
    pt2z = list(fr[11])

    # Count columns by story
    col_by_story = {}
    col_by_section = {}
    for i in range(num_frames):
        x1, y1, z1 = pt1x[i], pt1y[i], pt1z[i]
        x2, y2, z2 = pt2x[i], pt2y[i], pt2z[i]
        if abs(x1 - x2) < 0.01 and abs(y1 - y2) < 0.01:  # vertical = column
            story = frame_stories[i]
            sec = frame_sections[i]
            col_by_story[story] = col_by_story.get(story, 0) + 1
            col_by_section[sec] = col_by_section.get(sec, 0) + 1

    print(f"\n7. Columns: {sum(col_by_story.values())} total (expected 380)")
    print("   By story:")
    for story in expected_stories:
        count = col_by_story.get(story, 0)
        if story in ["B3F","B2F","B1F","1F"]:
            expected = 36
        elif story in ["R2F","R3F","PRF"]:
            expected = 4
        else:
            expected = 16
        status = "OK" if count == expected else f"FAIL(expected {expected})"
        print(f"     {story:>4s}: {count} columns -> {status}")

    print("   By section:")
    for sec, count in sorted(col_by_section.items()):
        print(f"     {sec}: {count}")

    # 8. Check modifiers on a sample column
    print(f"\n8. Column Modifier Check (sample):")
    if num_frames > 0:
        sample_col = frame_names[0]
        ret = sm.FrameObj.GetModifiers(sample_col, [])
        if isinstance(ret, (list, tuple)):
            mods = list(ret[0]) if isinstance(ret[0], (list, tuple)) else ret[:-1]
            print(f"   {sample_col}: {[round(m,4) for m in mods]}")
            expected_mods = [1.0, 1.0, 1.0, 0.0001, 0.7, 0.7, 0.95, 0.95]
            match = all(abs(a - b) < 0.001 for a, b in zip(mods, expected_mods))
            print(f"   Expected: {expected_mods} -> {'OK' if match else 'FAIL'}")

    # 9. Check rebar on a sample section
    print(f"\n9. Column Rebar Check:")
    for sec_name in ["C120X180C350", "C100X100C280"]:
        ret = sm.PropFrame.GetRebarColumn(sec_name, "", "", 0, 0, 0.0, 0, 0, 0, "", "", 0.0, 0, 0, False)
        if isinstance(ret, (list, tuple)):
            # MatLong, MatConfine, Pattern, ConfineType, Cover, NCBars, NR3, NR2, RebarSize, TieSize, TieSpacing, N2Dir, N3Dir, ToBeDesigned, retval
            mat_long = ret[0]
            cover = ret[4] if len(ret) > 4 else "?"
            nr3 = ret[6] if len(ret) > 6 else "?"
            nr2 = ret[7] if len(ret) > 7 else "?"
            rebar_size = ret[8] if len(ret) > 8 else "?"
            to_design = ret[13] if len(ret) > 13 else "?"
            last = ret[-1]
            print(f"   {sec_name}: mat={mat_long}, cover={cover}, NR3={nr3}, NR2={nr2}, bar={rebar_size}, design={to_design}, ret={last}")

    # Summary
    total_cols = sum(col_by_story.values())
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Stories:          {num_stories} (B3F~PRF)")
    print(f"  Base elevation:   {base_elev:.1f} m")
    print(f"  Grid lines:       {num_grids} (6X + 6Y)")
    print(f"  Materials:        {mat[0]} total ({len([m for m in required_mats if m in mat_names])}/{len(required_mats)} required)")
    print(f"  Frame sections:   {fs[0]} total ({len([s for s in required_sections if s in fs_names])}/{len(required_sections)} required)")
    print(f"  Area sections:    {asec[0]} total ({len([s for s in required_area if s in asec_names])}/{len(required_area)} required)")
    print(f"  Columns:          {total_cols} (expected 380)")
    print(f"  Beams:            0 (not yet built - MODELER-B task)")
    print(f"  Walls:            0 (not yet built)")
    print(f"  Slabs:            0 (not yet built)")
    print(f"  Model file:       C:\\Users\\User\\Desktop\\V22 AGENTIC MODEL\\ETABS REF\\A21\\MODEL\\A21.EDB")

if __name__ == "__main__":
    main()
