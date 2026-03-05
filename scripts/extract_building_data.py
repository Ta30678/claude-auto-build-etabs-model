"""
Extract above-1MF structural data from individual building models (A/B/C/D).
Also extracts grid line information for integration.
Outputs structured data files for merge.

Usage: python extract_building_data.py A   (or B, C, D)
"""
import re, json, sys, os

BASE = "C:/Users/User/Desktop/V22 AGENTIC MODEL/ETABS REF/大陳"

BUILDING_FILES = {
    'A': f"{BASE}/A/2026-0303_A_SC_KpKvKw.e2k",
    'B': f"{BASE}/B/2026-0303_B_SC_KpKvKw.e2k",
    'C': f"{BASE}/C/2026-0304_C_SC_KpKvKw.e2k",
    'D': f"{BASE}/D/2026-0303_D_SC_KpKvKw.e2k",
}

# Stories at 1MF and above (the ones we want from A/B/C/D)
ABOVE_1MF_STORIES = {
    '1MF', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F',
    '11F', '12F', '13F', '14F', '15F', '16F', '17F', '18F', '19F', '20F',
    '21F', '22F', '23F', '24F', '25F', '26F', '27F', '28F', '29F', '30F',
    '31F', '32F', '33F', '34F', 'R1F', 'R2F', 'R3F', 'PRF'
}


def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def get_units(content):
    """Detect units from CONTROLS section."""
    m = re.search(r'UNITS\s+"(\w+)"\s+"(\w+)"', content)
    if m:
        return m.group(1), m.group(2)  # force, length
    return 'TON', 'M'


def get_length_scale(length_unit):
    """Return multiplier to convert to meters."""
    if length_unit == 'CM':
        return 0.01
    elif length_unit == 'MM':
        return 0.001
    return 1.0


def extract_section(content, section_name):
    """Extract raw text of a section."""
    pattern = re.compile(
        rf'^\$ {re.escape(section_name)}\s*$(.*?)(?=^\$ |\Z)',
        re.MULTILINE | re.DOTALL
    )
    m = pattern.search(content)
    if m:
        return m.group(1).strip()
    return ''


def parse_point_coordinates(section_text, scale):
    """Parse POINT COORDINATES section. Returns dict {label: (x_m, y_m)}."""
    points = {}
    for line in section_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # POINT "label" X Y  (sometimes with extra spaces or scientific notation)
        m = re.match(r'POINT\s+"([^"]+)"\s+([-\d.E+]+)\s+([-\d.E+]+)', line)
        if m:
            label = m.group(1)
            x = float(m.group(2)) * scale
            y = float(m.group(3)) * scale
            points[label] = (round(x, 6), round(y, 6))
    return points


def parse_line_connectivities(section_text):
    """Parse LINE CONNECTIVITIES. Returns dict {label: {type, point_i, point_j, nstories}}."""
    lines = {}
    for raw_line in section_text.split('\n'):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        # LINE "label" COLUMN/BEAM "pointI" "pointJ" numStories
        m = re.match(r'LINE\s+"([^"]+)"\s+(\w+)\s+"([^"]+)"\s+"([^"]+)"\s+(\d+)', raw_line)
        if m:
            label = m.group(1)
            elem_type = m.group(2)
            point_i = m.group(3)
            point_j = m.group(4)
            nstories = int(m.group(5))
            lines[label] = {
                'type': elem_type,
                'point_i': point_i,
                'point_j': point_j,
                'nstories': nstories,
                'raw': raw_line
            }
    return lines


def parse_area_connectivities(section_text):
    """Parse AREA CONNECTIVITIES. Returns dict {label: raw_line}."""
    areas = {}
    for raw_line in section_text.split('\n'):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        m = re.match(r'AREA\s+"([^"]+)"\s+(.*)', raw_line)
        if m:
            label = m.group(1)
            areas[label] = raw_line
    return areas


def parse_assigns(section_text, keyword='LINEASSIGN'):
    """Parse LINEASSIGN/AREAASSIGN/POINTASSIGN sections.
    Returns dict {(label, story): raw_line} and also {label: set_of_stories}.
    """
    assigns = {}
    label_stories = {}
    for line in section_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(rf'{keyword}\s+"([^"]+)"\s+"([^"]+)"\s+(.*)', line)
        if m:
            label = m.group(1)
            story = m.group(2)
            assigns[(label, story)] = line
            if label not in label_stories:
                label_stories[label] = set()
            label_stories[label].add(story)
    return assigns, label_stories


