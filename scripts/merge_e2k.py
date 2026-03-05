"""
Merge ETABS e2k files for 大陳 project.
Combines:
  - 2026-0305 template (definitions, combos, etc.)
  - OLD basement (B6F-1F geometry)
  - A/B/C/D above-1MF structure (with renumbered labels)
  - Unified grid lines from A/B/C/D

Handles unit conversion (A/C/D are KGF-CM, template is TON-M).

Output: merged e2k file ready to import into ETABS.
"""
import re, json, os, sys
from collections import OrderedDict

BASE = "C:/Users/User/Desktop/V22 AGENTIC MODEL/ETABS REF/大陳"
TEMPLATE = f"{BASE}/ALL/2026-0305/2026-0305_ALL_BUT RC_KpKvKw.e2k"
OLD_FILE = f"{BASE}/ALL/OLD/2025-1111_ALL_BUT RC_KpKvKw.e2k"
OUTPUT = f"{BASE}/ALL/2026-0305/MERGED_ALL.e2k"

BUILDING_FILES = {
    'A': f"{BASE}/A/2026-0303_A_SC_KpKvKw.e2k",
    'B': f"{BASE}/B/2026-0303_B_SC_KpKvKw.e2k",
    'C': f"{BASE}/C/2026-0304_C_SC_KpKvKw.e2k",
    'D': f"{BASE}/D/2026-0303_D_SC_KpKvKw.e2k",
}

ABOVE_1MF_STORIES = {
    '1MF', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F',
    '11F', '12F', '13F', '14F', '15F', '16F', '17F', '18F', '19F', '20F',
    '21F', '22F', '23F', '24F', '25F', '26F', '27F', '28F', '29F', '30F',
    '31F', '32F', '33F', '34F', 'R1F', 'R2F', 'R3F', 'PRF'
}


def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def split_sections(content):
    """Split e2k content into ordered sections."""
    sections = OrderedDict()
    pattern = re.compile(r'^(\$ .+)$', re.MULTILINE)
    matches = list(pattern.finditer(content))
    # Include file header (before first $)
    if matches:
        header = content[:matches[0].start()].strip()
        if header:
            sections['__HEADER__'] = header

    for i, match in enumerate(matches):
        section_name = match.group(1).strip()
        start = match.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(content)
        section_text = content[start:end].rstrip()
        sections[section_name] = section_text
    return sections


def get_units(content):
    m = re.search(r'UNITS\s+"(\w+)"\s+"(\w+)"', content)
    if m:
        return m.group(1), m.group(2)
    return 'TON', 'M'


def get_length_scale(length_unit):
    if length_unit == 'CM': return 0.01
    elif length_unit == 'MM': return 0.001
    return 1.0


def convert_point_line(line, scale):
    """Convert POINT coordinates from one unit to meters."""
    m = re.match(r'(\s*POINT\s+"[^"]+"\s+)([-\d.E+]+)\s+([-\d.E+]+)(.*)', line)
    if m:
        prefix = m.group(1)
        x = float(m.group(2)) * scale
        y = float(m.group(3)) * scale
        suffix = m.group(4) if m.group(4) else ''
        return f'{prefix}{x:.6f} {y:.6f}{suffix}'
    return line


