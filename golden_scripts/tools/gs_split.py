"""
E2K Split Tool — Extract a single building from a multi-building e2k model.

Keeps all substructure (共構下構) + target building's superstructure.
Building membership is determined by Diaphragm Name on superstructure floors.

Usage:
    python -m golden_scripts.tools.gs_split \\
        --input all_buildings.e2k \\
        --building DA \\
        --output building_A.e2k

    Or from Python:
        from golden_scripts.tools.gs_split import split_e2k
        split_e2k("all.e2k", "DA", "building_A.e2k")
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
from golden_scripts.tools.e2k_writer import write_e2k


def discover_buildings(model):
    """Discover building identifiers from superstructure diaphragm assignments.

    Returns:
        dict {diaphragm_name: set_of_area_labels}
    """
    diaphragm_assigns = model.get_diaphragm_assignments()
    buildings = {}  # diaphragm_name -> set of area labels

    for (elem, story), diaph in diaphragm_assigns.items():
        if is_substructure_story(story):
            continue  # skip substructure diaphragms
        if diaph not in buildings:
            buildings[diaph] = set()
        buildings[diaph].add(elem)

    return buildings


def _get_elements_for_building(model, building_id):
    """Get all element labels belonging to a building (by diaphragm on super floors).

    Strategy: find all superstructure stories where the building's diaphragm
    appears, then collect ALL elements (line + area) assigned to those stories.
    This captures beams/columns that don't have diaphragm assignments directly.

    Args:
        model: E2KModel
        building_id: diaphragm name identifying the building (e.g. "DA")

    Returns:
        (super_line_labels, super_area_labels, super_stories)
    """
    # 1. Find which superstructure stories this building occupies
    diaphragm_assigns = model.get_diaphragm_assignments()
    building_stories = set()
    for (elem, story), diaph in diaphragm_assigns.items():
        if diaph == building_id and not is_substructure_story(story):
            building_stories.add(story)

    # 2. Get ALL elements on those stories that share the same diaphragm
    #    But also get elements WITHOUT diaphragm on those stories
    #    For areas: keep only those with matching diaphragm (or no diaphragm)
    #    For lines: keep all on those stories (beams/columns don't have diaphragms)

    # Collect area labels that belong to OTHER buildings on same stories
    other_area_labels = set()
    for (elem, story), diaph in diaphragm_assigns.items():
        if story in building_stories and diaph != building_id:
            other_area_labels.add(elem)

    # Get all line/area labels on building stories
    super_line_labels = model.get_element_labels_by_story(
        'LINE ASSIGNS', building_stories, 'LINEASSIGN')
    super_area_labels = model.get_element_labels_by_story(
        'AREA ASSIGNS', building_stories, 'AREAASSIGN')

    # Remove areas belonging to other buildings
    super_area_labels -= other_area_labels

    return super_line_labels, super_area_labels, building_stories


def _collect_substructure_elements(model):
    """Collect all element labels on substructure stories.

    Returns:
        (sub_line_labels, sub_area_labels, sub_stories)
    """
    sub_stories = {s for s in model.story_names if is_substructure_story(s)}

    sub_line_labels = model.get_element_labels_by_story(
        'LINE ASSIGNS', sub_stories, 'LINEASSIGN')
    sub_area_labels = model.get_element_labels_by_story(
        'AREA ASSIGNS', sub_stories, 'AREAASSIGN')

    return sub_line_labels, sub_area_labels, sub_stories


def _filter_section_defs(raw_text, used_names, keyword_pattern):
    """Keep only definitions whose name is in used_names.

    Args:
        raw_text: raw section text
        used_names: set of section names to keep
        keyword_pattern: regex for the definition keyword (e.g. 'FRAMESECTION')

    Returns: filtered text string
    """
    result_lines = []
    current_block = []
    current_name = None

    for line in raw_text.split('\n'):
        stripped = line.strip()
        if not stripped:
            if current_block and current_name in used_names:
                result_lines.extend(current_block)
            current_block = []
            current_name = None
            continue

        m = re.match(rf'{keyword_pattern}\s+"([^"]+)"', stripped)
        if m:
            # Flush previous block
            if current_block and current_name in used_names:
                result_lines.extend(current_block)
            current_name = m.group(1)
            current_block = [line.rstrip()]
        else:
            if current_name is not None:
                current_block.append(line.rstrip())
            else:
                # Non-definition line (comments, etc.) — keep
                result_lines.append(line.rstrip())

    # Flush last block
    if current_block and current_name in used_names:
        result_lines.extend(current_block)

    return '\n'.join(result_lines)


def _filter_material_defs(raw_text, used_materials):
    """Keep only material definitions whose name is in used_materials."""
    result_lines = []
    current_block = []
    current_name = None

    for line in raw_text.split('\n'):
        stripped = line.strip()

        m = re.match(r'MATERIAL\s+"([^"]+)"', stripped)
        if m:
            if current_block and current_name in used_materials:
                result_lines.extend(current_block)
            current_name = m.group(1)
            current_block = [line.rstrip()]
        elif current_name is not None:
            current_block.append(line.rstrip())

    if current_block and current_name in used_materials:
        result_lines.extend(current_block)

    return '\n'.join(result_lines)


def split_e2k(input_path, building_id, output_path, keep_all_defs=False):
    """Split a multi-building e2k into a single-building e2k.

    Args:
        input_path: path to source e2k file
        building_id: diaphragm name for the target building (e.g. "DA")
        output_path: path for output e2k file
        keep_all_defs: if True, don't clean up unused definitions

    Returns:
        dict with statistics about the split
    """
    print(f"Reading {input_path}...")
    model = E2KModel.from_file(input_path)
    print(f"  Units: {model.units}")
    print(f"  Stories: {len(model.stories)}")

    # Discover buildings
    buildings = discover_buildings(model)
    print(f"  Buildings found: {sorted(buildings.keys())}")
    if building_id not in buildings:
        available = sorted(buildings.keys())
        raise ValueError(
            f"Building '{building_id}' not found. Available: {available}")

    # Collect elements to keep
    print(f"\nExtracting building '{building_id}'...")
    super_lines, super_areas, super_stories = _get_elements_for_building(
        model, building_id)
    sub_lines, sub_areas, sub_stories = _collect_substructure_elements(model)

    keep_lines = super_lines | sub_lines
    keep_areas = super_areas | sub_areas
    keep_stories = super_stories | sub_stories

    print(f"  Superstructure: {len(super_lines)} lines, {len(super_areas)} areas")
    print(f"  Substructure: {len(sub_lines)} lines, {len(sub_areas)} areas")
    print(f"  Total: {len(keep_lines)} lines, {len(keep_areas)} areas")

    # Build output model
    out = E2KModel()
    out.units = model.units

    # Copy global sections unchanged
    for sec in ['PROGRAM INFORMATION', 'CONTROLS',
                'STORIES - IN SEQUENCE FROM TOP', 'GRIDS',
                'ANALYSIS OPTIONS', 'FUNCTIONS', 'RESPONSE SPECTRUM CASES',
                'LOAD COMBINATIONS', 'STEEL DESIGN PREFERENCES',
                'CONCRETE DESIGN PREFERENCES', 'CONCRETE DESIGN OVERWRITES',
                'COMPOSITE DESIGN PREFERENCES', 'WALL DESIGN PREFERENCES',
                'SPECIAL SEISMIC DATA', 'DIMENSION LINES',
                'DEVELOPED ELEVATIONS', 'REBAR DEFINITIONS',
                'AUTO SELECT SECTION LISTS']:
        if sec in model.raw_sections:
            out.raw_sections[sec] = model.raw_sections[sec]

    # Diaphragm names — keep all (substructure may reference them)
    if 'DIAPHRAGM NAMES' in model.raw_sections:
        out.raw_sections['DIAPHRAGM NAMES'] = model.raw_sections['DIAPHRAGM NAMES']

    # Filter connectivities
    line_conn_text = model.raw_sections.get('LINE CONNECTIVITIES', '')
    area_conn_text = model.raw_sections.get('AREA CONNECTIVITIES', '')

    kept_line_conns = filter_raw_lines(line_conn_text, keep_lines, 'LINE')
    kept_area_conns = filter_raw_lines(area_conn_text, keep_areas, 'AREA')

    out.raw_sections['LINE CONNECTIVITIES'] = '\n'.join(
        f'  {l}' for l in kept_line_conns)
    out.raw_sections['AREA CONNECTIVITIES'] = '\n'.join(
        f'  {l}' for l in kept_area_conns)

    # Filter points — only keep those referenced by kept connectivities
    used_points = get_point_labels_from_connectivities(
        kept_line_conns, kept_area_conns)
    # Also include points from POINT ASSIGNS for kept stories
    point_assign_text = model.raw_sections.get('POINT ASSIGNS', '')
    for line in point_assign_text.split('\n'):
        stripped = line.strip()
        m = re.match(r'POINTASSIGN\s+"([^"]+)"\s+"([^"]+)"', stripped)
        if m and m.group(2) in keep_stories:
            used_points.add(m.group(1))

    point_text = model.raw_sections.get('POINT COORDINATES', '')
    kept_points = filter_raw_lines(point_text, used_points, 'POINT')
    out.raw_sections['POINT COORDINATES'] = '\n'.join(
        f'  {l}' for l in kept_points)

    # Filter assigns
    line_assign_text = model.raw_sections.get('LINE ASSIGNS', '')
    area_assign_text = model.raw_sections.get('AREA ASSIGNS', '')
    point_assign_text = model.raw_sections.get('POINT ASSIGNS', '')

    kept_line_assigns = filter_raw_lines(line_assign_text, keep_lines, 'LINEASSIGN')
    kept_area_assigns = filter_raw_lines(area_assign_text, keep_areas, 'AREAASSIGN')
    kept_point_assigns = filter_raw_lines(point_assign_text, used_points, 'POINTASSIGN')

    out.raw_sections['LINE ASSIGNS'] = '\n'.join(
        f'  {l}' for l in kept_line_assigns)
    out.raw_sections['AREA ASSIGNS'] = '\n'.join(
        f'  {l}' for l in kept_area_assigns)
    out.raw_sections['POINT ASSIGNS'] = '\n'.join(
        f'  {l}' for l in kept_point_assigns)

    # Filter loads
    static_text = model.raw_sections.get('STATIC LOADS', '')
    area_load_text = model.raw_sections.get('AREA OBJECT LOADS', '')

    # Static loads: keep LOADCASE defs + LINELOAD/POINTLOAD for kept elements
    static_lines = []
    for line in static_text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        m_line = re.match(r'LINELOAD\s+"([^"]+)"', stripped)
        m_point = re.match(r'POINTLOAD\s+"([^"]+)"', stripped)
        if m_line:
            if m_line.group(1) in keep_lines:
                static_lines.append(f'  {stripped}')
        elif m_point:
            if m_point.group(1) in used_points:
                static_lines.append(f'  {stripped}')
        else:
            static_lines.append(f'  {stripped}')
    out.raw_sections['STATIC LOADS'] = '\n'.join(static_lines)

    # Area loads: keep only for kept areas
    area_load_lines = filter_raw_lines(area_load_text, keep_areas, 'AREALOAD')
    out.raw_sections['AREA OBJECT LOADS'] = '\n'.join(
        f'  {l}' for l in area_load_lines)

    # Clean up unused definitions
    if not keep_all_defs:
        # Collect all section names referenced by kept assigns
        used_sections = set()
        for assigns_text in [out.raw_sections.get('LINE ASSIGNS', ''),
                             out.raw_sections.get('AREA ASSIGNS', '')]:
            for m in re.finditer(r'SECTION\s+"([^"]+)"', assigns_text):
                used_sections.add(m.group(1))

        # Filter frame sections
        if 'FRAME SECTIONS' in model.raw_sections:
            out.raw_sections['FRAME SECTIONS'] = _filter_section_defs(
                model.raw_sections['FRAME SECTIONS'], used_sections,
                'FRAMESECTION')

        # Filter concrete sections
        if 'CONCRETE SECTIONS' in model.raw_sections:
            out.raw_sections['CONCRETE SECTIONS'] = _filter_section_defs(
                model.raw_sections['CONCRETE SECTIONS'], used_sections,
                'CONCRETESECTION')

        # Filter wall/slab/deck properties
        if 'WALL/SLAB/DECK PROPERTIES' in model.raw_sections:
            out.raw_sections['WALL/SLAB/DECK PROPERTIES'] = _filter_section_defs(
                model.raw_sections['WALL/SLAB/DECK PROPERTIES'], used_sections,
                r'(?:SHELLPROP|WALLPROP|DECKPROP)')

        # Filter materials — keep only those referenced by kept sections
        used_materials = set()
        for sec_key in ['FRAME SECTIONS', 'WALL/SLAB/DECK PROPERTIES']:
            text = out.raw_sections.get(sec_key, '')
            for m in re.finditer(r'MATERIAL\s+"([^"]+)"', text):
                used_materials.add(m.group(1))
        # Also keep rebar materials
        rebar_text = out.raw_sections.get('REBAR DEFINITIONS', '')
        for m in re.finditer(r'MATERIAL\s+"([^"]+)"', rebar_text):
            used_materials.add(m.group(1))

        if 'MATERIAL PROPERTIES' in model.raw_sections:
            out.raw_sections['MATERIAL PROPERTIES'] = _filter_material_defs(
                model.raw_sections['MATERIAL PROPERTIES'], used_materials)
    else:
        # Keep all definitions unchanged
        for sec in ['MATERIAL PROPERTIES', 'FRAME SECTIONS',
                     'CONCRETE SECTIONS', 'WALL/SLAB/DECK PROPERTIES']:
            if sec in model.raw_sections:
                out.raw_sections[sec] = model.raw_sections[sec]

    # Link properties — keep all (usually few)
    if 'LINK PROPERTIES' in model.raw_sections:
        out.raw_sections['LINK PROPERTIES'] = model.raw_sections['LINK PROPERTIES']
    if 'PIER/SPANDREL NAMES' in model.raw_sections:
        out.raw_sections['PIER/SPANDREL NAMES'] = model.raw_sections['PIER/SPANDREL NAMES']

    # Write output
    print(f"\nWriting {output_path}...")
    write_e2k(out, output_path)

    stats = {
        'input': input_path,
        'building': building_id,
        'output': output_path,
        'buildings_found': sorted(buildings.keys()),
        'super_lines': len(super_lines),
        'super_areas': len(super_areas),
        'sub_lines': len(sub_lines),
        'sub_areas': len(sub_areas),
        'total_lines': len(keep_lines),
        'total_areas': len(keep_areas),
        'points': len(used_points),
    }
    print(f"\nSplit complete:")
    print(f"  Lines: {stats['total_lines']} ({stats['super_lines']} super + {stats['sub_lines']} sub)")
    print(f"  Areas: {stats['total_areas']} ({stats['super_areas']} super + {stats['sub_areas']} sub)")
    print(f"  Points: {stats['points']}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Split a multi-building e2k into a single-building e2k')
    parser.add_argument('--input', '-i', required=True,
                        help='Input e2k file (multi-building)')
    parser.add_argument('--building', '-b', required=True,
                        help='Building diaphragm ID (e.g. DA, DB)')
    parser.add_argument('--output', '-o', required=True,
                        help='Output e2k file path')
    parser.add_argument('--keep-all-defs', action='store_true',
                        help='Keep all material/section definitions (no cleanup)')
    parser.add_argument('--list-buildings', action='store_true',
                        help='List available buildings and exit')

    args = parser.parse_args()

    if args.list_buildings:
        model = E2KModel.from_file(args.input)
        buildings = discover_buildings(model)
        print(f"Buildings in {args.input}:")
        for bld, areas in sorted(buildings.items()):
            print(f"  {bld}: {len(areas)} superstructure areas")
        return

    split_e2k(args.input, args.building, args.output,
              keep_all_defs=args.keep_all_defs)


if __name__ == '__main__':
    main()
