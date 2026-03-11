"""
E2K Merge Tool — Combine multiple single-building e2k files into one model.

Takes a base model (with substructure) and adds superstructure from each
building file. Handles unit conversion and label renaming to avoid conflicts.

Usage:
    python -m golden_scripts.tools.gs_merge \\
        --base substructure.e2k \\
        --buildings A=building_A.e2k B=building_B.e2k \\
        --output merged.e2k

    Or from Python:
        from golden_scripts.tools.gs_merge import merge_e2k
        merge_e2k(
            base_path="substructure.e2k",
            building_files={"A": "building_A.e2k", "B": "building_B.e2k"},
            output_path="merged.e2k"
        )
"""
import re
import sys
import argparse
from collections import OrderedDict

from golden_scripts.constants import is_substructure_story
from golden_scripts.tools.e2k_parser import (
    E2KModel,
    filter_raw_lines,
    filter_raw_lines_by_story,
    get_point_labels_from_connectivities,
)
from golden_scripts.tools.e2k_writer import write_e2k, format_float
from golden_scripts.tools.unit_converter import (
    detect_units,
    scale_factor,
    FORCE_TO_TON,
    LENGTH_TO_M,
)


def _convert_point_coords(line_text, length_scale):
    """Convert POINT coordinate values by length_scale."""
    m = re.match(r'(\s*POINT\s+"[^"]+"\s+)([-\d.E+]+)\s+([-\d.E+]+)(.*)', line_text)
    if m:
        x = float(m.group(2)) * length_scale
        y = float(m.group(3)) * length_scale
        return f'{m.group(1)}{format_float(x)} {format_float(y)}{m.group(4)}'
    return line_text


def _rename_label(line_text, prefix, element_keyword):
    """Add a prefix to the element label in a raw e2k line.

    Handles: POINT, LINE, AREA, POINTASSIGN, LINEASSIGN, AREAASSIGN,
             LINELOAD, AREALOAD, POINTLOAD
    """
    if element_keyword in ('LINE',):
        # LINE "label" TYPE "pi" "pj" N
        m = re.match(
            r'(\s*LINE\s+)"([^"]+)"(\s+\w+\s+)"([^"]+)"\s+"([^"]+)"(.*)',
            line_text)
        if m:
            return (f'{m.group(1)}"{prefix}{m.group(2)}"{m.group(3)}'
                    f'"{prefix}{m.group(4)}" "{prefix}{m.group(5)}"{m.group(6)}')

    elif element_keyword in ('AREA',):
        # AREA "label" PANEL N "p1" "p2" ... nums
        result = re.sub(
            r'AREA\s+"([^"]+)"',
            lambda m: f'AREA "{prefix}{m.group(1)}"',
            line_text, count=1)
        # Rename point references after PANEL N
        parts = re.split(r'(PANEL\s+\d+\s+)', result, maxsplit=1)
        if len(parts) == 3:
            pre, panel, point_data = parts
            point_data = re.sub(
                r'"(\d+)"',
                lambda m: f'"{prefix}{m.group(1)}"',
                point_data)
            return pre + panel + point_data
        return result

    elif element_keyword == 'POINT':
        return re.sub(
            r'POINT\s+"([^"]+)"',
            lambda m: f'POINT "{prefix}{m.group(1)}"',
            line_text, count=1)

    else:
        # Generic: KEYWORD "label" -> KEYWORD "prefix+label"
        return re.sub(
            rf'{element_keyword}\s+"([^"]+)"',
            lambda m: f'{element_keyword} "{prefix}{m.group(1)}"',
            line_text, count=1)

    return line_text


