import re
import sys

def extract_sections(filepath, encoding='utf-8'):
    """Extract all sections from an e2k file, keyed by section header."""
    sections = {}
    current_section = None
    current_lines = []

    with open(filepath, 'r', encoding=encoding, errors='replace') as f:
        for line in f:
            line = line.rstrip('\n').rstrip('\r')
            if line.startswith('$'):
                if current_section:
                    sections[current_section] = current_lines
                current_section = line.strip()
                current_lines = [line]
            else:
                if current_section:
                    current_lines.append(line)
    if current_section:
        sections[current_section] = current_lines
    return sections

def parse_grids(section_lines):
    """Parse grid lines into a dict of {label: (dir, coord)}"""
    grids = {}
    for line in section_lines:
        m = re.search(r'LABEL\s+"([^"]+)"\s+DIR\s+"([^"]+)"\s+COORD\s+([-\d.E+]+)', line)
        if m:
            label = m.group(1)
            direction = m.group(2)
            coord = float(m.group(3))
            grids[label] = (direction, coord)
    return grids

def get_stories_1MF_and_above(section_lines):
    """Get list of stories from top down to 1MF (inclusive). Stories listed top to bottom."""
    stories_ordered = []
    for line in section_lines:
        m = re.search(r'STORY\s+"([^"]+)"', line)
        if m:
            stories_ordered.append(m.group(1))
    result = set()
    for s in stories_ordered:
        if s == 'BASE':
            continue
        result.add(s)
        if s == '1MF':
            break
    return result

def get_point_ids_for_stories(point_assigns_lines, allowed_stories):
    """From POINT ASSIGNS section, get point IDs belonging to allowed stories."""
    point_ids = set()
    for line in point_assigns_lines:
        m = re.match(r'\s+POINTASSIGN\s+"([^"]+)"\s+"([^"]+)"', line)
        if m:
            pt_id = m.group(1)
            story = m.group(2)
            if story in allowed_stories:
                point_ids.add(pt_id)
    return point_ids

def get_line_ids_for_stories(line_assigns_lines, allowed_stories):
    """From LINE ASSIGNS section, get line IDs belonging to allowed stories."""
    line_ids = set()
    for line in line_assigns_lines:
        m = re.match(r'\s+LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"', line)
        if m:
            ln_id = m.group(1)
            story = m.group(2)
            if story in allowed_stories:
                line_ids.add(ln_id)
    return line_ids

def filter_points_by_ids(point_coord_lines, allowed_ids):
    """Filter POINT COORDINATES lines by point IDs."""
    results = []
    for line in point_coord_lines:
        m = re.match(r'\s+POINT\s+"([^"]+)"', line)
        if m:
            if m.group(1) in allowed_ids:
                results.append(line)
    return results

def filter_lines_by_ids(line_conn_lines, allowed_ids):
    """Filter LINE CONNECTIVITIES lines by line IDs."""
    results = []
    for line in line_conn_lines:
        m = re.match(r'\s+LINE\s+"([^"]+)"', line)
        if m:
            if m.group(1) in allowed_ids:
                results.append(line)
    return results

# File paths
b_path = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\B\2026-0303_B_SC_KpKvKw.e2k"
c_path = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\C\2026-0304_C_SC_KpKvKw.e2k"
out_path = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\agent2_BC_data.md"

print("Reading Building B...")
b_sections = extract_sections(b_path)
print(f"  Found {len(b_sections)} sections")

print("Reading Building C...")
c_sections = extract_sections(c_path)
print(f"  Found {len(c_sections)} sections")

# Parse grids
b_grids = parse_grids(b_sections.get('$ GRIDS', []))
c_grids = parse_grids(c_sections.get('$ GRIDS', []))

# Reference grids (ALL model, in meters)
ref_x = {
    'A': -31.2125, 'B': -28.3375, 'C': -24.7125, 'D': -18.6125, 'E': -16.7625,
    'F': -12.2125, 'G': -3.3875, 'H': 4.6625, 'I': 5.1125, 'J': 15.4625,
    "K'": 16.2875, 'K': 26.9125, 'L': 27.6625, 'M': 38.1125, "M'": 38.4625,
    'N': 48.7875, 'O': 49.0875, 'P': 49.0876, 'Q': 60.2875, 'R': 60.7625,
    'S': 64.9875, 'T': 68.7625, 'U': 70.5125, 'V': 70.9875, 'W': 76.9875,
    'X': 77.4875, 'Y': 80.7375, 'Z': 82.9875
}
ref_y = {
    '1': 0, '2': 5.5, '3': 10.05, '4': 11.6, '5': 12.65, '6': 21.8,
    '7': 23.3, '8-1': 24.975, '8-2': 32.8, '8-3': 34.2, '9': 40.3,
    '10': 41.525, '11': 42.85, '12': 43.65, '13': 47.175, '14': 52,
    '15': 52.35, '16': 53.5, '17': 58.45, '18': 60.6389, '19': 62.225,
    '20': 63.95, '21': 75.5, '22': 80.825
}