def filter_assigns_by_stories(assigns, target_stories):
    """Filter assigns to only include target stories."""
    return {k: v for k, v in assigns.items() if k[1] in target_stories}


def get_labels_for_stories(assigns, target_stories):
    """Get set of element labels that appear in target stories."""
    return {k[0] for k, v in assigns.items() if k[1] in target_stories}


def extract_load_section(content, section_name, target_element_labels=None):
    """Extract load lines that reference target elements."""
    text = extract_section(content, section_name)
    if not text:
        return []

    if target_element_labels is None:
        return text.split('\n')

    result = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Check if line references any target element
        m = re.match(r'\w+\s+"([^"]+)"', line)
        if m and m.group(1) in target_element_labels:
            result.append(line)
    return result


def extract_building(building_name):
    """Extract above-1MF data from a building model."""
    filepath = BUILDING_FILES[building_name]
    print(f"\n{'='*60}")
    print(f"Extracting building {building_name}: {filepath}")
    print(f"{'='*60}")

    content = read_file(filepath)
    force_unit, length_unit = get_units(content)
    scale = get_length_scale(length_unit)
    print(f"Units: {force_unit}/{length_unit}, scale={scale}")

    # Parse grid lines
    grid_text = extract_section(content, 'GRIDS')
    grids = {}
    for line in grid_text.split('\n'):
        m = re.search(r'LABEL\s+"([^"]+)"\s+DIR\s+"([^"]+)"\s+COORD\s+([-\d.E+]+)', line)
        if m:
            grids[m.group(1)] = {'dir': m.group(2), 'coord': round(float(m.group(3)) * scale, 6)}
    print(f"Grid lines: {len(grids)}")

    # Parse points
    point_text = extract_section(content, 'POINT COORDINATES')
    points = parse_point_coordinates(point_text, scale)
    print(f"Total points: {len(points)}")

    # Parse line connectivities
    line_conn_text = extract_section(content, 'LINE CONNECTIVITIES')
    line_conns = parse_line_connectivities(line_conn_text)
    print(f"Total line connectivities: {len(line_conns)}")

    # Parse area connectivities
    area_conn_text = extract_section(content, 'AREA CONNECTIVITIES')
    area_conns = parse_area_connectivities(area_conn_text)
    print(f"Total area connectivities: {len(area_conns)}")

    # Parse LINE ASSIGNS
    line_assign_text = extract_section(content, 'LINE ASSIGNS')
    line_assigns, line_label_stories = parse_assigns(line_assign_text, 'LINEASSIGN')
    print(f"Total line assigns: {len(line_assigns)}")

    # Parse AREA ASSIGNS
    area_assign_text = extract_section(content, 'AREA ASSIGNS')
    area_assigns, area_label_stories = parse_assigns(area_assign_text, 'AREAASSIGN')
    print(f"Total area assigns: {len(area_assigns)}")

    # Parse POINT ASSIGNS
    point_assign_text = extract_section(content, 'POINT ASSIGNS')
    point_assigns, point_label_stories = parse_assigns(point_assign_text, 'POINTASSIGN')
    print(f"Total point assigns: {len(point_assigns)}")

    # Filter to above-1MF stories
    above_line_assigns = filter_assigns_by_stories(line_assigns, ABOVE_1MF_STORIES)
    above_area_assigns = filter_assigns_by_stories(area_assigns, ABOVE_1MF_STORIES)
    above_point_assigns = filter_assigns_by_stories(point_assigns, ABOVE_1MF_STORIES)

    above_line_labels = get_labels_for_stories(line_assigns, ABOVE_1MF_STORIES)
    above_area_labels = get_labels_for_stories(area_assigns, ABOVE_1MF_STORIES)
    above_point_labels = get_labels_for_stories(point_assigns, ABOVE_1MF_STORIES)

    print(f"\nAbove-1MF elements:")
    print(f"  Lines: {len(above_line_labels)} (assigns: {len(above_line_assigns)})")
    print(f"  Areas: {len(above_area_labels)} (assigns: {len(above_area_assigns)})")
    print(f"  Points: {len(above_point_labels)} (assigns: {len(above_point_assigns)})")

    # Get above-1MF line connectivities and their points
    above_line_conns = {k: v for k, v in line_conns.items() if k in above_line_labels}
    above_area_conns = {k: v for k, v in area_conns.items() if k in above_area_labels}

    # Collect all point labels used by above-1MF elements
    used_point_labels = set()
    for l in above_line_conns.values():
        used_point_labels.add(l['point_i'])
        used_point_labels.add(l['point_j'])
    # For area conns, extract point labels from raw text
    for raw in above_area_conns.values():
        for pm in re.finditer(r'"(\d+)"', raw):
            used_point_labels.add(pm.group(1))
    # Also add explicitly assigned points
    used_point_labels.update(above_point_labels)

    above_points = {k: v for k, v in points.items() if k in used_point_labels}
    print(f"  Points used by elements: {len(above_points)}")

    # Count columns and beams
    columns = [l for l in above_line_conns.values() if l['type'] == 'COLUMN']
    beams = [l for l in above_line_conns.values() if l['type'] == 'BEAM']
    braces = [l for l in above_line_conns.values() if l['type'] == 'BRACE']
    print(f"  Columns: {len(columns)}, Beams: {len(beams)}, Braces: {len(braces)}")

    # Extract loads for above-1MF elements
    static_loads_text = extract_section(content, 'STATIC LOADS')
    area_loads_text = extract_section(content, 'AREA OBJECT LOADS')

    # Save raw section texts for direct merge
    result = {
        'building': building_name,
        'units': {'force': force_unit, 'length': length_unit, 'scale': scale},
        'grids': grids,
        'above_1mf': {
            'point_coordinates': above_points,
            'line_connectivities': {k: v['raw'] for k, v in above_line_conns.items()},
            'area_connectivities': above_area_conns,
            'line_assigns': {f"{k[0]}|{k[1]}": v for k, v in above_line_assigns.items()},
            'area_assigns': {f"{k[0]}|{k[1]}": v for k, v in above_area_assigns.items()},
            'point_assigns': {f"{k[0]}|{k[1]}": v for k, v in above_point_assigns.items()},
        },
        'stats': {
            'total_points': len(points),
            'total_lines': len(line_conns),
            'total_areas': len(area_conns),
            'above_1mf_points': len(above_points),
            'above_1mf_lines': len(above_line_labels),
            'above_1mf_areas': len(above_area_labels),
            'above_1mf_columns': len(columns),
            'above_1mf_beams': len(beams),
        }
    }

    # Save to JSON
    outpath = f"{BASE}/extract_{building_name}.json"
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    print(f"\nSaved to: {outpath}")
    print(f"File size: {os.path.getsize(outpath) / 1024 / 1024:.1f} MB")

    return result


