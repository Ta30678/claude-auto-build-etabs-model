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
from golden_scripts.constants import is_rooftop_story, is_substructure_story, is_superstructure_story


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

def strip_columns(columns, grid_info=None):
    """Normalize column fields: accept grid_x/grid_y or x1/y1, strip page_num.

    No snap/filter/dedup — these are handled upstream:
    - Snap: affine_calibrate.py snap_elements_to_grid() (per-axis, 0.5m tolerance)
    - Dedup: elements_merge.py dedup_elements()
    - Filter: PPT extraction + color matching

    Parameters
    ----------
    columns : list[dict]
        Columns with grid_x/x1 and grid_y/y1.
    grid_info : dict, optional
        Accepted for backward compatibility but not used.

    Returns
    -------
    (normalized_columns, dropped_count=0)
    """
    result = []
    for col in columns:
        result.append({
            "grid_x": round(col.get("grid_x", col.get("x1", 0)), 2),
            "grid_y": round(col.get("grid_y", col.get("y1", 0)), 2),
            "section": col.get("section", ""),
            "floors": list(col.get("floors", [])),
        })
    return result, 0


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

def _all_substructure(floors):
    """Check if ALL floors in the list are substructure (B*F, 1F, BASE)."""
    return bool(floors) and all(is_substructure_story(f) for f in floors)


def _choose_outline(element, building_outline, sub_outline):
    """Pick the right outline for an element based on its floors.

    Substructure-only elements use substructure_outline (rectangular → skip).
    Mixed / superstructure elements use building_outline (may be L-shaped).
    """
    floors = element.get("floors", [])
    if _all_substructure(floors) and sub_outline:
        return sub_outline
    return building_outline


def filter_by_outline(columns, beams, walls, outline,
                      substructure_outline=None, tolerance=0.01):
    """Filter elements outside the appropriate outline polygon.

    Uses building_outline for superstructure elements and
    substructure_outline for substructure-only elements.
    - Columns: point must be inside polygon.
    - Beams/walls: both endpoints outside → remove.

    Returns: (filtered_columns, filtered_beams, filtered_walls, warnings)
    """
    warnings = []
    if not outline or not is_non_rectangular(outline):
        return columns, beams, walls, warnings

    filtered_cols = []
    for i, col in enumerate(columns):
        ol = _choose_outline(col, outline, substructure_outline)
        if not is_non_rectangular(ol):
            filtered_cols.append(col)
            continue
        if point_in_or_near_polygon(col["grid_x"], col["grid_y"], ol, tolerance):
            filtered_cols.append(col)
        else:
            warnings.append(
                f"columns[{i}]: ({col['grid_x']}, {col['grid_y']}) "
                f"{col.get('section', '')} outside building_outline — REMOVED")

    filtered_beams = []
    for i, beam in enumerate(beams):
        ol = _choose_outline(beam, outline, substructure_outline)
        if not is_non_rectangular(ol):
            filtered_beams.append(beam)
            continue
        p1_in = point_in_or_near_polygon(beam["x1"], beam["y1"], ol, tolerance)
        p2_in = point_in_or_near_polygon(beam["x2"], beam["y2"], ol, tolerance)
        if p1_in or p2_in:
            filtered_beams.append(beam)
        else:
            warnings.append(
                f"beams[{i}]: ({beam['x1']},{beam['y1']})-({beam['x2']},{beam['y2']}) "
                f"{beam.get('section', '')} outside building_outline — REMOVED")

    filtered_walls = []
    for i, wall in enumerate(walls):
        ol = _choose_outline(wall, outline, substructure_outline)
        if not is_non_rectangular(ol):
            filtered_walls.append(wall)
            continue
        p1_in = point_in_or_near_polygon(wall["x1"], wall["y1"], ol, tolerance)
        p2_in = point_in_or_near_polygon(wall["x2"], wall["y2"], ol, tolerance)
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


def _find_top_floor(stories):
    """Find the highest superstructure story (e.g., 14F)."""
    super_stories = [s["name"] for s in stories
                     if is_superstructure_story(s["name"])]
    return super_stories[-1] if super_stories else None


def _in_core(x, y, core_grid_area, tolerance=0.01):
    """Check if point is within core_grid_area rectangle."""
    x_range = core_grid_area["x_range"]
    y_range = core_grid_area["y_range"]
    return (x_range[0] - tolerance <= x <= x_range[1] + tolerance and
            y_range[0] - tolerance <= y <= y_range[1] + tolerance)


