"""
Elements Merge Tool — Merge multiple elements.json files into one.

Phase 1 parallel extraction: READER-A and READER-B each produce partial
elements files (e.g., elements_A.json for superstructure pages, elements_B.json
for substructure pages). This tool merges them into a unified elements.json.

Usage:
    python -m golden_scripts.tools.elements_merge \
        --inputs elements_A.json elements_B.json \
        --output elements.json
        [--dry-run]
"""
import json
import argparse
import sys


def dedup_elements(elements_list, element_type):
    """Deduplicate elements by their defining tuple.

    For columns: (grid_x, grid_y, section, tuple(sorted(floors)))
    For beams/walls/small_beams: (x1, y1, x2, y2, section, tuple(sorted(floors)))

    Returns (deduplicated_list, duplicates_removed_count).
    """
    seen = set()
    result = []
    dupes = 0

    for el in elements_list:
        if element_type == "columns":
            key = (
                el.get("grid_x", ""),
                el.get("grid_y", ""),
                el.get("section", ""),
                tuple(sorted(el.get("floors", []))),
            )
        else:
            key = (
                el.get("x1", 0),
                el.get("y1", 0),
                el.get("x2", 0),
                el.get("y2", 0),
                el.get("section", ""),
                tuple(sorted(el.get("floors", []))),
            )

        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        result.append(el)

    return result, dupes


def merge_sections(sections_list):
    """Merge sections from multiple files.

    - frame: union of all frame section lists (sorted, unique strings)
    - wall: union of all wall thickness lists (sorted, unique integers)
    """
    all_frame = set()
    all_wall = set()

    for sec in sections_list:
        all_frame.update(sec.get("frame", []))
        all_wall.update(sec.get("wall", []))

    return {
        "frame": sorted(all_frame),
        "wall": sorted(all_wall),
    }


def merge_metadata(metadata_list):
    """Merge _metadata from multiple files.

    - Combine per_page_stats dicts (pages shouldn't overlap, just merge)
    - Combine page_floors dicts
    - Combine warnings lists
    - Take first file's input_file, phase, timestamp etc.
    - Sum totals values
    """
    if not metadata_list:
        return {}

    base = dict(metadata_list[0])
    merged_per_page = {}
    merged_page_floors = {}
    merged_warnings = []
    merged_totals = {}

    for meta in metadata_list:
        merged_per_page.update(meta.get("per_page_stats", {}))
        merged_page_floors.update(meta.get("page_floors", {}))
        merged_warnings.extend(meta.get("warnings", []))

        for k, v in meta.get("totals", {}).items():
            if isinstance(v, (int, float)):
                merged_totals[k] = merged_totals.get(k, 0) + v
            else:
                merged_totals[k] = v

    base["per_page_stats"] = merged_per_page
    base["page_floors"] = merged_page_floors
    base["warnings"] = merged_warnings
    base["totals"] = merged_totals
    return base


def normalize_per_slide_input(slide_data):
    """Convert per-slide JSON format to standard elements format.

    Per-slide JSONs from pptx_to_elements.py --slides-info-dir have elements
    grouped by type (columns/beams/walls/small_beams) with element_type field
    on each element. This function converts to the standard merge format.

    Returns:
        Standard elements dict compatible with merge_elements().
    """
    # Per-slide format already has columns/beams/walls/small_beams keys
    # Check if it's actually a per-slide format by looking for _metadata.slide_num
    meta = slide_data.get("_metadata", {})
    is_per_slide = "slide_num" in meta

    if not is_per_slide:
        # Already in standard format
        return slide_data

    # Reconstruct sections from elements
    frame_set = set()
    wall_set = set()
    for cat in ("columns", "beams", "small_beams"):
        for elem in slide_data.get(cat, []):
            sec = elem.get("section", "")
            if sec:
                frame_set.add(sec)
    for elem in slide_data.get("walls", []):
        sec = elem.get("section", "")
        if sec:
            # Wall sections are thickness integers like "W25" -> 25
            import re
            m = re.match(r"W(\d+)", sec)
            if m:
                wall_set.add(int(m.group(1)))

    # Build metadata for merge compatibility
    floors = meta.get("floors", [])
    slide_num = meta.get("slide_num", 0)
    floor_label = meta.get("floor_label", "")

    result = {
        "columns": slide_data.get("columns", []),
        "beams": slide_data.get("beams", []),
        "walls": slide_data.get("walls", []),
        "small_beams": slide_data.get("small_beams", []),
        "sections": {
            "frame": sorted(frame_set),
            "wall": sorted(wall_set),
        },
        "_metadata": {
            "input_file": meta.get("floor_label", "per-slide"),
            "phase": "phase1",
            "per_page_stats": {str(slide_num): meta.get("stats", {})},
            "page_floors": {str(slide_num): floors},
            "totals": {
                "columns": len(slide_data.get("columns", [])),
                "beams": len(slide_data.get("beams", [])),
                "walls": len(slide_data.get("walls", [])),
                "small_beams": len(slide_data.get("small_beams", [])),
            },
            "warnings": [],
        },
    }
    return result


