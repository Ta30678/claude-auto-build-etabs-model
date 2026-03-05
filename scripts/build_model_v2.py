"""
Build merged model v2: Start from OLD.EDB, add only above-1MF elements.
"""
import comtypes.client
from comtypes.gen import ETABSv1
import subprocess
import time
import re
import os

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

def parse_e2k(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    lines = content.split('\n')
    sections = {}
    cur = None
    cur_lines = []
    for line in lines:
        if line.startswith('$ '):
            if cur:
                sections[cur] = cur_lines
            cur = line[2:].strip()
            cur_lines = []
        else:
            cur_lines.append(line)
    if cur:
        sections[cur] = cur_lines
    return sections

def main():
    print("=" * 60)
    print("BUILD MERGED MODEL v2 - Above-1MF Only")
    print("=" * 60)

    SapModel, pid = connect_etabs()
    if not SapModel:
        print("ERROR: Cannot connect to ETABS")
        return
    print(f"Connected to PID {pid}")

    # Step 1: Open OLD.EDB as base
    old_edb = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\OLD\OLD.EDB'
    print(f"\n[1] Opening OLD.EDB...")
    ret = SapModel.File.OpenFile(old_edb)
    print(f"  OpenFile: {ret}")
    time.sleep(2)

    # Check baseline
    ret_f = SapModel.FrameObj.GetNameList(0, [])
    ret_a = SapModel.AreaObj.GetNameList(0, [])
    ret_p = SapModel.PointObj.GetNameList(0, [])
    baseline_frames = ret_f[0]
    baseline_areas = ret_a[0]
    baseline_points = ret_p[0]
    print(f"  Baseline: {baseline_frames} frames, {baseline_areas} areas, {baseline_points} points")

    # Save copy
    output = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v4.EDB'
    SapModel.File.Save(output)
    SapModel.SetModelIsLocked(False)

    # Get story data
    ret = SapModel.Story.GetStories_2(0, 0, [], [], [], [], [], [], [], [])
    story_names = list(ret[2])
    story_elevs = list(ret[3])
    story_map = dict(zip(story_names, story_elevs))
    base_elev = float(ret[0])
    print(f"  Stories: {len(story_map)}, Base elev: {base_elev}")

    # Step 2: Parse merged e2k
    merged = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_ALL_v2.e2k'
    print(f"\n[2] Parsing merged e2k...")
    sections = parse_e2k(merged)

    # Parse points
    points = {}
    for line in sections.get('POINT COORDINATES', []):
        m = re.match(r'\s+POINT\s+"([^"]+)"\s+([\d.\-E+]+)\s+([\d.\-E+]+)', line)
        if m:
            points[m.group(1)] = (float(m.group(2)), float(m.group(3)))

    # Parse line connectivities - ONLY above-1MF (prefixed labels)
    above_1mf_prefixes = ('AC', 'AB', 'AW', 'AF', 'BC', 'BB', 'BW', 'BF',
                          'CC', 'CB', 'CW', 'CF', 'DC', 'DB', 'DW', 'DF')

    new_lines = []
    for line in sections.get('LINE CONNECTIVITIES', []):
        m = re.match(r'\s+LINE\s+"([^"]+)"\s+(BEAM|COLUMN)\s+"([^"]+)"\s+"([^"]+)"\s+(\d+)', line)
        if m and m.group(1).startswith(above_1mf_prefixes):
            new_lines.append({
                'label': m.group(1),
                'type': m.group(2),
                'pt1': m.group(3),
                'pt2': m.group(4),
            })

    # Parse area connectivities - ONLY above-1MF
    new_areas = []
    for line in sections.get('AREA CONNECTIVITIES', []):
        m = re.match(r'\s+AREA\s+"([^"]+)"\s+(PANEL|FLOOR)\s+(\d+)\s+(.*)', line)
        if m and m.group(1).startswith(above_1mf_prefixes):
            label = m.group(1)
            atype = m.group(2)
            num_pts = int(m.group(3))
            rest = m.group(4)
            all_pts = re.findall(r'"([^"]+)"', rest)
            new_areas.append({
                'label': label,
                'type': atype,
                'points': all_pts[:num_pts],
            })

    # Parse line assigns for above-1MF only
    line_assigns = {}
    for line in sections.get('LINE ASSIGNS', []):
        m = re.match(r'\s+LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"(.*)$', line)
        if m and m.group(1).startswith(above_1mf_prefixes):
            label = m.group(1)
            story = m.group(2)
            section = m.group(3)
            rest = m.group(4)
            ang = 0
            am = re.search(r'ANG\s+([\d.\-E+]+)', rest)
            if am: ang = float(am.group(1))
            if label not in line_assigns:
                line_assigns[label] = []
            line_assigns[label].append({'story': story, 'section': section, 'angle': ang})

    # Parse area assigns for above-1MF only
    area_assigns = {}
    for line in sections.get('AREA ASSIGNS', []):
        m = re.match(r'\s+AREAASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"', line)
        if m and m.group(1).startswith(above_1mf_prefixes):
            label = m.group(1)
            if label not in area_assigns:
                area_assigns[label] = []
            area_assigns[label].append({'story': m.group(2), 'section': m.group(3)})

    print(f"  Above-1MF lines: {len(new_lines)}")
    print(f"  Above-1MF areas: {len(new_areas)}")
    print(f"  Line assigns: {len(line_assigns)} labels")
    print(f"  Area assigns: {len(area_assigns)} labels")

    # Step 3: Add missing section definitions
    print(f"\n[3] Checking/adding section definitions...")

    needed_sections = set()
    for assigns in line_assigns.values():
        for a in assigns:
            needed_sections.add(a['section'])

    # Get existing sections
    ret = SapModel.PropFrame.GetNameList(0, [])
    existing_secs = set(ret[1]) if ret[0] > 0 else set()

    missing_secs = needed_sections - existing_secs
    if missing_secs:
        print(f"  Missing sections: {sorted(missing_secs)}")

        # Parse frame section definitions from merged e2k
        for sec_name in missing_secs:
            found = False
            for line in sections.get('FRAME SECTIONS', []):
                if f'"{sec_name}"' in line and 'FRAMESECTION' in line:
                    mat_m = re.search(r'MATERIAL\s+"([^"]+)"', line)
                    d_m = re.search(r'\bD\s+([\d.]+)', line)
                    b_m = re.search(r'\bB\s+([\d.]+)', line)
                    if mat_m and d_m and b_m:
                        mat = mat_m.group(1)
                        d = float(d_m.group(1))
                        b = float(b_m.group(1))

                        # Check if material exists
                        ret_mat = SapModel.PropMaterial.GetNameList(0, [])
                        existing_mats = set(ret_mat[1]) if ret_mat[0] > 0 else set()

                        if mat not in existing_mats:
                            # Add material as concrete
                            print(f"    Adding material: {mat}")
                            ret = SapModel.PropMaterial.AddMaterial(mat, 2, "", "", "")
                            # Set basic concrete properties (C420 = 420 kgf/cm2 = 4200 T/m2)
                            fc = 4200  # Default C420
                            if '280' in mat: fc = 2800
                            elif '350' in mat: fc = 3500
                            elif '560' in mat: fc = 5600
                            elif '630' in mat: fc = 6300
                            E = 25000 * (fc/10)**0.5 * 10  # Approximate E
                            SapModel.PropMaterial.SetMPIsotropic(mat, E, 0.2, 9.9e-6)

                        ret = SapModel.PropFrame.SetRectangle(sec_name, mat, d, b)
                        print(f"    Added {sec_name}: D={d}, B={b}, mat={mat}, ret={ret}")
                        found = True
                    break

            if not found:
                # Check concrete sections
                for line in sections.get('CONCRETE SECTIONS', []):
                    if f'"{sec_name}"' in line:
                        print(f"    {sec_name}: Concrete section (needs frame section first)")
                        # The concrete section references a frame section by the same name
                        # which should already exist
                        break

    else:
        print(f"  All sections exist")

    # Also check area sections
    needed_area_secs = set()
    for assigns in area_assigns.values():
        for a in assigns:
            needed_area_secs.add(a['section'])

    ret = SapModel.PropArea.GetNameList(0, [])
    existing_area_secs = set(ret[1]) if ret[0] > 0 else set()
    missing_area_secs = needed_area_secs - existing_area_secs
    if missing_area_secs:
        print(f"  Missing area sections: {sorted(missing_area_secs)}")
    else:
        print(f"  All area sections exist")

    # Step 4: Add above-1MF frame elements
    print(f"\n[4] Adding {len(new_lines)} above-1MF frame elements...")

    added_frames = 0
    frame_errors = 0
    skipped = 0

    for ldata in new_lines:
        label = ldata['label']
        ltype = ldata['type']
        pt1 = ldata['pt1']
        pt2 = ldata['pt2']

        if pt1 not in points or pt2 not in points:
            frame_errors += 1
            continue

        x1, y1 = points[pt1]
        x2, y2 = points[pt2]

        # Get assigns for this element
        if label not in line_assigns:
            skipped += 1
            continue

        assigns = line_assigns[label]

        if ltype == 'COLUMN':
            # Column: use first assign's section, add at each story
            sec = assigns[0]['section']
            for a in assigns:
                story = a['story']
                if story not in story_map:
                    continue
                z_bot = story_map[story]

                # Find story above
                idx = story_names.index(story) if story in story_names else -1
                if idx > 0:
                    z_top = story_elevs[idx - 1]
                else:
                    continue  # Skip if at top

                ret = SapModel.FrameObj.AddByCoord(x1, y1, z_bot, x1, y1, z_top, '', a['section'])
                if isinstance(ret, (list, tuple)) and len(ret) >= 2:
                    added_frames += 1
                else:
                    frame_errors += 1

        elif ltype == 'BEAM':
            # Beam: add at each story
            for a in assigns:
                story = a['story']
                if story not in story_map:
                    continue
                z = story_map[story]

                ret = SapModel.FrameObj.AddByCoord(x1, y1, z, x2, y2, z, '', a['section'])
                if isinstance(ret, (list, tuple)) and len(ret) >= 2:
                    added_frames += 1
                else:
                    frame_errors += 1

        if (added_frames + frame_errors) % 500 == 0:
            print(f"  Progress: {added_frames} added, {frame_errors} errors...")

    print(f"  Done: {added_frames} added, {frame_errors} errors, {skipped} skipped")

    # Step 5: Add above-1MF area elements
    print(f"\n[5] Adding {len(new_areas)} above-1MF area elements...")

    added_areas = 0
    area_errors = 0

    for adata in new_areas:
        label = adata['label']
        atype = adata['type']
        pts = adata['points']

        # Get coordinates
        xs, ys = [], []
        ok = True
        for p in pts:
            if p in points:
                x, y = points[p]
                xs.append(x)
                ys.append(y)
            else:
                ok = False
                break
        if not ok:
            area_errors += 1
            continue

        if label not in area_assigns:
            area_errors += 1
            continue

        for a in area_assigns[label]:
            story = a['story']
            sec = a['section']
            if story not in story_map:
                continue

            z = story_map[story]

            if atype == 'PANEL':
                # Wall: vertical, need z_bot and z_top
                idx = story_names.index(story) if story in story_names else -1
                if idx <= 0:
                    continue
                z_top = story_elevs[idx - 1]

                if len(pts) >= 2:
                    # Wall defined by 2 base points, extruded vertically
                    x_arr = [xs[0], xs[1], xs[1], xs[0]]
                    y_arr = [ys[0], ys[1], ys[1], ys[0]]
                    z_arr = [z, z, z_top, z_top]
                    ret = SapModel.AreaObj.AddByCoord(4, x_arr, y_arr, z_arr, '', sec)
                    if isinstance(ret, (list, tuple)) and len(ret) >= 2:
                        added_areas += 1
                    else:
                        area_errors += 1

            elif atype == 'FLOOR':
                # Slab: horizontal
                num = len(xs)
                z_arr = [z] * num
                ret = SapModel.AreaObj.AddByCoord(num, xs, ys, z_arr, '', sec)
                if isinstance(ret, (list, tuple)) and len(ret) >= 2:
                    added_areas += 1
                else:
                    area_errors += 1

    print(f"  Done: {added_areas} added, {area_errors} errors")

    # Step 6: Update grid lines
    print(f"\n[6] Updating grid lines...")
    # Parse grid lines from merged e2k
    grid_lines = []
    for line in sections.get('GRIDS', []):
        m = re.match(r'\s+GRID\s+"([^"]+)"\s+LABEL\s+"([^"]+)"\s+DIR\s+"([^"]+)"\s+COORD\s+([\d.\-E+]+)', line)
        if m:
            grid_lines.append({
                'system': m.group(1),
                'label': m.group(2),
                'dir': m.group(3),
                'coord': float(m.group(4))
            })

    if grid_lines:
        print(f"  Grid lines to set: {len(grid_lines)}")
        # Use DatabaseTables to update grid lines
        try:
            # Get current grid data
            ret = SapModel.DatabaseTables.GetTableForEditingArray(
                "Grid Lines", [], "", 0, [], 0, [])
            print(f"  GetTableForEditing: type={type(ret)}")
            if isinstance(ret, (list, tuple)):
                print(f"  Fields: {ret[0] if len(ret) > 0 else 'N/A'}")
        except Exception as e:
            print(f"  Grid table error: {e}")
            # Alternative: use GridSys API
            try:
                # Delete existing grids and recreate
                for gl in grid_lines:
                    # SetGrid doesn't exist - we need to use the grid system API
                    pass
            except:
                pass

    # Step 7: Save and report
    print(f"\n[7] Saving and reporting...")
    SapModel.View.RefreshView(0, False)
    ret = SapModel.File.Save(output)
    print(f"  Save: {ret}")

    ret_f = SapModel.FrameObj.GetNameList(0, [])
    ret_a = SapModel.AreaObj.GetNameList(0, [])
    ret_p = SapModel.PointObj.GetNameList(0, [])

    print(f"\n{'='*60}")
    print(f"FINAL MODEL:")
    print(f"  Frames: {ret_f[0]} (was {baseline_frames}, added {ret_f[0]-baseline_frames})")
    print(f"  Areas:  {ret_a[0]} (was {baseline_areas}, added {ret_a[0]-baseline_areas})")
    print(f"  Points: {ret_p[0]} (was {baseline_points}, added {ret_p[0]-baseline_points})")
    print(f"  Saved to: {output}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
