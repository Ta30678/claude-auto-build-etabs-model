"""
Config Build Tool — Merge elements.json + grid_info.json → model_config.json

Phase 1 deterministic merge: combines pptx_to_elements.py output (elements.json)
with READER AI output (grid_info.json) to produce model_config.json.
Replaces the CONFIG-BUILDER's mechanical merge work with a zero-token script.

Usage:
    python -m golden_scripts.tools.config_build \
        --elements elements.json \
        --grid-info grid_info.json \
        --output model_config.json \
        --save-path "C:/path/to/model.EDB" \
        --project-name "ProjectName" \
        [--dry-run]
"""
import json
import argparse
import math
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from golden_scripts.tools.config_merge import validate_config
from golden_scripts.constants import is_rooftop_story


# ── Geometry Utilities ─────────────────────────────────────────

def point_in_polygon(x, y, polygon):
    """Ray-casting algorithm for point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def point_to_segment_distance(px, py, x1, y1, x2, y2):
    """Minimum distance from point to line segment."""
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-12:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def point_in_or_near_polygon(x, y, polygon, tolerance=0.01):
    """Check if point is inside polygon or within tolerance of boundary."""
    if point_in_polygon(x, y, polygon):
        return True
    for i in range(len(polygon)):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % len(polygon)]
        if point_to_segment_distance(x, y, x1, y1, x2, y2) <= tolerance:
            return True
    return False


def polygon_area(polygon):
    """Shoelace formula for polygon area."""
    n = len(polygon)
    area = 0.0
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def is_non_rectangular(polygon):
    """Check if polygon is non-rectangular (L-shaped, etc.)."""
    if not polygon or len(polygon) < 3:
        return False
    if len(polygon) != 4:
        return True
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    bbox_area = (max(xs) - min(xs)) * (max(ys) - min(ys))
    poly_area = polygon_area(polygon)
    return abs(bbox_area - poly_area) > 0.01


# ── Element Stripping ──────────────────────────────────────────

def strip_columns(columns):
    """Remove page_num from columns."""
    result = []
    for col in columns:
        out = {
            "grid_x": col["grid_x"],
            "grid_y": col["grid_y"],
            "section": col.get("section", ""),
            "floors": list(col.get("floors", [])),
        }
        result.append(out)
    return result


def strip_beams(beams):
    """Remove page_num and direction from beams."""
    result = []
    for beam in beams:
        out = {
            "x1": beam["x1"], "y1": beam["y1"],
            "x2": beam["x2"], "y2": beam["y2"],
            "section": beam.get("section", ""),
            "floors": list(beam.get("floors", [])),
        }
        result.append(out)
    return result


def strip_walls(walls):
    """Remove page_num and direction from walls. Preserve is_diaphragm_wall."""
    result = []
    for wall in walls:
        out = {
            "x1": wall["x1"], "y1": wall["y1"],
            "x2": wall["x2"], "y2": wall["y2"],
            "section": wall.get("section", ""),
            "floors": list(wall.get("floors", [])),
        }
        if wall.get("is_diaphragm_wall"):
            out["is_diaphragm_wall"] = True
        result.append(out)
    return result


def strip_small_beams(small_beams):
    """Remove page_num and direction from small beams."""
    result = []
    for sb in small_beams:
        out = {
            "x1": sb["x1"], "y1": sb["y1"],
            "x2": sb["x2"], "y2": sb["y2"],
            "section": sb.get("section", ""),
            "floors": list(sb.get("floors", [])),
        }
        result.append(out)
    return result


# ── Building Outline Filtering ─────────────────────────────────

def filter_by_outline(columns, beams, walls, outline, tolerance=0.01):
    """Filter elements outside building_outline polygon.

    Only activates for non-rectangular outlines.
    - Columns: point must be inside polygon.
    - Beams/walls: both endpoints outside → remove.

    Returns: (filtered_columns, filtered_beams, filtered_walls, warnings)
    """
    warnings = []
    if not outline or not is_non_rectangular(outline):
        return columns, beams, walls, warnings

    filtered_cols = []
    for i, col in enumerate(columns):
        if point_in_or_near_polygon(col["grid_x"], col["grid_y"], outline, tolerance):
            filtered_cols.append(col)
        else:
            warnings.append(
                f"columns[{i}]: ({col['grid_x']}, {col['grid_y']}) "
                f"{col.get('section', '')} outside building_outline — REMOVED")

    filtered_beams = []
    for i, beam in enumerate(beams):
        p1_in = point_in_or_near_polygon(beam["x1"], beam["y1"], outline, tolerance)
        p2_in = point_in_or_near_polygon(beam["x2"], beam["y2"], outline, tolerance)
        if p1_in or p2_in:
            filtered_beams.append(beam)
        else:
            warnings.append(
                f"beams[{i}]: ({beam['x1']},{beam['y1']})-({beam['x2']},{beam['y2']}) "
                f"{beam.get('section', '')} outside building_outline — REMOVED")

    filtered_walls = []
    for i, wall in enumerate(walls):
        p1_in = point_in_or_near_polygon(wall["x1"], wall["y1"], outline, tolerance)
        p2_in = point_in_or_near_polygon(wall["x2"], wall["y2"], outline, tolerance)
        if p1_in or p2_in:
            filtered_walls.append(wall)
        else:
            warnings.append(
                f"walls[{i}]: ({wall['x1']},{wall['y1']})-({wall['x2']},{wall['y2']}) "
                f"{wall.get('section', '')} outside building_outline — REMOVED")

    return filtered_cols, filtered_beams, filtered_walls, warnings


# ── Rooftop Replication ────────────────────────────────────────

def has_r2f_or_above(stories):
    """Check if any story is R2F or higher (triggers rooftop replication)."""
    for s in stories:
        m = re.match(r'^R(\d+)F$', s["name"])
        if m and int(m.group(1)) >= 2:
            return True
    return False


def _in_core(x, y, core_grid_area, tolerance=0.01):
    """Check if point is within core_grid_area rectangle."""
    x_range = core_grid_area["x_range"]
    y_range = core_grid_area["y_range"]
    return (x_range[0] - tolerance <= x <= x_range[1] + tolerance and
            y_range[0] - tolerance <= y <= y_range[1] + tolerance)


def replicate_rooftop(columns, beams, walls, stories, core_grid_area):
    """Add rooftop floors to elements within core grid area.

    Trigger: core_grid_area exists AND stories have R2F+.

    Logic:
    - Columns/walls in core: add R1F ~ second-to-last rooftop floor
    - Beams with both endpoints in core: add second rooftop ~ last rooftop floor

    Modifies elements in-place.
    """
    all_names = [s["name"] for s in stories]
    rooftop = [n for n in all_names if is_rooftop_story(n)]
    # Exclude RF (main building roof) — only R1F+ and PRF are replicable
    replicable = [n for n in rooftop if n != "RF"]
    if len(replicable) < 2:
        return

    # Column/wall floors: R1F ~ second-to-last (e.g., R1F, R2F, R3F — not PRF)
    col_wall_floors = replicable[:-1]
    # Beam floors: R2F ~ last (e.g., R2F, R3F, PRF — not R1F)
    beam_floors = replicable[1:]

    for col in columns:
        if _in_core(col["grid_x"], col["grid_y"], core_grid_area):
            existing = set(col["floors"])
            for f in col_wall_floors:
                if f not in existing:
                    col["floors"].append(f)

    for wall in walls:
        if (_in_core(wall["x1"], wall["y1"], core_grid_area) and
                _in_core(wall["x2"], wall["y2"], core_grid_area)):
            existing = set(wall["floors"])
            for f in col_wall_floors:
                if f not in existing:
                    wall["floors"].append(f)

    for beam in beams:
        if (_in_core(beam["x1"], beam["y1"], core_grid_area) and
                _in_core(beam["x2"], beam["y2"], core_grid_area)):
            existing = set(beam["floors"])
            for f in beam_floors:
                if f not in existing:
                    beam["floors"].append(f)


def replicate_rooftop_small_beams(small_beams, stories, core_grid_area):
    """Add rooftop floors to small beams within core grid area.

    Same logic as beams: add second rooftop ~ last rooftop floor.
    Exported for use by sb_patch_build.py.
    """
    if not core_grid_area or not has_r2f_or_above(stories):
        return

    all_names = [s["name"] for s in stories]
    rooftop = [n for n in all_names if is_rooftop_story(n)]
    replicable = [n for n in rooftop if n != "RF"]
    if len(replicable) < 2:
        return

    beam_floors = replicable[1:]

    for sb in small_beams:
        if (_in_core(sb["x1"], sb["y1"], core_grid_area) and
                _in_core(sb["x2"], sb["y2"], core_grid_area)):
            existing = set(sb["floors"])
            for f in beam_floors:
                if f not in existing:
                    sb["floors"].append(f)


# ── Config Building ────────────────────────────────────────────

def build_config(elements, grid_info, project_name, save_path):
    """Merge elements.json + grid_info.json → model_config dict.

    Returns: (config_dict, warnings_list)
    """
    warnings = []
    config = {}

    # Project
    config["project"] = {
        "name": project_name,
        "save_path": save_path,
        "units": 12,
        "new_model": True,
    }

    # From grid_info
    config["grids"] = grid_info["grids"]
    config["stories"] = grid_info["stories"]
    config["base_elevation"] = grid_info.get("base_elevation", 0)
    config["strength_map"] = grid_info.get("strength_map", {})

    # Optional grid_info fields
    for key in ("building_outline", "substructure_outline",
                "core_grid_area", "slab_region_matrix"):
        if key in grid_info:
            config[key] = grid_info[key]

    # From elements — strip auxiliary fields
    columns = strip_columns(elements.get("columns", []))
    beams = strip_beams(elements.get("beams", []))
    walls = strip_walls(elements.get("walls", []))

    # Sections from elements (Phase 1: no SB/slab/raft)
    elem_sections = elements.get("sections", {})
    config["sections"] = {
        "frame": list(elem_sections.get("frame", [])),
        "wall": list(elem_sections.get("wall", [])),
        "slab": [],
        "raft": [],
    }

    # Warn about empty sections (uncertain from pptx_to_elements)
    for i, col in enumerate(columns):
        if not col.get("section"):
            warnings.append(
                f"WARNING: columns[{i}] at ({col['grid_x']}, {col['grid_y']}) has empty section")
    for i, beam in enumerate(beams):
        if not beam.get("section"):
            warnings.append(
                f"WARNING: beams[{i}] at ({beam['x1']},{beam['y1']})-"
                f"({beam['x2']},{beam['y2']}) has empty section")
    for i, wall in enumerate(walls):
        if not wall.get("section"):
            warnings.append(
                f"WARNING: walls[{i}] at ({wall['x1']},{wall['y1']})-"
                f"({wall['x2']},{wall['y2']}) has empty section")

    # Building outline filtering (non-rectangular only)
    outline = grid_info.get("building_outline")
    if outline and is_non_rectangular(outline):
        columns, beams, walls, outline_warnings = filter_by_outline(
            columns, beams, walls, outline)
        warnings.extend(outline_warnings)

    # Rooftop replication
    core_grid_area = grid_info.get("core_grid_area")
    if core_grid_area and has_r2f_or_above(config["stories"]):
        replicate_rooftop(columns, beams, walls, config["stories"], core_grid_area)

    config["columns"] = columns
    config["beams"] = beams
    config["walls"] = walls
    config["small_beams"] = []
    config["slabs"] = []

    return config, warnings


def main():
    parser = argparse.ArgumentParser(
        description="Merge elements.json + grid_info.json → model_config.json")
    parser.add_argument("--elements", required=True,
                        help="Path to elements.json (pptx_to_elements output)")
    parser.add_argument("--grid-info", required=True,
                        help="Path to grid_info.json (READER output)")
    parser.add_argument("--output", required=True,
                        help="Output path for model_config.json")
    parser.add_argument("--save-path", required=True,
                        help="ETABS .EDB save path")
    parser.add_argument("--project-name", required=True,
                        help="Project name")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing output")
    args = parser.parse_args()

    # Load inputs
    with open(args.elements, encoding="utf-8") as f:
        elements = json.load(f)
    print(f"Elements loaded: {args.elements}")
    print(f"  columns: {len(elements.get('columns', []))}")
    print(f"  beams: {len(elements.get('beams', []))}")
    print(f"  walls: {len(elements.get('walls', []))}")

    with open(args.grid_info, encoding="utf-8") as f:
        grid_info = json.load(f)
    print(f"Grid info loaded: {args.grid_info}")
    print(f"  stories: {len(grid_info.get('stories', []))}")

    # Build config
    config, build_warnings = build_config(
        elements, grid_info, args.project_name, args.save_path)

    for w in build_warnings:
        print(f"  {w}")

    # Validate
    errors, val_warnings = validate_config(config)
    for w in val_warnings:
        print(f"  WARNING: {w}")
    if errors:
        print(f"\nVALIDATION FAILED ({len(errors)} errors):")
        for e in errors:
            print(f"  ERROR: {e}")

    # Summary
    print(f"\nConfig summary:")
    print(f"  columns: {len(config['columns'])}")
    print(f"  beams: {len(config['beams'])}")
    print(f"  walls: {len(config['walls'])}")
    print(f"  small_beams: {len(config['small_beams'])} (Phase 1: empty)")
    print(f"  slabs: {len(config['slabs'])} (Phase 1: empty)")
    print(f"  frame sections: {config['sections']['frame']}")
    print(f"  wall sections: {config['sections']['wall']}")

    # Write output
    if args.dry_run:
        print("\n[DRY RUN] Output not written.")
        if errors:
            sys.exit(1)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"\nConfig written to: {args.output}")
        if errors:
            sys.exit(1)


if __name__ == "__main__":
    main()