def merge_elements(*element_files):
    """Main merge function.

    Args:
        *element_files: Parsed JSON dicts from elements.json files.

    Returns:
        (merged_dict, stats_dict)
    """
    all_columns = []
    all_beams = []
    all_walls = []
    all_small_beams = []
    all_sections = []
    all_metadata = []

    for ef in element_files:
        all_columns.extend(ef.get("columns", []))
        all_beams.extend(ef.get("beams", []))
        all_walls.extend(ef.get("walls", []))
        all_small_beams.extend(ef.get("small_beams", []))
        all_sections.append(ef.get("sections", {"frame": [], "wall": []}))
        if "_metadata" in ef:
            all_metadata.append(ef["_metadata"])

    col_raw = len(all_columns)
    beam_raw = len(all_beams)
    wall_raw = len(all_walls)
    sb_raw = len(all_small_beams)

    all_columns, col_dupes = dedup_elements(all_columns, "columns")
    all_beams, beam_dupes = dedup_elements(all_beams, "beams")
    all_walls, wall_dupes = dedup_elements(all_walls, "walls")
    all_small_beams, sb_dupes = dedup_elements(all_small_beams, "small_beams")

    merged = {
        "columns": all_columns,
        "beams": all_beams,
        "walls": all_walls,
        "small_beams": all_small_beams,
        "sections": merge_sections(all_sections),
    }

    if all_metadata:
        merged["_metadata"] = merge_metadata(all_metadata)

    # Build empty-section details
    empty_details = []
    for i, c in enumerate(all_columns):
        if c.get("section", "") == "":
            empty_details.append({
                "type": "column",
                "index": i,
                "coords": f"({c.get('grid_x', '')}, {c.get('grid_y', '')})",
                "floors": c.get("floors", []),
            })
    for etype in ("beams", "walls", "small_beams"):
        for i, el in enumerate(merged[etype]):
            if el.get("section", "") == "":
                empty_details.append({
                    "type": etype.rstrip("s"),
                    "index": i,
                    "coords": f"({el.get('x1',0)}, {el.get('y1',0)}) -> ({el.get('x2',0)}, {el.get('y2',0)})",
                    "floors": el.get("floors", []),
                })

    stats = {
        "input_count": len(element_files),
        "columns": {"total": col_raw, "deduped": len(all_columns)},
        "beams": {"total": beam_raw, "deduped": len(all_beams)},
        "walls": {"total": wall_raw, "deduped": len(all_walls)},
        "small_beams": {"total": sb_raw, "deduped": len(all_small_beams)},
        "empty_section_count": len(empty_details),
        "empty_section_details": empty_details,
    }

    return merged, stats


