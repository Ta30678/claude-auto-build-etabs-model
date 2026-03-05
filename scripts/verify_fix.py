"""
Post-fix verification of MERGED_v5.EDB:
1. Check column connectivity at ALL story interfaces
2. Verify section assignments
3. Check beam connectivity
4. Identify any remaining issues
"""
import comtypes.client
from comtypes.gen import ETABSv1
import subprocess
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

    # Get all frames
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [],
        [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])

    num_frames = ret[0]
    print(f"Total frames: {num_frames}")

    # Get story data
    ret_s = SapModel.Story.GetStories_2(0, 0, [], [], [], [], [], [], [], [])
    story_names = list(ret_s[2])
    story_elevs = list(ret_s[3])
    print(f"Stories: {len(story_names)}")

    # Identify all columns per story
    columns_by_story = defaultdict(list)
    beams_by_story = defaultdict(list)

    for i in range(num_frames):
        dx = abs(ret[6][i] - ret[9][i])
        dy = abs(ret[7][i] - ret[10][i])
        dz = abs(ret[8][i] - ret[11][i])
        story = ret[3][i]

        if dx < 0.01 and dy < 0.01 and dz > 0.5:  # column
            columns_by_story[story].append({
                'name': ret[1][i], 'prop': ret[2][i],
                'x': (ret[6][i] + ret[9][i]) / 2,
                'y': (ret[7][i] + ret[10][i]) / 2,
                'z_bot': min(ret[8][i], ret[11][i]),
                'z_top': max(ret[8][i], ret[11][i]),
                'pt1': ret[4][i], 'pt2': ret[5][i],
            })
        elif dz < 0.01:  # beam (horizontal)
            beams_by_story[story].append({
                'name': ret[1][i], 'prop': ret[2][i],
                'pt1': ret[4][i], 'pt2': ret[5][i],
                'x1': ret[6][i], 'y1': ret[7][i], 'z1': ret[8][i],
                'x2': ret[9][i], 'y2': ret[10][i], 'z2': ret[11][i],
            })

    # ===== CHECK COLUMN CONNECTIVITY AT EACH STORY INTERFACE =====
    print("\n" + "=" * 60)
    print("COLUMN CONNECTIVITY AT EACH STORY INTERFACE")
    print("=" * 60)

    story_order = ['B6F', 'B5F', 'B4F', 'B3F', 'B2F', 'B1F', '1F', '1MF',
                   '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F',
                   '11F', '12F', '13F', '14F', '15F', '16F', '17F', '18F',
                   '19F', '20F', '21F', '22F', '23F', '24F', '25F', '26F',
                   '27F', '28F', '29F', '30F', '31F', '32F', '33F', '34F',
                   'R1F', 'R2F', 'R3F', 'PRF']

    TOL = 0.02  # 2cm

    for i in range(len(story_order) - 1):
        lower = story_order[i]
        upper = story_order[i + 1]

        if lower not in columns_by_story or upper not in columns_by_story:
            continue

        lower_cols = columns_by_story[lower]
        upper_cols = columns_by_story[upper]

        connected = 0
        shared_pt = 0
        for c1 in lower_cols:
            for c2 in upper_cols:
                if abs(c1['x'] - c2['x']) < TOL and abs(c1['y'] - c2['y']) < TOL:
                    connected += 1
                    if c1['pt2'] == c2['pt1'] or c1['pt1'] == c2['pt1']:
                        shared_pt += 1
                    break

        status = "OK" if connected >= min(len(lower_cols), len(upper_cols)) else "ISSUE"
        if connected < min(len(lower_cols), len(upper_cols)):
            print(f"  {lower}->{upper}: {len(lower_cols)} lower, {len(upper_cols)} upper, "
                  f"{connected} connected, {shared_pt} shared_pt [{status}]")
        elif lower == '1F' or lower == 'B1F':
            print(f"  {lower}->{upper}: {len(lower_cols)} lower, {len(upper_cols)} upper, "
                  f"{connected} connected, {shared_pt} shared_pt [{status}]")

    # ===== CHECK UNMATCHED 1F COLUMNS =====
    print("\n" + "=" * 60)
    print("REMAINING UNMATCHED 1F COLUMNS")
    print("=" * 60)

    cols_1f = columns_by_story.get('1F', [])
    cols_1mf = columns_by_story.get('1MF', [])

    unmatched = []
    for c1 in cols_1f:
        found = False
        for c2 in cols_1mf:
            if abs(c1['x'] - c2['x']) < TOL and abs(c1['y'] - c2['y']) < TOL:
                found = True
                break
        if not found:
            unmatched.append(c1)

    if unmatched:
        print(f"  {len(unmatched)} 1F columns without 1MF match:")
        for u in unmatched:
            # Check if this column has a B1F match below (to verify it's part of basement)
            has_below = False
            for cb in columns_by_story.get('B1F', []):
                if abs(u['x'] - cb['x']) < TOL and abs(u['y'] - cb['y']) < TOL:
                    has_below = True
                    break
            print(f"    {u['name']}({u['prop']}) at ({u['x']:.3f},{u['y']:.3f}) "
                  f"has_B1F_below={has_below}")
    else:
        print("  All 1F columns have 1MF matches!")

    # ===== BEAM CONNECTIVITY CHECK =====
    print("\n" + "=" * 60)
    print("BEAM CONNECTIVITY SPOT CHECK")
    print("=" * 60)

    # Check beams at 1F level - do they connect to column endpoints?
    beams_1f = beams_by_story.get('1F', [])
    cols_1f_pts = set()
    for c in cols_1f:
        cols_1f_pts.add(c['pt1'])
        cols_1f_pts.add(c['pt2'])

    beam_connected = 0
    beam_orphan = 0
    for b in beams_1f[:50]:  # check first 50
        pt1_ok = b['pt1'] in cols_1f_pts
        pt2_ok = b['pt2'] in cols_1f_pts
        if pt1_ok or pt2_ok:
            beam_connected += 1
        else:
            beam_orphan += 1

    print(f"  1F beams checked: {min(50, len(beams_1f))}")
    print(f"  Connected to column pts: {beam_connected}")
    print(f"  Not connected to column pts: {beam_orphan}")
    print(f"  (Note: beams may connect to other beams, not just columns)")

    # ===== SUMMARY =====
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total frames: {num_frames}")
    print(f"  Columns per story:")
    for s in ['B6F', 'B5F', 'B1F', '1F', '1MF', '2F', '3F', '34F', 'R1F', 'PRF']:
        if s in columns_by_story:
            print(f"    {s}: {len(columns_by_story[s])}")
    print(f"  Beams per story:")
    for s in ['B6F', 'B1F', '1F', '1MF', '2F', '3F']:
        if s in beams_by_story:
            print(f"    {s}: {len(beams_by_story[s])}")

    print(f"\n  1F-1MF: {len(cols_1f)} 1F cols, {len(cols_1mf)} 1MF cols, "
          f"{len(cols_1f) - len(unmatched)} connected, {len(unmatched)} unmatched")

if __name__ == '__main__':
    main()