def rename_label_in_line(line, prefix, label_map=None):
    """Rename element labels in a raw e2k line by adding prefix.
    Handles POINT "xxx", LINE "xxx", AREA "xxx", etc.
    Also handles POINTI, POINTJ references.
    """
    # This is for POINT COORDINATES: POINT "label" X Y
    def replace_point(m):
        old_label = m.group(1)
        new_label = f"{prefix}{old_label}"
        if label_map is not None:
            label_map[old_label] = new_label
        return f'POINT "{new_label}"'

    # For LINE CONNECTIVITIES: LINE "label" TYPE "point_i" "point_j" num
    def replace_line_conn(m):
        line_label = m.group(1)
        line_type = m.group(2)
        pi = m.group(3)
        pj = m.group(4)
        rest = m.group(5)
        new_line = f"{prefix}{line_label}"
        new_pi = f"{prefix}{pi}"
        new_pj = f"{prefix}{pj}"
        return f'LINE  "{new_line}"  {line_type}  "{new_pi}"  "{new_pj}"{rest}'

    # For AREA CONNECTIVITIES: AREA "label" PANEL numPts "p1" "p2" ... num1 num2
    def replace_area_conn(line_text):
        # Replace area label
        line_text = re.sub(
            r'AREA\s+"([^"]+)"',
            lambda m: f'AREA "{prefix}{m.group(1)}"',
            line_text, count=1
        )
        # Replace all quoted numeric point references after PANEL numPts
        # Find the part after PANEL N and replace quoted numbers
        parts = re.split(r'(PANEL\s+\d+\s+)', line_text, maxsplit=1)
        if len(parts) == 3:
            pre, panel, point_data = parts
            # Replace all "number" references with prefixed versions
            point_data = re.sub(
                r'"(\d+)"',
                lambda m: f'"{prefix}{m.group(1)}"',
                point_data
            )
            return pre + panel + point_data
        return line_text

    # Detect line type
    stripped = line.strip()

    if stripped.startswith('POINT '):
        result = re.sub(r'POINT\s+"([^"]+)"', replace_point, line, count=1)
        return result

    elif stripped.startswith('LINE '):
        result = re.sub(
            r'LINE\s+"([^"]+)"\s+(\w+)\s+"([^"]+)"\s+"([^"]+)"(.*)',
            replace_line_conn, line, count=1
        )
        return result

    elif stripped.startswith('AREA '):
        return replace_area_conn(line)

    elif stripped.startswith('POINTASSIGN '):
        return re.sub(r'POINTASSIGN\s+"([^"]+)"',
                       lambda m: f'POINTASSIGN  "{prefix}{m.group(1)}"',
                       line, count=1)

    elif stripped.startswith('LINEASSIGN '):
        return re.sub(r'LINEASSIGN\s+"([^"]+)"',
                       lambda m: f'LINEASSIGN  "{prefix}{m.group(1)}"',
                       line, count=1)

    elif stripped.startswith('AREAASSIGN '):
        return re.sub(r'AREAASSIGN\s+"([^"]+)"',
                       lambda m: f'AREAASSIGN  "{prefix}{m.group(1)}"',
                       line, count=1)

    elif stripped.startswith('LINELOAD ') or stripped.startswith('AREALOAD '):
        kw = stripped.split()[0]
        return re.sub(rf'{kw}\s+"([^"]+)"',
                       lambda m: f'{kw}  "{prefix}{m.group(1)}"',
                       line, count=1)

    return line


def filter_lines_by_story(text, target_stories, keyword):
    """Filter LINEASSIGN/AREAASSIGN/POINTASSIGN lines to target stories."""
    result = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(rf'{keyword}\s+"[^"]+"\s+"([^"]+)"', stripped)
        if m and m.group(1) in target_stories:
            result.append(stripped)
    return result


def get_line_labels_for_stories(assign_text, target_stories, keyword='LINEASSIGN'):
    """Get set of element labels in target stories."""
    labels = set()
    for line in assign_text.split('\n'):
        stripped = line.strip()
        m = re.match(rf'{keyword}\s+"([^"]+)"\s+"([^"]+)"', stripped)
        if m and m.group(2) in target_stories:
            labels.add(m.group(1))
    return labels


def filter_connectivities_by_labels(text, target_labels, keyword='LINE'):
    """Filter LINE/AREA CONNECTIVITIES to only include target labels."""
    result = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(rf'{keyword}\s+"([^"]+)"', stripped)
        if m and m.group(1) in target_labels:
            result.append(stripped)
    return result


def get_point_labels_from_conns(line_conn_lines, area_conn_lines):
    """Extract all point labels referenced in connectivities."""
    points = set()
    for line in line_conn_lines:
        for m in re.finditer(r'"(\d+)"', line):
            points.add(m.group(1))
    for line in area_conn_lines:
        for m in re.finditer(r'"(\d+)"', line):
            points.add(m.group(1))
    return points


def filter_points_by_labels(text, target_labels):
    """Filter POINT COORDINATES to target labels."""
    result = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(r'POINT\s+"([^"]+)"', stripped)
        if m and m.group(1) in target_labels:
            result.append(stripped)
    return result


