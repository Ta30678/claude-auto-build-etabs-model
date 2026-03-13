"""
Beam Validate Tool — Deterministic beam endpoint connectivity validator.

Phase 1 of the BTS workflow extracts major beams from structural plans via
pptx_to_elements.py. The extracted beam endpoint coordinates may not land
precisely on grid intersections, columns, walls, or other beams due to PPTX
shape imprecision. This tool validates and auto-snaps floating endpoints.

Usage:
    python -m golden_scripts.tools.beam_validate \
        --elements elements.json \
        --grid-data grid_data.json \
        --output elements_validated.json \
        --tolerance 1.5 \
        --report beam_validation_report.json

    # Preview without writing:
    python -m golden_scripts.tools.beam_validate \
        --elements elements.json \
        --grid-data grid_data.json \
        --output elements_validated.json \
        --dry-run
"""
import json
import argparse
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from golden_scripts.tools.config_snap import (
    point_to_segment_nearest,
    SnapTarget,
    floors_overlap,
)


# ---------------------------------------------------------------------------
# 1. Target construction
# ---------------------------------------------------------------------------

def build_beam_targets(elements, grid_data):
    """Build snap targets from grid intersections, columns, and walls.

    Returns (grid_targets, element_targets) as separate lists so beam targets
    can be added incrementally during the multi-round snapping process.

    Parameters
    ----------
    elements : dict
        Parsed elements.json with "columns", "walls", "beams" keys.
    grid_data : dict
        Grid data with "x" and "y" lists of {"label": str, "coordinate": float}.

    Returns
    -------
    tuple[list[SnapTarget], list[SnapTarget]]
        (grid_targets, element_targets)
    """
    grid_targets = []
    element_targets = []

    # Grid intersections: all x * y combinations
    x_grids = grid_data.get("x", [])
    y_grids = grid_data.get("y", [])
    for xg in x_grids:
        for yg in y_grids:
            x_coord = xg["coordinate"]
            y_coord = yg["coordinate"]
            label = f"{xg['label']}/{yg['label']}"
            # floors=[] means skip floor overlap check (applies to all floors)
            grid_targets.append(SnapTarget(
                "point", x_coord, y_coord, x_coord, y_coord, floors=[]))

    # Columns -> point targets
    for col in elements.get("columns", []):
        element_targets.append(SnapTarget(
            "point",
            col["grid_x"], col["grid_y"],
            col["grid_x"], col["grid_y"],
            col.get("floors", [])))

    # Walls -> segment targets
    for wall in elements.get("walls", []):
        element_targets.append(SnapTarget(
            "segment",
            wall["x1"], wall["y1"],
            wall["x2"], wall["y2"],
            wall.get("floors", [])))

    return grid_targets, element_targets


def _grid_label_at(x, y, grid_data):
    """Find the grid intersection label for coordinates (x, y).

    Returns "X_label/Y_label" if both match a grid line, else None.
    """
    x_label = None
    y_label = None
    for xg in grid_data.get("x", []):
        if abs(xg["coordinate"] - x) < 0.005:
            x_label = xg["label"]
            break
    for yg in grid_data.get("y", []):
        if abs(yg["coordinate"] - y) < 0.005:
            y_label = yg["label"]
            break
    if x_label and y_label:
        return f"{x_label}/{y_label}"
    return None


# ---------------------------------------------------------------------------
# 2. Single-point snapping
# ---------------------------------------------------------------------------

def snap_beam_point(px, py, floors, targets, tolerance, grid_data=None):
    """Find nearest target within tolerance for a beam endpoint.

    For grid intersection targets (floors=[]), floor overlap check is skipped.
    For element targets, floors must overlap.

    Parameters
    ----------
    px, py : float
        Beam endpoint coordinates.
    floors : list[str]
        Floors the beam exists on.
    targets : list[SnapTarget]
        Available snap targets.
    tolerance : float
        Maximum snap distance in meters.
    grid_data : dict or None
        Grid data for generating target labels (optional).

    Returns
    -------
    tuple or None
        (snapped_x, snapped_y, distance, target_info_str) or None if no
        target within tolerance.
    """
    best_nx, best_ny, best_dist = None, None, tolerance + 1
    best_target = None

    for t in targets:
        # Skip floor overlap check for grid intersections (floors=[])
        if t.floors:
            if not floors_overlap(floors, t.floors):
                continue

        nx, ny, d = t.nearest(px, py)
        if d < best_dist:
            best_dist = d
            best_nx = round(nx, 2)
            best_ny = round(ny, 2)
            best_target = t

    if best_target is None or best_dist > tolerance:
        return None

    # Build target_info_str
    target_info = _build_target_info(best_target, best_nx, best_ny, grid_data)

    return best_nx, best_ny, best_dist, target_info


