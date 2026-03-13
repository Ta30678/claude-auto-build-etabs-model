"""
SB Patch Build Tool — sb_elements_aligned.json → sb_patch.json

Phase 2 deterministic extraction: extracts small beams from aligned elements
and produces a patch file for config_merge.
Replaces the CONFIG-BUILDER's mechanical SB extraction work with a zero-token script.

Usage:
    python -m golden_scripts.tools.sb_patch_build \
        --sb-elements sb_elements_aligned.json \
        --config model_config.json \
        --output sb_patch.json \
        [--dry-run]
"""
import json
import argparse
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from golden_scripts.tools.config_build import (
    strip_small_beams,
    has_r2f_or_above,
    replicate_rooftop_small_beams,
)

_FRAME_RE = re.compile(r'^(B|SB|WB|FB|FSB|FWB|C)\d+X\d+(?:C\d+)?$')


def validate_sb_patch(patch, story_names):
    """Validate sb_patch for common errors.

    Returns: (errors, warnings)
    """
    errors = []
    warnings = []

    for i, sb in enumerate(patch.get("small_beams", [])):
        loc = f"small_beams[{i}]"

        # Coordinate types
        for coord in ("x1", "y1", "x2", "y2"):
            val = sb.get(coord)
            if val is not None and not isinstance(val, (int, float)):
                errors.append(
                    f"{loc}.{coord}: expected number, got {type(val).__name__} ({val!r})")

        # Section regex
        sec = sb.get("section", "")
        if sec and not _FRAME_RE.match(sec):
            errors.append(f"{loc}.section: invalid name {sec!r}")

        # Floors
        floors = sb.get("floors")
        if floors is not None:
            if not isinstance(floors, list):
                errors.append(
                    f"{loc}.floors: expected array, got {type(floors).__name__}")
            else:
                for j, fl in enumerate(floors):
                    if not isinstance(fl, str):
                        errors.append(
                            f"{loc}.floors[{j}]: expected string, got {type(fl).__name__}")
                    elif fl not in story_names:
                        errors.append(
                            f"{loc}.floors[{j}]: floor {fl!r} not in stories")

        # Zero-length check
        x1, y1 = sb.get("x1"), sb.get("y1")
        x2, y2 = sb.get("x2"), sb.get("y2")
        if (isinstance(x1, (int, float)) and isinstance(y1, (int, float)) and
                isinstance(x2, (int, float)) and isinstance(y2, (int, float))):
            if x1 == x2 and y1 == y2:
                errors.append(f"{loc}: zero-length beam at ({x1}, {y1})")

    # Check sections coverage
    frame_sections = set(patch.get("sections", {}).get("frame", []))
    for i, sb in enumerate(patch.get("small_beams", [])):
        sec = sb.get("section", "")
        if sec and sec not in frame_sections:
            base = re.sub(r'C\d+$', '', sec)
            if base not in frame_sections:
                errors.append(
                    f"small_beams[{i}].section = {sec!r} not in sections.frame")

    return errors, warnings


def build_sb_patch(sb_elements, config):
    """Build sb_patch.json from sb_elements_aligned.json + model_config.json.

    Returns: (patch_dict, warnings)
    """
    warnings = []

    # Extract and strip small beams
    raw_sbs = sb_elements.get("small_beams", [])
    small_beams = strip_small_beams(raw_sbs)

    # Collect unique SB sections
    frame_set = set()
    for sb in small_beams:
        sec = sb.get("section", "")
        if sec:
            frame_set.add(sec)

    # Rooftop replication
    stories = config.get("stories", [])
    core_grid_area = config.get("core_grid_area")
    if core_grid_area and has_r2f_or_above(stories):
        replicate_rooftop_small_beams(small_beams, stories, core_grid_area)

    # Warn about empty sections
    for i, sb in enumerate(small_beams):
        if not sb.get("section"):
            warnings.append(
                f"WARNING: small_beams[{i}] at ({sb['x1']},{sb['y1']})-"
                f"({sb['x2']},{sb['y2']}) has empty section")

    patch = {
        "small_beams": small_beams,
        "sections": {
            "frame": sorted(frame_set),
        },
    }

    return patch, warnings


def main():
    parser = argparse.ArgumentParser(
        description="Extract small beams → sb_patch.json")
    parser.add_argument("--sb-elements", required=True,
                        help="Path to sb_elements_aligned.json (affine-calibrated)")
    parser.add_argument("--config", required=True,
                        help="Path to model_config.json (Phase 1 output)")
    parser.add_argument("--output", required=True,
                        help="Output path for sb_patch.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing output")
    args = parser.parse_args()

    # Load inputs
    with open(args.sb_elements, encoding="utf-8") as f:
        sb_elements = json.load(f)
    print(f"SB elements loaded: {args.sb_elements}")
    print(f"  small_beams: {len(sb_elements.get('small_beams', []))}")

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)
    print(f"Config loaded: {args.config}")

    # Build patch
    patch, build_warnings = build_sb_patch(sb_elements, config)
    for w in build_warnings:
        print(f"  {w}")

    # Validate
    story_names = {s["name"] for s in config.get("stories", [])}
    errors, val_warnings = validate_sb_patch(patch, story_names)
    for w in val_warnings:
        print(f"  WARNING: {w}")
    if errors:
        print(f"\nVALIDATION FAILED ({len(errors)} errors):")
        for e in errors:
            print(f"  ERROR: {e}")

    # Summary
    print(f"\nPatch summary:")
    print(f"  small_beams: {len(patch['small_beams'])}")
    print(f"  frame sections: {patch['sections']['frame']}")

    # Write output
    if args.dry_run:
        print("\n[DRY RUN] Output not written.")
        if errors:
            sys.exit(1)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(patch, f, ensure_ascii=False, indent=2)
        print(f"\nPatch written to: {args.output}")
        if errors:
            sys.exit(1)


if __name__ == "__main__":
    main()
