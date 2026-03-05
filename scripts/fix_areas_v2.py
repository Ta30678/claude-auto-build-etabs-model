"""
Fix missing areas: Use ETABS model points for coordinates when e2k points are missing.
The OLD.EDB points are in the model but weren't in the merged e2k.
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

def parse_e2k_points_and_areas(filepath):
    """Parse e2k for points, areas, and area assigns."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    points = {}
    areas = {}
    areaassigns = defaultdict(list)

    for line in content.split('\n'):
        # Points
        m = re.match(r'\s+POINT\s+"([^"]+)"\s+([\d.\-E+]+)\s+([\d.\-E+]+)', line)
        if m:
            points[m.group(1)] = (float(m.group(2)), float(m.group(3)))
            continue

        # Areas
        m = re.match(r'\s+AREA\s+"([^"]+)"\s+(FLOOR|PANEL|RAMP|WALL)\s+(\d+)\s+(.*)', line)
        if m:
            area_name = m.group(1)
            area_type = m.group(2)
            num_pts = int(m.group(3))
            rest = m.group(4)
            # Extract quoted point names
            pt_names = re.findall(r'"([^"]+)"', rest)
            areas[area_name] = (area_type, num_pts, pt_names[:num_pts])
            continue

        # Area assigns
        m = re.match(r'\s+AREAASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"', line)
        if m:
            areaassigns[m.group(1)].append((m.group(2), m.group(3)))
            continue

    return points, areas, areaassigns

