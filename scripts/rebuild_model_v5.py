"""
Rebuild MERGED model from scratch:
1. Open OLD.EDB (basement model)
2. Save as MERGED_v5.EDB
3. Add all above-1MF frames (columns + beams) from merged e2k
4. Add all above-1MF areas (floors) from merged e2k
5. Fix section dimensions
6. Update grids
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

def get_building_prefix(name):
    """Get building letter from element name. AF1 -> A, BF1901 -> B, etc."""
    if len(name) >= 2:
        first = name[0]
        if first in ('A', 'B', 'C', 'D'):
            return first
    return None

def parse_merged_e2k(filepath):
    """Parse the merged e2k file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')

    data = {
        'points': {},       # name -> (x, y) in METERS
        'lines': {},        # name -> (type, pt_i, pt_j, num_stories)
        'areas': {},        # name -> (type, num_pts, [pt_names])
        'lineassigns': [],  # [(name, story, section, rest)]
        'areaassigns': [],  # [(name, story, section, rest)]
    }

    for line in lines:
        m = re.match(r'\s+POINT\s+"([^"]+)"\s+([\d.\-E+]+)\s+([\d.\-E+]+)', line)
        if m:
            data['points'][m.group(1)] = (float(m.group(2)), float(m.group(3)))
            continue

        m = re.match(r'\s+LINE\s+"([^"]+)"\s+(BEAM|COLUMN|BRACE)\s+"([^"]+)"\s+"([^"]+)"\s+(\d+)', line)
        if m:
            data['lines'][m.group(1)] = (m.group(2), m.group(3), m.group(4), int(m.group(5)))
            continue

        m = re.match(r'\s+AREA\s+"([^"]+)"\s+(FLOOR|PANEL|RAMP|WALL)\s+(\d+)\s+(.*)', line)
        if m:
            area_name = m.group(1)
            area_type = m.group(2)
            num_pts = int(m.group(3))
            rest = m.group(4)
            pt_names = re.findall(r'"([^"]+)"', rest)
            data['areas'][area_name] = (area_type, num_pts, pt_names[:num_pts])
            continue

        m = re.match(r'\s+LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"(.*)', line)
        if m:
            data['lineassigns'].append((m.group(1), m.group(2), m.group(3), m.group(4).strip()))
            continue

        m = re.match(r'\s+AREAASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"(.*)', line)
        if m:
            data['areaassigns'].append((m.group(1), m.group(2), m.group(3), m.group(4).strip()))
            continue

    return data

