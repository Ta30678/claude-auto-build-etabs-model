"""
Affine Calibrate Tool — Transform PPTX-meter coordinates to grid-aligned coordinates.

Phase 1's pptx_to_elements.py extracts element coordinates in PPTX-meter space
(using EMU-per-meter scale from tick marks). These coordinates are NOT the same as
the structural grid system because the PPT origin, rotation, and scale differ
per slide.

This tool computes a per-slide affine transform by matching Phase 1 elements
(in PPTX-meter) to their grid-aligned counterparts (in model_config.json),
then applies the same transform to Phase 2 small beam coordinates.

Usage:
    python -m golden_scripts.tools.affine_calibrate \
        --elements elements.json \
        --config model_config.json \
        --sb-elements sb_elements.json \
        --output sb_elements_aligned.json

    # Preview without writing:
    python -m golden_scripts.tools.affine_calibrate \
        --elements elements.json \
        --config model_config.json \
        --sb-elements sb_elements.json \
        --output sb_elements_aligned.json \
        --dry-run
"""

import argparse
import json
import math
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 1. Correspondence point collection
# ---------------------------------------------------------------------------

def _direction_of(x1, y1, x2, y2):
    """Determine beam direction: 'X' (horizontal) or 'Y' (vertical)."""
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    if dx < 0.01 and dy < 0.01:
        return ""
    if dy < 0.01 or (dx > 0 and dy / max(dx, 1e-9) < 0.1):
        return "X"
    if dx < 0.01 or (dy > 0 and dx / max(dy, 1e-9) < 0.1):
        return "Y"
    return ""


def _floors_overlap(floors_a, floors_b):
    """True if two floor lists share at least one common floor."""
    return bool(set(floors_a) & set(floors_b))


def collect_correspondences(elements_page, config, element_type="beams"):
    """Find matching elements between PPTX-space and grid-space.

    For beams: match by section + direction + floor overlap.
    For columns: match by section + floor overlap (position proximity as tiebreak).

    Returns list of (pptx_x, pptx_y, grid_x, grid_y) tuples.
    """
    correspondences = []

    if element_type == "beams":
        config_beams = config.get("beams", [])
        for pptx_elem in elements_page:
            section = pptx_elem.get("section", "")
            direction = pptx_elem.get("direction", "")
            if not section and not direction:
                continue
            p_floors = pptx_elem.get("floors", [])

            best_match = None
            best_score = float("inf")

            for cfg_beam in config_beams:
                cfg_sec = cfg_beam.get("section", "")
                cfg_dir = _direction_of(cfg_beam["x1"], cfg_beam["y1"],
                                        cfg_beam["x2"], cfg_beam["y2"])

                # Must match direction
                if direction and cfg_dir and direction != cfg_dir:
                    continue

                # Section match (exact or prefix)
                if section and cfg_sec and section != cfg_sec:
                    continue

                # Floor overlap
                cfg_floors = cfg_beam.get("floors", [])
                if p_floors and cfg_floors and not _floors_overlap(p_floors, cfg_floors):
                    continue

                # Score: coordinate proximity (rough)
                dx1 = pptx_elem["x1"] - cfg_beam["x1"]
                dy1 = pptx_elem["y1"] - cfg_beam["y1"]
                dx2 = pptx_elem["x2"] - cfg_beam["x2"]
                dy2 = pptx_elem["y2"] - cfg_beam["y2"]
                score = math.hypot(dx1, dy1) + math.hypot(dx2, dy2)

                if score < best_score:
                    best_score = score
                    best_match = cfg_beam

            if best_match:
                # Add both endpoints as correspondences
                correspondences.append((
                    pptx_elem["x1"], pptx_elem["y1"],
                    best_match["x1"], best_match["y1"],
                ))
                correspondences.append((
                    pptx_elem["x2"], pptx_elem["y2"],
                    best_match["x2"], best_match["y2"],
                ))

    elif element_type == "columns":
        config_cols = config.get("columns", [])
        for pptx_elem in elements_page:
            section = pptx_elem.get("section", "")
            p_floors = pptx_elem.get("floors", [])
            px = pptx_elem.get("grid_x", pptx_elem.get("x1", 0))
            py = pptx_elem.get("grid_y", pptx_elem.get("y1", 0))

            best_match = None
            best_dist = float("inf")

            for cfg_col in config_cols:
                cfg_sec = cfg_col.get("section", "")
                cfg_floors = cfg_col.get("floors", [])

                if section and cfg_sec and section != cfg_sec:
                    continue
                if p_floors and cfg_floors and not _floors_overlap(p_floors, cfg_floors):
                    continue

                dist = math.hypot(px - cfg_col["grid_x"], py - cfg_col["grid_y"])
                if dist < best_dist:
                    best_dist = dist
                    best_match = cfg_col

            if best_match:
                correspondences.append((
                    px, py,
                    best_match["grid_x"], best_match["grid_y"],
                ))

    return correspondences


