"""
Beam Validate Tool — Deterministic beam endpoint connectivity validator.

Phase 1 of the BTS workflow extracts major beams from structural plans via
pptx_to_elements.py. The extracted beam endpoint coordinates may not land
precisely on grid intersections, columns, walls, or other beams due to PPTX
shape imprecision. This tool validates and auto-snaps floating endpoints,
splits beams/walls at intermediate supports (columns, walls, other beams),
and corrects near-orthogonal angle deviations.

Pipeline order:
  Step 0: Angle correction (2° default, runs FIRST for accurate ray direction)
  Step 1: 3-round ray snap with post-round clustering
  Step 2: Split beams at columns + walls + other beams
  Step 3: Split walls at columns + beams + other walls
  Step 4: Wall-to-beam re-snap (1.0m default, aligns walls under parallel beams)

Usage:
    python -m golden_scripts.tools.beam_validate \
        --elements elements.json \
        --grid-data grid_data.json \
        --output elements_validated.json \
        --tolerance 1.5 \
        --report beam_validation_report.json

    # With angle correction + splitting (default):
    python -m golden_scripts.tools.beam_validate \
        --elements elements.json \
        --grid-data grid_data.json \
        --output elements_validated.json \
        --angle-threshold 2.0 \
        --split-tolerance 0.15

    # Disable angle correction or splitting:
    python -m golden_scripts.tools.beam_validate \
        --elements elements.json \
        --grid-data grid_data.json \
        --output elements_validated.json \
        --no-angle-correct --no-split

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
    segment_intersection as _segment_intersection,
    _grid_label_at as __grid_label_at,
    snap_by_ray,
    ray_ray_intersection,
    cluster_free_endpoints,
)
from golden_scripts.tools.geometry import point_in_or_near_polygon, is_non_rectangular


# ---------------------------------------------------------------------------
# 1. Target construction
# ---------------------------------------------------------------------------

def _normalize_grid_data_for_bv(raw):
    """Accept any grid_data format, return {x: [{label, coordinate}], y: [...]}.

    Supported input formats:
      1. {grids: {x: [{label, coordinate}], y: [...]}}      — read_grid.py output (canonical)
      2. {x_grids: [{name, coordinate}], y_grids: [...]}     — affine_calibrate format
      3. {x: [{label, coordinate}], y: [...]}                — already flat (pass-through)
    """
    # Format 1: nested under "grids"
    if "grids" in raw:
        inner = raw["grids"]
        return {"x": inner.get("x", []), "y": inner.get("y", [])}
    # Format 2: affine format with "name" field
    if "x_grids" in raw:
        return {
            "x": [{"label": g["name"], "coordinate": g["coordinate"]} for g in raw["x_grids"]],
            "y": [{"label": g["name"], "coordinate": g["coordinate"]} for g in raw.get("y_grids", [])],
        }
    # Format 3: already {x: [{label}]} — pass through
    return raw


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
        cx = col.get("grid_x", col.get("x1", 0))
        cy = col.get("grid_y", col.get("y1", 0))
        element_targets.append(SnapTarget(
            "point", cx, cy, cx, cy,
            col.get("floors", [])))

    # Walls -> segment targets
    for wall in elements.get("walls", []):
        element_targets.append(SnapTarget(
            "segment",
            wall["x1"], wall["y1"],
            wall["x2"], wall["y2"],
            wall.get("floors", [])))

    return grid_targets, element_targets


# Re-export from config_snap for backward compatibility
_grid_label_at = __grid_label_at


# ---------------------------------------------------------------------------
# 2. Angle correction
# ---------------------------------------------------------------------------

def _find_nearest_grid_value(coord, grid_lines):
    """Find nearest grid line coordinate.

    Parameters
    ----------
    coord : float
        Coordinate to match.
    grid_lines : list[dict]
        [{"label": "A", "coordinate": 0.0}, ...]

    Returns
    -------
    tuple
        (grid_coordinate, distance, grid_label) or (None, float('inf'), None).
    """
    if not grid_lines:
        return None, float("inf"), None
    best_coord = None
    best_dist = float("inf")
    best_label = None
    for g in grid_lines:
        d = abs(g["coordinate"] - coord)
        if d < best_dist:
            best_dist = d
            best_coord = g["coordinate"]
            best_label = g["label"]
    return best_coord, best_dist, best_label


def correct_angles(elements, grid_data, angle_threshold_deg=2.0,
                   outline=None, outline_tolerance=0.5):
    """Auto-correct near-orthogonal angle deviations for beams and walls.

    For each beam/wall with endpoints (x1,y1)→(x2,y2):
    - If nearly horizontal (angle ≤ threshold): align Y coordinates to nearest
      Y grid line, or fallback to average.
    - If nearly vertical (|angle - 90°| ≤ threshold): align X coordinates to
      nearest X grid line, or fallback to average.
    - Otherwise: leave unchanged (true diagonal).

    If outline is provided and non-rectangular, the fallback average path checks
    whether the resulting midpoint is inside the outline. If outside, it tries
    each grid line sorted by distance and picks the first one where the midpoint
    is inside. If no valid candidate, the original coordinates are kept.

    Parameters
    ----------
    elements : dict
        Elements with "beams" and "walls" lists.
    grid_data : dict
        Grid data with "x" and "y" lists.
    angle_threshold_deg : float
        Maximum angle deviation from horizontal/vertical to correct (default 2.0).
    outline : list or None
        Building outline polygon [[x,y],...].
    outline_tolerance : float
        Tolerance for outline proximity check (default 0.5m).

    Returns
    -------
    tuple[dict, list[dict]]
        (corrected_elements, angle_report_list)
    """
    threshold_rad = math.radians(angle_threshold_deg)
    x_grids = grid_data.get("x", [])
    y_grids = grid_data.get("y", [])
    # Max distance to accept a grid line (beyond this, use average)
    grid_max_dist = 2.0

    use_outline = outline and is_non_rectangular(outline)

    angle_report = []

    def _outline_aware_fallback_y(item, avg_y):
        """Pick a Y target that keeps the beam midpoint inside the outline."""
        mid_x = (item["x1"] + item["x2"]) / 2.0
        if not use_outline:
            return round(avg_y, 2), "average"
        # Check if average is inside
        if point_in_or_near_polygon(mid_x, avg_y, outline, outline_tolerance):
            return round(avg_y, 2), "average"
        # Try each Y grid sorted by distance
        for g in sorted(y_grids, key=lambda g: abs(g["coordinate"] - avg_y)):
            yc = g["coordinate"]
            if point_in_or_near_polygon(mid_x, yc, outline, outline_tolerance):
                return round(yc, 2), g["label"] + " (outline_rescue)"
        # No valid candidate — keep original
        return None, "outline_rescue_skipped"

    def _outline_aware_fallback_x(item, avg_x):
        """Pick an X target that keeps the beam midpoint inside the outline."""
        mid_y = (item["y1"] + item["y2"]) / 2.0
        if not use_outline:
            return round(avg_x, 2), "average"
        if point_in_or_near_polygon(avg_x, mid_y, outline, outline_tolerance):
            return round(avg_x, 2), "average"
        for g in sorted(x_grids, key=lambda g: abs(g["coordinate"] - avg_x)):
            xc = g["coordinate"]
            if point_in_or_near_polygon(xc, mid_y, outline, outline_tolerance):
                return round(xc, 2), g["label"] + " (outline_rescue)"
        return None, "outline_rescue_skipped"

    for element_type in ("beams", "walls"):
        items = elements.get(element_type, [])
        for idx, item in enumerate(items):
            direction = item.get("direction", "").upper()
            if direction in ("X", "Y"):
                continue  # PPT extraction confident — skip angle correction
            x1, y1 = item["x1"], item["y1"]
            x2, y2 = item["x2"], item["y2"]
            dx = x2 - x1
            dy = y2 - y1
            length = math.hypot(dx, dy)
            if length < 0.01:
                continue  # skip zero-length

            angle = math.atan2(abs(dy), abs(dx))  # 0=horizontal, pi/2=vertical

            corrected = False
            correction_axis = None
            target_label = None
            original = [x1, y1, x2, y2]

            if angle <= threshold_rad:
                # Near horizontal → align Y
                correction_axis = "Y"
                g1_coord, g1_dist, g1_label = _find_nearest_grid_value(y1, y_grids)
                g2_coord, g2_dist, g2_label = _find_nearest_grid_value(y2, y_grids)

                if g1_dist <= g2_dist and g1_dist <= grid_max_dist:
                    y_target = g1_coord
                    target_label = g1_label
                elif g2_dist <= grid_max_dist:
                    y_target = g2_coord
                    target_label = g2_label
                else:
                    avg_y = (y1 + y2) / 2.0
                    y_target, target_label = _outline_aware_fallback_y(item, avg_y)
                    if y_target is None:
                        continue  # skip — no valid correction

                item["y1"] = round(y_target, 2)
                item["y2"] = round(y_target, 2)
                corrected = True

            elif abs(angle - math.pi / 2) <= threshold_rad:
                # Near vertical → align X
                correction_axis = "X"
                g1_coord, g1_dist, g1_label = _find_nearest_grid_value(x1, x_grids)
                g2_coord, g2_dist, g2_label = _find_nearest_grid_value(x2, x_grids)

                if g1_dist <= g2_dist and g1_dist <= grid_max_dist:
                    x_target = g1_coord
                    target_label = g1_label
                elif g2_dist <= grid_max_dist:
                    x_target = g2_coord
                    target_label = g2_label
                else:
                    avg_x = (x1 + x2) / 2.0
                    x_target, target_label = _outline_aware_fallback_x(item, avg_x)
                    if x_target is None:
                        continue  # skip — no valid correction

                item["x1"] = round(x_target, 2)
                item["x2"] = round(x_target, 2)
                corrected = True

            if corrected:
                displacement = max(
                    math.hypot(item["x1"] - original[0], item["y1"] - original[1]),
                    math.hypot(item["x2"] - original[2], item["y2"] - original[3]),
                )
                angle_report.append({
                    "element_type": element_type.rstrip("s"),  # "beam" or "wall"
                    "index": idx,
                    "section": item.get("section", ""),
                    "original": original,
                    "corrected": [item["x1"], item["y1"], item["x2"], item["y2"]],
                    "angle_deg": round(math.degrees(angle), 2),
                    "correction_axis": correction_axis,
                    "target_grid_label": target_label,
                    "displacement": round(displacement, 4),
                })

    return elements, angle_report


# ---------------------------------------------------------------------------
# 3. Beam splitting
# ---------------------------------------------------------------------------

# Re-export from config_snap for backward compatibility
segment_intersection = _segment_intersection


def find_intermediate_supports(beam, columns, walls, split_tolerance=0.15,
                               segments=None):
    """Find intermediate support points (columns/walls/segments) along a beam.

    Parameters
    ----------
    beam : dict
        Beam with x1,y1,x2,y2,floors.
    columns : list[dict]
        Column list with grid_x, grid_y, floors.
    walls : list[dict]
        Wall list with x1,y1,x2,y2,floors.
    split_tolerance : float
        Max perpendicular distance for column projection (default 0.15m).
    segments : list[dict] or None
        Additional segment targets (other beams or walls) with
        x1,y1,x2,y2,floors. Processed with the same logic as walls
        (intersection + parallelism check + floor overlap).

    Returns
    -------
    list[tuple]
        [(t, x, y, source_label)] sorted by t, where t is parameter [0,1].
    """
    bx1, by1 = beam["x1"], beam["y1"]
    bx2, by2 = beam["x2"], beam["y2"]
    b_floors = beam.get("floors", [])
    bdx = bx2 - bx1
    bdy = by2 - by1
    b_len_sq = bdx * bdx + bdy * bdy
    if b_len_sq < 1e-12:
        return []
    b_len = math.sqrt(b_len_sq)

    supports = []

    # Check columns
    for col in columns:
        if not floors_overlap(b_floors, col.get("floors", [])):
            continue
        cx = col.get("grid_x", col.get("x1", 0))
        cy = col.get("grid_y", col.get("y1", 0))
        # Project column onto beam line
        t = ((cx - bx1) * bdx + (cy - by1) * bdy) / b_len_sq
        if t <= 0.02 or t >= 0.98:
            continue  # at or beyond endpoints
        # Perpendicular distance
        proj_x = bx1 + t * bdx
        proj_y = by1 + t * bdy
        d = math.hypot(cx - proj_x, cy - proj_y)
        if d <= split_tolerance:
            supports.append((t, round(proj_x, 2), round(proj_y, 2),
                             f"column at ({cx},{cy})"))

    # Helper: check segment-type targets (walls or other beams/walls)
    def _check_segments(seg_list, label_prefix):
        for seg in seg_list:
            if not floors_overlap(b_floors, seg.get("floors", [])):
                continue
            sx1, sy1 = seg["x1"], seg["y1"]
            sx2, sy2 = seg["x2"], seg["y2"]
            # Check parallelism: skip segments parallel to beam
            sdx = sx2 - sx1
            sdy = sy2 - sy1
            s_len = math.hypot(sdx, sdy)
            if s_len < 1e-6:
                continue
            dot = abs((bdx * sdx + bdy * sdy) / (b_len * s_len))
            if dot > 0.95:
                continue  # parallel, skip

            result = segment_intersection(bx1, by1, bx2, by2,
                                          sx1, sy1, sx2, sy2)
            if result is None:
                continue
            x, y, t_beam, t_seg = result
            if t_beam <= 0.02 or t_beam >= 0.98:
                continue  # at or beyond endpoints
            supports.append((t_beam, round(x, 2), round(y, 2),
                             f"{label_prefix} ({sx1},{sy1})-({sx2},{sy2})"))

    # Check walls
    _check_segments(walls, "wall")

    # Check additional segments (other beams, other walls, etc.)
    if segments:
        _check_segments(segments, "segment")

    # Helper: check segment endpoints as point projections (like columns)
    def _check_endpoints(seg_list, label_prefix):
        for seg in seg_list:
            if not floors_overlap(b_floors, seg.get("floors", [])):
                continue
            for ep_x, ep_y in [(seg["x1"], seg["y1"]),
                               (seg["x2"], seg["y2"])]:
                t = ((ep_x - bx1) * bdx + (ep_y - by1) * bdy) / b_len_sq
                if t <= 0.02 or t >= 0.98:
                    continue
                proj_x = bx1 + t * bdx
                proj_y = by1 + t * bdy
                d = math.hypot(ep_x - proj_x, ep_y - proj_y)
                if d <= split_tolerance:
                    supports.append((t, round(proj_x, 2), round(proj_y, 2),
                                     f"{label_prefix}-ep ({ep_x},{ep_y})"))

    # Check wall endpoints
    _check_endpoints(walls, "wall")

    # Check segment endpoints (beams when called from split_all_walls)
    if segments:
        _check_endpoints(segments, "seg")

    # Sort by t, deduplicate close points (delta_t < 0.02)
    supports.sort(key=lambda s: s[0])
    deduped = []
    for s in supports:
        if deduped and abs(s[0] - deduped[-1][0]) < 0.02:
            continue
        deduped.append(s)

    return deduped


def split_beam(beam, support_points):
    """Split a beam at support points into N+1 sub-beams.

    Each sub-beam inherits section, floors, and all extra fields.

    Parameters
    ----------
    beam : dict
        Original beam dict.
    support_points : list[tuple]
        [(t, x, y, label)] from find_intermediate_supports.

    Returns
    -------
    list[dict]
        List of sub-beam dicts.
    """
    if not support_points:
        return [beam]

    # Collect all split coordinates in order
    points = [(beam["x1"], beam["y1"])]
    for _, x, y, _ in support_points:
        points.append((x, y))
    points.append((beam["x2"], beam["y2"]))

    # Build sub-beams
    sub_beams = []
    # Collect extra fields to inherit
    skip_keys = {"x1", "y1", "x2", "y2"}
    extra = {k: v for k, v in beam.items() if k not in skip_keys}

    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        # Skip very short sub-beams (< 0.3m)
        if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) < 0.3:
            continue
        sub = dict(extra)
        sub["x1"] = p1[0]
        sub["y1"] = p1[1]
        sub["x2"] = p2[0]
        sub["y2"] = p2[1]
        sub_beams.append(sub)

    return sub_beams if sub_beams else [beam]


def split_all_beams(elements, grid_data, split_tolerance=0.15):
    """Split all beams at intermediate column/wall/beam supports.

    Each beam is split at:
    - Columns within split_tolerance perpendicular distance
    - Walls crossing the beam (non-parallel, with floor overlap)
    - Other beams crossing the beam (non-parallel, with floor overlap)

    Parameters
    ----------
    elements : dict
        Elements with "beams", "columns", "walls".
    grid_data : dict
        Grid data (unused directly, reserved for future).
    split_tolerance : float
        Max perpendicular distance for column projection.

    Returns
    -------
    tuple[dict, dict]
        (elements_with_split_beams, split_report)
    """
    beams = elements.get("beams", [])
    columns = elements.get("columns", [])
    walls = elements.get("walls", [])

    new_beams = []
    split_details = []
    split_count = 0
    new_from_split = 0

    for i, beam in enumerate(beams):
        # Other beams as additional segment targets (exclude self)
        other_beams = beams[:i] + beams[i + 1:]
        supports = find_intermediate_supports(
            beam, columns, walls, segments=other_beams,
            split_tolerance=split_tolerance)
        if supports:
            sub_beams = split_beam(beam, supports)
            new_beams.extend(sub_beams)
            split_count += 1
            new_from_split += len(sub_beams) - 1
            split_details.append({
                "original_index": i,
                "section": beam.get("section", ""),
                "original_coords": [beam["x1"], beam["y1"], beam["x2"], beam["y2"]],
                "split_points": [(s[1], s[2], s[3]) for s in supports],
                "result_count": len(sub_beams),
            })
        else:
            new_beams.append(beam)

    elements["beams"] = new_beams

    split_report = {
        "split_beams": split_count,
        "new_beams_from_split": new_from_split,
        "total_beams_after_split": len(new_beams),
        "split_details": split_details,
    }

    return elements, split_report


def split_all_walls(elements, grid_data, split_tolerance=0.15):
    """Split all walls at intermediate column/beam/wall supports.

    Each wall is split at:
    - Columns within split_tolerance perpendicular distance
    - Beams crossing the wall (non-parallel, with floor overlap)
    - Other walls crossing the wall (non-parallel, with floor overlap)

    Parameters
    ----------
    elements : dict
        Elements with "beams", "columns", "walls".
    grid_data : dict
        Grid data (unused directly, reserved for future).
    split_tolerance : float
        Max perpendicular distance for column projection.

    Returns
    -------
    tuple[dict, dict]
        (elements_with_split_walls, wall_split_report)
    """
    walls = elements.get("walls", [])
    columns = elements.get("columns", [])
    beams = elements.get("beams", [])

    new_walls = []
    split_details = []
    split_count = 0
    new_from_split = 0

    for i, wall in enumerate(walls):
        # Other walls as additional segment targets (exclude self)
        other_walls = walls[:i] + walls[i + 1:]
        # Beams are segment targets for wall splitting
        supports = find_intermediate_supports(
            wall, columns, other_walls, segments=beams,
            split_tolerance=split_tolerance)
        if supports:
            sub_walls = split_beam(wall, supports)  # split_beam is generic
            new_walls.extend(sub_walls)
            split_count += 1
            new_from_split += len(sub_walls) - 1
            split_details.append({
                "original_index": i,
                "section": wall.get("section", ""),
                "original_coords": [wall["x1"], wall["y1"], wall["x2"], wall["y2"]],
                "split_points": [(s[1], s[2], s[3]) for s in supports],
                "result_count": len(sub_walls),
            })
        else:
            new_walls.append(wall)

    elements["walls"] = new_walls

    wall_split_report = {
        "wall_split_walls": split_count,
        "wall_new_from_split": new_from_split,
        "wall_total_after_split": len(new_walls),
        "wall_split_details": split_details,
    }

    return elements, wall_split_report


# snap_beam_point removed — replaced by ray-based snap (snap_by_ray)


# ---------------------------------------------------------------------------
# 5. Snap helpers
# ---------------------------------------------------------------------------

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
    t = best_target
    if t.kind == "segment":
        info = f"segment ({t.x1},{t.y1})-({t.x2},{t.y2})"
    elif t.kind == "point":
        if t.floors:
            info = f"column ({t.x1},{t.y1})"
        else:
            info = f"grid_intersection ({t.x1},{t.y1})"
    else:
        info = f"{t.kind} ({t.x1},{t.y1})"
    return best_nx, best_ny, best_dist, info


# ---------------------------------------------------------------------------
# 6. Wall-to-beam snap
# ---------------------------------------------------------------------------

def _wall_direction(wall):
    """Return 'X' or 'Y' based on which axis the wall is parallel to.

    A wall along X has its variable axis in X (fixed Y).
    A wall along Y has its variable axis in Y (fixed X).
    """
    dx = abs(wall["x2"] - wall["x1"])
    dy = abs(wall["y2"] - wall["y1"])
    return "X" if dx >= dy else "Y"


def _beam_direction(beam):
    """Return 'X' or 'Y' based on which axis the beam spans."""
    dx = abs(beam["x2"] - beam["x1"])
    dy = abs(beam["y2"] - beam["y1"])
    return "X" if dx >= dy else "Y"


def _ranges_overlap(a_min, a_max, b_min, b_max):
    """True if [a_min, a_max] and [b_min, b_max] overlap (with 0.01m tolerance)."""
    return a_min <= b_max + 0.01 and b_min <= a_max + 0.01


def snap_walls_to_beams(elements, tolerance=1.0, var_tolerance=0.5):
    """Snap wall fixed-axis coordinate AND variable-axis endpoints to beams.

    In PPT 2D structural plans, walls are drawn next to beams (offset)
    because they can't overlap in 2D. In the 3D ETABS model, walls should
    be placed directly under beams (same axis coordinate).

    For each wall:
      1. Determine direction (X or Y)
      2. Find same-direction beams with overlapping variable-axis range
         and at least one common floor
      3. Snap wall's fixed-axis to the nearest qualifying beam's fixed-axis
      4. Only snap if distance > 0.01m and <= tolerance
      5. After fixed-axis snap, snap each variable-axis endpoint to the
         nearest colinear beam endpoint within var_tolerance

    Parameters
    ----------
    elements : dict
        Parsed elements with "beams" and "walls".
    tolerance : float
        Max fixed-axis snap distance in meters (default 1.0).
    var_tolerance : float
        Max variable-axis endpoint snap distance in meters (default 0.5).

    Returns
    -------
    tuple[dict, list]
        (updated_elements, snap_details_list)
    """
    walls = elements.get("walls", [])
    beams = elements.get("beams", [])
    snap_details = []

    if not walls or not beams:
        return elements, snap_details

    for wall in walls:
        w_dir = _wall_direction(wall)
        w_floors = set(wall.get("floors", []))

        if w_dir == "X":
            # Wall is horizontal: fixed axis = Y, variable axis = X
            w_fixed = (wall["y1"] + wall["y2"]) / 2.0
            w_var_min = min(wall["x1"], wall["x2"])
            w_var_max = max(wall["x1"], wall["x2"])
        else:
            # Wall is vertical: fixed axis = X, variable axis = Y
            w_fixed = (wall["x1"] + wall["x2"]) / 2.0
            w_var_min = min(wall["y1"], wall["y2"])
            w_var_max = max(wall["y1"], wall["y2"])

        best_beam = None
        best_dist = float("inf")
        best_beam_fixed = None

        for beam in beams:
            b_dir = _beam_direction(beam)
            if b_dir != w_dir:
                continue

            # Check floor overlap
            b_floors = set(beam.get("floors", []))
            if not (w_floors & b_floors):
                continue

            if b_dir == "X":
                b_fixed = (beam["y1"] + beam["y2"]) / 2.0
                b_var_min = min(beam["x1"], beam["x2"])
                b_var_max = max(beam["x1"], beam["x2"])
            else:
                b_fixed = (beam["x1"] + beam["x2"]) / 2.0
                b_var_min = min(beam["y1"], beam["y2"])
                b_var_max = max(beam["y1"], beam["y2"])

            # Check variable-axis overlap
            if not _ranges_overlap(w_var_min, w_var_max, b_var_min, b_var_max):
                continue

            dist = abs(w_fixed - b_fixed)
            if dist < best_dist:
                best_dist = dist
                best_beam = beam
                best_beam_fixed = b_fixed

        # Apply fixed-axis snap if within tolerance and meaningful
        fixed_snapped = False
        if best_beam is not None and best_dist > 0.01 and best_dist <= tolerance:
            before = {
                "x1": wall["x1"], "y1": wall["y1"],
                "x2": wall["x2"], "y2": wall["y2"],
            }

            if w_dir == "X":
                wall["y1"] = best_beam_fixed
                wall["y2"] = best_beam_fixed
            else:
                wall["x1"] = best_beam_fixed
                wall["x2"] = best_beam_fixed

            fixed_snapped = True
            snap_details.append({
                "wall_section": wall.get("section", ""),
                "wall_floors": wall.get("floors", []),
                "direction": w_dir,
                "snap_type": "fixed_axis",
                "before": before,
                "after": {
                    "x1": wall["x1"], "y1": wall["y1"],
                    "x2": wall["x2"], "y2": wall["y2"],
                },
                "distance": round(best_dist, 4),
                "target_beam_section": best_beam.get("section", ""),
            })

        # --- Variable-axis endpoint snap ---
        # Recalculate fixed coordinate after potential snap
        if w_dir == "X":
            w_fixed_now = (wall["y1"] + wall["y2"]) / 2.0
        else:
            w_fixed_now = (wall["x1"] + wall["x2"]) / 2.0

        # Collect all colinear beam endpoints (same direction, tight fixed-axis match, floor overlap)
        COLINEAR_THRESHOLD = 0.05  # 5cm — wall and beam should already be snapped
        colinear_endpoints = []
        for beam in beams:
            b_dir = _beam_direction(beam)
            if b_dir != w_dir:
                continue
            b_floors = set(beam.get("floors", []))
            if not (w_floors & b_floors):
                continue
            if w_dir == "X":
                b_fixed = (beam["y1"] + beam["y2"]) / 2.0
                if abs(b_fixed - w_fixed_now) > COLINEAR_THRESHOLD:
                    continue
                colinear_endpoints.append(min(beam["x1"], beam["x2"]))
                colinear_endpoints.append(max(beam["x1"], beam["x2"]))
            else:
                b_fixed = (beam["x1"] + beam["x2"]) / 2.0
                if abs(b_fixed - w_fixed_now) > COLINEAR_THRESHOLD:
                    continue
                colinear_endpoints.append(min(beam["y1"], beam["y2"]))
                colinear_endpoints.append(max(beam["y1"], beam["y2"]))

        if not colinear_endpoints:
            continue

        colinear_endpoints.sort()

        # Current wall variable-axis endpoints
        if w_dir == "X":
            var_min = min(wall["x1"], wall["x2"])
            var_max = max(wall["x1"], wall["x2"])
        else:
            var_min = min(wall["y1"], wall["y2"])
            var_max = max(wall["y1"], wall["y2"])

        # Snap var_min to nearest colinear beam endpoint
        best_min_ep = None
        best_min_dist = float("inf")
        for ep in colinear_endpoints:
            d = abs(ep - var_min)
            if d < best_min_dist:
                best_min_dist = d
                best_min_ep = ep

        # Snap var_max to nearest colinear beam endpoint
        best_max_ep = None
        best_max_dist = float("inf")
        for ep in colinear_endpoints:
            d = abs(ep - var_max)
            if d < best_max_dist:
                best_max_dist = d
                best_max_ep = ep

        # Apply variable-axis snaps
        for snap_end, snap_ep, snap_dist in [
            ("var_min", best_min_ep, best_min_dist),
            ("var_max", best_max_ep, best_max_dist),
        ]:
            if snap_ep is None or snap_dist < 0.01 or snap_dist > var_tolerance:
                continue

            before_var = {
                "x1": wall["x1"], "y1": wall["y1"],
                "x2": wall["x2"], "y2": wall["y2"],
            }

            if w_dir == "X":
                if snap_end == "var_min":
                    # Snap the endpoint that has the smaller X
                    if wall["x1"] <= wall["x2"]:
                        wall["x1"] = snap_ep
                    else:
                        wall["x2"] = snap_ep
                else:
                    # Snap the endpoint that has the larger X
                    if wall["x1"] >= wall["x2"]:
                        wall["x1"] = snap_ep
                    else:
                        wall["x2"] = snap_ep
            else:
                if snap_end == "var_min":
                    if wall["y1"] <= wall["y2"]:
                        wall["y1"] = snap_ep
                    else:
                        wall["y2"] = snap_ep
                else:
                    if wall["y1"] >= wall["y2"]:
                        wall["y1"] = snap_ep
                    else:
                        wall["y2"] = snap_ep

            snap_details.append({
                "wall_section": wall.get("section", ""),
                "wall_floors": wall.get("floors", []),
                "direction": w_dir,
                "snap_type": "variable_axis_" + snap_end,
                "before": before_var,
                "after": {
                    "x1": wall["x1"], "y1": wall["y1"],
                    "x2": wall["x2"], "y2": wall["y2"],
                },
                "distance": round(snap_dist, 4),
            })

    return elements, snap_details


# ---------------------------------------------------------------------------
# 6b. Beam follow-up after wall re-snap
# ---------------------------------------------------------------------------

def _follow_wall_resnap(elements, snap_details):
    """Update beam endpoints that matched old wall positions to new positions.

    After snap_walls_to_beams() moves wall coordinates, beams that were
    previously snapped to those wall endpoints become floating. This function
    finds beam endpoints matching old (before) wall coordinates and moves
    them to the new (after) coordinates.
    """
    MATCH_TOL = 0.05  # 5cm
    beams = elements.get("beams", [])

    for detail in snap_details:
        before = detail["before"]
        after = detail["after"]

        # Check each wall endpoint (x1,y1) and (x2,y2) for changes
        for coord_key in [("x1", "y1"), ("x2", "y2")]:
            old_x = before[coord_key[0]]
            old_y = before[coord_key[1]]
            new_x = after[coord_key[0]]
            new_y = after[coord_key[1]]

            if abs(old_x - new_x) < 0.01 and abs(old_y - new_y) < 0.01:
                continue  # no change for this endpoint

            for beam in beams:
                for ep in [("x1", "y1"), ("x2", "y2")]:
                    bx, by = beam[ep[0]], beam[ep[1]]
                    if abs(bx - old_x) < MATCH_TOL and abs(by - old_y) < MATCH_TOL:
                        beam[ep[0]] = new_x
                        beam[ep[1]] = new_y


# ---------------------------------------------------------------------------
# 7. Main validation
# ---------------------------------------------------------------------------

def validate_beams(elements, grid_data, tolerance=1.5,
                   split_tolerance=0.15, no_split=False,
                   angle_threshold_deg=2.0, no_angle_correct=False,
                   cluster_tolerance=0.50, no_cluster=False,
                   outline=None, outline_tolerance=0.5):
    """Validate and auto-snap major beam endpoints.

    Pipeline order:
      Step 0: Angle correction (2° default, runs FIRST for accurate ray direction)
      Step 1: 3-round ray snap with post-round clustering
      Step 2: Split beams at columns + walls + other beams
      Step 3: Split walls at columns + beams + other walls
      Step 4: Wall-to-beam re-snap (1.0m default, aligns walls under beams)

    Parameters
    ----------
    elements : dict
        Parsed elements.json with "columns", "walls", "beams" keys.
    grid_data : dict
        Grid data with "x" and "y" lists.
    tolerance : float
        Maximum snap distance in meters (default 1.5).
    split_tolerance : float
        Max perpendicular distance for beam splitting (default 0.15m).
    no_split : bool
        If True, skip beam and wall splitting steps.
    angle_threshold_deg : float
        Max angle deviation to correct (default 2.0 degrees).
    no_angle_correct : bool
        If True, skip angle correction step.
    cluster_tolerance : float
        Max distance for clustering free endpoints of half-snapped beams
        (default 0.50m).
    no_cluster : bool
        If True, skip endpoint clustering.
    outline : list or None
        Building outline polygon [[x,y],...] for outline-aware corrections.
    outline_tolerance : float
        Tolerance for outline proximity check (default 0.5m).

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
            "angle_corrections": [],
            "angle_corrected_beams": 0,
            "angle_corrected_walls": 0,
            "split_beams": 0,
            "new_beams_from_split": 0,
            "total_beams_after_split": 0,
            "split_details": [],
            "wall_split_walls": 0,
            "wall_new_from_split": 0,
            "wall_total_after_split": len(elements.get("walls", [])),
            "wall_split_details": [],
            "wall_beam_snaps": 0,
            "wall_beam_snap_details": [],
            "clustered_endpoints": 0,
            "cluster_count": 0,
            "snap_rounds": 0,
        }
        return elements, report

    # --- Step 0: Angle correction FIRST (ray snap needs accurate direction) ---
    angle_corrections = []
    if not no_angle_correct:
        elements, angle_corrections = correct_angles(
            elements, grid_data, angle_threshold_deg,
            outline=outline, outline_tolerance=outline_tolerance)
        # Re-read beams after angle correction (may have changed)
        beams = elements.get("beams", [])
        n = len(beams)

    # --- Step 1: 3-round ray snap with post-round clustering ---

    # Build targets
    grid_targets, element_targets = build_beam_targets(elements, grid_data)
    base_targets = grid_targets + element_targets

    # Track snap state per endpoint: False = unsnapped
    snapped_state = [[False, False] for _ in range(n)]

    # Beam segment targets (added after each round)
    beam_snap_targets = []

    # --- Helper: ray snap one round ---
    def _snap_round_ray(targets):
        """Try to ray-snap all unsnapped endpoints. Returns count of newly snapped."""
        count = 0
        for i in range(n):
            beam = beams[i]
            floors = beam.get("floors", [])
            # Compute beam direction unit vector
            dx = beam["x2"] - beam["x1"]
            dy = beam["y2"] - beam["y1"]
            length = math.hypot(dx, dy)
            if length < 1e-6:
                continue  # zero-length beam, skip
            dx /= length
            dy /= length

            for ep in range(2):  # 0=start, 1=end
                if snapped_state[i][ep]:
                    continue
                if ep == 0:
                    px, py = beam["x1"], beam["y1"]
                else:
                    px, py = beam["x2"], beam["y2"]

                result = snap_by_ray(px, py, dx, dy, floors, targets,
                                     tolerance, grid_data,
                                     point_snap_mode="direct")
                if result:
                    nx, ny, d, target_info = result

                    # Determine target_type from target_info
                    if target_info.startswith("grid_intersection"):
                        target_type = "grid_intersection"
                    elif target_info.startswith("column"):
                        target_type = "column"
                    elif target_info.startswith("segment"):
                        target_type = "segment"
                    else:
                        target_type = "other"

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

    all_cluster_corrections = []

    def _post_round_cluster():
        """After each snap round: promote fully-snapped → cluster → promote again."""
        _add_fully_snapped_beams()
        if not no_cluster:
            cc = cluster_free_endpoints(beams, snapped_state, cluster_tolerance,
                                        beam_key_prefix="beam")
            all_cluster_corrections.extend(cc)
            _add_fully_snapped_beams()

    # Convergence loop: snap until no new snaps or MAX_ROUNDS
    MAX_ROUNDS = 10
    snap_rounds = 0
    while snap_rounds < MAX_ROUNDS:
        snap_rounds += 1
        targets = base_targets if snap_rounds == 1 else base_targets + beam_snap_targets
        new_snaps = _snap_round_ray(targets)
        _post_round_cluster()
        if new_snaps == 0:
            break

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

    # --- Step 2: Beam splitting (beams at columns + walls + other beams) ---
    split_report = {
        "split_beams": 0,
        "new_beams_from_split": 0,
        "total_beams_after_split": len(elements.get("beams", [])),
        "split_details": [],
    }
    if not no_split:
        elements, split_report = split_all_beams(elements, grid_data, split_tolerance)

    # --- Step 3: Wall splitting (walls at columns + beams + other walls) ---
    wall_split_report = {
        "wall_split_walls": 0,
        "wall_new_from_split": 0,
        "wall_total_after_split": len(elements.get("walls", [])),
        "wall_split_details": [],
    }
    if not no_split:
        elements, wall_split_report = split_all_walls(elements, grid_data, split_tolerance)

    # --- Step 4: Wall-to-beam re-snap ---
    elements, wall_beam_snap_details = snap_walls_to_beams(elements, tolerance=1.0)

    # --- Step 4b: Update beams that followed moved walls ---
    if wall_beam_snap_details:
        _follow_wall_resnap(elements, wall_beam_snap_details)

    # --- Build report ---
    snap_distances = [c["snap_distance"] for c in corrections]
    clustered_eps = sum(c["member_count"] for c in all_cluster_corrections)
    report = {
        "total_beams": n,
        "total_endpoints": n * 2,
        "snapped_endpoints": len(corrections),
        "warning_endpoints": len(warnings),
        "max_snap_distance": max(snap_distances) if snap_distances else 0,
        "avg_snap_distance": round(sum(snap_distances) / len(snap_distances), 4) if snap_distances else 0,
        "corrections": corrections,
        "warnings": warnings,
        "angle_corrections": angle_corrections,
        "angle_corrected_beams": sum(1 for a in angle_corrections if a["element_type"] == "beam"),
        "angle_corrected_walls": sum(1 for a in angle_corrections if a["element_type"] == "wall"),
        "clustered_endpoints": clustered_eps,
        "cluster_count": len(all_cluster_corrections),
        **split_report,
        **wall_split_report,
        "wall_beam_snaps": len(wall_beam_snap_details),
        "wall_beam_snap_details": wall_beam_snap_details,
        "snap_rounds": snap_rounds,
    }

    return elements, report