# Stories for filtering
b_stories_above = get_stories_1MF_and_above(b_sections.get('$ STORIES - IN SEQUENCE FROM TOP', []))
c_stories_above = get_stories_1MF_and_above(c_sections.get('$ STORIES - IN SEQUENCE FROM TOP', []))
print(f"B stories 1MF+above ({len(b_stories_above)}): {sorted(b_stories_above)}")
print(f"C stories 1MF+above ({len(c_stories_above)}): {sorted(c_stories_above)}")

# Get point IDs and line IDs for 1MF and above
b_pt_ids = get_point_ids_for_stories(b_sections.get('$ POINT ASSIGNS', []), b_stories_above)
c_pt_ids = get_point_ids_for_stories(c_sections.get('$ POINT ASSIGNS', []), c_stories_above)
b_ln_ids = get_line_ids_for_stories(b_sections.get('$ LINE ASSIGNS', []), b_stories_above)
c_ln_ids = get_line_ids_for_stories(c_sections.get('$ LINE ASSIGNS', []), c_stories_above)

print(f"B point IDs on 1MF+: {len(b_pt_ids)}")
print(f"C point IDs on 1MF+: {len(c_pt_ids)}")
print(f"B line IDs on 1MF+: {len(b_ln_ids)}")
print(f"C line IDs on 1MF+: {len(c_ln_ids)}")

# Filter coordinates and connectivities
b_points_filtered = filter_points_by_ids(b_sections.get('$ POINT COORDINATES', []), b_pt_ids)
c_points_filtered = filter_points_by_ids(c_sections.get('$ POINT COORDINATES', []), c_pt_ids)
b_lines_filtered = filter_lines_by_ids(b_sections.get('$ LINE CONNECTIVITIES', []), b_ln_ids)
c_lines_filtered = filter_lines_by_ids(c_sections.get('$ LINE CONNECTIVITIES', []), c_ln_ids)

print(f"B points filtered: {len(b_points_filtered)}")
print(f"C points filtered: {len(c_points_filtered)}")
print(f"B lines filtered: {len(b_lines_filtered)}")
print(f"C lines filtered: {len(c_lines_filtered)}")

# --- Build output ---
out = []
out.append("# Buildings B and C - Structural Data Extracted from E2K Files")
out.append("")
out.append("**Source files:**")
out.append("- B: `C:/Users/User/Desktop/V22 AGENTIC MODEL/ETABS REF/大陳/B/2026-0303_B_SC_KpKvKw.e2k`")
out.append("- C: `C:/Users/User/Desktop/V22 AGENTIC MODEL/ETABS REF/大陳/C/2026-0304_C_SC_KpKvKw.e2k`")
out.append("")
out.append("## Units")
out.append("- **Building B**: meters (m) -- story heights like 2.8, 3.4; grid coords like -31.2125")
out.append("- **Building C**: centimeters (cm) -- story heights like 280, 340; grid coords like -3121.25")
out.append("")

# ============================================================
# SECTION 1: STORIES
# ============================================================
out.append("---")
out.append("## 1. STORIES")
out.append("")
out.append("### Building B Stories")
out.append("```")
for line in b_sections.get('$ STORIES - IN SEQUENCE FROM TOP', []):
    out.append(line)
out.append("```")
out.append("")
out.append("### Building C Stories")
out.append("```")
for line in c_sections.get('$ STORIES - IN SEQUENCE FROM TOP', []):
    out.append(line)
out.append("```")
out.append("")

# ============================================================
# SECTION 2: GRIDS
# ============================================================
out.append("---")
out.append("## 2. GRIDS")
out.append("")
out.append("### Building B Grids (units: m)")
out.append("```")
for line in b_sections.get('$ GRIDS', []):
    out.append(line)
out.append("```")
out.append("")
out.append("### Building C Grids (units: cm)")
out.append("```")
for line in c_sections.get('$ GRIDS', []):
    out.append(line)
out.append("```")
out.append("")

