import re
import os

def read_e2k(path):
    with open(path, 'r', encoding='big5', errors='replace') as f:
        return f.read()

def extract_section_lines(text, section_name):
    lines = text.split('\n')
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('$ ' + section_name):
            start_idx = i
        elif start_idx is not None and stripped.startswith('$ ') and not stripped.startswith('$ ' + section_name):
            end_idx = i
            break
    if start_idx is None:
        return []
    if end_idx is None:
        end_idx = len(lines)
    return [line.rstrip() for line in lines[start_idx:end_idx] if line.strip()]

def extract_section_raw(text, section_name):
    return '\n'.join(extract_section_lines(text, section_name))

def parse_grids(text):
    section = extract_section_raw(text, 'GRIDS')
    grids_x = []
    grids_y = []
    for line in section.split('\n'):
        m = re.search(r'LABEL\s+"([^"]+)"\s+DIR\s+"([^"]+)"\s+COORD\s+([-\d.]+)', line)
        if m:
            label, direction, coord = m.group(1), m.group(2), float(m.group(3))
            if direction == 'X':
                grids_x.append((label, coord))
            else:
                grids_y.append((label, coord))
    return grids_x, grids_y

BASE_DIR = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳'
a_path = os.path.join(BASE_DIR, 'A', '2026-0303_A_SC_KpKvKw.e2k')
d_path = os.path.join(BASE_DIR, 'D', '2026-0303_D_SC_KpKvKw.e2k')

a_text = read_e2k(a_path)
d_text = read_e2k(d_path)

# ====== STORIES ======
a_stories_raw = extract_section_raw(a_text, 'STORIES - IN SEQUENCE FROM TOP')
d_stories_raw = extract_section_raw(d_text, 'STORIES - IN SEQUENCE FROM TOP')

# ====== GRIDS ======
a_grids_raw = extract_section_raw(a_text, 'GRIDS')
d_grids_raw = extract_section_raw(d_text, 'GRIDS')
a_gx, a_gy = parse_grids(a_text)
d_gx, d_gy = parse_grids(d_text)

# Reference ALL grids (in cm)
ref_x = {
    'A':-3121.25, 'B':-2833.75, 'C':-2471.25, 'D':-1861.25, 'E':-1676.25,
    'F':-1221.25, 'G':-338.75, 'H':466.25, 'I':511.25, 'J':1546.25,
    "K'":1628.75, 'K':2691.25, 'L':2766.25, 'M':3811.25, "M'":3846.25,
    'N':4878.75, 'O':4908.75, 'P':4908.76, 'Q':6028.75, 'R':6076.25,
    'S':6498.75, 'T':6876.25, 'U':7051.25, 'V':7098.75, 'W':7698.75,
    'X':7748.75, 'Y':8073.75, 'Z':8298.75
}
ref_y = {
    '1':0, '2':550, '3':1005, '4':1160, '5':1265, '6':2180, '7':2330,
    '8-1':2497.5, '8-2':3280, '8-3':3420, '9':4030, '10':4152.5,
    '11':4285, '12':4365, '13':4717.5, '14':5200, '15':5235,
    '16':5350, '17':5845, '18':6063.89, '19':6222.5, '20':6395,
    '21':7550, '22':8082.5
}

def compare_grids_to_ref(label, grids_x, grids_y):
    diffs = []
    mx = {l: c for l, c in grids_x}
    my = {l: c for l, c in grids_y}

    for lbl in sorted(ref_x.keys(), key=lambda x: ref_x[x]):
        rv = ref_x[lbl]
        if lbl in mx:
            if abs(mx[lbl] - rv) > 0.001:
                diffs.append(f"  X-{lbl}: {label}={mx[lbl]/100:.4f}m, ALL={rv/100:.4f}m, diff={(mx[lbl]-rv)/100:.4f}m")
        else:
            diffs.append(f"  X-{lbl}: MISSING in {label}")
    for lbl in mx:
        if lbl not in ref_x:
            diffs.append(f"  X-{lbl}: EXTRA in {label} ({mx[lbl]/100:.4f}m)")

    y_labels_ordered = sorted(ref_y.keys(), key=lambda x: ref_y[x])
    for lbl in y_labels_ordered:
        rv = ref_y[lbl]
        if lbl in my:
            if abs(my[lbl] - rv) > 0.001:
                diffs.append(f"  Y-{lbl}: {label}={my[lbl]/100:.4f}m, ALL={rv/100:.4f}m, diff={(my[lbl]-rv)/100:.4f}m")
        else:
            diffs.append(f"  Y-{lbl}: MISSING in {label}")
    for lbl in my:
        if lbl not in ref_y:
            diffs.append(f"  Y-{lbl}: EXTRA in {label} ({my[lbl]/100:.4f}m)")

    return diffs

