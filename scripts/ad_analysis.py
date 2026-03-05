"""
Agent 1: Buildings A & D Analysis Script
Parses A, D, and OLD e2k files. Compares grids, sections, and column connectivity.
Outputs findings to agent_reports/ad_analysis.md
"""
import re
import os
from collections import defaultdict

# ============================================================
# File paths
# ============================================================
A_E2K = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\A\2026-0303_A_SC_KpKvKw.e2k"
D_E2K = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\D\2026-0303_D_SC_KpKvKw.e2k"
OLD_E2K = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\OLD\2025-1111_ALL_BUT RC_KpKvKw.e2k"
REPORT_PATH = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\scripts\agent_reports\ad_analysis.md"

# ============================================================
# Parsing Functions
# ============================================================
def parse_e2k(filepath, units_cm=True):
    """Parse an e2k file and extract key data."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    lines = content.split('\n')

    data = {
        'units': 'KGF/CM' if units_cm else 'TON/M',
        'grids_x': {},     # label -> coord (in meters)
        'grids_y': {},     # label -> coord (in meters)
        'sections': {},    # name -> {material, shape, D, B, ...}
        'points': {},      # name -> (x_m, y_m)
        'columns': {},     # line_name -> point_name
        'beams': {},       # line_name -> (pt_i, pt_j)
        'col_assigns': defaultdict(dict),  # {story: {line_name: section}}
        'beam_assigns': defaultdict(dict), # {story: {line_name: section}}
        'stories': [],     # list of (name, height_m)
    }

    scale = 0.01 if units_cm else 1.0  # convert to meters

    for line in lines:
        line = line.rstrip()

        # ----- GRID -----
        m = re.match(r'\s+GRID\s+"GLOBAL"\s+LABEL\s+"([^"]+)"\s+DIR\s+"([XY])"\s+COORD\s+([\d.\-E+]+)', line)
        if m:
            label, direction, coord = m.group(1), m.group(2), float(m.group(3))
            coord_m = coord * scale
            if direction == 'X':
                data['grids_x'][label] = coord_m
            else:
                data['grids_y'][label] = coord_m
            continue

        # ----- FRAMESECTION -----
        m = re.match(r'\s+FRAMESECTION\s+"([^"]+)"\s+MATERIAL\s+"([^"]+)"\s+SHAPE\s+"([^"]+)"(.*)', line)
        if m:
            sec_name = m.group(1)
            material = m.group(2)
            shape = m.group(3)
            rest = m.group(4)
            sec_data = {'material': material, 'shape': shape}
            # Extract D and B values
            d_match = re.search(r'\bD\s+([\d.\-E+]+)', rest)
            b_match = re.search(r'\bB\s+([\d.\-E+]+)', rest)
            if d_match:
                sec_data['D'] = float(d_match.group(1))
            if b_match:
                sec_data['B'] = float(b_match.group(1))
            data['sections'][sec_name] = sec_data
            continue

        # ----- FRAMESECTION (General shape, no SHAPE "..." but has D/B) -----
        m2 = re.match(r'\s+FRAMESECTION\s+"([^"]+)"\s+MATERIAL\s+"([^"]+)"\s+SHAPE\s+"General"\s+(.*)', line)
        if m2 and m2.group(1) not in data['sections']:
            sec_name = m2.group(1)
            material = m2.group(2)
            rest = m2.group(3)
            sec_data = {'material': material, 'shape': 'General'}
            d_match = re.search(r'\bD\s+([\d.\-E+]+)', rest)
            b_match = re.search(r'\bB\s+([\d.\-E+]+)', rest)
            if d_match:
                sec_data['D'] = float(d_match.group(1))
            if b_match:
                sec_data['B'] = float(b_match.group(1))
            data['sections'][sec_name] = sec_data
            continue

        # ----- POINT -----
        m = re.match(r'\s+POINT\s+"([^"]+)"\s+([\d.\-E+]+)\s+([\d.\-E+]+)', line)
        if m:
            pt_name = m.group(1)
            x = float(m.group(2)) * scale
            y = float(m.group(3)) * scale
            data['points'][pt_name] = (x, y)
            continue

        # ----- LINE (COLUMN) -----
        m = re.match(r'\s+LINE\s+"([^"]+)"\s+COLUMN\s+"([^"]+)"\s+"([^"]+)"\s+(\d+)', line)
        if m:
            line_name = m.group(1)
            pt_i = m.group(2)
            data['columns'][line_name] = pt_i
            continue

        # ----- LINE (BEAM) -----
        m = re.match(r'\s+LINE\s+"([^"]+)"\s+BEAM\s+"([^"]+)"\s+"([^"]+)"\s+(\d+)', line)
        if m:
            line_name = m.group(1)
            pt_i = m.group(2)
            pt_j = m.group(3)
            data['beams'][line_name] = (pt_i, pt_j)
            continue

        # ----- LINEASSIGN -----
        m = re.match(r'\s+LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"', line)
        if m:
            line_name = m.group(1)
            story = m.group(2)
            section = m.group(3)
            if line_name.startswith('C') and line_name[1:].isdigit():
                data['col_assigns'][story][line_name] = section
            elif line_name.startswith('B') and line_name[1:].isdigit():
                data['beam_assigns'][story][line_name] = section
            continue

        # ----- STORY -----
        m = re.match(r'\s+STORY\s+"([^"]+)"\s+HEIGHT\s+([\d.\-E+]+)', line)
        if m:
            story_name = m.group(1)
            height = float(m.group(2)) * scale
            data['stories'].append((story_name, height))
            continue

        # ----- STORY with ELEV -----
        m = re.match(r'\s+STORY\s+"([^"]+)"\s+ELEV\s+([\d.\-E+]+)', line)
        if m:
            story_name = m.group(1)
            # BASE elevation
            data['stories'].append((story_name, float(m.group(2)) * scale))
            continue

    return data


def compare_grids(data_a, data_b, label_a, label_b, tolerance_m=0.01):
    """Compare grids between two models. Returns list of differences."""
    diffs = []

    all_labels_x = set(data_a['grids_x'].keys()) | set(data_b['grids_x'].keys())
    for label in sorted(all_labels_x):
        coord_a = data_a['grids_x'].get(label)
        coord_b = data_b['grids_x'].get(label)
        if coord_a is None:
            diffs.append(f"  X-Grid '{label}': MISSING in {label_a}, present in {label_b} at {coord_b:.4f}m")
        elif coord_b is None:
            diffs.append(f"  X-Grid '{label}': present in {label_a} at {coord_a:.4f}m, MISSING in {label_b}")
        elif abs(coord_a - coord_b) > tolerance_m:
            diffs.append(f"  X-Grid '{label}': {label_a}={coord_a:.4f}m vs {label_b}={coord_b:.4f}m (diff={abs(coord_a-coord_b):.4f}m)")

    all_labels_y = set(data_a['grids_y'].keys()) | set(data_b['grids_y'].keys())
    for label in sorted(all_labels_y, key=lambda x: (len(x), x)):
        coord_a = data_a['grids_y'].get(label)
        coord_b = data_b['grids_y'].get(label)
        if coord_a is None:
            diffs.append(f"  Y-Grid '{label}': MISSING in {label_a}, present in {label_b} at {coord_b:.4f}m")
        elif coord_b is None:
            diffs.append(f"  Y-Grid '{label}': present in {label_a} at {coord_a:.4f}m, MISSING in {label_b}")
        elif abs(coord_a - coord_b) > tolerance_m:
            diffs.append(f"  Y-Grid '{label}': {label_a}={coord_a:.4f}m vs {label_b}={coord_b:.4f}m (diff={abs(coord_a-coord_b):.4f}m)")

    return diffs


def section_dims_in_m(sec_data, units_cm):
    """Get D and B in meters."""
    d = sec_data.get('D', 0)
    b = sec_data.get('B', 0)
    if units_cm:
        return d * 0.01, b * 0.01
    else:
        return d, b


def get_section_name_dims(sec_name):
    """Try to extract expected dimensions from section name pattern CxxxXxxxC...
    Returns (D_cm, B_cm) or None if not matching.
    Pattern: C{depth}X{width}... where depth/width are in cm
    """
    m = re.match(r'C(\d+)X(\d+)', sec_name)
    if m:
        return int(m.group(1)), int(m.group(2))

    # SRC sections
    m = re.match(r'SRC(\d+)X(\d+)', sec_name)
    if m:
        return int(m.group(1)), int(m.group(2))

    return None


def main():
    print("=" * 70)
    print("Agent 1: Buildings A & D Analysis")
    print("=" * 70)

    # ============================================================
    # 1. Parse all e2k files
    # ============================================================
    print("\n[1] Parsing Building A e2k...")
    data_a = parse_e2k(A_E2K, units_cm=True)
    print(f"    Points: {len(data_a['points'])}, Columns: {len(data_a['columns'])}, "
          f"Beams: {len(data_a['beams'])}, Sections: {len(data_a['sections'])}")
    print(f"    X-Grids: {len(data_a['grids_x'])}, Y-Grids: {len(data_a['grids_y'])}")
    print(f"    Column assignment stories: {sorted(data_a['col_assigns'].keys())}")

    print("\n[2] Parsing Building D e2k...")
    data_d = parse_e2k(D_E2K, units_cm=True)
    print(f"    Points: {len(data_d['points'])}, Columns: {len(data_d['columns'])}, "
          f"Beams: {len(data_d['beams'])}, Sections: {len(data_d['sections'])}")
    print(f"    X-Grids: {len(data_d['grids_x'])}, Y-Grids: {len(data_d['grids_y'])}")
    print(f"    Column assignment stories: {sorted(data_d['col_assigns'].keys())}")

    print("\n[3] Parsing OLD model e2k...")
    data_old = parse_e2k(OLD_E2K, units_cm=False)
    print(f"    Points: {len(data_old['points'])}, Columns: {len(data_old['columns'])}, "
          f"Beams: {len(data_old['beams'])}, Sections: {len(data_old['sections'])}")
    print(f"    X-Grids: {len(data_old['grids_x'])}, Y-Grids: {len(data_old['grids_y'])}")
    print(f"    Column assignment stories: {sorted(data_old['col_assigns'].keys())}")

    # ============================================================
    # 2. Grid Comparisons
    # ============================================================
    print("\n[4] Comparing grids...")
    a_vs_old = compare_grids(data_a, data_old, "A", "OLD")
    d_vs_old = compare_grids(data_d, data_old, "D", "OLD")
    a_vs_d = compare_grids(data_a, data_d, "A", "D")

    print(f"    A vs OLD: {len(a_vs_old)} differences")
    for d in a_vs_old[:10]:
        print(f"    {d}")
    print(f"    D vs OLD: {len(d_vs_old)} differences")
    for d in d_vs_old[:10]:
        print(f"    {d}")
    print(f"    A vs D: {len(a_vs_d)} differences")
    for d in a_vs_d[:10]:
        print(f"    {d}")

    # ============================================================
    # 3. Section Definition Analysis
    # ============================================================
    print("\n[5] Analyzing section definitions...")

    # Separate column sections vs beam sections
    def classify_sections(sections, units_cm):
        col_secs = {}
        beam_secs = {}
        src_secs = {}
        general_secs = {}
        other_secs = {}
        for name, sec in sections.items():
            if sec['shape'] == 'General':
                general_secs[name] = sec
            elif name.startswith('SRC') or name.startswith('SRB'):
                src_secs[name] = sec
            elif name.startswith('C') and 'X' in name:
                col_secs[name] = sec
            elif name.startswith('B') or name.startswith('WB') or name.startswith('FB') or name.startswith('FWB') or name.startswith('FSB') or name.startswith('SB') or name.startswith('AB') or name.startswith('ABH') or name.startswith('ASB'):
                beam_secs[name] = sec
            else:
                other_secs[name] = sec
        return col_secs, beam_secs, src_secs, general_secs, other_secs

    a_col, a_beam, a_src, a_gen, a_other = classify_sections(data_a['sections'], True)
    d_col, d_beam, d_src, d_gen, d_other = classify_sections(data_d['sections'], True)
    old_col, old_beam, old_src, old_gen, old_other = classify_sections(data_old['sections'], False)

    print(f"    Building A: {len(a_col)} col, {len(a_beam)} beam, {len(a_src)} SRC, {len(a_gen)} general, {len(a_other)} other")
    print(f"    Building D: {len(d_col)} col, {len(d_beam)} beam, {len(d_src)} SRC, {len(d_gen)} general, {len(d_other)} other")
    print(f"    OLD model: {len(old_col)} col, {len(old_beam)} beam, {len(old_src)} SRC, {len(old_gen)} general, {len(old_other)} other")

    # Check section name-vs-dimension consistency for A
    print("\n    Checking A section name vs actual dimensions (units: CM)...")
    a_dim_mismatches = []
    for name, sec in data_a['sections'].items():
        expected = get_section_name_dims(name)
        if expected and sec['shape'] == 'Rectangular':
            exp_d, exp_b = expected
            act_d = sec.get('D', 0)
            act_b = sec.get('B', 0)
            if abs(act_d - exp_d) > 0.5 or abs(act_b - exp_b) > 0.5:
                a_dim_mismatches.append((name, exp_d, exp_b, act_d, act_b))

    if a_dim_mismatches:
        print(f"    FOUND {len(a_dim_mismatches)} dimension mismatches in A:")
        for name, ed, eb, ad, ab in a_dim_mismatches[:10]:
            print(f"      {name}: expected D={ed} B={eb} cm, actual D={ad} B={ab} cm")
    else:
        print(f"    All A Rectangular section names match their D/B values")

    # Check section name-vs-dimension consistency for D
    print("\n    Checking D section name vs actual dimensions (units: CM)...")
    d_dim_mismatches = []
    for name, sec in data_d['sections'].items():
        expected = get_section_name_dims(name)
        if expected and sec['shape'] == 'Rectangular':
            exp_d, exp_b = expected
            act_d = sec.get('D', 0)
            act_b = sec.get('B', 0)
            if abs(act_d - exp_d) > 0.5 or abs(act_b - exp_b) > 0.5:
                d_dim_mismatches.append((name, exp_d, exp_b, act_d, act_b))

    if d_dim_mismatches:
        print(f"    FOUND {len(d_dim_mismatches)} dimension mismatches in D:")
        for name, ed, eb, ad, ab in d_dim_mismatches[:10]:
            print(f"      {name}: expected D={ed} B={eb} cm, actual D={ad} B={ab} cm")
    else:
        print(f"    All D Rectangular section names match their D/B values")

    # Check OLD sections (units: M, so expected dims from name are in cm, actual in m)
    print("\n    Checking OLD section name vs actual dimensions (units: M)...")
    old_dim_mismatches = []
    for name, sec in data_old['sections'].items():
        expected = get_section_name_dims(name)
        if expected and sec['shape'] == 'Rectangular':
            exp_d_cm, exp_b_cm = expected
            act_d_m = sec.get('D', 0)
            act_b_m = sec.get('B', 0)
            exp_d_m = exp_d_cm / 100.0
            exp_b_m = exp_b_cm / 100.0
            if abs(act_d_m - exp_d_m) > 0.005 or abs(act_b_m - exp_b_m) > 0.005:
                old_dim_mismatches.append((name, exp_d_cm, exp_b_cm, act_d_m * 100, act_b_m * 100))

    if old_dim_mismatches:
        print(f"    FOUND {len(old_dim_mismatches)} dimension mismatches in OLD:")
        for name, ed, eb, ad, ab in old_dim_mismatches[:10]:
            print(f"      {name}: expected D={ed} B={eb} cm, actual D={ad:.1f} B={ab:.1f} cm")
    else:
        print(f"    All OLD Rectangular section names match their D/B values")

    # Sections unique to A but not in OLD
    a_sec_names = set(data_a['sections'].keys())
    d_sec_names = set(data_d['sections'].keys())
    old_sec_names = set(data_old['sections'].keys())

    a_only = a_sec_names - old_sec_names
    d_only = d_sec_names - old_sec_names
    old_only = old_sec_names - a_sec_names - d_sec_names

    print(f"\n    Sections in A but NOT in OLD: {len(a_only)}")
    print(f"    Sections in D but NOT in OLD: {len(d_only)}")
    print(f"    Sections in OLD but NOT in A or D: {len(old_only)}")

    # Compare section dimensions between A and D for shared sections
    shared_ad = a_sec_names & d_sec_names
    ad_dim_diffs = []
    for name in sorted(shared_ad):
        sec_a = data_a['sections'][name]
        sec_d = data_d['sections'][name]
        if sec_a.get('D') != sec_d.get('D') or sec_a.get('B') != sec_d.get('B'):
            ad_dim_diffs.append((name, sec_a, sec_d))

    print(f"\n    Sections shared by A and D with DIFFERENT dimensions: {len(ad_dim_diffs)}")
    for name, sa, sd in ad_dim_diffs[:10]:
        print(f"      {name}: A(D={sa.get('D')}, B={sa.get('B')}) vs D(D={sd.get('D')}, B={sd.get('B')})")

    # Compare section dimensions between A/D and OLD for shared sections
    shared_a_old = a_sec_names & old_sec_names
    a_old_dim_diffs = []
    for name in sorted(shared_a_old):
        sec_a = data_a['sections'][name]
        sec_old = data_old['sections'][name]
        # A is in cm, OLD is in m
        a_d = sec_a.get('D', 0)
        a_b = sec_a.get('B', 0)
        old_d = sec_old.get('D', 0) * 100  # convert m to cm
        old_b = sec_old.get('B', 0) * 100
        if abs(a_d - old_d) > 0.5 or abs(a_b - old_b) > 0.5:
            a_old_dim_diffs.append((name, a_d, a_b, old_d, old_b))

    print(f"\n    Sections shared by A and OLD with DIFFERENT dimensions: {len(a_old_dim_diffs)}")
    for name, ad, ab, od, ob in a_old_dim_diffs[:10]:
        print(f"      {name}: A(D={ad}, B={ab}cm) vs OLD(D={od:.1f}, B={ob:.1f}cm)")

    # ============================================================
    # 4. Column Connectivity Analysis
    # ============================================================
    print("\n[6] Column connectivity analysis...")

    # The key question: columns at 1MF/1F levels in buildings A and D
    # should match column positions in OLD model at the same levels.
    # All three e2k files share the SAME column line names (C24, C25, etc.)
    # and the SAME point names (7359, 7360, etc.)

    # Check: do A, D, and OLD share the same column definitions?
    a_col_names = set(data_a['columns'].keys())
    d_col_names = set(data_d['columns'].keys())
    old_col_names = set(data_old['columns'].keys())

    print(f"    Column line names: A={len(a_col_names)}, D={len(d_col_names)}, OLD={len(old_col_names)}")
    print(f"    Common to all three: {len(a_col_names & d_col_names & old_col_names)}")
    print(f"    In A but not OLD: {len(a_col_names - old_col_names)}")
    print(f"    In D but not OLD: {len(d_col_names - old_col_names)}")
    print(f"    In OLD but not A: {len(old_col_names - a_col_names)}")
    print(f"    In OLD but not D: {len(old_col_names - d_col_names)}")

    # Check point coordinates match between A/D and OLD for columns
    print("\n    Checking column point coordinate alignment...")
    a_col_coord_diffs = []
    d_col_coord_diffs = []

    for col_name in sorted(a_col_names & old_col_names):
        pt_a = data_a['columns'][col_name]
        pt_old = data_old['columns'][col_name]
        if pt_a in data_a['points'] and pt_old in data_old['points']:
            xa, ya = data_a['points'][pt_a]
            xo, yo = data_old['points'][pt_old]
            dx = abs(xa - xo)
            dy = abs(ya - yo)
            if dx > 0.01 or dy > 0.01:  # 1cm tolerance
                a_col_coord_diffs.append((col_name, pt_a, xa, ya, pt_old, xo, yo, dx, dy))

    for col_name in sorted(d_col_names & old_col_names):
        pt_d = data_d['columns'][col_name]
        pt_old = data_old['columns'][col_name]
        if pt_d in data_d['points'] and pt_old in data_old['points']:
            xd, yd = data_d['points'][pt_d]
            xo, yo = data_old['points'][pt_old]
            dx = abs(xd - xo)
            dy = abs(yd - yo)
            if dx > 0.01 or dy > 0.01:
                d_col_coord_diffs.append((col_name, pt_d, xd, yd, pt_old, xo, yo, dx, dy))

    print(f"    A vs OLD column coordinate mismatches (>1cm): {len(a_col_coord_diffs)}")
    for item in a_col_coord_diffs[:10]:
        col_name, pt_a, xa, ya, pt_old, xo, yo, dx, dy = item
        print(f"      {col_name}: A pt{pt_a}({xa:.4f},{ya:.4f}) vs OLD pt{pt_old}({xo:.4f},{yo:.4f}) dx={dx:.4f}m dy={dy:.4f}m")

    print(f"    D vs OLD column coordinate mismatches (>1cm): {len(d_col_coord_diffs)}")
    for item in d_col_coord_diffs[:10]:
        col_name, pt_d, xd, yd, pt_old, xo, yo, dx, dy = item
        print(f"      {col_name}: D pt{pt_d}({xd:.4f},{yd:.4f}) vs OLD pt{pt_old}({xo:.4f},{yo:.4f}) dx={dx:.4f}m dy={dy:.4f}m")

    # ============================================================
    # 5. Column Section Assignments at Key Stories
    # ============================================================
    print("\n[7] Column section assignments at transition stories...")

    key_stories = ['B1F', '1F', '1MF', '2F', '3F']
    for story in key_stories:
        a_assigns = data_a['col_assigns'].get(story, {})
        d_assigns = data_d['col_assigns'].get(story, {})
        old_assigns = data_old['col_assigns'].get(story, {})
        print(f"\n    Story {story}: A={len(a_assigns)} cols, D={len(d_assigns)} cols, OLD={len(old_assigns)} cols")

        # Compare A vs OLD at this story
        if a_assigns and old_assigns:
            common = set(a_assigns.keys()) & set(old_assigns.keys())
            diffs = [(c, a_assigns[c], old_assigns[c]) for c in sorted(common) if a_assigns[c] != old_assigns[c]]
            if diffs:
                print(f"      A vs OLD section differences ({len(diffs)}):")
                for c, sa, so in diffs[:5]:
                    print(f"        {c}: A='{sa}' vs OLD='{so}'")

        # Compare D vs OLD at this story
        if d_assigns and old_assigns:
            common = set(d_assigns.keys()) & set(old_assigns.keys())
            diffs = [(c, d_assigns[c], old_assigns[c]) for c in sorted(common) if d_assigns[c] != old_assigns[c]]
            if diffs:
                print(f"      D vs OLD section differences ({len(diffs)}):")
                for c, sd, so in diffs[:5]:
                    print(f"        {c}: D='{sd}' vs OLD='{so}'")

        # Compare A vs D at this story
        if a_assigns and d_assigns:
            common = set(a_assigns.keys()) & set(d_assigns.keys())
            diffs = [(c, a_assigns[c], d_assigns[c]) for c in sorted(common) if a_assigns[c] != d_assigns[c]]
            if diffs:
                print(f"      A vs D section differences ({len(diffs)}):")
                for c, sa, sd in diffs[:5]:
                    print(f"        {c}: A='{sa}' vs D='{sd}'")

    # ============================================================
    # 6. Identify which columns belong to which building
    # ============================================================
    print("\n[8] Identifying building-specific columns...")

    # Columns that appear in A's LINEASSIGN at above-ground stories but not in D
    a_above_cols = set()
    d_above_cols = set()
    old_basement_cols = set()

    above_stories = ['1F', '1MF', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F',
                     '11F', '12F', '13F', '14F', '15F', '16F', '17F', '18F', '19F', '20F',
                     '21F', '22F', '23F', '24F', '25F', '26F', '27F', '28F', '29F', '30F',
                     '31F', '32F', '33F', '34F', 'R1F', 'R2F', 'R3F', 'PRF']
    basement_stories = ['B6F', 'B5F', 'B4F', 'B3F', 'B2F', 'B1F']

    for story in above_stories:
        for col in data_a['col_assigns'].get(story, {}):
            a_above_cols.add(col)
        for col in data_d['col_assigns'].get(story, {}):
            d_above_cols.add(col)

    for story in basement_stories + ['1F']:
        for col in data_old['col_assigns'].get(story, {}):
            old_basement_cols.add(col)

    a_only_above = a_above_cols - d_above_cols
    d_only_above = d_above_cols - a_above_cols
    shared_above = a_above_cols & d_above_cols

    print(f"    A-only above-ground columns: {len(a_only_above)}")
    print(f"    D-only above-ground columns: {len(d_only_above)}")
    print(f"    Shared above-ground columns: {len(shared_above)}")
    print(f"    OLD basement columns: {len(old_basement_cols)}")

    # Columns in A above-ground that have NO matching OLD basement column
    a_disconnected = a_above_cols - old_basement_cols
    d_disconnected = d_above_cols - old_basement_cols
    print(f"\n    A columns with NO matching OLD basement column: {len(a_disconnected)}")
    if a_disconnected:
        sorted_disc = sorted(a_disconnected, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)
        print(f"      {sorted_disc[:20]}")
    print(f"    D columns with NO matching OLD basement column: {len(d_disconnected)}")
    if d_disconnected:
        sorted_disc = sorted(d_disconnected, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)
        print(f"      {sorted_disc[:20]}")

    # ============================================================
    # 7. Detailed Column Position Table for Connectivity
    # ============================================================
    print("\n[9] Building column position table for 1F level...")

    # For each column assigned at 1F in A or D, get position and compare to OLD
    all_1f_cols = set()
    all_1f_cols.update(data_a['col_assigns'].get('1F', {}).keys())
    all_1f_cols.update(data_d['col_assigns'].get('1F', {}).keys())
    all_1f_cols.update(data_old['col_assigns'].get('1F', {}).keys())

    connectivity_table = []
    for col_name in sorted(all_1f_cols, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0):
        row = {'col': col_name}

        # A position
        if col_name in data_a['columns'] and data_a['columns'][col_name] in data_a['points']:
            pt = data_a['columns'][col_name]
            row['a_x'], row['a_y'] = data_a['points'][pt]
            row['a_sec_1f'] = data_a['col_assigns'].get('1F', {}).get(col_name, '-')
            row['a_sec_1mf'] = data_a['col_assigns'].get('1MF', {}).get(col_name, '-')
        else:
            row['a_x'] = row['a_y'] = None
            row['a_sec_1f'] = row['a_sec_1mf'] = '-'

        # D position
        if col_name in data_d['columns'] and data_d['columns'][col_name] in data_d['points']:
            pt = data_d['columns'][col_name]
            row['d_x'], row['d_y'] = data_d['points'][pt]
            row['d_sec_1f'] = data_d['col_assigns'].get('1F', {}).get(col_name, '-')
            row['d_sec_1mf'] = data_d['col_assigns'].get('1MF', {}).get(col_name, '-')
        else:
            row['d_x'] = row['d_y'] = None
            row['d_sec_1f'] = row['d_sec_1mf'] = '-'

        # OLD position
        if col_name in data_old['columns'] and data_old['columns'][col_name] in data_old['points']:
            pt = data_old['columns'][col_name]
            row['old_x'], row['old_y'] = data_old['points'][pt]
            row['old_sec_1f'] = data_old['col_assigns'].get('1F', {}).get(col_name, '-')
            row['old_sec_b1f'] = data_old['col_assigns'].get('B1F', {}).get(col_name, '-')
        else:
            row['old_x'] = row['old_y'] = None
            row['old_sec_1f'] = row['old_sec_b1f'] = '-'

        connectivity_table.append(row)

    # ============================================================
    # Generate Report
    # ============================================================
    print("\n[10] Generating report...")

    report = []
    report.append("# Agent 1: Buildings A & D Analysis Report\n")
    report.append("## 1. Data Summary\n")
    report.append(f"| Item | Building A | Building D | OLD Model |")
    report.append(f"|------|-----------|-----------|-----------|")
    report.append(f"| Units | KGF/CM | KGF/CM | TON/M |")
    report.append(f"| Points | {len(data_a['points'])} | {len(data_d['points'])} | {len(data_old['points'])} |")
    report.append(f"| Column lines | {len(data_a['columns'])} | {len(data_d['columns'])} | {len(data_old['columns'])} |")
    report.append(f"| Beam lines | {len(data_a['beams'])} | {len(data_d['beams'])} | {len(data_old['beams'])} |")
    report.append(f"| Frame sections | {len(data_a['sections'])} | {len(data_d['sections'])} | {len(data_old['sections'])} |")
    report.append(f"| X-Grids | {len(data_a['grids_x'])} | {len(data_d['grids_x'])} | {len(data_old['grids_x'])} |")
    report.append(f"| Y-Grids | {len(data_a['grids_y'])} | {len(data_d['grids_y'])} | {len(data_old['grids_y'])} |")
    report.append("")

    # Grid comparison
    report.append("## 2. Grid Coordinate Comparison\n")
    report.append("### 2a. A vs OLD (after converting A from CM to M)\n")
    if a_vs_old:
        for d in a_vs_old:
            report.append(d)
    else:
        report.append("  No differences found (within 1cm tolerance)")
    report.append("")

    report.append("### 2b. D vs OLD (after converting D from CM to M)\n")
    if d_vs_old:
        for d in d_vs_old:
            report.append(d)
    else:
        report.append("  No differences found (within 1cm tolerance)")
    report.append("")

    report.append("### 2c. A vs D (both in CM, converted to M)\n")
    if a_vs_d:
        for d in a_vs_d:
            report.append(d)
    else:
        report.append("  No differences found (within 1cm tolerance)")
    report.append("")

    # Section analysis
    report.append("## 3. Section Definition Analysis\n")
    report.append("### 3a. Section Counts by Type\n")
    report.append(f"| Type | Building A | Building D | OLD Model |")
    report.append(f"|------|-----------|-----------|-----------|")
    report.append(f"| Column (CxxxXxxx) | {len(a_col)} | {len(d_col)} | {len(old_col)} |")
    report.append(f"| Beam (B/WB/FB/SB/AB) | {len(a_beam)} | {len(d_beam)} | {len(old_beam)} |")
    report.append(f"| SRC/SRB | {len(a_src)} | {len(d_src)} | {len(old_src)} |")
    report.append(f"| General (SRC box) | {len(a_gen)} | {len(d_gen)} | {len(old_gen)} |")
    report.append(f"| Other | {len(a_other)} | {len(d_other)} | {len(old_other)} |")
    report.append("")

    report.append("### 3b. Section Name vs Actual Dimension Mismatches\n")
    report.append("#### Building A\n")
    if a_dim_mismatches:
        report.append(f"| Section Name | Expected D(cm) | Expected B(cm) | Actual D(cm) | Actual B(cm) |")
        report.append(f"|-------------|----------------|----------------|-------------|-------------|")
        for name, ed, eb, ad, ab in a_dim_mismatches:
            report.append(f"| {name} | {ed} | {eb} | {ad} | {ab} |")
    else:
        report.append("All Rectangular section names match their D/B values.")
    report.append("")

    report.append("#### Building D\n")
    if d_dim_mismatches:
        report.append(f"| Section Name | Expected D(cm) | Expected B(cm) | Actual D(cm) | Actual B(cm) |")
        report.append(f"|-------------|----------------|----------------|-------------|-------------|")
        for name, ed, eb, ad, ab in d_dim_mismatches:
            report.append(f"| {name} | {ed} | {eb} | {ad} | {ab} |")
    else:
        report.append("All Rectangular section names match their D/B values.")
    report.append("")

    report.append("#### OLD Model\n")
    if old_dim_mismatches:
        report.append(f"| Section Name | Expected D(cm) | Expected B(cm) | Actual D(cm) | Actual B(cm) |")
        report.append(f"|-------------|----------------|----------------|-------------|-------------|")
        for name, ed, eb, ad, ab in old_dim_mismatches:
            report.append(f"| {name} | {ed} | {eb} | {ad:.1f} | {ab:.1f} |")
    else:
        report.append("All Rectangular section names match their D/B values.")
    report.append("")

    report.append("### 3c. Sections Unique to Each Model\n")
    report.append(f"\n**Sections in A but NOT in OLD ({len(a_only)}):**\n")
    for s in sorted(a_only):
        sec = data_a['sections'][s]
        d_val = sec.get('D', '?')
        b_val = sec.get('B', '?')
        report.append(f"- `{s}` (shape={sec['shape']}, D={d_val}, B={b_val} cm)")
    report.append("")

    report.append(f"\n**Sections in D but NOT in OLD ({len(d_only)}):**\n")
    for s in sorted(d_only):
        sec = data_d['sections'][s]
        d_val = sec.get('D', '?')
        b_val = sec.get('B', '?')
        report.append(f"- `{s}` (shape={sec['shape']}, D={d_val}, B={b_val} cm)")
    report.append("")

    report.append(f"\n**Sections in OLD but NOT in A or D ({len(old_only)}):**\n")
    for s in sorted(old_only):
        sec = data_old['sections'][s]
        d_val = sec.get('D', '?')
        b_val = sec.get('B', '?')
        report.append(f"- `{s}` (shape={sec['shape']}, D={d_val}, B={b_val} m)")
    report.append("")

    report.append("### 3d. Sections Shared Between A and D with Different Dimensions\n")
    if ad_dim_diffs:
        report.append(f"| Section | A_D(cm) | A_B(cm) | D_D(cm) | D_B(cm) |")
        report.append(f"|---------|---------|---------|---------|---------|")
        for name, sa, sd in ad_dim_diffs:
            report.append(f"| {name} | {sa.get('D','?')} | {sa.get('B','?')} | {sd.get('D','?')} | {sd.get('B','?')} |")
    else:
        report.append("All shared sections have identical dimensions.")
    report.append("")

    report.append("### 3e. Sections Shared Between A and OLD with Different Dimensions (converted to CM)\n")
    if a_old_dim_diffs:
        report.append(f"| Section | A_D(cm) | A_B(cm) | OLD_D(cm) | OLD_B(cm) |")
        report.append(f"|---------|---------|---------|-----------|-----------|")
        for name, ad, ab, od, ob in a_old_dim_diffs:
            report.append(f"| {name} | {ad} | {ab} | {od:.1f} | {ob:.1f} |")
    else:
        report.append("All shared sections have matching dimensions.")
    report.append("")

    # Column connectivity
    report.append("## 4. Column Connectivity Analysis\n")
    report.append("### 4a. Column Line Summary\n")
    report.append(f"| Category | Count |")
    report.append(f"|----------|-------|")
    report.append(f"| Total column lines in A | {len(a_col_names)} |")
    report.append(f"| Total column lines in D | {len(d_col_names)} |")
    report.append(f"| Total column lines in OLD | {len(old_col_names)} |")
    report.append(f"| Common to all three | {len(a_col_names & d_col_names & old_col_names)} |")
    report.append(f"| In A but not OLD | {len(a_col_names - old_col_names)} |")
    report.append(f"| In D but not OLD | {len(d_col_names - old_col_names)} |")
    report.append(f"| In OLD but not A | {len(old_col_names - a_col_names)} |")
    report.append(f"| In OLD but not D | {len(old_col_names - d_col_names)} |")
    report.append("")

    report.append("### 4b. Column Coordinate Mismatches (A vs OLD, >1cm)\n")
    if a_col_coord_diffs:
        report.append(f"| Column | A_X(m) | A_Y(m) | OLD_X(m) | OLD_Y(m) | dX(m) | dY(m) |")
        report.append(f"|--------|--------|--------|----------|----------|-------|-------|")
        for item in a_col_coord_diffs:
            col_name, pt_a, xa, ya, pt_old, xo, yo, dx, dy = item
            report.append(f"| {col_name} | {xa:.4f} | {ya:.4f} | {xo:.4f} | {yo:.4f} | {dx:.4f} | {dy:.4f} |")
    else:
        report.append("All A column positions match OLD within 1cm tolerance.")
    report.append("")

    report.append("### 4c. Column Coordinate Mismatches (D vs OLD, >1cm)\n")
    if d_col_coord_diffs:
        report.append(f"| Column | D_X(m) | D_Y(m) | OLD_X(m) | OLD_Y(m) | dX(m) | dY(m) |")
        report.append(f"|--------|--------|--------|----------|----------|-------|-------|")
        for item in d_col_coord_diffs:
            col_name, pt_d, xd, yd, pt_old, xo, yo, dx, dy = item
            report.append(f"| {col_name} | {xd:.4f} | {yd:.4f} | {xo:.4f} | {yo:.4f} | {dx:.4f} | {dy:.4f} |")
    else:
        report.append("All D column positions match OLD within 1cm tolerance.")
    report.append("")

    report.append("### 4d. Building-Specific Columns (Above Ground)\n")
    report.append(f"| Category | Count |")
    report.append(f"|----------|-------|")
    report.append(f"| A-only above-ground columns | {len(a_only_above)} |")
    report.append(f"| D-only above-ground columns | {len(d_only_above)} |")
    report.append(f"| Shared above-ground columns (both A and D) | {len(shared_above)} |")
    report.append(f"| OLD basement columns (B6F-1F) | {len(old_basement_cols)} |")
    report.append(f"| A columns missing from OLD | {len(a_disconnected)} |")
    report.append(f"| D columns missing from OLD | {len(d_disconnected)} |")
    report.append("")

    if a_disconnected:
        sorted_disc = sorted(a_disconnected, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)
        report.append(f"**A columns with NO matching OLD basement column:** {sorted_disc}\n")
    if d_disconnected:
        sorted_disc = sorted(d_disconnected, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)
        report.append(f"**D columns with NO matching OLD basement column:** {sorted_disc}\n")

    # Column section at transition
    report.append("## 5. Column Section Assignments at Transition Stories\n")
    report.append("### Key: 1F is the connection level between basement (OLD) and superstructure (A/D)\n")

    for story in key_stories:
        a_assigns = data_a['col_assigns'].get(story, {})
        d_assigns = data_d['col_assigns'].get(story, {})
        old_assigns = data_old['col_assigns'].get(story, {})

        report.append(f"\n#### Story: {story}\n")
        report.append(f"Columns assigned: A={len(a_assigns)}, D={len(d_assigns)}, OLD={len(old_assigns)}\n")

        # A vs OLD differences
        if a_assigns and old_assigns:
            common = set(a_assigns.keys()) & set(old_assigns.keys())
            diffs = [(c, a_assigns[c], old_assigns[c]) for c in sorted(common, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0) if a_assigns[c] != old_assigns[c]]
            if diffs:
                report.append(f"**A vs OLD section differences ({len(diffs)}):**\n")
                report.append(f"| Column | A Section | OLD Section |")
                report.append(f"|--------|-----------|-------------|")
                for c, sa, so in diffs:
                    report.append(f"| {c} | {sa} | {so} |")
                report.append("")

        # D vs OLD differences
        if d_assigns and old_assigns:
            common = set(d_assigns.keys()) & set(old_assigns.keys())
            diffs = [(c, d_assigns[c], old_assigns[c]) for c in sorted(common, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0) if d_assigns[c] != old_assigns[c]]
            if diffs:
                report.append(f"**D vs OLD section differences ({len(diffs)}):**\n")
                report.append(f"| Column | D Section | OLD Section |")
                report.append(f"|--------|-----------|-------------|")
                for c, sd, so in diffs:
                    report.append(f"| {c} | {sd} | {so} |")
                report.append("")

        # A vs D differences
        if a_assigns and d_assigns:
            common = set(a_assigns.keys()) & set(d_assigns.keys())
            diffs = [(c, a_assigns[c], d_assigns[c]) for c in sorted(common, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0) if a_assigns[c] != d_assigns[c]]
            if diffs:
                report.append(f"**A vs D section differences ({len(diffs)}):**\n")
                report.append(f"| Column | A Section | D Section |")
                report.append(f"|--------|-----------|-----------|")
                for c, sa, sd in diffs:
                    report.append(f"| {c} | {sa} | {sd} |")
                report.append("")

    # Connectivity table (first 30 columns)
    report.append("## 6. Column Connectivity Detail Table (at 1F level)\n")
    report.append("Shows column positions and section assignments for A, D, and OLD at transition stories.\n")
    report.append(f"| Col | A_X(m) | A_Y(m) | OLD_X(m) | OLD_Y(m) | dX(cm) | dY(cm) | A_sec@1F | D_sec@1F | OLD_sec@1F | Match? |")
    report.append(f"|-----|--------|--------|----------|----------|--------|--------|----------|----------|------------|--------|")

    for row in connectivity_table[:80]:
        col = row['col']
        a_x = f"{row['a_x']:.4f}" if row['a_x'] is not None else "N/A"
        a_y = f"{row['a_y']:.4f}" if row['a_y'] is not None else "N/A"
        old_x = f"{row['old_x']:.4f}" if row['old_x'] is not None else "N/A"
        old_y = f"{row['old_y']:.4f}" if row['old_y'] is not None else "N/A"

        # Calculate dx, dy in cm
        if row['a_x'] is not None and row['old_x'] is not None:
            dx_cm = abs(row['a_x'] - row['old_x']) * 100
            dy_cm = abs(row['a_y'] - row['old_y']) * 100
            dx_str = f"{dx_cm:.1f}"
            dy_str = f"{dy_cm:.1f}"
            match = "OK" if dx_cm < 1 and dy_cm < 1 else "MISMATCH"
        elif row['d_x'] is not None and row['old_x'] is not None:
            dx_cm = abs(row['d_x'] - row['old_x']) * 100
            dy_cm = abs(row['d_y'] - row['old_y']) * 100
            dx_str = f"{dx_cm:.1f}"
            dy_str = f"{dy_cm:.1f}"
            match = "OK" if dx_cm < 1 and dy_cm < 1 else "MISMATCH"
        else:
            dx_str = "N/A"
            dy_str = "N/A"
            match = "N/A"

        a_sec = row['a_sec_1f']
        d_sec = row['d_sec_1f']
        old_sec = row['old_sec_1f']

        report.append(f"| {col} | {a_x} | {a_y} | {old_x} | {old_y} | {dx_str} | {dy_str} | {a_sec} | {d_sec} | {old_sec} | {match} |")

    report.append("")

    # ============================================================
    # 7. All Rectangular Column Sections (A e2k) with dimensions
    # ============================================================
    report.append("## 7. All Column Sections (Rectangular) in Building A\n")
    report.append(f"| Section Name | Material | D(cm) | B(cm) |")
    report.append(f"|-------------|----------|-------|-------|")
    for name in sorted(a_col.keys()):
        sec = a_col[name]
        report.append(f"| {name} | {sec['material']} | {sec.get('D','?')} | {sec.get('B','?')} |")
    report.append("")

    report.append("## 8. All Column Sections (Rectangular) in Building D\n")
    report.append(f"| Section Name | Material | D(cm) | B(cm) |")
    report.append(f"|-------------|----------|-------|-------|")
    for name in sorted(d_col.keys()):
        sec = d_col[name]
        report.append(f"| {name} | {sec['material']} | {sec.get('D','?')} | {sec.get('B','?')} |")
    report.append("")

    report.append("## 9. SRC Sections\n")
    report.append("### Building A SRC Sections\n")
    report.append(f"| Section Name | Material | Shape | D(cm) | B(cm) |")
    report.append(f"|-------------|----------|-------|-------|-------|")
    for name in sorted(a_src.keys()):
        sec = a_src[name]
        report.append(f"| {name} | {sec['material']} | {sec['shape']} | {sec.get('D','?')} | {sec.get('B','?')} |")
    report.append("")

    report.append("### Building D SRC Sections\n")
    report.append(f"| Section Name | Material | Shape | D(cm) | B(cm) |")
    report.append(f"|-------------|----------|-------|-------|-------|")
    for name in sorted(d_src.keys()):
        sec = d_src[name]
        report.append(f"| {name} | {sec['material']} | {sec['shape']} | {sec.get('D','?')} | {sec.get('B','?')} |")
    report.append("")

    # Summary findings
    report.append("## 10. Key Findings Summary\n")
    report.append("### Grid Differences\n")
    total_grid_diffs = len(a_vs_old) + len(d_vs_old) + len(a_vs_d)
    if total_grid_diffs == 0:
        report.append("- All grid coordinates match across A, D, and OLD models (within 1cm tolerance).\n")
    else:
        report.append(f"- A vs OLD: {len(a_vs_old)} grid differences\n")
        report.append(f"- D vs OLD: {len(d_vs_old)} grid differences\n")
        report.append(f"- A vs D: {len(a_vs_d)} grid differences\n")

    report.append("### Section Dimension Issues\n")
    if a_dim_mismatches or d_dim_mismatches or old_dim_mismatches:
        report.append(f"- Building A: {len(a_dim_mismatches)} section name/dimension mismatches\n")
        report.append(f"- Building D: {len(d_dim_mismatches)} section name/dimension mismatches\n")
        report.append(f"- OLD model: {len(old_dim_mismatches)} section name/dimension mismatches\n")
    else:
        report.append("- No section name/dimension mismatches found in any model.\n")

    report.append("### Column Connectivity\n")
    report.append(f"- A vs OLD coordinate mismatches: {len(a_col_coord_diffs)}\n")
    report.append(f"- D vs OLD coordinate mismatches: {len(d_col_coord_diffs)}\n")
    report.append(f"- A columns missing from OLD basement: {len(a_disconnected)}\n")
    report.append(f"- D columns missing from OLD basement: {len(d_disconnected)}\n")

    if a_disconnected or d_disconnected:
        report.append("\n**CRITICAL:** Some above-ground columns in A/D have no corresponding basement column in OLD. ")
        report.append("These columns will be disconnected in the merged model.\n")

    # Write report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print(f"\nReport written to: {REPORT_PATH}")
    print(f"Report size: {len(report)} lines")
    print("\nDONE.")


if __name__ == '__main__':
    main()
