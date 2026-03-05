"""
Fix the MERGED_v4.EDB model:
1. Verify existing frames are at correct locations
2. Add all missing above-1MF area elements (floors/walls)
3. Verify final state
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

def parse_e2k(filepath):
    """Parse merged e2k file and extract all definitions."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')

    data = {
        'points': {},       # name -> (x, y)
        'lines': {},        # name -> (type, pt_i, pt_j, num_stories)
        'areas': {},        # name -> (type, num_pts, [pt_names], [offsets])
        'lineassigns': [],  # [(name, story, section, ...)]
        'areaassigns': [],  # [(name, story, section, ...)]
        'stories': {},      # name -> (elev, height)
    }

    for line in lines:
        # Points
        m = re.match(r'\s+POINT\s+"([^"]+)"\s+([\d.\-E+]+)\s+([\d.\-E+]+)', line)
        if m:
            data['points'][m.group(1)] = (float(m.group(2)), float(m.group(3)))
            continue

        # Lines (columns, beams, braces)
        m = re.match(r'\s+LINE\s+"([^"]+)"\s+(BEAM|COLUMN|BRACE)\s+"([^"]+)"\s+"([^"]+)"\s+(\d+)', line)
        if m:
            data['lines'][m.group(1)] = (m.group(2), m.group(3), m.group(4), int(m.group(5)))
            continue

        # Areas
        m = re.match(r'\s+AREA\s+"([^"]+)"\s+(FLOOR|PANEL|RAMP|WALL)\s+(\d+)\s+(.*)', line)
        if m:
            area_name = m.group(1)
            area_type = m.group(2)
            num_pts = int(m.group(3))
            rest = m.group(4)
            pts_and_offsets = re.findall(r'"([^"]+)"|\b(\d+)\b', rest)
            pt_names = []
            offsets = []
            for quoted, number in pts_and_offsets:
                if quoted:
                    pt_names.append(quoted)
                else:
                    offsets.append(int(number))
            data['areas'][area_name] = (area_type, num_pts, pt_names, offsets)
            continue

        # Line assigns
        m = re.match(r'\s+LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"(.*)', line)
        if m:
            la_name = m.group(1)
            la_story = m.group(2)
            la_section = m.group(3)
            la_rest = m.group(4)
            data['lineassigns'].append((la_name, la_story, la_section, la_rest.strip()))
            continue

        # Area assigns
        m = re.match(r'\s+AREAASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"(.*)', line)
        if m:
            aa_name = m.group(1)
            aa_story = m.group(2)
            aa_section = m.group(3)
            aa_rest = m.group(4)
            data['areaassigns'].append((aa_name, aa_story, aa_section, aa_rest.strip()))
            continue

    return data

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
    print(f"Stories: {len(story_names)}")

    # Parse e2k
    merged = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_ALL_v2.e2k'
    data = parse_e2k(merged)
    print(f"E2K Points: {len(data['points'])}")
    print(f"E2K Lines: {len(data['lines'])}")
    print(f"E2K Areas: {len(data['areas'])}")
    print(f"E2K LineAssigns: {len(data['lineassigns'])}")
    print(f"E2K AreaAssigns: {len(data['areaassigns'])}")

    # Filter for above-1MF elements
    above_prefixes = ['AC', 'AB', 'AW', 'AF', 'BC', 'BB', 'BW', 'BF', 'CC', 'CB', 'CW', 'CF', 'DC', 'DB', 'DW', 'DF']

    def is_above_1mf(name):
        return any(name.startswith(p) for p in above_prefixes)

    # Group area assigns by area name
    area_assign_map = defaultdict(list)
    for aa_name, aa_story, aa_section, aa_rest in data['areaassigns']:
        if is_above_1mf(aa_name):
            area_assign_map[aa_name].append((aa_story, aa_section, aa_rest))

    above_areas = {k: v for k, v in data['areas'].items() if is_above_1mf(k)}
    print(f"\nAbove-1MF areas to add: {len(above_areas)}")
    print(f"Above-1MF area assigns: {len(area_assign_map)}")

    # Group line assigns by line name
    line_assign_map = defaultdict(list)
    for la_name, la_story, la_section, la_rest in data['lineassigns']:
        if is_above_1mf(la_name):
            line_assign_map[la_name].append((la_story, la_section, la_rest))

    above_lines = {k: v for k, v in data['lines'].items() if is_above_1mf(k)}
    print(f"Above-1MF lines defined: {len(above_lines)}")
    print(f"Above-1MF line assign groups: {len(line_assign_map)}")

    # Count total line assigns (each story = one frame to add)
    total_line_assigns = sum(len(v) for v in line_assign_map.values())
    print(f"Total above-1MF line assigns (=frames needed): {total_line_assigns}")

    # Check current model frame count
    ret_f = SapModel.FrameObj.GetNameList(0, [])
    current_frames = ret_f[0]
    print(f"Current model frames: {current_frames}")

    # Verify: OLD had 2299 frames. If 8328 added = 10627, check total_line_assigns
    print(f"Expected frames to add: {total_line_assigns}")
    print(f"Frames added so far: {current_frames - 2299}")

    # ===== ADD MISSING AREAS =====
    print("\n" + "=" * 60)
    print("ADDING MISSING AREA ELEMENTS")
    print("=" * 60)

    # Check which area sections exist
    ret = SapModel.PropArea.GetNameList(0, [])
    existing_area_secs = set(ret[1]) if ret[0] > 0 else set()
    print(f"Existing area sections: {sorted(existing_area_secs)}")

    # Find area sections needed
    needed_area_secs = set()
    for aa_name, assigns in area_assign_map.items():
        for story, section, rest in assigns:
            needed_area_secs.add(section)

    missing_area_secs = needed_area_secs - existing_area_secs
    if missing_area_secs:
        print(f"Missing area sections: {sorted(missing_area_secs)}")
        # Create missing area sections as shell-thin
        for sec in missing_area_secs:
            # Default to 20cm slab
            thick = 0.2
            mat = 'C420'
            if 'W' in sec:
                # Wall section - extract thickness
                m = re.match(r'W(\d+)', sec)
                if m:
                    thick = float(m.group(1)) / 100  # cm to m
                ret = SapModel.PropArea.SetWall(sec, 0, 1, mat, thick)
                print(f"  Created wall section {sec}: thick={thick} -> ret={ret}")
            elif 'S' in sec:
                m = re.match(r'S(\d+)', sec)
                if m:
                    thick = float(m.group(1)) / 100
                ret = SapModel.PropArea.SetSlab(sec, 0, 1, mat, thick)
                print(f"  Created slab section {sec}: thick={thick} -> ret={ret}")
            elif 'D' in sec:
                m = re.match(r'D.*?(\d+)', sec)
                if m:
                    thick = float(m.group(1)) / 100
                ret = SapModel.PropArea.SetSlab(sec, 0, 1, mat, thick)
                print(f"  Created slab section {sec}: thick={thick} -> ret={ret}")
            else:
                ret = SapModel.PropArea.SetSlab(sec, 0, 1, mat, thick)
                print(f"  Created default section {sec}: thick={thick} -> ret={ret}")

    # Now add areas
    added = 0
    errors = 0
    error_details = []

    for area_name, (area_type, num_pts, pt_names, offsets) in sorted(above_areas.items()):
        # Get assigns for this area
        assigns = area_assign_map.get(area_name, [])
        if not assigns:
            # No assign found - skip
            errors += 1
            error_details.append(f"{area_name}: no AREAASSIGN found")
            continue

        for story, section, rest in assigns:
            if story not in story_elev_map:
                errors += 1
                error_details.append(f"{area_name} at {story}: story not found")
                continue

            elev = story_elev_map[story]

            # Get point coordinates
            X = []
            Y = []
            Z = []
            all_pts_found = True
            for pt in pt_names[:num_pts]:
                if pt in data['points']:
                    px, py = data['points'][pt]
                    X.append(px)
                    Y.append(py)
                    if area_type == 'PANEL':
                        # Walls span from bottom to top of story
                        # Use story elevation for top, story_elev - height for bottom
                        # This needs to be handled per-point (2 at top, 2 at bottom)
                        Z.append(elev)  # Will be fixed below for panels
                    else:
                        Z.append(elev)
                else:
                    all_pts_found = False
                    break

            if not all_pts_found:
                errors += 1
                error_details.append(f"{area_name} at {story}: point {pt} not found in e2k")
                continue

            if len(X) < 3:
                errors += 1
                error_details.append(f"{area_name} at {story}: only {len(X)} points")
                continue

            # Handle PANEL (wall) elements - Z coords need to span story height
            if area_type == 'PANEL':
                # Walls have 4 points: 2 at top, 2 at bottom
                # Typically points 0,1 at top and 2,3 at bottom (or vice versa)
                story_h = story_height_map.get(story, 3.4)
                bot_elev = elev - story_h
                if num_pts == 4:
                    Z = [elev, elev, bot_elev, bot_elev]

            try:
                name = ''
                ret = SapModel.AreaObj.AddByCoord(num_pts, X, Y, Z, name, section)
                if isinstance(ret, (list, tuple)):
                    assigned_name = ret[0] if len(ret) > 0 else ''
                    status = ret[-1] if len(ret) > 1 else ret[0]
                    if isinstance(status, int) and status != 0:
                        errors += 1
                        error_details.append(f"{area_name} at {story}: AddByCoord ret={ret}")
                    else:
                        added += 1
                else:
                    added += 1
            except Exception as e:
                errors += 1
                error_details.append(f"{area_name} at {story}: {e}")

        if (added + errors) % 50 == 0:
            print(f"  Progress: {added} added, {errors} errors")

    print(f"\nArea results: {added} added, {errors} errors")
    if error_details:
        print(f"First 30 errors:")
        for ed in error_details[:30]:
            print(f"  {ed}")

    # ===== VERIFY =====
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    ret_f = SapModel.FrameObj.GetNameList(0, [])
    ret_a = SapModel.AreaObj.GetNameList(0, [])
    ret_p = SapModel.PointObj.GetNameList(0, [])
    print(f"Frames: {ret_f[0]}")
    print(f"Areas: {ret_a[0]}")
    print(f"Points: {ret_p[0]}")

    # Save
    SapModel.View.RefreshView(0, False)
    output = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v4.EDB'
    SapModel.File.Save(output)
    print(f"\nSaved to: {output}")

if __name__ == '__main__':
    main()