# Grid comparison tables
out.append("### Grid Comparison: B vs Reference (ALL model)")
out.append("")
out.append("Building B is in meters, same as reference. Direct comparison:")
out.append("")
out.append("#### X-Direction Grids")
out.append("| Grid | B (m) | Reference (m) | Match? |")
out.append("|------|-------|---------------|--------|")
x_labels = ['A','B','C','D','E','F','G','H','I','J',"K'",'K','L','M',"M'",'N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
for label in x_labels:
    b_val = b_grids.get(label, (None, None))
    ref_val = ref_x.get(label, None)
    if b_val[0] == 'X':
        match = "YES" if ref_val is not None and abs(b_val[1] - ref_val) < 0.0001 else "**DIFFERENT**"
        out.append(f"| {label} | {b_val[1]} | {ref_val} | {match} |")
    elif label in ref_x:
        out.append(f"| {label} | MISSING | {ref_val} | **MISSING** |")

out.append("")
out.append("#### Y-Direction Grids")
out.append("| Grid | B (m) | Reference (m) | Match? |")
out.append("|------|-------|---------------|--------|")
y_labels = ['1','2','3','4','5','6','7','8-1','8-2','8-3','9','10','11','12','13','14','15','16','17','18','19','20','21','22']
for label in y_labels:
    b_val = b_grids.get(label, (None, None))
    ref_val = ref_y.get(label, None)
    if b_val[0] == 'Y':
        match = "YES" if ref_val is not None and abs(b_val[1] - ref_val) < 0.0001 else "**DIFFERENT**"
        out.append(f"| {label} | {b_val[1]} | {ref_val} | {match} |")
    elif label in ref_y:
        out.append(f"| {label} | MISSING | {ref_val} | **MISSING** |")

out.append("")
out.append("### Grid Comparison: C vs Reference (ALL model)")
out.append("")
out.append("Building C is in cm. Converting to meters for comparison:")
out.append("")
out.append("#### X-Direction Grids")
out.append("| Grid | C (cm) | C (m) | Reference (m) | Match? | Delta (m) |")
out.append("|------|--------|-------|---------------|--------|-----------|")
for label in x_labels:
    c_val = c_grids.get(label, (None, None))
    ref_val = ref_x.get(label, None)
    if c_val[0] == 'X':
        c_m = c_val[1] / 100.0
        match = abs(c_m - ref_val) < 0.0001 if ref_val is not None else False
        delta = round(c_m - ref_val, 4) if ref_val is not None else "N/A"
        status = "YES" if match else "**DIFFERENT**"
        out.append(f"| {label} | {c_val[1]} | {c_m:.4f} | {ref_val} | {status} | {delta} |")
    elif label in ref_x:
        out.append(f"| {label} | MISSING | - | {ref_val} | **MISSING** | - |")

out.append("")
out.append("#### Y-Direction Grids")
out.append("| Grid | C (cm) | C (m) | Reference (m) | Match? | Delta (m) |")
out.append("|------|--------|-------|---------------|--------|-----------|")
for label in y_labels:
    c_val = c_grids.get(label, (None, None))
    ref_val = ref_y.get(label, None)
    if c_val[0] == 'Y':
        c_m = c_val[1] / 100.0
        match = abs(c_m - ref_val) < 0.0001 if ref_val is not None else False
        delta = round(c_m - ref_val, 4) if ref_val is not None else "N/A"
        status = "YES" if match else "**DIFFERENT**"
        out.append(f"| {label} | {c_val[1]} | {c_m:.4f} | {ref_val} | {status} | {delta} |")
    elif label in ref_y:
        out.append(f"| {label} | MISSING | - | {ref_val} | **MISSING** | - |")

out.append("")

# Summary of differences
out.append("### Summary of Grid Differences")
out.append("")

# B differences
b_diffs = []
for label in x_labels:
    b_val = b_grids.get(label, (None, None))
    if b_val[0] == 'X' and label in ref_x and abs(b_val[1] - ref_x[label]) > 0.0001:
        b_diffs.append(f"  - X-grid {label}: B={b_val[1]}, Ref={ref_x[label]}, delta={round(b_val[1]-ref_x[label],4)}")
for label in y_labels:
    b_val = b_grids.get(label, (None, None))
    if b_val[0] == 'Y' and label in ref_y and abs(b_val[1] - ref_y[label]) > 0.0001:
        b_diffs.append(f"  - Y-grid {label}: B={b_val[1]}, Ref={ref_y[label]}, delta={round(b_val[1]-ref_y[label],4)}")

if b_diffs:
    out.append("**Building B differences from reference:**")
    for d in b_diffs:
        out.append(d)
else:
    out.append("**Building B: ALL grids match the reference exactly.**")

out.append("")

c_diffs = []
for label in x_labels:
    c_val = c_grids.get(label, (None, None))
    if c_val[0] == 'X' and label in ref_x:
        c_m = c_val[1] / 100.0
        if abs(c_m - ref_x[label]) > 0.0001:
            c_diffs.append(f"  - X-grid {label}: C={c_val[1]}cm ({c_m:.4f}m), Ref={ref_x[label]}m, delta={round(c_m-ref_x[label],4)}m")
for label in y_labels:
    c_val = c_grids.get(label, (None, None))
    if c_val[0] == 'Y' and label in ref_y:
        c_m = c_val[1] / 100.0
        if abs(c_m - ref_y[label]) > 0.0001:
            c_diffs.append(f"  - Y-grid {label}: C={c_val[1]}cm ({c_m:.4f}m), Ref={ref_y[label]}m, delta={round(c_m-ref_y[label],4)}m")

if c_diffs:
    out.append("**Building C differences from reference:**")
    for d in c_diffs:
        out.append(d)
else:
    out.append("**Building C: ALL grids match the reference exactly (after cm->m conversion).**")

out.append("")

# ============================================================
# SECTION 3: FRAME SECTIONS
# ============================================================
out.append("---")
out.append("## 3. FRAME SECTIONS")
out.append("")
out.append("### Building B Frame Sections (units: m)")
out.append("```")
for line in b_sections.get('$ FRAME SECTIONS', []):
    out.append(line)
out.append("```")
out.append("")
out.append("### Building C Frame Sections (units: cm)")
out.append("```")
for line in c_sections.get('$ FRAME SECTIONS', []):
    out.append(line)
out.append("```")
out.append("")

# ============================================================
# SECTION 4: CONCRETE SECTIONS
# ============================================================
out.append("---")
out.append("## 4. CONCRETE SECTIONS")
out.append("")
out.append("### Building B Concrete Sections")
out.append("```")
for line in b_sections.get('$ CONCRETE SECTIONS', []):
    out.append(line)
out.append("```")
out.append("")
out.append("### Building C Concrete Sections")
out.append("```")
for line in c_sections.get('$ CONCRETE SECTIONS', []):
    out.append(line)
out.append("```")
out.append("")

# ============================================================
# SECTION 5: WALL/SLAB/DECK PROPERTIES
# ============================================================
out.append("---")
out.append("## 5. WALL/SLAB/DECK PROPERTIES")
out.append("")
out.append("### Building B Wall/Slab/Deck Properties")
out.append("```")
for line in b_sections.get('$ WALL/SLAB/DECK PROPERTIES', []):
    out.append(line)
out.append("```")
out.append("")
out.append("### Building C Wall/Slab/Deck Properties")
out.append("```")
for line in c_sections.get('$ WALL/SLAB/DECK PROPERTIES', []):
    out.append(line)
out.append("```")
out.append("")

# ============================================================
# SECTION 6: POINT COORDINATES (1MF and above)
# ============================================================
out.append("---")
out.append("## 6. POINT COORDINATES (1MF and above)")
out.append("")
out.append("Note: In e2k format, POINT COORDINATES are global (X,Y only). Points are assigned to stories")
out.append("via POINT ASSIGNS. Below are points that appear on 1MF or any story above 1MF.")
out.append("")
out.append(f"### Building B Point Coordinates (1MF+above: {len(b_points_filtered)} unique points)")
out.append("```")
out.append("$ POINT COORDINATES")
for line in b_points_filtered:
    out.append(line)
out.append("```")
out.append("")
out.append(f"### Building C Point Coordinates (1MF+above: {len(c_points_filtered)} unique points)")
out.append("```")
out.append("$ POINT COORDINATES")
for line in c_points_filtered:
    out.append(line)
out.append("```")
out.append("")

# ============================================================
# SECTION 7: LINE CONNECTIVITIES (1MF and above)
# ============================================================
out.append("---")
out.append("## 7. LINE CONNECTIVITIES (1MF and above)")
out.append("")
out.append("Note: LINE CONNECTIVITIES define element topology (point-to-point connections).")
out.append("Lines are assigned to stories via LINE ASSIGNS. Below are lines assigned to 1MF or above.")
out.append("")
out.append(f"### Building B Line Connectivities (1MF+above: {len(b_lines_filtered)} lines)")
out.append("```")
out.append("$ LINE CONNECTIVITIES")
for line in b_lines_filtered:
    out.append(line)
out.append("```")
out.append("")
out.append(f"### Building C Line Connectivities (1MF+above: {len(c_lines_filtered)} lines)")
out.append("```")
out.append("$ LINE CONNECTIVITIES")
for line in c_lines_filtered:
    out.append(line)
out.append("```")
out.append("")

# Write output
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print(f"\nOutput written to: {out_path}")
print(f"Total output lines: {len(out)}")
