"""
Check column sections around R1F in MERGED_v5 ETABS model
and compare against original A/B/C/D e2k files.
Then fix any mismatches directly in the model.
"""
import comtypes.client
from comtypes.gen import ETABSv1
import subprocess
import os
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

def parse_e2k_sections_and_assignments(filepath, unit_scale=1.0):
    """Parse e2k file for frame sections and line assignments."""
    sections = {}  # name -> {D, B, material, shape}
    assignments = []  # list of {name, story, section, ...}
    stories = {}  # name -> height

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Parse FRAMESECTION definitions
    for m in re.finditer(r'FRAMESECTION\s+"([^"]+)".*?MATERIAL\s+"([^"]+)".*?SHAPE\s+"([^"]+)"(.*?)(?=\n\s*(?:FRAMESECTION|$))', content, re.DOTALL):
        sec_name = m.group(1)
        mat = m.group(2)
        shape = m.group(3)
        rest = m.group(4)

        d_match = re.search(r'\bD\s+([\d.]+)', rest)
        b_match = re.search(r'\bB\s+([\d.]+)', rest)

        d_val = float(d_match.group(1)) * unit_scale if d_match else 0
        b_val = float(b_match.group(1)) * unit_scale if b_match else 0

        sections[sec_name] = {'D': d_val, 'B': b_val, 'material': mat, 'shape': shape}

    # Parse LINEASSIGN for columns (vertical members)
    for m in re.finditer(r'LINEASSIGN\s+"([^"]+)"\s+STORY\s+"([^"]+)"\s+(.*)', content):
        frame_name = m.group(1)
        story = m.group(2)
        rest = m.group(3)

        sec_match = re.search(r'SECTION\s+"([^"]+)"', rest)
        if sec_match:
            section = sec_match.group(1)
            assignments.append({
                'name': frame_name,
                'story': story,
                'section': section,
            })

    # Parse stories
    for m in re.finditer(r'STORY\s+"([^"]+)"\s+HEIGHT\s+([\d.]+)', content):
        stories[m.group(1)] = float(m.group(2)) * unit_scale

    return sections, assignments, stories

