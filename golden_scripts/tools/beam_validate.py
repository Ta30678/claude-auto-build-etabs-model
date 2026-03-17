"""
Beam Validate Tool — Deterministic beam endpoint connectivity validator.

Phase 1 of the BTS workflow extracts major beams from structural plans via
pptx_to_elements.py. The extracted beam endpoint coordinates may not land
precisely on grid intersections, columns, walls, or other beams due to PPTX
shape imprecision. This tool validates and auto-snaps floating endpoints,
splits beams/walls at intermediate supports (columns, walls, other beams),
and corrects near-orthogonal angle deviations on the final geometry.

Pipeline order:
  Step 0: 3-round snap (grid + columns + walls + beams)
  Step 1: Split beams at columns + walls + other beams
  Step 2: Split walls at columns + beams + other walls
  Step 3: Angle correction (2° default, runs on post-split geometry)

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
)


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


def correct_angles(elements, grid_data, angle_threshold_deg=2.0):
    """Auto-correct near-orthogonal angle deviations for beams and walls.

    For each beam/wall with endpoints (x1,y1)→(x2,y2):
    - If nearly horizontal (angle ≤ threshold): align Y coordinates to nearest
      Y grid line, or fallback to average.
    - If nearly vertical (|angle - 90°| ≤ threshold): align X coordinates to
      nearest X grid line, or fallback to average.
    - Otherwise: leave unchanged (true diagonal).

    Angle correction runs AFTER snap + split so that it operates on final
    geometry without risk of moving endpoints away from correct snap targets.

    Parameters
    ----------
    elements : dict
        Elements with "beams" and "walls" lists.
    grid_data : dict
        Grid data with "x" and "y" lists.
    angle_threshold_deg : float
        Maximum angle deviation from horizontal/vertical to correct (default 2.0).

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

    angle_report = []

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
                    y_target = round((y1 + y2) / 2, 2)
                    target_label = "average"

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
                    x_target = round((x1 + x2) / 2, 2)
                    target_label = "average"

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

def segment_intersection(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
    """Compute intersection point of two line segments.

    Returns (x, y, t_a, t_b) where t_a and t_b are parameter values [0,1]
    on segment A and B respectively, or None if no intersection.
    """
    dax = ax2 - ax1
    day = ay2 - ay1
    dbx = bx2 - bx1
    dby = by2 - by1

    denom = dax * dby - day * dbx
    if abs(denom) < 1e-12:
        return None  # parallel or coincident

    t_a = ((bx1 - ax1) * dby - (by1 - ay1) * dbx) / denom
    t_b = ((bx1 - ax1) * day - (by1 - ay1) * dax) / denom

    if t_a < -1e-9 or t_a > 1 + 1e-9 or t_b < -1e-9 or t_b > 1 + 1e-9:
        return None  # no intersection within segments

    x = ax1 + t_a * dax
    y = ay1 + t_a * day
    return x, y, t_a, t_b


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
        # Skip very short sub-beams (< 0.1m)
        if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) < 0.1:
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


# ---------------------------------------------------------------------------
# 4. Single-point snapping
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
    info = _build_target_info(best_target, best_nx, best_ny, None)
    return best_nx, best_ny, best_dist, info


# ---------------------------------------------------------------------------
# 6. Main validation
# ---------------------------------------------------------------------------

def validate_beams(elements, grid_data, tolerance=1.5,
                   split_tolerance=0.15, no_split=False,
                   angle_threshold_deg=2.0, no_angle_correct=False):
    """Validate and auto-snap major beam endpoints.

    Pipeline order:
      Step 0: 3-round snap (grid + columns + walls + beams)
      Step 1: Split beams at columns + walls + other beams
      Step 2: Split walls at columns + beams + other walls
      Step 3: Angle correction (2° default, on post-split geometry)

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
        }
        return elements, report

    # --- Step 0: 3-round snap ---

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

    # --- Step 1: Beam splitting (beams at columns + walls + other beams) ---
    split_report = {
        "split_beams": 0,
        "new_beams_from_split": 0,
        "total_beams_after_split": len(elements.get("beams", [])),
        "split_details": [],
    }
    if not no_split:
        elements, split_report = split_all_beams(elements, grid_data, split_tolerance)

    # --- Step 2: Wall splitting (walls at columns + beams + other walls) ---
    wall_split_report = {
        "wall_split_walls": 0,
        "wall_new_from_split": 0,
        "wall_total_after_split": len(elements.get("walls", [])),
        "wall_split_details": [],
    }
    if not no_split:
        elements, wall_split_report = split_all_walls(elements, grid_data, split_tolerance)

    # --- Step 3: Angle correction (on post-split geometry) ---
    angle_corrections = []
    if not no_angle_correct:
        elements, angle_corrections = correct_angles(
            elements, grid_data, angle_threshold_deg)

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
        "angle_corrections": angle_corrections,
        "angle_corrected_beams": sum(1 for a in angle_corrections if a["element_type"] == "beam"),
        "angle_corrected_walls": sum(1 for a in angle_corrections if a["element_type"] == "wall"),
        **split_report,
        **wall_split_report,
    }

    return elements, report


# ---------------------------------------------------------------------------
# 7. CLI entry point
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
