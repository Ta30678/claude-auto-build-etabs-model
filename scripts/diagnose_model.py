"""
Diagnose the current MERGED_v4.EDB model state and identify issues.
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
        print("ERROR: Cannot connect to ETABS")
        return
    print(f"Connected to PID {pid}")

    fn = SapModel.GetModelFilename()
    print(f"Model: {fn}")

    SapModel.SetPresentUnits(12)  # TON/M

    # === Basic counts ===
    ret_f = SapModel.FrameObj.GetNameList(0, [])
    ret_a = SapModel.AreaObj.GetNameList(0, [])
    ret_p = SapModel.PointObj.GetNameList(0, [])
    print(f"\nCounts: Frames={ret_f[0]}, Areas={ret_a[0]}, Points={ret_p[0]}")

    # === Stories ===
    ret = SapModel.Story.GetStories_2(0, 0, [], [], [], [], [], [], [], [])
    num_stories = ret[1]
    story_names = list(ret[2])
    story_elevs = list(ret[3])
    story_heights = list(ret[4])
    print(f"\nStories ({num_stories}):")
    for i, (name, elev, h) in enumerate(zip(story_names, story_elevs, story_heights)):
        print(f"  {name}: elev={elev:.3f}, h={h:.3f}")

    # === Frame sections ===
    ret = SapModel.PropFrame.GetNameList(0, [])
    frame_secs = list(ret[1]) if ret[0] > 0 else []
    print(f"\nFrame sections ({len(frame_secs)}):")
    for sec in sorted(frame_secs):
        print(f"  {sec}")

    # === Area sections ===
    ret = SapModel.PropArea.GetNameList(0, [])
    area_secs = list(ret[1]) if ret[0] > 0 else []
    print(f"\nArea sections ({len(area_secs)}):")
    for sec in sorted(area_secs):
        print(f"  {sec}")

    # === Materials ===
    ret = SapModel.PropMaterial.GetNameList(0, [])
    materials = list(ret[1]) if ret[0] > 0 else []
    print(f"\nMaterials ({len(materials)}):")
    for mat in sorted(materials):
        print(f"  {mat}")

    # === Load patterns ===
    ret = SapModel.LoadPatterns.GetNameList(0, [])
    load_pats = list(ret[1]) if ret[0] > 0 else []
    print(f"\nLoad patterns ({len(load_pats)}):")
    for lp in sorted(load_pats):
        print(f"  {lp}")

    # === Diaphragms ===
    ret = SapModel.Diaphragm.GetNameList(0, [])
    diaphs = list(ret[1]) if ret[0] > 0 else []
    print(f"\nDiaphragms: {diaphs}")

    # === Check frame section dimensions ===
    print("\n=== Frame Section Dimensions ===")
    for sec in sorted(frame_secs):
        try:
            # Try GetRectangle first
            ret = SapModel.PropFrame.GetRectangle(sec, '', 0, 0)
            mat = ret[0]
            d = ret[1]
            b = ret[2]
            if d > 0:
                print(f"  RECT {sec}: mat={mat}, D={d:.4f}, B={b:.4f}")
                if b > 10:
                    print(f"    *** WARNING: B={b:.4f} looks like it's in CM, not M!")
        except:
            pass

    # === Sample some frames to check coordinates ===
    print("\n=== Sample Frame Coordinates ===")
    all_frames = list(ret_f[1]) if ret_f[0] > 0 else []

    # Get some above-1MF frames
    above_prefixes = ['AC', 'AB', 'AW', 'AF', 'BC', 'BB', 'BW', 'BF', 'CC', 'CB', 'CW', 'CF', 'DC', 'DB', 'DW', 'DF']
    above_frames = [f for f in all_frames if any(f.startswith(p) for p in above_prefixes)]
    print(f"Above-1MF frames: {len(above_frames)}")

    # Check a few
    for frame in above_frames[:10]:
        try:
            ret = SapModel.FrameObj.GetPoints(frame, '', '')
            pt_i = ret[0]
            pt_j = ret[1]
            ret_i = SapModel.PointObj.GetCoordCartesian(pt_i, 0, 0, 0)
            ret_j = SapModel.PointObj.GetCoordCartesian(pt_j, 0, 0, 0)
            xi, yi, zi = ret_i[0], ret_i[1], ret_i[2]
            xj, yj, zj = ret_j[0], ret_j[1], ret_j[2]
            ret_sec = SapModel.FrameObj.GetSection(frame, '', '')
            sec = ret_sec[0]
            print(f"  {frame}: ({xi:.2f},{yi:.2f},{zi:.2f})->({xj:.2f},{yj:.2f},{zj:.2f}) sec={sec}")
        except Exception as e:
            print(f"  {frame}: ERROR {e}")

    # === Check areas ===
    all_areas = list(ret_a[1]) if ret_a[0] > 0 else []
    above_areas = [a for a in all_areas if any(a.startswith(p) for p in above_prefixes)]
    print(f"\nAbove-1MF areas: {len(above_areas)}")

    for area in above_areas[:5]:
        try:
            ret = SapModel.AreaObj.GetPoints(area, 0, [])
            num_pts = ret[0]
            pts = list(ret[1])
            ret_sec = SapModel.AreaObj.GetProperty(area, '')
            sec = ret_sec[0]
            print(f"  {area}: {num_pts} pts, sec={sec}")
            for pt in pts:
                ret_p = SapModel.PointObj.GetCoordCartesian(pt, 0, 0, 0)
                print(f"    {pt}: ({ret_p[0]:.2f},{ret_p[1]:.2f},{ret_p[2]:.2f})")
        except Exception as e:
            print(f"  {area}: ERROR {e}")

    # === Parse merged e2k to count expected elements ===
    merged = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_ALL_v2.e2k'
    with open(merged, 'r', encoding='utf-8') as f:
        content = f.read()

    # Count elements by prefix
    e2k_lines = {}
    e2k_areas = {}
    for line in content.split('\n'):
        m = re.match(r'\s+LINE\s+"([^"]+)"\s+(BEAM|COLUMN|BRACE)', line)
        if m:
            label = m.group(1)
            for p in above_prefixes:
                if label.startswith(p):
                    e2k_lines[label] = line.strip()
                    break
        m = re.match(r'\s+AREA\s+"([^"]+)"', line)
        if m:
            label = m.group(1)
            for p in above_prefixes:
                if label.startswith(p):
                    e2k_areas[label] = line.strip()
                    break

    print(f"\n=== E2K above-1MF elements ===")
    print(f"Lines: {len(e2k_lines)}")
    print(f"Areas: {len(e2k_areas)}")

    # Check which e2k areas are NOT in the model
    missing_areas = set(e2k_areas.keys()) - set(above_areas)
    print(f"\nMissing areas (in e2k but not model): {len(missing_areas)}")
    for a in sorted(list(missing_areas))[:20]:
        print(f"  {a}: {e2k_areas[a][:120]}")

    # Check which model frames are NOT from above-1MF (i.e., OLD baseline)
    old_frames = [f for f in all_frames if not any(f.startswith(p) for p in above_prefixes)]
    print(f"\nOLD baseline frames: {len(old_frames)}")
    print(f"Above-1MF frames in model: {len(above_frames)}")

    old_areas = [a for a in all_areas if not any(a.startswith(p) for p in above_prefixes)]
    print(f"OLD baseline areas: {len(old_areas)}")
    print(f"Above-1MF areas in model: {len(above_areas)}")

if __name__ == '__main__':
    main()