def main():
    SapModel, pid = connect_etabs()
    if not SapModel:
        print("ERROR: Cannot connect to ETABS")
        return
    print(f"Connected to PID {pid}")

    SapModel.SetPresentUnits(12)  # TON/M
    SapModel.SetModelIsLocked(False)

    # Get story data
    ret = SapModel.Story.GetStories_2(0, 0, [], [], [], [], [], [], [], [])
    story_names = list(ret[2])
    story_elevs = list(ret[3])
    story_heights = list(ret[4])
    story_elev_map = dict(zip(story_names, story_elevs))
    story_height_map = dict(zip(story_names, story_heights))

    # Parse e2k
    merged = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_ALL_v2.e2k'
    e2k_points, e2k_areas, e2k_areaassigns = parse_e2k_points_and_areas(merged)
    print(f"E2K points: {len(e2k_points)}, areas: {len(e2k_areas)}, area assigns: {len(e2k_areaassigns)}")

    # Build complete point coordinate map from ETABS model
    # First load all model points
    ret = SapModel.PointObj.GetNameList(0, [])
    model_point_names = list(ret[1]) if ret[0] > 0 else []
    print(f"Model points: {len(model_point_names)}")

    # Build a mapping of model point name -> (x, y) at their base Z
    # We need X,Y for area placement; Z comes from story elevation
    model_points_xy = {}
    print("Loading model point coordinates...")
    for pt_name in model_point_names:
        try:
            ret = SapModel.PointObj.GetCoordCartesian(pt_name, 0.0, 0.0, 0.0)
            model_points_xy[pt_name] = (ret[0], ret[1])
        except:
            pass
    print(f"Loaded {len(model_points_xy)} model point XY coords")

    # Merge: e2k points + model points
    all_points = dict(e2k_points)  # Start with e2k points
    for pt_name, (x, y) in model_points_xy.items():
        if pt_name not in all_points:
            all_points[pt_name] = (x, y)
    print(f"Total point coordinates available: {len(all_points)}")

    # Filter for above-1MF areas
    above_prefixes = ['AC', 'AB', 'AW', 'AF', 'BC', 'BB', 'BW', 'BF', 'CC', 'CB', 'CW', 'CF', 'DC', 'DB', 'DW', 'DF']
    def is_above_1mf(name):
        return any(name.startswith(p) for p in above_prefixes)

    above_areas = {k: v for k, v in e2k_areas.items() if is_above_1mf(k)}
    above_assigns = {k: v for k, v in e2k_areaassigns.items() if is_above_1mf(k)}
    print(f"\nAbove-1MF areas: {len(above_areas)}")
    print(f"Above-1MF area assigns: {len(above_assigns)}")

    # Check how many points we can now resolve
    missing_pts = set()
    for area_name, (area_type, num_pts, pt_names) in above_areas.items():
        for pt in pt_names:
            if pt not in all_points:
                missing_pts.add(pt)
    print(f"Still missing points: {len(missing_pts)}")
    if missing_pts:
        print(f"  Examples: {sorted(list(missing_pts))[:20]}")

    # Check existing area sections
    ret = SapModel.PropArea.GetNameList(0, [])
    existing_area_secs = set(ret[1]) if ret[0] > 0 else set()

    needed_secs = set()
    for area_name, assigns in above_assigns.items():
        for story, section in assigns:
            needed_secs.add(section)

    missing_secs = needed_secs - existing_area_secs
    if missing_secs:
        print(f"\nCreating missing area sections: {sorted(missing_secs)}")
        for sec in missing_secs:
            thick = 0.2
            mat = 'C420'
            try:
                ret = SapModel.PropArea.SetSlab(sec, 0, 1, mat, thick)
                print(f"  Created {sec}: ret={ret}")
            except Exception as e:
                print(f"  Error creating {sec}: {e}")

    # === ADD AREAS ===
    print("\n" + "=" * 60)
    print("ADDING AREA ELEMENTS")
    print("=" * 60)

    added = 0
    errors = 0
    error_types = defaultdict(int)

    for area_name, (area_type, num_pts, pt_names) in sorted(above_areas.items()):
        assigns = above_assigns.get(area_name, [])
        if not assigns:
            error_types['no_assign'] += 1
            continue

        for story, section in assigns:
            if story not in story_elev_map:
                error_types['bad_story'] += 1
                continue

            elev = story_elev_map[story]
            story_h = story_height_map.get(story, 3.4)

            # Get point coordinates
            X = []
            Y = []
            Z = []
            all_ok = True
            for pt in pt_names:
                if pt in all_points:
                    px, py = all_points[pt]
                    X.append(px)
                    Y.append(py)
                    Z.append(elev)  # Floor at story elevation
                else:
                    all_ok = False
                    error_types['missing_point'] += 1
                    break

            if not all_ok or len(X) < 3:
                if all_ok:
                    error_types['too_few_pts'] += 1
                continue

            # For PANEL (wall), adjust Z to span story height
            if area_type == 'PANEL' and num_pts == 4:
                bot_elev = elev - story_h
                Z = [elev, elev, bot_elev, bot_elev]

            try:
                name = ''
                ret = SapModel.AreaObj.AddByCoord(num_pts, X, Y, Z, name, section)
                if isinstance(ret, (list, tuple)):
                    added += 1
                else:
                    added += 1
            except Exception as e:
                error_types[f'api_error'] += 1

        if (added + sum(error_types.values())) % 100 == 0 and added > 0:
            print(f"  Progress: {added} added, errors={dict(error_types)}")

    print(f"\nResults: {added} added")
    print(f"Errors: {dict(error_types)}")

    # === VERIFY ===
    print("\n" + "=" * 60)
    print("FINAL STATE")
    print("=" * 60)

    ret_f = SapModel.FrameObj.GetNameList(0, [])
    ret_a = SapModel.AreaObj.GetNameList(0, [])
    ret_p = SapModel.PointObj.GetNameList(0, [])
    print(f"Frames: {ret_f[0]}")
    print(f"Areas: {ret_a[0]}")
    print(f"Points: {ret_p[0]}")

    # Sample some areas to verify
    print("\nSample new areas:")
    all_areas = list(ret_a[1]) if ret_a[0] > 0 else []
    # Get last 5 added areas
    for a in all_areas[-5:]:
        try:
            ret = SapModel.AreaObj.GetPoints(a, 0, [])
            pts = list(ret[1])
            ret_sec = SapModel.AreaObj.GetProperty(a, '')
            sec = ret_sec[0]
            coords = []
            for pt in pts:
                r = SapModel.PointObj.GetCoordCartesian(pt, 0, 0, 0)
                coords.append(f"({r[0]:.1f},{r[1]:.1f},{r[2]:.1f})")
            print(f"  {a}: sec={sec}, pts={' '.join(coords)}")
        except Exception as e:
            print(f"  {a}: ERROR {e}")

    # Save
    SapModel.View.RefreshView(0, False)
    output = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v4.EDB'
    SapModel.File.Save(output)
    print(f"\nSaved!")

if __name__ == '__main__':
    main()
