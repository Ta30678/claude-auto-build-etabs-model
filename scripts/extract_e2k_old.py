import re

e2k_path = r"C:/Users/User/Desktop/V22 AGENTIC MODEL/ETABS REF/大陳/ALL/OLD/2025-1111_ALL_BUT RC_KpKvKw.e2k"
out_path = r"C:/Users/User/Desktop/V22 AGENTIC MODEL/ETABS REF/大陳/agent_OLD_data.md"

with open(e2k_path, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Parse sections
sections = {}
current_section = None
current_lines = []

for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith('$ ') and not stripped.startswith('$ File'):
        if current_section:
            sections[current_section] = current_lines
        current_section = stripped
        current_lines = [line]
    else:
        current_lines.append(line)
if current_section:
    sections[current_section] = current_lines

# ============================
# Compute story elevations
# ============================
story_lines_sec = sections.get('$ STORIES - IN SEQUENCE FROM TOP', [])
stories_raw = []
for line in story_lines_sec:
    line_s = line.strip()
    m_elev = re.match(r'STORY\s+"([^"]+)"\s+ELEV\s+([-\d.]+)', line_s)
    m_height = re.match(r'STORY\s+"([^"]+)"\s+HEIGHT\s+([-\d.]+)(.*)', line_s)
    if m_elev:
        stories_raw.append({'name': m_elev.group(1), 'elev': float(m_elev.group(2)), 'height': None, 'rest': ''})
    elif m_height:
        rest = m_height.group(3).strip()
        stories_raw.append({'name': m_height.group(1), 'height': float(m_height.group(2)), 'rest': rest})

stories_raw.reverse()
story_elevs = {}
for i, s in enumerate(stories_raw):
    if s.get('elev') is not None:
        story_elevs[s['name']] = s['elev']
    else:
        prev = stories_raw[i-1]
        story_elevs[s['name']] = story_elevs[prev['name']] + s['height']
stories_raw.reverse()

elev_1f = story_elevs.get('1F', 0.6)
below_1f_stories = set()
for name, elev in story_elevs.items():
    if elev <= elev_1f + 0.001:
        below_1f_stories.add(name)

# ============================
# Helper: get second quoted string (the story) from ASSIGN/LOAD lines
# Format: KEYWORD "objname" "storyname" ...
# ============================
def get_second_quoted(line):
    matches = re.findall(r'"([^"]*)"', line)
    if len(matches) >= 2:
        return matches[1]
    return None

# ============================
# POINT COORDINATES (2D plan coords - no Z in e2k)
# In e2k, points are 2D plan coordinates. Story assignment determines Z.
# We identify which points appear in below-1F stories via POINTASSIGN
# ============================
point_section = sections.get('$ POINT COORDINATES', [])
all_point_lines = {}
for line in point_section:
    line_s = line.strip()
    m = re.match(r'POINT\s+"([^"]+)"\s+(.*)', line_s)
    if m:
        all_point_lines[m.group(1)] = line_s

# ============================
# POINT ASSIGNS - filter by story (second quoted = story)
# ============================
pt_assign_section = sections.get('$ POINT ASSIGNS', [])
below_1f_pt_assigns = []
below_1f_point_names = set()
for line in pt_assign_section:
    line_s = line.strip()
    if line_s.startswith('$') or line_s == '':
        continue
    story = get_second_quoted(line_s)
    if story and story in below_1f_stories:
        below_1f_pt_assigns.append(line)
        m = re.match(r'POINTASSIGN\s+"([^"]+)"', line_s)
        if m:
            below_1f_point_names.add(m.group(1))

# ============================
# LINE ASSIGNS - filter by story
# ============================
line_assign_section = sections.get('$ LINE ASSIGNS', [])
below_1f_line_assigns = []
below_1f_line_names_from_assign = set()
for line in line_assign_section:
    line_s = line.strip()
    if line_s.startswith('$') or line_s == '':
        continue
    story = get_second_quoted(line_s)
    if story and story in below_1f_stories:
        below_1f_line_assigns.append(line)
        m = re.match(r'LINEASSIGN\s+"([^"]+)"', line_s)
        if m:
            below_1f_line_names_from_assign.add(m.group(1))

# ============================
# AREA ASSIGNS - filter by story
# ============================
area_assign_section = sections.get('$ AREA ASSIGNS', [])
below_1f_area_assigns = []
below_1f_area_names_from_assign = set()
for line in area_assign_section:
    line_s = line.strip()
    if line_s.startswith('$') or line_s == '':
        continue
    story = get_second_quoted(line_s)
    if story and story in below_1f_stories:
        below_1f_area_assigns.append(line)
        m = re.match(r'AREAASSIGN\s+"([^"]+)"', line_s)
        if m:
            below_1f_area_names_from_assign.add(m.group(1))

# ============================
# LINE CONNECTIVITIES - filter by line names found in below-1F assigns
# ============================
line_conn_section = sections.get('$ LINE CONNECTIVITIES', [])
below_1f_line_data = []
for line in line_conn_section:
    line_s = line.strip()
    if line_s.startswith('$') or line_s == '':
        continue
    m = re.match(r'LINE\s+"([^"]+)"', line_s)
    if m and m.group(1) in below_1f_line_names_from_assign:
        below_1f_line_data.append(line)

# ============================
# AREA CONNECTIVITIES - filter by area names found in below-1F assigns
# ============================
area_conn_section = sections.get('$ AREA CONNECTIVITIES', [])
below_1f_area_data = []
for line in area_conn_section:
    line_s = line.strip()
    if line_s.startswith('$') or line_s == '':
        continue
    m = re.match(r'AREA\s+"([^"]+)"', line_s)
    if m and m.group(1) in below_1f_area_names_from_assign:
        below_1f_area_data.append(line)

# ============================
# POINT COORDINATES for below-1F points
# ============================
below_1f_point_coord_lines = []
for pname in sorted(below_1f_point_names):
    if pname in all_point_lines:
        below_1f_point_coord_lines.append(all_point_lines[pname])

# ============================
# STATIC LOADS section (this section contains LOADCASE definitions + seismic/wind params)
# Not object-specific, so include the entire section
# ============================
static_load_section = sections.get('$ STATIC LOADS', [])

# ============================
# AREA OBJECT LOADS - filter by story (second quoted = story)
# ============================
area_load_section = sections.get('$ AREA OBJECT LOADS', [])
below_1f_area_loads = []
for line in area_load_section:
    line_s = line.strip()
    if line_s.startswith('$') or line_s == '':
        continue
    story = get_second_quoted(line_s)
    if story and story in below_1f_stories:
        below_1f_area_loads.append(line)

print(f"Points at/below 1F (via POINTASSIGN): {len(below_1f_point_names)}")
print(f"Lines at/below 1F (via LINEASSIGN): {len(below_1f_line_names_from_assign)}")
print(f"Areas at/below 1F (via AREAASSIGN): {len(below_1f_area_names_from_assign)}")
print(f"Line connectivities matched: {len(below_1f_line_data)}")
print(f"Area connectivities matched: {len(below_1f_area_data)}")
print(f"Point assigns: {len(below_1f_pt_assigns)}")
print(f"Line assigns: {len(below_1f_line_assigns)}")
print(f"Area assigns: {len(below_1f_area_assigns)}")
print(f"Area object loads: {len(below_1f_area_loads)}")

# ============================
# Build output
# ============================
out = []
out.append("# OLD Model (ALL) - Structural Data Extraction")
out.append("# Source: 2025-1111_ALL_BUT RC_KpKvKw.e2k")
out.append("# Focus: 1F and below (basement structure)")
out.append("")

# 1. STORIES
out.append("## 1. STORIES")
out.append("")
out.append("Story definitions (top to bottom) with computed elevations:")
out.append("")
out.append("| Story | Height (m) | Elevation (m) | Master/Similar | At/Below 1F |")
out.append("|-------|-----------|---------------|----------------|-------------|")
for s in stories_raw:
    name = s['name']
    height = s.get('height')
    elev = story_elevs[name]
    rest = s.get('rest', '')
    h_str = str(height) if height else "---"
    marker = "YES" if name in below_1f_stories else ""
    out.append(f"| {name} | {h_str} | {elev:.1f} | {rest} | {marker} |")
out.append("")
out.append("**Key basement stories: 1F (elev 0.6), B1F (-3.6), B2F (-6.7), B3F (-9.8), B4F (-12.9), B5F (-16.0), B6F (-19.1), BASE (-22.2)**")
out.append("")

# Raw stories section
out.append("### Raw STORIES data")
out.append("")
out.append("```")
for line in story_lines_sec:
    out.append(line.rstrip())
out.append("```")
out.append("")

# 1b. DIAPHRAGM NAMES
out.append("## 1b. DIAPHRAGM NAMES")
out.append("")
out.append("```")
for line in sections.get('$ DIAPHRAGM NAMES', []):
    out.append(line.rstrip())
out.append("```")
out.append("")

# 2. GRIDS
out.append("## 2. GRIDS")
out.append("")
out.append("### X-Direction Grids")
out.append("")
out.append("| Label | Coord (m) |")
out.append("|-------|----------|")
for line in sections.get('$ GRIDS', []):
    m = re.search(r'LABEL\s+"([^"]+)"\s+DIR\s+"X"\s+COORD\s+([-\d.E+]+)', line)
    if m:
        out.append(f"| {m.group(1)} | {m.group(2)} |")
out.append("")

out.append("### Y-Direction Grids")
out.append("")
out.append("| Label | Coord (m) |")
out.append("|-------|----------|")
for line in sections.get('$ GRIDS', []):
    m = re.search(r'LABEL\s+"([^"]+)"\s+DIR\s+"Y"\s+COORD\s+([-\d.E+]+)', line)
    if m:
        out.append(f"| {m.group(1)} | {m.group(2)} |")
out.append("")

out.append("### Full Raw Grid Data")
out.append("")
out.append("```")
for line in sections.get('$ GRIDS', []):
    out.append(line.rstrip())
out.append("```")
out.append("")

# 3. FRAME SECTIONS
out.append("## 3. FRAME SECTIONS")
out.append("")
frame_sec_lines = sections.get('$ FRAME SECTIONS', [])
defs = []
mods = []
for line in frame_sec_lines:
    line_s = line.strip()
    if line_s.startswith('$') or line_s == '':
        continue
    if 'SHAPE' in line_s:
        defs.append(line_s)
    elif 'MOD' in line_s:
        mods.append(line_s)

rc_rect = [d for d in defs if 'Rectangular' in d]
steel_i = [d for d in defs if 'I/Wide Flange' in d]
general = [d for d in defs if 'General' in d]
auto_select = [d for d in defs if 'Auto Select' in d]

out.append(f"Total section definitions: {len(defs)}")
out.append(f"Total modifier lines: {len(mods)}")
out.append("")

out.append(f"### 3a. Rectangular (RC/SRC) Sections ({len(rc_rect)})")
out.append("")
out.append("```")
for d in rc_rect:
    out.append(d)
out.append("```")
out.append("")

out.append(f"### 3b. Steel I/Wide Flange Sections ({len(steel_i)})")
out.append("")
out.append("```")
for d in steel_i:
    out.append(d)
out.append("```")
out.append("")

out.append(f"### 3c. General (CFT Composite) Sections ({len(general)})")
out.append("")
out.append("```")
for d in general:
    out.append(d)
out.append("```")
out.append("")

out.append(f"### 3d. Auto Select Lists ({len(auto_select)})")
out.append("")
out.append("```")
for d in auto_select:
    out.append(d)
out.append("```")
out.append("")

out.append(f"### 3e. Section Modifiers ({len(mods)})")
out.append("")
out.append("```")
for m in mods:
    out.append(m)
out.append("```")
out.append("")

# AUTO SELECT SECTION LISTS
out.append("### 3f. AUTO SELECT SECTION LISTS (detail)")
out.append("")
out.append("```")
for line in sections.get('$ AUTO SELECT SECTION LISTS', []):
    out.append(line.rstrip())
out.append("```")
out.append("")

# REBAR DEFINITIONS
out.append("### 3g. REBAR DEFINITIONS")
out.append("")
out.append("```")
for line in sections.get('$ REBAR DEFINITIONS', []):
    out.append(line.rstrip())
out.append("```")
out.append("")

# 4. CONCRETE SECTIONS
out.append("## 4. CONCRETE SECTIONS")
out.append("")
out.append("```")
for line in sections.get('$ CONCRETE SECTIONS', []):
    out.append(line.rstrip())
out.append("```")
out.append("")

# 5. WALL/SLAB/DECK PROPERTIES
out.append("## 5. WALL/SLAB/DECK PROPERTIES")
out.append("")
out.append("```")
for line in sections.get('$ WALL/SLAB/DECK PROPERTIES', []):
    out.append(line.rstrip())
out.append("```")
out.append("")

# 6. POINT COORDINATES at/below 1F
out.append("## 6. POINT COORDINATES (at/below 1F)")
out.append("")
out.append(f"Total points in model: {len(all_point_lines)}")
out.append(f"Points assigned to stories at/below 1F: {len(below_1f_point_names)}")
out.append("")
out.append("Note: e2k POINT COORDINATES are 2D plan (X, Y). Story assignment determines Z.")
out.append("")
out.append("```")
for pl in below_1f_point_coord_lines:
    out.append(pl)
out.append("```")
out.append("")

# 7. LINE CONNECTIVITIES
out.append("## 7. LINE CONNECTIVITIES (at/below 1F)")
out.append("")
out.append(f"Total lines at/below 1F: {len(below_1f_line_names_from_assign)}")
out.append(f"Line connectivities matched: {len(below_1f_line_data)}")
out.append("")
out.append("```")
for line in below_1f_line_data:
    out.append(line.rstrip())
out.append("```")
out.append("")

# 8. AREA CONNECTIVITIES
out.append("## 8. AREA CONNECTIVITIES (at/below 1F)")
out.append("")
out.append(f"Total areas at/below 1F: {len(below_1f_area_names_from_assign)}")
out.append(f"Area connectivities matched: {len(below_1f_area_data)}")
out.append("")
out.append("```")
for line in below_1f_area_data:
    out.append(line.rstrip())
out.append("```")
out.append("")

# 9. POINT ASSIGNS
out.append("## 9. POINT ASSIGNS (at/below 1F)")
out.append("")
out.append(f"Total point assign lines at/below 1F: {len(below_1f_pt_assigns)}")
out.append("")
out.append("```")
for line in below_1f_pt_assigns:
    out.append(line.rstrip())
out.append("```")
out.append("")

# 10. LINE ASSIGNS
out.append("## 10. LINE ASSIGNS (at/below 1F)")
out.append("")
out.append(f"Total line assign lines at/below 1F: {len(below_1f_line_assigns)}")
out.append("")
out.append("```")
for line in below_1f_line_assigns:
    out.append(line.rstrip())
out.append("```")
out.append("")

# 11. AREA ASSIGNS
out.append("## 11. AREA ASSIGNS (at/below 1F)")
out.append("")
out.append(f"Total area assign lines at/below 1F: {len(below_1f_area_assigns)}")
out.append("")
out.append("```")
for line in below_1f_area_assigns:
    out.append(line.rstrip())
out.append("```")
out.append("")

# 12. STATIC LOADS (full section - load case definitions)
out.append("## 12. STATIC LOADS (full section - load case definitions)")
out.append("")
out.append("```")
for line in static_load_section:
    out.append(line.rstrip())
out.append("```")
out.append("")

# 13. AREA OBJECT LOADS
out.append("## 13. AREA OBJECT LOADS (at/below 1F)")
out.append("")
out.append(f"Total area load lines at/below 1F: {len(below_1f_area_loads)}")
out.append("")
out.append("```")
for line in below_1f_area_loads:
    out.append(line.rstrip())
out.append("```")
out.append("")

# 14. PIER/SPANDREL NAMES
out.append("## 14. PIER/SPANDREL NAMES")
out.append("")
out.append("```")
for line in sections.get('$ PIER/SPANDREL NAMES', []):
    out.append(line.rstrip())
out.append("```")
out.append("")

# 15. MATERIAL PROPERTIES
out.append("## 15. MATERIAL PROPERTIES (for reference)")
out.append("")
out.append("```")
for line in sections.get('$ MATERIAL PROPERTIES', []):
    out.append(line.rstrip())
out.append("```")
out.append("")

# SUMMARY
out.append("## SUMMARY")
out.append("")
out.append(f"- Total stories: {len(stories_raw)}")
out.append(f"- Stories at/below 1F: {len(below_1f_stories)} ({', '.join(sorted(below_1f_stories, key=lambda x: story_elevs.get(x, 0), reverse=True))})")
x_dir = 'DIR "X"'
y_dir = 'DIR "Y"'
x_count = sum(1 for l in sections.get('$ GRIDS', []) if x_dir in l)
y_count = sum(1 for l in sections.get('$ GRIDS', []) if y_dir in l)
out.append(f"- X-grids: {x_count}")
out.append(f"- Y-grids: {y_count}")
out.append(f"- Frame section definitions: {len(defs)} ({len(rc_rect)} rectangular, {len(steel_i)} I-sections, {len(general)} general/CFT, {len(auto_select)} auto-select)")
out.append(f"- Section modifier lines: {len(mods)}")
out.append(f"- Total points in model: {len(all_point_lines)}, at/below 1F: {len(below_1f_point_names)}")
out.append(f"- Lines at/below 1F: {len(below_1f_line_names_from_assign)} (connectivity records matched: {len(below_1f_line_data)})")
out.append(f"- Areas at/below 1F: {len(below_1f_area_names_from_assign)} (connectivity records matched: {len(below_1f_area_data)})")
out.append(f"- Point assigns at/below 1F: {len(below_1f_pt_assigns)} lines")
out.append(f"- Line assigns at/below 1F: {len(below_1f_line_assigns)} lines")
out.append(f"- Area assigns at/below 1F: {len(below_1f_area_assigns)} lines")
out.append(f"- Area object loads at/below 1F: {len(below_1f_area_loads)} lines")
out.append(f"- Pier names: P1")
out.append(f"- Spandrel names: S1")
out.append("")

# Write output
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print(f"\nOutput written to: {out_path}")
print(f"Total output lines: {len(out)}")