def filter_loads_by_labels(text, target_labels, keyword='LINELOAD'):
    """Filter load lines by element labels."""
    result = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(rf'{keyword}\s+"([^"]+)"', stripped)
        if m and m.group(1) in target_labels:
            result.append(stripped)
        elif not m:
            # Non-element-specific lines (e.g., LOADCASE definitions)
            result.append(stripped)
    return result


def extract_missing_sections(building_file, section_names, target_unit_m=True):
    """Extract FRAMESECTION and CONCRETESECTION definitions for named sections.
    Converts from building's units to TON/M if needed.
    """
    content = read_file(building_file)
    _, length_unit = get_units(content)
    scale = get_length_scale(length_unit)
    need_convert = (length_unit != 'M')

    # Extract FRAME SECTIONS
    frame_sec_text = ''
    m = re.search(r'\$ FRAME SECTIONS(.*?)(?=\$ )', content, re.DOTALL)
    if m:
        frame_sec_text = m.group(1)

    # Extract CONCRETE SECTIONS
    conc_sec_text = ''
    m = re.search(r'\$ CONCRETE SECTIONS(.*?)(?=\$ )', content, re.DOTALL)
    if m:
        conc_sec_text = m.group(1)

    frame_lines = []
    conc_lines = []

    for sec_name in section_names:
        # Find FRAMESECTION lines for this section
        for line in frame_sec_text.split('\n'):
            if f'"{sec_name}"' in line:
                if need_convert:
                    # Convert dimensional values (D, BF, TF, TW, etc.)
                    # This is complex - dimensions are after specific keywords
                    # For now, convert known dimension keywords
                    def convert_dim(m):
                        val = float(m.group(2))
                        return f'{m.group(1)}{val * scale:.6f}'
                    line = re.sub(r'(D\s+)([\d.E+-]+)', convert_dim, line)
                    line = re.sub(r'(BF\s+)([\d.E+-]+)', convert_dim, line)
                    line = re.sub(r'(TF\s+)([\d.E+-]+)', convert_dim, line)
                    line = re.sub(r'(TW\s+)([\d.E+-]+)', convert_dim, line)
                    line = re.sub(r'(DIS\s+)([\d.E+-]+)', convert_dim, line)
                    line = re.sub(r'(WIDTH\s+)([\d.E+-]+)', convert_dim, line)
                    line = re.sub(r'(DEPTH\s+)([\d.E+-]+)', convert_dim, line)
                    # Area: cm² -> m² (scale²)
                    line = re.sub(r'(AREA\s+)([\d.E+-]+)',
                        lambda m2: f'{m2.group(1)}{float(m2.group(2)) * scale * scale:.8f}', line)
                    # Inertia: cm⁴ -> m⁴ (scale⁴)
                    for kw in ['I33', 'I22', 'I23', 'AS2', 'AS3', 'TORSION']:
                        line = re.sub(rf'({kw}\s+)([\d.E+-]+)',
                            lambda m2, s=scale: f'{m2.group(1)}{float(m2.group(2)) * s**4:.12f}', line)
                frame_lines.append(line.strip())

        # Find CONCRETESECTION lines for this section
        for line in conc_sec_text.split('\n'):
            if f'"{sec_name}"' in line:
                if need_convert:
                    # Convert cover dimension
                    line = re.sub(r'(COVER\s+)([\d.E+-]+)',
                        lambda m2: f'{m2.group(1)}{float(m2.group(2)) * scale:.6f}', line)
                    line = re.sub(r'(BARSPACING\s+)([\d.E+-]+)',
                        lambda m2: f'{m2.group(1)}{float(m2.group(2)) * scale:.6f}', line)
                conc_lines.append(line.strip())

    return frame_lines, conc_lines


