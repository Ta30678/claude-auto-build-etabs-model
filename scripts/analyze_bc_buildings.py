"""
Agent 2: Analyze Buildings B and C
- Parse B e2k (TON/M), C e2k (KGF/CM -> convert to M), OLD e2k (TON/M)
- Compare grids, section definitions, column connectivity
- Output: agent_reports/bc_analysis.md
"""
import re
from collections import defaultdict

# File paths
B_E2K = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\B\2026-0303_B_SC_KpKvKw.e2k'
C_E2K = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\C\2026-0304_C_SC_KpKvKw.e2k'
OLD_E2K = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\OLD\2025-1111_ALL_BUT RC_KpKvKw.e2k'
OUTPUT = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\scripts\agent_reports\bc_analysis.md'


def parse_e2k(filepath, unit_scale=1.0):
    """Parse e2k file. unit_scale converts coords to meters (1.0 for TON/M, 0.01 for KGF/CM)."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    lines = content.split('\n')

    data = {
        'framesections': {},   # name -> {material, shape, D, B, ...}
        'points': {},          # name -> (x_m, y_m)
        'columns': {},         # line_name -> point_name
        'beams': {},           # line_name -> (pt_i, pt_j)
        'lineassigns': [],     # (line_name, story, section, rest)
        'grids_x': {},         # label -> coord_m
        'grids_y': {},         # label -> coord_m
        'stories': [],         # [(name, height_m)]
    }

    for line in lines:
        # FRAMESECTION
        m = re.match(r'\s+FRAMESECTION\s+"([^"]+)"\s+MATERIAL\s+"([^"]+)"\s+SHAPE\s+"([^"]+)"(.*)', line)
        if m:
            sec_name = m.group(1)
            material = m.group(2)
            shape = m.group(3)
            rest = m.group(4)
            props = {}
            props['material'] = material
            props['shape'] = shape
            # Extract D and B
            d_m = re.search(r'\bD\s+([\d.\-E+]+)', rest)
            b_m = re.search(r'\bB\s+([\d.\-E+]+)', rest)
            if d_m:
                props['D'] = float(d_m.group(1)) * unit_scale
            if b_m:
                props['B'] = float(b_m.group(1)) * unit_scale
            # For I-sections, also get TF, TW
            tf_m = re.search(r'\bTF\s+([\d.\-E+]+)', rest)
            tw_m = re.search(r'\bTW\s+([\d.\-E+]+)', rest)
            if tf_m:
                props['TF'] = float(tf_m.group(1)) * unit_scale
            if tw_m:
                props['TW'] = float(tw_m.group(1)) * unit_scale
            data['framesections'][sec_name] = props
            continue

        # POINT
        m = re.match(r'\s+POINT\s+"([^"]+)"\s+([\d.\-E+]+)\s+([\d.\-E+]+)', line)
        if m:
            data['points'][m.group(1)] = (float(m.group(2)) * unit_scale, float(m.group(3)) * unit_scale)
            continue

        # LINE COLUMN
        m = re.match(r'\s+LINE\s+"([^"]+)"\s+COLUMN\s+"([^"]+)"\s+"([^"]+)"\s+(\d+)', line)
        if m:
            data['columns'][m.group(1)] = m.group(2)  # pt_i (same as pt_j for columns)
            continue

        # LINE BEAM/BRACE
        m = re.match(r'\s+LINE\s+"([^"]+)"\s+(BEAM|BRACE)\s+"([^"]+)"\s+"([^"]+)"\s+(\d+)', line)
        if m:
            data['beams'][m.group(1)] = (m.group(3), m.group(4))
            continue

        # LINEASSIGN
        m = re.match(r'\s+LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"(.*)', line)
        if m:
            data['lineassigns'].append((m.group(1), m.group(2), m.group(3), m.group(4).strip()))
            continue

        # GRID
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

        # STORY
        m = re.match(r'\s+STORY\s+"([^"]+)"\s+HEIGHT\s+([\d.\-E+]+)', line)
        if m:
            height_m = float(m.group(2)) * unit_scale
            data['stories'].append((m.group(1), height_m))
            continue

        # STORY with ELEV (BASE)
        m = re.match(r'\s+STORY\s+"([^"]+)"\s+ELEV\s+([\d.\-E+]+)', line)
        if m:
            data['stories'].append((m.group(1), float(m.group(2)) * unit_scale))
            continue

    return data


def get_column_assignments_at_story(data, story_name):
    """Get column-to-section mapping at a specific story."""
    result = {}
    for line_name, story, section, rest in data['lineassigns']:
        if story == story_name and line_name in data['columns']:
            result[line_name] = section
    return result


def get_column_xy(data, line_name):
    """Get x,y coords of a column."""
    if line_name in data['columns']:
        pt = data['columns'][line_name]
        if pt in data['points']:
            return data['points'][pt]
    return None


def section_name_to_dims_cm(sec_name):
    """Parse section name like C120X120... to (D_cm, B_cm)."""
    m = re.match(r'C(\d+)X(\d+)', sec_name)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = re.match(r'SRC(\d+)X(\d+)', sec_name)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return None


def rebuild_v5_dims_m(sec_name):
    """What rebuild_model_v5.py would create for this section (D_m, B_m).
    It parses CnnnXnnn -> cm/100 = m. This is what the rebuilt model has."""
    m = re.match(r'C(\d+)X(\d+)', sec_name)
    if m:
        return (float(m.group(1)) / 100.0, float(m.group(2)) / 100.0)
    m = re.match(r'SRC(\d+)X(\d+)', sec_name)
    if m:
        return (float(m.group(1)) / 100.0, float(m.group(2)) / 100.0)
    m = re.match(r'B(\d+)X(\d+)', sec_name)
    if m:
        return (float(m.group(1)) / 100.0, float(m.group(2)) / 100.0)
    m = re.match(r'WB(\d+)X(\d+)', sec_name)
    if m:
        return (float(m.group(1)) / 100.0, float(m.group(2)) / 100.0)
    m = re.match(r'(?:FB|FSB|FWB)(\d+)X(\d+)', sec_name)
    if m:
        return (float(m.group(1)) / 100.0, float(m.group(2)) / 100.0)
    return None


# ============ MAIN ANALYSIS ============
print("=" * 60)
print("Agent 2: Building B & C Analysis")
print("=" * 60)

# Parse all three e2k files
print("\n[1] Parsing Building B e2k (TON/M)...")
b_data = parse_e2k(B_E2K, unit_scale=1.0)
print(f"  Sections: {len(b_data['framesections'])}")
print(f"  Points: {len(b_data['points'])}")
print(f"  Columns: {len(b_data['columns'])}")
print(f"  Beams: {len(b_data['beams'])}")
print(f"  LineAssigns: {len(b_data['lineassigns'])}")
print(f"  Grids: {len(b_data['grids_x'])} X, {len(b_data['grids_y'])} Y")
print(f"  Stories: {len(b_data['stories'])}")

print("\n[2] Parsing Building C e2k (KGF/CM -> M)...")
c_data = parse_e2k(C_E2K, unit_scale=0.01)
print(f"  Sections: {len(c_data['framesections'])}")
print(f"  Points: {len(c_data['points'])}")
print(f"  Columns: {len(c_data['columns'])}")
print(f"  Beams: {len(c_data['beams'])}")
print(f"  LineAssigns: {len(c_data['lineassigns'])}")
print(f"  Grids: {len(c_data['grids_x'])} X, {len(c_data['grids_y'])} Y")
print(f"  Stories: {len(c_data['stories'])}")

print("\n[3] Parsing OLD e2k (TON/M)...")
old_data = parse_e2k(OLD_E2K, unit_scale=1.0)
print(f"  Sections: {len(old_data['framesections'])}")
print(f"  Points: {len(old_data['points'])}")
print(f"  Columns: {len(old_data['columns'])}")
print(f"  Beams: {len(old_data['beams'])}")
print(f"  LineAssigns: {len(old_data['lineassigns'])}")
print(f"  Grids: {len(old_data['grids_x'])} X, {len(old_data['grids_y'])} Y")
print(f"  Stories: {len(old_data['stories'])}")


# ============ ANALYSIS ============
report = []
report.append("# Agent 2: Building B & C Analysis Report\n")
report.append("## 1. E2K File Summary\n")
report.append("| Model | Sections | Points | Columns | Beams | LineAssigns | Grids X | Grids Y | Stories |")
report.append("|-------|----------|--------|---------|-------|------------|---------|---------|---------|")
for name, d in [("B (TON/M)", b_data), ("C (KGF/CM)", c_data), ("OLD (TON/M)", old_data)]:
    report.append(f"| {name} | {len(d['framesections'])} | {len(d['points'])} | {len(d['columns'])} | {len(d['beams'])} | {len(d['lineassigns'])} | {len(d['grids_x'])} | {len(d['grids_y'])} | {len(d['stories'])} |")
report.append("")

# ============ 2. GRID COMPARISON ============
report.append("## 2. Grid Coordinate Comparison\n")

report.append("### 2a. X-Grids: B vs OLD\n")
report.append("| Label | B (m) | OLD (m) | Diff (mm) | Match? |")
report.append("|-------|-------|---------|-----------|--------|")
all_x_labels = sorted(set(list(b_data['grids_x'].keys()) + list(old_data['grids_x'].keys())),
                       key=lambda x: b_data['grids_x'].get(x, old_data['grids_x'].get(x, 0)))
x_grid_mismatches_b = []
for label in all_x_labels:
    b_val = b_data['grids_x'].get(label)
    o_val = old_data['grids_x'].get(label)
    if b_val is not None and o_val is not None:
        diff_mm = abs(b_val - o_val) * 1000
        match = "OK" if diff_mm < 10 else "MISMATCH"
        report.append(f"| {label} | {b_val:.4f} | {o_val:.4f} | {diff_mm:.1f} | {match} |")
        if match == "MISMATCH":
            x_grid_mismatches_b.append((label, b_val, o_val, diff_mm))
    elif b_val is not None:
        report.append(f"| {label} | {b_val:.4f} | --- | --- | B only |")
    else:
        report.append(f"| {label} | --- | {o_val:.4f} | --- | OLD only |")

report.append("")
report.append("### 2b. Y-Grids: B vs OLD\n")
report.append("| Label | B (m) | OLD (m) | Diff (mm) | Match? |")
report.append("|-------|-------|---------|-----------|--------|")
all_y_labels = sorted(set(list(b_data['grids_y'].keys()) + list(old_data['grids_y'].keys())),
                       key=lambda x: b_data['grids_y'].get(x, old_data['grids_y'].get(x, 0)))
y_grid_mismatches_b = []
for label in all_y_labels:
    b_val = b_data['grids_y'].get(label)
    o_val = old_data['grids_y'].get(label)
    if b_val is not None and o_val is not None:
        diff_mm = abs(b_val - o_val) * 1000
        match = "OK" if diff_mm < 10 else "MISMATCH"
        report.append(f"| {label} | {b_val:.4f} | {o_val:.4f} | {diff_mm:.1f} | {match} |")
        if match == "MISMATCH":
            y_grid_mismatches_b.append((label, b_val, o_val, diff_mm))
    elif b_val is not None:
        report.append(f"| {label} | {b_val:.4f} | --- | --- | B only |")
    else:
        report.append(f"| {label} | --- | {o_val:.4f} | --- | OLD only |")

report.append("")
report.append("### 2c. X-Grids: C vs OLD\n")
report.append("| Label | C (m) | OLD (m) | Diff (mm) | Match? |")
report.append("|-------|-------|---------|-----------|--------|")
all_x_labels_c = sorted(set(list(c_data['grids_x'].keys()) + list(old_data['grids_x'].keys())),
                          key=lambda x: c_data['grids_x'].get(x, old_data['grids_x'].get(x, 0)))
x_grid_mismatches_c = []
for label in all_x_labels_c:
    c_val = c_data['grids_x'].get(label)
    o_val = old_data['grids_x'].get(label)
    if c_val is not None and o_val is not None:
        diff_mm = abs(c_val - o_val) * 1000
        match = "OK" if diff_mm < 10 else "MISMATCH"
        report.append(f"| {label} | {c_val:.4f} | {o_val:.4f} | {diff_mm:.1f} | {match} |")
        if match == "MISMATCH":
            x_grid_mismatches_c.append((label, c_val, o_val, diff_mm))
    elif c_val is not None:
        report.append(f"| {label} | {c_val:.4f} | --- | --- | C only |")
    else:
        report.append(f"| {label} | --- | {o_val:.4f} | --- | OLD only |")

report.append("")
report.append("### 2d. Y-Grids: C vs OLD\n")
report.append("| Label | C (m) | OLD (m) | Diff (mm) | Match? |")
report.append("|-------|-------|---------|-----------|--------|")
all_y_labels_c = sorted(set(list(c_data['grids_y'].keys()) + list(old_data['grids_y'].keys())),
                          key=lambda x: c_data['grids_y'].get(x, old_data['grids_y'].get(x, 0)))
y_grid_mismatches_c = []
for label in all_y_labels_c:
    c_val = c_data['grids_y'].get(label)
    o_val = old_data['grids_y'].get(label)
    if c_val is not None and o_val is not None:
        diff_mm = abs(c_val - o_val) * 1000
        match = "OK" if diff_mm < 10 else "MISMATCH"
        report.append(f"| {label} | {c_val:.4f} | {o_val:.4f} | {diff_mm:.1f} | {match} |")
        if match == "MISMATCH":
            y_grid_mismatches_c.append((label, c_val, o_val, diff_mm))
    elif c_val is not None:
        report.append(f"| {label} | {c_val:.4f} | --- | --- | C only |")
    else:
        report.append(f"| {label} | --- | {o_val:.4f} | --- | OLD only |")

report.append("")
report.append(f"**Grid Summary**: B X-mismatches={len(x_grid_mismatches_b)}, B Y-mismatches={len(y_grid_mismatches_b)}, "
              f"C X-mismatches={len(x_grid_mismatches_c)}, C Y-mismatches={len(y_grid_mismatches_c)}\n")

# ============ 3. SECTION DEFINITIONS COMPARISON ============
report.append("## 3. Section Definitions Comparison\n")

# 3a. Rectangular column sections in B
report.append("### 3a. Building B - Rectangular Column Sections (CnnnXnnn pattern)\n")
report.append("| Section Name | E2K D (m) | E2K B (m) | rebuild_v5 D (m) | rebuild_v5 B (m) | D Match? | B Match? |")
report.append("|-------------|-----------|-----------|-----------------|-----------------|----------|----------|")
b_col_secs = {k: v for k, v in b_data['framesections'].items() if re.match(r'C\d+X\d+', k) and v.get('shape') == 'Rectangular'}
b_section_issues = []
for sec_name in sorted(b_col_secs.keys()):
    props = b_col_secs[sec_name]
    e2k_d = props.get('D', 0)
    e2k_b = props.get('B', 0)
    rv5 = rebuild_v5_dims_m(sec_name)
    if rv5:
        rv5_d, rv5_b = rv5
        d_ok = "OK" if abs(e2k_d - rv5_d) < 0.001 else "WRONG"
        b_ok = "OK" if abs(e2k_b - rv5_b) < 0.001 else "WRONG"
        report.append(f"| {sec_name} | {e2k_d:.3f} | {e2k_b:.3f} | {rv5_d:.3f} | {rv5_b:.3f} | {d_ok} | {b_ok} |")
        if d_ok == "WRONG" or b_ok == "WRONG":
            b_section_issues.append((sec_name, e2k_d, e2k_b, rv5_d, rv5_b))
    else:
        report.append(f"| {sec_name} | {e2k_d:.3f} | {e2k_b:.3f} | N/A | N/A | --- | --- |")

report.append(f"\n**B column section issues**: {len(b_section_issues)} sections with dimension mismatch\n")
if b_section_issues:
    report.append("**Detailed mismatches:**\n")
    for sec, e_d, e_b, r_d, r_b in b_section_issues:
        report.append(f"- `{sec}`: e2k=({e_d:.3f} x {e_b:.3f})m, rebuild_v5=({r_d:.3f} x {r_b:.3f})m")
    report.append("")

# 3b. Rectangular column sections in C
report.append("### 3b. Building C - Rectangular Column Sections (CnnnXnnn pattern)\n")
report.append("| Section Name | E2K D (m) | E2K B (m) | rebuild_v5 D (m) | rebuild_v5 B (m) | D Match? | B Match? |")
report.append("|-------------|-----------|-----------|-----------------|-----------------|----------|----------|")
c_col_secs = {k: v for k, v in c_data['framesections'].items() if re.match(r'C\d+X\d+', k) and v.get('shape') == 'Rectangular'}
c_section_issues = []
for sec_name in sorted(c_col_secs.keys()):
    props = c_col_secs[sec_name]
    e2k_d = props.get('D', 0)
    e2k_b = props.get('B', 0)
    rv5 = rebuild_v5_dims_m(sec_name)
    if rv5:
        rv5_d, rv5_b = rv5
        d_ok = "OK" if abs(e2k_d - rv5_d) < 0.001 else "WRONG"
        b_ok = "OK" if abs(e2k_b - rv5_b) < 0.001 else "WRONG"
        report.append(f"| {sec_name} | {e2k_d:.3f} | {e2k_b:.3f} | {rv5_d:.3f} | {rv5_b:.3f} | {d_ok} | {b_ok} |")
        if d_ok == "WRONG" or b_ok == "WRONG":
            c_section_issues.append((sec_name, e2k_d, e2k_b, rv5_d, rv5_b))
    else:
        report.append(f"| {sec_name} | {e2k_d:.3f} | {e2k_b:.3f} | N/A | N/A | --- | --- |")

report.append(f"\n**C column section issues**: {len(c_section_issues)} sections with dimension mismatch\n")
if c_section_issues:
    report.append("**Detailed mismatches:**\n")
    for sec, e_d, e_b, r_d, r_b in c_section_issues:
        report.append(f"- `{sec}`: e2k=({e_d:.3f} x {e_b:.3f})m, rebuild_v5=({r_d:.3f} x {r_b:.3f})m")
    report.append("")

# 3c. Beam sections comparison
report.append("### 3c. Beam Section Comparison (B, WB, FB, FSB, FWB, SB patterns)\n")
beam_patterns = [r'B\d+X\d+', r'WB\d+X\d+', r'FB\d+X\d+', r'FSB\d+X\d+', r'FWB\d+X\d+', r'SB\d+X\d+']

for model_name, model_data in [("B", b_data), ("C", c_data)]:
    beam_secs = {}
    for k, v in model_data['framesections'].items():
        for pat in beam_patterns:
            if re.match(pat, k) and v.get('shape') == 'Rectangular':
                beam_secs[k] = v
                break

    beam_issues = []
    report.append(f"\n**{model_name} model beam sections:**\n")
    report.append("| Section Name | E2K D (m) | E2K B (m) | rebuild_v5 D (m) | rebuild_v5 B (m) | Match? |")
    report.append("|-------------|-----------|-----------|-----------------|-----------------|--------|")
    for sec_name in sorted(beam_secs.keys()):
        props = beam_secs[sec_name]
        e2k_d = props.get('D', 0)
        e2k_b = props.get('B', 0)
        rv5 = rebuild_v5_dims_m(sec_name)
        if rv5:
            rv5_d, rv5_b = rv5
            match = "OK" if (abs(e2k_d - rv5_d) < 0.001 and abs(e2k_b - rv5_b) < 0.001) else "WRONG"
            report.append(f"| {sec_name} | {e2k_d:.3f} | {e2k_b:.3f} | {rv5_d:.3f} | {rv5_b:.3f} | {match} |")
            if match == "WRONG":
                beam_issues.append((sec_name, e2k_d, e2k_b, rv5_d, rv5_b))
        else:
            report.append(f"| {sec_name} | {e2k_d:.3f} | {e2k_b:.3f} | N/A | N/A | --- |")

    if beam_issues:
        report.append(f"\n**{model_name} beam dimension mismatches**: {len(beam_issues)}")
        for sec, e_d, e_b, r_d, r_b in beam_issues:
            report.append(f"- `{sec}`: e2k=({e_d:.3f} x {e_b:.3f})m, rebuild_v5=({r_d:.3f} x {r_b:.3f})m")
    report.append("")

# 3d. SRC sections
report.append("### 3d. SRC Section Comparison\n")
for model_name, model_data in [("B", b_data), ("C", c_data)]:
    src_secs = {k: v for k, v in model_data['framesections'].items() if re.match(r'SRC\d+X\d+', k)}
    if src_secs:
        report.append(f"\n**{model_name} SRC sections:**\n")
        report.append("| Section Name | Shape | E2K D (m) | E2K B (m) | rebuild_v5 D (m) | rebuild_v5 B (m) | Match? |")
        report.append("|-------------|-------|-----------|-----------|-----------------|-----------------|--------|")
        for sec_name in sorted(src_secs.keys()):
            props = src_secs[sec_name]
            e2k_d = props.get('D', 0)
            e2k_b = props.get('B', 0)
            rv5 = rebuild_v5_dims_m(sec_name)
            if rv5:
                rv5_d, rv5_b = rv5
                match = "OK" if (abs(e2k_d - rv5_d) < 0.001 and abs(e2k_b - rv5_b) < 0.001) else "WRONG"
                report.append(f"| {sec_name} | {props['shape']} | {e2k_d:.3f} | {e2k_b:.3f} | {rv5_d:.3f} | {rv5_b:.3f} | {match} |")
            else:
                report.append(f"| {sec_name} | {props['shape']} | {e2k_d:.3f} | {e2k_b:.3f} | N/A | N/A | --- |")
    else:
        report.append(f"\n**{model_name}**: No SRC sections found.\n")
report.append("")

# 3e. Steel I-sections (H-sections in B)
report.append("### 3e. Steel I-Sections (H-sections)\n")
for model_name, model_data in [("B", b_data), ("C", c_data)]:
    h_secs = {k: v for k, v in model_data['framesections'].items() if v.get('shape') == 'I/Wide Flange'}
    if h_secs:
        report.append(f"\n**{model_name} I-Sections** ({len(h_secs)} total):\n")
        report.append("| Section Name | D (m) | B (m) | TF (m) | TW (m) |")
        report.append("|-------------|-------|-------|--------|--------|")
        for sec_name in sorted(h_secs.keys())[:20]:  # limit display
            props = h_secs[sec_name]
            report.append(f"| {sec_name} | {props.get('D',0):.4f} | {props.get('B',0):.4f} | {props.get('TF',0):.4f} | {props.get('TW',0):.4f} |")
        if len(h_secs) > 20:
            report.append(f"| ... | ({len(h_secs)-20} more) | | | |")
    else:
        report.append(f"\n**{model_name}**: No I-sections found.\n")
report.append("")

# 3f. General (composite/SRC) sections - these are the "-500x1100x30x30C630O" style sections
report.append("### 3f. General Shape Sections (Composite/SRC with Steel Core)\n")
for model_name, model_data in [("B", b_data), ("C", c_data)]:
    gen_secs = {k: v for k, v in model_data['framesections'].items() if v.get('shape') == 'General'}
    if gen_secs:
        report.append(f"\n**{model_name} General sections** ({len(gen_secs)} total):\n")
        report.append("| Section Name | D (m) | B (m) |")
        report.append("|-------------|-------|-------|")
        for sec_name in sorted(gen_secs.keys())[:20]:
            props = gen_secs[sec_name]
            report.append(f"| {sec_name} | {props.get('D',0):.4f} | {props.get('B',0):.4f} |")
        if len(gen_secs) > 20:
            report.append(f"| ... | ({len(gen_secs)-20} more) | |")
    else:
        report.append(f"\n**{model_name}**: No General-shape sections found.\n")
report.append("")

# 3g. Sections in B/C not in OLD
report.append("### 3g. Sections Unique to B/C (not in OLD)\n")
b_only = set(b_data['framesections'].keys()) - set(old_data['framesections'].keys())
c_only = set(c_data['framesections'].keys()) - set(old_data['framesections'].keys())
old_only_vs_b = set(old_data['framesections'].keys()) - set(b_data['framesections'].keys())
old_only_vs_c = set(old_data['framesections'].keys()) - set(c_data['framesections'].keys())

report.append(f"- Sections in B but not OLD: {len(b_only)}")
if b_only:
    report.append(f"  - Examples: {sorted(b_only)[:10]}")
report.append(f"- Sections in C but not OLD: {len(c_only)}")
if c_only:
    report.append(f"  - Examples: {sorted(c_only)[:10]}")
report.append(f"- Sections in OLD but not B: {len(old_only_vs_b)}")
if old_only_vs_b:
    report.append(f"  - Examples: {sorted(old_only_vs_b)[:10]}")
report.append(f"- Sections in OLD but not C: {len(old_only_vs_c)}")
if old_only_vs_c:
    report.append(f"  - Examples: {sorted(old_only_vs_c)[:10]}")
report.append("")


# ============ 4. COLUMN CONNECTIVITY ANALYSIS ============
report.append("## 4. Column Connectivity Analysis\n")
report.append("Checking if columns in OLD model at 1F level connect to columns in B/C at 1F level.\n")

# Get columns at 1F in OLD
old_cols_1f = get_column_assignments_at_story(old_data, '1F')
# Get columns at 1F in B
b_cols_1f = get_column_assignments_at_story(b_data, '1F')
# Get columns at 1F in C
c_cols_1f = get_column_assignments_at_story(c_data, '1F')

# Also check 1MF and 2F
old_cols_1mf = get_column_assignments_at_story(old_data, '1MF')
b_cols_1mf = get_column_assignments_at_story(b_data, '1MF')
b_cols_2f = get_column_assignments_at_story(b_data, '2F')
c_cols_1mf = get_column_assignments_at_story(c_data, '1MF')
c_cols_2f = get_column_assignments_at_story(c_data, '2F')

report.append(f"### Column counts by story:\n")
report.append("| Story | OLD | B | C |")
report.append("|-------|-----|---|---|")
report.append(f"| 1F | {len(old_cols_1f)} | {len(b_cols_1f)} | {len(c_cols_1f)} |")
report.append(f"| 1MF | {len(old_cols_1mf)} | {len(b_cols_1mf)} | {len(c_cols_1mf)} |")
report.append(f"| 2F | --- | {len(b_cols_2f)} | {len(c_cols_2f)} |")
report.append("")

# The merge model takes OLD basement (B6F to 1MF) and B/C above-1MF (1MF to PRF).
# OLD columns at 1F have their top at 1MF level.
# B/C columns at 1MF have their bottom at 1MF and top at 2F.
# The connection point is at the 1MF level.
# OLD columns assigned at "1F" story go from 1F top-of-story down to B1F top (i.e., column at 1F means bottom is at B1F level, top is at 1F level).
# Wait - actually ETABS story-based columns: a column assigned at story "1F" sits below the 1F diaphragm.
# The top of OLD column at "1F" story = 1F elevation. The bottom of B/C column at "1MF" = 1MF elevation.
# Since 1MF is between B1F and 1F, we need OLD columns that span to 1MF level.
# Actually, let's check: what does OLD have at 1MF?

report.append("### 4a. Column Position Matching: OLD (1F) vs B (1F)\n")
report.append("These columns should share the same LINE names and POINT coordinates.\n")

# Columns shared by name between OLD 1F and B 1F
shared_b = set(old_cols_1f.keys()) & set(b_cols_1f.keys())
old_only_1f = set(old_cols_1f.keys()) - set(b_cols_1f.keys())
b_only_1f = set(b_cols_1f.keys()) - set(old_cols_1f.keys())

report.append(f"- Shared column names (OLD 1F & B 1F): {len(shared_b)}")
report.append(f"- OLD 1F only: {len(old_only_1f)}")
report.append(f"- B 1F only: {len(b_only_1f)}")
report.append("")

# For shared columns, check XY coordinate match
report.append("**Coordinate check for shared columns (tolerance = 1cm = 0.01m):**\n")
report.append("| Column | OLD X (m) | OLD Y (m) | B X (m) | B Y (m) | dX (mm) | dY (mm) | Match? | OLD Section | B Section |")
report.append("|--------|-----------|-----------|---------|---------|---------|---------|--------|-------------|-----------|")
b_coord_matches = 0
b_coord_mismatches = []
b_section_diffs = []
for col in sorted(shared_b):
    old_xy = get_column_xy(old_data, col)
    b_xy = get_column_xy(b_data, col)
    old_sec = old_cols_1f[col]
    b_sec = b_cols_1f[col]
    if old_xy and b_xy:
        dx_mm = abs(old_xy[0] - b_xy[0]) * 1000
        dy_mm = abs(old_xy[1] - b_xy[1]) * 1000
        match = "OK" if (dx_mm < 10 and dy_mm < 10) else "MISMATCH"
        sec_match = "same" if old_sec == b_sec else "DIFF"
        report.append(f"| {col} | {old_xy[0]:.4f} | {old_xy[1]:.4f} | {b_xy[0]:.4f} | {b_xy[1]:.4f} | {dx_mm:.1f} | {dy_mm:.1f} | {match} | {old_sec} | {b_sec} |")
        if match == "OK":
            b_coord_matches += 1
        else:
            b_coord_mismatches.append((col, dx_mm, dy_mm))
        if sec_match == "DIFF":
            b_section_diffs.append((col, old_sec, b_sec))
    else:
        report.append(f"| {col} | ? | ? | ? | ? | ? | ? | NO DATA | {old_sec} | {b_sec} |")

report.append(f"\n**B Result**: {b_coord_matches} matched, {len(b_coord_mismatches)} mismatched out of {len(shared_b)} shared columns\n")
if b_section_diffs:
    report.append(f"**B Section differences at 1F** ({len(b_section_diffs)} columns):\n")
    for col, os, bs in b_section_diffs[:20]:
        report.append(f"- `{col}`: OLD={os}, B={bs}")
    report.append("")

# Columns only in OLD at 1F (not in B) - potential disconnects
if old_only_1f:
    report.append(f"**OLD 1F columns NOT in B** ({len(old_only_1f)} columns):\n")
    report.append("These may belong to other buildings (A, C, D) or are truly disconnected.\n")
    # Try to identify which building by checking if they are in C or other
    for col in sorted(old_only_1f)[:30]:
        xy = get_column_xy(old_data, col)
        in_c = col in c_cols_1f
        xy_str = f"({xy[0]:.2f}, {xy[1]:.2f})" if xy else "(?,?)"
        report.append(f"- `{col}` at {xy_str}" + (f" [also in C 1F]" if in_c else ""))
    if len(old_only_1f) > 30:
        report.append(f"- ... ({len(old_only_1f) - 30} more)")
    report.append("")

if b_only_1f:
    report.append(f"**B 1F columns NOT in OLD** ({len(b_only_1f)} columns):\n")
    for col in sorted(b_only_1f)[:20]:
        xy = get_column_xy(b_data, col)
        xy_str = f"({xy[0]:.2f}, {xy[1]:.2f})" if xy else "(?,?)"
        report.append(f"- `{col}` at {xy_str}")
    if len(b_only_1f) > 20:
        report.append(f"- ... ({len(b_only_1f) - 20} more)")
    report.append("")


# 4b. Same for C
report.append("### 4b. Column Position Matching: OLD (1F) vs C (1F)\n")
shared_c = set(old_cols_1f.keys()) & set(c_cols_1f.keys())
old_only_c = set(old_cols_1f.keys()) - set(c_cols_1f.keys())
c_only_1f = set(c_cols_1f.keys()) - set(old_cols_1f.keys())

report.append(f"- Shared column names (OLD 1F & C 1F): {len(shared_c)}")
report.append(f"- OLD 1F only: {len(old_only_c)}")
report.append(f"- C 1F only: {len(c_only_1f)}")
report.append("")

report.append("**Coordinate check for shared columns (tolerance = 1cm = 0.01m):**\n")
report.append("| Column | OLD X (m) | OLD Y (m) | C X (m) | C Y (m) | dX (mm) | dY (mm) | Match? | OLD Section | C Section |")
report.append("|--------|-----------|-----------|---------|---------|---------|---------|--------|-------------|-----------|")
c_coord_matches = 0
c_coord_mismatches = []
c_sec_diffs = []
for col in sorted(shared_c):
    old_xy = get_column_xy(old_data, col)
    c_xy = get_column_xy(c_data, col)
    old_sec = old_cols_1f[col]
    c_sec = c_cols_1f[col]
    if old_xy and c_xy:
        dx_mm = abs(old_xy[0] - c_xy[0]) * 1000
        dy_mm = abs(old_xy[1] - c_xy[1]) * 1000
        match = "OK" if (dx_mm < 10 and dy_mm < 10) else "MISMATCH"
        sec_match = "same" if old_sec == c_sec else "DIFF"
        report.append(f"| {col} | {old_xy[0]:.4f} | {old_xy[1]:.4f} | {c_xy[0]:.4f} | {c_xy[1]:.4f} | {dx_mm:.1f} | {dy_mm:.1f} | {match} | {old_sec} | {c_sec} |")
        if match == "OK":
            c_coord_matches += 1
        else:
            c_coord_mismatches.append((col, dx_mm, dy_mm))
        if sec_match == "DIFF":
            c_sec_diffs.append((col, old_sec, c_sec))
    else:
        report.append(f"| {col} | ? | ? | ? | ? | ? | ? | NO DATA | {old_sec} | {c_sec} |")

report.append(f"\n**C Result**: {c_coord_matches} matched, {len(c_coord_mismatches)} mismatched out of {len(shared_c)} shared columns\n")
if c_sec_diffs:
    report.append(f"**C Section differences at 1F** ({len(c_sec_diffs)} columns):\n")
    for col, os, cs in c_sec_diffs[:20]:
        report.append(f"- `{col}`: OLD={os}, C={cs}")
    report.append("")

if c_only_1f:
    report.append(f"**C 1F columns NOT in OLD** ({len(c_only_1f)} columns):\n")
    for col in sorted(c_only_1f)[:20]:
        xy = get_column_xy(c_data, col)
        xy_str = f"({xy[0]:.2f}, {xy[1]:.2f})" if xy else "(?,?)"
        report.append(f"- `{col}` at {xy_str}")
    if len(c_only_1f) > 20:
        report.append(f"- ... ({len(c_only_1f) - 20} more)")
    report.append("")


# 4c. Find B/C columns above 1MF that need to connect to OLD basement
report.append("### 4c. B/C Above-1MF Columns that Need Connection to OLD Basement\n")
report.append("In MERGED_v5, the OLD model provides B6F-1MF, and B/C provide 1MF-PRF.\n")
report.append("Columns at 1MF story in B/C should connect to columns at 1F story in OLD (which top at 1MF elev).\n")

# Get all B column positions at any above-1MF story (e.g. 1MF, 2F)
b_above_stories = set()
for ln, st, sec, rest in b_data['lineassigns']:
    if ln in b_data['columns']:
        b_above_stories.add(st)

c_above_stories = set()
for ln, st, sec, rest in c_data['lineassigns']:
    if ln in c_data['columns']:
        c_above_stories.add(st)

# Story order for reference
report.append(f"B column stories: {sorted(b_above_stories)}\n")
report.append(f"C column stories: {sorted(c_above_stories)}\n")

# Now find columns in B at 1MF (which is the connection story)
b_cols_at_1mf = get_column_assignments_at_story(b_data, '1MF')
report.append(f"B columns at 1MF: {len(b_cols_at_1mf)} (these are BEAMS at 1MF level, not columns)")

# Actually, for buildings B/C, columns are assigned at stories like B5F, B4F,...,1F, 1MF, 2F,...PRF
# The column at "1MF" story spans from 1F top to 1MF top.
# The column at "2F" story spans from 1MF top to 2F top.
# So the LOWEST above-ground column in B/C is at "2F" story (if they have it).
# The OLD column at "1F" story has its top at 1F level (= 1MF bottom + 1MF height?).
# Let's clarify:
#   OLD stories: ... B1F(h=3.1), 1F(h=4.2), 1MF(h=3), 2F(h=3), ...
#   B stories: same structure
# OLD column at "1F" story: bottom at B1F top, top at 1F top.
# B column at "1F" story: bottom at B1F top, top at 1F top.
# If the merged model takes OLD B6F-1MF and B/C 1MF-PRF:
# OLD has columns at stories B5F, B4F, B3F, B2F, B1F, 1F (top at 1F level)
# B/C has columns at stories 1MF (bottom at 1F, top at 1MF), 2F, 3F,...PRF
# So the interface is at 1F level (top of OLD 1F column = bottom of B/C 1MF column).

# Wait, let me re-check. The MERGED_v5 takes OLD for B6F-1MF. Let me check what stories B/C actually have
# columns assigned at. The question is which stories from B/C were imported into MERGED_v5.

# Looking at the rebuild script, it takes above-1MF frames. So the first B/C story used is probably 1MF or 2F.
# Let's collect: which unique stories do B/C column LINEASSIGN use?

b_col_story_counts = defaultdict(int)
for ln, st, sec, rest in b_data['lineassigns']:
    if ln in b_data['columns']:
        b_col_story_counts[st] += 1

c_col_story_counts = defaultdict(int)
for ln, st, sec, rest in c_data['lineassigns']:
    if ln in c_data['columns']:
        c_col_story_counts[st] += 1

report.append(f"\n**B columns per story:**\n")
# Sort stories in building order
story_order = ['B6F', 'B5F', 'B4F', 'B3F', 'B2F', 'B1F', '1F', '1MF', '2F', '3F', '4F', '5F',
               '6F', '7F', '8F', '9F', '10F', '11F', '12F', '13F', '14F', '15F', '16F', '17F',
               '18F', '19F', '20F', '21F', '22F', '23F', '24F', '25F', '26F', '27F', '28F',
               '29F', '30F', '31F', '32F', '33F', '34F', 'R1F', 'R2F', 'R3F', 'PRF']

for st in story_order:
    if st in b_col_story_counts:
        report.append(f"- {st}: {b_col_story_counts[st]} columns")

report.append(f"\n**C columns per story:**\n")
for st in story_order:
    if st in c_col_story_counts:
        report.append(f"- {st}: {c_col_story_counts[st]} columns")
report.append("")

# For OLD, same thing
old_col_story_counts = defaultdict(int)
for ln, st, sec, rest in old_data['lineassigns']:
    if ln in old_data['columns']:
        old_col_story_counts[st] += 1

report.append(f"**OLD columns per story:**\n")
for st in story_order:
    if st in old_col_story_counts:
        report.append(f"- {st}: {old_col_story_counts[st]} columns")
report.append("")


# 4d. XY proximity matching between OLD 1F columns and B/C 1MF columns
# Some columns might have different names but same location
report.append("### 4d. XY Proximity Matching: OLD 1F columns vs B 1MF columns\n")
report.append("Searching for OLD columns at 1F with no name match in B, but with XY proximity match.\n")

# Build spatial index for B columns at 1MF
b_1mf_cols_by_xy = {}
for col in b_cols_1mf:
    xy = get_column_xy(b_data, col)
    if xy:
        b_1mf_cols_by_xy[col] = xy

# Also build for B columns at 2F
b_2f_cols_by_xy = {}
for col in b_cols_2f:
    xy = get_column_xy(b_data, col)
    if xy:
        b_2f_cols_by_xy[col] = xy

# For each OLD 1F column not in B by name, find nearest B column
old_unmatched_for_b = set(old_cols_1f.keys()) - set(b_cols_1f.keys())
proximity_matches_b = []
no_proximity_b = []

for old_col in sorted(old_unmatched_for_b):
    old_xy = get_column_xy(old_data, old_col)
    if not old_xy:
        continue

    best_dist = float('inf')
    best_col = None
    best_story = None

    # Check B 1MF columns
    for b_col, b_xy in b_1mf_cols_by_xy.items():
        dist = ((old_xy[0] - b_xy[0])**2 + (old_xy[1] - b_xy[1])**2)**0.5
        if dist < best_dist:
            best_dist = dist
            best_col = b_col
            best_story = '1MF'

    # Check B 2F columns
    for b_col, b_xy in b_2f_cols_by_xy.items():
        dist = ((old_xy[0] - b_xy[0])**2 + (old_xy[1] - b_xy[1])**2)**0.5
        if dist < best_dist:
            best_dist = dist
            best_col = b_col
            best_story = '2F'

    if best_dist < 0.01:  # within 1cm
        proximity_matches_b.append((old_col, best_col, best_story, best_dist * 1000))
    elif best_dist < 1.0:  # within 1m (possibly shifted)
        no_proximity_b.append((old_col, old_xy, best_col, best_story, best_dist))

if proximity_matches_b:
    report.append(f"**XY proximity matches found**: {len(proximity_matches_b)}\n")
    report.append("| OLD Col | B Col | B Story | Dist (mm) |")
    report.append("|---------|-------|---------|-----------|")
    for oc, bc, bs, dist in proximity_matches_b[:30]:
        report.append(f"| {oc} | {bc} | {bs} | {dist:.1f} |")
    report.append("")
else:
    report.append("No XY proximity matches found for unmatched OLD columns.\n")

if no_proximity_b:
    report.append(f"**Columns with nearest B neighbor > 1cm but < 1m**: {len(no_proximity_b)}\n")
    report.append("| OLD Col | OLD XY (m) | Nearest B Col | B Story | Dist (m) |")
    report.append("|---------|------------|---------------|---------|----------|")
    for oc, oxy, bc, bs, dist in no_proximity_b[:20]:
        report.append(f"| {oc} | ({oxy[0]:.2f}, {oxy[1]:.2f}) | {bc} | {bs} | {dist:.3f} |")
    report.append("")

# Same for C
report.append("### 4e. XY Proximity Matching: OLD 1F columns vs C 1MF columns\n")
c_1mf_cols_by_xy = {}
for col in c_cols_1mf:
    xy = get_column_xy(c_data, col)
    if xy:
        c_1mf_cols_by_xy[col] = xy

c_2f_cols_by_xy = {}
for col in c_cols_2f:
    xy = get_column_xy(c_data, col)
    if xy:
        c_2f_cols_by_xy[col] = xy

old_unmatched_for_c = set(old_cols_1f.keys()) - set(c_cols_1f.keys())
proximity_matches_c = []
no_proximity_c = []

for old_col in sorted(old_unmatched_for_c):
    old_xy = get_column_xy(old_data, old_col)
    if not old_xy:
        continue

    best_dist = float('inf')
    best_col = None
    best_story = None

    for c_col, c_xy in c_1mf_cols_by_xy.items():
        dist = ((old_xy[0] - c_xy[0])**2 + (old_xy[1] - c_xy[1])**2)**0.5
        if dist < best_dist:
            best_dist = dist
            best_col = c_col
            best_story = '1MF'

    for c_col, c_xy in c_2f_cols_by_xy.items():
        dist = ((old_xy[0] - c_xy[0])**2 + (old_xy[1] - c_xy[1])**2)**0.5
        if dist < best_dist:
            best_dist = dist
            best_col = c_col
            best_story = '2F'

    if best_dist < 0.01:
        proximity_matches_c.append((old_col, best_col, best_story, best_dist * 1000))
    elif best_dist < 1.0:
        no_proximity_c.append((old_col, old_xy, best_col, best_story, best_dist))

if proximity_matches_c:
    report.append(f"**XY proximity matches found**: {len(proximity_matches_c)}\n")
    report.append("| OLD Col | C Col | C Story | Dist (mm) |")
    report.append("|---------|-------|---------|-----------|")
    for oc, cc, cs, dist in proximity_matches_c[:30]:
        report.append(f"| {oc} | {cc} | {cs} | {dist:.1f} |")
    report.append("")
else:
    report.append("No XY proximity matches found for unmatched OLD columns.\n")

if no_proximity_c:
    report.append(f"**Columns with nearest C neighbor > 1cm but < 1m**: {len(no_proximity_c)}\n")
    report.append("| OLD Col | OLD XY (m) | Nearest C Col | C Story | Dist (m) |")
    report.append("|---------|------------|---------------|---------|----------|")
    for oc, oxy, cc, cs, dist in no_proximity_c[:20]:
        report.append(f"| {oc} | ({oxy[0]:.2f}, {oxy[1]:.2f}) | {cc} | {cs} | {dist:.3f} |")
    report.append("")


# ============ 5. KEY FINDINGS SUMMARY ============
report.append("## 5. Key Findings Summary\n")

report.append("### Grid Alignment\n")
total_grid_issues = len(x_grid_mismatches_b) + len(y_grid_mismatches_b) + len(x_grid_mismatches_c) + len(y_grid_mismatches_c)
if total_grid_issues == 0:
    report.append("All grids match between B/C and OLD within 10mm tolerance.\n")
else:
    report.append(f"**{total_grid_issues} grid mismatches found**:\n")
    for label, bv, ov, d in x_grid_mismatches_b:
        report.append(f"- B X-grid '{label}': B={bv:.4f}m, OLD={ov:.4f}m (diff={d:.0f}mm)")
    for label, bv, ov, d in y_grid_mismatches_b:
        report.append(f"- B Y-grid '{label}': B={bv:.4f}m, OLD={ov:.4f}m (diff={d:.0f}mm)")
    for label, cv, ov, d in x_grid_mismatches_c:
        report.append(f"- C X-grid '{label}': C={cv:.4f}m, OLD={ov:.4f}m (diff={d:.0f}mm)")
    for label, cv, ov, d in y_grid_mismatches_c:
        report.append(f"- C Y-grid '{label}': C={cv:.4f}m, OLD={ov:.4f}m (diff={d:.0f}mm)")
    report.append("")

report.append("### Section Dimension Issues\n")
total_sec_issues = len(b_section_issues) + len(c_section_issues)
if total_sec_issues == 0:
    report.append("All rectangular column sections match between e2k definitions and rebuild_v5 parsing.\n")
else:
    report.append(f"**{total_sec_issues} section dimension mismatches** (rebuild_v5 interprets name differently than e2k definition):\n")
    for sec, e_d, e_b, r_d, r_b in b_section_issues:
        report.append(f"- B `{sec}`: e2k=({e_d:.3f}x{e_b:.3f})m vs rebuild_v5=({r_d:.3f}x{r_b:.3f})m")
    for sec, e_d, e_b, r_d, r_b in c_section_issues:
        report.append(f"- C `{sec}`: e2k=({e_d:.3f}x{e_b:.3f})m vs rebuild_v5=({r_d:.3f}x{r_b:.3f})m")
    report.append("")

report.append("### Column Connectivity\n")
report.append(f"- OLD columns at 1F: {len(old_cols_1f)}\n")
report.append(f"- B columns at 1F: {len(b_cols_1f)} (shared with OLD: {len(shared_b)})\n")
report.append(f"- C columns at 1F: {len(c_cols_1f)} (shared with OLD: {len(shared_c)})\n")
report.append(f"- B coordinate matches: {b_coord_matches}/{len(shared_b)}\n")
report.append(f"- C coordinate matches: {c_coord_matches}/{len(shared_c)}\n")
if b_coord_mismatches:
    report.append(f"- B coordinate MISMATCHES: {len(b_coord_mismatches)} columns have >1cm offset\n")
if c_coord_mismatches:
    report.append(f"- C coordinate MISMATCHES: {len(c_coord_mismatches)} columns have >1cm offset\n")

# Identify truly disconnected columns
report.append("\n### Potentially Disconnected Columns\n")
report.append("These are OLD basement columns at 1F with NO corresponding B or C column (by name or proximity).\n")

# Columns in OLD 1F that are NOT in either B or C (by name)
old_not_in_bc = set(old_cols_1f.keys()) - set(b_cols_1f.keys()) - set(c_cols_1f.keys())
# Remove those that had proximity matches
prox_matched_old = set(m[0] for m in proximity_matches_b) | set(m[0] for m in proximity_matches_c)
truly_disconnected = old_not_in_bc - prox_matched_old

report.append(f"OLD columns at 1F not in B or C by name: {len(old_not_in_bc)}\n")
report.append(f"After proximity matching: {len(truly_disconnected)} truly disconnected\n")

if truly_disconnected:
    report.append("\n| Column | X (m) | Y (m) | Section at 1F |")
    report.append("|--------|-------|-------|--------------|")
    for col in sorted(truly_disconnected):
        xy = get_column_xy(old_data, col)
        sec = old_cols_1f.get(col, "?")
        if xy:
            report.append(f"| {col} | {xy[0]:.4f} | {xy[1]:.4f} | {sec} |")
        else:
            report.append(f"| {col} | ? | ? | {sec} |")
    report.append("")


# Write report
print("\n[4] Writing report...")
report_text = '\n'.join(report)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(report_text)
print(f"Report written to: {OUTPUT}")
print(f"Report length: {len(report_text)} chars, {len(report)} lines")

# Print summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Grid mismatches: {total_grid_issues}")
print(f"Section dimension issues: {total_sec_issues}")
print(f"B columns at 1F shared with OLD: {len(shared_b)} ({b_coord_matches} coord match)")
print(f"C columns at 1F shared with OLD: {len(shared_c)} ({c_coord_matches} coord match)")
print(f"Truly disconnected OLD columns: {len(truly_disconnected)}")