def main():
    SapModel, pid = connect_etabs()
    if not SapModel:
        print("ERROR: Cannot connect to ETABS")
        return
    print(f"Connected to PID {pid}")

    # ===== STEP 1: Open OLD.EDB =====
    print("\n[STEP 1] Opening OLD.EDB...")
    old_path = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\OLD\OLD.EDB'
    ret = SapModel.File.OpenFile(old_path)
    print(f"  Open: ret={ret}")

    SapModel.SetPresentUnits(12)  # TON/M
    SapModel.SetModelIsLocked(False)

    # Check baseline counts
    ret_f = SapModel.FrameObj.GetNameList(0, [])
    ret_a = SapModel.AreaObj.GetNameList(0, [])
    ret_p = SapModel.PointObj.GetNameList(0, [])
    print(f"  Baseline: Frames={ret_f[0]}, Areas={ret_a[0]}, Points={ret_p[0]}")

    # Get story data
    ret = SapModel.Story.GetStories_2(0, 0, [], [], [], [], [], [], [], [])
    story_names = list(ret[2])
    story_elevs = list(ret[3])
    story_heights = list(ret[4])
    story_elev_map = dict(zip(story_names, story_elevs))
    story_height_map = dict(zip(story_names, story_heights))
    print(f"  Stories: {len(story_names)}")

    # ===== STEP 2: Save as MERGED_v5.EDB =====
    output = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v5.EDB'
    ret = SapModel.File.Save(output)
    print(f"\n[STEP 2] Saved as MERGED_v5.EDB: ret={ret}")

    # ===== STEP 3: Parse merged e2k =====
    print("\n[STEP 3] Parsing merged e2k...")
    merged = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_ALL_v2.e2k'
    data = parse_merged_e2k(merged)
    print(f"  Points: {len(data['points'])}")
    print(f"  Lines: {len(data['lines'])}")
    print(f"  Areas: {len(data['areas'])}")
    print(f"  LineAssigns: {len(data['lineassigns'])}")
    print(f"  AreaAssigns: {len(data['areaassigns'])}")

    # Filter above-1MF elements
    above_prefixes = ['AC', 'AB', 'AW', 'AF', 'BC', 'BB', 'BW', 'BF',
                      'CC', 'CB', 'CW', 'CF', 'DC', 'DB', 'DW', 'DF']

    def is_above_1mf(name):
        return any(name.startswith(p) for p in above_prefixes)

    # Group line assigns
    line_assign_map = defaultdict(list)
    for la_name, la_story, la_section, la_rest in data['lineassigns']:
        if is_above_1mf(la_name):
            line_assign_map[la_name].append((la_story, la_section, la_rest))

    # Group area assigns
    area_assign_map = defaultdict(list)
    for aa_name, aa_story, aa_section, aa_rest in data['areaassigns']:
        if is_above_1mf(aa_name):
            area_assign_map[aa_name].append((aa_story, aa_section, aa_rest))

    above_lines = {k: v for k, v in data['lines'].items() if is_above_1mf(k)}
    above_areas = {k: v for k, v in data['areas'].items() if is_above_1mf(k)}

    total_line_assigns = sum(len(v) for v in line_assign_map.values())
    total_area_assigns = sum(len(v) for v in area_assign_map.values())

    print(f"\n  Above-1MF lines: {len(above_lines)}, total assigns: {total_line_assigns}")
    print(f"  Above-1MF areas: {len(above_areas)}, total assigns: {total_area_assigns}")

    # ===== STEP 4: Create missing sections =====
    print("\n[STEP 4] Creating missing sections...")

    # Get existing sections
    ret = SapModel.PropFrame.GetNameList(0, [])
    existing_frame_secs = set(ret[1]) if ret[0] > 0 else set()
    ret = SapModel.PropArea.GetNameList(0, [])
    existing_area_secs = set(ret[1]) if ret[0] > 0 else set()

    # Collect needed sections
    needed_frame_secs = set()
    for la_name, assigns in line_assign_map.items():
        for story, section, rest in assigns:
            needed_frame_secs.add(section)

    needed_area_secs = set()
    for aa_name, assigns in area_assign_map.items():
        for story, section, rest in assigns:
            needed_area_secs.add(section)

    missing_frame_secs = needed_frame_secs - existing_frame_secs
    missing_area_secs = needed_area_secs - existing_area_secs

    print(f"  Missing frame sections: {sorted(missing_frame_secs)}")
    print(f"  Missing area sections: {sorted(missing_area_secs)}")

    # Create missing frame sections
    for sec in sorted(missing_frame_secs):
        mat = 'C420'
        d = 0.5
        b = 0.5

        # Parse name for dimensions CnnnXnnn
        m = re.match(r'C(\d+)X(\d+)', sec)
        if m:
            d = float(m.group(1)) / 100  # cm to m
            b = float(m.group(2)) / 100
            if 'SD490' in sec:
                mat = 'C420SD490' if 'C420' in sec else ('C280SD490' if 'C280' in sec else 'C420SD490')
                if 'C56' in sec: mat = 'C560SD490'
                if 'C49' in sec: mat = 'C420SD490'
                if 'C42' in sec: mat = 'C420SD490'
                if 'C28' in sec: mat = 'C280SD490'
            elif 'C42' in sec: mat = 'C420'
            elif 'C28' in sec: mat = 'C280'
            elif 'C56' in sec: mat = 'C560SD490'
            ret = SapModel.PropFrame.SetRectangle(sec, mat, d, b)
            print(f"  Created column {sec}: D={d}, B={b}, mat={mat}")
            continue

        # SRC sections
        m = re.match(r'SRC(\d+)X(\d+)', sec)
        if m:
            d = float(m.group(1)) / 100
            b = float(m.group(2)) / 100
            mat = 'C420'
            if 'SD490' in sec: mat = 'C420SD490'
            ret = SapModel.PropFrame.SetRectangle(sec, mat, d, b)
            print(f"  Created SRC {sec}: D={d}, B={b}")
            continue

        # SRB sections
        m = re.match(r'SRB(\d+)X(\d+)', sec)
        if m:
            d = float(m.group(1)) / 100
            b = float(m.group(2)) / 100
            mat = 'C420'
            if 'SD490' in sec: mat = 'C420SD490'
            ret = SapModel.PropFrame.SetRectangle(sec, mat, d, b)
            print(f"  Created SRB {sec}: D={d}, B={b}")
            continue

        # Beam sections BnnnXnnn
        m = re.match(r'B(\d+)X(\d+)', sec)
        if m:
            d = float(m.group(1)) / 100
            b = float(m.group(2)) / 100
            mat = 'C280'
            if 'SD490' in sec: mat = 'C280SD490'
            ret = SapModel.PropFrame.SetRectangle(sec, mat, d, b)
            print(f"  Created beam {sec}: D={d}, B={b}")
            continue

        # WB sections
        m = re.match(r'WB(\d+)X(\d+)', sec)
        if m:
            d = float(m.group(1)) / 100
            b = float(m.group(2)) / 100
            mat = 'C280SD490'
            ret = SapModel.PropFrame.SetRectangle(sec, mat, d, b)
            print(f"  Created WB {sec}: D={d}, B={b}")
            continue

        # FB/FSB/FWB sections
        m = re.match(r'(?:FB|FSB|FWB)(\d+)X(\d+)', sec)
        if m:
            d = float(m.group(1)) / 100
            b = float(m.group(2)) / 100
            mat = 'C420SD490'
            ret = SapModel.PropFrame.SetRectangle(sec, mat, d, b)
            print(f"  Created {sec}: D={d}, B={b}")
            continue

        # SB sections (simple beam)
        m = re.match(r'SB(\d+)$', sec)
        if m:
            d_cm = float(m.group(1))
            d = d_cm / 100
            b = d * 0.5  # assume width = 0.5 * depth
            mat = 'C280'
            ret = SapModel.PropFrame.SetRectangle(sec, mat, d, b)
            print(f"  Created {sec}: D={d}, B={b}")
            continue

        # SBnnnXnnn
        m = re.match(r'SB(\d+)X(\d+)', sec)
        if m:
            d = float(m.group(1)) / 100
            b = float(m.group(2)) / 100
            mat = 'C280'
            ret = SapModel.PropFrame.SetRectangle(sec, mat, d, b)
            print(f"  Created {sec}: D={d}, B={b}")
            continue

        # Auto select beams and columns (AB, ABH, ASB, ACx, AUTOSC)
        auto_dims = {
            'AB70': (0.70, 0.40), 'AB75': (0.75, 0.40), 'AB80': (0.80, 0.40), 'AB85': (0.85, 0.40),
            'ABH70': (0.70, 0.50), 'ABH75': (0.75, 0.50), 'ABH80': (0.80, 0.50), 'ABH85': (0.85, 0.50),
            'ASB': (0.55, 0.30),
            'ACA2': (0.70, 0.35), 'ACA3': (0.70, 0.35),
            'ACB3': (0.60, 0.30), 'ACB4': (0.60, 0.30),
            'ACBC2': (0.55, 0.30), 'ACBC3': (0.55, 0.30),
            'ACD2': (0.60, 0.30), 'ACD3': (0.60, 0.30),
            'ACN1': (0.55, 0.30),
            'AUTOSC800SM': (0.80, 0.80),
            'AUTOSCBEAM900SM': (0.90, 0.50),
        }
        if sec in auto_dims:
            d, b = auto_dims[sec]
            mat = 'C280SD490' if 'SC' not in sec else 'C420SD490'
            if 'SC800' in sec or 'SC' in sec[:4]:
                mat = 'C420SD490'
            ret = SapModel.PropFrame.SetRectangle(sec, mat, d, b)
            print(f"  Created auto {sec}: D={d}, B={b}")
            continue

        # BH sections (beam height variations)
        m = re.match(r'BH(\d+)', sec)
        if m:
            d_cm = float(m.group(1)[:2]) if len(m.group(1)) >= 2 else float(m.group(1))
            d = d_cm / 100
            b = d * 0.5
            mat = 'C280SD490'
            ret = SapModel.PropFrame.SetRectangle(sec, mat, d, b)
            print(f"  Created BH {sec}: D={d}, B={b}")
            continue

        # MSC-BH sections (steel I-beam)
        m = re.match(r'MSC-BH(\d+)x(\d+)x(\d+)x(\d+)', sec)
        if m:
            h = float(m.group(1)) / 1000   # mm to m
            bf = float(m.group(2)) / 1000
            tw = float(m.group(3)) / 1000
            tf = float(m.group(4)) / 1000
            mat = 'SN490'
            try:
                ret = SapModel.PropFrame.SetISection(sec, mat, h, bf, tf, tw, bf, tf)
                print(f"  Created I-section {sec}: H={h}, BF={bf}, TF={tf}, TW={tw}")
            except:
                ret = SapModel.PropFrame.SetRectangle(sec, mat, h, bf)
                print(f"  Created rect fallback {sec}: D={h}, B={bf}")
            continue

        # SB70 I-section
        if sec == 'SB70':
            ret = SapModel.PropFrame.SetISection('SB70', 'SN490', 0.7, 0.3, 0.024, 0.013, 0.3, 0.024)
            print(f"  Created SB70 I-section")
            continue

        # Fallback
        print(f"  WARNING: Unknown section {sec}, creating 50x50 rect")
        ret = SapModel.PropFrame.SetRectangle(sec, 'C280', 0.5, 0.5)

    # Create missing area sections
    for sec in sorted(missing_area_secs):
        thick = 0.2
        mat = 'C420'
        m = re.match(r'(?:DS|S|FS)(\d+)', sec)
        if m:
            thick = float(m.group(1)) / 100
        m = re.match(r'(?:DW|W)(\d+)', sec)
        if m:
            thick = float(m.group(1)) / 100
            ret = SapModel.PropArea.SetWall(sec, 0, 1, mat, thick)
            print(f"  Created wall section {sec}: thick={thick}")
            continue
        ret = SapModel.PropArea.SetSlab(sec, 0, 1, mat, thick)
        print(f"  Created slab section {sec}: thick={thick}")

    # ===== STEP 5: Add frames =====
    print("\n[STEP 5] Adding above-1MF frames...")

    frame_added = 0
    frame_errors = 0
    frame_error_types = defaultdict(int)

    for line_name, (line_type, pt_i, pt_j, num_stories) in sorted(above_lines.items()):
        assigns = line_assign_map.get(line_name, [])
        if not assigns:
            frame_error_types['no_assign'] += 1
            continue

        for story, section, rest in assigns:
            if story not in story_elev_map:
                frame_error_types['bad_story'] += 1
                continue

            elev_top = story_elev_map[story]
            story_h = story_height_map.get(story, 3.4)
            elev_bot = elev_top - story_h

            if line_type == 'COLUMN':
                # Column: vertical, both points same X,Y
                if pt_i not in data['points']:
                    frame_error_types['missing_point'] += 1
                    continue
                px, py = data['points'][pt_i]
                xi, yi, zi = px, py, elev_bot
                xj, yj, zj = px, py, elev_top
            elif line_type in ('BEAM', 'BRACE'):
                # Beam/brace: horizontal, different points
                if pt_i not in data['points'] or pt_j not in data['points']:
                    frame_error_types['missing_point'] += 1
                    continue
                pxi, pyi = data['points'][pt_i]
                pxj, pyj = data['points'][pt_j]
                if line_type == 'BEAM':
                    zi = zj = elev_top
                else:  # BRACE
                    zi = elev_bot
                    zj = elev_top
                xi, yi = pxi, pyi
                xj, yj = pxj, pyj
            else:
                frame_error_types['unknown_type'] += 1
                continue

            try:
                name = ''
                ret = SapModel.FrameObj.AddByCoord(xi, yi, zi, xj, yj, zj, name, section)
                frame_added += 1
            except Exception as e:
                frame_error_types['api_error'] += 1

        if (frame_added + sum(frame_error_types.values())) % 500 == 0 and frame_added > 0:
            print(f"  Progress: {frame_added} added, errors={dict(frame_error_types)}")

    print(f"  Frames: {frame_added} added, errors={dict(frame_error_types)}")

    # ===== STEP 6: Add areas =====
    print("\n[STEP 6] Adding above-1MF areas...")

    area_added = 0
    area_errors = 0
    area_error_types = defaultdict(int)

    for area_name, (area_type, num_pts, pt_names) in sorted(above_areas.items()):
        assigns = area_assign_map.get(area_name, [])
        if not assigns:
            area_error_types['no_assign'] += 1
            continue

        # Get building prefix for point lookup
        bldg = get_building_prefix(area_name)
        if not bldg:
            area_error_types['no_building'] += 1
            continue

        for story, section, rest in assigns:
            if story not in story_elev_map:
                area_error_types['bad_story'] += 1
                continue

            elev = story_elev_map[story]
            story_h = story_height_map.get(story, 3.4)

            X = []
            Y = []
            Z = []
            all_ok = True

            for pt in pt_names:
                # Try prefixed point name first (e.g., "A7531")
                prefixed = bldg + pt
                if prefixed in data['points']:
                    px, py = data['points'][prefixed]
                elif pt in data['points']:
                    px, py = data['points'][pt]
                else:
                    all_ok = False
                    area_error_types['missing_point'] += 1
                    break

                X.append(px)
                Y.append(py)
                Z.append(elev)

            if not all_ok or len(X) < 3:
                continue

            # For PANEL (wall), two points at top, two at bottom
            if area_type == 'PANEL' and num_pts == 4:
                bot_elev = elev - story_h
                Z = [elev, elev, bot_elev, bot_elev]

            try:
                name = ''
                ret = SapModel.AreaObj.AddByCoord(num_pts, X, Y, Z, name, section)
                area_added += 1
            except Exception as e:
                area_error_types['api_error'] += 1

        if (area_added + sum(area_error_types.values())) % 200 == 0 and area_added > 0:
            print(f"  Progress: {area_added} added, errors={dict(area_error_types)}")

    print(f"  Areas: {area_added} added, errors={dict(area_error_types)}")

    # ===== STEP 7: Fix section dimensions =====
    print("\n[STEP 7] Fixing section dimensions...")

    # Fix column sections that might have wrong dimensions
    dim_fixes = {
        'C130X130C42': ('C420', 1.3, 1.3),
        'C150X150C42': ('C420', 1.5, 1.5),
        'C100X100C42': ('C420', 1.0, 1.0),
        'C130X130C420': ('C420', 1.3, 1.3),
        'C150X150C420': ('C420', 1.5, 1.5),
        'C100X100C420': ('C420', 1.0, 1.0),
        'C130X130C420SD490': ('C420SD490', 1.3, 1.3),
        'C150X150C420SD490': ('C420SD490', 1.5, 1.5),
        'C100X100C420SD490': ('C420SD490', 1.0, 1.0),
    }
    for sec_name, (mat, d, b) in dim_fixes.items():
        try:
            ret = SapModel.PropFrame.SetRectangle(sec_name, mat, d, b)
            if ret == 0:
                print(f"  Fixed {sec_name}: D={d}, B={b}")
        except:
            pass

    # ===== STEP 8: Update grids =====
    print("\n[STEP 8] Updating grids via DatabaseTables...")

    # Parse grids from merged e2k
    x_grids = []
    y_grids = []
    with open(merged, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'\s+GRID\s+"([^"]+)"\s+LABEL\s+"([^"]+)"\s+DIR\s+"([^"]+)"\s+COORD\s+([\d.\-E+]+)', line)
            if m:
                label = m.group(2)
                direction = m.group(3)
                coord = float(m.group(4))
                if direction == 'X':
                    x_grids.append((label, coord))
                elif direction == 'Y':
                    y_grids.append((label, coord))

    print(f"  E2K grids: {len(x_grids)} X, {len(y_grids)} Y")

    # Build grid table data
    fields = ('Name', 'LineType', 'ID', 'Ordinate', 'BubbleLoc', 'Visible')
    grid_data = []
    for label, coord in x_grids:
        grid_data.extend(['G1', 'X (Cartesian)', label, str(coord), 'End', 'Yes'])
    for label, coord in y_grids:
        grid_data.extend(['G1', 'Y (Cartesian)', label, str(coord), 'Start', 'Yes'])

    num_records = len(x_grids) + len(y_grids)
    try:
        ret = SapModel.DatabaseTables.SetTableForEditingArray(
            "Grid Definitions - Grid Lines", 0, fields, num_records, tuple(grid_data))
        print(f"  SetTable: {ret[0] if isinstance(ret, (list,tuple)) else ret}")
        ret = SapModel.DatabaseTables.ApplyEditedTables(True, 0, 0, 0, 0, "")
        if isinstance(ret, (list, tuple)):
            fatal = ret[0]
            errs = ret[1]
            warns = ret[2]
            print(f"  Apply: fatal={fatal}, errors={errs}, warnings={warns}")
        else:
            print(f"  Apply: {ret}")
    except Exception as e:
        print(f"  Grid update error: {e}")

    # ===== FINAL =====
    print("\n" + "=" * 60)
    print("FINAL STATE")
    print("=" * 60)

    ret_f = SapModel.FrameObj.GetNameList(0, [])
    ret_a = SapModel.AreaObj.GetNameList(0, [])
    ret_p = SapModel.PointObj.GetNameList(0, [])
    print(f"Frames: {ret_f[0]}")
    print(f"Areas: {ret_a[0]}")
    print(f"Points: {ret_p[0]}")

    # Sample verification
    print("\nSample frames (last 3):")
    all_frames = list(ret_f[1]) if ret_f[0] > 0 else []
    for f in all_frames[-3:]:
        try:
            ret = SapModel.FrameObj.GetPoints(f, '', '')
            pt_i, pt_j = ret[0], ret[1]
            ri = SapModel.PointObj.GetCoordCartesian(pt_i, 0, 0, 0)
            rj = SapModel.PointObj.GetCoordCartesian(pt_j, 0, 0, 0)
            rs = SapModel.FrameObj.GetSection(f, '', '')
            print(f"  {f}: ({ri[0]:.2f},{ri[1]:.2f},{ri[2]:.2f})->({rj[0]:.2f},{rj[1]:.2f},{rj[2]:.2f}) sec={rs[0]}")
        except:
            pass

    print("\nSample areas (last 3):")
    all_areas = list(ret_a[1]) if ret_a[0] > 0 else []
    for a in all_areas[-3:]:
        try:
            ret = SapModel.AreaObj.GetPoints(a, 0, [])
            pts = list(ret[1])
            rs = SapModel.AreaObj.GetProperty(a, '')
            coords = []
            for pt in pts:
                r = SapModel.PointObj.GetCoordCartesian(pt, 0, 0, 0)
                coords.append(f"({r[0]:.2f},{r[1]:.2f},{r[2]:.2f})")
            print(f"  {a}: sec={rs[0]}, {' '.join(coords)}")
        except:
            pass

    # Save
    SapModel.View.RefreshView(0, False)
    SapModel.File.Save(output)
    print(f"\nSaved to: {output}")

if __name__ == '__main__':
    main()