def build_unified_grids():
    """Build unified grid section from A/B/C/D changes.

    Strategy for conflicting grids:
    - For grids changed by only one model: use that model's value
    - For grids changed by multiple models: use the AVERAGE
    - Grid lines are display-only; actual geometry uses coordinates
    """
    # Load grid comparison data
    with open(f"{BASE}/grid_comparison.json", 'r') as f:
        grid_data = json.load(f)

    unified = {}
    for label, info in grid_data['unified_grids'].items():
        unified[label] = (info['dir'], info['coord'])

    # Check for conflicts (grids changed by >1 model)
    grid_changes = {}  # label -> [(model, new_coord), ...]
    for model, changes in grid_data['changes_by_model'].items():
        for c in changes:
            if c['old'] is not None:
                label = c['label']
                if label not in grid_changes:
                    grid_changes[label] = []
                grid_changes[label].append((model, c['new']))

    conflicts = {k: v for k, v in grid_changes.items() if len(v) > 1}
    if conflicts:
        print("\nGRID CONFLICTS (multiple buildings changed same grid):")
        for label, changes in conflicts.items():
            vals = [c[1] for c in changes]
            avg = sum(vals) / len(vals)
            print(f"  Grid {label}: {changes} -> using average {avg:.4f}m")
            d = unified[label][0]
            unified[label] = (d, round(avg, 4))

    # Build e2k grid text in TON/M (meters)
    lines = []
    lines.append('  COORDSYSTEM "GLOBAL"  TYPE "CARTESIAN"  BUBBLESIZE 1.25')
    # X grids first
    x_grids = [(label, coord) for label, (d, coord) in unified.items() if d == 'X']
    x_grids.sort(key=lambda x: x[1])
    for label, coord in x_grids:
        lines.append(f'  GRID "GLOBAL"  LABEL "{label}"  DIR "X"  COORD {coord}  GRIDTYPE  "PRIMARY"    BUBBLELOC "DEFAULT"  GRIDHIDE "NO"  ')
    # Y grids
    y_grids = [(label, coord) for label, (d, coord) in unified.items() if d == 'Y']
    y_grids.sort(key=lambda x: x[1])
    for label, coord in y_grids:
        lines.append(f'  GRID "GLOBAL"  LABEL "{label}"  DIR "Y"  COORD {coord}  GRIDTYPE  "PRIMARY"    BUBBLELOC "SWITCHED"  GRIDHIDE "NO"  ')

    return '\n'.join(lines)


def process_building_above_1mf(building_name, prefix):
    """Extract above-1MF data from a building and return renamed e2k text blocks."""
    print(f"\n  Processing building {building_name} (prefix={prefix})...")
    filepath = BUILDING_FILES[building_name]
    content = read_file(filepath)
    _, length_unit = get_units(content)
    scale = get_length_scale(length_unit)
    need_convert = (length_unit != 'M')

    # Extract raw sections
    sections = split_sections(content)

    # Get line/area labels for above-1MF stories
    line_assign_text = sections.get('$ LINE ASSIGNS', '')
    area_assign_text = sections.get('$ AREA ASSIGNS', '')
    point_assign_text = sections.get('$ POINT ASSIGNS', '')

    above_line_labels = get_line_labels_for_stories(line_assign_text, ABOVE_1MF_STORIES, 'LINEASSIGN')
    above_area_labels = get_line_labels_for_stories(area_assign_text, ABOVE_1MF_STORIES, 'AREAASSIGN')
    above_point_labels = get_line_labels_for_stories(point_assign_text, ABOVE_1MF_STORIES, 'POINTASSIGN')

    print(f"    Above-1MF: {len(above_line_labels)} lines, {len(above_area_labels)} areas, {len(above_point_labels)} points")

    # Filter connectivities
    line_conn_text = sections.get('$ LINE CONNECTIVITIES', '')
    area_conn_text = sections.get('$ AREA CONNECTIVITIES', '')
    point_text = sections.get('$ POINT COORDINATES', '')

    above_line_conns = filter_connectivities_by_labels(line_conn_text, above_line_labels, 'LINE')
    above_area_conns = filter_connectivities_by_labels(area_conn_text, above_area_labels, 'AREA')

    # Get all point labels used by above-1MF elements
    used_points = get_point_labels_from_conns(above_line_conns, above_area_conns)
    used_points.update(above_point_labels)

    above_points = filter_points_by_labels(point_text, used_points)
    print(f"    Points used: {len(above_points)}")

    # Filter assigns
    above_line_assigns = filter_lines_by_story(line_assign_text, ABOVE_1MF_STORIES, 'LINEASSIGN')
    above_area_assigns = filter_lines_by_story(area_assign_text, ABOVE_1MF_STORIES, 'AREAASSIGN')
    above_point_assigns = filter_lines_by_story(point_assign_text, ABOVE_1MF_STORIES, 'POINTASSIGN')

    # Filter loads
    static_loads_text = sections.get('$ STATIC LOADS', '')
    area_loads_text = sections.get('$ AREA OBJECT LOADS', '')
    above_line_loads = filter_loads_by_labels(static_loads_text, above_line_labels, 'LINELOAD')
    above_area_loads = filter_loads_by_labels(area_loads_text, above_area_labels, 'AREALOAD')

    # Convert coordinates and rename labels
    result = {
        'points': [],
        'line_conns': [],
        'area_conns': [],
        'point_assigns': [],
        'line_assigns': [],
        'area_assigns': [],
        'line_loads': [],
        'area_loads': [],
    }

    for line in above_points:
        renamed = rename_label_in_line(line, prefix)
        if need_convert:
            renamed = convert_point_line(renamed, scale)
        result['points'].append(renamed)

    for line in above_line_conns:
        result['line_conns'].append(rename_label_in_line(line, prefix))

    for line in above_area_conns:
        result['area_conns'].append(rename_label_in_line(line, prefix))

    for line in above_point_assigns:
        result['point_assigns'].append(rename_label_in_line(line, prefix))

    for line in above_line_assigns:
        result['line_assigns'].append(rename_label_in_line(line, prefix))

    for line in above_area_assigns:
        result['area_assigns'].append(rename_label_in_line(line, prefix))

    # Loads reference element labels - but loads also have unit-dependent values
    # For now, skip load conversion (loads from template are preferred)

    return result


