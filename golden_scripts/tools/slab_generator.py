"""
Slab Generator — Pure-generate slab polygon generation from beam intersections.

Reads a config.json (containing all beams including small beams) and
generates slab polygons by walking along beams clockwise through exact
intersection points.  No space division, no node clustering.

Algorithm:
  Step 1: Collect all structural segments (beams, small_beams, walls)
  Step 2: Compute ALL pairwise intersections (exact) + T-junctions (15cm)
  Step 3: Build beam segments between consecutive intersection points
  Step 4: Build adjacency at each intersection point (angle-sorted)
  Step 5: Walk clockwise to generate slab polygons
  Step 6: Filter (outline, region, min area)
  Step 7: Assign floors and sections

Usage:
    python -m golden_scripts.tools.slab_generator \
        --config merged_config.json \
        --output final_config.json

    # Custom thicknesses:
    python -m golden_scripts.tools.slab_generator \
        --config merged_config.json \
        --slab-thickness 15 \
        --raft-thickness 100 \
        --output final_config.json

    # Preview without writing:
    python -m golden_scripts.tools.slab_generator \
        --config merged_config.json \
        --output final_config.json \
        --dry-run
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

from golden_scripts.constants import expand_floor_range, normalize_stories_order, is_substructure_story
from golden_scripts.tools.config_snap import segment_intersection
from golden_scripts.tools.geometry import point_in_polygon as _pip_geometry


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

T_JUNCTION_TOL = 0.15    # 15cm: snap endpoint to nearby beam interior
MIN_FACE_AREA = 0.25     # m²: discard faces smaller than this
COORD_DECIMALS = 4       # round to 0.1mm for deterministic point identity
DEDUP_DIST = 0.005       # 5mm: minimum distance between consecutive splits


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _coord_key(x, y):
    """Deterministic point identity — no clustering, no drift."""
    return (round(x, COORD_DECIMALS), round(y, COORD_DECIMALS))


def _project_point_on_segment(px, py, ax, ay, bx, by):
    """Project point (px, py) onto segment (ax, ay)→(bx, by).

    Returns (t, proj_x, proj_y, distance).
    """
    dx, dy = bx - ax, by - ay
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-12:
        return 0.5, ax, ay, math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / len_sq
    t_clamped = max(0.0, min(1.0, t))
    proj_x = ax + t_clamped * dx
    proj_y = ay + t_clamped * dy
    dist = math.hypot(px - proj_x, py - proj_y)
    return t_clamped, proj_x, proj_y, dist


# ---------------------------------------------------------------------------
# Step 1-2: Compute intersections
# ---------------------------------------------------------------------------

def compute_intersections(segments, t_junction_tol=T_JUNCTION_TOL):
    """Compute all intersection and T-junction points along each segment.

    For each segment, returns an ordered list of split points (including
    endpoints) with exact analytical coordinates.

    T-junction: if a segment endpoint is within *t_junction_tol* of another
    segment's interior (but does not intersect exactly), the endpoint is
    snapped to the projection point on that segment.

    Args:
        segments: list of (x1, y1, x2, y2, floors_set)
        t_junction_tol: max perpendicular distance for T-junction snap

    Returns:
        seg_points: dict[seg_idx] → sorted list of (t, x, y)
    """
    n = len(segments)
    # Interior intersection points per segment: [(t, x, y), ...]
    raw_splits = {i: [] for i in range(n)}
    # Endpoint snaps from T-junctions: (seg_idx, 0_or_1) → (x, y)
    endpoint_snaps = {}

    # --- 1. Exact pairwise intersections ---
    for i in range(n):
        ax1, ay1, ax2, ay2, _ = segments[i]
        for j in range(i + 1, n):
            bx1, by1, bx2, by2, _ = segments[j]
            result = segment_intersection(ax1, ay1, ax2, ay2,
                                          bx1, by1, bx2, by2)
            if result is None:
                continue
            x, y, ta, tb = result
            ta = max(0.0, min(1.0, ta))
            tb = max(0.0, min(1.0, tb))
            raw_splits[i].append((ta, x, y))
            raw_splits[j].append((tb, x, y))

    # --- 2. T-junction detection (imperfect endpoints near other beams) ---
    for i in range(n):
        x1, y1, x2, y2, _ = segments[i]
        for end_idx, (px, py) in enumerate([(x1, y1), (x2, y2)]):
            t_end = float(end_idx)  # 0.0 or 1.0
            # Skip if this endpoint already has a nearby crossing
            has_nearby = any(
                abs(t - t_end) < 0.05
                for t, _, _ in raw_splits[i]
            )
            if has_nearby:
                continue

            # Find closest segment interior within tolerance
            best_dist = t_junction_tol
            best_match = None
            for j in range(n):
                if i == j:
                    continue
                bx1, by1, bx2, by2, _ = segments[j]
                t_j, proj_x, proj_y, dist = _project_point_on_segment(
                    px, py, bx1, by1, bx2, by2)
                if dist < best_dist and 0.01 < t_j < 0.99:
                    best_dist = dist
                    best_match = (j, t_j, proj_x, proj_y)

            if best_match is not None:
                j, t_j, proj_x, proj_y = best_match
                raw_splits[j].append((t_j, proj_x, proj_y))
                endpoint_snaps[(i, end_idx)] = (proj_x, proj_y)

    # --- 3. Build final sorted points per segment (endpoints + splits) ---
    seg_points = {}
    for i, (x1, y1, x2, y2, _) in enumerate(segments):
        # Use snapped endpoints if available
        sx, sy = endpoint_snaps.get((i, 0), (x1, y1))
        ex, ey = endpoint_snaps.get((i, 1), (x2, y2))

        points = [(0.0, sx, sy)]
        for t, x, y in raw_splits[i]:
            # Only interior points (endpoints handled above)
            if 0.001 < t < 0.999:
                points.append((t, x, y))
        points.append((1.0, ex, ey))

        # Sort by parameter t
        points.sort(key=lambda p: p[0])

        # Deduplicate consecutive points too close together
        deduped = [points[0]]
        for p in points[1:]:
            dist = math.hypot(p[1] - deduped[-1][1], p[2] - deduped[-1][2])
            if dist > DEDUP_DIST:
                deduped.append(p)

        seg_points[i] = deduped

    return seg_points


# ---------------------------------------------------------------------------
# Step 3: Build beam segments
# ---------------------------------------------------------------------------

def build_beam_segments(segments, seg_points):
    """Create directed segments between consecutive intersection points.

    Returns list of (coord_key_start, coord_key_end, floors_set).
    """
    beam_segments = []
    for i, (x1, y1, x2, y2, floors) in enumerate(segments):
        points = seg_points[i]
        for k in range(len(points) - 1):
            _, sx, sy = points[k]
            _, ex, ey = points[k + 1]
            ks = _coord_key(sx, sy)
            ke = _coord_key(ex, ey)
            if ks != ke:
                beam_segments.append((ks, ke, floors))
    return beam_segments


# ---------------------------------------------------------------------------
# Step 4: Build adjacency
# ---------------------------------------------------------------------------

def build_point_adjacency(beam_segments):
    """Build angle-sorted adjacency at each intersection point.

    Returns:
        adj: dict[coord_key] → [neighbor_key, ...] sorted by angle
        edge_floors: dict[(min_key, max_key)] → floors_set
    """
    adj_set = {}  # coord_key → set of neighbor keys
    edge_floors = {}

    for ks, ke, floors in beam_segments:
        adj_set.setdefault(ks, set()).add(ke)
        adj_set.setdefault(ke, set()).add(ks)
        ekey = (min(ks, ke), max(ks, ke))
        if ekey in edge_floors:
            edge_floors[ekey] |= floors
        else:
            edge_floors[ekey] = set(floors)

    # Sort neighbors by angle at each node
    adj = {}
    for pt, neighbors in adj_set.items():
        px, py = pt
        nb_list = list(neighbors)
        nb_list.sort(key=lambda nb: math.atan2(nb[1] - py, nb[0] - px))
        adj[pt] = nb_list

    return adj, edge_floors


# ---------------------------------------------------------------------------
# Step 5: Walk clockwise to generate slab polygons
# ---------------------------------------------------------------------------

def walk_slab_polygons(adj):
    """Walk along beams clockwise to generate slab polygons.

    For each unvisited directed half-edge (A→B), at B find the next
    edge by taking the smallest CW turn from the incoming direction.
    Continue until returning to start.

    Returns list of polygons, each = [coord_key, ...] (ordered vertices).
    """
    used = set()  # visited half-edges: (key_from, key_to)
    polygons = []

    for start_u in adj:
        for start_v in adj[start_u]:
            if (start_u, start_v) in used:
                continue

            face = []
            u, v = start_u, start_v
            max_steps = len(adj) * 2 + 10

            for _ in range(max_steps):
                if (u, v) in used:
                    break
                used.add((u, v))
                face.append(u)

                neighbors = adj.get(v, [])
                if not neighbors:
                    break

                # Incoming angle: direction from v back to u
                vx, vy = v
                ux, uy = u
                incoming_angle = math.atan2(uy - vy, ux - vx)

                # Find CW-nearest neighbor (smallest positive CW rotation)
                best_w = None
                best_delta = float("inf")
                for w in neighbors:
                    if w == u and len(neighbors) > 1:
                        continue  # avoid backtrack on degree≥2 nodes
                    wx, wy = w
                    outgoing_angle = math.atan2(wy - vy, wx - vx)
                    delta = incoming_angle - outgoing_angle
                    if delta <= 0:
                        delta += 2 * math.pi
                    if delta < best_delta:
                        best_delta = delta
                        best_w = w

                if best_w is None:
                    break

                u, v = v, best_w
                if u == start_u and v == start_v:
                    break

            if len(face) >= 3:
                polygons.append(face)

    return polygons


# ---------------------------------------------------------------------------
# Geometry utilities
# ---------------------------------------------------------------------------

def face_area_signed(polygon):
    """Compute signed area of a polygon. Positive = CCW, negative = CW.

    polygon: list of (x, y) tuples.
    """
    n = len(polygon)
    area = 0.0
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def face_centroid(polygon):
    """Compute centroid of a polygon.

    polygon: list of (x, y) tuples.
    """
    n = len(polygon)
    cx = sum(x for x, y in polygon) / n
    cy = sum(y for x, y in polygon) / n
    return cx, cy


def point_in_polygon(px, py, polygon):
    """Ray casting point-in-polygon test (delegates to geometry.py)."""
    return _pip_geometry(px, py, polygon)


# ---------------------------------------------------------------------------
# Step 6: Filter
# ---------------------------------------------------------------------------

def filter_slabs(polygons, config, range_floors=None):
    """Filter polygons to keep only valid slab regions.

    Removes:
    - Outer boundary (CW winding = negative area)
    - Largest face (safety check)
    - Faces with centroid outside building_outline
    - Faces in slab_region_matrix no-slab zones
    - Degenerate faces (area < MIN_FACE_AREA)

    Args:
        range_floors: Optional set/list of floor names for this range.
            If ALL floors are substructure, uses substructure_outline instead
            of building_outline for centroid filtering.

    Returns list of (polygon, abs_area) tuples.
    """
    if not polygons:
        return []

    sub_outline = config.get("substructure_outline")
    sup_outline = config.get("building_outline")

    if range_floors and sub_outline and all(is_substructure_story(f) for f in range_floors):
        outline = sub_outline
    else:
        outline = sup_outline
    outline_poly = [(pt[0], pt[1]) for pt in outline] if outline else None

    valid = []
    for poly in polygons:
        area = face_area_signed(poly)
        abs_area = abs(area)

        # Skip CW faces (negative area = exterior)
        if area < 0:
            continue

        # Skip degenerate
        if abs_area < MIN_FACE_AREA:
            continue

        # Check centroid inside building outline
        cx, cy = face_centroid(poly)
        if outline_poly and not point_in_polygon(cx, cy, outline_poly):
            continue

        # Check slab_region_matrix
        srm = config.get("slab_region_matrix")
        if srm and not _in_slab_region(cx, cy, srm, config):
            continue

        valid.append((poly, abs_area))

    return valid


def _in_slab_region(cx, cy, srm, config):
    """Check if point is in a slab region according to slab_region_matrix."""
    if isinstance(srm, list):
        for entry in srm:
            if isinstance(entry, dict):
                if entry.get("build") is False or entry.get("建板") is False:
                    bounds = entry.get("bounds")
                    if bounds and len(bounds) >= 4:
                        x_min, y_min, x_max, y_max = bounds[:4]
                        if x_min <= cx <= x_max and y_min <= cy <= y_max:
                            return False
    return True


# ---------------------------------------------------------------------------
# Floor grouping (per-floor slab generation)
# ---------------------------------------------------------------------------

def group_segments_by_floor(segments):
    """Group floors that share identical segment geometry.

    Floors that see exactly the same set of segment coordinates are grouped
    together, allowing per-group slab generation instead of mixing all floors
    into one 2D plane.

    Args:
        segments: list of (x1, y1, x2, y2, floors_set)

    Returns list of (frozenset_of_floors, segment_list) tuples.
    """
    all_floors = set()
    for _, _, _, _, floors in segments:
        all_floors |= floors

    if not all_floors:
        return [(frozenset(), segments)]

    # For each floor, compute which segment geometries are present
    floor_to_seg_keys = {}
    for floor in all_floors:
        seg_keys = set()
        for x1, y1, x2, y2, floors in segments:
            if floor in floors:
                k1 = _coord_key(x1, y1)
                k2 = _coord_key(x2, y2)
                seg_keys.add((min(k1, k2), max(k1, k2)))
        floor_to_seg_keys[floor] = frozenset(seg_keys)

    # Group floors with identical segment key sets
    key_to_floors = {}
    for floor, seg_key_set in floor_to_seg_keys.items():
        if seg_key_set not in key_to_floors:
            key_to_floors[seg_key_set] = set()
        key_to_floors[seg_key_set].add(floor)

    # For each group, collect actual segments (deduplicated)
    result = []
    for seg_key_set, floor_group in key_to_floors.items():
        fs = frozenset(floor_group)
        group_segments = []
        seen = set()
        for x1, y1, x2, y2, floors in segments:
            if floors & fs:
                k1 = _coord_key(x1, y1)
                k2 = _coord_key(x2, y2)
                seg_id = (min(k1, k2), max(k1, k2))
                if seg_id not in seen:
                    seen.add(seg_id)
                    group_segments.append((x1, y1, x2, y2, fs))
        result.append((fs, group_segments))

    return result


# ---------------------------------------------------------------------------
# Per-slide floor range support (replaces group_segments_by_floor for 共構)
# ---------------------------------------------------------------------------

def parse_slide_floor_ranges(ranges_str):
    """Parse semicolon-separated floor ranges into (label, frozenset) pairs.

    Input:  "B3F; B2F~B1F; 1F~2F; 3F~14F; R1F~R3F"
    Output: [("B3F", frozenset({"B3F"})),
             ("B2F~B1F", frozenset({"B2F","B1F"})), ...]

    Raises ValueError on overlapping floors across ranges.
    """
    if not ranges_str or not ranges_str.strip():
        return []

    result = []
    seen_floors = {}  # floor -> range_label for overlap detection

    for part in ranges_str.split(";"):
        part = part.strip()
        if not part:
            continue
        floors = expand_floor_range(part)
        floor_set = frozenset(floors)

        # Check for overlaps
        for f in floors:
            if f in seen_floors:
                raise ValueError(
                    f"Floor '{f}' appears in both '{seen_floors[f]}' and "
                    f"'{part}' — ranges must not overlap")
            seen_floors[f] = part

        result.append((part, floor_set))

    return result


def filter_segments_by_range(segments, floor_set):
    """Filter segments whose floors intersect with floor_set.

    Returns new segments with floors narrowed to the intersection.
    """
    filtered = []
    for x1, y1, x2, y2, floors in segments:
        overlap = floors & floor_set
        if overlap:
            filtered.append((x1, y1, x2, y2, overlap))
    return filtered


def write_range_debug(debug_dir, range_label, segments, polygons_raw,
                      polygons_filtered, slabs, slab_zones=None):
    """Write per-range debug output files.

    Output:
        {debug_dir}/{range_label}/
        ├── segments.json
        ├── polygons_raw.json
        ├── polygons_filtered.json
        ├── slabs.json
        └── slabs.png  (if matplotlib available)

    Args:
        slab_zones: Optional list of slab zone dicts with "section" and
            "color_hex" fields. When provided, slabs.png uses PPT legend
            colors instead of the default palette.
    """
    range_dir = Path(debug_dir) / range_label
    range_dir.mkdir(parents=True, exist_ok=True)

    # segments.json
    seg_data = []
    for x1, y1, x2, y2, floors in segments:
        seg_data.append({
            "x1": round(x1, 4), "y1": round(y1, 4),
            "x2": round(x2, 4), "y2": round(y2, 4),
            "floors": sorted(floors),
        })
    with open(range_dir / "segments.json", "w", encoding="utf-8") as f:
        json.dump(seg_data, f, ensure_ascii=False, indent=2)

    # polygons_raw.json
    raw_data = []
    for poly in polygons_raw:
        raw_data.append([[round(x, 4), round(y, 4)] for x, y in poly])
    with open(range_dir / "polygons_raw.json", "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)

    # polygons_filtered.json
    filt_data = []
    for poly, area in polygons_filtered:
        filt_data.append({
            "corners": [[round(x, 4), round(y, 4)] for x, y in poly],
            "area": round(area, 2),
        })
    with open(range_dir / "polygons_filtered.json", "w", encoding="utf-8") as f:
        json.dump(filt_data, f, ensure_ascii=False, indent=2)

    # slabs.json
    with open(range_dir / "slabs.json", "w", encoding="utf-8") as f:
        json.dump(slabs, f, ensure_ascii=False, indent=2)

    # slabs.png (guarded import)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(1, 1, figsize=(12, 10))
        ax.set_aspect("equal")
        ax.set_title(f"Slabs: {range_label} ({len(slabs)} slabs)")

        # Draw segments
        for x1, y1, x2, y2, _ in segments:
            ax.plot([x1, x2], [y1, y2], "k-", linewidth=0.5, alpha=0.3)

        # Build section → RGB from slab_zones PPT legend colors
        section_colors = {}
        if slab_zones:
            for zone in slab_zones:
                sec = zone.get("section", "")
                hex_c = zone.get("color_hex", "")
                if sec and hex_c and len(hex_c) >= 6 and sec not in section_colors:
                    section_colors[sec] = (int(hex_c[0:2], 16) / 255,
                                           int(hex_c[2:4], 16) / 255,
                                           int(hex_c[4:6], 16) / 255)
        fallback_colors = plt.cm.Set3.colors

        # Draw slab polygons with fill
        for idx, slab in enumerate(slabs):
            corners = slab["corners"]
            xs = [c[0] for c in corners] + [corners[0][0]]
            ys = [c[1] for c in corners] + [corners[0][1]]
            section = slab.get("section", "")
            color = section_colors.get(section,
                                       fallback_colors[idx % len(fallback_colors)])
            ax.fill(xs, ys, alpha=0.3, color=color)
            ax.plot(xs, ys, "-", linewidth=0.8, color=color)
            cx = sum(c[0] for c in corners) / len(corners)
            cy = sum(c[1] for c in corners) / len(corners)
            ax.text(cx, cy, section, ha="center", va="center", fontsize=6)

        # Legend: section → color
        import matplotlib.patches as mpatches
        legend_handles = []
        seen_sections = set()
        for slab in slabs:
            sec = slab.get("section", "")
            if sec and sec not in seen_sections:
                seen_sections.add(sec)
                c = section_colors.get(sec, fallback_colors[0])
                legend_handles.append(
                    mpatches.Patch(facecolor=c, alpha=0.3, edgecolor=c,
                                   label=sec))
        if legend_handles:
            ax.legend(handles=legend_handles, loc="upper left", fontsize=7,
                      framealpha=0.9)

        ax.grid(True, alpha=0.2)
        fig.tight_layout()
        fig.savefig(range_dir / "slabs.png", dpi=120)
        plt.close(fig)
    except ImportError:
        pass  # matplotlib not available

    print(f"    Debug output written to: {range_dir}")


# ---------------------------------------------------------------------------
# Step 7: Floor assignment
# ---------------------------------------------------------------------------

def assign_floors_to_slabs(valid_faces, edge_floors, config):
    """Assign floors to each slab polygon based on boundary edge floors.

    Each slab's floors = intersection of all boundary edges' floor sets.
    """
    stories = config.get("stories", [])
    foundation_floor = None
    for s in stories:
        if isinstance(s, dict) and s.get("name", "").startswith("B"):
            if foundation_floor is None:
                foundation_floor = s["name"]

    all_story_names = [s["name"] for s in stories if isinstance(s, dict)]

    slabs = []
    for poly, area in valid_faces:
        face_floors = None
        n = len(poly)

        for i in range(n):
            u = poly[i]
            v = poly[(i + 1) % n]
            ekey = (min(u, v), max(u, v))
            efloors = edge_floors.get(ekey)
            if efloors:
                if face_floors is None:
                    face_floors = set(efloors)
                else:
                    face_floors &= efloors

        if not face_floors:
            face_floors = set(all_story_names) if all_story_names else {"1F"}

        corners = [[round(x, 2), round(y, 2)] for x, y in poly]

        floor_order = {s["name"]: i for i, s in enumerate(stories)
                       if isinstance(s, dict)}
        sorted_floors = sorted(face_floors,
                               key=lambda f: floor_order.get(f, 999))

        slabs.append({
            "corners": corners,
            "floors": sorted_floors,
            "area": round(area, 2),
        })

    return slabs


def assign_floors_simple(valid_faces, floor_set, stories, foundation_floor):
    """Assign a fixed floor set to all slabs in a group.

    Since all segments in the group share the same floors, no intersection
    logic is needed — every slab gets the group's floor set.
    """
    floor_order = {s["name"]: i for i, s in enumerate(stories)
                   if isinstance(s, dict)}
    sorted_floors = sorted(floor_set,
                           key=lambda f: floor_order.get(f, 999))

    slabs = []
    for poly, area in valid_faces:
        corners = [[round(x, 2), round(y, 2)] for x, y in poly]
        slabs.append({
            "corners": corners,
            "floors": list(sorted_floors),
            "area": round(area, 2),
        })

    return slabs


def _normalize_corners(corners):
    """Normalize corner list for comparison (canonical rotation).

    Rotates the corner list so the lexicographically smallest corner is first.
    """
    if not corners:
        return tuple()
    min_idx = min(range(len(corners)),
                  key=lambda i: (corners[i][0], corners[i][1]))
    rotated = corners[min_idx:] + corners[:min_idx]
    return tuple(tuple(c) for c in rotated)


def _merge_slab_entries(slabs, stories):
    """Merge slabs with identical corners from different floor groups.

    Two slabs are considered identical if they have the same corner
    coordinates (after canonical rotation). Their floor lists are combined.
    """
    floor_order = {s["name"]: i for i, s in enumerate(stories)
                   if isinstance(s, dict)}

    by_corners = {}
    for slab in slabs:
        key = _normalize_corners(slab["corners"])
        if key in by_corners:
            existing = by_corners[key]
            existing_set = set(existing["floors"])
            for f in slab["floors"]:
                if f not in existing_set:
                    existing["floors"].append(f)
                    existing_set.add(f)
            existing["floors"].sort(key=lambda f: floor_order.get(f, 999))
        else:
            by_corners[key] = {
                "corners": slab["corners"],
                "floors": list(slab["floors"]),
                "area": slab["area"],
            }

    return list(by_corners.values())


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def _match_zone(cx, cy, floors, slab_zones, is_foundation):
    """Match a slab centroid to a slab zone polygon.

    Args:
        cx, cy: Slab centroid coordinates.
        floors: Set or list of floor names for this slab.
        slab_zones: List of zone dicts with "section", "corners", "floors".
        is_foundation: True if this slab is at the foundation floor.

    Returns:
        Matched section string (e.g. "S15", "FS100") or None.
    """
    floors_set = set(floors) if not isinstance(floors, set) else floors

    for zone in slab_zones:
        zone_section = zone.get("section", "")
        zone_corners = zone.get("corners", [])
        zone_floors = set(zone.get("floors", []))

        if len(zone_corners) < 3:
            continue

        # FS zones only match foundation slabs; S zones only match regular slabs
        zone_is_fs = zone_section.upper().startswith("FS")
        if zone_is_fs != is_foundation:
            continue

        # Check floor overlap
        if zone_floors and not (floors_set & zone_floors):
            continue

        # Point-in-polygon test
        polygon = [(c[0], c[1]) for c in zone_corners]
        if point_in_polygon(cx, cy, polygon):
            return zone_section

    return None


def generate_slab_config(slabs, slab_thickness=15, raft_thickness=100,
                         foundation_floor=None, slab_zones=None):
    """Convert internal slab list to config format.

    When a slab spans both foundation and non-foundation floors, it is split
    into an FS entry (foundation floors) and an S entry (remaining floors).

    Returns (slab_entries, new_sections).
    """
    slab_entries = []
    slab_thicknesses = set()
    raft_thicknesses = set()

    for slab in slabs:
        floors = slab["floors"]
        corners = slab["corners"]

        if foundation_floor and foundation_floor in floors:
            # Foundation floor slab
            fs_section = f"FS{raft_thickness}"
            if slab_zones:
                cx, cy = face_centroid([(c[0], c[1]) for c in corners])
                matched = _match_zone(cx, cy, [foundation_floor], slab_zones,
                                      is_foundation=True)
                if matched:
                    fs_section = matched
            # Extract thickness from section name for sections tracking
            fs_m = re.match(r"FS(\d+)", fs_section)
            if fs_m:
                raft_thicknesses.add(int(fs_m.group(1)))
            else:
                raft_thicknesses.add(raft_thickness)
            slab_entries.append({
                "corners": corners,
                "section": fs_section,
                "floors": [foundation_floor],
            })
            other_floors = [f for f in floors if f != foundation_floor]
            if other_floors:
                s_section = f"S{slab_thickness}"
                if slab_zones:
                    cx, cy = face_centroid([(c[0], c[1]) for c in corners])
                    matched = _match_zone(cx, cy, other_floors, slab_zones,
                                          is_foundation=False)
                    if matched:
                        s_section = matched
                s_m = re.match(r"S(\d+)", s_section)
                if s_m:
                    slab_thicknesses.add(int(s_m.group(1)))
                else:
                    slab_thicknesses.add(slab_thickness)
                slab_entries.append({
                    "corners": corners,
                    "section": s_section,
                    "floors": other_floors,
                })
        else:
            s_section = f"S{slab_thickness}"
            if slab_zones:
                cx, cy = face_centroid([(c[0], c[1]) for c in corners])
                matched = _match_zone(cx, cy, floors, slab_zones,
                                      is_foundation=False)
                if matched:
                    s_section = matched
            s_m = re.match(r"S(\d+)", s_section)
            if s_m:
                slab_thicknesses.add(int(s_m.group(1)))
            else:
                slab_thicknesses.add(slab_thickness)
            slab_entries.append({
                "corners": corners,
                "section": s_section,
                "floors": floors,
            })

    sections = {}
    if slab_thicknesses:
        sections["slab"] = sorted(slab_thicknesses)
    if raft_thicknesses:
        sections["raft"] = sorted(raft_thicknesses)

    return slab_entries, sections


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def generate_slabs(config, slab_thickness=15, raft_thickness=100, slab_zones=None,
                    slide_floor_ranges=None, debug_dir=None):
    """Main entry point: config → slab entries.

    Processes each floor group independently to avoid mixing segments
    from incompatible floors into a single 2D plane.

    Args:
        config: Complete config dict (must contain beams, small_beams, etc.)
        slab_thickness: Default slab thickness in cm
        raft_thickness: Default raft thickness in cm
        slab_zones: Optional slab zone overlay for per-region thickness
        slide_floor_ranges: Optional list of (label, frozenset) from
            parse_slide_floor_ranges(). When provided, each range is processed
            independently — no cross-range merging. Fixes 共構 bugs.
        debug_dir: Optional path for per-range debug output

    Returns (updated_config, stats).
    """
    stats = {
        "total_segments": 0,
        "total_intersections": 0,
        "total_beam_segments": 0,
        "total_polygons_raw": 0,
        "total_polygons_filtered": 0,
        "total_slabs": 0,
        "foundation_slabs": 0,
        "regular_slabs": 0,
        "floor_groups": 0,
        "warnings": [],
    }

    # Step 1: Collect structural segments
    print("  Step 1: Collecting structural segments...")
    segments = []

    for beam in config.get("beams", []):
        segments.append((
            beam["x1"], beam["y1"], beam["x2"], beam["y2"],
            set(beam.get("floors", [])),
        ))

    for sb in config.get("small_beams", []):
        segments.append((
            sb["x1"], sb["y1"], sb["x2"], sb["y2"],
            set(sb.get("floors", [])),
        ))

    for wall in config.get("walls", []):
        segments.append((
            wall["x1"], wall["y1"], wall["x2"], wall["y2"],
            set(wall.get("floors", [])),
        ))

    stats["total_segments"] = len(segments)
    print(f"    Segments: {len(segments)}")

    if len(segments) < 3:
        stats["warnings"].append("Too few segments to form any slab")
        return config, stats

    stories = normalize_stories_order(config.get("stories", []))
    foundation_floor = None
    for s in stories:
        if isinstance(s, dict) and s.get("name", "").startswith("B"):
            if foundation_floor is None:
                foundation_floor = s["name"]

    all_slabs = []

    if slide_floor_ranges:
        # --- Per-slide-range mode: each range processed independently ---
        print("  Step 2: Per-slide floor ranges (no cross-range merge)...")
        stats["floor_groups"] = len(slide_floor_ranges)
        print(f"    Ranges: {len(slide_floor_ranges)}")

        # Warn about uncovered floors
        all_config_floors = set()
        for seg in segments:
            all_config_floors |= seg[4]
        covered = set()
        for _, fs in slide_floor_ranges:
            covered |= fs
        uncovered = all_config_floors - covered
        if uncovered:
            msg = (f"Floors {sorted(uncovered)} in config are not covered "
                   f"by any slide-floor-range")
            stats["warnings"].append(msg)
            print(f"    WARNING: {msg}")

        for range_label, floor_set in slide_floor_ranges:
            range_segs = filter_segments_by_range(segments, floor_set)
            print(f"      {range_label} ({sorted(floor_set)}): "
                  f"{len(range_segs)} segments")

            if len(range_segs) < 3:
                continue

            seg_points = compute_intersections(range_segs)
            n_ints = sum(len(pts) - 2 for pts in seg_points.values())
            stats["total_intersections"] += n_ints

            beam_segs = build_beam_segments(range_segs, seg_points)
            stats["total_beam_segments"] += len(beam_segs)

            if len(beam_segs) < 3:
                continue

            adj, edge_floors = build_point_adjacency(beam_segs)
            polygons = walk_slab_polygons(adj)
            stats["total_polygons_raw"] += len(polygons)

            valid_faces = filter_slabs(polygons, config, range_floors=floor_set)
            stats["total_polygons_filtered"] += len(valid_faces)

            range_slabs = assign_floors_simple(
                valid_faces, floor_set, stories, foundation_floor)
            print(f"      -> {len(valid_faces)} slabs")

            if debug_dir:
                write_range_debug(debug_dir, range_label, range_segs,
                                  polygons, valid_faces, range_slabs,
                                  slab_zones=slab_zones)

            all_slabs.extend(range_slabs)

        # NO _merge_slab_entries — ranges are independent
        merged_slabs = all_slabs
        print(f"  Total slabs across ranges: {len(merged_slabs)}")

    else:
        # --- Legacy mode: geometry-based grouping + merge ---
        print("  Step 2: Grouping floors by segment geometry...")
        floor_groups = group_segments_by_floor(segments)
        stats["floor_groups"] = len(floor_groups)
        print(f"    Floor groups: {len(floor_groups)}")
        for fs, gs in floor_groups:
            print(f"      {sorted(fs)}: {len(gs)} segments")

        for floor_set, group_segs in floor_groups:
            if len(group_segs) < 3:
                continue

            print(f"  Processing group {sorted(floor_set)} "
                  f"({len(group_segs)} segments)...")

            seg_points = compute_intersections(group_segs)
            n_ints = sum(len(pts) - 2 for pts in seg_points.values())
            stats["total_intersections"] += n_ints

            beam_segs = build_beam_segments(group_segs, seg_points)
            stats["total_beam_segments"] += len(beam_segs)

            if len(beam_segs) < 3:
                continue

            adj, edge_floors = build_point_adjacency(beam_segs)
            polygons = walk_slab_polygons(adj)
            stats["total_polygons_raw"] += len(polygons)

            valid_faces = filter_slabs(polygons, config, range_floors=floor_set)
            stats["total_polygons_filtered"] += len(valid_faces)

            group_slabs = assign_floors_simple(
                valid_faces, floor_set, stories, foundation_floor)
            all_slabs.extend(group_slabs)
            print(f"    -> {len(valid_faces)} slabs")

        print("  Step 7: Merging slabs across groups...")
        merged_slabs = _merge_slab_entries(all_slabs, stories)
        print(f"    {len(all_slabs)} raw -> {len(merged_slabs)} merged")

    if not merged_slabs:
        stats["warnings"].append("No valid slab polygons found after filtering")
        return config, stats

    # Generate config entries
    slab_entries, new_sections = generate_slab_config(
        merged_slabs, slab_thickness, raft_thickness, foundation_floor,
        slab_zones=slab_zones)

    stats["total_slabs"] = len(slab_entries)
    stats["foundation_slabs"] = sum(
        1 for e in slab_entries if e["section"].startswith("FS"))
    stats["regular_slabs"] = stats["total_slabs"] - stats["foundation_slabs"]

    # Update config
    updated = json.loads(json.dumps(config))  # deep copy
    updated["slabs"] = slab_entries

    # Merge sections
    existing_sections = updated.get("sections", {})
    if "slab" in new_sections:
        existing_slab = set(existing_sections.get("slab", []))
        for t in new_sections["slab"]:
            existing_slab.add(t)
        existing_sections["slab"] = sorted(existing_slab)
    if "raft" in new_sections:
        existing_raft = set(existing_sections.get("raft", []))
        for t in new_sections["raft"]:
            existing_raft.add(t)
        existing_sections["raft"] = sorted(existing_raft)
    updated["sections"] = existing_sections

    return updated, stats


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate slab polygons from beam layout")
    parser.add_argument("--config", required=True,
                        help="Path to config with all beams")
    parser.add_argument("--output", required=True,
                        help="Path for output config with slabs")
    parser.add_argument("--slab-thickness", type=int, default=15,
                        help="Default slab thickness in cm (default: 15)")
    parser.add_argument("--raft-thickness", type=int, default=100,
                        help="Default raft thickness in cm (default: 100)")
    parser.add_argument("--slab-zones",
                        help="Path to slab zones JSON (standalone or sb_elements_validated.json)")
    parser.add_argument("--slide-floor-ranges",
                        help="Semicolon-separated floor ranges from PPT page-floors "
                             "(e.g. 'B3F; B2F~B1F; 1F~2F; 3F~14F; R1F~R3F'). "
                             "Each range is processed independently — no cross-range merge.")
    parser.add_argument("--debug-dir",
                        help="Directory for per-range debug output "
                             "(segments, polygons, slabs per range)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show results without writing output")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)

    # Load slab zones if provided
    slab_zones = None
    if args.slab_zones:
        with open(args.slab_zones, encoding="utf-8") as f:
            zones_data = json.load(f)
        # Auto-detect: standalone zones list or sb_elements with slab_zones key
        if isinstance(zones_data, list):
            slab_zones = zones_data
        elif "slab_zones" in zones_data:
            slab_zones = zones_data["slab_zones"]
        else:
            print(f"  WARNING: No slab_zones found in {args.slab_zones}")
        if slab_zones:
            print(f"  Slab zones loaded: {len(slab_zones)} zones from {args.slab_zones}")

    # Parse slide floor ranges if provided
    slide_floor_ranges = None
    if args.slide_floor_ranges:
        slide_floor_ranges = parse_slide_floor_ranges(args.slide_floor_ranges)
        print(f"Slide floor ranges: {len(slide_floor_ranges)} ranges")
        for label, fs in slide_floor_ranges:
            print(f"  {label}: {sorted(fs)}")

    print(f"Config loaded: {args.config}")
    print(f"  beams: {len(config.get('beams', []))}")
    print(f"  small_beams: {len(config.get('small_beams', []))}")
    print(f"  walls: {len(config.get('walls', []))}")
    print(f"  columns: {len(config.get('columns', []))}")
    print(f"  slab_thickness: {args.slab_thickness}cm")
    print(f"  raft_thickness: {args.raft_thickness}cm")

    print(f"\n--- Generating slabs ---")
    updated_config, stats = generate_slabs(
        config,
        slab_thickness=args.slab_thickness,
        raft_thickness=args.raft_thickness,
        slab_zones=slab_zones,
        slide_floor_ranges=slide_floor_ranges,
        debug_dir=args.debug_dir,
    )

    print(f"\n--- Slab Generation Summary ---")
    print(f"  Segments: {stats['total_segments']}")
    print(f"  Floor groups: {stats['floor_groups']}")
    print(f"  Intersections: {stats['total_intersections']}")
    print(f"  Beam segments: {stats['total_beam_segments']}")
    print(f"  Raw polygons: {stats['total_polygons_raw']}")
    print(f"  Filtered slabs: {stats['total_polygons_filtered']}")
    print(f"  Total slabs: {stats['total_slabs']}")
    print(f"    Regular (S): {stats['regular_slabs']}")
    print(f"    Foundation (FS): {stats['foundation_slabs']}")

    if stats["warnings"]:
        print(f"\nWARNINGS ({len(stats['warnings'])}):")
        for w in stats["warnings"]:
            print(f"  WARNING: {w}")

    slabs = updated_config.get("slabs", [])
    if slabs:
        print(f"\nSample slabs (first 5):")
        for s in slabs[:5]:
            n_corners = len(s["corners"])
            n_floors = len(s["floors"])
            print(f"  {s['section']}: {n_corners} corners, {n_floors} floors, "
                  f"corners={s['corners']}")

    if args.dry_run:
        print(f"\n[DRY RUN] No output written.")
    else:
        from golden_scripts.tools.config_integrity import stamp_config
        stamp_config(updated_config)
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(updated_config, f, ensure_ascii=False, indent=2)
        print(f"\nFinal config written to: {args.output}")
        print(f"  slabs: {len(slabs)}")
        print(f"  sections.slab: {updated_config.get('sections', {}).get('slab', [])}")
        print(f"  sections.raft: {updated_config.get('sections', {}).get('raft', [])}")


if __name__ == "__main__":
    main()