def main():
    SapModel, pid = connect_etabs()
    if not SapModel:
        print("ERROR: Cannot connect to ETABS")
        return
    print(f"Connected to ETABS PID {pid}")
    SapModel.SetPresentUnits(12)  # TON/M

    # ===== STEP 1: Get column data from ETABS around R1F =====
    print("\n" + "="*70)
    print("STEP 1: Getting column data from ETABS model")
    print("="*70)

    # Target stories around R1F
    target_stories = ['30F', '31F', '32F', '33F', '34F', 'R1F', 'R2F', 'R3F', 'PRF']

    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [],
        [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])

    num_frames = ret[0]
    print(f"Total frames in model: {num_frames}")

    # Collect columns at target stories
    etabs_columns = defaultdict(list)  # story -> [{name, section, x, y}]

    for i in range(num_frames):
        story = ret[3][i]
        if story not in target_stories:
            continue

        # Check if it's a column (vertical)
        dx = abs(ret[6][i] - ret[9][i])
        dy = abs(ret[7][i] - ret[10][i])
        dz = abs(ret[8][i] - ret[11][i])

        if dx < 0.01 and dy < 0.01 and dz > 0.5:
            etabs_columns[story].append({
                'name': ret[1][i],
                'section': ret[2][i],
                'x': (ret[6][i] + ret[9][i]) / 2,
                'y': (ret[7][i] + ret[10][i]) / 2,
            })

    print("\nColumns per story in ETABS:")
    for s in target_stories:
        if s in etabs_columns:
            # Count sections
            sec_counts = defaultdict(int)
            for c in etabs_columns[s]:
                sec_counts[c['section']] += 1
            sec_str = ', '.join(f"{k}:{v}" for k, v in sorted(sec_counts.items()))
            print(f"  {s}: {len(etabs_columns[s])} columns - {sec_str}")

    # Get section dimensions from ETABS
    print("\nSection dimensions in ETABS:")
    ret_sec = SapModel.PropFrame.GetNameList(0, [])
    all_sections = set(ret_sec[1]) if ret_sec[0] > 0 else set()

    # Collect all section names used at target stories
    used_sections = set()
    for story_cols in etabs_columns.values():
        for c in story_cols:
            used_sections.add(c['section'])

    etabs_sec_dims = {}
    import math
    for sec in sorted(used_sections):
        if sec not in all_sections:
            print(f"  {sec}: NOT IN MODEL!")
            continue
        try:
            ret = SapModel.PropFrame.GetSectProps(sec, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            area = ret[0]
            i22 = ret[3]
            i33 = ret[4]
            if area > 0:
                d_calc = math.sqrt(12 * i33 / area)
                b_calc = math.sqrt(12 * i22 / area)
                etabs_sec_dims[sec] = {'D': round(d_calc, 4), 'B': round(b_calc, 4)}
                print(f"  {sec}: D={d_calc:.4f}m, B={b_calc:.4f}m (A={area:.6f})")
            else:
                print(f"  {sec}: A=0 (non-rectangular?)")
        except Exception as e:
            print(f"  {sec}: Error - {e}")

    # ===== STEP 2: Parse source e2k files =====
    print("\n" + "="*70)
    print("STEP 2: Parsing source A/B/C/D e2k files")
    print("="*70)

    base = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳'

    # Find e2k files
    e2k_files = {}
    for bldg, subdir, scale in [('A', 'A棟', 0.01), ('B', 'B棟', 1.0), ('C', 'C棟', 0.01), ('D', 'D棟', 0.01)]:
        folder = os.path.join(base, subdir)
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.lower().endswith('.e2k'):
                    e2k_files[bldg] = (os.path.join(folder, f), scale)
                    break

    print(f"Found e2k files: {list(e2k_files.keys())}")

    # Parse each building's e2k
    bldg_data = {}
    for bldg, (filepath, scale) in e2k_files.items():
        print(f"\n--- Building {bldg}: {os.path.basename(filepath)} (scale={scale}) ---")
        sections, assignments, stories = parse_e2k_sections_and_assignments(filepath, scale)
        bldg_data[bldg] = {'sections': sections, 'assignments': assignments, 'stories': stories}

        # Show stories around R1F
        r1f_stories = [s for s in stories if any(t in s for t in ['30F', '31F', '32F', '33F', '34F', 'R1F', 'R2F', 'R3F', 'PRF'])]
        print(f"  Stories near R1F: {r1f_stories}")

        # Show column assignments at target stories
        for target in target_stories:
            cols = [a for a in assignments if a['story'] == target]
            if cols:
                sec_counts = defaultdict(int)
                for c in cols:
                    sec_counts[c['section']] += 1
                sec_str = ', '.join(f"{k}:{v}" for k, v in sorted(sec_counts.items()))
                print(f"  {target}: {len(cols)} assignments - {sec_str}")

        # Show section dimensions for sections used at target stories
        target_secs = set()
        for a in assignments:
            if a['story'] in target_stories:
                target_secs.add(a['section'])

        for sec in sorted(target_secs):
            if sec in sections:
                s = sections[sec]
                print(f"    Section {sec}: D={s['D']:.4f}m, B={s['B']:.4f}m")

    # ===== STEP 3: Compare ETABS vs source e2k =====
    print("\n" + "="*70)
    print("STEP 3: COMPARISON - ETABS vs Source E2K")
    print("="*70)

    mismatches = []

    for bldg, data in bldg_data.items():
        print(f"\n--- Building {bldg} ---")
        e2k_secs = data['sections']

        for sec_name, etabs_dims in etabs_sec_dims.items():
            if sec_name in e2k_secs:
                e2k_d = e2k_secs[sec_name]['D']
                e2k_b = e2k_secs[sec_name]['B']
                etabs_d = etabs_dims['D']
                etabs_b = etabs_dims['B']

                d_match = abs(etabs_d - e2k_d) < 0.02
                b_match = abs(etabs_b - e2k_b) < 0.02

                if not (d_match and b_match):
                    status = "MISMATCH!"
                    mismatches.append({
                        'section': sec_name,
                        'building': bldg,
                        'etabs_D': etabs_d,
                        'etabs_B': etabs_b,
                        'e2k_D': e2k_d,
                        'e2k_B': e2k_b,
                    })
                else:
                    status = "OK"
                print(f"  {sec_name}: ETABS(D={etabs_d:.4f},B={etabs_b:.4f}) vs E2K(D={e2k_d:.4f},B={e2k_b:.4f}) -> {status}")

    # Also check: do the ETABS assignments at each story match the source?
    print("\n" + "="*70)
    print("STEP 3b: ASSIGNMENT COMPARISON (which section at which story)")
    print("="*70)

    assignment_mismatches = []

    for story in target_stories:
        etabs_cols = etabs_columns.get(story, [])
        if not etabs_cols:
            continue

        print(f"\n  Story {story}: {len(etabs_cols)} columns in ETABS")

        # For each ETABS column, try to find matching source assignment by position
        for bldg, data in bldg_data.items():
            e2k_assigns = [a for a in data['assignments'] if a['story'] == story]
            if not e2k_assigns:
                continue

            # Get unique section sets
            etabs_secs = set(c['section'] for c in etabs_cols)
            e2k_secs = set(a['section'] for a in e2k_assigns)

            only_etabs = etabs_secs - e2k_secs
            only_e2k = e2k_secs - etabs_secs

            if only_etabs or only_e2k:
                print(f"    vs {bldg}: ETABS-only sections: {only_etabs}, E2K-only sections: {only_e2k}")
                for sec in only_e2k:
                    assignment_mismatches.append({
                        'story': story,
                        'building': bldg,
                        'missing_section': sec,
                        'etabs_sections': list(etabs_secs),
                    })

    # ===== STEP 4: Summary =====
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if mismatches:
        print(f"\n  DIMENSION MISMATCHES: {len(mismatches)}")
        for m in mismatches:
            print(f"    {m['section']} (Bldg {m['building']}): "
                  f"ETABS D={m['etabs_D']:.4f}/B={m['etabs_B']:.4f} vs "
                  f"E2K D={m['e2k_D']:.4f}/B={m['e2k_B']:.4f}")
    else:
        print("\n  No dimension mismatches found!")

    if assignment_mismatches:
        print(f"\n  ASSIGNMENT MISMATCHES: {len(assignment_mismatches)}")
        for m in assignment_mismatches:
            print(f"    {m['story']} (Bldg {m['building']}): missing {m['missing_section']}, "
                  f"ETABS has {m['etabs_sections']}")
    else:
        print("\n  No assignment mismatches found!")

    return mismatches, assignment_mismatches

if __name__ == '__main__':
    main()
