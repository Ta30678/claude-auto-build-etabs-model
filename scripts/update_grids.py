"""
Update grid lines in the MERGED_v4.EDB model using the ETABS API.
Read grid positions from merged e2k and apply them.
"""
import comtypes.client
from comtypes.gen import ETABSv1
import subprocess
import re

def connect_etabs():
    helper = comtypes.client.CreateObject('ETABSv1.Helper')
    helper = helper.QueryInterface(ETABSv1.cHelper)
    result = subprocess.run(['tasklist'], capture_output=True, text=True)
    pids = [int(line.split()[1]) for line in result.stdout.split('\n') if 'ETABS.exe' in line]
    for pid in pids:
        try:
            etabs = helper.GetObjectProcess('CSI.ETABS.API.ETABSObject', pid)
            if etabs is not None:
                return etabs.SapModel, pid
        except:
            pass
    return None, None

def main():
    SapModel, pid = connect_etabs()
    if not SapModel:
        print("ERROR: Cannot connect")
        return
    print(f"Connected to PID {pid}")

    # Set units to TON/M
    SapModel.SetPresentUnits(12)
    SapModel.SetModelIsLocked(False)

    # Parse grids from merged e2k
    merged = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_ALL_v2.e2k'
    with open(merged, 'r', encoding='utf-8') as f:
        content = f.read()

    x_grids = []
    y_grids = []
    for line in content.split('\n'):
        m = re.match(r'\s+GRID\s+"([^"]+)"\s+LABEL\s+"([^"]+)"\s+DIR\s+"([^"]+)"\s+COORD\s+([\d.\-E+]+)', line)
        if m:
            label = m.group(2)
            direction = m.group(3)
            coord = float(m.group(4))
            if direction == 'X':
                x_grids.append((label, coord))
            elif direction == 'Y':
                y_grids.append((label, coord))

    print(f"Merged e2k grids: {len(x_grids)} X, {len(y_grids)} Y")

    # Get current grid system
    ret = SapModel.GridSys.GetGridSysCartesian(
        "G1", 0.0, 0.0, 0.0, True, "", "", 0.0, 0, 0, [], [], [], [], 0, [], [], [], [], 0, [], [], [], [], [], [], [])

    cur_x_labels = list(ret[9])
    cur_x_coords = list(ret[10])
    cur_y_labels = list(ret[14])
    cur_y_coords = list(ret[15])

    print(f"Current OLD grids: {len(cur_x_labels)} X, {len(cur_y_labels)} Y")

    # Show differences
    print("\n=== Grid Changes ===")
    merged_x = dict(x_grids)
    merged_y = dict(y_grids)

    for label in cur_x_labels:
        if label in merged_x:
            old_c = cur_x_coords[cur_x_labels.index(label)]
            new_c = merged_x[label]
            if abs(old_c - new_c) > 0.001:
                print(f"  X {label}: {old_c:.4f} -> {new_c:.4f} (delta={new_c-old_c:.4f})")
        else:
            print(f"  X {label}: EXISTS in OLD but not in merged")

    # New grids not in OLD
    for label, coord in x_grids:
        if label not in cur_x_labels:
            print(f"  X {label}: NEW at {coord:.4f}")

    for label in cur_y_labels:
        if label in merged_y:
            old_c = cur_y_coords[cur_y_labels.index(label)]
            new_c = merged_y[label]
            if abs(old_c - new_c) > 0.001:
                print(f"  Y {label}: {old_c:.4f} -> {new_c:.4f} (delta={new_c-old_c:.4f})")

    for label, coord in y_grids:
        if label not in cur_y_labels:
            print(f"  Y {label}: NEW at {coord:.4f}")

    # Prepare new grid data
    # Keep all existing grids and add/update with merged data
    new_x_labels = []
    new_x_coords = []
    new_x_visible = []
    new_x_bubble = []

    # Start with merged X grids (these have the updated coordinates)
    for label, coord in x_grids:
        new_x_labels.append(label)
        new_x_coords.append(coord)
        new_x_visible.append(True)
        new_x_bubble.append("b")  # b = bottom

    new_y_labels = []
    new_y_coords = []
    new_y_visible = []
    new_y_bubble = []

    for label, coord in y_grids:
        new_y_labels.append(label)
        new_y_coords.append(coord)
        new_y_visible.append(True)
        new_y_bubble.append("a")  # a = above (switched)

    print(f"\nNew grids to set: {len(new_x_labels)} X, {len(new_y_labels)} Y")

    # Use SetGridSys to update
    # SetGridSys(Name, Xo, Yo, RZ, StoryRangeIsDefault, TopStory, BottomStory,
    #   BubbleSize, NumXLines, GridLineIDX, OrdinateX, VisibleX, BubbleLocX,
    #   NumYLines, GridLineIDY, OrdinateY, VisibleY, BubbleLocY)
    try:
        ret = SapModel.GridSys.SetGridSys(
            "G1",           # Name
            0.0,            # Xo
            0.0,            # Yo
            0.0,            # RZ
            True,           # StoryRangeIsDefault
            "",             # TopStory
            "",             # BottomStory
            1.25,           # BubbleSize
            len(new_x_labels),  # NumXLines
            new_x_labels,       # GridLineIDX
            new_x_coords,       # OrdinateX
            new_x_visible,      # VisibleX
            new_x_bubble,       # BubbleLocX
            len(new_y_labels),  # NumYLines
            new_y_labels,       # GridLineIDY
            new_y_coords,       # OrdinateY
            new_y_visible,      # VisibleY
            new_y_bubble,       # BubbleLocY
        )
        print(f"SetGridSys result: {ret}")
    except Exception as e:
        print(f"SetGridSys error: {e}")
        import traceback
        traceback.print_exc()

    # Verify
    ret = SapModel.GridSys.GetGridSysCartesian(
        "G1", 0.0, 0.0, 0.0, True, "", "", 0.0, 0, 0, [], [], [], [], 0, [], [], [], [], 0, [], [], [], [], [], [], [])

    print(f"\nVerification - X grids: {len(ret[9])}, Y grids: {len(ret[14])}")
    for l, c in zip(ret[9], ret[10]):
        print(f"  X {l}: {c:.4f}")
    for l, c in zip(ret[14], ret[15]):
        print(f"  Y {l}: {c:.4f}")

    # Refresh and save
    SapModel.View.RefreshView(0, False)
    output = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v4.EDB'
    SapModel.File.Save(output)
    print(f"\nSaved to: {output}")

if __name__ == '__main__':
    main()
