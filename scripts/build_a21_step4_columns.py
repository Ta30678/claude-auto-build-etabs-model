"""
A21 Model Build - Step 4: Create All Columns
Uses AddByCoord with correct coordinates and sections per floor.

+1 Floor Rule: Column shown on NF plan -> ETABS story (N+1)F
  In AddByCoord, we use z_bot = story_bottom, z_top = story_top
  So the actual coordinates already encode the correct position.

Grid coordinates (m):
  Lower (B3F~1F): X: A=-8.5, B=0, C=8.5, D=19.5, E=30.5, F=41.5
                   Y: 4=-9.0, 5=0, 6=9.0, 7=17.6, 8=27.4, 9=37.2
  Upper (2F~R1F): X: B=0, C=8.5, D=19.5, E=30.5
                   Y: 5=0, 6=9.0, 7=17.6, 8=27.4
  R2F~PRF:        X: C=8.5, D=19.5
                   Y: 6=9.0, 7=17.6
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

    # Grid coordinates
    lower_x = {"A": -8.5, "B": 0.0, "C": 8.5, "D": 19.5, "E": 30.5, "F": 41.5}
    lower_y = {"4": -9.0, "5": 0.0, "6": 9.0, "7": 17.6, "8": 27.4, "9": 37.2}
    upper_x = {"B": 0.0, "C": 8.5, "D": 19.5, "E": 30.5}
    upper_y = {"5": 0.0, "6": 9.0, "7": 17.6, "8": 27.4}
    roof_x  = {"C": 8.5, "D": 19.5}
    roof_y  = {"6": 9.0, "7": 17.6}

    # Story elevations (top of story)
    # Base = -10.2m, each story 3.4m
    base_elev = -10.2
    story_names = [
        "B3F","B2F","B1F","1F",
        "2F","3F","4F","5F","6F","7F","8F","9F","10F",
        "11F","12F","13F","14F",
        "R1F","R2F","R3F","PRF"
    ]
    story_elevs = {}
    elev = base_elev
    for name in story_names:
        story_elevs[name] = (elev, elev + 3.4)  # (bot, top)
        elev += 3.4

    # Column placement table:
    # ETABS Story | Grid Range | Section
    col_config = [
        # Basement: 6x6 grid (A-F x 4-9), C120X180C350
        ("B3F", lower_x, lower_y, "C120X180C350"),
        ("B2F", lower_x, lower_y, "C120X180C350"),
        ("B1F", lower_x, lower_y, "C120X180C350"),
        ("1F",  lower_x, lower_y, "C120X180C350"),
        # Upper: 4x4 grid (B-E x 5-8)
        ("2F",  upper_x, upper_y, "C120X150C350"),
        ("3F",  upper_x, upper_y, "C120X150C280"),
        ("4F",  upper_x, upper_y, "C120X120C280"),
        ("5F",  upper_x, upper_y, "C120X120C280"),
        ("6F",  upper_x, upper_y, "C120X120C280"),
        ("7F",  upper_x, upper_y, "C120X120C280"),
        ("8F",  upper_x, upper_y, "C120X120C280"),
        ("9F",  upper_x, upper_y, "C120X120C280"),
        ("10F", upper_x, upper_y, "C120X120C280"),
        ("11F", upper_x, upper_y, "C120X120C280"),
        ("12F", upper_x, upper_y, "C120X120C280"),
        ("13F", upper_x, upper_y, "C120X120C280"),
        ("14F", upper_x, upper_y, "C120X120C280"),
        ("R1F", upper_x, upper_y, "C120X120C280"),
        # Roof: 2x2 grid (C-D x 6-7)
        ("R2F", roof_x,  roof_y,  "C100X100C280"),
        ("R3F", roof_x,  roof_y,  "C100X100C280"),
        ("PRF", roof_x,  roof_y,  "C100X100C280"),
    ]

    total_cols = 0
    col_names_all = []

    for story, x_dict, y_dict, section in col_config:
        z_bot, z_top = story_elevs[story]
        count = 0
        for x_label, x_coord in sorted(x_dict.items()):
            for y_label, y_coord in sorted(y_dict.items()):
                name = ""
                ret = sm.FrameObj.AddByCoord(
                    x_coord, y_coord, z_bot,
                    x_coord, y_coord, z_top,
                    name, section
                )
                if isinstance(ret, (list, tuple)):
                    col_name = ret[0]
                    status = ret[-1]
                else:
                    col_name = "?"
                    status = ret

                if status == 0:
                    count += 1
                    col_names_all.append(col_name)
                else:
                    print(f"  [FAIL] {story} ({x_label},{y_label}) -> ret={ret}")

        n_expected = len(x_dict) * len(y_dict)
        total_cols += count
        print(f"  {story}: {count}/{n_expected} columns ({section}), z=[{z_bot:.1f}, {z_top:.1f}]")

    print(f"\n[SUMMARY] Total columns created: {total_cols}")

    # Verify
    fr = sm.FrameObj.GetNameList(0, [])
    print(f"Total frame objects in model: {fr[0]}")

    # Refresh view
    sm.View.RefreshView(0, False)

    # Save
    ret = sm.File.Save(r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\A21\MODEL\A21.EDB")
    print(f"File.Save: ret={ret}")
    print("[OK] All columns created and saved")

if __name__ == "__main__":
    main()