def _build_target_info(target, nx, ny, grid_data):
    """Build a human-readable target info string."""
    if target.kind == "point" and not target.floors:
        # Grid intersection
        label = None
        if grid_data:
            label = _grid_label_at(target.x1, target.y1, grid_data)
        if label:
            return f"grid_intersection {label}"
        return f"grid_intersection at ({target.x1}, {target.y1})"

    if target.kind == "point" and target.floors:
        return f"column at ({target.x1}, {target.y1})"

    if target.kind == "segment" and target.floors:
        # Could be wall or beam — check by whether the target was added
        # as wall or beam. Since we can't distinguish after creation,
        # use a generic label based on what's stored.
        return f"segment at ({target.x1},{target.y1})-({target.x2},{target.y2})"

    return f"target at ({nx}, {ny})"


def _find_nearest_any(px, py, targets):
    """Find nearest target regardless of floor overlap. For warning messages."""
    best_nx, best_ny, best_dist = None, None, float("inf")
    best_target = None
    for t in targets:
        nx, ny, d = t.nearest(px, py)
        if d < best_dist:
            best_dist = d
            best_nx = round(nx, 2)
            best_ny = round(ny, 2)
            best_target = t
    if best_target is None:
        return None, None, float("inf"), "none"
    info = _build_target_info(best_target, best_nx, best_ny, None)
    return best_nx, best_ny, best_dist, info


# ---------------------------------------------------------------------------
# 3. Main validation
# ---------------------------------------------------------------------------

