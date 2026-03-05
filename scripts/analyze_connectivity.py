"""
Analyze column connectivity between OLD substructure and A/B/C/D superstructure.
Compares:
1. OLD column positions at 1F level (top) with A/B/C/D column positions at 1MF (bottom)
2. Section definitions in each building vs merged e2k
3. Grid coordinate differences between buildings
"""
import re
import json
from collections import defaultdict

def parse_e2k_full(filepath, unit_scale=1.0):
    """Parse e2k file, extracting points, lines, lineassigns, sections, grids."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    lines = content.split('\n')

    data = {
        'points': {},        # name -> (x_m, y_m)
        'columns': {},       # name -> point_name
        'lineassigns': {},   # name -> {story: section}
        'sections': {},      # name -> {mat, shape, D, B, ...}
        'grids_x': {},       # label -> coord_m
        'grids_y': {},       # label -> coord_m
    }

    for line in lines:
        # Points
        m = re.match(r'\s+POINT\s+"([^"]+)"\s+([\d.\-E+]+)\s+([\d.\-E+]+)', line)
        if m:
            data['points'][m.group(1)] = (
                float(m.group(2)) * unit_scale,
                float(m.group(3)) * unit_scale
            )
            continue

        # Column lines
        m = re.match(r'\s+LINE\s+"([^"]+)"\s+COLUMN\s+"([^"]+)"\s+"([^"]+)"\s+(\d+)', line)
        if m:
            data['columns'][m.group(1)] = m.group(2)
            continue

        # Line assigns
        m = re.match(r'\s+LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"(.*)', line)
        if m:
            name = m.group(1)
            story = m.group(2)
            section = m.group(3)
            if name not in data['lineassigns']:
                data['lineassigns'][name] = {}
            data['lineassigns'][name][story] = section
            continue

        # Frame sections
        m = re.match(r'\s+FRAMESECTION\s+"([^"]+)"(.*)', line)
        if m:
            sec_name = m.group(1)
            rest = m.group(2)
            sec_info = {'raw': rest.strip()}

            mm = re.search(r'MATERIAL\s+"([^"]+)"', rest)
            if mm: sec_info['material'] = mm.group(1)

            mm = re.search(r'SHAPE\s+"([^"]+)"', rest)
            if mm: sec_info['shape'] = mm.group(1)

            mm = re.search(r'\bD\s+([\d.\-E+]+)', rest)
            if mm: sec_info['D'] = float(mm.group(1)) * unit_scale

            mm = re.search(r'\bB\s+([\d.\-E+]+)', rest)
            if mm: sec_info['B'] = float(mm.group(1)) * unit_scale

            data['sections'][sec_name] = sec_info
            continue

        # Grids
        m = re.match(r'\s+GRID\s+"([^"]+)"\s+LABEL\s+"([^"]+)"\s+DIR\s+"([^"]+)"\s+COORD\s+([\d.\-E+]+)', line)
        if m:
            label = m.group(2)
            direction = m.group(3)
            coord = float(m.group(4)) * unit_scale
            if direction == 'X':
                data['grids_x'][label] = coord
            elif direction == 'Y':
                data['grids_y'][label] = coord
            continue

    return data

def get_column_positions(data, story_filter=None):
    """Get column XY positions at a specific story (or all if None)."""
    positions = {}  # col_name -> (x, y, section)
    for col_name, pt_name in data['columns'].items():
        if pt_name in data['points']:
            x, y = data['points'][pt_name]
            assigns = data['lineassigns'].get(col_name, {})
            if story_filter:
                if story_filter in assigns:
                    positions[col_name] = (x, y, assigns[story_filter])
            else:
                # Return with all story assignments
                positions[col_name] = (x, y, assigns)
    return positions

def main():
    print("=" * 70)
    print("COLUMN CONNECTIVITY & SECTION ANALYSIS")
    print("=" * 70)

    # Parse all e2k files
    print("\n[1] Parsing e2k files...")

    old = parse_e2k_full(
        r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\OLD\2025-1111_ALL_BUT RC_KpKvKw.e2k',
        unit_scale=1.0  # TON/M
    )
    print(f"  OLD: {len(old['points'])} points, {len(old['columns'])} columns, {len(old['sections'])} sections")

    bldg_a = parse_e2k_full(
        r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\A\2026-0303_A_SC_KpKvKw.e2k',
        unit_scale=0.01  # KGF/CM -> M
    )
    print(f"  A: {len(bldg_a['points'])} points, {len(bldg_a['columns'])} columns, {len(bldg_a['sections'])} sections")

    bldg_b = parse_e2k_full(
        r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\B\2026-0303_B_SC_KpKvKw.e2k',
        unit_scale=1.0  # TON/M
    )
    print(f"  B: {len(bldg_b['points'])} points, {len(bldg_b['columns'])} columns, {len(bldg_b['sections'])} sections")

    bldg_c = parse_e2k_full(
        r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\C\2026-0304_C_SC_KpKvKw.e2k',
        unit_scale=0.01  # KGF/CM -> M
    )
    print(f"  C: {len(bldg_c['points'])} points, {len(bldg_c['columns'])} columns, {len(bldg_c['sections'])} sections")

    bldg_d = parse_e2k_full(
        r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\D\2026-0303_D_SC_KpKvKw.e2k',
        unit_scale=0.01  # KGF/CM -> M
    )
    print(f"  D: {len(bldg_d['points'])} points, {len(bldg_d['columns'])} columns, {len(bldg_d['sections'])} sections")

    merged = parse_e2k_full(
        r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_ALL_v2.e2k',
        unit_scale=1.0  # TON/M (already merged)
    )
    print(f"  MERGED: {len(merged['points'])} points, {len(merged['columns'])} columns, {len(merged['sections'])} sections")

    # ===== GRID COMPARISON =====
    print("\n" + "=" * 70)
    print("[2] GRID COORDINATE COMPARISON")
    print("=" * 70)

    report_grids = []
    for label in sorted(set(list(old['grids_x'].keys()) + list(bldg_a['grids_x'].keys()))):
        old_val = old['grids_x'].get(label)
        a_val = bldg_a['grids_x'].get(label)
        b_val = bldg_b['grids_x'].get(label)
        c_val = bldg_c['grids_x'].get(label)
        d_val = bldg_d['grids_x'].get(label)
        merged_val = merged['grids_x'].get(label)

        values = [old_val, a_val, b_val, c_val, d_val, merged_val]
        non_none = [v for v in values if v is not None]

        if non_none:
            max_diff = max(non_none) - min(non_none)
            if max_diff > 0.005:  # > 5mm difference
                print(f"\n  X Grid '{label}' MISMATCH (max diff: {max_diff:.4f} m):")
                print(f"    OLD:    {old_val}")
                print(f"    A:      {a_val}")
                print(f"    B:      {b_val}")
                print(f"    C:      {c_val}")
                print(f"    D:      {d_val}")
                print(f"    MERGED: {merged_val}")
                report_grids.append({
                    'dir': 'X', 'label': label, 'max_diff': max_diff,
                    'OLD': old_val, 'A': a_val, 'B': b_val, 'C': c_val, 'D': d_val, 'MERGED': merged_val
                })

    for label in sorted(set(list(old['grids_y'].keys()) + list(bldg_a['grids_y'].keys()))):
        old_val = old['grids_y'].get(label)
        a_val = bldg_a['grids_y'].get(label)
        b_val = bldg_b['grids_y'].get(label)
        c_val = bldg_c['grids_y'].get(label)
        d_val = bldg_d['grids_y'].get(label)
        merged_val = merged['grids_y'].get(label)

        values = [old_val, a_val, b_val, c_val, d_val, merged_val]
        non_none = [v for v in values if v is not None]

        if non_none:
            max_diff = max(non_none) - min(non_none)
            if max_diff > 0.005:
                print(f"\n  Y Grid '{label}' MISMATCH (max diff: {max_diff:.4f} m):")
                print(f"    OLD:    {old_val}")
                print(f"    A:      {a_val}")
                print(f"    B:      {b_val}")
                print(f"    C:      {c_val}")
                print(f"    D:      {d_val}")
                print(f"    MERGED: {merged_val}")
                report_grids.append({
                    'dir': 'Y', 'label': label, 'max_diff': max_diff,
                    'OLD': old_val, 'A': a_val, 'B': b_val, 'C': c_val, 'D': d_val, 'MERGED': merged_val
                })

    if not report_grids:
        print("  All grids match within 5mm tolerance!")

    # ===== COLUMN CONNECTIVITY =====
    print("\n" + "=" * 70)
    print("[3] COLUMN CONNECTIVITY ANALYSIS")
    print("=" * 70)

    # OLD columns at 1F (top of basement = interface with superstructure)
    old_cols_1f = get_column_positions(old, '1F')
    print(f"\n  OLD columns at 1F: {len(old_cols_1f)}")

    # Get ALL OLD columns with their point positions
    old_col_all = {}
    for col_name, pt_name in old['columns'].items():
        if pt_name in old['points']:
            x, y = old['points'][pt_name]
            old_col_all[col_name] = (x, y)

    # A/B/C/D columns at 1MF and 1F (interface stories)
    buildings = {'A': bldg_a, 'B': bldg_b, 'C': bldg_c, 'D': bldg_d}
    bldg_cols = {}
    for bname, bdata in buildings.items():
        cols_1f = get_column_positions(bdata, '1F')
        cols_1mf = get_column_positions(bdata, '1MF')
        cols_2f = get_column_positions(bdata, '2F')
        bldg_cols[bname] = {
            '1F': cols_1f,
            '1MF': cols_1mf,
            '2F': cols_2f,
        }
        print(f"  Building {bname}: 1F={len(cols_1f)} cols, 1MF={len(cols_1mf)} cols, 2F={len(cols_2f)} cols")

    # Match OLD 1F columns with superstructure columns
    TOLERANCE = 0.02  # 2cm tolerance

    matched = []
    unmatched_old = []

    for old_col, (ox, oy, old_sec) in old_cols_1f.items():
        found = False
        for bname in ['A', 'B', 'C', 'D']:
            # Check 1F columns in this building
            for new_col, (nx, ny, new_sec) in bldg_cols[bname].get('1F', {}).items():
                dx = abs(ox - nx)
                dy = abs(oy - ny)
                if dx < TOLERANCE and dy < TOLERANCE:
                    matched.append({
                        'old_col': old_col, 'old_x': ox, 'old_y': oy, 'old_sec': old_sec,
                        'new_col': new_col, 'new_x': nx, 'new_y': ny, 'new_sec': new_sec,
                        'building': bname, 'dx': dx, 'dy': dy
                    })
                    found = True
                    break
            if found:
                break

        if not found:
            unmatched_old.append({
                'col': old_col, 'x': ox, 'y': oy, 'sec': old_sec
            })

    print(f"\n  Matched: {len(matched)} OLD columns -> superstructure")
    print(f"  Unmatched OLD: {len(unmatched_old)} columns have NO corresponding superstructure column")

    # Check section mismatches among matched columns
    sec_mismatches = [m for m in matched if m['old_sec'] != m['new_sec']]
    print(f"\n  Section mismatches at interface: {len(sec_mismatches)}")
    for sm in sec_mismatches[:20]:
        print(f"    OLD {sm['old_col']} ({sm['old_sec']}) <-> {sm['building']}{sm['new_col']} ({sm['new_sec']})")

    # For unmatched OLD columns, find nearest superstructure column
    print(f"\n  Unmatched OLD columns (nearest superstructure column):")
    for um in unmatched_old[:30]:
        best_dist = 999
        best_col = None
        best_bldg = None
        for bname in ['A', 'B', 'C', 'D']:
            for new_col, (nx, ny, new_sec) in bldg_cols[bname].get('1F', {}).items():
                dist = ((um['x'] - nx)**2 + (um['y'] - ny)**2)**0.5
                if dist < best_dist:
                    best_dist = dist
                    best_col = new_col
                    best_bldg = bname

        print(f"    OLD {um['col']} ({um['x']:.3f},{um['y']:.3f}) sec={um['sec']}")
        if best_col:
            print(f"      Nearest: {best_bldg}-{best_col} dist={best_dist:.4f}m")

    # ===== SECTION COMPARISON =====
    print("\n" + "=" * 70)
    print("[4] SECTION DEFINITION COMPARISON")
    print("=" * 70)

    # Compare sections that appear in merged with original buildings
    # Focus on column sections (C pattern)
    col_sec_pattern = re.compile(r'^(C|SRC)\d+X\d+')

    print("\n  Comparing column section dimensions (original building vs merged e2k):")
    sec_issues = []

    for sec_name in sorted(merged['sections'].keys()):
        if not col_sec_pattern.match(sec_name):
            continue

        merged_sec = merged['sections'][sec_name]
        merged_d = merged_sec.get('D')
        merged_b = merged_sec.get('B')

        # Find this section in individual buildings
        for bname, bdata in buildings.items():
            if sec_name in bdata['sections']:
                orig_sec = bdata['sections'][sec_name]
                orig_d = orig_sec.get('D')
                orig_b = orig_sec.get('B')

                if orig_d is not None and merged_d is not None:
                    if abs(orig_d - merged_d) > 0.005 or abs(orig_b - merged_b) > 0.005:
                        issue = f"  {sec_name}: {bname} has D={orig_d:.4f} B={orig_b:.4f}, MERGED has D={merged_d:.4f} B={merged_b:.4f}"
                        print(issue)
                        sec_issues.append({
                            'section': sec_name,
                            'building': bname,
                            'orig_D': orig_d, 'orig_B': orig_b,
                            'merged_D': merged_d, 'merged_B': merged_b,
                            'material': orig_sec.get('material', '')
                        })

    if not sec_issues:
        print("  All column sections match between buildings and merged e2k!")

    # Check what rebuild_model_v5.py might have created wrong
    print("\n  Checking sections in rebuild_model_v5.py parse patterns:")
    rebuild_pattern_issues = []
    for sec_name, sec_info in merged['sections'].items():
        merged_d = sec_info.get('D')
        merged_b = sec_info.get('B')
        if merged_d is None or merged_b is None:
            continue

        # Check CnnnXnnn pattern parsing
        m = re.match(r'C(\d+)X(\d+)', sec_name)
        if m:
            # rebuild_model_v5.py converts cm to m: /100
            # But merged e2k already has meters
            parsed_d = float(m.group(1)) / 100
            parsed_b = float(m.group(2)) / 100
            if abs(parsed_d - merged_d) > 0.005 or abs(parsed_b - merged_b) > 0.005:
                rebuild_pattern_issues.append({
                    'section': sec_name,
                    'parsed_D': parsed_d, 'parsed_B': parsed_b,
                    'actual_D': merged_d, 'actual_B': merged_b
                })

    if rebuild_pattern_issues:
        print(f"\n  REBUILD PATTERN ISSUES ({len(rebuild_pattern_issues)}):")
        for ri in rebuild_pattern_issues[:20]:
            print(f"    {ri['section']}: parsed D={ri['parsed_D']:.3f} B={ri['parsed_B']:.3f}, actual D={ri['actual_D']:.3f} B={ri['actual_B']:.3f}")
    else:
        print("  No rebuild pattern issues found.")

    # ===== SECTIONS IN OLD BUT NOT IN BUILDINGS =====
    print("\n" + "=" * 70)
    print("[5] SECTIONS USED IN OLD BUT NOT DEFINED IN ANY BUILDING")
    print("=" * 70)

    old_used_sections = set()
    for col_name, assigns in old['lineassigns'].items():
        for story, sec in assigns.items():
            old_used_sections.add(sec)

    all_bldg_sections = set()
    for bdata in buildings.values():
        all_bldg_sections.update(bdata['sections'].keys())

    old_only = old_used_sections - all_bldg_sections
    if old_only:
        print(f"  Sections only in OLD ({len(old_only)}):")
        for s in sorted(old_only):
            print(f"    {s}")

    # ===== SUMMARY REPORT =====
    print("\n" + "=" * 70)
    print("[6] SUMMARY")
    print("=" * 70)

    report = {
        'grid_mismatches': report_grids,
        'matched_columns': len(matched),
        'unmatched_old_columns': len(unmatched_old),
        'section_mismatches': sec_mismatches[:50],
        'unmatched_details': unmatched_old[:50],
        'rebuild_pattern_issues': rebuild_pattern_issues,
        'section_comparison_issues': sec_issues
    }

    report_path = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\scripts\agent_reports\connectivity_analysis.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Detailed report saved to: {report_path}")

    print(f"\n  Grid mismatches: {len(report_grids)}")
    print(f"  Column connectivity: {len(matched)} matched, {len(unmatched_old)} unmatched")
    print(f"  Section mismatches at interface: {len(sec_mismatches)}")
    print(f"  Section definition issues: {len(sec_issues)}")
    print(f"  Rebuild pattern issues: {len(rebuild_pattern_issues)}")

if __name__ == '__main__':
    main()