a_diffs = compare_grids_to_ref('A', a_gx, a_gy)
d_diffs = compare_grids_to_ref('D', d_gx, d_gy)

# ====== FRAME SECTIONS ======
a_fs_raw = extract_section_raw(a_text, 'FRAME SECTIONS')
d_fs_raw = extract_section_raw(d_text, 'FRAME SECTIONS')

# Parse unique section names with key properties
def parse_frame_sections_summary(text):
    section_lines = extract_section_lines(text, 'FRAME SECTIONS')
    seen = {}
    for line in section_lines:
        line = line.strip()
        if not line.startswith('FRAMESECTION'):
            continue
        name_m = re.search(r'FRAMESECTION\s+"([^"]+)"', line)
        if not name_m:
            continue
        name = name_m.group(1)
        if name in seen:
            continue
        mat_m = re.search(r'MATERIAL\s+"([^"]+)"', line)
        shape_m = re.search(r'SHAPE\s+"([^"]+)"', line)
        d_m = re.search(r'\bD\s+([\d.E+\-]+)', line)
        b_m = re.search(r'\bB\s+([\d.E+\-]+)', line)

        mat = mat_m.group(1) if mat_m else ''
        shape = shape_m.group(1) if shape_m else ''
        d_val = d_m.group(1) if d_m else ''
        b_val = b_m.group(1) if b_m else ''
        seen[name] = {'mat': mat, 'shape': shape, 'D': d_val, 'B': b_val, 'full_line': line}
    return seen

a_fs = parse_frame_sections_summary(a_text)
d_fs = parse_frame_sections_summary(d_text)

# ====== CONCRETE SECTIONS ======
a_conc_raw = extract_section_raw(a_text, 'CONCRETE SECTIONS')
d_conc_raw = extract_section_raw(d_text, 'CONCRETE SECTIONS')

# ====== WALL/SLAB/DECK PROPERTIES ======
a_wall_raw = extract_section_raw(a_text, 'WALL/SLAB/DECK PROPERTIES')
d_wall_raw = extract_section_raw(d_text, 'WALL/SLAB/DECK PROPERTIES')

# ====== POINT COORDINATES ======
a_pts_raw = extract_section_raw(a_text, 'POINT COORDINATES')
d_pts_raw = extract_section_raw(d_text, 'POINT COORDINATES')

# ====== LINE CONNECTIVITIES ======
a_lns_raw = extract_section_raw(a_text, 'LINE CONNECTIVITIES')
d_lns_raw = extract_section_raw(d_text, 'LINE CONNECTIVITIES')

# Get story assignments
def get_assign_map(text, assign_keyword):
    # Search across POINT ASSIGNS or LINE ASSIGNS sections
    if assign_keyword == 'POINTASSIGN':
        section = extract_section_raw(text, 'POINT ASSIGNS')
    else:
        section = extract_section_raw(text, 'LINE ASSIGNS')
    mapping = {}
    for line in section.split('\n'):
        m = re.match(r'\s*' + assign_keyword + r'\s+"([^"]+)"\s+"([^"]+)"', line.strip())
        if m:
            obj_name = m.group(1)
            story = m.group(2)
            if obj_name not in mapping:
                mapping[obj_name] = set()
            mapping[obj_name].add(story)
    return mapping

stories_1mf_and_above = set(['PRF','R3F','R2F','R1F','1MF','2F'] + [f'{i}F' for i in range(3,35)])

a_pt_story = get_assign_map(a_text, 'POINTASSIGN')
d_pt_story = get_assign_map(d_text, 'POINTASSIGN')
a_ln_story = get_assign_map(a_text, 'LINEASSIGN')
d_ln_story = get_assign_map(d_text, 'LINEASSIGN')

def filter_objs(raw_text, obj_keyword, story_map, target_stories):
    result = []
    header = None
    for line in raw_text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('$'):
            header = stripped
            continue
        m = re.match(r'\s*' + obj_keyword + r'\s+"([^"]+)"', stripped)
        if m:
            obj = m.group(1)
            stories = story_map.get(obj, set())
            if stories & target_stories:
                result.append(stripped)
    return result, header

a_pts_1mf, a_pts_header = filter_objs(a_pts_raw, 'POINT', a_pt_story, stories_1mf_and_above)
d_pts_1mf, d_pts_header = filter_objs(d_pts_raw, 'POINT', d_pt_story, stories_1mf_and_above)
a_lns_1mf, a_lns_header = filter_objs(a_lns_raw, 'LINE', a_ln_story, stories_1mf_and_above)
d_lns_1mf, d_lns_header = filter_objs(d_lns_raw, 'LINE', d_ln_story, stories_1mf_and_above)

