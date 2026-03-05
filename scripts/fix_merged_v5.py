"""
Fix MERGED_v5.EDB column connectivity:
1. Match each 1MF superstructure column to nearest OLD 1F column
2. Move OLD column points to superstructure positions using select + EditGeneral.Move
3. This reconnects basement to superstructure at the 1F/1MF interface

Strategy: Move basement points to align with superstructure column positions.
Uses cEditGeneral.Move(DX, DY, DZ) on selected points.
"""
import comtypes.client
from comtypes.gen import ETABSv1
import subprocess
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

def main():
    SapModel, pid = connect_etabs()
    if not SapModel:
        print("ERROR: Cannot connect to ETABS")
        return
    print(f"Connected to ETABS PID {pid}")

    SapModel.SetPresentUnits(12)  # TON/M
    SapModel.SetModelIsLocked(False)

    # ===== STEP 1: Get all frame data =====
    print("\n[STEP 1] Getting all frames...")
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [],
        [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])

    num_frames = ret[0]
    print(f"  Total frames: {num_frames}")

    # ===== STEP 2: Identify columns at 1F and 1MF =====
    print("\n[STEP 2] Identifying columns at 1F and 1MF...")

    columns_1f = []
    columns_1mf = []

    for i in range(num_frames):
        dx = abs(ret[6][i] - ret[9][i])
        dy = abs(ret[7][i] - ret[10][i])
        if dx < 0.01 and dy < 0.01 and abs(ret[8][i] - ret[11][i]) > 0.5:
            col_info = {
                'name': ret[1][i],
                'prop': ret[2][i],
                'story': ret[3][i],
                'x': (ret[6][i] + ret[9][i]) / 2,
                'y': (ret[7][i] + ret[10][i]) / 2,
                'z_bot': min(ret[8][i], ret[11][i]),
                'z_top': max(ret[8][i], ret[11][i]),
                'pt1': ret[4][i],
                'pt2': ret[5][i],
            }
            if ret[3][i] == '1F':
                columns_1f.append(col_info)
            elif ret[3][i] == '1MF':
                columns_1mf.append(col_info)

    print(f"  1F columns: {len(columns_1f)}")
    print(f"  1MF columns: {len(columns_1mf)}")

    # ===== STEP 3: Match 1F to 1MF columns =====
    print("\n[STEP 3] Matching 1F -> 1MF columns...")

    TOL = 0.02
    MAX_SEARCH = 5.0

    # Find already-connected
    unmatched_1f = list(columns_1f)
    unmatched_1mf = list(columns_1mf)
    matched_direct = []

    for c1 in columns_1f[:]:
        for c2 in columns_1mf[:]:
            if abs(c1['x'] - c2['x']) < TOL and abs(c1['y'] - c2['y']) < TOL:
                matched_direct.append((c1, c2))
                if c1 in unmatched_1f:
                    unmatched_1f.remove(c1)
                if c2 in unmatched_1mf:
                    unmatched_1mf.remove(c2)
                break

    print(f"  Already connected: {len(matched_direct)}")
    print(f"  Unmatched 1F: {len(unmatched_1f)}")
    print(f"  Unmatched 1MF: {len(unmatched_1mf)}")

    # Match unmatched by nearest neighbor
    matched_move = []  # (1f_col, 1mf_col, dx, dy)
    still_unmatched_1mf = list(unmatched_1mf)

    for c2 in unmatched_1mf:
        best_dist = MAX_SEARCH
        best_c1 = None
        for c1 in unmatched_1f:
            dist = ((c1['x'] - c2['x'])**2 + (c1['y'] - c2['y'])**2)**0.5
            if dist < best_dist:
                best_dist = dist
                best_c1 = c1

        if best_c1 is not None:
            dx = c2['x'] - best_c1['x']
            dy = c2['y'] - best_c1['y']
            matched_move.append((best_c1, c2, dx, dy))
            unmatched_1f.remove(best_c1)
            still_unmatched_1mf.remove(c2)
            print(f"  Pair: 1F:{best_c1['name']}({best_c1['x']:.3f},{best_c1['y']:.3f}) "
                  f"-> 1MF:{c2['name']}({c2['x']:.3f},{c2['y']:.3f}) "
                  f"delta=({dx:.4f},{dy:.4f}) dist={best_dist:.4f}")

    print(f"\n  Pairs to move: {len(matched_move)}")

    if unmatched_1f:
        print(f"\n  Remaining unmatched 1F columns ({len(unmatched_1f)}):")
        for c in unmatched_1f:
            print(f"    {c['name']}({c['prop']}) at ({c['x']:.3f},{c['y']:.3f})")

    if still_unmatched_1mf:
        print(f"\n  Remaining unmatched 1MF columns ({len(still_unmatched_1mf)}):")
        for c in still_unmatched_1mf:
            print(f"    {c['name']}({c['prop']}) at ({c['x']:.3f},{c['y']:.3f})")

    # ===== STEP 4: Build point movement map =====
    print("\n[STEP 4] Building point movement map...")

    # Group by unique delta to minimize select/move operations
    point_moves = {}  # (old_x_round, old_y_round) -> (dx, dy)

    for c1, c2, dx, dy in matched_move:
        key = (round(c1['x'], 4), round(c1['y'], 4))
        point_moves[key] = (dx, dy)

    print(f"  Unique positions to move: {len(point_moves)}")

    # Get story elevation data
    ret = SapModel.Story.GetStories_2(0, 0, [], [], [], [], [], [], [], [])
    story_names = list(ret[2])
    story_elevs = list(ret[3])
    story_elev_map = dict(zip(story_names, story_elevs))

    f1_elev = story_elev_map.get('1F', 0.6)  # top of 1F
    print(f"  1F elevation (top): {f1_elev}")

    # Find ALL points at or below 1F that need moving
    ret = SapModel.PointObj.GetNameList(0, [])
    num_points = ret[0]
    point_names = list(ret[1]) if num_points > 0 else []
    print(f"  Total points in model: {num_points}")

    # Group points by the delta they need
    delta_groups = defaultdict(list)  # (dx_round, dy_round) -> [point_names]

    scanned = 0
    for pt_name in point_names:
        try:
            ret = SapModel.PointObj.GetCoordCartesian(pt_name, 0, 0, 0)
            px, py, pz = ret[0], ret[1], ret[2]
        except:
            continue

        scanned += 1
        if scanned % 2000 == 0:
            print(f"    Scanned {scanned}/{num_points} points...")

        # Only move points at or below 1F elevation (basement)
        if pz > f1_elev + 0.01:
            continue

        # Check if this point is at a position that needs moving
        key = (round(px, 4), round(py, 4))
        if key in point_moves:
            dx, dy = point_moves[key]
            delta_key = (round(dx, 6), round(dy, 6))
            delta_groups[delta_key].append(pt_name)

    total_points = sum(len(pts) for pts in delta_groups.values())
    print(f"\n  Points to move: {total_points}")
    print(f"  Unique deltas: {len(delta_groups)}")

    for dk, pts in sorted(delta_groups.items()):
        print(f"    delta=({dk[0]:.4f},{dk[1]:.4f}): {len(pts)} points")

    # ===== STEP 5: Execute moves using select + EditGeneral.Move =====
    if total_points == 0:
        print("\n  No points to move!")
        return

    print(f"\n[STEP 5] Moving {total_points} points in {len(delta_groups)} batches...")

    total_moved = 0
    total_errors = 0

    for (dx, dy), pt_list in delta_groups.items():
        print(f"\n  Batch: delta=({dx:.4f},{dy:.4f}), {len(pt_list)} points")

        # Clear selection
        SapModel.SelectObj.ClearSelection()

        # Select all points in this batch
        selected = 0
        for pt_name in pt_list:
            try:
                ret = SapModel.PointObj.SetSelected(pt_name, True)
                if ret == 0:
                    selected += 1
            except:
                pass

        print(f"    Selected: {selected}/{len(pt_list)} points")

        if selected == 0:
            continue

        # Move selected objects
        try:
            ret = SapModel.EditGeneral.Move(dx, dy, 0)
            if ret == 0:
                print(f"    Move successful")
                total_moved += selected
            else:
                print(f"    Move returned: {ret}")
                total_errors += selected
        except Exception as e:
            print(f"    Move error: {e}")
            total_errors += selected

    # Clear selection
    SapModel.SelectObj.ClearSelection()

    print(f"\n  Total moved: {total_moved}")
    print(f"  Total errors: {total_errors}")

    # ===== STEP 6: Verify connectivity =====
    print("\n[STEP 6] Verifying connectivity after moves...")

    SapModel.View.RefreshView(0, False)

    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [],
        [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])

    num_frames = ret[0]
    new_cols_1f = []
    new_cols_1mf = []

    for i in range(num_frames):
        dx = abs(ret[6][i] - ret[9][i])
        dy = abs(ret[7][i] - ret[10][i])
        if dx < 0.01 and dy < 0.01 and abs(ret[8][i] - ret[11][i]) > 0.5:
            x = (ret[6][i] + ret[9][i]) / 2
            y = (ret[7][i] + ret[10][i]) / 2
            story = ret[3][i]
            pt1 = ret[4][i]
            pt2 = ret[5][i]
            if story == '1F':
                new_cols_1f.append({'x': x, 'y': y, 'name': ret[1][i], 'pt2': pt2})
            elif story == '1MF':
                new_cols_1mf.append({'x': x, 'y': y, 'name': ret[1][i], 'pt1': pt1})

    connected_after = 0
    shared_point = 0
    for c1 in new_cols_1f:
        for c2 in new_cols_1mf:
            if abs(c1['x'] - c2['x']) < TOL and abs(c1['y'] - c2['y']) < TOL:
                connected_after += 1
                if c1.get('pt2') == c2.get('pt1'):
                    shared_point += 1
                break

    print(f"  1F columns: {len(new_cols_1f)}")
    print(f"  1MF columns: {len(new_cols_1mf)}")
    print(f"  Connected 1F-1MF pairs: {connected_after}")
    print(f"  Shared endpoint (fully connected): {shared_point}")
    print(f"\n  BEFORE: 15 connected out of 65 1F cols")
    print(f"  AFTER:  {connected_after} connected out of {len(new_cols_1f)} 1F cols")

    # ===== STEP 7: Save =====
    output = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v5.EDB'
    SapModel.File.Save(output)
    print(f"\nSaved to: {output}")

    # Save report
    report = {
        'matched_direct': len(matched_direct),
        'matched_move': len(matched_move),
        'total_points_moved': total_moved,
        'total_errors': total_errors,
        'connected_before': 15,
        'connected_after': connected_after,
        'shared_point_after': shared_point,
        'unmatched_1f_remaining': len(unmatched_1f),
        'unmatched_1mf_remaining': len(still_unmatched_1mf),
    }
    report_path = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\scripts\agent_reports\fix_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Report saved to: {report_path}")

if __name__ == '__main__':
    main()