def replicate_rooftop(columns, beams, walls, stories, core_grid_area,
                      slabs=None):
    """Add rooftop floors to elements. Two phases:

    Phase A — R1F:
      Columns/walls in core → add R1F (core check, same as Phase B).
      Beams/slabs with top_floor → add R1F (full copy, no core check).
      Fallback: when core_grid_area is None, all elements get full copy.

    Phase B — R2F~PRF core copy (needs core_grid_area):
      Columns/walls in core → add R2F ~ second-to-last rooftop (not PRF).
      Beams/slabs in core → add R2F ~ last rooftop (including PRF).

    Modifies elements in-place.
    """
    all_names = [s["name"] for s in stories]
    rooftop = [n for n in all_names if is_rooftop_story(n)]
    # Exclude RF (main building roof) — only R1F+ and PRF are replicable
    replicable = [n for n in rooftop if n != "RF"]
    if not replicable:
        return

    # ── Phase A: R1F — columns/walls use core check, beams/slabs full copy ──
    top_floor = _find_top_floor(stories)
    if top_floor and "R1F" in replicable:
        for col in columns:
            if top_floor in col["floors"] and "R1F" not in col["floors"]:
                if not core_grid_area or _in_core(col["grid_x"], col["grid_y"], core_grid_area):
                    col["floors"].append("R1F")

        for wall in walls:
            if top_floor in wall["floors"] and "R1F" not in wall["floors"]:
                if not core_grid_area or (_in_core(wall["x1"], wall["y1"], core_grid_area) and
                        _in_core(wall["x2"], wall["y2"], core_grid_area)):
                    wall["floors"].append("R1F")

        for beam in beams:
            if top_floor in beam["floors"] and "R1F" not in beam["floors"]:
                beam["floors"].append("R1F")

        if slabs:
            for slab in slabs:
                if top_floor in slab["floors"] and "R1F" not in slab["floors"]:
                    slab["floors"].append("R1F")

    # ── Phase B: R2F~PRF core copy (needs core_grid_area) ──
    r2f_plus = [n for n in replicable if n != "R1F"]
    if not r2f_plus or not core_grid_area:
        return

    # Column/wall floors: R2F ~ second-to-last (e.g., R2F, R3F — not PRF)
    col_wall_floors = r2f_plus[:-1] if len(r2f_plus) > 1 else []
    # Beam/slab floors: R2F ~ last (e.g., R2F, R3F, PRF)
    beam_floors = r2f_plus

    for col in columns:
        if (top_floor in col["floors"] or "R1F" in col["floors"]) and \
                _in_core(col["grid_x"], col["grid_y"], core_grid_area):
            existing = set(col["floors"])
            for f in col_wall_floors:
                if f not in existing:
                    col["floors"].append(f)

    for wall in walls:
        if (top_floor in wall["floors"] or "R1F" in wall["floors"]) and \
                (_in_core(wall["x1"], wall["y1"], core_grid_area) and
                _in_core(wall["x2"], wall["y2"], core_grid_area)):
            existing = set(wall["floors"])
            for f in col_wall_floors:
                if f not in existing:
                    wall["floors"].append(f)

    for beam in beams:
        if (top_floor in beam["floors"] or "R1F" in beam["floors"]) and \
                (_in_core(beam["x1"], beam["y1"], core_grid_area) and
                _in_core(beam["x2"], beam["y2"], core_grid_area)):
            existing = set(beam["floors"])
            for f in beam_floors:
                if f not in existing:
                    beam["floors"].append(f)

    if slabs:
        for slab in slabs:
            corners = slab.get("corners", [])
            if (top_floor in slab["floors"] or "R1F" in slab["floors"]) and \
                    corners and all(
                    _in_core(c[0], c[1], core_grid_area) for c in corners):
                existing = set(slab["floors"])
                for f in beam_floors:
                    if f not in existing:
                        slab["floors"].append(f)