def _convert_section_dimensions(raw_text, length_scale, force_scale):
    """Convert dimensional values in FRAMESECTION/CONCRETESECTION definitions.

    Length dimensions: D, BF, TF, TW, DIS, WIDTH, DEPTH, COVER, BARSPACING
    Area dimensions: AREA (length^2)
    Inertia dimensions: I33, I22, AS2, AS3, TORSION (length^4)
    """
    if abs(length_scale - 1.0) < 1e-10:
        return raw_text  # no conversion needed

    result_lines = []
    for line in raw_text.split('\n'):
        # Length dimensions
        for kw in ['D', 'B', 'BF', 'TF', 'TW', 'DIS', 'WIDTH', 'DEPTH',
                    'COVER', 'BARSPACING']:
            line = re.sub(
                rf'(\b{kw}\s+)([-\d.E+]+)',
                lambda m, s=length_scale: f'{m.group(1)}{format_float(float(m.group(2)) * s)}',
                line)
        # Area (length^2)
        line = re.sub(
            r'(\bAREA\s+)([-\d.E+]+)',
            lambda m: f'{m.group(1)}{format_float(float(m.group(2)) * length_scale**2, 8)}',
            line)
        # Inertia (length^4)
        for kw in ['I33', 'I22', 'I23', 'AS2', 'AS3', 'TORSION']:
            line = re.sub(
                rf'(\b{kw}\s+)([-\d.E+]+)',
                lambda m, s=length_scale: f'{m.group(1)}{format_float(float(m.group(2)) * s**4, 12)}',
                line)
        result_lines.append(line)
    return '\n'.join(result_lines)


def _extract_superstructure_data(model, prefix, target_units):
    """Extract superstructure elements from a building model, with unit conversion
    and label renaming.

    Args:
        model: E2KModel of the building
        prefix: label prefix for renaming (e.g. "A")
        target_units: (force, length) target unit tuple

    Returns:
        dict with keys: points, line_conns, area_conns,
                        point_assigns, line_assigns, area_assigns,
                        line_loads, area_loads, frame_sections, concrete_sections,
                        area_properties, material_properties
    """
    src_force, src_length = model.units
    tgt_force, tgt_length = target_units
    l_scale = scale_factor(src_force, src_length, tgt_force, tgt_length, 'length')
    need_convert = abs(l_scale - 1.0) > 1e-10

    # Identify superstructure stories
    super_stories = {s for s in model.story_names if not is_substructure_story(s)}

    # Get element labels on super stories
    super_line_labels = model.get_element_labels_by_story(
        'LINE ASSIGNS', super_stories, 'LINEASSIGN')
    super_area_labels = model.get_element_labels_by_story(
        'AREA ASSIGNS', super_stories, 'AREAASSIGN')
    super_point_labels = model.get_element_labels_by_story(
        'POINT ASSIGNS', super_stories, 'POINTASSIGN')

    # Filter connectivities
    line_conn_text = model.raw_sections.get('LINE CONNECTIVITIES', '')
    area_conn_text = model.raw_sections.get('AREA CONNECTIVITIES', '')
    point_text = model.raw_sections.get('POINT COORDINATES', '')

    super_line_conns = filter_raw_lines(line_conn_text, super_line_labels, 'LINE')
    super_area_conns = filter_raw_lines(area_conn_text, super_area_labels, 'AREA')

    # Get points used by superstructure elements
    used_points = get_point_labels_from_connectivities(
        super_line_conns, super_area_conns)
    used_points.update(super_point_labels)
    super_points = filter_raw_lines(point_text, used_points, 'POINT')

    # Filter assigns
    line_assign_text = model.raw_sections.get('LINE ASSIGNS', '')
    area_assign_text = model.raw_sections.get('AREA ASSIGNS', '')
    point_assign_text = model.raw_sections.get('POINT ASSIGNS', '')

    super_line_assigns = filter_raw_lines_by_story(
        line_assign_text, super_stories, 'LINEASSIGN')
    super_area_assigns = filter_raw_lines_by_story(
        area_assign_text, super_stories, 'AREAASSIGN')
    super_point_assigns = filter_raw_lines_by_story(
        point_assign_text, super_stories, 'POINTASSIGN')

    # Filter loads
    static_text = model.raw_sections.get('STATIC LOADS', '')
    area_load_text = model.raw_sections.get('AREA OBJECT LOADS', '')
    super_line_loads = filter_raw_lines(static_text, super_line_labels, 'LINELOAD')
    super_area_loads = filter_raw_lines(area_load_text, super_area_labels, 'AREALOAD')

    # Rename labels with prefix + convert coordinates
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

    for line in super_points:
        renamed = _rename_label(line, prefix, 'POINT')
        if need_convert:
            renamed = _convert_point_coords(renamed, l_scale)
        result['points'].append(renamed)

    for line in super_line_conns:
        result['line_conns'].append(_rename_label(line, prefix, 'LINE'))

    for line in super_area_conns:
        result['area_conns'].append(_rename_label(line, prefix, 'AREA'))

    for line in super_point_assigns:
        result['point_assigns'].append(_rename_label(line, prefix, 'POINTASSIGN'))

    for line in super_line_assigns:
        result['line_assigns'].append(_rename_label(line, prefix, 'LINEASSIGN'))

    for line in super_area_assigns:
        result['area_assigns'].append(_rename_label(line, prefix, 'AREAASSIGN'))

    for line in super_line_loads:
        result['line_loads'].append(_rename_label(line, prefix, 'LINELOAD'))

    for line in super_area_loads:
        result['area_loads'].append(_rename_label(line, prefix, 'AREALOAD'))

    # Collect section/material definitions (for dedup)
    # Sections used by superstructure
    used_sections = set()
    for assigns_text in ['\n'.join(super_line_assigns),
                         '\n'.join(super_area_assigns)]:
        for m in re.finditer(r'SECTION\s+"([^"]+)"', assigns_text):
            used_sections.add(m.group(1))

    result['used_sections'] = used_sections
    result['stats'] = {
        'lines': len(super_line_labels),
        'areas': len(super_area_labels),
        'points': len(used_points),
    }

    return result


