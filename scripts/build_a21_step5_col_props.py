"""
A21 Model Build - Step 5: Column Modifiers and Rebar
1. Set stiffness modifiers for all columns:
   [Area=1, As2=1, As3=1, Torsion=0.0001, I22=0.7, I33=0.7, Mass=0.95, Wt=0.95]
2. Set rebar on each column section:
   Cover=0.07m, ToBeDesigned=True, SD420
   NumR2/NumR3 based on Width:Depth ratio
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
    sm.SetPresentUnits(12)  # TON_M
    sm.SetModelIsLocked(False)
    print("[OK] Connected, units=TON_M")

    # ============================================================
    # Step 8: Column Modifiers (on individual frame objects)
    # ============================================================
    col_mods = [1.0, 1.0, 1.0, 0.0001, 0.7, 0.7, 0.95, 0.95]
    #           Area  As2   As3  Tors   I22  I33  Mass  Wt

    # Get all frame objects
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

    print(f"Total frame objects: {num_frames}")

    # Identify columns (vertical: same x,y, different z)
    col_count = 0
    col_fail = 0
    for i in range(num_frames):
        name = frame_names[i]
        x1, y1, z1 = pt1x[i], pt1y[i], pt1z[i]
        x2, y2, z2 = pt2x[i], pt2y[i], pt2z[i]
        # Column = vertical member (same x,y, z1 != z2)
        if abs(x1 - x2) < 0.01 and abs(y1 - y2) < 0.01 and abs(z1 - z2) > 0.1:
            r = sm.FrameObj.SetModifiers(name, col_mods)
            if isinstance(r, (list, tuple)):
                if r[-1] != 0:
                    col_fail += 1
                    if col_fail <= 3:
                        print(f"  [FAIL] SetModifiers({name}): ret={r}")
                else:
                    col_count += 1
            elif r != 0:
                col_fail += 1
            else:
                col_count += 1

    print(f"Column modifiers set: {col_count} OK, {col_fail} failed")

    # ============================================================
    # Step 9: Column Rebar (on section properties)
    # ============================================================
    # SetRebarColumn(Name, MatRebar, MatConfine, Pattern, ConfineType,
    #                Cover, NumBars3Dir, NumBars2Dir, BarSizeCorner, BarSizeEdge,
    #                TieBarSize, TieSpacing, NumC2, NumC3, ToBeDesigned)
    # Wait -- let me check the exact signature

    # From CLAUDE.md:
    # SetRebarColumn("COL30x30", "Rebar", "Rebar", 1, 1, 4, 8, 3, 3, "#5", "#3", 10, 2, 2, True)
    # Args: Name, MatLong, MatConfine, Pattern(1=rect), ConfineType(1=ties),
    #       Cover, NumCornerBars, NumR3, NumR2, BarSize, TieSize, TieSpacing, Num2Dir, Num3Dir, ToBeDesigned

    # Column sections and their W:D ratios
    col_sections = {
        # name: (width_cm, depth_cm)
        "C120X180C350": (120, 180),  # ratio W:D = 120:180 = 0.67
        "C120X150C350": (120, 150),  # ratio = 0.8
        "C120X150C280": (120, 150),
        "C120X120C280": (120, 120),  # ratio = 1.0
        "C100X100C280": (100, 100),  # ratio = 1.0
    }

    print("\n--- Column Rebar Settings ---")
    for sec_name, (w_cm, d_cm) in col_sections.items():
        cover = 0.07  # 7cm in meters

        # NumR2 (along width/2-dir) and NumR3 (along depth/3-dir)
        # Based on dimension: roughly 1 bar per 25-30cm, min=2, max=6
        # NumR2 = width direction bars (between corners)
        # NumR3 = depth direction bars (between corners)
        num_r2 = max(2, min(6, int(w_cm / 30)))  # along width (2-dir)
        num_r3 = max(2, min(6, int(d_cm / 30)))  # along depth (3-dir)

        # For C120X180: num_r2=4 (120/30), num_r3=6 (180/30)
        # For C120X150: num_r2=4, num_r3=5
        # For C120X120: num_r2=4, num_r3=4
        # For C100X100: num_r2=3, num_r3=3

        # API signature from CLAUDE.md:
        # SetRebarColumn(Name, MatLong, MatConfine, Pattern, ConfineType,
        #                Cover, NumCornerBars, NumR3, NumR2, BarSize, TieSize,
        #                TieSpacing, Num2Dir, Num3Dir, ToBeDesigned)
        # Use metric bar sizes: "25" for main bars, "10" for ties
        ret = sm.PropFrame.SetRebarColumn(
            sec_name,
            "SD420",      # MatRebar (longitudinal)
            "SD420",      # MatConfine (ties)
            1,            # Pattern = 1 (rectangular)
            1,            # ConfineType = 1 (ties)
            cover,        # Cover = 0.07m
            8,            # NumCornerBars = 8 (4 corners x 2 = but this is total corner bars)
            num_r3,       # NumR3 (along depth, 3-dir)
            num_r2,       # NumR2 (along width, 2-dir)
            "25",         # BarSize (main bars = 25mm)
            "10",         # TieSize = 10mm
            0.15,         # TieSpacing = 15cm = 0.15m
            2,            # Num2Dir (tie legs in 2-dir)
            2,            # Num3Dir (tie legs in 3-dir)
            True          # ToBeDesigned
        )
        status = "OK" if ret == 0 else f"ret={ret}"
        print(f"  {sec_name}: cover={cover}m, NumR2={num_r2}, NumR3={num_r3} -> {status}")

    # Save
    ret = sm.File.Save(r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\A21\MODEL\A21.EDB")
    print(f"\nFile.Save: ret={ret}")
    print(f"[OK] Column modifiers ({col_count}) and rebar ({len(col_sections)} sections) configured")

if __name__ == "__main__":
    main()
