"""
Config Merge Tool — Merge a base model_config.json with a patch file.

Phase 1 produces model_config.json (grids, stories, columns, walls, beams).
Phase 2 produces sb_slabs_patch.json (small_beams, slabs, additional sections).

This tool merges the patch into the base config for Phase 2 execution.

Usage:
    python -m golden_scripts.tools.config_merge \
        --base model_config.json \
        --patch sb_slabs_patch.json \
        --output merged_config.json

    # Validate only (no output written on errors):
    python -m golden_scripts.tools.config_merge \
        --base model_config.json \
        --patch sb_slabs_patch.json \
        --output merged_config.json \
        --validate
"""
import json
import argparse
import os
import re
import sys


def merge_configs(base: dict, patch: dict) -> dict:
    """Merge patch into base config.

    Merge rules:
    - small_beams: replaced entirely from patch
    - slabs: replaced entirely from patch
    - sections.frame: union of both lists (no duplicates)
    - sections.slab: union of both lists (no duplicates)
    - sections.wall: union (no duplicates)
    - sections.raft: union (no duplicates)
    - All other fields: kept from base unchanged
    """
    merged = json.loads(json.dumps(base))  # deep copy

    # Replace small_beams and slabs from patch
    if "small_beams" in patch:
        merged["small_beams"] = patch["small_beams"]
    if "slabs" in patch:
        merged["slabs"] = patch["slabs"]

    # Merge sections (union, no duplicates)
    if "sections" in patch:
        base_sections = merged.get("sections", {})
        patch_sections = patch["sections"]

        # Frame sections: list of strings
        if "frame" in patch_sections:
            base_frames = set(base_sections.get("frame", []))
            patch_frames = set(patch_sections["frame"])
            # Preserve base order, append new from patch
            merged_frames = list(base_sections.get("frame", []))
            for f in patch_sections["frame"]:
                if f not in base_frames:
                    merged_frames.append(f)
            base_sections["frame"] = merged_frames

        # Slab sections: list of integers (thicknesses)
        if "slab" in patch_sections:
            base_slabs = set(base_sections.get("slab", []))
            merged_slabs = list(base_sections.get("slab", []))
            for s in patch_sections["slab"]:
                if s not in base_slabs:
                    merged_slabs.append(s)
            base_sections["slab"] = merged_slabs

        # Wall sections: list of integers
        if "wall" in patch_sections:
            base_walls = set(base_sections.get("wall", []))
            merged_walls = list(base_sections.get("wall", []))
            for w in patch_sections["wall"]:
                if w not in base_walls:
                    merged_walls.append(w)
            base_sections["wall"] = merged_walls

        # Raft sections: list of integers
        if "raft" in patch_sections:
            base_rafts = set(base_sections.get("raft", []))
            merged_rafts = list(base_sections.get("raft", []))
            for r in patch_sections["raft"]:
                if r not in base_rafts:
                    merged_rafts.append(r)
            base_sections["raft"] = merged_rafts

        merged["sections"] = base_sections

    return merged


def validate_merged(merged: dict) -> list:
    """Basic validation of the merged config. Returns list of warnings."""
    warnings = []

    if not merged.get("small_beams"):
        warnings.append("small_beams is empty after merge")
    if not merged.get("slabs"):
        warnings.append("slabs is empty after merge")
    if not merged.get("grids"):
        warnings.append("grids missing from base config")
    if not merged.get("stories"):
        warnings.append("stories missing from base config")
    if not merged.get("strength_map"):
        warnings.append("strength_map missing from base config")

    return warnings


# --- Comprehensive validation ---

_FRAME_RE = re.compile(r'^(B|SB|WB|FB|FSB|FWB|C)\d+X\d+(?:C\d+)?$')
_AREA_RE = re.compile(r'^(S|W|FS)\d+(?:C\d+)?$')


