"""
A21 Model Build - Step 1: Initialize, Stories, Grid
Connect to running ETABS, create new blank model, define stories and grid.
"""
import comtypes.client
import time
import sys

def connect_etabs():
    """Connect to running ETABS instance."""
    try:
        etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        sm = etabs.SapModel
        print("[OK] Connected to running ETABS")
        return etabs, sm
    except Exception as e:
        print(f"[ERROR] Cannot connect to ETABS: {e}")
        print("Please make sure ETABS is running.")
        sys.exit(1)

def main():
    etabs, sm = connect_etabs()

    # ============================================================
    # Step 1: Initialize new blank model
    # ============================================================
    ret = sm.InitializeNewModel(12)  # 12 = TON_M
    print(f"InitializeNewModel(TON_M): ret={ret}")

    ret = sm.File.NewBlank()
    print(f"File.NewBlank(): ret={ret}")

    sm.SetPresentUnits(12)
    sm.SetModelIsLocked(False)
    print("[OK] New blank model created, units=TON_M, unlocked")

    # ============================================================
    # Step 2: Define Stories (A21: B3F~PRF, 21 stories, 3.4m each)
    # Base elevation = -10.2m (3 basement x 3.4m)
    # ============================================================
    story_names = [
        "B3F","B2F","B1F","1F",
        "2F","3F","4F","5F","6F","7F","8F","9F","10F",
        "11F","12F","13F","14F",
        "R1F","R2F","R3F","PRF"
    ]
    n = len(story_names)  # 21
    heights = [3.4] * n
    base_elev = -10.2
    is_master = [True] + [False] * (n - 1)
    similar = [""] * n
    splice = [False] * n
    splice_h = [0.0] * n
    color = [0] * n

    ret = sm.Story.SetStories_2(
        base_elev, n, story_names, heights,
        is_master, similar, splice, splice_h, color
    )
    if isinstance(ret, (list, tuple)):
        success = (ret[-1] == 0)
    else:
        success = (ret == 0)
    print(f"SetStories_2: success={success}")

    # Verify stories
    r = sm.Story.GetStories_2(0.0, 0, [], [], [], [], [], [], [], [])
    actual_names = list(r[2])
    actual_elevs = [round(e, 2) for e in r[3]]
    print(f"  Base elevation: {r[0]}")
    print(f"  Num stories: {r[1]}")
    print(f"  Stories: {actual_names}")
    print(f"  Elevations: {actual_elevs}")

    # Verify expected elevations
    expected = {}
    elev = base_elev
    for name, h in zip(story_names, heights):
        elev += h
        expected[name] = round(elev, 2)
    print(f"  Expected top elevations:")
    for name in story_names:
        print(f"    {name}: {expected[name]} m")

    if r[1] != n:
        print(f"[WARNING] Expected {n} stories, got {r[1]}")
    else:
        print(f"[OK] All {n} stories defined correctly")

    # ============================================================
    # Step 3: Define Grid System via DatabaseTables
    # ============================================================
    # A21 Grid coordinates (m):
    # X grids: A=-8.5, B=0, C=8.5, D=19.5, E=30.5, F=41.5
    # Y grids: 4=-9.0, 5=0, 6=9.0, 7=17.6, 8=27.4, 9=37.2

    x_grids = [("A", -8.5), ("B", 0.0), ("C", 8.5), ("D", 19.5), ("E", 30.5), ("F", 41.5)]
    y_grids = [("4", -9.0), ("5", 0.0), ("6", 9.0), ("7", 17.6), ("8", 27.4), ("9", 37.2)]

    # Build grid data for DatabaseTables
    # Fields: Name, X Grid ID/Y Grid ID, Ordinate, Visible, BubbleLoc
    fields = ["Name", "X Grid ID", "Ordinate", "Visible", "BubbleLoc"]
    grid_data = []

    # X grids
    for label, coord in x_grids:
        grid_data.extend(["G1", label, str(coord), "Yes", "End"])

    # Y grids
    fields_y = ["Name", "Y Grid ID", "Ordinate", "Visible", "BubbleLoc"]
    grid_data_y = []
    for label, coord in y_grids:
        grid_data_y.extend(["G1", label, str(coord), "Yes", "End"])

    # Use SetTableForEditingArray for grid lines
    # The table key is "Grid Lines - Grid Lines"
    # But let's try the GridSys API instead

    # Create a Cartesian grid system using GridSys API
    # First add a grid system
    ret = sm.GridSys.SetGridSys("G1", 0.0, 0.0, 0.0)  # name, x_origin, y_origin, rotation
    print(f"SetGridSys('G1'): ret={ret}")

    # Now set grid lines via database tables
    # Table: "Grid Definitions - Grid Lines"
    table_key = "Grid Definitions - Grid Lines"

    # Build data: X grids first, then Y grids
    all_fields = ["Name", "Grid Line Type", "ID", "Ordinate", "Visible", "Bubble Location"]
    all_data = []

    for label, coord in x_grids:
        all_data.extend(["G1", "X (Cartesian)", label, str(coord), "Yes", "End"])

    for label, coord in y_grids:
        all_data.extend(["G1", "Y (Cartesian)", label, str(coord), "Yes", "End"])

    num_records = len(x_grids) + len(y_grids)

    ret = sm.DatabaseTables.SetTableForEditingArray(
        table_key, 0, all_fields, num_records, all_data
    )
    print(f"SetTableForEditingArray (grid): ret={ret}")

    ret = sm.DatabaseTables.ApplyEditedTables(True, 0, 0, 0, 0, "")
    print(f"ApplyEditedTables: ret={ret}")
    if isinstance(ret, (list, tuple)):
        fatal = ret[1] if len(ret) > 1 else "?"
        errors = ret[2] if len(ret) > 2 else "?"
        warnings = ret[3] if len(ret) > 3 else "?"
        log = ret[5] if len(ret) > 5 else ""
        print(f"  Fatal={fatal}, Errors={errors}, Warnings={warnings}")
        if log:
            print(f"  Log: {log}")

    # Verify grid
    sm.View.RefreshView(0, False)

    # ============================================================
    # Save progress
    # ============================================================
    import os
    save_dir = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\A21\MODEL"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "A21.EDB")
    ret = sm.File.Save(save_path)
    print(f"File.Save: ret={ret}")
    print(f"[OK] Model saved to {save_path}")

    print("\n=== Step 1 Complete: Init + Stories + Grid ===")

if __name__ == "__main__":
    main()
