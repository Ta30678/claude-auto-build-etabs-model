"""
Comprehensive comparison of ALL frame section dimensions between
source A/B/C/D e2k files and the MERGED_v5 ETABS model.
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
        print("ERROR: Cannot connect to ETABS")
        return
    print(f"Connected to ETABS PID {pid}")
    SapModel.SetPresentUnits(12)  # TON/M

    # Get ALL section dimensions from ETABS
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        'Frame Section Property Definitions - Concrete Rectangular', [], 'All',
        0, [], 0, [])

    fields = list(ret[2])
    num_fields = len(fields)
    num_records = ret[3]
    data = list(ret[4])

    name_idx = fields.index('Name')
    t3_idx = fields.index('t3')
    t2_idx = fields.index('t2')
    mat_idx = fields.index('Material')

    etabs_secs = {}
    for r in range(num_records):
        row = data[r*num_fields:(r+1)*num_fields]
        name = row[name_idx]
        t3 = float(row[t3_idx]) if row[t3_idx] else 0
        t2 = float(row[t2_idx]) if row[t2_idx] else 0
        mat = row[mat_idx] if row[mat_idx] else ''
        etabs_secs[name] = {'t3': t3, 't2': t2, 'material': mat}

    print(f"ETABS concrete rectangular sections: {len(etabs_secs)}")

    # Parse source e2k files
    files = {
        'A': ('ETABS REF/大陳/A/2026-0303_A_SC_KpKvKw.e2k', 0.01),
        'B': ('ETABS REF/大陳/B/2026-0303_B_SC_KpKvKw.e2k', 1.0),
        'C': ('ETABS REF/大陳/C/2026-0304_C_SC_KpKvKw.e2k', 0.01),
        'D': ('ETABS REF/大陳/D/2026-0303_D_SC_KpKvKw.e2k', 0.01),
    }

    all_e2k_secs = {}  # name -> {D, B, building, material}

    for bldg, (filepath, scale) in files.items():
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        for m in re.finditer(r'FRAMESECTION\s+"([^"]+)".*?MATERIAL\s+"([^"]+)".*?SHAPE\s+"([^"]+)".*?D\s+([\d.]+).*?B\s+([\d.]+)', content):
            name = m.group(1)
            mat = m.group(2)
            shape = m.group(3)
            d_val = float(m.group(4)) * scale
            b_val = float(m.group(5)) * scale

            if name not in all_e2k_secs:
                all_e2k_secs[name] = {'D': d_val, 'B': b_val, 'material': mat, 'buildings': [bldg], 'shape': shape}
            else:
                if bldg not in all_e2k_secs[name]['buildings']:
                    all_e2k_secs[name]['buildings'].append(bldg)

    print(f"Source e2k sections: {len(all_e2k_secs)}")

    # Compare
    print("\n" + "="*80)
    print("DIMENSION MISMATCHES (e2k D/B vs ETABS t3/t2)")
    print("="*80)

    mismatches = []
    matches = 0
    missing_in_etabs = 0
    not_rectangular = 0

    for name, e2k in sorted(all_e2k_secs.items()):
        if name in etabs_secs:
            et = etabs_secs[name]
            d_ok = abs(et['t3'] - e2k['D']) < 0.02
            b_ok = abs(et['t2'] - e2k['B']) < 0.02
            if d_ok and b_ok:
                matches += 1
            else:
                # Check if D/B are swapped
                d_swap = abs(et['t3'] - e2k['B']) < 0.02
                b_swap = abs(et['t2'] - e2k['D']) < 0.02
                swapped = d_swap and b_swap

                mismatches.append({
                    'name': name,
                    'e2k_D': e2k['D'],
                    'e2k_B': e2k['B'],
                    'etabs_t3': et['t3'],
                    'etabs_t2': et['t2'],
                    'buildings': e2k['buildings'],
                    'swapped': swapped,
                })
                tag = " [D/B SWAPPED!]" if swapped else ""
                print(f"  {name}: E2K(D={e2k['D']:.4f},B={e2k['B']:.4f}) vs ETABS(t3={et['t3']:.4f},t2={et['t2']:.4f}){tag}")
        else:
            # Check if it's a column section (not beam/brace)
            if name.startswith(('C', 'SRC')):
                missing_in_etabs += 1
                # Only report column sections
                if not any(x in name for x in ['AB', 'ASB', 'SB', 'FB', 'WB', 'FSB', 'FWB']):
                    pass  # Don't spam - many sections may be missing if only above-1MF was built

    print(f"\n  Summary:")
    print(f"  Matching: {matches}")
    print(f"  Mismatches: {len(mismatches)}")
    print(f"  Missing in ETABS (columns): {missing_in_etabs}")

    # Now check per-story assignments
    print("\n" + "="*80)
    print("CHECKING COLUMN ASSIGNMENTS AT EVERY STORY")
    print("="*80)

    # Get all frame data from ETABS
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [],
        [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])

    num_frames = ret[0]

    # Columns by story in ETABS
    etabs_col_by_story = defaultdict(lambda: defaultdict(int))
    for i in range(num_frames):
        dx = abs(ret[6][i] - ret[9][i])
        dy = abs(ret[7][i] - ret[10][i])
        dz = abs(ret[8][i] - ret[11][i])
        if dx < 0.01 and dy < 0.01 and dz > 0.5:
            story = ret[3][i]
            etabs_col_by_story[story][ret[2][i]] += 1

    # Source assignments by story (columns only)
    source_col_by_story = defaultdict(lambda: defaultdict(int))

    for bldg, (filepath, scale) in files.items():
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # Get column line names
        cols = set()
        for m in re.finditer(r'LINE\s+"([^"]+)"\s+COLUMN\s', content):
            cols.add(m.group(1))

        # Get assignments for columns only
        for m in re.finditer(r'LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"', content):
            frame = m.group(1)
            story = m.group(2)
            section = m.group(3)
            if frame in cols:
                source_col_by_story[story][section] += 1

    # Compare counts per story
    all_stories = ['1MF','2F','3F','4F','5F','6F','7F','8F','9F','10F',
                   '11F','12F','13F','14F','15F','16F','17F','18F','19F','20F',
                   '21F','22F','23F','24F','25F','26F','27F','28F','29F','30F',
                   '31F','32F','33F','34F','R1F','R2F','R3F','PRF']

    for story in all_stories:
        et_secs = etabs_col_by_story.get(story, {})
        src_secs = source_col_by_story.get(story, {})

        et_total = sum(et_secs.values())
        src_total = sum(src_secs.values())

        if et_total != src_total:
            print(f"\n  {story}: ETABS={et_total} cols, Source={src_total} cols  <-- COUNT MISMATCH!")
            et_str = ', '.join(f'{k}:{v}' for k, v in sorted(et_secs.items()))
            src_str = ', '.join(f'{k}:{v}' for k, v in sorted(src_secs.items()))
            print(f"    ETABS:  {et_str}")
            print(f"    Source: {src_str}")

        # Check section name mismatches (same count but different sections)
        elif et_secs != dict(src_secs):
            only_et = set(et_secs.keys()) - set(src_secs.keys())
            only_src = set(src_secs.keys()) - set(et_secs.keys())
            if only_et or only_src:
                print(f"\n  {story}: Same count ({et_total}) but different sections!")
                if only_et:
                    print(f"    ETABS-only: {', '.join(f'{s}:{et_secs[s]}' for s in sorted(only_et))}")
                if only_src:
                    print(f"    Source-only: {', '.join(f'{s}:{src_secs[s]}' for s in sorted(only_src))}")

    # Fix dimension mismatches if found
    if mismatches:
        print("\n" + "="*80)
        print(f"FIXING {len(mismatches)} DIMENSION MISMATCHES")
        print("="*80)

        SapModel.SetModelIsLocked(False)

        for m in mismatches:
            name = m['name']
            correct_d = m['e2k_D']
            correct_b = m['e2k_B']

            if name in etabs_secs:
                mat = etabs_secs[name]['material']
                try:
                    ret = SapModel.PropFrame.SetRectangle(name, mat, correct_d, correct_b)
                    status = 'OK' if ret == 0 else f'FAIL(ret={ret})'
                    print(f"  Fixed {name}: t3={correct_d:.4f}, t2={correct_b:.4f}, mat={mat} -> {status}")
                except Exception as e:
                    print(f"  Error fixing {name}: {e}")

        output = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v5.EDB'
        SapModel.File.Save(output)
        print(f"\nSaved to: {output}")
    else:
        print("\nNo dimension mismatches to fix!")

if __name__ == '__main__':
    main()