def _verify_column_connectivity(base_model, building_models, tolerance=0.02):
    """Verify column positions match between substructure and superstructure.

    Args:
        base_model: E2KModel with substructure
        building_models: dict {name: E2KModel}
        tolerance: max coordinate difference in file units (default 2cm for meters)

    Returns:
        dict with match/mismatch counts
    """
    # Get substructure column positions at 1F (interface level)
    base_lines = base_model.lines
    base_points = base_model.points
    base_assigns_text = base_model.raw_sections.get('LINE ASSIGNS', '')

    # Find columns at 1F
    base_cols_1f = {}
    for line in base_assigns_text.split('\n'):
        stripped = line.strip()
        m = re.match(r'LINEASSIGN\s+"([^"]+)"\s+"1F"', stripped)
        if m:
            label = m.group(1)
            # Find this line's point
            for ln in base_lines:
                if ln['label'] == label and ln['type'] == 'COLUMN':
                    pt = ln['point_i']
                    if pt in base_points:
                        base_cols_1f[label] = base_points[pt]
                    break

    results = {'base_cols_1f': len(base_cols_1f), 'matches': {}}

    for bld_name, bld_model in building_models.items():
        bld_lines = bld_model.lines
        bld_points = bld_model.points

        # Find columns at 1MF or lowest super story
        super_stories = {s for s in bld_model.story_names
                         if not is_substructure_story(s)}
        if not super_stories:
            continue

        bld_cols = {}
        assigns_text = bld_model.raw_sections.get('LINE ASSIGNS', '')
        for line in assigns_text.split('\n'):
            stripped = line.strip()
            for story in super_stories:
                m = re.match(rf'LINEASSIGN\s+"([^"]+)"\s+"{re.escape(story)}"',
                             stripped)
                if m:
                    label = m.group(1)
                    for ln in bld_lines:
                        if ln['label'] == label and ln['type'] == 'COLUMN':
                            pt = ln['point_i']
                            if pt in bld_points:
                                bld_cols[label] = bld_points[pt]
                            break

        # Match by coordinate proximity
        matched = 0
        unmatched = 0
        for base_label, (bx, by) in base_cols_1f.items():
            found = False
            for bld_label, (sx, sy) in bld_cols.items():
                if abs(bx - sx) < tolerance and abs(by - sy) < tolerance:
                    matched += 1
                    found = True
                    break
            if not found:
                unmatched += 1

        results['matches'][bld_name] = {
            'matched': matched,
            'unmatched': unmatched,
            'building_cols': len(bld_cols),
        }

    return results