def main():
    print("="*70)
    print("MERGE E2K: 大陳 2026-0305 Model Integration")
    print("="*70)

    # Read template
    print("\n1. Reading template (2026-0305)...")
    template_content = read_file(TEMPLATE)
    template_sections = split_sections(template_content)
    print(f"   Template sections: {len(template_sections)}")

    # Read OLD basement
    print("\n2. Reading OLD basement...")
    old_content = read_file(OLD_FILE)
    old_sections = split_sections(old_content)

    # Build unified grids
    print("\n3. Building unified grid lines...")
    unified_grid_text = build_unified_grids()

    # Extract above-1MF from each building
    print("\n4. Extracting above-1MF structure from A/B/C/D...")
    buildings_data = {}
    for bld, prefix in [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]:
        buildings_data[bld] = process_building_above_1mf(bld, prefix)

    # Collect missing section definitions
    print("\n5. Extracting missing section definitions...")
    # Find all section names used in above-1MF assigns
    all_section_names = set()
    for bld_data in buildings_data.values():
        for line in bld_data['line_assigns']:
            m = re.search(r'SECTION\s+"([^"]+)"', line)
            if m:
                all_section_names.add(m.group(1))
        for line in bld_data['area_assigns']:
            m = re.search(r'SECTION\s+"([^"]+)"', line)
            if m:
                all_section_names.add(m.group(1))

    # Check which are missing from template
    template_frame_secs = set()
    frame_sec_text = template_sections.get('$ FRAME SECTIONS', '')
    for m in re.finditer(r'FRAMESECTION\s+"([^"]+)"', frame_sec_text):
        template_frame_secs.add(m.group(1))

    missing_secs = all_section_names - template_frame_secs
    print(f"   Missing sections: {missing_secs}")

    extra_frame_lines = []
    extra_conc_lines = []
    for bld, filepath in BUILDING_FILES.items():
        fl, cl = extract_missing_sections(filepath, missing_secs)
        extra_frame_lines.extend(fl)
        extra_conc_lines.extend(cl)
    # Deduplicate
    extra_frame_lines = list(dict.fromkeys(extra_frame_lines))
    extra_conc_lines = list(dict.fromkeys(extra_conc_lines))
    print(f"   Additional frame section defs: {len(extra_frame_lines)}")
    print(f"   Additional concrete section defs: {len(extra_conc_lines)}")

    # Build the merged e2k file
    print("\n6. Building merged e2k file...")
    output_lines = []

    # Header
    output_lines.append(f'$ File MERGED_ALL.e2k - Generated by merge script')
    output_lines.append('')

    # PROGRAM INFORMATION
    output_lines.append('$ PROGRAM INFORMATION')
    output_lines.append(template_sections.get('$ PROGRAM INFORMATION', ''))
    output_lines.append('')

    # CONTROLS
    output_lines.append('$ CONTROLS')
    output_lines.append(template_sections.get('$ CONTROLS', ''))
    output_lines.append('')

    # STORIES
    output_lines.append('$ STORIES - IN SEQUENCE FROM TOP')
    output_lines.append(template_sections.get('$ STORIES - IN SEQUENCE FROM TOP', ''))
    output_lines.append('')

    # DIAPHRAGM NAMES
    output_lines.append('$ DIAPHRAGM NAMES')
    output_lines.append(template_sections.get('$ DIAPHRAGM NAMES', ''))
    output_lines.append('')

    # GRIDS (unified)
    output_lines.append('$ GRIDS')
    output_lines.append(unified_grid_text)
    output_lines.append('')

    # MATERIAL PROPERTIES
    output_lines.append('$ MATERIAL PROPERTIES')
    output_lines.append(template_sections.get('$ MATERIAL PROPERTIES', ''))
    output_lines.append('')

    # FRAME SECTIONS (template + extras)
    output_lines.append('$ FRAME SECTIONS')
    output_lines.append(template_sections.get('$ FRAME SECTIONS', ''))
    if extra_frame_lines:
        output_lines.append('  ; --- Additional sections from A/B/C/D ---')
        output_lines.extend(f'  {l}' for l in extra_frame_lines)
    output_lines.append('')

    # AUTO SELECT SECTION LISTS
    if '$ AUTO SELECT SECTION LISTS' in template_sections:
        output_lines.append('$ AUTO SELECT SECTION LISTS')
        output_lines.append(template_sections['$ AUTO SELECT SECTION LISTS'])
        output_lines.append('')

    # REBAR DEFINITIONS
    output_lines.append('$ REBAR DEFINITIONS')
    output_lines.append(template_sections.get('$ REBAR DEFINITIONS', ''))
    output_lines.append('')

    # CONCRETE SECTIONS (template + extras)
    output_lines.append('$ CONCRETE SECTIONS')
    output_lines.append(template_sections.get('$ CONCRETE SECTIONS', ''))
    if extra_conc_lines:
        output_lines.append('  ; --- Additional concrete sections from A/B/C/D ---')
        output_lines.extend(f'  {l}' for l in extra_conc_lines)
    output_lines.append('')

    # WALL/SLAB/DECK PROPERTIES
    output_lines.append('$ WALL/SLAB/DECK PROPERTIES')
    output_lines.append(template_sections.get('$ WALL/SLAB/DECK PROPERTIES', ''))
    output_lines.append('')

    # LINK PROPERTIES
    output_lines.append('$ LINK PROPERTIES')
    output_lines.append(template_sections.get('$ LINK PROPERTIES', ''))
    output_lines.append('')

    # PIER/SPANDREL NAMES
    output_lines.append('$ PIER/SPANDREL NAMES ')
    output_lines.append(template_sections.get('$ PIER/SPANDREL NAMES', template_sections.get('$ PIER/SPANDREL NAMES ', '')))
    output_lines.append('')

    # POINT COORDINATES (OLD basement + A/B/C/D above-1MF)
    output_lines.append('$ POINT COORDINATES')
    output_lines.append('  ; --- OLD basement points (B6F-1F) ---')
    output_lines.append(old_sections.get('$ POINT COORDINATES', ''))
    for bld in ['A', 'B', 'C', 'D']:
        output_lines.append(f'  ; --- Building {bld} points (1MF+) ---')
        output_lines.extend(f'  {l}' for l in buildings_data[bld]['points'])
    output_lines.append('')

    # LINE CONNECTIVITIES
    output_lines.append('$ LINE CONNECTIVITIES')
    output_lines.append('  ; --- OLD basement lines ---')
    output_lines.append(old_sections.get('$ LINE CONNECTIVITIES', ''))
    for bld in ['A', 'B', 'C', 'D']:
        output_lines.append(f'  ; --- Building {bld} lines (1MF+) ---')
        output_lines.extend(f'  {l}' for l in buildings_data[bld]['line_conns'])
    output_lines.append('')

    # AREA CONNECTIVITIES
    output_lines.append('$ AREA CONNECTIVITIES')
    output_lines.append('  ; --- OLD basement areas ---')
    output_lines.append(old_sections.get('$ AREA CONNECTIVITIES', ''))
    for bld in ['A', 'B', 'C', 'D']:
        output_lines.append(f'  ; --- Building {bld} areas (1MF+) ---')
        output_lines.extend(f'  {l}' for l in buildings_data[bld]['area_conns'])
    output_lines.append('')

    # POINT ASSIGNS
    output_lines.append('$ POINT ASSIGNS')
    output_lines.append('  ; --- OLD basement ---')
    output_lines.append(old_sections.get('$ POINT ASSIGNS', ''))
    for bld in ['A', 'B', 'C', 'D']:
        output_lines.append(f'  ; --- Building {bld} (1MF+) ---')
        output_lines.extend(f'  {l}' for l in buildings_data[bld]['point_assigns'])
    output_lines.append('')

    # LINE ASSIGNS
    output_lines.append('$ LINE ASSIGNS')
    output_lines.append('  ; --- OLD basement ---')
    output_lines.append(old_sections.get('$ LINE ASSIGNS', ''))
    for bld in ['A', 'B', 'C', 'D']:
        output_lines.append(f'  ; --- Building {bld} (1MF+) ---')
        output_lines.extend(f'  {l}' for l in buildings_data[bld]['line_assigns'])
    output_lines.append('')

    # AREA ASSIGNS
    output_lines.append('$ AREA ASSIGNS')
    output_lines.append('  ; --- OLD basement ---')
    output_lines.append(old_sections.get('$ AREA ASSIGNS', ''))
    for bld in ['A', 'B', 'C', 'D']:
        output_lines.append(f'  ; --- Building {bld} (1MF+) ---')
        output_lines.extend(f'  {l}' for l in buildings_data[bld]['area_assigns'])
    output_lines.append('')

    # STATIC LOADS
    output_lines.append('$ STATIC LOADS')
    output_lines.append(template_sections.get('$ STATIC LOADS', ''))
    # Add load data from OLD basement
    old_static = old_sections.get('$ STATIC LOADS', '')
    # Filter to only LINELOAD/AREALOAD entries (not LOADCASE defs which are in template)
    for line in old_static.split('\n'):
        stripped = line.strip()
        if stripped.startswith('LINELOAD') or stripped.startswith('POINTLOAD'):
            output_lines.append(f'  {stripped}')
    output_lines.append('')

    # AREA OBJECT LOADS
    output_lines.append('$ AREA OBJECT LOADS')
    output_lines.append(old_sections.get('$ AREA OBJECT LOADS', ''))
    output_lines.append('')

    # Remaining template sections (ANALYSIS OPTIONS, FUNCTIONS, COMBOS, etc.)
    remaining_sections = [
        '$ ANALYSIS OPTIONS', '$ FUNCTIONS', '$ RESPONSE SPECTRUM CASES',
        '$ LOAD COMBINATIONS', '$ STEEL DESIGN PREFERENCES',
        '$ CONCRETE DESIGN PREFERENCES', '$ COMPOSITE DESIGN PREFERENCES',
        '$ WALL DESIGN PREFERENCES', '$ SPECIAL SEISMIC DATA',
        '$ DEVELOPED ELEVATIONS',
    ]
    for sec_name in remaining_sections:
        if sec_name in template_sections:
            output_lines.append(sec_name)
            output_lines.append(template_sections[sec_name])
            output_lines.append('')

    output_lines.append('$ END OF MODEL FILE')
    output_lines.append('')

    # Write output
    output_text = '\n'.join(output_lines)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(output_text)

    output_size = os.path.getsize(OUTPUT)
    total_lines = output_text.count('\n')
    print(f"\n{'='*70}")
    print(f"MERGE COMPLETE!")
    print(f"Output: {OUTPUT}")
    print(f"Size: {output_size / 1024:.1f} KB ({total_lines} lines)")
    print(f"{'='*70}")

    # Summary stats
    total_points = len([l for l in output_text.split('\n') if 'POINT "' in l and 'COORDINATES' not in l])
    total_lines_elem = len([l for l in output_text.split('\n') if re.match(r'\s*LINE\s+"', l)])
    total_areas = len([l for l in output_text.split('\n') if re.match(r'\s*AREA\s+"', l)])
    print(f"\nElement counts:")
    print(f"  Points: ~{total_points}")
    print(f"  Lines: ~{total_lines_elem}")
    print(f"  Areas: ~{total_areas}")


if __name__ == '__main__':
    main()
