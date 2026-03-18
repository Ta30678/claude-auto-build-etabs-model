"""
SB Validate Tool — Phase 2 small beam angle correction, snapping, and splitting.

After affine_calibrate aligns SB coordinates to the grid system, SB endpoints may
still have small angle deviations, miss intermediate supports, or not land precisely
on structural elements. This tool applies the same angle correction, multi-round
snapping, and splitting logic from beam_validate.py, adapted for Phase 2 small beams.

Replaces config_snap.py in the Phase 2 pipeline.

Usage:
    python -m golden_scripts.tools.sb_validate \
        --sb-elements sb_elements_aligned.json \
        --config model_config.json \
        --grid-data grid_data.json \
        --output sb_elements_validated.json \
        --report sb_validate_report.json

    # Custom tolerances:
    python -m golden_scripts.tools.sb_validate \
        --sb-elements sb_elements_aligned.json \
        --config model_config.json \
        --grid-data grid_data.json \
        --output sb_elements_validated.json \
        --tolerance 1.0 \
        --split-tolerance 0.30

    # Disable angle correction or splitting:
    python -m golden_scripts.tools.sb_validate \
        --sb-elements sb_elements_aligned.json \
        --config model_config.json \
        --grid-data grid_data.json \
        --output sb_elements_validated.json \
        --no-angle-correct --no-split

    # Preview without writing:
    python -m golden_scripts.tools.sb_validate \
        --sb-elements sb_elements_aligned.json \
        --config model_config.json \
        --grid-data grid_data.json \
        --output sb_elements_validated.json \
        --dry-run
"""
import json
import argparse
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from golden_scripts.tools.config_snap import (
    SnapTarget,
    point_to_segment_nearest,
    floors_overlap,
)
from golden_scripts.tools.beam_validate import (
    _normalize_grid_data_for_bv,
    _find_nearest_grid_value,
    segment_intersection,
    split_beam,
    _grid_label_at,
)
from golden_scripts.constants import parse_frame_section


# ---------------------------------------------------------------------------
# 1. Ray-based snap for SB endpoints
# ---------------------------------------------------------------------------

def snap_sb_by_ray(px, py, ray_dx, ray_dy, floors, targets, tolerance,
                   grid_data=None):
    """Snap SB endpoint by extending ray along SB direction.

    Creates a search segment of length 2*tolerance centered on (px, py)
    along the SB direction (ray_dx, ray_dy), then finds intersections
    with target segments. For point targets, checks perpendicular distance
    to ray and projects onto the ray.

    Parameters
    ----------
    px, py : float
        SB endpoint coordinates.
    ray_dx, ray_dy : float
        SB direction unit vector.
    floors : list[str]
        Floors the SB exists on.
    targets : list[SnapTarget]
        Available snap targets.
    tolerance : float
        Maximum extension distance along ray AND max perpendicular distance
        for point targets.
    grid_data : dict or None
        Grid data for generating target labels (optional).

    Returns
    -------
    tuple or None
        (snapped_x, snapped_y, distance, target_info_str) or None if no
        target found along the ray within tolerance.
    """
    best_nx, best_ny, best_dist = None, None, tolerance + 1
    best_info = None

    # Search segment: extend tolerance in both directions from endpoint
    sx1 = px - ray_dx * tolerance
    sy1 = py - ray_dy * tolerance
    sx2 = px + ray_dx * tolerance
    sy2 = py + ray_dy * tolerance

    for t in targets:
        # Floor overlap check (skip for grid targets with floors=[])
        if t.floors:
            if not floors_overlap(floors, t.floors):
                continue

        if t.kind == "segment":
            # Find intersection of search ray segment with target segment
            result = segment_intersection(
                sx1, sy1, sx2, sy2, t.x1, t.y1, t.x2, t.y2)
            if result is None:
                continue
            ix, iy, t_ray, t_seg = result
            d = math.hypot(ix - px, iy - py)
            if d < best_dist:
                best_nx = round(ix, 2)
                best_ny = round(iy, 2)
                best_dist = d
                best_info = f"segment ({t.x1},{t.y1})-({t.x2},{t.y2})"

        elif t.kind == "point":
            # Project point onto ray, check perpendicular distance
            dot = (t.x1 - px) * ray_dx + (t.y1 - py) * ray_dy
            if abs(dot) > tolerance:
                continue  # too far along ray
            proj_x = px + dot * ray_dx
            proj_y = py + dot * ray_dy
            perp_dist = math.hypot(t.x1 - proj_x, t.y1 - proj_y)
            if perp_dist > tolerance:
                continue  # too far off-axis
            d = abs(dot)  # distance along ray
            if d < best_dist:
                best_nx = round(proj_x, 2)
                best_ny = round(proj_y, 2)
                best_dist = d
                # Identify target type
                if t.floors:
                    best_info = f"column ({t.x1},{t.y1})"
                else:
                    label = _grid_label_at(t.x1, t.y1, grid_data) if grid_data else None
                    best_info = f"grid_intersection {label or f'({t.x1},{t.y1})'}"

    if best_nx is not None:
        return best_nx, best_ny, round(best_dist, 4), best_info
    return None