def check_section_coverage(merged, stats):
    """Check section coverage.

    - Count elements with empty section (section == "")
    - If any column or beam has empty section, print WARNING with details
    - If empty section > 30% of total elements, return False
    - Otherwise return True
    """
    total_elements = (
        len(merged.get("columns", []))
        + len(merged.get("beams", []))
        + len(merged.get("walls", []))
        + len(merged.get("small_beams", []))
    )

    if total_elements == 0:
        return True

    empty_count = stats.get("empty_section_count", 0)
    empty_details = stats.get("empty_section_details", [])

    if empty_count > 0:
        # Warn for any empty columns or beams
        critical = [d for d in empty_details if d["type"] in ("column", "beam")]
        if critical:
            print(f"WARNING: {len(critical)} column/beam element(s) have empty sections:")
            for d in critical:
                print(f"  - {d['type']} at {d['coords']}, floors={d['floors']}")

        # Non-critical empties
        other = [d for d in empty_details if d["type"] not in ("column", "beam")]
        if other:
            print(f"WARNING: {len(other)} other element(s) have empty sections:")
            for d in other:
                print(f"  - {d['type']} at {d['coords']}, floors={d['floors']}")

    ratio = empty_count / total_elements
    if ratio > 0.30:
        print(
            f"ERROR: {empty_count}/{total_elements} elements ({ratio:.0%}) have empty sections "
            f"(threshold: 30%). Aborting."
        )
        return False

    return True


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Merge multiple elements.json files into one unified elements.json."
    )
    parser.add_argument(
        "--inputs", nargs="+",
        help="Input elements JSON files to merge",
    )
    parser.add_argument(
        "--inputs-dir",
        help="Directory containing per-slide JSON files to merge (globs *.json)",
    )
    parser.add_argument(
        "--output", required=True,
        help="Output merged elements JSON file",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview without writing output",
    )
    args = parser.parse_args()

    # Validate: need either --inputs or --inputs-dir
    if not args.inputs and not args.inputs_dir:
        print("ERROR: --inputs or --inputs-dir is required")
        sys.exit(1)

    # Collect input file paths
    input_paths = []
    if args.inputs:
        input_paths.extend(args.inputs)
    if args.inputs_dir:
        from pathlib import Path
        dir_path = Path(args.inputs_dir)
        if not dir_path.is_dir():
            print(f"ERROR: --inputs-dir is not a directory: {args.inputs_dir}")
            sys.exit(1)
        json_files = sorted(dir_path.glob("*/elements.json"))
        if not json_files:
            json_files = sorted(dir_path.glob("*.json"))
        if not json_files:
            print(f"ERROR: No .json files found in {args.inputs_dir} (tried */elements.json and *.json)")
            sys.exit(1)
        input_paths.extend(str(f) for f in json_files)
        print(f"Found {len(json_files)} JSON files in {args.inputs_dir}")

    if not input_paths:
        print("ERROR: No input files specified")
        sys.exit(1)

    # Load input files
    element_files = []
    for path in input_paths:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Normalize per-slide format if needed
        data = normalize_per_slide_input(data)
        print(f"Loaded {path}:")
        print(f"  columns={len(data.get('columns', []))}"
              f"  beams={len(data.get('beams', []))}"
              f"  walls={len(data.get('walls', []))}"
              f"  small_beams={len(data.get('small_beams', []))}")
        element_files.append(data)

    # Merge
    merged, stats = merge_elements(*element_files)

    # Summary
    print(f"\n--- Merge Summary ({stats['input_count']} files) ---")
    for cat in ("columns", "beams", "walls", "small_beams"):
        s = stats[cat]
        removed = s["total"] - s["deduped"]
        suffix = f" ({removed} duplicates removed)" if removed else ""
        print(f"  {cat}: {s['total']} -> {s['deduped']}{suffix}")

    sec = merged.get("sections", {})
    print(f"  frame sections: {len(sec.get('frame', []))}")
    print(f"  wall sections:  {len(sec.get('wall', []))}")

    if stats["empty_section_count"] > 0:
        print(f"  empty sections: {stats['empty_section_count']}")

    # Coverage check
    ok = check_section_coverage(merged, stats)

    if args.dry_run:
        print("\n[DRY-RUN] No file written.")
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"\nWrote {args.output}")

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
