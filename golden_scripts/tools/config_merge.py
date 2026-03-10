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
"""
import json
import argparse
import os
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


def main():
    parser = argparse.ArgumentParser(
        description="Merge base model_config.json with sb_slabs_patch.json")
    parser.add_argument("--base", required=True,
                        help="Path to base model_config.json (Phase 1 output)")
    parser.add_argument("--patch", required=True,
                        help="Path to sb_slabs_patch.json (Phase 2 output)")
    parser.add_argument("--output", required=True,
                        help="Path for merged output config")
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

    # Validate
    warnings = validate_merged(merged)
    if warnings:
        for w in warnings:
            print(f"  WARNING: {w}")

    # Write output
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