def validate_beams(elements, grid_data, tolerance=1.5):
    """Validate and auto-snap major beam endpoints.

    Uses a 3-round snapping strategy:
      Round 1: Snap to grid intersections + columns + walls only.
      Round 2: Add fully-snapped beams as segment targets, snap remaining.
      Round 3: Add newly fully-snapped beams, final pass.

    Parameters
    ----------
    elements : dict
        Parsed elements.json with "columns", "walls", "beams" keys.
    grid_data : dict
        Grid data with "x" and "y" lists.
    tolerance : float
        Maximum snap distance in meters (default 1.5).

    Returns
    -------
    tuple[dict, dict]
        (validated_elements, report_dict)
    """
    # Deep copy to avoid mutating the original
    elements = json.loads(json.dumps(elements))

    beams = elements.get("beams", [])
    n = len(beams)

    corrections = []
    warnings = []

    if n == 0:
        report = {
            "total_beams": 0,
            "total_endpoints": 0,
            "snapped_endpoints": 0,
            "warning_endpoints": 0,
            "max_snap_distance": 0,
            "avg_snap_distance": 0,
            "corrections": [],
            "warnings": [],
        }
        return elements, report

    # Build targets
    grid_targets, element_targets = build_beam_targets(elements, grid_data)
    base_targets = grid_targets + element_targets

    # Track snap state per endpoint: False = unsnapped
    snapped_state = [[False, False] for _ in range(n)]

    # Beam segment targets (added after each round)
    beam_snap_targets = []

    # --- Helper: snap one round ---
    def _snap_round(targets):
        """Try to snap all unsnapped endpoints. Returns count of newly snapped."""
        count = 0
        for i in range(n):
            beam = beams[i]
            floors = beam.get("floors", [])
            for ep in range(2):  # 0=start, 1=end
                if snapped_state[i][ep]:
                    continue
                if ep == 0:
                    px, py = beam["x1"], beam["y1"]
                else:
                    px, py = beam["x2"], beam["y2"]

                result = snap_beam_point(px, py, floors, targets, tolerance, grid_data)
                if result:
                    nx, ny, d, target_info = result

                    # Determine target_type from target_info
                    if target_info.startswith("grid_intersection"):
                        target_type = "grid_intersection"
                    elif target_info.startswith("column"):
                        target_type = "column"
                    elif target_info.startswith("wall"):
                        target_type = "wall"
                    elif target_info.startswith("beam"):
                        target_type = "beam"
                    else:
                        target_type = "segment"

                    corrections.append({
                        "beam_index": i,
                        "original_x1": beam["x1"],
                        "original_y1": beam["y1"],
                        "original_x2": beam["x2"],
                        "original_y2": beam["y2"],
                        "section": beam.get("section", ""),
                        "floors": beam.get("floors", []),
                        "endpoint": "start" if ep == 0 else "end",
                        "original_coord": [px, py],
                        "corrected_coord": [nx, ny],
                        "snap_distance": round(d, 4),
                        "target_type": target_type,
                        "target_label": target_info,
                    })

                    # Update beam coordinates
                    if ep == 0:
                        beam["x1"], beam["y1"] = nx, ny
                    else:
                        beam["x2"], beam["y2"] = nx, ny
                    snapped_state[i][ep] = True
                    count += 1
        return count

    def _add_fully_snapped_beams():
        """Add beams with both endpoints snapped as segment targets."""
        added = 0
        for i in range(n):
            if snapped_state[i][0] and snapped_state[i][1]:
                b = beams[i]
                # Check if already added
                already = any(
                    t.x1 == b["x1"] and t.y1 == b["y1"] and
                    t.x2 == b["x2"] and t.y2 == b["y2"]
                    for t in beam_snap_targets)
                if not already:
                    beam_snap_targets.append(SnapTarget(
                        "segment",
                        b["x1"], b["y1"],
                        b["x2"], b["y2"],
                        b.get("floors", [])))
                    added += 1
        return added

    # Round 1: grid + columns + walls (NO beam targets)
    _snap_round(base_targets)

    # After round 1: add fully-snapped beams
    _add_fully_snapped_beams()

    # Round 2: base targets + snapped beam targets
    _snap_round(base_targets + beam_snap_targets)

    # After round 2: add newly fully-snapped beams
    _add_fully_snapped_beams()

    # Round 3: final pass with all targets
    _snap_round(base_targets + beam_snap_targets)

    # --- Collect warnings for unsnapped endpoints ---
    all_targets = base_targets + beam_snap_targets
    for i in range(n):
        beam = beams[i]
        for ep in range(2):
            if snapped_state[i][ep]:
                continue
            if ep == 0:
                px, py = beam["x1"], beam["y1"]
            else:
                px, py = beam["x2"], beam["y2"]

            # Find nearest target for the warning message
            _, _, nearest_dist, nearest_info = _find_nearest_any(px, py, all_targets)

            warnings.append({
                "beam_index": i,
                "original_x1": beam["x1"],
                "original_y1": beam["y1"],
                "original_x2": beam["x2"],
                "original_y2": beam["y2"],
                "section": beam.get("section", ""),
                "floors": beam.get("floors", []),
                "endpoint": "start" if ep == 0 else "end",
                "coord": [px, py],
                "nearest_target": nearest_info,
                "nearest_distance": round(nearest_dist, 4),
                "message": f"No target within {tolerance}m tolerance",
            })

    # --- Check for zero-length beams after snap ---
    for i in range(n):
        b = beams[i]
        if abs(b["x1"] - b["x2"]) < 0.005 and abs(b["y1"] - b["y2"]) < 0.005:
            warnings.append({
                "beam_index": i,
                "original_x1": b["x1"],
                "original_y1": b["y1"],
                "original_x2": b["x2"],
                "original_y2": b["y2"],
                "section": b.get("section", ""),
                "floors": b.get("floors", []),
                "endpoint": "both",
                "coord": [b["x1"], b["y1"]],
                "nearest_target": "self",
                "nearest_distance": 0,
                "message": "Zero-length beam after snap — both endpoints at same location",
            })

    # --- Build report ---
    snap_distances = [c["snap_distance"] for c in corrections]
    report = {
        "total_beams": n,
        "total_endpoints": n * 2,
        "snapped_endpoints": len(corrections),
        "warning_endpoints": len(warnings),
        "max_snap_distance": max(snap_distances) if snap_distances else 0,
        "avg_snap_distance": round(sum(snap_distances) / len(snap_distances), 4) if snap_distances else 0,
        "corrections": corrections,
        "warnings": warnings,
    }

    return elements, report


