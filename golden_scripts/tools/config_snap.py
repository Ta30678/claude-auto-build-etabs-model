"""
Config Snap Tool — Snap SB endpoint coordinates to nearest structural elements.

Phase 2 SB-READER extracts small beam coordinates from hand-drawn Bluebeam PDF
annotations. These coordinates are imprecise — SB endpoints don't land precisely
on major beams, columns, or walls. This tool corrects SB endpoint coordinates by
snapping them to the nearest structural element using geometry.

Usage:
    python -m golden_scripts.tools.config_snap \
        --input merged_config.json \
        --output snapped_config.json

    # Custom tolerance (default 0.3m = 30cm):
    python -m golden_scripts.tools.config_snap \
        --input merged_config.json \
        --output snapped_config.json \
        --tolerance 0.3

    # Preview changes without writing:
    python -m golden_scripts.tools.config_snap \
        --input merged_config.json \
        --output snapped_config.json \
        --dry-run
"""
import json
import argparse
import math
import sys


# ---------------------------------------------------------------------------
# 1a. Geometric utilities
# ---------------------------------------------------------------------------

def point_to_segment_nearest(px, py, ax, ay, bx, by):
    """Nearest point on segment A->B to point P.

    Returns (nx, ny, distance).
    """
    dx, dy = bx - ax, by - ay
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-12:
        # Degenerate segment (point)
        dist = math.hypot(px - ax, py - ay)
        return ax, ay, dist
    t = ((px - ax) * dx + (py - ay) * dy) / len_sq
    t = max(0.0, min(1.0, t))
    nx = ax + t * dx
    ny = ay + t * dy
    dist = math.hypot(px - nx, py - ny)
    return nx, ny, dist


def floors_overlap(floors_a, floors_b):
    """True if two floor lists share at least one common floor."""
    return bool(set(floors_a) & set(floors_b))