# ---------------------------------------------------------------------------
# 2. Affine parameter estimation (axis-independent: x and y separately)
# ---------------------------------------------------------------------------

def solve_affine_1d(pptx_vals, grid_vals):
    """Least-squares fit: grid = scale * pptx + offset.

    Returns (scale, offset, residuals_list).
    """
    n = len(pptx_vals)
    if n == 0:
        return 1.0, 0.0, []
    if n == 1:
        # Only one point: use it as offset with scale=1
        return 1.0, grid_vals[0] - pptx_vals[0], [0.0]

    # Solve via normal equations:
    # [sum(xi^2)  sum(xi)] [s]   [sum(xi*yi)]
    # [sum(xi)    n      ] [o] = [sum(yi)   ]
    sx = sum(pptx_vals)
    sy = sum(grid_vals)
    sxx = sum(x * x for x in pptx_vals)
    sxy = sum(x * y for x, y in zip(pptx_vals, grid_vals))

    det = sxx * n - sx * sx
    if abs(det) < 1e-12:
        # Degenerate: all pptx values are the same
        # Use mean offset with scale=1
        mean_offset = sy / n - sx / n
        return 1.0, mean_offset, [abs(g - (p + mean_offset)) for p, g in zip(pptx_vals, grid_vals)]

    scale = (sxy * n - sx * sy) / det
    offset = (sxx * sy - sx * sxy) / det

    residuals = [abs(g - (scale * p + offset)) for p, g in zip(pptx_vals, grid_vals)]
    return scale, offset, residuals


def compute_affine(correspondences):
    """Compute per-axis affine transform from correspondence points.

    Returns {
        "sx": float, "ox": float,  # x_grid = sx * x_pptx + ox
        "sy": float, "oy": float,  # y_grid = sy * y_pptx + oy
        "n_points": int,
        "max_residual": float,
        "mean_residual": float,
        "residuals_x": [...],
        "residuals_y": [...],
    }
    """
    if not correspondences:
        return None

    pptx_x = [c[0] for c in correspondences]
    pptx_y = [c[1] for c in correspondences]
    grid_x = [c[2] for c in correspondences]
    grid_y = [c[3] for c in correspondences]

    sx, ox, res_x = solve_affine_1d(pptx_x, grid_x)
    sy, oy, res_y = solve_affine_1d(pptx_y, grid_y)

    all_res = res_x + res_y
    max_res = max(all_res) if all_res else 0.0
    mean_res = sum(all_res) / len(all_res) if all_res else 0.0

    return {
        "sx": sx, "ox": ox,
        "sy": sy, "oy": oy,
        "n_points": len(correspondences),
        "max_residual": round(max_res, 4),
        "mean_residual": round(mean_res, 4),
        "residuals_x": [round(r, 4) for r in res_x],
        "residuals_y": [round(r, 4) for r in res_y],
    }


def apply_affine(x, y, transform):
    """Apply affine transform to a single point."""
    nx = transform["sx"] * x + transform["ox"]
    ny = transform["sy"] * y + transform["oy"]
    return round(nx, 2), round(ny, 2)


# ---------------------------------------------------------------------------
# 3. Per-slide processing
# ---------------------------------------------------------------------------

def group_by_page(elements_list, key="page_num"):
    """Group elements by page_num, returning {page_num: [elements]}."""
    groups = {}
    for elem in elements_list:
        pn = elem.get(key)
        if pn is not None:
            groups.setdefault(pn, []).append(elem)
    return groups