def validate_config(config: dict) -> tuple:
    """Validate config for common AI-generated JSON errors.

    Returns (errors: list[str], warnings: list[str]).
    Errors are fatal (will cause ETABS API failures).
    Warnings are informational.
    """
    errors = []
    warnings = []

    # Build story name set
    story_names = set()
    for s in config.get("stories", []):
        if isinstance(s, dict) and "name" in s:
            story_names.add(s["name"])

    # Build section sets from config
    frame_sections = set(config.get("sections", {}).get("frame", []))
    slab_sections = set()
    for t in config.get("sections", {}).get("slab", []):
        slab_sections.add(f"S{t}")
    raft_sections = set()
    for t in config.get("sections", {}).get("raft", []):
        raft_sections.add(f"FS{t}")
    wall_sections = set()
    for t in config.get("sections", {}).get("wall", []):
        wall_sections.add(f"W{t}")

    # --- Validate beams (including small_beams) ---
    for key in ("beams", "small_beams"):
        for i, beam in enumerate(config.get(key, [])):
            loc = f"{key}[{i}]"

            # Coordinate types
            for coord in ("x1", "y1", "x2", "y2"):
                val = beam.get(coord)
                if val is not None and not isinstance(val, (int, float)):
                    errors.append(f"{loc}.{coord}: expected number, got {type(val).__name__} ({val!r})")

            # Section name format
            sec = beam.get("section", "")
            base_sec = re.sub(r'C\d+$', '', sec)  # strip Cfc suffix for lookup
            if sec and not _FRAME_RE.match(sec):
                errors.append(f"{loc}.section: invalid frame section name {sec!r}")
            elif sec and base_sec not in frame_sections and sec not in frame_sections:
                warnings.append(f"{loc}.section: {sec!r} not in sections.frame")

            # Floors must be array of strings
            floors = beam.get("floors")
            if floors is not None:
                if not isinstance(floors, list):
                    errors.append(f"{loc}.floors: expected array, got {type(floors).__name__} ({floors!r})")
                else:
                    for j, fl in enumerate(floors):
                        if not isinstance(fl, str):
                            errors.append(f"{loc}.floors[{j}]: expected string, got {type(fl).__name__} ({fl!r})")
                        elif fl not in story_names:
                            errors.append(f"{loc}.floors[{j}]: floor {fl!r} not in stories")

            # Zero-length beam check
            x1, y1 = beam.get("x1"), beam.get("y1")
            x2, y2 = beam.get("x2"), beam.get("y2")
            if (isinstance(x1, (int, float)) and isinstance(y1, (int, float)) and
                    isinstance(x2, (int, float)) and isinstance(y2, (int, float))):
                if x1 == x2 and y1 == y2:
                    errors.append(f"{loc}: zero-length beam at ({x1}, {y1})")

    # --- Validate columns ---
    for i, col in enumerate(config.get("columns", [])):
        loc = f"columns[{i}]"
        sec = col.get("section", "")
        if sec and not _FRAME_RE.match(sec):
            errors.append(f"{loc}.section: invalid frame section name {sec!r}")
        # Coordinate types
        for coord in ("grid_x", "grid_y"):
            val = col.get(coord)
            if val is not None and not isinstance(val, (int, float)):
                errors.append(f"{loc}.{coord}: expected number, got {type(val).__name__} ({val!r})")
        floors = col.get("floors")
        if floors is not None:
            if not isinstance(floors, list):
                errors.append(f"{loc}.floors: expected array, got {type(floors).__name__}")
            else:
                for j, fl in enumerate(floors):
                    if not isinstance(fl, str):
                        errors.append(f"{loc}.floors[{j}]: expected string, got {type(fl).__name__}")
                    elif fl not in story_names:
                        errors.append(f"{loc}.floors[{j}]: floor {fl!r} not in stories")

    # --- Validate walls ---
    for i, wall in enumerate(config.get("walls", [])):
        loc = f"walls[{i}]"
        # Coordinate types
        for coord in ("x1", "y1", "x2", "y2"):
            val = wall.get(coord)
            if val is not None and not isinstance(val, (int, float)):
                errors.append(f"{loc}.{coord}: expected number, got {type(val).__name__} ({val!r})")
        floors = wall.get("floors")
        if floors is not None:
            if not isinstance(floors, list):
                errors.append(f"{loc}.floors: expected array, got {type(floors).__name__}")
            else:
                for j, fl in enumerate(floors):
                    if not isinstance(fl, str):
                        errors.append(f"{loc}.floors[{j}]: expected string, got {type(fl).__name__}")
                    elif fl not in story_names:
                        errors.append(f"{loc}.floors[{j}]: floor {fl!r} not in stories")

    # --- Validate slabs ---
    for i, slab in enumerate(config.get("slabs", [])):
        loc = f"slabs[{i}]"

        # Section name format
        sec = slab.get("section", "")
        base_sec = re.sub(r'C\d+$', '', sec)  # strip Cfc suffix
        if sec and not _AREA_RE.match(sec):
            errors.append(f"{loc}.section: invalid area section name {sec!r}")
        elif sec:
            prefix = re.match(r'^(S|W|FS)', sec)
            if prefix and prefix.group(1) == "FS":
                if base_sec not in raft_sections and sec not in raft_sections:
                    warnings.append(f"{loc}.section: {sec!r} not in sections.raft")
            elif prefix and prefix.group(1) == "S":
                if base_sec not in slab_sections and sec not in slab_sections:
                    warnings.append(f"{loc}.section: {sec!r} not in sections.slab")

        # Floors must be array of strings
        floors = slab.get("floors")
        if floors is not None:
            if not isinstance(floors, list):
                errors.append(f"{loc}.floors: expected array, got {type(floors).__name__} ({floors!r})")
            else:
                for j, fl in enumerate(floors):
                    if not isinstance(fl, str):
                        errors.append(f"{loc}.floors[{j}]: expected string, got {type(fl).__name__}")
                    elif fl not in story_names:
                        errors.append(f"{loc}.floors[{j}]: floor {fl!r} not in stories")

        # Corners validation
        corners = slab.get("corners")
        if corners is not None:
            if not isinstance(corners, list):
                errors.append(f"{loc}.corners: expected array, got {type(corners).__name__}")
            else:
                for j, pt in enumerate(corners):
                    if not isinstance(pt, list) or len(pt) != 2:
                        errors.append(f"{loc}.corners[{j}]: expected [x, y] pair, got {pt!r}")
                    else:
                        for k, v in enumerate(pt):
                            if not isinstance(v, (int, float)):
                                errors.append(f"{loc}.corners[{j}][{k}]: expected number, got {type(v).__name__} ({v!r})")

    # --- Validate sections.frame format ---
    for i, sec_name in enumerate(config.get("sections", {}).get("frame", [])):
        if not _FRAME_RE.match(sec_name):
            errors.append(
                f"sections.frame[{i}] = {sec_name!r} — 格式不匹配\n"
                f"  期望格式: {{PREFIX}}{{WIDTH}}X{{DEPTH}}[C{{fc}}]  例如: B55X80 或 B55X80C350\n"
                f"  有效 PREFIX: B, SB, WB, FB, FSB, FWB, C")

    # --- Validate strength_map key format ---
    for key in config.get("strength_map", {}):
        if not re.match(r'^\w+~\w+$', key):
            errors.append(
                f"strength_map key {key!r} — 格式不匹配\n"
                f"  期望格式: {{START}}~{{END}}  例如: B3F~1F 或 2F~7F")

    # --- Validate sections coverage ---
    frame_bases = set()
    for sec in config.get("sections", {}).get("frame", []):
        frame_bases.add(sec)
        frame_bases.add(re.sub(r'C\d+$', '', sec))
    for key in ("columns", "beams", "small_beams"):
        for i, elem in enumerate(config.get(key, [])):
            sec = elem.get("section", "")
            if not sec:
                continue
            base = re.sub(r'C\d+$', '', sec)
            if base not in frame_bases and sec not in frame_bases:
                errors.append(
                    f"{key}[{i}].section = {sec!r} — base name {base!r} not in sections.frame\n"
                    f"  Add {base!r} to sections.frame or check spelling")

    # --- Validate stories elevation order ---
    for i, s in enumerate(config.get("stories", [])):
        h = s.get("height", 0)
        if not isinstance(h, (int, float)) or h <= 0:
            errors.append(f"stories[{i}].height = {h!r} — must be a positive number")

    # --- Validate sections.wall format ---
    for i, t in enumerate(config.get("sections", {}).get("wall", [])):
        if not isinstance(t, int):
            errors.append(
                f"sections.wall[{i}] = {t!r} — expected integer (thickness in cm), got {type(t).__name__}")

    # --- Validate sections.slab format ---
    for i, t in enumerate(config.get("sections", {}).get("slab", [])):
        if not isinstance(t, int):
            errors.append(
                f"sections.slab[{i}] = {t!r} — expected integer (thickness in cm), got {type(t).__name__}")

    # --- WARNING: sections.frame with Cfc suffix ---
    for sec in config.get("sections", {}).get("frame", []):
        m = re.match(r'^(?:B|SB|WB|FB|FSB|FWB|C)\d+X\d+C(\d+)$', sec)
        if m:
            warnings.append(
                f"sections.frame: '{sec}' has Cfc suffix — only this grade will be created (no expansion)")

    # --- WARNING: strength_map coverage ---
    all_story_list = [s["name"] for s in config.get("stories", [])
                      if isinstance(s, dict) and "name" in s]
    covered = set()
    for range_key in config.get("strength_map", {}):
        if "~" in range_key:
            parts = range_key.split("~", 1)
            start, end = parts[0], parts[1]
            if start in all_story_list and end in all_story_list:
                i_s = all_story_list.index(start)
                i_e = all_story_list.index(end)
                if i_s > i_e:
                    i_s, i_e = i_e, i_s
                covered.update(all_story_list[i_s:i_e + 1])
        else:
            if range_key in all_story_list:
                covered.add(range_key)
    for s_name in all_story_list:
        if s_name not in covered:
            warnings.append(f"strength_map: story {s_name!r} not covered by any range")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(
        description="Merge base model_config.json with sb_slabs_patch.json")
    parser.add_argument("--base", required=True,
                        help="Path to base model_config.json (Phase 1 output)")
    parser.add_argument("--patch", required=True,
                        help="Path to sb_slabs_patch.json (Phase 2 output)")
    parser.add_argument("--output", required=True,
                        help="Path for merged output config")
    parser.add_argument("--validate", action="store_true",
                        help="Run comprehensive validation; exit non-zero on errors")
    args = parser.parse_args()

    # Load base config
    with open(args.base, encoding="utf-8") as f:
        base = json.load(f)
    print(f"Base config loaded: {args.base}")
    print(f"  columns: {len(base.get('columns', []))}")
    print(f"  beams: {len(base.get('beams', []))}")
    print(f"  walls: {len(base.get('walls', []))}")

    # Load patch
    with open(args.patch, encoding="utf-8") as f:
        patch = json.load(f)
    print(f"Patch loaded: {args.patch}")
    print(f"  small_beams: {len(patch.get('small_beams', []))}")
    print(f"  slabs: {len(patch.get('slabs', []))}")

    # Merge
    merged = merge_configs(base, patch)

    # Basic validation
    basic_warnings = validate_merged(merged)
    if basic_warnings:
        for w in basic_warnings:
            print(f"  WARNING: {w}")

    # Comprehensive validation
    errors, val_warnings = validate_config(merged)
    if val_warnings:
        for w in val_warnings:
            print(f"  WARNING: {w}")
    if errors:
        print(f"\nVALIDATION FAILED ({len(errors)} errors):")
        for e in errors:
            print(f"  ERROR: {e}")
        if args.validate:
            sys.exit(1)
    elif args.validate:
        print("\nValidation passed.")

    # Write output (skip if --validate and errors)
    if errors and args.validate:
        print("\nOutput NOT written due to validation errors.")
    else:
        from golden_scripts.tools.config_integrity import stamp_config
        stamp_config(merged)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"\nMerged config written to: {args.output}")
        print(f"  columns: {len(merged.get('columns', []))}")
        print(f"  beams: {len(merged.get('beams', []))}")
        print(f"  walls: {len(merged.get('walls', []))}")
        print(f"  small_beams: {len(merged.get('small_beams', []))}")
        print(f"  slabs: {len(merged.get('slabs', []))}")
        print(f"  frame sections: {merged.get('sections', {}).get('frame', [])}")


if __name__ == "__main__":
    main()