def replicate_rooftop_sb_slabs(small_beams, slabs, stories, core_grid_area):
    """Add rooftop floors to small beams and slabs. Two phases:

    Phase A — R1F full copy: SB/Slab with top_floor → add R1F (no core check).
    Phase B — R2F~PRF core copy: SB/Slab in core → add R2F~PRF.

    Exported for use by sb_patch_build.py.
    """
    all_names = [s["name"] for s in stories]
    rooftop = [n for n in all_names if is_rooftop_story(n)]
    replicable = [n for n in rooftop if n != "RF"]
    if not replicable:
        return

    # ── Phase A: R1F full copy (no core check) ──
    top_floor = _find_top_floor(stories)
    if top_floor and "R1F" in replicable:
        for sb in small_beams:
            if top_floor in sb["floors"] and "R1F" not in sb["floors"]:
                sb["floors"].append("R1F")

        if slabs:
            for slab in slabs:
                if top_floor in slab["floors"] and "R1F" not in slab["floors"]:
                    slab["floors"].append("R1F")

    # ── Phase B: R2F~PRF core copy (needs core_grid_area) ──
    r2f_plus = [n for n in replicable if n != "R1F"]
    if not r2f_plus or not core_grid_area:
        return

    beam_floors = r2f_plus

    for sb in small_beams:
        if top_floor not in sb["floors"]:
            continue  # Only replicate SBs from the top superstructure floor
        if (_in_core(sb["x1"], sb["y1"], core_grid_area) and
                _in_core(sb["x2"], sb["y2"], core_grid_area)):
            existing = set(sb["floors"])
            for f in beam_floors:
                if f not in existing:
                    sb["floors"].append(f)

    if slabs:
        for slab in slabs:
            if top_floor not in slab["floors"]:
                continue  # Only replicate slabs from the top superstructure floor
            corners = slab.get("corners", [])
            if corners and all(
                    _in_core(c[0], c[1], core_grid_area) for c in corners):
                existing = set(slab["floors"])
                for f in beam_floors:
                    if f not in existing:
                        slab["floors"].append(f)


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
        "skip_materials": False,
    }

    # From grid_info
    config["grids"] = grid_info["grids"]
    config["stories"] = grid_info["stories"]
    config["base_elevation"] = grid_info.get("base_elevation", 0)
    config["strength_map"] = grid_info.get("strength_map", {})

    # Optional grid_info fields (slab_region_matrix moved to Phase 2 SB-READER)
    for key in ("building_outline", "substructure_outline", "core_grid_area"):
        if key in grid_info:
            config[key] = grid_info[key]

    # From elements — strip auxiliary fields
    columns, _ = strip_columns(elements.get("columns", []), grid_info)
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
    sub_outline = grid_info.get("substructure_outline")
    if outline and is_non_rectangular(outline):
        columns, beams, walls, outline_warnings = filter_by_outline(
            columns, beams, walls, outline,
            substructure_outline=sub_outline)
        warnings.extend(outline_warnings)

    # Rooftop replication
    core_grid_area = grid_info.get("core_grid_area")
    rooftop_names = [s["name"] for s in config["stories"]
                     if is_rooftop_story(s["name"])]
    if rooftop_names:
        replicate_rooftop(columns, beams, walls, config["stories"],
                          core_grid_area)
        # Summary log
        top_floor = _find_top_floor(config["stories"])
        for rn in rooftop_names:
            n_cols = sum(1 for c in columns if rn in c["floors"])
            n_beams = sum(1 for b in beams if rn in b["floors"])
            n_walls = sum(1 for w in walls if rn in w["floors"])
            print(f"  Rooftop {rn}: {n_cols} columns, {n_beams} beams, {n_walls} walls")
        if top_floor:
            total_cols = sum(1 for c in columns if top_floor in c["floors"])
            total_beams = sum(1 for b in beams if top_floor in b["floors"])
            print(f"  (Top floor {top_floor}: {total_cols} columns, {total_beams} beams)")
            # Warn if R2F+ has suspiciously many elements (core filter may be broken)
            for rn in rooftop_names:
                if rn in ("RF", "R1F"):
                    continue
                n_cols_rn = sum(1 for c in columns if rn in c["floors"])
                if total_cols > 0 and n_cols_rn > total_cols * 0.5:
                    w = (f"WARNING: {rn} has {n_cols_rn} columns "
                         f"(> 50% of {top_floor}'s {total_cols}) — "
                         f"core_grid_area filter may not be working correctly")
                    warnings.append(w)
                    print(f"  {w}")

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