def compute_per_slide_transforms(elements_json, config):
    """Compute affine transforms for each slide.

    Args:
        elements_json: Phase 1 elements.json output (with page_num).
        config: Phase 1 model_config.json.

    Returns {slide_num: transform_dict}.
    """
    # Collect all elements with page_num
    all_elems = []
    for key in ("beams", "columns", "walls"):
        for elem in elements_json.get(key, []):
            if "page_num" in elem:
                elem_copy = dict(elem)
                elem_copy["_type"] = key
                all_elems.append(elem_copy)

    by_page = group_by_page(all_elems)
    transforms = {}

    for page_num, page_elems in sorted(by_page.items()):
        beams = [e for e in page_elems if e["_type"] == "beams"]
        columns = [e for e in page_elems if e["_type"] == "columns"]

        # Collect correspondences from beams and columns
        corr = []
        if beams:
            corr.extend(collect_correspondences(beams, config, "beams"))
        if columns:
            corr.extend(collect_correspondences(columns, config, "columns"))

        if len(corr) < 2:
            print(f"  Slide {page_num}: only {len(corr)} correspondence points, "
                  f"insufficient for affine fit")
            continue

        # Deduplicate correspondence points (same pptx coord → same grid coord)
        seen = set()
        unique_corr = []
        for c in corr:
            key = (round(c[0], 2), round(c[1], 2), round(c[2], 2), round(c[3], 2))
            if key not in seen:
                seen.add(key)
                unique_corr.append(c)

        transform = compute_affine(unique_corr)
        if transform:
            transforms[page_num] = transform
            print(f"  Slide {page_num}: {transform['n_points']} points, "
                  f"max_residual={transform['max_residual']:.4f}m, "
                  f"scale=({transform['sx']:.6f}, {transform['sy']:.6f}), "
                  f"offset=({transform['ox']:.4f}, {transform['oy']:.4f})")

    return transforms


def find_fallback_transform(transforms, page_num):
    """Find the nearest available transform for a page without its own."""
    if not transforms:
        return None
    pages = sorted(transforms.keys())
    # Find nearest page
    best_page = min(pages, key=lambda p: abs(p - page_num))
    return transforms[best_page]


# ---------------------------------------------------------------------------
# 4. Apply transforms to SB elements
# ---------------------------------------------------------------------------

def align_sb_elements(sb_elements_json, transforms):
    """Apply per-slide affine transforms to small beam coordinates.

    Args:
        sb_elements_json: Phase 2 sb_elements.json output (with page_num).
        transforms: {slide_num: transform_dict}.

    Returns (aligned_json, stats).
    """
    aligned = json.loads(json.dumps(sb_elements_json))  # deep copy
    small_beams = aligned.get("small_beams", [])

    stats = {
        "total": len(small_beams),
        "transformed": 0,
        "fallback": 0,
        "identity": 0,
        "per_slide": {},
        "warnings": [],
    }

    for sb in small_beams:
        page_num = sb.get("page_num")
        if page_num is None:
            stats["warnings"].append(
                f"SB {sb.get('section', '?')} at ({sb['x1']},{sb['y1']}) "
                f"has no page_num, using identity transform")
            stats["identity"] += 1
            continue

        transform = transforms.get(page_num)
        used_fallback = False

        if transform is None:
            transform = find_fallback_transform(transforms, page_num)
            if transform is None:
                stats["warnings"].append(
                    f"SB on slide {page_num}: no transform available, "
                    f"using identity")
                stats["identity"] += 1
                continue
            used_fallback = True
            stats["fallback"] += 1

        # Apply transform
        old_x1, old_y1 = sb["x1"], sb["y1"]
        old_x2, old_y2 = sb["x2"], sb["y2"]
        sb["x1"], sb["y1"] = apply_affine(old_x1, old_y1, transform)
        sb["x2"], sb["y2"] = apply_affine(old_x2, old_y2, transform)
        stats["transformed"] += 1

        # Track per-slide stats
        slide_key = str(page_num)
        if slide_key not in stats["per_slide"]:
            stats["per_slide"][slide_key] = {"count": 0, "fallback": used_fallback}
        stats["per_slide"][slide_key]["count"] += 1

    aligned["small_beams"] = small_beams

    # Add alignment metadata
    meta = aligned.get("_metadata", {})
    meta["affine_alignment"] = {
        "total_sbs": stats["total"],
        "transformed": stats["transformed"],
        "fallback": stats["fallback"],
        "identity": stats["identity"],
        "transforms": {
            str(k): {
                "sx": v["sx"], "ox": v["ox"],
                "sy": v["sy"], "oy": v["oy"],
                "n_points": v["n_points"],
                "max_residual": v["max_residual"],
            }
            for k, v in transforms.items()
        },
    }
    aligned["_metadata"] = meta

    return aligned, stats