def ray_ray_intersection(p1x, p1y, d1x, d1y, p2x, p2y, d2x, d2y):
    """Compute intersection point of two rays.

    Ray 1: (p1x,p1y) + t*(d1x,d1y)
    Ray 2: (p2x,p2y) + s*(d2x,d2y)

    Returns (ix, iy) or None if parallel.
    """
    cross = d1x * d2y - d1y * d2x
    if abs(cross) < 1e-9:
        return None
    dx = p2x - p1x
    dy = p2y - p1y
    t = (dx * d2y - dy * d2x) / cross
    ix = round(p1x + t * d1x, 2)
    iy = round(p1y + t * d1y, 2)
    return ix, iy


# ---------------------------------------------------------------------------
# 2. Target construction
# ---------------------------------------------------------------------------

def build_sb_targets(config, grid_data):
    """Build snap targets from model_config.json for SB snapping.

    Unlike beam_validate's build_beam_targets, this includes major beams
    as segment targets from the start (they are already validated in Phase 1).

    Parameters
    ----------
    config : dict
        model_config.json with columns, beams, walls.
    grid_data : dict
        Normalized grid data with "x" and "y" lists.

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
            grid_targets.append(SnapTarget(
                "point", xg["coordinate"], yg["coordinate"],
                xg["coordinate"], yg["coordinate"], floors=[]))

    # Columns -> point targets
    for col in config.get("columns", []):
        element_targets.append(SnapTarget(
            "point",
            col["grid_x"], col["grid_y"],
            col["grid_x"], col["grid_y"],
            col.get("floors", [])))

    # Walls -> segment targets
    for wall in config.get("walls", []):
        element_targets.append(SnapTarget(
            "segment",
            wall["x1"], wall["y1"],
            wall["x2"], wall["y2"],
            wall.get("floors", [])))

    # Major beams -> segment targets (already validated in Phase 1)
    for beam in config.get("beams", []):
        element_targets.append(SnapTarget(
            "segment",
            beam["x1"], beam["y1"],
            beam["x2"], beam["y2"],
            beam.get("floors", [])))

    return grid_targets, element_targets


# ---------------------------------------------------------------------------
# 2. Angle correction
# ---------------------------------------------------------------------------

def correct_sb_angles(sb_data, grid_data, angle_threshold_deg=5.0):
    """Auto-correct near-orthogonal angle deviations for small beams.

    Same logic as beam_validate.correct_angles but iterates over
    sb_data["small_beams"] instead of elements["beams"/"walls"].

    Parameters
    ----------
    sb_data : dict
        Data with "small_beams" list.
    grid_data : dict
        Grid data with "x" and "y" lists.
    angle_threshold_deg : float
        Max angle deviation from horizontal/vertical to correct.

    Returns
    -------
    tuple[dict, list[dict]]
        (corrected_sb_data, angle_report_list)
    """
    threshold_rad = math.radians(angle_threshold_deg)
    x_grids = grid_data.get("x", [])
    y_grids = grid_data.get("y", [])
    grid_max_dist = 2.0

    angle_report = []

    small_beams = sb_data.get("small_beams", [])
    for idx, sb in enumerate(small_beams):
        direction = sb.get("direction", "").upper()
        if direction in ("X", "Y"):
            continue  # PPT extraction confident — skip angle correction
        x1, y1 = sb["x1"], sb["y1"]
        x2, y2 = sb["x2"], sb["y2"]
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 0.01:
            continue

        angle = math.atan2(abs(dy), abs(dx))

        corrected = False
        correction_axis = None
        target_label = None
        original = [x1, y1, x2, y2]

        if angle <= threshold_rad:
            # Near horizontal -> align Y
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

            sb["y1"] = round(y_target, 2)
            sb["y2"] = round(y_target, 2)
            corrected = True

        elif abs(angle - math.pi / 2) <= threshold_rad:
            # Near vertical -> align X
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

            sb["x1"] = round(x_target, 2)
            sb["x2"] = round(x_target, 2)
            corrected = True

        if corrected:
            displacement = max(
                math.hypot(sb["x1"] - original[0], sb["y1"] - original[1]),
                math.hypot(sb["x2"] - original[2], sb["y2"] - original[3]),
            )
            angle_report.append({
                "element_type": "small_beam",
                "index": idx,
                "section": sb.get("section", ""),
                "original": original,
                "corrected": [sb["x1"], sb["y1"], sb["x2"], sb["y2"]],
                "angle_deg": round(math.degrees(angle), 2),
                "correction_axis": correction_axis,
                "target_grid_label": target_label,
                "displacement": round(displacement, 4),
            })

    return sb_data, angle_report


# ---------------------------------------------------------------------------
# 3. Section area computation
# ---------------------------------------------------------------------------

def _compute_section_area(section_name):
    """Compute width * depth from section name for SB sorting.

    Returns area in cm^2, or 0 if parsing fails.
    """
    prefix, width, depth, fc = parse_frame_section(section_name)
    if width and depth:
        return width * depth
    return 0


# ---------------------------------------------------------------------------
# 4. SB splitting
# ---------------------------------------------------------------------------

def find_sb_intermediate_supports(sb, columns, walls, beams, larger_sbs,
                                  split_tolerance=0.30):
    """Find intermediate support points along a small beam.

    Extended version of beam_validate.find_intermediate_supports that also
    considers major beams and larger SBs as split targets.

    Parameters
    ----------
    sb : dict
        Small beam with x1,y1,x2,y2,floors.
    columns : list[dict]
        Column list with grid_x, grid_y, floors.
    walls : list[dict]
        Wall list with x1,y1,x2,y2,floors.
    beams : list[dict]
        Major beam list with x1,y1,x2,y2,floors.
    larger_sbs : list[dict]
        Already-processed SBs (larger or equal section area).
    split_tolerance : float
        Max perpendicular distance for column projection.

    Returns
    -------
    list[tuple]
        [(t, x, y, source_label)] sorted by t.
    """
    bx1, by1 = sb["x1"], sb["y1"]
    bx2, by2 = sb["x2"], sb["y2"]
    b_floors = sb.get("floors", [])
    bdx = bx2 - bx1
    bdy = by2 - by1
    b_len_sq = bdx * bdx + bdy * bdy
    if b_len_sq < 1e-12:
        return []
    b_len = math.sqrt(b_len_sq)

    supports = []

    # Check columns (vertical projection)
    for col in columns:
        if not floors_overlap(b_floors, col.get("floors", [])):
            continue
        cx, cy = col["grid_x"], col["grid_y"]
        t = ((cx - bx1) * bdx + (cy - by1) * bdy) / b_len_sq
        if t <= 0.02 or t >= 0.98:
            continue
        proj_x = bx1 + t * bdx
        proj_y = by1 + t * bdy
        d = math.hypot(cx - proj_x, cy - proj_y)
        if d <= split_tolerance:
            supports.append((t, round(proj_x, 2), round(proj_y, 2),
                             f"column at ({col['grid_x']},{col['grid_y']})"))

    # Check walls (segment intersection)
    for wall in walls:
        if not floors_overlap(b_floors, wall.get("floors", [])):
            continue
        wx1, wy1 = wall["x1"], wall["y1"]
        wx2, wy2 = wall["x2"], wall["y2"]
        wdx = wx2 - wx1
        wdy = wy2 - wy1
        w_len = math.hypot(wdx, wdy)
        if w_len < 1e-6:
            continue
        dot = abs((bdx * wdx + bdy * wdy) / (b_len * w_len))
        if dot > 0.95:
            continue  # parallel
        result = segment_intersection(bx1, by1, bx2, by2, wx1, wy1, wx2, wy2)
        if result is None:
            continue
        x, y, t_beam, t_wall = result
        if t_beam <= 0.02 or t_beam >= 0.98:
            continue
        supports.append((t_beam, round(x, 2), round(y, 2),
                         f"wall ({wx1},{wy1})-({wx2},{wy2})"))

    # Check major beams (segment intersection)
    for beam in beams:
        if not floors_overlap(b_floors, beam.get("floors", [])):
            continue
        mx1, my1 = beam["x1"], beam["y1"]
        mx2, my2 = beam["x2"], beam["y2"]
        mdx = mx2 - mx1
        mdy = my2 - my1
        m_len = math.hypot(mdx, mdy)
        if m_len < 1e-6:
            continue
        dot = abs((bdx * mdx + bdy * mdy) / (b_len * m_len))
        if dot > 0.95:
            continue  # parallel
        result = segment_intersection(bx1, by1, bx2, by2, mx1, my1, mx2, my2)
        if result is None:
            continue
        x, y, t_sb, t_major = result
        if t_sb <= 0.02 or t_sb >= 0.98:
            continue
        supports.append((t_sb, round(x, 2), round(y, 2),
                         f"beam ({mx1},{my1})-({mx2},{my2})"))

    # Check larger SBs (segment intersection)
    for lsb in larger_sbs:
        if not floors_overlap(b_floors, lsb.get("floors", [])):
            continue
        lx1, ly1 = lsb["x1"], lsb["y1"]
        lx2, ly2 = lsb["x2"], lsb["y2"]
        ldx = lx2 - lx1
        ldy = ly2 - ly1
        l_len = math.hypot(ldx, ldy)
        if l_len < 1e-6:
            continue
        dot = abs((bdx * ldx + bdy * ldy) / (b_len * l_len))
        if dot > 0.95:
            continue  # parallel
        result = segment_intersection(bx1, by1, bx2, by2, lx1, ly1, lx2, ly2)
        if result is None:
            continue
        x, y, t_sb, t_lsb = result
        if t_sb <= 0.02 or t_sb >= 0.98:
            continue
        supports.append((t_sb, round(x, 2), round(y, 2),
                         f"sb ({lx1},{ly1})-({lx2},{ly2})"))

    # Sort by t, deduplicate close points (delta_t < 0.02)
    supports.sort(key=lambda s: s[0])
    deduped = []
    for s in supports:
        if deduped and abs(s[0] - deduped[-1][0]) < 0.02:
            continue
        deduped.append(s)

    return deduped


def split_all_sbs(sb_data, config, grid_data, split_tolerance=0.30):
    """Split all small beams at intermediate supports, processing larger SBs first.

    SB-to-SB rule: ordered by width*depth descending. Larger SBs are processed
    first and become split targets for smaller SBs. Same-size tie-breaking uses
    original array index (earlier = processed first).

    Parameters
    ----------
    sb_data : dict
        Data with "small_beams" list.
    config : dict
        model_config.json with columns, beams, walls.
    grid_data : dict
        Grid data (reserved).
    split_tolerance : float
        Max perpendicular distance for split detection.

    Returns
    -------
    tuple[dict, dict]
        (sb_data_with_split, split_report)
    """
    sbs = sb_data.get("small_beams", [])
    columns = config.get("columns", [])
    walls = config.get("walls", [])
    beams = config.get("beams", [])

    if not sbs:
        return sb_data, {"split_sbs": 0, "new_sbs_from_split": 0,
                         "total_sbs_after_split": 0, "split_details": []}

    # 1. Compute section area for each SB
    areas = [_compute_section_area(sb.get("section", "")) for sb in sbs]

    # 2. Sort by area descending, then by index for tie-breaking
    sorted_indices = sorted(range(len(sbs)), key=lambda i: (-areas[i], i))

    # 3. Process in order
    processed_sbs = []
    split_count = 0
    new_from_split = 0
    split_details = []

    for idx in sorted_indices:
        sb = sbs[idx]
        supports = find_sb_intermediate_supports(
            sb, columns, walls, beams, processed_sbs, split_tolerance)
        if supports:
            sub_sbs = split_beam(sb, supports)
            processed_sbs.extend(sub_sbs)
            split_count += 1
            new_from_split += len(sub_sbs) - 1
            split_details.append({
                "original_index": idx,
                "section": sb.get("section", ""),
                "original_coords": [sb["x1"], sb["y1"], sb["x2"], sb["y2"]],
                "split_points": [(s[1], s[2], s[3]) for s in supports],
                "result_count": len(sub_sbs),
            })
        else:
            processed_sbs.append(sb)

    sb_data["small_beams"] = processed_sbs

    split_report = {
        "split_sbs": split_count,
        "new_sbs_from_split": new_from_split,
        "total_sbs_after_split": len(processed_sbs),
        "split_details": split_details,
    }

    return sb_data, split_report


# ---------------------------------------------------------------------------
# 5. Endpoint clustering
# ---------------------------------------------------------------------------

def cluster_free_endpoints(small_beams, snapped_state, cluster_tolerance=0.30):
    """Cluster free endpoints of half-snapped SBs within tolerance.

    Collects free endpoints from SBs where exactly one endpoint is snapped,
    then groups nearby endpoints (direct radius search, no transitive BFS)
    that share at least one overlapping floor. Moves all members to the
    cluster centroid and marks them as snapped.

    Parameters
    ----------
    small_beams : list[dict]
        The small_beams list (mutated in place).
    snapped_state : list[list[bool]]
        Per-SB [start_snapped, end_snapped] (mutated in place).
    cluster_tolerance : float
        Max distance between endpoints to form a cluster (default 0.30m).

    Returns
    -------
    list[dict]
        Cluster correction records.
    """
    # 1. Collect half-snapped free endpoints
    free_eps = []  # [(sb_idx, ep_idx, x, y, floors)]
    for i, sb in enumerate(small_beams):
        s0, s1 = snapped_state[i]
        if s0 and not s1:
            free_eps.append((i, 1, sb["x2"], sb["y2"], sb.get("floors", [])))
        elif s1 and not s0:
            free_eps.append((i, 0, sb["x1"], sb["y1"], sb.get("floors", [])))

    if len(free_eps) < 2:
        return []

    # 2. Direct radius clustering (no transitive)
    visited = [False] * len(free_eps)
    corrections = []

    for seed_idx in range(len(free_eps)):
        if visited[seed_idx]:
            continue
        seed_sb, seed_ep, sx, sy, s_floors = free_eps[seed_idx]

        # Find all unvisited endpoints within tolerance with floor overlap
        members = [seed_idx]
        for j in range(seed_idx + 1, len(free_eps)):
            if visited[j]:
                continue
            _, _, jx, jy, j_floors = free_eps[j]
            dist = math.hypot(jx - sx, jy - sy)
            if dist <= cluster_tolerance and floors_overlap(s_floors, j_floors):
                members.append(j)

        if len(members) < 2:
            continue

        # 3. Pre-compute ray directions for each member (snapped→free)
        member_rays = []
        for m in members:
            sb_idx, ep_idx, ox, oy, fl = free_eps[m]
            sb = small_beams[sb_idx]
            if ep_idx == 0:
                s_x, s_y = sb["x2"], sb["y2"]  # snapped end
            else:
                s_x, s_y = sb["x1"], sb["y1"]
            rdx = ox - s_x
            rdy = oy - s_y
            rlen = math.hypot(rdx, rdy)
            if rlen > 1e-6:
                member_rays.append((s_x, s_y, rdx / rlen, rdy / rlen))
            else:
                member_rays.append((s_x, s_y, 0, 0))

        # 4. Try ray-ray intersection for non-parallel pairs
        intersection_point = None
        if len(members) == 2:
            r0, r1 = member_rays[0], member_rays[1]
            result = ray_ray_intersection(r0[0], r0[1], r0[2], r0[3],
                                          r1[0], r1[1], r1[2], r1[3])
            if result:
                ix, iy = result
                max_d = max(math.hypot(free_eps[m][2] - ix,
                                       free_eps[m][3] - iy) for m in members)
                if max_d <= cluster_tolerance * 3:
                    intersection_point = (ix, iy)
        elif len(members) >= 3:
            import statistics
            ixs, iys = [], []
            for a in range(len(members)):
                for b in range(a + 1, len(members)):
                    ra, rb = member_rays[a], member_rays[b]
                    result = ray_ray_intersection(
                        ra[0], ra[1], ra[2], ra[3],
                        rb[0], rb[1], rb[2], rb[3])
                    if result:
                        ixs.append(result[0])
                        iys.append(result[1])
            if ixs:
                mid_x = round(statistics.median(ixs), 2)
                mid_y = round(statistics.median(iys), 2)
                max_d = max(math.hypot(free_eps[m][2] - mid_x,
                                       free_eps[m][3] - mid_y) for m in members)
                if max_d <= cluster_tolerance * 3:
                    intersection_point = (mid_x, mid_y)

        if intersection_point:
            cx, cy = intersection_point
            method = "ray_intersection"
        else:
            cx = round(sum(free_eps[m][2] for m in members) / len(members), 2)
            cy = round(sum(free_eps[m][3] for m in members) / len(members), 2)
            method = "centroid_projection"

        # 5. Move each member to target PROJECTED onto its SB axis
        member_details = []
        for m in members:
            visited[m] = True
            sb_idx, ep_idx, ox, oy, fl = free_eps[m]
            sb = small_beams[sb_idx]

            # SB direction from snapped endpoint to free endpoint
            if ep_idx == 0:  # free = start, snapped = end
                sx, sy = sb["x2"], sb["y2"]
            else:            # free = end, snapped = start
                sx, sy = sb["x1"], sb["y1"]

            dx_sb = ox - sx
            dy_sb = oy - sy
            length = math.hypot(dx_sb, dy_sb)
            if length > 1e-6:
                dx_sb /= length
                dy_sb /= length
                # Project centroid onto SB direction from snapped endpoint
                dot = (cx - sx) * dx_sb + (cy - sy) * dy_sb
                proj_x = round(sx + dot * dx_sb, 2)
                proj_y = round(sy + dot * dy_sb, 2)
            else:
                proj_x, proj_y = cx, cy

            d = math.hypot(ox - proj_x, oy - proj_y)
            if ep_idx == 0:
                sb["x1"], sb["y1"] = proj_x, proj_y
            else:
                sb["x2"], sb["y2"] = proj_x, proj_y
            snapped_state[sb_idx][ep_idx] = True
            member_details.append({
                "sb_index": sb_idx,
                "endpoint": "start" if ep_idx == 0 else "end",
                "original_coord": [ox, oy],
                "projected_coord": [proj_x, proj_y],
                "snap_distance": round(d, 4),
            })

        corrections.append({
            "method": method,
            "target": [cx, cy],
            "centroid": [cx, cy],
            "member_count": len(members),
            "members": member_details,
        })

    return corrections


# ---------------------------------------------------------------------------
# 6. Main validation
# ---------------------------------------------------------------------------

def validate_small_beams(sb_data, config, grid_data, tolerance=1.0,
                         split_tolerance=0.30, no_split=False,
                         angle_threshold_deg=5.0, no_angle_correct=False,
                         cluster_tolerance=0.30, no_cluster=False):
    """Validate and auto-snap small beam endpoints.

    Pipeline order:
      Step 0: Angle correction (correct near-orthogonal SBs)
      Step 1-3: 3-round snap with post-round clustering
      Step 4: Post-validation (zero-length, direction changes, unsnapped)
      Step 5: SB splitting (at columns, walls, major beams, larger SBs)

    Parameters
    ----------
    sb_data : dict
        Data with "small_beams" list from sb_elements_aligned.json.
    config : dict
        model_config.json with columns, beams, walls.
    grid_data : dict
        Grid data with "x" and "y" lists.
    tolerance : float
        Maximum snap distance in meters (default 1.0).
    split_tolerance : float
        Max perpendicular distance for split detection (default 0.30m).
    no_split : bool
        If True, skip splitting step.
    angle_threshold_deg : float
        Max angle deviation to correct (default 5.0 degrees).
    no_angle_correct : bool
        If True, skip angle correction step.
    cluster_tolerance : float
        Max distance for clustering free endpoints of half-snapped SBs
        (default 0.30m).
    no_cluster : bool
        If True, skip endpoint clustering.

    Returns
    -------
    tuple[dict, dict]
        (validated_sb_data, report_dict)
    """
    # Deep copy to avoid mutating originals
    sb_data = json.loads(json.dumps(sb_data))

    # --- Step 0: Angle correction ---
    angle_corrections = []
    if not no_angle_correct:
        sb_data, angle_corrections = correct_sb_angles(
            sb_data, grid_data, angle_threshold_deg)

    small_beams = sb_data.get("small_beams", [])
    n = len(small_beams)

    corrections = []
    warnings = []

    if n == 0:
        report = {
            "total_sbs": 0,
            "total_endpoints": 0,
            "snapped_endpoints": 0,
            "warning_endpoints": 0,
            "max_snap_distance": 0,
            "avg_snap_distance": 0,
            "corrections": [],
            "warnings": [],
            "angle_corrections": angle_corrections,
            "angle_corrected_sbs": len(angle_corrections),
            "clustered_endpoints": 0,
            "cluster_count": 0,
            "split_sbs": 0,
            "new_sbs_from_split": 0,
            "total_sbs_after_split": 0,
            "split_details": [],
        }
        return sb_data, report

    # Record original orientations (after angle correction, before snap)
    orig_directions = []
    for sb in small_beams:
        dx = abs(sb["x2"] - sb["x1"])
        dy = abs(sb["y2"] - sb["y1"])
        if dx < 0.01:
            orig_directions.append("vertical")
        elif dy < 0.01:
            orig_directions.append("horizontal")
        else:
            orig_directions.append("diagonal")

    # Build targets from model_config (including major beams from the start)
    grid_targets, element_targets = build_sb_targets(config, grid_data)
    base_targets = grid_targets + element_targets

    # Track snap state per endpoint
    snapped_state = [[False, False] for _ in range(n)]

    # SB segment targets (added after each round)
    sb_snap_targets = []

    # --- Helper: snap one round ---
    def _snap_round(targets):
        count = 0
        for i in range(n):
            sb = small_beams[i]
            floors = sb.get("floors", [])
            # Compute SB direction unit vector
            sb_dx = sb["x2"] - sb["x1"]
            sb_dy = sb["y2"] - sb["y1"]
            sb_len = math.hypot(sb_dx, sb_dy)
            if sb_len < 1e-6:
                continue  # zero-length SB, skip
            sb_dx /= sb_len
            sb_dy /= sb_len

            for ep in range(2):
                if snapped_state[i][ep]:
                    continue
                if ep == 0:
                    px, py = sb["x1"], sb["y1"]
                else:
                    px, py = sb["x2"], sb["y2"]

                result = snap_sb_by_ray(px, py, sb_dx, sb_dy,
                                        floors, targets, tolerance,
                                        grid_data)
                if result:
                    nx, ny, d, target_info = result

                    if target_info.startswith("grid_intersection"):
                        target_type = "grid_intersection"
                    elif target_info.startswith("column"):
                        target_type = "column"
                    elif target_info.startswith("segment"):
                        target_type = "segment"
                    else:
                        target_type = "other"

                    corrections.append({
                        "sb_index": i,
                        "section": sb.get("section", ""),
                        "floors": sb.get("floors", []),
                        "endpoint": "start" if ep == 0 else "end",
                        "original_coord": [px, py],
                        "corrected_coord": [nx, ny],
                        "snap_distance": round(d, 4),
                        "target_type": target_type,
                        "target_label": target_info,
                    })

                    if ep == 0:
                        sb["x1"], sb["y1"] = nx, ny
                    else:
                        sb["x2"], sb["y2"] = nx, ny
                    snapped_state[i][ep] = True
                    count += 1
        return count

    def _add_fully_snapped_sbs():
        added = 0
        for i in range(n):
            if snapped_state[i][0] and snapped_state[i][1]:
                sb = small_beams[i]
                already = any(
                    t.x1 == sb["x1"] and t.y1 == sb["y1"] and
                    t.x2 == sb["x2"] and t.y2 == sb["y2"]
                    for t in sb_snap_targets)
                if not already:
                    sb_snap_targets.append(SnapTarget(
                        "segment",
                        sb["x1"], sb["y1"],
                        sb["x2"], sb["y2"],
                        sb.get("floors", [])))
                    added += 1
        return added

    all_cluster_corrections = []

    def _post_round_cluster():
        """After each snap round: promote fully-snapped → cluster → promote again."""
        _add_fully_snapped_sbs()
        if not no_cluster:
            cc = cluster_free_endpoints(small_beams, snapped_state, cluster_tolerance)
            all_cluster_corrections.extend(cc)
            _add_fully_snapped_sbs()

    # Round 1: grid + columns + walls + major beams
    _snap_round(base_targets)
    _post_round_cluster()

    # Round 2: + snapped SBs
    _snap_round(base_targets + sb_snap_targets)
    _post_round_cluster()

    # Round 3: final pass
    _snap_round(base_targets + sb_snap_targets)
    _post_round_cluster()

    # --- Post-validation: unsnapped endpoints ---
    all_targets = base_targets + sb_snap_targets
    for i in range(n):
        sb = small_beams[i]
        for ep in range(2):
            if snapped_state[i][ep]:
                continue
            if ep == 0:
                px, py = sb["x1"], sb["y1"]
            else:
                px, py = sb["x2"], sb["y2"]

            best_dist = float("inf")
            best_info = "none"
            for t in all_targets:
                nx, ny, d = t.nearest(px, py)
                if d < best_dist:
                    best_dist = d
                    best_info = f"target at ({round(nx, 2)}, {round(ny, 2)})"

            warnings.append({
                "sb_index": i,
                "section": sb.get("section", ""),
                "floors": sb.get("floors", []),
                "endpoint": "start" if ep == 0 else "end",
                "coord": [px, py],
                "nearest_target": best_info,
                "nearest_distance": round(best_dist, 4),
                "message": f"No target within {tolerance}m tolerance",
            })

    # --- Post-validation: zero-length check ---
    for i in range(n):
        sb = small_beams[i]
        if abs(sb["x1"] - sb["x2"]) < 0.005 and abs(sb["y1"] - sb["y2"]) < 0.005:
            warnings.append({
                "sb_index": i,
                "section": sb.get("section", ""),
                "floors": sb.get("floors", []),
                "endpoint": "both",
                "coord": [sb["x1"], sb["y1"]],
                "nearest_target": "self",
                "nearest_distance": 0,
                "message": "Zero-length SB after snap — both endpoints at same location",
            })

    # --- Post-validation: direction change check ---
    for i in range(n):
        sb = small_beams[i]
        dx = abs(sb["x2"] - sb["x1"])
        dy = abs(sb["y2"] - sb["y1"])
        if dx < 0.01:
            new_dir = "vertical"
        elif dy < 0.01:
            new_dir = "horizontal"
        else:
            new_dir = "diagonal"

        if orig_directions[i] != new_dir and orig_directions[i] != "diagonal":
            warnings.append({
                "sb_index": i,
                "section": sb.get("section", ""),
                "floors": sb.get("floors", []),
                "endpoint": "both",
                "coord": [sb["x1"], sb["y1"]],
                "nearest_target": "self",
                "nearest_distance": 0,
                "message": (f"Direction changed from {orig_directions[i]} "
                            f"to {new_dir} after snap"),
            })

    # --- Step 5: Splitting ---
    split_report = {
        "split_sbs": 0,
        "new_sbs_from_split": 0,
        "total_sbs_after_split": n,
        "split_details": [],
    }
    if not no_split:
        sb_data, split_report = split_all_sbs(
            sb_data, config, grid_data, split_tolerance)

    # --- Build report ---
    snap_distances = [c["snap_distance"] for c in corrections]
    unsnapped_count = sum(
        1 for w in warnings if w["message"].startswith("No target"))
    clustered_eps = sum(c["member_count"] for c in all_cluster_corrections)
    report = {
        "total_sbs": n,
        "total_endpoints": n * 2,
        "snapped_endpoints": len(corrections),
        "warning_endpoints": unsnapped_count,
        "max_snap_distance": max(snap_distances) if snap_distances else 0,
        "avg_snap_distance": (round(sum(snap_distances) / len(snap_distances), 4)
                              if snap_distances else 0),
        "corrections": corrections,
        "warnings": warnings,
        "angle_corrections": angle_corrections,
        "angle_corrected_sbs": len(angle_corrections),
        "clustered_endpoints": clustered_eps,
        "cluster_count": len(all_cluster_corrections),
        **split_report,
    }

    return sb_data, report


# ---------------------------------------------------------------------------
# 6. CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Validate and auto-snap Phase 2 small beam endpoints")
    parser.add_argument("--sb-elements", required=True,
                        help="Path to sb_elements_aligned.json")
    parser.add_argument("--config", required=True,
                        help="Path to model_config.json")
    parser.add_argument("--grid-data", required=True,
                        help="Path to grid_data.json")
    parser.add_argument("--output", required=True,
                        help="Path for validated SB output")
    parser.add_argument("--tolerance", type=float, default=1.0,
                        help="Snap tolerance in meters (default: 1.0)")
    parser.add_argument("--angle-threshold", type=float, default=5.0,
                        help="Angle correction threshold in degrees (default: 5.0)")
    parser.add_argument("--no-angle-correct", action="store_true",
                        help="Skip angle correction step")
    parser.add_argument("--split-tolerance", type=float, default=0.30,
                        help="Max perpendicular distance for SB splitting "
                        "(default: 0.30m)")
    parser.add_argument("--no-split", action="store_true",
                        help="Skip SB splitting step")
    parser.add_argument("--cluster-tolerance", type=float, default=0.30,
                        help="Max distance for clustering free endpoints of "
                        "half-snapped SBs (default: 0.30m)")
    parser.add_argument("--no-cluster", action="store_true",
                        help="Skip endpoint clustering step")
    parser.add_argument("--report", default=None,
                        help="Path for validation report JSON (optional)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing output")
    args = parser.parse_args()

    # Load inputs
    with open(args.sb_elements, encoding="utf-8") as f:
        sb_data = json.load(f)
    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)
    with open(args.grid_data, encoding="utf-8") as f:
        grid_data = json.load(f)
    grid_data = _normalize_grid_data_for_bv(grid_data)

    n_sbs = len(sb_data.get("small_beams", []))
    n_cols = len(config.get("columns", []))
    n_beams = len(config.get("beams", []))
    n_walls = len(config.get("walls", []))
    x_grids = len(grid_data.get("x", []))
    y_grids = len(grid_data.get("y", []))

    print(f"SB elements loaded: {args.sb_elements}")
    print(f"  small_beams: {n_sbs}")
    print(f"Config loaded: {args.config}")
    print(f"  columns: {n_cols}, beams: {n_beams}, walls: {n_walls}")
    print(f"Grid data loaded: {args.grid_data}")
    print(f"  x-grids: {x_grids}, y-grids: {y_grids}")
    print(f"  grid intersections: {x_grids * y_grids}")
    print(f"  tolerance: {args.tolerance}m")
    if not args.no_angle_correct:
        print(f"  angle threshold: {args.angle_threshold}\u00b0")
    if not args.no_split:
        print(f"  split tolerance: {args.split_tolerance}m")
    if not args.no_cluster:
        print(f"  cluster tolerance: {args.cluster_tolerance}m")

    if n_sbs == 0:
        print("\nNo small beams to validate.")
        if not args.dry_run:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(sb_data, f, ensure_ascii=False, indent=2)
            print(f"Output written to: {args.output}")
        return

    # Run validation
    validated, report = validate_small_beams(
        sb_data, config, grid_data,
        tolerance=args.tolerance,
        split_tolerance=args.split_tolerance,
        no_split=args.no_split,
        angle_threshold_deg=args.angle_threshold,
        no_angle_correct=args.no_angle_correct,
        cluster_tolerance=args.cluster_tolerance,
        no_cluster=args.no_cluster,
    )

    # Print summary
    print(f"\n--- SB Validation Summary ---")
    print(f"  Total small beams: {report['total_sbs']}")
    print(f"  Total endpoints: {report['total_endpoints']}")
    print(f"  Snapped endpoints: {report['snapped_endpoints']}")
    print(f"  Warning endpoints: {report['warning_endpoints']}")
    if report["snapped_endpoints"] > 0:
        print(f"  Max snap distance: {report['max_snap_distance']:.4f}m")
        print(f"  Avg snap distance: {report['avg_snap_distance']:.4f}m")

    if report.get("angle_corrections"):
        print(f"  Angle corrections: {report['angle_corrected_sbs']}")

    if report.get("cluster_count", 0) > 0:
        print(f"  Endpoint clusters: {report['cluster_count']} "
              f"({report['clustered_endpoints']} endpoints)")

    if report.get("split_sbs", 0) > 0:
        print(f"  Split SBs: {report['split_sbs']} \u2192 "
              f"{report['new_sbs_from_split']} new sub-SBs "
              f"(total after split: {report['total_sbs_after_split']})")

    if report["warnings"]:
        print(f"\nWARNINGS ({len(report['warnings'])}):")
        for w in report["warnings"]:
            ep_label = w["endpoint"]
            print(f"  SB[{w['sb_index']}] {w.get('section', '')} {ep_label}: "
                  f"{w['message']} "
                  f"(coord={w['coord']}, nearest={w.get('nearest_target', '')}, "
                  f"d={w.get('nearest_distance', '')}m)")

    if args.dry_run:
        print(f"\n[DRY RUN] No output written.")
        if report["corrections"]:
            print(f"\nSnap corrections preview ({len(report['corrections'])}):")
            for c in report["corrections"]:
                print(f"  SB[{c['sb_index']}] {c['section']} {c['endpoint']}: "
                      f"({c['original_coord'][0]}, {c['original_coord'][1]}) -> "
                      f"({c['corrected_coord'][0]}, {c['corrected_coord'][1]}) "
                      f"d={c['snap_distance']}m [{c['target_label']}]")
        if report.get("angle_corrections"):
            print(f"\nAngle corrections preview "
                  f"({len(report['angle_corrections'])}):")
            for a in report["angle_corrections"]:
                print(f"  SB[{a['index']}] {a['section']}: "
                      f"{a['angle_deg']}\u00b0 \u2192 {a['correction_axis']} "
                      f"[{a['target_grid_label']}] "
                      f"\u0394={a['displacement']}m")
        if report.get("split_details"):
            print(f"\nSplit preview ({len(report['split_details'])}):")
            for s in report["split_details"]:
                pts = ", ".join(f"({p[0]},{p[1]})" for p in s["split_points"])
                print(f"  SB[{s['original_index']}] {s['section']}: "
                      f"\u2192 {s['result_count']} segments at [{pts}]")
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(validated, f, ensure_ascii=False, indent=2)
        print(f"\nValidated SB elements written to: {args.output}")

        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"Validation report written to: {args.report}")


if __name__ == "__main__":
    main()