# Get LINE ASSIGNS for 1MF+ with section info
def get_line_assigns_filtered(text, target_stories):
    section = extract_section_raw(text, 'LINE ASSIGNS')
    result = []
    for line in section.split('\n'):
        m = re.match(r'\s*LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"', line.strip())
        if m:
            story = m.group(2)
            if story in target_stories:
                result.append(line.strip())
    return result

a_la_1mf = get_line_assigns_filtered(a_text, stories_1mf_and_above)
d_la_1mf = get_line_assigns_filtered(d_text, stories_1mf_and_above)

# ====== FORMAT GRIDS TABLE ======
def format_grids_table(grids_x, grids_y, label):
    out = []
    out.append(f"### {label} - X Direction Grids")
    out.append("| Grid | Coord (cm) | Coord (m) |")
    out.append("|------|-----------|-----------|")
    for lbl, coord in grids_x:
        out.append(f"| {lbl} | {coord} | {coord/100:.4f} |")
    out.append("")
    out.append(f"### {label} - Y Direction Grids")
    out.append("| Grid | Coord (cm) | Coord (m) |")
    out.append("|------|-----------|-----------|")
    for lbl, coord in grids_y:
        out.append(f"| {lbl} | {coord} | {coord/100:.4f} |")
    return '\n'.join(out)

# ====== FORMAT FRAME SECTIONS TABLE ======
def format_frame_sections_table(fs_dict, label):
    out = []
    out.append(f"### {label} - Frame Sections ({len(fs_dict)} unique sections)")
    out.append("")
    out.append("| Section Name | Material | Shape | D (cm) | B (cm) |")
    out.append("|-------------|----------|-------|--------|--------|")
    for name in sorted(fs_dict.keys()):
        info = fs_dict[name]
        out.append(f"| {name} | {info['mat']} | {info['shape']} | {info['D']} | {info['B']} |")
    return '\n'.join(out)

# ====== BUILD OUTPUT ======
output = []
output.append("# Buildings A and D - Structural Data Extraction")
output.append(f"Source files:")
output.append(f"- A: {a_path}")
output.append(f"- D: {d_path}")
output.append(f"- Date: 2026-03-05")
output.append("")

# ===== 1. STORIES =====
output.append("---")
output.append("## 1. STORIES")
output.append("")
output.append("### Building A - Stories")
output.append("```")
for line in a_stories_raw.split('\n'):
    output.append(line)
output.append("```")
output.append("")
output.append("### Building D - Stories")
output.append("```")
for line in d_stories_raw.split('\n'):
    output.append(line)
output.append("```")
output.append("")
output.append("**Note:** A and D have identical story definitions.")
output.append("")

# ===== 2. GRIDS =====
output.append("---")
output.append("## 2. GRIDS")
output.append("")
output.append(format_grids_table(a_gx, a_gy, "Building A"))
output.append("")
output.append(format_grids_table(d_gx, d_gy, "Building D"))
output.append("")

# ===== GRID COMPARISON =====
output.append("---")
output.append("## 2b. GRID COMPARISON vs ALL/2026-0305 Reference")
output.append("")
output.append("### Building A differences from ALL:")
if a_diffs:
    for d in a_diffs:
        output.append(d)
else:
    output.append("  (no differences)")
output.append("")
output.append("### Building D differences from ALL:")
if d_diffs:
    for d in d_diffs:
        output.append(d)
else:
    output.append("  (no differences)")
output.append("")

# Compare A vs D
output.append("### Building A vs Building D grid differences:")
a_mx = {l: c for l, c in a_gx}
a_my = {l: c for l, c in a_gy}
d_mx = {l: c for l, c in d_gx}
d_my = {l: c for l, c in d_gy}

ad_diffs = []
all_x_labels = sorted(set(list(a_mx.keys()) + list(d_mx.keys())), key=lambda x: a_mx.get(x, d_mx.get(x, 0)))
for lbl in all_x_labels:
    a_val = a_mx.get(lbl)
    d_val = d_mx.get(lbl)
    if a_val is not None and d_val is not None:
        if abs(a_val - d_val) > 0.001:
            ad_diffs.append(f"  X-{lbl}: A={a_val/100:.4f}m, D={d_val/100:.4f}m, diff={(a_val-d_val)/100:.4f}m")
    elif a_val is None:
        ad_diffs.append(f"  X-{lbl}: only in D ({d_val/100:.4f}m)")
    else:
        ad_diffs.append(f"  X-{lbl}: only in A ({a_val/100:.4f}m)")

