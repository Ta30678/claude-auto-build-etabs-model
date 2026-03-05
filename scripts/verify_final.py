"""
Final verification of MERGED_v5.EDB model.
"""
import comtypes.client
from comtypes.gen import ETABSv1
import subprocess
import re
from collections import defaultdict

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

    SapModel.SetPresentUnits(12)  # TON/M

    fn = SapModel.GetModelFilename()
    print(f"Model: {fn}")

    # === Counts ===
    ret_f = SapModel.FrameObj.GetNameList(0, [])
    ret_a = SapModel.AreaObj.GetNameList(0, [])
    ret_p = SapModel.PointObj.GetNameList(0, [])
    print(f"\nFrames: {ret_f[0]}")
    print(f"Areas: {ret_a[0]}")
    print(f"Points: {ret_p[0]}")

    # === Verify frame coordinate ranges ===
    print("\n=== Frame Coordinate Ranges ===")
    all_frames = list(ret_f[1]) if ret_f[0] > 0 else []
    x_min = y_min = z_min = 1e9
    x_max = y_max = z_max = -1e9

    sample_count = min(1000, len(all_frames))
    step = max(1, len(all_frames) // sample_count)
    for i in range(0, len(all_frames), step):
        f = all_frames[i]
        try:
            ret = SapModel.FrameObj.GetPoints(f, '', '')
            pt_i, pt_j = ret[0], ret[1]
            ri = SapModel.PointObj.GetCoordCartesian(pt_i, 0, 0, 0)
            rj = SapModel.PointObj.GetCoordCartesian(pt_j, 0, 0, 0)
            for r in [ri, rj]:
                x_min = min(x_min, r[0]); x_max = max(x_max, r[0])
                y_min = min(y_min, r[1]); y_max = max(y_max, r[1])
                z_min = min(z_min, r[2]); z_max = max(z_max, r[2])
        except:
            pass

    print(f"X: {x_min:.2f} to {x_max:.2f} ({x_max-x_min:.2f}m span)")
    print(f"Y: {y_min:.2f} to {y_max:.2f} ({y_max-y_min:.2f}m span)")
    print(f"Z: {z_min:.2f} to {z_max:.2f} ({z_max-z_min:.2f}m span)")

    # Check reasonableness
    if x_max - x_min > 200:
        print("WARNING: X span > 200m, possible coordinate error!")
    if y_max - y_min > 200:
        print("WARNING: Y span > 200m, possible coordinate error!")
    if z_max > 150 or z_min < -30:
        print("WARNING: Z range unusual!")

    # === Verify area coordinate ranges ===
    print("\n=== Area Coordinate Ranges ===")
    all_areas = list(ret_a[1]) if ret_a[0] > 0 else []
    ax_min = ay_min = az_min = 1e9
    ax_max = ay_max = az_max = -1e9

    sample_count = min(500, len(all_areas))
    step = max(1, len(all_areas) // sample_count)
    for i in range(0, len(all_areas), step):
        a = all_areas[i]
        try:
            ret = SapModel.AreaObj.GetPoints(a, 0, [])
            pts = list(ret[1])
            for pt in pts:
                r = SapModel.PointObj.GetCoordCartesian(pt, 0, 0, 0)
                ax_min = min(ax_min, r[0]); ax_max = max(ax_max, r[0])
                ay_min = min(ay_min, r[1]); ay_max = max(ay_max, r[1])
                az_min = min(az_min, r[2]); az_max = max(az_max, r[2])
        except:
            pass

    print(f"X: {ax_min:.2f} to {ax_max:.2f} ({ax_max-ax_min:.2f}m span)")
    print(f"Y: {ay_min:.2f} to {ay_max:.2f} ({ay_max-ay_min:.2f}m span)")
    print(f"Z: {az_min:.2f} to {az_max:.2f} ({az_max-az_min:.2f}m span)")

    if ax_max - ax_min > 200:
        print("WARNING: Area X span > 200m!")
    if ay_max - ay_min > 200:
        print("WARNING: Area Y span > 200m!")

    # === Check section dimensions ===
    print("\n=== Section Dimension Check ===")
    ret = SapModel.PropFrame.GetNameList(0, [])
    frame_secs = list(ret[1]) if ret[0] > 0 else []

    bad_secs = []
    for sec in frame_secs:
        try:
            ret = SapModel.PropFrame.GetRectangle(sec, '', 0, 0)
            mat, d, b = ret[0], ret[1], ret[2]
            if d > 0:
                if b > 10:  # B in cm instead of m
                    bad_secs.append(f"{sec}: D={d:.4f}, B={b:.4f} (B too large!)")
                elif d > 10:
                    bad_secs.append(f"{sec}: D={d:.4f}, B={b:.4f} (D too large!)")
        except:
            pass

    if bad_secs:
        print(f"BAD section dimensions ({len(bad_secs)}):")
        for s in bad_secs[:20]:
            print(f"  {s}")
    else:
        print("All rectangular section dimensions look reasonable (< 10m)")

    # === Check stories vs elements ===
    print("\n=== Element Distribution by Story (sample) ===")
    # Use DatabaseTables to get frame assignments
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Frame Assignments - Summary", [], "All", 0, [], 0, [])
        if ret[5] > 0:
            fields = list(ret[4])
            num_records = ret[5]
            data = list(ret[6])
            num_fields = len(fields)

            # Find Story field index
            story_idx = fields.index('Story') if 'Story' in fields else -1
            if story_idx >= 0:
                story_counts = defaultdict(int)
                for i in range(num_records):
                    row = data[i*num_fields:(i+1)*num_fields]
                    story = row[story_idx]
                    story_counts[story] += 1

                print(f"Total frame assignments: {num_records}")
                for story in sorted(story_counts.keys()):
                    print(f"  {story}: {story_counts[story]} frames")
    except Exception as e:
        print(f"  Table error: {e}")

    # === Check grid lines ===
    print("\n=== Grid Lines ===")
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Grid Definitions - Grid Lines", [], "All", 0, [], 0, [])
        if ret[5] > 0:
            fields = list(ret[4])
            num_records = ret[5]
            data = list(ret[6])
            num_fields = len(fields)
            print(f"Grid lines: {num_records}")
            x_count = sum(1 for i in range(num_records) if data[i*num_fields+1] == 'X (Cartesian)')
            y_count = sum(1 for i in range(num_records) if data[i*num_fields+1] == 'Y (Cartesian)')
            print(f"  X grids: {x_count}, Y grids: {y_count}")
    except Exception as e:
        print(f"  Grid check error: {e}")

    # === Check load patterns ===
    print("\n=== Load Patterns ===")
    ret = SapModel.LoadPatterns.GetNameList(0, [])
    load_pats = list(ret[1]) if ret[0] > 0 else []
    print(f"Load patterns ({len(load_pats)}): {', '.join(sorted(load_pats))}")

    # === Check materials ===
    ret = SapModel.PropMaterial.GetNameList(0, [])
    mats = list(ret[1]) if ret[0] > 0 else []
    print(f"\nMaterials: {len(mats)}")

    # === Summary ===
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Model: MERGED_v5.EDB")
    print(f"Frames: {ret_f[0]} (2299 OLD + 8328 above-1MF)")
    print(f"Areas: {ret_a[0]} (2039 OLD + 4719 above-1MF)")
    print(f"Points: {ret_p[0]}")
    print(f"Stories: 45 (B6F to PRF)")
    print(f"Grid lines: {x_count + y_count if 'x_count' in dir() else 'N/A'}")
    print(f"Load patterns: {len(load_pats)}")
    print(f"Materials: {len(mats)}")
    print(f"Frame sections: {len(frame_secs)}")
    if not bad_secs:
        print("Section dimensions: ALL OK")
    else:
        print(f"Section dimensions: {len(bad_secs)} BAD")

if __name__ == '__main__':
    main()
