"""
Build the merged ALL model in ETABS v22 using the API directly.
Instead of importing e2k (which doesn't work via API in v22),
we open the template EDB and add elements programmatically.

Strategy:
1. Open 2026-0305.EDB (has all definitions: materials, sections, load cases, combos)
2. Open OLD.EDB to read basement data (stories, grids, elements)
3. Parse merged e2k for above-1MF building data
4. Build everything via API
"""
import comtypes.client
from comtypes.gen import ETABSv1
import subprocess
import time
import re
import os
import json
import sys

def connect_etabs():
    """Connect to a running ETABS instance."""
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

def parse_e2k_sections(filepath):
    """Parse e2k file into sections."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    lines = content.split('\n')
    sections = {}
    current_section = None
    current_lines = []

    for line in lines:
        if line.startswith('$ '):
            if current_section:
                sections[current_section] = current_lines
            current_section = line[2:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_section:
        sections[current_section] = current_lines

    return sections

def parse_points(section_lines):
    """Parse POINT COORDINATES section."""
    points = {}
    for line in section_lines:
        m = re.match(r'\s+POINT\s+"([^"]+)"\s+([\d.\-E+]+)\s+([\d.\-E+]+)', line)
        if m:
            points[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return points

def parse_line_connectivities(section_lines):
    """Parse LINE CONNECTIVITIES section."""
    lines_data = []
    for line in section_lines:
        m = re.match(r'\s+LINE\s+"([^"]+)"\s+(BEAM|COLUMN|BRACE)\s+"([^"]+)"\s+"([^"]+)"\s+(\d+)', line)
        if m:
            lines_data.append({
                'label': m.group(1),
                'type': m.group(2),
                'pt1': m.group(3),
                'pt2': m.group(4),
                'num_stories': int(m.group(5))
            })
    return lines_data

def parse_area_connectivities(section_lines):
    """Parse AREA CONNECTIVITIES section."""
    areas = []
    for line in section_lines:
        m = re.match(r'\s+AREA\s+"([^"]+)"\s+(PANEL|FLOOR)\s+(\d+)\s+"([^"]+)"(.*)', line)
        if m:
            label = m.group(1)
            atype = m.group(2)
            num_pts = int(m.group(3))
            first_pt = m.group(4)
            rest = m.group(5)

            # Extract remaining points and trailing numbers
            all_quoted = re.findall(r'"([^"]+)"', rest)
            pts = [first_pt] + all_quoted[:num_pts-1]

            areas.append({
                'label': label,
                'type': atype,
                'num_pts': num_pts,
                'points': pts
            })
    return areas

def parse_line_assigns(section_lines):
    """Parse LINE ASSIGNS section."""
    assigns = {}
    for line in section_lines:
        m = re.match(r'\s+LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"(.*)$', line)
        if m:
            label = m.group(1)
            story = m.group(2)
            section = m.group(3)
            rest = m.group(4)

            ang = 0
            ang_m = re.search(r'ANG\s+([\d.\-E+]+)', rest)
            if ang_m:
                ang = float(ang_m.group(1))

            if label not in assigns:
                assigns[label] = []
            assigns[label].append({
                'story': story,
                'section': section,
                'angle': ang,
                'raw': line.strip()
            })
    return assigns

def parse_area_assigns(section_lines):
    """Parse AREA ASSIGNS section."""
    assigns = {}
    for line in section_lines:
        m = re.match(r'\s+AREAASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"(.*)$', line)
        if m:
            label = m.group(1)
            story = m.group(2)
            section = m.group(3)

            if label not in assigns:
                assigns[label] = []
            assigns[label].append({
                'story': story,
                'section': section,
                'raw': line.strip()
            })
    return assigns

def parse_point_assigns(section_lines):
    """Parse POINT ASSIGNS section for diaphragm info."""
    assigns = {}
    for line in section_lines:
        m = re.match(r'\s+POINTASSIGN\s+"([^"]+)"\s+"([^"]+)"(.*)$', line)
        if m:
            label = m.group(1)
            story = m.group(2)
            rest = m.group(3)

            diaph = None
            dm = re.search(r'DIAPH\s+"([^"]+)"', rest)
            if dm:
                diaph = dm.group(1)

            if label not in assigns:
                assigns[label] = []
            assigns[label].append({
                'story': story,
                'diaph': diaph
            })
    return assigns

def get_story_elevation(SapModel, story_name):
    """Get the elevation of a specific story."""
    ret = SapModel.Story.GetStories_2(0, 0, [], [], [], [], [], [], [], [])
    if ret[0] is not None:
        names = ret[2]
        elevs = ret[3]
        for n, e in zip(names, elevs):
            if n == story_name:
                return e
    return None


def main():
    print("=" * 60)
    print("BUILD MERGED MODEL IN ETABS v22 VIA API")
    print("=" * 60)

    # Step 1: Connect to ETABS
    print("\n[1] Connecting to ETABS...")
    SapModel, pid = connect_etabs()
    if SapModel is None:
        print("ERROR: Could not connect to ETABS")
        return
    print(f"  Connected to PID {pid}")

    # Step 2: Open OLD.EDB as the base (it has the basement structure)
    old_edb = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\OLD\OLD.EDB'
    print(f"\n[2] Opening OLD.EDB as base model...")
    ret = SapModel.File.OpenFile(old_edb)
    print(f"  OpenFile: {ret}")
    time.sleep(2)

    # Verify OLD model loaded correctly
    ret = SapModel.Story.GetStories_2(0, 0, [], [], [], [], [], [], [], [])
    num_stories = ret[1]
    print(f"  Stories: {num_stories}")

    ret_f = SapModel.FrameObj.GetNameList(0, [])
    num_frames = ret_f[0]
    print(f"  Frames: {num_frames}")

    ret_a = SapModel.AreaObj.GetNameList(0, [])
    num_areas = ret_a[0]
    print(f"  Areas: {num_areas}")

    ret_p = SapModel.PointObj.GetNameList(0, [])
    num_points = ret_p[0]
    print(f"  Points: {num_points}")

    if num_frames == 0:
        print("ERROR: OLD model has no frames!")
        return

    # Step 3: Save as new file (we'll modify this copy)
    output_path = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v3.EDB'
    print(f"\n[3] Saving copy as: {output_path}")
    ret = SapModel.File.Save(output_path)
    print(f"  Save: {ret}")

    # Step 4: Unlock model for editing
    print(f"\n[4] Unlocking model...")
    ret = SapModel.SetModelIsLocked(False)
    print(f"  Unlock: {ret}")

    # Step 5: Parse the merged e2k for above-1MF data
    merged_e2k = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_ALL_v2.e2k'
    print(f"\n[5] Parsing merged e2k: {merged_e2k}")

    sections = parse_e2k_sections(merged_e2k)
    print(f"  Sections found: {list(sections.keys())}")

    # Parse data
    all_points = parse_points(sections.get('POINT COORDINATES', []))
    all_line_conns = parse_line_connectivities(sections.get('LINE CONNECTIVITIES', []))
    all_area_conns = parse_area_connectivities(sections.get('AREA CONNECTIVITIES', []))
    all_line_assigns = parse_line_assigns(sections.get('LINE ASSIGNS', []))
    all_area_assigns = parse_area_assigns(sections.get('AREA ASSIGNS', []))
    all_point_assigns = parse_point_assigns(sections.get('POINT ASSIGNS', []))

    print(f"  Points: {len(all_points)}")
    print(f"  Line conns: {len(all_line_conns)}")
    print(f"  Area conns: {len(all_area_conns)}")
    print(f"  Line assigns: {len(all_line_assigns)} labels")
    print(f"  Area assigns: {len(all_area_assigns)} labels")

    # Identify which elements are from A/B/C/D (above-1MF, prefixed)
    # OLD basement elements: labels like C24, B952, W1, F1792
    # A/B/C/D above-1MF: labels like AC1, AB1, BC1, BB1, CC1, CB1, DC1, DB1

    above_1mf_lines = [l for l in all_line_conns if l['label'].startswith(('A', 'B', 'C', 'D')) and
                        len(l['label']) > 1 and l['label'][1] in 'CBWF']
    above_1mf_areas = [a for a in all_area_conns if a['label'].startswith(('A', 'B', 'C', 'D')) and
                        len(a['label']) > 1 and a['label'][1] in 'FWSD']

    # Actually, let me identify based on the prefixes used in the merge script
    # A/B/C/D prefixed elements have labels starting with A/B/C/D followed by original label
    # OLD basement: original labels (C24, B952, W1, F1792, etc.)

    # Get existing frame labels from OLD model
    existing_frames = set()
    if ret_f[0] > 0:
        existing_frames = set(ret_f[1])

    existing_areas = set()
    if ret_a[0] > 0:
        existing_areas = set(ret_a[1])

    existing_points = set()
    if ret_p[0] > 0:
        existing_points = set(ret_p[1])

    print(f"\n  Existing in OLD: {len(existing_frames)} frames, {len(existing_areas)} areas, {len(existing_points)} points")

    # New elements to add = those in merged but not in OLD
    new_lines = [l for l in all_line_conns if l['label'] not in existing_frames]
    new_areas = [a for a in all_area_conns if a['label'] not in existing_areas]

    # Points needed for new elements
    needed_points = set()
    for l in new_lines:
        needed_points.add(l['pt1'])
        needed_points.add(l['pt2'])
    for a in new_areas:
        for p in a['points']:
            needed_points.add(p)

    new_points = {p: all_points[p] for p in needed_points if p not in existing_points and p in all_points}

    print(f"\n  New elements to add:")
    print(f"    Points: {len(new_points)}")
    print(f"    Lines: {len(new_lines)}")
    print(f"    Areas: {len(new_areas)}")

    if len(new_lines) == 0 and len(new_areas) == 0:
        print("\n  No new elements to add (all from OLD). Checking assigns...")

    # Step 6: Get story elevations from the model
    print(f"\n[6] Getting story data...")
    ret = SapModel.Story.GetStories_2(0, 0, [], [], [], [], [], [], [], [])
    story_names = list(ret[2])
    story_elevs = list(ret[3])
    story_map = dict(zip(story_names, story_elevs))
    print(f"  Stories in model: {len(story_map)}")

    # Step 7: Add missing sections (from A/B/C/D buildings)
    print(f"\n[7] Checking section definitions...")

    # Get sections referenced in new line assigns
    new_line_labels = {l['label'] for l in new_lines}
    new_sections_needed = set()
    for label in new_line_labels:
        if label in all_line_assigns:
            for a in all_line_assigns[label]:
                new_sections_needed.add(a['section'])

    print(f"  Sections needed by new lines: {sorted(new_sections_needed)}")

    # Check which sections already exist in the model
    # We'll try to get section properties for each
    missing_sections = []
    for sec_name in new_sections_needed:
        try:
            ret = SapModel.PropFrame.GetNameList(0, [])
            existing_secs = set(ret[1]) if ret[0] > 0 else set()
            if sec_name not in existing_secs:
                missing_sections.append(sec_name)
        except:
            pass
        break  # Only need to get the list once

    # Get full list of existing frame sections
    try:
        ret = SapModel.PropFrame.GetNameList(0, [])
        existing_frame_secs = set(ret[1]) if ret[0] > 0 else set()
        print(f"  Existing frame sections: {len(existing_frame_secs)}")
    except:
        existing_frame_secs = set()

    missing_frame_secs = new_sections_needed - existing_frame_secs
    if missing_frame_secs:
        print(f"  MISSING frame sections: {sorted(missing_frame_secs)}")

        # Parse section definitions from merged e2k
        frame_sec_lines = sections.get('FRAME SECTIONS', [])
        concrete_sec_lines = sections.get('CONCRETE SECTIONS', [])

        for sec_name in missing_frame_secs:
            # Try to add it
            print(f"    Adding section: {sec_name}")
            # Find definition in e2k
            for line in frame_sec_lines:
                if f'"{sec_name}"' in line:
                    # Extract shape info
                    shape_m = re.search(r'SHAPE\s+"([^"]+)"', line)
                    mat_m = re.search(r'MATERIAL\s+"([^"]+)"', line)
                    d_m = re.search(r'\bD\s+([\d.]+)', line)
                    b_m = re.search(r'\bB\s+([\d.]+)', line)

                    if shape_m and mat_m and d_m and b_m:
                        shape = shape_m.group(1)
                        mat = mat_m.group(1)
                        d = float(d_m.group(1))
                        b = float(b_m.group(1))

                        if shape == 'Rectangular':
                            ret = SapModel.PropFrame.SetRectangle(sec_name, mat, d, b)
                            print(f"      SetRectangle({sec_name}, {mat}, D={d}, B={b}): {ret}")
                    break

    # Step 8: Add new points
    if new_points:
        print(f"\n[8] Adding {len(new_points)} new points...")
        # ETABS doesn't have a direct "add point" - points are created when adding frames/areas
        # We'll need to add them through the elements
    else:
        print(f"\n[8] No new points to add")

    # Step 9: Add new frame elements (above-1MF)
    if new_lines:
        print(f"\n[9] Adding {len(new_lines)} new frame elements...")

        added = 0
        errors = 0

        for ldata in new_lines:
            label = ldata['label']
            ltype = ldata['type']
            pt1 = ldata['pt1']
            pt2 = ldata['pt2']

            if pt1 not in all_points or pt2 not in all_points:
                print(f"  SKIP {label}: missing point def")
                errors += 1
                continue

            x1, y1 = all_points[pt1]
            x2, y2 = all_points[pt2]

            # Get section from assigns
            sec_name = "NONE"
            if label in all_line_assigns:
                sec_name = all_line_assigns[label][0]['section']

            # Get story assignments
            stories = []
            if label in all_line_assigns:
                stories = [a['story'] for a in all_line_assigns[label]]

            if ltype == 'COLUMN':
                # For columns: add at each story
                for story in stories:
                    if story in story_map:
                        z_bot = story_map[story]
                        # Find the story above
                        story_idx = story_names.index(story) if story in story_names else -1
                        if story_idx > 0:
                            z_top = story_elevs[story_idx - 1]
                        else:
                            z_top = z_bot + 3.4  # default

                        name_out = ''
                        ret = SapModel.FrameObj.AddByCoord(x1, y1, z_bot, x1, y1, z_top, name_out, sec_name)
                        if ret[0] == 0:
                            added += 1
                        else:
                            if added < 5 or errors < 3:
                                print(f"  Column {label} at {story}: ret={ret[0]}")
                            errors += 1

            elif ltype == 'BEAM':
                # For beams: add at each story elevation
                for story in stories:
                    if story in story_map:
                        z = story_map[story]
                        name_out = ''
                        ret = SapModel.FrameObj.AddByCoord(x1, y1, z, x2, y2, z, name_out, sec_name)
                        if ret[0] == 0:
                            added += 1
                        else:
                            if added < 5 or errors < 3:
                                print(f"  Beam {label} at {story}: ret={ret[0]}")
                            errors += 1

        print(f"  Added: {added}, Errors: {errors}")
    else:
        print(f"\n[9] No new frames to add")

    # Step 10: Add new area elements (above-1MF)
    if new_areas:
        print(f"\n[10] Adding {len(new_areas)} new area elements...")

        added = 0
        errors = 0

        for adata in new_areas:
            label = adata['label']
            atype = adata['type']
            pts = adata['points']
            num_pts = adata['num_pts']

            # Get coordinates
            coords_ok = True
            xs, ys = [], []
            for p in pts:
                if p in all_points:
                    x, y = all_points[p]
                    xs.append(x)
                    ys.append(y)
                else:
                    coords_ok = False
                    break

            if not coords_ok:
                errors += 1
                continue

            # Get section from assigns
            sec_name = "NONE"
            if label in all_area_assigns:
                sec_name = all_area_assigns[label][0]['section']

            # Get story
            stories = []
            if label in all_area_assigns:
                stories = [a['story'] for a in all_area_assigns[label]]

            for story in stories:
                if story in story_map:
                    z = story_map[story]

                    if atype == 'PANEL':
                        # Wall: vertical element spanning one story
                        # Need z_bot and z_top
                        story_idx = story_names.index(story) if story in story_names else -1
                        if story_idx > 0:
                            z_top = story_elevs[story_idx - 1]
                        else:
                            z_top = z + 3.4

                        # Create 4 corners with bottom and top Z
                        if num_pts == 4:
                            x_arr = [xs[0], xs[1], xs[1], xs[0]]
                            y_arr = [ys[0], ys[1], ys[1], ys[0]]
                            z_arr = [z, z, z_top, z_top]
                            name_out = ''
                            ret = SapModel.AreaObj.AddByCoord(4, x_arr, y_arr, z_arr, name_out, sec_name)
                            if ret[0] == 0:
                                added += 1
                            else:
                                errors += 1

                    elif atype == 'FLOOR':
                        # Slab: horizontal element
                        z_arr = [z] * num_pts
                        name_out = ''
                        ret = SapModel.AreaObj.AddByCoord(num_pts, xs, ys, z_arr, name_out, sec_name)
                        if ret[0] == 0:
                            added += 1
                        else:
                            errors += 1

        print(f"  Added: {added}, Errors: {errors}")
    else:
        print(f"\n[10] No new areas to add")

    # Step 11: Update grid lines
    print(f"\n[11] Updating grid lines from merged e2k...")
    # TODO: Read grid data from merged e2k and update via API

    # Step 12: Refresh and save
    print(f"\n[12] Refreshing view and saving...")
    SapModel.View.RefreshView(0, False)
    ret = SapModel.File.Save(output_path)
    print(f"  Save: {ret}")

    # Final summary
    print(f"\n{'='*60}")
    print("FINAL MODEL SUMMARY")
    print(f"{'='*60}")

    ret_f = SapModel.FrameObj.GetNameList(0, [])
    print(f"Frames: {ret_f[0]}")

    ret_a = SapModel.AreaObj.GetNameList(0, [])
    print(f"Areas: {ret_a[0]}")

    ret_p = SapModel.PointObj.GetNameList(0, [])
    print(f"Points: {ret_p[0]}")

    print(f"\nModel saved to: {output_path}")
    print("Review in ETABS and check:")
    print("  1. Grid lines")
    print("  2. Above-1MF elements")
    print("  3. Column/beam continuity at 1F/1MF")
    print("  4. Section assignments")

if __name__ == '__main__':
    main()