def extract_old_basement():
    """Extract basement data from OLD model."""
    filepath = f"{BASE}/ALL/OLD/2025-1111_ALL_BUT RC_KpKvKw.e2k"
    print(f"\n{'='*60}")
    print(f"Extracting OLD basement: {filepath}")
    print(f"{'='*60}")

    content = read_file(filepath)
    force_unit, length_unit = get_units(content)
    scale = get_length_scale(length_unit)
    print(f"Units: {force_unit}/{length_unit}, scale={scale}")

    # All data is already basement (B6F-1F), so take everything
    sections_to_extract = [
        'POINT COORDINATES', 'LINE CONNECTIVITIES', 'AREA CONNECTIVITIES',
        'POINT ASSIGNS', 'LINE ASSIGNS', 'AREA ASSIGNS',
        'STATIC LOADS', 'AREA OBJECT LOADS'
    ]

    raw_data = {}
    for sec in sections_to_extract:
        raw_data[sec] = extract_section(content, sec)
        lines_count = len([l for l in raw_data[sec].split('\n') if l.strip()])
        print(f"  {sec}: {lines_count} lines")

    # Save raw sections
    outpath = f"{BASE}/extract_OLD.json"
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump({
            'building': 'OLD',
            'units': {'force': force_unit, 'length': length_unit, 'scale': scale},
            'raw_sections': raw_data,
        }, f, indent=1, ensure_ascii=False)
    print(f"\nSaved to: {outpath}")

    return raw_data


if __name__ == '__main__':
    if len(sys.argv) > 1:
        building = sys.argv[1].upper()
        if building == 'OLD':
            extract_old_basement()
        elif building in BUILDING_FILES:
            extract_building(building)
        elif building == 'ALL':
            extract_old_basement()
            for b in ['A', 'B', 'C', 'D']:
                extract_building(b)
        else:
            print(f"Unknown building: {building}")
    else:
        print("Usage: python extract_building_data.py [A|B|C|D|OLD|ALL]")