# ---------------------------------------------------------------------------
# 8. CLI entry point
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
    parser.add_argument("--angle-threshold", type=float, default=2.0,
                        help="Angle correction threshold in degrees (default: 2.0)")
    parser.add_argument("--no-angle-correct", action="store_true",
                        help="Skip angle correction step")
    parser.add_argument("--split-tolerance", type=float, default=0.15,
                        help="Max perpendicular distance for beam splitting (default: 0.15m)")
    parser.add_argument("--no-split", action="store_true",
                        help="Skip beam splitting step")
    parser.add_argument("--cluster-tolerance", type=float, default=0.50,
                        help="Max distance for clustering free endpoints of "
                        "half-snapped beams (default: 0.50m)")
    parser.add_argument("--no-cluster", action="store_true",
                        help="Skip endpoint clustering step")
    parser.add_argument("--outline",
                        help="Path to JSON with building_outline polygon "
                             "(or model_config.json with building_outline field)")
    parser.add_argument("--outline-tolerance", type=float, default=0.5,
                        help="Tolerance for outline proximity check (default: 0.5m)")
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
    grid_data = _normalize_grid_data_for_bv(grid_data)

    # Load outline if provided
    outline = None
    if args.outline:
        with open(args.outline, encoding="utf-8") as f:
            outline_data = json.load(f)
        if isinstance(outline_data, list):
            outline = outline_data
        elif isinstance(outline_data, dict):
            outline = outline_data.get("building_outline")
        if outline:
            print(f"Outline loaded: {args.outline} ({len(outline)} vertices)")

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
    if not args.no_angle_correct:
        print(f"  angle threshold: {args.angle_threshold}°")
    if not args.no_split:
        print(f"  split tolerance: {args.split_tolerance}m")
    if not args.no_cluster:
        print(f"  cluster tolerance: {args.cluster_tolerance}m")

    if n_beams == 0:
        print("\nNo beams to validate.")
        if not args.dry_run:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(elements, f, ensure_ascii=False, indent=2)
            print(f"Output written to: {args.output}")
        return

    # Run validation
    validated, report = validate_beams(
        elements, grid_data,
        tolerance=args.tolerance,
        split_tolerance=args.split_tolerance,
        no_split=args.no_split,
        angle_threshold_deg=args.angle_threshold,
        no_angle_correct=args.no_angle_correct,
        cluster_tolerance=args.cluster_tolerance,
        no_cluster=args.no_cluster,
        outline=outline,
        outline_tolerance=args.outline_tolerance,
    )

    # Print summary
    print(f"\n--- Beam Validation Summary ---")
    print(f"  Total beams: {report['total_beams']}")
    print(f"  Total endpoints: {report['total_endpoints']}")
    print(f"  Snapped endpoints: {report['snapped_endpoints']}")
    print(f"  Warning endpoints: {report['warning_endpoints']}")
    if report["snapped_endpoints"] > 0:
        print(f"  Max snap distance: {report['max_snap_distance']:.4f}m")
        print(f"  Avg snap distance: {report['avg_snap_distance']:.4f}m")

    # Cluster summary
    if report.get("cluster_count", 0) > 0:
        print(f"  Endpoint clusters: {report['cluster_count']} "
              f"({report['clustered_endpoints']} endpoints)")

    # Angle correction summary
    if report.get("angle_corrections"):
        n_angle = len(report["angle_corrections"])
        print(f"  Angle corrections: {n_angle} "
              f"(beams: {report['angle_corrected_beams']}, "
              f"walls: {report['angle_corrected_walls']})")

    # Split summary
    if report.get("split_beams", 0) > 0:
        print(f"  Split beams: {report['split_beams']} → "
              f"{report['new_beams_from_split']} new sub-beams "
              f"(total after split: {report['total_beams_after_split']})")
    if report.get("wall_split_walls", 0) > 0:
        print(f"  Split walls: {report['wall_split_walls']} → "
              f"{report['wall_new_from_split']} new sub-walls "
              f"(total after split: {report['wall_total_after_split']})")

    # Wall-beam snap summary
    if report.get("wall_beam_snaps", 0) > 0:
        print(f"  Wall-beam snaps: {report['wall_beam_snaps']}")
        for d in report["wall_beam_snap_details"]:
            print(f"    {d['wall_section']} ({d['direction']}): "
                  f"Δ={d['distance']}m → {d.get('target_beam_section', d.get('snap_type', ''))}")

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
            print(f"\nSnap corrections preview ({len(report['corrections'])}):")
            for c in report["corrections"]:
                print(f"  beam[{c['beam_index']}] {c['section']} {c['endpoint']}: "
                      f"({c['original_coord'][0]}, {c['original_coord'][1]}) -> "
                      f"({c['corrected_coord'][0]}, {c['corrected_coord'][1]}) "
                      f"d={c['snap_distance']}m [{c['target_label']}]")
        if report.get("angle_corrections"):
            print(f"\nAngle corrections preview ({len(report['angle_corrections'])}):")
            for a in report["angle_corrections"]:
                print(f"  {a['element_type']}[{a['index']}] {a['section']}: "
                      f"{a['angle_deg']}° → {a['correction_axis']} "
                      f"[{a['target_grid_label']}] Δ={a['displacement']}m")
        if report.get("split_details"):
            print(f"\nBeam split preview ({len(report['split_details'])}):")
            for s in report["split_details"]:
                pts = ", ".join(f"({p[0]},{p[1]})" for p in s["split_points"])
                print(f"  beam[{s['original_index']}] {s['section']}: "
                      f"→ {s['result_count']} segments at [{pts}]")
        if report.get("wall_split_details"):
            print(f"\nWall split preview ({len(report['wall_split_details'])}):")
            for s in report["wall_split_details"]:
                pts = ", ".join(f"({p[0]},{p[1]})" for p in s["split_points"])
                print(f"  wall[{s['original_index']}] {s['section']}: "
                      f"→ {s['result_count']} segments at [{pts}]")
        if report.get("wall_beam_snap_details"):
            print(f"\nWall-beam snap preview ({len(report['wall_beam_snap_details'])}):")
            for d in report["wall_beam_snap_details"]:
                print(f"  {d['wall_section']} ({d['direction']}): "
                      f"Δ={d['distance']}m → {d.get('target_beam_section', d.get('snap_type', ''))}")
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