# ---------------------------------------------------------------------------
# 5. CLI interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Transform PPTX-meter SB coordinates to grid-aligned coordinates")
    parser.add_argument("--elements", required=True,
                        help="Path to Phase 1 elements.json (PPTX-meter, with page_num)")
    parser.add_argument("--config", required=True,
                        help="Path to Phase 1 model_config.json (grid-aligned)")
    parser.add_argument("--sb-elements", required=True,
                        help="Path to Phase 2 sb_elements.json (PPTX-meter)")
    parser.add_argument("--output", required=True,
                        help="Path for aligned output (sb_elements_aligned.json)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show transform details without writing output")
    args = parser.parse_args()

    # Load inputs
    with open(args.elements, encoding="utf-8") as f:
        elements = json.load(f)
    print(f"Elements loaded: {args.elements}")
    print(f"  beams: {len(elements.get('beams', []))}")
    print(f"  columns: {len(elements.get('columns', []))}")

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)
    print(f"Config loaded: {args.config}")
    print(f"  beams: {len(config.get('beams', []))}")
    print(f"  columns: {len(config.get('columns', []))}")

    with open(args.sb_elements, encoding="utf-8") as f:
        sb_elements = json.load(f)
    print(f"SB elements loaded: {args.sb_elements}")
    print(f"  small_beams: {len(sb_elements.get('small_beams', []))}")

    # Check page_num availability
    has_page_num = False
    for key in ("beams", "columns", "walls"):
        for elem in elements.get(key, []):
            if "page_num" in elem:
                has_page_num = True
                break
        if has_page_num:
            break

    if not has_page_num:
        print("\nWARNING: elements.json has no page_num fields.")
        print("  Re-run pptx_to_elements.py to generate elements.json with page_num.")
        print("  Falling back to identity transform (no coordinate change).")
        if not args.dry_run:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(sb_elements, f, ensure_ascii=False, indent=2)
            print(f"Output written (unchanged): {args.output}")
        return

    # Compute per-slide transforms
    print("\n--- Computing per-slide affine transforms ---")
    transforms = compute_per_slide_transforms(elements, config)

    if not transforms:
        print("\nERROR: Could not compute any affine transforms.")
        print("  Check that elements.json and model_config.json have matching elements.")
        sys.exit(1)

    # Validate transforms
    print("\n--- Transform validation ---")
    for page_num, t in sorted(transforms.items()):
        if t["max_residual"] > 0.05:
            print(f"  WARNING: Slide {page_num} max residual {t['max_residual']:.4f}m > 0.05m")
        # Check for unreasonable scale
        if abs(t["sx"] - 1.0) > 0.5 or abs(t["sy"] - 1.0) > 0.5:
            print(f"  WARNING: Slide {page_num} unusual scale "
                  f"({t['sx']:.4f}, {t['sy']:.4f})")

    # Apply transforms to SB elements
    print("\n--- Applying transforms to SB coordinates ---")
    aligned, stats = align_sb_elements(sb_elements, transforms)

    print(f"\n--- Alignment Summary ---")
    print(f"  Total SBs: {stats['total']}")
    print(f"  Transformed: {stats['transformed']}")
    print(f"  Fallback (neighbor slide): {stats['fallback']}")
    print(f"  Identity (no transform): {stats['identity']}")

    if stats["warnings"]:
        print(f"\nWARNINGS ({len(stats['warnings'])}):")
        for w in stats["warnings"]:
            print(f"  WARNING: {w}")

    if args.dry_run:
        print(f"\n[DRY RUN] No output written.")
        # Show sample transforms
        for sb in aligned.get("small_beams", [])[:5]:
            print(f"  SB {sb.get('section', '?')}: "
                  f"({sb['x1']}, {sb['y1']}) → ({sb['x2']}, {sb['y2']})")
    else:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(aligned, f, ensure_ascii=False, indent=2)
        print(f"\nAligned SB elements written to: {args.output}")
        print(f"  small_beams: {len(aligned.get('small_beams', []))}")


if __name__ == "__main__":
    main()