# ---------------------------------------------------------------------------
# 4. CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Validate and auto-snap major beam endpoints to structural targets")
    parser.add_argument("--elements", required=True,
                        help="Path to elements.json (Phase 1 extraction output)")
    parser.add_argument("--grid-data", required=True,
                        help="Path to grid_data.json (ETABS grid read output)")
    parser.add_argument("--output", required=True,
                        help="Path for validated elements output")
    parser.add_argument("--tolerance", type=float, default=1.5,
                        help="Snap tolerance in meters (default: 1.5)")
    parser.add_argument("--report", default=None,
                        help="Path for validation report JSON (optional)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing output")
    args = parser.parse_args()

    # Load inputs
    with open(args.elements, encoding="utf-8") as f:
        elements = json.load(f)
    with open(args.grid_data, encoding="utf-8") as f:
        grid_data = json.load(f)

    n_beams = len(elements.get("beams", []))
    n_cols = len(elements.get("columns", []))
    n_walls = len(elements.get("walls", []))
    x_grids = len(grid_data.get("x", []))
    y_grids = len(grid_data.get("y", []))

    print(f"Elements loaded: {args.elements}")
    print(f"  beams: {n_beams}, columns: {n_cols}, walls: {n_walls}")
    print(f"Grid data loaded: {args.grid_data}")
    print(f"  x-grids: {x_grids}, y-grids: {y_grids}")
    print(f"  grid intersections: {x_grids * y_grids}")
    print(f"  tolerance: {args.tolerance}m")

    if n_beams == 0:
        print("\nNo beams to validate.")
        if not args.dry_run:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(elements, f, ensure_ascii=False, indent=2)
            print(f"Output written to: {args.output}")
        return

    # Run validation
    validated, report = validate_beams(elements, grid_data, tolerance=args.tolerance)

    # Print summary
    print(f"\n--- Beam Validation Summary ---")
    print(f"  Total beams: {report['total_beams']}")
    print(f"  Total endpoints: {report['total_endpoints']}")
    print(f"  Snapped endpoints: {report['snapped_endpoints']}")
    print(f"  Warning endpoints: {report['warning_endpoints']}")
    if report["snapped_endpoints"] > 0:
        print(f"  Max snap distance: {report['max_snap_distance']:.4f}m")
        print(f"  Avg snap distance: {report['avg_snap_distance']:.4f}m")

    if report["warnings"]:
        print(f"\nWARNINGS ({len(report['warnings'])}):")
        for w in report["warnings"]:
            ep_label = w["endpoint"]
            print(f"  beam[{w['beam_index']}] {w.get('section', '')} {ep_label}: "
                  f"{w['message']} "
                  f"(coord={w['coord']}, nearest={w['nearest_target']}, "
                  f"d={w['nearest_distance']}m)")

    if args.dry_run:
        print(f"\n[DRY RUN] No output written.")
        if report["corrections"]:
            print(f"\nCorrections preview ({len(report['corrections'])}):")
            for c in report["corrections"]:
                print(f"  beam[{c['beam_index']}] {c['section']} {c['endpoint']}: "
                      f"({c['original_coord'][0]}, {c['original_coord'][1]}) -> "
                      f"({c['corrected_coord'][0]}, {c['corrected_coord'][1]}) "
                      f"d={c['snap_distance']}m [{c['target_label']}]")
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(validated, f, ensure_ascii=False, indent=2)
        print(f"\nValidated elements written to: {args.output}")

        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"Validation report written to: {args.report}")


if __name__ == "__main__":
    main()
