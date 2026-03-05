"""
Diagnose MERGED_v5.EDB in ETABS - check sections, connectivity, grids.
Connects to running ETABS instance and extracts live model data.
"""
import comtypes.client
from comtypes.gen import ETABSv1
import subprocess
import re
import json
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

def parse_e2k_sections(filepath, unit_scale=1.0):
    """Parse frame section definitions from e2k file."""
    sections = {}
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = re.match(r'\s+FRAMESECTION\s+"([^"]+)"(.*)', line)
            if m:
                sec_name = m.group(1)
                rest = m.group(2)
                info = {}
                mm = re.search(r'MATERIAL\s+"([^"]+)"', rest)
                if mm: info['material'] = mm.group(1)
                mm = re.search(r'SHAPE\s+"([^"]+)"', rest)
                if mm: info['shape'] = mm.group(1)
                mm = re.search(r'\bD\s+([\d.\-E+]+)', rest)
                if mm: info['D'] = float(mm.group(1)) * unit_scale
                mm = re.search(r'\bB\s+([\d.\-E+]+)', rest)
                if mm: info['B'] = float(mm.group(1)) * unit_scale
                sections[sec_name] = info
    return sections

def main():
    SapModel, pid = connect_etabs()
    if not SapModel:
        print("ERROR: Cannot connect to ETABS")
        return
    print(f"Connected to ETABS PID {pid}")

    SapModel.SetPresentUnits(12)  # TON/M

    # Get model filename
    ret = SapModel.GetModelFilename()
    if isinstance(ret, (list, tuple)):
        filename = ret[0] if ret[0] else ret
    else:
        filename = ret
    print(f"Model: {filename}")

    # ====== 1. GET ALL FRAME SECTIONS ======
    print("\n" + "=" * 60)
    print("[1] FRAME SECTIONS IN ETABS MODEL")
    print("=" * 60)

    ret = SapModel.PropFrame.GetNameList(0, [])
    num_secs = ret[0]
    sec_names = list(ret[1]) if num_secs > 0 else []
    print(f"Total frame sections: {num_secs}")

    # Get dimensions for each section
    etabs_sections = {}
    for sn in sec_names:
        try:
            # GetRectangle returns: (Name, MatProp, T3, T2, Color, Notes, GUID, ret)
            ret = SapModel.PropFrame.GetRectangle(sn, '', 0, 0, 0, '', '')
            if isinstance(ret, (list, tuple)) and len(ret) >= 4:
                mat = ret[0]
                d = ret[1]  # T3 = depth
                b = ret[2]  # T2 = width
                etabs_sections[sn] = {'material': mat, 'D': d, 'B': b, 'shape': 'Rectangular'}
        except:
            pass

    # Parse original building sections
    print("\nLoading original building section definitions...")
    a_secs = parse_e2k_sections(
        r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\A\2026-0303_A_SC_KpKvKw.e2k', 0.01)
    b_secs = parse_e2k_sections(
        r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\B\2026-0303_B_SC_KpKvKw.e2k', 1.0)
    c_secs = parse_e2k_sections(
        r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\C\2026-0304_C_SC_KpKvKw.e2k', 0.01)
    d_secs = parse_e2k_sections(
        r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\D\2026-0303_D_SC_KpKvKw.e2k', 0.01)
    old_secs = parse_e2k_sections(
        r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\OLD\2025-1111_ALL_BUT RC_KpKvKw.e2k', 1.0)

    all_original_secs = {}
    for src, secs in [('A', a_secs), ('B', b_secs), ('C', c_secs), ('D', d_secs), ('OLD', old_secs)]:
        for name, info in secs.items():
            if name not in all_original_secs:
                all_original_secs[name] = {'info': info, 'source': src}

    # Compare ETABS model sections with originals
    sec_issues = []
    for sn, etabs_info in etabs_sections.items():
        if sn in all_original_secs:
            orig = all_original_secs[sn]['info']
            orig_d = orig.get('D')
            orig_b = orig.get('B')
            etabs_d = etabs_info.get('D')
            etabs_b = etabs_info.get('B')

            if orig_d is not None and etabs_d is not None:
                if abs(orig_d - etabs_d) > 0.005 or abs(orig_b - etabs_b) > 0.005:
                    sec_issues.append({
                        'section': sn,
                        'source': all_original_secs[sn]['source'],
                        'etabs_D': etabs_d, 'etabs_B': etabs_b,
                        'orig_D': orig_d, 'orig_B': orig_b,
                        'material': orig.get('material', '')
                    })

    print(f"\nSection dimension mismatches: {len(sec_issues)}")
    for si in sec_issues:
        print(f"  {si['section']} (from {si['source']}): ETABS D={si['etabs_D']:.4f} B={si['etabs_B']:.4f} "
              f"vs original D={si['orig_D']:.4f} B={si['orig_B']:.4f}")

    # ====== 2. CHECK COLUMN CONNECTIVITY ======
    print("\n" + "=" * 60)
    print("[2] COLUMN CONNECTIVITY CHECK")
    print("=" * 60)

    # Get all frames
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [],
        [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])

    num_frames = ret[0]
    frame_names = list(ret[1]) if num_frames > 0 else []
    frame_props = list(ret[2]) if num_frames > 0 else []
    frame_stories = list(ret[3]) if num_frames > 0 else []
    pt1_names = list(ret[4]) if num_frames > 0 else []
    pt2_names = list(ret[5]) if num_frames > 0 else []
    pt1_x = list(ret[6]) if num_frames > 0 else []
    pt1_y = list(ret[7]) if num_frames > 0 else []
    pt1_z = list(ret[8]) if num_frames > 0 else []
    pt2_x = list(ret[9]) if num_frames > 0 else []
    pt2_y = list(ret[10]) if num_frames > 0 else []
    pt2_z = list(ret[11]) if num_frames > 0 else []

    print(f"Total frames: {num_frames}")

    # Identify columns (vertical frames where X1≈X2, Y1≈Y2)
    columns_by_story = defaultdict(list)
    for i in range(num_frames):
        dx = abs(pt1_x[i] - pt2_x[i])
        dy = abs(pt1_y[i] - pt2_y[i])
        if dx < 0.01 and dy < 0.01 and abs(pt1_z[i] - pt2_z[i]) > 0.5:
            story = frame_stories[i]
            columns_by_story[story].append({
                'name': frame_names[i],
                'prop': frame_props[i],
                'x': (pt1_x[i] + pt2_x[i]) / 2,
                'y': (pt1_y[i] + pt2_y[i]) / 2,
                'z_bot': min(pt1_z[i], pt2_z[i]),
                'z_top': max(pt1_z[i], pt2_z[i]),
                'pt1': pt1_names[i],
                'pt2': pt2_names[i],
            })

    print("\nColumns per story:")
    for story in sorted(columns_by_story.keys()):
        cols = columns_by_story[story]
        print(f"  {story}: {len(cols)} columns")

    # Check connectivity at 1F/1MF interface
    cols_1f = columns_by_story.get('1F', [])
    cols_1mf = columns_by_story.get('1MF', [])
    cols_2f = columns_by_story.get('2F', [])

    print(f"\n  Interface check: 1F={len(cols_1f)} cols, 1MF={len(cols_1mf)} cols, 2F={len(cols_2f)} cols")

    # For each 1F column, find matching 1MF column
    TOL = 0.02  # 2cm
    connected = []
    disconnected_1f = []

    for c1 in cols_1f:
        found = False
        for c2 in cols_1mf:
            if abs(c1['x'] - c2['x']) < TOL and abs(c1['y'] - c2['y']) < TOL:
                # Check if they share a point (true connectivity)
                shares_point = (c1['pt2'] == c2['pt1'] or c1['pt2'] == c2['pt2'] or
                               c1['pt1'] == c2['pt1'] or c1['pt1'] == c2['pt2'])
                # Check z continuity
                z_gap = abs(c1['z_top'] - c2['z_bot'])
                connected.append({
                    '1f_col': c1['name'], '1f_prop': c1['prop'],
                    '1mf_col': c2['name'], '1mf_prop': c2['prop'],
                    'shares_point': shares_point,
                    'z_gap': z_gap,
                    'x': c1['x'], 'y': c1['y']
                })
                found = True
                break
        if not found:
            disconnected_1f.append(c1)

    print(f"\n  1F-1MF pairs: {len(connected)}")
    print(f"  Disconnected 1F cols (no 1MF match): {len(disconnected_1f)}")

    # Check shared points vs separate points
    shared = sum(1 for c in connected if c['shares_point'])
    separate = sum(1 for c in connected if not c['shares_point'])
    z_gaps = [c for c in connected if c['z_gap'] > 0.01]

    print(f"\n  Shared endpoint: {shared}")
    print(f"  Separate endpoints (NOT connected): {separate}")
    print(f"  Z gaps > 1cm: {len(z_gaps)}")

    if separate > 0:
        print("\n  ISSUE: Columns with separate endpoints (need connection):")
        for c in connected[:20]:
            if not c['shares_point']:
                print(f"    1F:{c['1f_col']}({c['1f_prop']}) <-> 1MF:{c['1mf_col']}({c['1mf_prop']}) "
                      f"at ({c['x']:.3f},{c['y']:.3f}), z_gap={c['z_gap']:.4f}m")

    if z_gaps:
        print(f"\n  Z gaps:")
        for c in z_gaps[:10]:
            print(f"    {c['1f_col']} z_top={c.get('1f_z_top', 'N/A')} vs {c['1mf_col']} z_bot")

    # Also check 1MF-2F connectivity
    print("\n  Checking 1MF-2F connectivity...")
    for c_mf in cols_1mf[:5]:
        found_2f = False
        for c_2f in cols_2f:
            if abs(c_mf['x'] - c_2f['x']) < TOL and abs(c_mf['y'] - c_2f['y']) < TOL:
                shares = (c_mf['pt2'] == c_2f['pt1'] or c_mf['pt2'] == c_2f['pt2'])
                z_gap = abs(c_mf['z_top'] - c_2f['z_bot'])
                print(f"    1MF:{c_mf['name']}({c_mf['prop']}) -> 2F:{c_2f['name']}({c_2f['prop']}) "
                      f"shares_pt={shares}, z_gap={z_gap:.4f}")
                found_2f = True
                break
        if not found_2f:
            print(f"    1MF:{c_mf['name']} has NO 2F match at ({c_mf['x']:.3f},{c_mf['y']:.3f})")

    # ====== 3. DISCONNECTED COLUMNS DETAIL ======
    if disconnected_1f:
        print(f"\n  Disconnected 1F columns (no matching 1MF):")
        for dc in disconnected_1f[:20]:
            print(f"    {dc['name']}({dc['prop']}) at ({dc['x']:.3f},{dc['y']:.3f}) "
                  f"z={dc['z_bot']:.2f}-{dc['z_top']:.2f}")

    # ====== 4. SAVE REPORT ======
    report = {
        'section_issues': sec_issues,
        'total_frames': num_frames,
        'columns_per_story': {s: len(c) for s, c in columns_by_story.items()},
        'connected_pairs': len(connected),
        'shared_point': shared,
        'separate_point': separate,
        'disconnected_1f': len(disconnected_1f),
        'connected_details': connected[:50],
        'disconnected_details': [{'name': d['name'], 'prop': d['prop'], 'x': d['x'], 'y': d['y']} for d in disconnected_1f[:50]],
    }

    report_path = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\scripts\agent_reports\etabs_diagnosis.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to: {report_path}")

if __name__ == '__main__':
    main()