def cluster_axis_values(values, threshold=0.05):
    """Group nearly-identical values, return {original: cluster_median}.

    Sort -> sweep -> any value within threshold of previous joins current cluster.
    """
    if not values:
        return {}
    sorted_vals = sorted(set(values))
    clusters = []
    current_cluster = [sorted_vals[0]]
    for v in sorted_vals[1:]:
        if v - current_cluster[-1] <= threshold:
            current_cluster.append(v)
        else:
            clusters.append(current_cluster)
            current_cluster = [v]
    clusters.append(current_cluster)

    mapping = {}
    for cluster in clusters:
        if len(cluster) == 1:
            continue  # No need to snap a lone value
        median = sorted(cluster)[len(cluster) // 2]
        for v in cluster:
            if v != median:
                mapping[v] = median
    return mapping


# ---------------------------------------------------------------------------
# 1b. Target construction
# ---------------------------------------------------------------------------

class SnapTarget:
    """A point or line segment that SB endpoints can snap to."""

    __slots__ = ("kind", "x1", "y1", "x2", "y2", "floors")

    def __init__(self, kind, x1, y1, x2, y2, floors):
        self.kind = kind      # "point" or "segment"
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2          # same as x1/y1 for points
        self.y2 = y2
        self.floors = floors

    def nearest(self, px, py):
        """Return (nx, ny, distance) — nearest point on this target to (px,py)."""
        if self.kind == "point":
            d = math.hypot(px - self.x1, py - self.y1)
            return self.x1, self.y1, d
        return point_to_segment_nearest(px, py, self.x1, self.y1, self.x2, self.y2)


def build_targets(config):
    """Build initial snap targets from beams, columns, and walls."""
    targets = []

    # Columns -> points
    for col in config.get("columns", []):
        targets.append(SnapTarget(
            "point", col["grid_x"], col["grid_y"],
            col["grid_x"], col["grid_y"], col["floors"]))

    # Beams -> segments
    for beam in config.get("beams", []):
        targets.append(SnapTarget(
            "segment", beam["x1"], beam["y1"],
            beam["x2"], beam["y2"], beam["floors"]))

    # Walls -> segments
    for wall in config.get("walls", []):
        targets.append(SnapTarget(
            "segment", wall["x1"], wall["y1"],
            wall["x2"], wall["y2"], wall["floors"]))

    return targets


def snap_point(px, py, floors, targets, tolerance):
    """Find the nearest target within tolerance that overlaps floors.

    Returns (snapped_x, snapped_y, distance) or None if nothing within tolerance.
    """
    best = None
    best_dist = tolerance + 1
    for t in targets:
        if not floors_overlap(floors, t.floors):
            continue
        nx, ny, d = t.nearest(px, py)
        if d < best_dist:
            best_dist = d
            best = (nx, ny, d)
    if best is not None and best_dist <= tolerance:
        return best
    return None


# ---------------------------------------------------------------------------
# 1c. Core snap algorithm
# ---------------------------------------------------------------------------

def snap_config(config, tolerance=0.3, axis_threshold=0.05):
    """Snap SB endpoints to nearest structural elements. Returns (snapped_config, stats).

    Phases:
      A — Axis clustering among SBs
      B — Endpoint snapping (3 rounds: major-only, major+snapped-SB, SB-to-SB)
      C — Slab coordinate update
      D — Post-snap validation
    """
    config = json.loads(json.dumps(config))  # deep copy
    small_beams = config.get("small_beams", [])
    if not small_beams:
        return config, {"total_snapped": 0, "warnings": []}

    stats = {
        "total_endpoints": len(small_beams) * 2,
        "axis_clustered": 0,
        "round1_snapped": 0,
        "round2_snapped": 0,
        "round3_snapped": 0,
        "total_snapped": 0,
        "max_distance": 0.0,
        "sum_distance": 0.0,
        "slab_coords_updated": 0,
        "warnings": [],
        "details": [],  # per-SB snap details
    }

    # Track original coords for slab mapping (before ANY modifications)
    orig_coords = [(sb["x1"], sb["y1"], sb["x2"], sb["y2"]) for sb in small_beams]

    # --- Phase A: Axis alignment + clustering ---
    # A1: Collect structural reference coordinates (columns, beam/wall endpoints)
    ref_x = set()
    ref_y = set()
    for col in config.get("columns", []):
        ref_x.add(col["grid_x"])
        ref_y.add(col["grid_y"])
    for elem in list(config.get("beams", [])) + list(config.get("walls", [])):
        ref_x.add(elem["x1"])
        ref_x.add(elem["x2"])
        ref_y.add(elem["y1"])
        ref_y.add(elem["y2"])
    sorted_ref_x = sorted(ref_x)
    sorted_ref_y = sorted(ref_y)

    def nearest_ref(val, refs):
        """Find nearest reference value. Returns (ref_val, distance)."""
        best_ref, best_d = None, float("inf")
        for r in refs:
            d = abs(val - r)
            if d < best_d:
                best_d = d
                best_ref = r
        return best_ref, best_d

    # A2: Snap SB fixed axes to nearest structural coordinate (within tolerance)
    for sb in small_beams:
        if sb["x1"] == sb["x2"]:
            # Vertical SB — snap fixed X to nearest structural X
            ref, d = nearest_ref(sb["x1"], sorted_ref_x)
            if ref is not None and d <= tolerance and d > 0:
                sb["x1"] = ref
                sb["x2"] = ref
                stats["axis_clustered"] += 1
        elif sb["y1"] == sb["y2"]:
            # Horizontal SB — snap fixed Y to nearest structural Y
            ref, d = nearest_ref(sb["y1"], sorted_ref_y)
            if ref is not None and d <= tolerance and d > 0:
                sb["y1"] = ref
                sb["y2"] = ref
                stats["axis_clustered"] += 1

    # A3: Cluster remaining SB axes among themselves (align near-identical values)
    x_vals = []
    y_vals = []
    for sb in small_beams:
        if sb["x1"] == sb["x2"]:
            x_vals.append(sb["x1"])
        elif sb["y1"] == sb["y2"]:
            y_vals.append(sb["y1"])

    x_map = cluster_axis_values(x_vals, axis_threshold)
    y_map = cluster_axis_values(y_vals, axis_threshold)

    for sb in small_beams:
        if sb["x1"] == sb["x2"] and sb["x1"] in x_map:
            new_x = x_map[sb["x1"]]
            sb["x1"] = new_x
            sb["x2"] = new_x
            stats["axis_clustered"] += 1
        elif sb["y1"] == sb["y2"] and sb["y1"] in y_map:
            new_y = y_map[sb["y1"]]
            sb["y1"] = new_y
            sb["y2"] = new_y
            stats["axis_clustered"] += 1

    # --- Phase B: Endpoint snapping ---
    major_targets = build_targets(config)
    n = len(small_beams)
    # Track snap state per endpoint: 0=unsnapped, 1=snapped
    snapped_state = [[0, 0] for _ in range(n)]

    def snap_endpoints(sb_indices, targets, round_name):
        """Try to snap endpoints of given SB indices. Returns count of newly snapped endpoints."""
        count = 0
        for i in sb_indices:
            sb = small_beams[i]
            for ep in range(2):  # 0=start, 1=end
                if snapped_state[i][ep]:
                    continue
                px = sb["x1"] if ep == 0 else sb["x2"]
                py = sb["y1"] if ep == 0 else sb["y2"]
                result = snap_point(px, py, sb["floors"], targets, tolerance)
                if result:
                    nx, ny, d = result
                    # Round to 1cm precision
                    nx = round(nx, 2)
                    ny = round(ny, 2)
                    if ep == 0:
                        sb["x1"], sb["y1"] = nx, ny
                    else:
                        sb["x2"], sb["y2"] = nx, ny
                    snapped_state[i][ep] = 1
                    count += 1
                    stats["max_distance"] = max(stats["max_distance"], d)
                    stats["sum_distance"] += d
                    stats["details"].append({
                        "sb_index": i,
                        "endpoint": "start" if ep == 0 else "end",
                        "from": (px, py),
                        "to": (nx, ny),
                        "distance": round(d, 4),
                        "round": round_name,
                    })
        return count

    all_indices = list(range(n))

    # Round 1: snap to major elements only; prioritize SBs where both endpoints are close
    stats["round1_snapped"] = snap_endpoints(all_indices, major_targets, "R1")

    # Add round-1-snapped SBs as new targets
    snapped_sb_targets = []
    for i in range(n):
        if snapped_state[i][0] and snapped_state[i][1]:
            sb = small_beams[i]
            snapped_sb_targets.append(SnapTarget(
                "segment", sb["x1"], sb["y1"], sb["x2"], sb["y2"], sb["floors"]))

    # Round 2: major + snapped SBs
    round2_targets = major_targets + snapped_sb_targets
    stats["round2_snapped"] = snap_endpoints(all_indices, round2_targets, "R2")

    # Add newly fully-snapped SBs
    for i in range(n):
        if snapped_state[i][0] and snapped_state[i][1]:
            sb = small_beams[i]
            # Check if already added
            already = any(
                t.x1 == sb["x1"] and t.y1 == sb["y1"] and
                t.x2 == sb["x2"] and t.y2 == sb["y2"]
                for t in snapped_sb_targets)
            if not already:
                snapped_sb_targets.append(SnapTarget(
                    "segment", sb["x1"], sb["y1"],
                    sb["x2"], sb["y2"], sb["floors"]))

    # Round 3: all targets (major + all snapped SBs)
    round3_targets = major_targets + snapped_sb_targets
    stats["round3_snapped"] = snap_endpoints(all_indices, round3_targets, "R3")

    stats["total_snapped"] = (
        stats["round1_snapped"] + stats["round2_snapped"] + stats["round3_snapped"])

    # Warn about unsnapped endpoints
    for i in range(n):
        sb = small_beams[i]
        for ep in range(2):
            if not snapped_state[i][ep]:
                px = sb["x1"] if ep == 0 else sb["x2"]
                py = sb["y1"] if ep == 0 else sb["y2"]
                ep_name = "start" if ep == 0 else "end"
                stats["warnings"].append(
                    f"small_beams[{i}] {ep_name} ({px}, {py}) "
                    f"not within {tolerance}m of any target")

    # --- Phase C: Slab coordinate update ---
    # Build old->new coordinate mapping from SB axis changes
    coord_map_x = {}  # old_x -> new_x
    coord_map_y = {}  # old_y -> new_y
    for i in range(n):
        ox1, oy1, ox2, oy2 = orig_coords[i]
        sb = small_beams[i]
        if ox1 != sb["x1"]:
            coord_map_x[ox1] = sb["x1"]
        if oy1 != sb["y1"]:
            coord_map_y[oy1] = sb["y1"]
        if ox2 != sb["x2"]:
            coord_map_x[ox2] = sb["x2"]
        if oy2 != sb["y2"]:
            coord_map_y[oy2] = sb["y2"]

    # Also include axis clustering maps
    for old_x, new_x in x_map.items():
        coord_map_x[old_x] = new_x
    for old_y, new_y in y_map.items():
        coord_map_y[old_y] = new_y

    COORD_MATCH_TOL = 0.01  # 1cm matching tolerance for slab corners

    for slab in config.get("slabs", []):
        for corner in slab.get("corners", []):
            cx, cy = corner[0], corner[1]
            # Try to match X coordinate
            for old_x, new_x in coord_map_x.items():
                if abs(cx - old_x) <= COORD_MATCH_TOL:
                    corner[0] = new_x
                    stats["slab_coords_updated"] += 1
                    break
            # Try to match Y coordinate
            for old_y, new_y in coord_map_y.items():
                if abs(cy - old_y) <= COORD_MATCH_TOL:
                    corner[1] = new_y
                    stats["slab_coords_updated"] += 1
                    break

    # --- Phase D: Post-snap validation ---
    # Check for zero-length SBs
    to_remove = []
    for i, sb in enumerate(small_beams):
        if sb["x1"] == sb["x2"] and sb["y1"] == sb["y2"]:
            stats["warnings"].append(
                f"small_beams[{i}] became zero-length after snap at "
                f"({sb['x1']}, {sb['y1']}), removing")
            to_remove.append(i)

    # Remove zero-length SBs (reverse order to preserve indices)
    for i in reversed(to_remove):
        small_beams.pop(i)

    # Verify direction preserved (horizontal stays horizontal, vertical stays vertical)
    for i, (sb, (ox1, oy1, ox2, oy2)) in enumerate(zip(small_beams, orig_coords)):
        was_horiz = (oy1 == oy2)
        was_vert = (ox1 == ox2)
        is_horiz = (sb["y1"] == sb["y2"])
        is_vert = (sb["x1"] == sb["x2"])
        if was_horiz and not is_horiz:
            stats["warnings"].append(
                f"small_beams[{i}] was horizontal but direction changed after snap")
        if was_vert and not is_vert:
            stats["warnings"].append(
                f"small_beams[{i}] was vertical but direction changed after snap")

    config["small_beams"] = small_beams
    return config, stats


# ---------------------------------------------------------------------------
# 1d. CLI interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Snap SB endpoint coordinates to nearest structural elements")
    parser.add_argument("--input", required=True,
                        help="Path to merged_config.json")
    parser.add_argument("--output", required=True,
                        help="Path for snapped output config")
    parser.add_argument("--tolerance", type=float, default=0.3,
                        help="Snap tolerance in meters (default: 0.3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing output")
    args = parser.parse_args()

    # Load config
    with open(args.input, encoding="utf-8") as f:
        config = json.load(f)
    print(f"Config loaded: {args.input}")
    print(f"  columns: {len(config.get('columns', []))}")
    print(f"  beams: {len(config.get('beams', []))}")
    print(f"  walls: {len(config.get('walls', []))}")
    print(f"  small_beams: {len(config.get('small_beams', []))}")
    print(f"  slabs: {len(config.get('slabs', []))}")
    print(f"  tolerance: {args.tolerance}m")

    if not config.get("small_beams"):
        print("\nNo small beams to snap. Copying input to output.")
        if not args.dry_run:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"Output written to: {args.output}")
        return

    # Run snap
    snapped, stats = snap_config(config, tolerance=args.tolerance)

    # --- 1e. Console output ---
    print(f"\n--- Snap Summary ---")
    print(f"  Total endpoints: {stats['total_endpoints']}")
    print(f"  Axis-clustered SBs: {stats['axis_clustered']}")
    print(f"  Round 1 (major elements): {stats['round1_snapped']} endpoints snapped")
    print(f"  Round 2 (+ snapped SBs): {stats['round2_snapped']} endpoints snapped")
    print(f"  Round 3 (+ all SBs): {stats['round3_snapped']} endpoints snapped")
    print(f"  Total snapped: {stats['total_snapped']} / {stats['total_endpoints']}")
    if stats["total_snapped"] > 0:
        avg_dist = stats["sum_distance"] / stats["total_snapped"]
        print(f"  Max snap distance: {stats['max_distance']:.4f}m")
        print(f"  Avg snap distance: {avg_dist:.4f}m")
    print(f"  Slab coordinates updated: {stats['slab_coords_updated']}")

    if stats["warnings"]:
        print(f"\nWARNINGS ({len(stats['warnings'])}):")
        for w in stats["warnings"]:
            print(f"  WARNING: {w}")

    if args.dry_run:
        print(f"\n[DRY RUN] No output written.")
        if stats["details"]:
            print(f"\nSnap details:")
            for d in stats["details"]:
                print(f"  SB[{d['sb_index']}] {d['endpoint']}: "
                      f"({d['from'][0]}, {d['from'][1]}) -> "
                      f"({d['to'][0]}, {d['to'][1]}) "
                      f"d={d['distance']}m [{d['round']}]")
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(snapped, f, ensure_ascii=False, indent=2)
        print(f"\nSnapped config written to: {args.output}")
        print(f"  small_beams: {len(snapped.get('small_beams', []))}")
        print(f"  slabs: {len(snapped.get('slabs', []))}")


if __name__ == "__main__":
    main()