def merge_e2k(base_path, building_files, output_path, target_units=None):
    """Merge multiple building e2k files into one model.

    Args:
        base_path: path to base e2k (contains substructure)
        building_files: dict {prefix: filepath} for each building
        output_path: path for output e2k file
        target_units: (force, length) target units, default uses base's units

    Returns:
        dict with merge statistics
    """
    # Read base model
    print(f"Reading base model: {base_path}")
    base = E2KModel.from_file(base_path)
    print(f"  Units: {base.units}")

    if target_units is None:
        target_units = base.units

    # Read building models
    building_models = {}
    building_data = {}
    for prefix, filepath in building_files.items():
        print(f"\nReading building {prefix}: {filepath}")
        bld_model = E2KModel.from_file(filepath)
        print(f"  Units: {bld_model.units}")
        building_models[prefix] = bld_model

        data = _extract_superstructure_data(bld_model, prefix, target_units)
        building_data[prefix] = data
        stats = data['stats']
        print(f"  Superstructure: {stats['lines']} lines, {stats['areas']} areas, {stats['points']} points")

    # Verify column connectivity
    print("\nVerifying column connectivity...")
    conn_results = _verify_column_connectivity(base, building_models)
    print(f"  Base columns at 1F: {conn_results['base_cols_1f']}")
    for bld, info in conn_results.get('matches', {}).items():
        print(f"  Building {bld}: {info['matched']} matched, {info['unmatched']} unmatched")

    # Build merged model
    print("\nBuilding merged model...")
    merged = E2KModel()
    merged.units = target_units

    # Copy base global sections
    for sec in ['PROGRAM INFORMATION', 'CONTROLS',
                'STORIES - IN SEQUENCE FROM TOP', 'DIAPHRAGM NAMES',
                'GRIDS', 'REBAR DEFINITIONS', 'AUTO SELECT SECTION LISTS',
                'LINK PROPERTIES', 'PIER/SPANDREL NAMES',
                'ANALYSIS OPTIONS', 'FUNCTIONS', 'RESPONSE SPECTRUM CASES',
                'LOAD COMBINATIONS', 'STEEL DESIGN PREFERENCES',
                'CONCRETE DESIGN PREFERENCES', 'CONCRETE DESIGN OVERWRITES',
                'COMPOSITE DESIGN PREFERENCES', 'WALL DESIGN PREFERENCES',
                'SPECIAL SEISMIC DATA', 'DIMENSION LINES',
                'DEVELOPED ELEVATIONS']:
        if sec in base.raw_sections:
            merged.raw_sections[sec] = base.raw_sections[sec]

    # Material properties — start with base, add missing from buildings
    base_materials = base.get_material_names_defined()
    mat_text = base.raw_sections.get('MATERIAL PROPERTIES', '')
    extra_mat_lines = []
    for prefix, bld_model in building_models.items():
        bld_mat_text = bld_model.raw_sections.get('MATERIAL PROPERTIES', '')
        for block in re.split(r'\n(?=\s*MATERIAL\s+")', bld_mat_text):
            m = re.match(r'\s*MATERIAL\s+"([^"]+)"', block)
            if m and m.group(1) not in base_materials:
                extra_mat_lines.append(block.rstrip())
                base_materials.add(m.group(1))
    if extra_mat_lines:
        mat_text += '\n' + '\n'.join(extra_mat_lines)
    merged.raw_sections['MATERIAL PROPERTIES'] = mat_text

    # Frame sections — dedup by name (same name = same definition)
    base_frame_secs = base.get_frame_section_names_defined()
    frame_text = base.raw_sections.get('FRAME SECTIONS', '')
    extra_frame = []
    for prefix, bld_model in building_models.items():
        src_force, src_length = bld_model.units
        l_scale = scale_factor(src_force, src_length,
                               target_units[0], target_units[1], 'length')
        f_scale = scale_factor(src_force, src_length,
                               target_units[0], target_units[1], 'force')
        bld_frame_text = bld_model.raw_sections.get('FRAME SECTIONS', '')
        need_convert = abs(l_scale - 1.0) > 1e-10

        for block in re.split(r'\n(?=\s*FRAMESECTION\s+")', bld_frame_text):
            m = re.match(r'\s*FRAMESECTION\s+"([^"]+)"', block)
            if m and m.group(1) not in base_frame_secs:
                if need_convert:
                    block = _convert_section_dimensions(block, l_scale, f_scale)
                extra_frame.append(block.rstrip())
                base_frame_secs.add(m.group(1))
    if extra_frame:
        frame_text += '\n' + '\n'.join(extra_frame)
    merged.raw_sections['FRAME SECTIONS'] = frame_text

    # Concrete sections — dedup
    base_conc_secs = set()
    conc_text = base.raw_sections.get('CONCRETE SECTIONS', '')
    for m in re.finditer(r'CONCRETESECTION\s+"([^"]+)"', conc_text):
        base_conc_secs.add(m.group(1))
    extra_conc = []
    for prefix, bld_model in building_models.items():
        src_force, src_length = bld_model.units
        l_scale = scale_factor(src_force, src_length,
                               target_units[0], target_units[1], 'length')
        bld_conc_text = bld_model.raw_sections.get('CONCRETE SECTIONS', '')
        need_convert = abs(l_scale - 1.0) > 1e-10
        for block in re.split(r'\n(?=\s*CONCRETESECTION\s+")', bld_conc_text):
            m_c = re.match(r'\s*CONCRETESECTION\s+"([^"]+)"', block)
            if m_c and m_c.group(1) not in base_conc_secs:
                if need_convert:
                    block = _convert_section_dimensions(block, l_scale, 1.0)
                extra_conc.append(block.rstrip())
                base_conc_secs.add(m_c.group(1))
    if extra_conc:
        conc_text += '\n' + '\n'.join(extra_conc)
    merged.raw_sections['CONCRETE SECTIONS'] = conc_text

    # Wall/slab/deck properties — dedup
    base_area_secs = base.get_area_section_names_defined()
    area_prop_text = base.raw_sections.get('WALL/SLAB/DECK PROPERTIES', '')
    extra_area = []
    for prefix, bld_model in building_models.items():
        bld_text = bld_model.raw_sections.get('WALL/SLAB/DECK PROPERTIES', '')
        for block in re.split(r'\n(?=\s*(?:SHELLPROP|WALLPROP|DECKPROP)\s+")', bld_text):
            m_a = re.match(r'\s*(?:SHELLPROP|WALLPROP|DECKPROP)\s+"([^"]+)"', block)
            if m_a and m_a.group(1) not in base_area_secs:
                extra_area.append(block.rstrip())
                base_area_secs.add(m_a.group(1))
    if extra_area:
        area_prop_text += '\n' + '\n'.join(extra_area)
    merged.raw_sections['WALL/SLAB/DECK PROPERTIES'] = area_prop_text

    # Merge geometry: points, connectivities, assigns, loads
    # Start with base content
    base_point_text = base.raw_sections.get('POINT COORDINATES', '')
    base_line_conn = base.raw_sections.get('LINE CONNECTIVITIES', '')
    base_area_conn = base.raw_sections.get('AREA CONNECTIVITIES', '')
    base_point_assigns = base.raw_sections.get('POINT ASSIGNS', '')
    base_line_assigns = base.raw_sections.get('LINE ASSIGNS', '')
    base_area_assigns = base.raw_sections.get('AREA ASSIGNS', '')
    base_static_loads = base.raw_sections.get('STATIC LOADS', '')
    base_area_loads = base.raw_sections.get('AREA OBJECT LOADS', '')

    # Append building data
    for prefix in sorted(building_data.keys()):
        data = building_data[prefix]
        if data['points']:
            base_point_text += '\n' + '\n'.join(f'  {l}' for l in data['points'])
        if data['line_conns']:
            base_line_conn += '\n' + '\n'.join(f'  {l}' for l in data['line_conns'])
        if data['area_conns']:
            base_area_conn += '\n' + '\n'.join(f'  {l}' for l in data['area_conns'])
        if data['point_assigns']:
            base_point_assigns += '\n' + '\n'.join(f'  {l}' for l in data['point_assigns'])
        if data['line_assigns']:
            base_line_assigns += '\n' + '\n'.join(f'  {l}' for l in data['line_assigns'])
        if data['area_assigns']:
            base_area_assigns += '\n' + '\n'.join(f'  {l}' for l in data['area_assigns'])
        if data['line_loads']:
            base_static_loads += '\n' + '\n'.join(f'  {l}' for l in data['line_loads'])
        if data['area_loads']:
            base_area_loads += '\n' + '\n'.join(f'  {l}' for l in data['area_loads'])

    merged.raw_sections['POINT COORDINATES'] = base_point_text
    merged.raw_sections['LINE CONNECTIVITIES'] = base_line_conn
    merged.raw_sections['AREA CONNECTIVITIES'] = base_area_conn
    merged.raw_sections['POINT ASSIGNS'] = base_point_assigns
    merged.raw_sections['LINE ASSIGNS'] = base_line_assigns
    merged.raw_sections['AREA ASSIGNS'] = base_area_assigns
    merged.raw_sections['STATIC LOADS'] = base_static_loads
    merged.raw_sections['AREA OBJECT LOADS'] = base_area_loads

    # Write output
    print(f"\nWriting {output_path}...")
    write_e2k(merged, output_path)

    total_lines = sum(d['stats']['lines'] for d in building_data.values())
    total_areas = sum(d['stats']['areas'] for d in building_data.values())
    total_points = sum(d['stats']['points'] for d in building_data.values())

    stats = {
        'base': base_path,
        'buildings': list(building_files.keys()),
        'output': output_path,
        'target_units': target_units,
        'super_lines': total_lines,
        'super_areas': total_areas,
        'super_points': total_points,
        'connectivity': conn_results,
    }
    print(f"\nMerge complete:")
    print(f"  Buildings merged: {list(building_files.keys())}")
    print(f"  Superstructure added: {total_lines} lines, {total_areas} areas")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Merge multiple building e2k files into one model')
    parser.add_argument('--base', '-b', required=True,
                        help='Base e2k file (with substructure)')
    parser.add_argument('--buildings', '-B', nargs='+', required=True,
                        help='Building files as PREFIX=PATH pairs '
                             '(e.g. A=building_A.e2k B=building_B.e2k)')
    parser.add_argument('--output', '-o', required=True,
                        help='Output e2k file path')
    parser.add_argument('--target-units', nargs=2, default=None,
                        metavar=('FORCE', 'LENGTH'),
                        help='Target units (default: use base units)')

    args = parser.parse_args()

    # Parse building files
    building_files = {}
    for item in args.buildings:
        if '=' not in item:
            parser.error(f"Invalid building format: {item}. Use PREFIX=PATH")
        prefix, path = item.split('=', 1)
        building_files[prefix] = path

    target_units = tuple(args.target_units) if args.target_units else None

    merge_e2k(args.base, building_files, args.output,
              target_units=target_units)


if __name__ == '__main__':
    main()