all_y_labels = sorted(set(list(a_my.keys()) + list(d_my.keys())), key=lambda x: a_my.get(x, d_my.get(x, 0)))
for lbl in all_y_labels:
    a_val = a_my.get(lbl)
    d_val = d_my.get(lbl)
    if a_val is not None and d_val is not None:
        if abs(a_val - d_val) > 0.001:
            ad_diffs.append(f"  Y-{lbl}: A={a_val/100:.4f}m, D={d_val/100:.4f}m, diff={(a_val-d_val)/100:.4f}m")
    elif a_val is None:
        ad_diffs.append(f"  Y-{lbl}: only in D ({d_val/100:.4f}m)")
    else:
        ad_diffs.append(f"  Y-{lbl}: only in A ({a_val/100:.4f}m)")

if ad_diffs:
    for d in ad_diffs:
        output.append(d)
else:
    output.append("  (identical)")
output.append("")

# ===== 3. FRAME SECTIONS =====
output.append("---")
output.append("## 3. FRAME SECTIONS")
output.append("")
output.append(format_frame_sections_table(a_fs, "Building A"))
output.append("")
output.append(format_frame_sections_table(d_fs, "Building D"))
output.append("")

# ===== 4. CONCRETE SECTIONS =====
output.append("---")
output.append("## 4. CONCRETE SECTIONS")
output.append("")
output.append("### Building A - Concrete Sections")
output.append("```")
for line in a_conc_raw.split('\n'):
    output.append(line)
output.append("```")
output.append("")
output.append("### Building D - Concrete Sections")
output.append("```")
for line in d_conc_raw.split('\n'):
    output.append(line)
output.append("```")
output.append("")

# ===== 5. WALL/SLAB/DECK PROPERTIES =====
output.append("---")
output.append("## 5. WALL/SLAB/DECK PROPERTIES")
output.append("")
output.append("### Building A")
output.append("```")
for line in a_wall_raw.split('\n'):
    output.append(line)
output.append("```")
output.append("")
output.append("### Building D")
output.append("```")
for line in d_wall_raw.split('\n'):
    output.append(line)
output.append("```")
output.append("")

# ===== 6. POINT COORDINATES (1MF and above) =====
output.append("---")
output.append("## 6. POINT COORDINATES (filtered: 1MF and above)")
output.append("")
output.append(f"### Building A - Points on 1MF+ ({len(a_pts_1mf)} points)")
output.append("```")
for line in a_pts_1mf:
    output.append(line)
output.append("```")
output.append("")
output.append(f"### Building D - Points on 1MF+ ({len(d_pts_1mf)} points)")
output.append("```")
for line in d_pts_1mf:
    output.append(line)
output.append("```")
output.append("")

# ===== 7. LINE CONNECTIVITIES (1MF and above) =====
output.append("---")
output.append("## 7. LINE CONNECTIVITIES (filtered: 1MF and above)")
output.append("")
output.append(f"### Building A - Lines on 1MF+ ({len(a_lns_1mf)} lines)")
output.append("```")
for line in a_lns_1mf:
    output.append(line)
output.append("```")
output.append("")
output.append(f"### Building D - Lines on 1MF+ ({len(d_lns_1mf)} lines)")
output.append("```")
for line in d_lns_1mf:
    output.append(line)
output.append("```")
output.append("")

# ===== 7b. LINE ASSIGNS for 1MF+ (with section info) =====
output.append("---")
output.append("## 7b. LINE ASSIGNS (1MF and above, with section assignments)")
output.append("")
output.append(f"### Building A - Line Assigns on 1MF+ ({len(a_la_1mf)} assignments)")
output.append("")

# Group by story
def group_by_story(assigns):
    groups = {}
    for line in assigns:
        m = re.match(r'LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"(.*)', line)
        if m:
            obj = m.group(1)
            story = m.group(2)
            rest = m.group(3)
            if story not in groups:
                groups[story] = []
            groups[story].append(line)
    return groups

a_groups = group_by_story(a_la_1mf)
d_groups = group_by_story(d_la_1mf)

# Print summary per story
output.append("| Story | # Lines |")
output.append("|-------|---------|")
for story in sorted(a_groups.keys()):
    output.append(f"| {story} | {len(a_groups[story])} |")
output.append("")

output.append("```")
for line in a_la_1mf:
    output.append(line)
output.append("```")
output.append("")

output.append(f"### Building D - Line Assigns on 1MF+ ({len(d_la_1mf)} assignments)")
output.append("")
output.append("| Story | # Lines |")
output.append("|-------|---------|")
for story in sorted(d_groups.keys()):
    output.append(f"| {story} | {len(d_groups[story])} |")
output.append("")

output.append("```")
for line in d_la_1mf:
    output.append(line)
output.append("```")
output.append("")

# Write output
out_path = os.path.join(BASE_DIR, 'agent1_AD_data.md')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print(f"Output written to: {out_path}")
print(f"Total lines: {len(output)}")
