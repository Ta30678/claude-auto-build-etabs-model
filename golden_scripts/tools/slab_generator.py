"""
Slab Generator — Graph-based slab polygon generation from beam layout.

Reads a snapped_config.json (containing all beams including small beams) and
generates slab polygons using half-edge face enumeration on the planar beam graph.

This replaces the Cartesian cutting-line approach with a proper planar subdivision
that handles T-intersections, non-rectangular panels, and complex beam layouts.

Algorithm:
  Step 1: Collect all structural nodes (beam endpoints, column positions, intersections)
  Step 2: Build planar graph (split beams at intersections)
  Step 3: Half-edge face enumeration (find minimal enclosed faces)
  Step 4: Filter faces (building outline, slab region, minimum area)
  Step 5: Assign floors to each face

Usage:
    python -m golden_scripts.tools.slab_generator \
        --config snapped_config.json \
        --output final_config.json

    # Custom thicknesses:
    python -m golden_scripts.tools.slab_generator \
        --config snapped_config.json \
        --slab-thickness 15 \
        --raft-thickness 100 \
        --output final_config.json

    # Preview without writing:
    python -m golden_scripts.tools.slab_generator \
        --config snapped_config.json \
        --output final_config.json \
        --dry-run
"""

import argparse
import json
import math
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NODE_CLUSTER_TOL = 0.02      # 2cm: merge nodes within this distance
INTERSECTION_TOL = 1e-6      # numerical tolerance for segment intersection
MIN_FACE_AREA = 0.25         # m²: discard faces smaller than this
COLLINEAR_TOL = 0.01         # 1cm: tolerance for collinear point check


# ---------------------------------------------------------------------------
# 1. Node collection and clustering
# ---------------------------------------------------------------------------

class NodePool:
    """Manages a pool of 2D nodes with automatic clustering."""

    def __init__(self, tolerance=NODE_CLUSTER_TOL):
        self.nodes = []  # list of (x, y)
        self.tolerance = tolerance

    def add(self, x, y):
        """Add a point, returning its index (merging if close to existing)."""
        for i, (nx, ny) in enumerate(self.nodes):
            if math.hypot(x - nx, y - ny) <= self.tolerance:
                return i
        idx = len(self.nodes)
        self.nodes.append((round(x, 2), round(y, 2)))
        return idx

    def __len__(self):
        return len(self.nodes)


def _seg_intersection(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
    """Compute intersection point of two line segments (if any).

    Returns (x, y) or None. Only returns interior intersections
    (both-interior, i.e. crossing points not at any endpoint).
    """
    dx1 = ax2 - ax1
    dy1 = ay2 - ay1
    dx2 = bx2 - bx1
    dy2 = by2 - by1

    denom = dx1 * dy2 - dy1 * dx2
    if abs(denom) < INTERSECTION_TOL:
        return None  # Parallel or collinear

    t = ((bx1 - ax1) * dy2 - (by1 - ay1) * dx2) / denom
    u = ((bx1 - ax1) * dy1 - (by1 - ay1) * dx1) / denom

    # Check if intersection is strictly interior to both segments
    eps = 0.001  # Small margin to avoid endpoint duplicates
    if eps < t < 1 - eps and eps < u < 1 - eps:
        ix = ax1 + t * dx1
        iy = ay1 + t * dy1
        return (round(ix, 2), round(iy, 2))
    return None


def _point_on_segment_interior(px, py, ax, ay, bx, by, tol=NODE_CLUSTER_TOL):
    """Check if point (px,py) lies on the interior of segment A->B.

    Returns True if the point projects onto the segment interior
    (not at endpoints) within tolerance.
    """
    dx, dy = bx - ax, by - ay
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-12:
        return False
    t = ((px - ax) * dx + (py - ay) * dy) / len_sq
    if t < 0.01 or t > 0.99:  # Must be interior
        return False
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    dist = math.hypot(px - proj_x, py - proj_y)
    return dist <= tol


def collect_nodes_and_edges(config, pool):
    """Collect nodes from all structural elements and build edge list.

    Returns list of (node_idx_1, node_idx_2, floors_set) tuples.
    """
    raw_segments = []  # (x1, y1, x2, y2, floors)

    # Columns → nodes only (no edges)
    for col in config.get("columns", []):
        pool.add(col["grid_x"], col["grid_y"])

    # Beams → segments
    for beam in config.get("beams", []):
        raw_segments.append((
            beam["x1"], beam["y1"], beam["x2"], beam["y2"],
            set(beam.get("floors", [])),
        ))

    # Small beams → segments
    for sb in config.get("small_beams", []):
        raw_segments.append((
            sb["x1"], sb["y1"], sb["x2"], sb["y2"],
            set(sb.get("floors", [])),
        ))

    # Walls → segments
    for wall in config.get("walls", []):
        raw_segments.append((
            wall["x1"], wall["y1"], wall["x2"], wall["y2"],
            set(wall.get("floors", [])),
        ))

    # Compute all pairwise intersections and add as nodes
    n_seg = len(raw_segments)
    seg_splits = {i: [] for i in range(n_seg)}  # segment_idx -> [intersection_points]

    for i in range(n_seg):
        for j in range(i + 1, n_seg):
            ax1, ay1, ax2, ay2, _ = raw_segments[i]
            bx1, by1, bx2, by2, _ = raw_segments[j]
            pt = _seg_intersection(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2)
            if pt:
                pool.add(pt[0], pt[1])
                seg_splits[i].append(pt)
                seg_splits[j].append(pt)

    # T-junction detection: segment endpoint lying on another segment's interior
    for i in range(n_seg):
        ax1, ay1, ax2, ay2, _ = raw_segments[i]
        for j in range(n_seg):
            if i == j:
                continue
            bx1, by1, bx2, by2, _ = raw_segments[j]
            # Check if endpoint of segment i lies on interior of segment j
            for px, py in [(ax1, ay1), (ax2, ay2)]:
                if _point_on_segment_interior(px, py, bx1, by1, bx2, by2):
                    pool.add(px, py)
                    seg_splits[j].append((round(px, 2), round(py, 2)))

    # Build edges: split each segment at intersection points
    edges = []  # (node_idx_1, node_idx_2, floors_set)

    for i, (x1, y1, x2, y2, floors) in enumerate(raw_segments):
        # Collect all points along this segment (endpoints + splits)
        points = [(x1, y1), (x2, y2)]
        for pt in seg_splits[i]:
            points.append(pt)

        # Sort points along segment direction
        if abs(x2 - x1) >= abs(y2 - y1):
            points.sort(key=lambda p: p[0] if x2 >= x1 else -p[0])
        else:
            points.sort(key=lambda p: p[1] if y2 >= y1 else -p[1])

        # Deduplicate consecutive points
        deduped = [points[0]]
        for p in points[1:]:
            if math.hypot(p[0] - deduped[-1][0], p[1] - deduped[-1][1]) > COLLINEAR_TOL:
                deduped.append(p)

        # Create sub-edges
        for k in range(len(deduped) - 1):
            n1 = pool.add(deduped[k][0], deduped[k][1])
            n2 = pool.add(deduped[k + 1][0], deduped[k + 1][1])
            if n1 != n2:
                edges.append((n1, n2, floors))

    return edges


# ---------------------------------------------------------------------------
# 2. Build planar graph (adjacency with angular ordering)
# ---------------------------------------------------------------------------

def build_adjacency(edges, nodes):
    """Build adjacency list with edges sorted by angle at each node.

    Returns adj: {node_idx: [(neighbor_idx, edge_idx), ...]} sorted CW by angle.
    """
    # Build bidirectional edge list
    adj = {}
    edge_floors = {}  # edge_key -> floors_set

    for idx, (n1, n2, floors) in enumerate(edges):
        adj.setdefault(n1, []).append(n2)
        adj.setdefault(n2, []).append(n1)
        edge_key = (min(n1, n2), max(n1, n2))
        if edge_key in edge_floors:
            edge_floors[edge_key] |= floors
        else:
            edge_floors[edge_key] = set(floors)

    # Sort neighbors by angle (clockwise from +X axis)
    for node_idx in adj:
        nx, ny = nodes[node_idx]
        neighbors = adj[node_idx]
        # Remove duplicates
        neighbors = list(set(neighbors))

        def angle_key(nb):
            nbx, nby = nodes[nb]
            return math.atan2(nby - ny, nbx - nx)

        neighbors.sort(key=angle_key)
        adj[node_idx] = neighbors

    return adj, edge_floors


# ---------------------------------------------------------------------------
# 3. Half-edge face enumeration
# ---------------------------------------------------------------------------

def enumerate_faces(adj, nodes):
    """Find all minimal faces in the planar graph using half-edge traversal.

    For each directed edge (u→v), find the "next" edge by taking the first
    neighbor of v that is clockwise from the direction v→u.

    Returns list of faces, each face = [node_idx, ...] (ordered vertices).
    """
    if not adj:
        return []

    # Build next-edge mapping
    # For directed edge u→v, "next" is the edge v→w where w is the first
    # neighbor of v clockwise after the direction v→u
    used_half_edges = set()
    faces = []

    for start_u in adj:
        for start_v in adj[start_u]:
            he = (start_u, start_v)
            if he in used_half_edges:
                continue

            # Trace face
            face = []
            u, v = start_u, start_v
            max_steps = len(nodes) * 2 + 10  # Safety limit

            for _ in range(max_steps):
                if (u, v) in used_half_edges:
                    break
                used_half_edges.add((u, v))
                face.append(u)

                # Find next edge: at node v, incoming from u
                # We want the first neighbor of v that is CW from direction v→u
                neighbors = adj.get(v, [])
                if not neighbors:
                    break

                # Direction from v back to u
                vx, vy = nodes[v]
                ux, uy = nodes[u]
                incoming_angle = math.atan2(uy - vy, ux - vx)

                # Find the neighbor with the smallest positive CW rotation
                best_w = None
                best_delta = float("inf")
                for w in neighbors:
                    if w == u and len(neighbors) > 1:
                        # Avoid going back on degree-2+ nodes
                        continue
                    wx, wy = nodes[w]
                    outgoing_angle = math.atan2(wy - vy, wx - vx)
                    # CW delta: how much to rotate CW from incoming to outgoing
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
                faces.append(face)

    return faces


def face_area_signed(face, nodes):
    """Compute signed area of a face (positive = CCW, negative = CW)."""
    n = len(face)
    area = 0.0
    for i in range(n):
        x1, y1 = nodes[face[i]]
        x2, y2 = nodes[face[(i + 1) % n]]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def face_centroid(face, nodes):
    """Compute centroid of a face."""
    n = len(face)
    cx = sum(nodes[idx][0] for idx in face) / n
    cy = sum(nodes[idx][1] for idx in face) / n
    return cx, cy


# ---------------------------------------------------------------------------
# 4. Face filtering
# ---------------------------------------------------------------------------

def point_in_polygon(px, py, polygon):
    """Ray casting point-in-polygon test.

    polygon: list of (x, y) tuples.
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def filter_faces(faces, nodes, config, edge_floors):
    """Filter faces to keep only valid slab regions.

    Removes:
    - Outer face (largest area or CW winding)
    - Faces with centroid outside building_outline
    - Faces in slab_region_matrix no-slab zones
    - Degenerate faces (area < MIN_FACE_AREA)

    Returns list of (face, area, is_foundation) tuples.
    """
    if not faces:
        return []

    # Build building outline polygon
    outline = config.get("building_outline")
    outline_poly = None
    if outline:
        outline_poly = [(pt[0], pt[1]) for pt in outline]

    # Compute areas
    face_data = []
    for face in faces:
        area = face_area_signed(face, nodes)
        face_data.append((face, area))

    # Find outer face (largest absolute area, or CW winding = negative area)
    max_abs_area = max(abs(a) for _, a in face_data) if face_data else 0

    valid_faces = []
    for face, area in face_data:
        abs_area = abs(area)

        # Skip outer face (largest area)
        if abs_area > max_abs_area * 0.95 and abs_area > 100:
            continue

        # Skip CW faces (negative area = exterior face in CCW convention)
        if area < 0:
            continue

        # Skip degenerate
        if abs_area < MIN_FACE_AREA:
            continue

        # Check centroid inside building outline
        cx, cy = face_centroid(face, nodes)
        if outline_poly and not point_in_polygon(cx, cy, outline_poly):
            continue

        # Check slab_region_matrix if available
        srm = config.get("slab_region_matrix")
        if srm and not _in_slab_region(cx, cy, srm, config):
            continue

        valid_faces.append((face, abs_area))

    return valid_faces


def _in_slab_region(cx, cy, srm, config):
    """Check if point is in a slab region according to slab_region_matrix.

    The matrix maps grid zones to slab/no-slab. Simple heuristic:
    if the zone is explicitly marked as no-slab, return False.
    """
    # slab_region_matrix format varies; try common format
    # If it's a list of dicts with "zone" and "build" fields
    if isinstance(srm, list):
        for entry in srm:
            if isinstance(entry, dict):
                if entry.get("build") is False or entry.get("建板") is False:
                    # Check if point is in this zone's bounds
                    bounds = entry.get("bounds")
                    if bounds and len(bounds) >= 4:
                        x_min, y_min, x_max, y_max = bounds[:4]
                        if x_min <= cx <= x_max and y_min <= cy <= y_max:
                            return False
    return True


# ---------------------------------------------------------------------------
# 5. Floor assignment
# ---------------------------------------------------------------------------

def assign_floors_to_faces(valid_faces, nodes, edges, edge_floors, config):
    """Assign floors to each face based on boundary edges' floor sets.

    Each face's floors = intersection of all boundary edges' floors.
    If a boundary edge has no floor info, it's ignored (not constraining).

    Returns list of slab dicts.
    """
    # Determine foundation stories
    stories = config.get("stories", [])
    foundation_floor = None
    for s in stories:
        if isinstance(s, dict) and s.get("name", "").startswith("B"):
            # Keep the first (lowest) basement
            if foundation_floor is None:
                foundation_floor = s["name"]

    # Collect all story names for "all floors" default
    all_story_names = []
    for s in stories:
        if isinstance(s, dict):
            all_story_names.append(s["name"])

    slabs = []
    for face, area in valid_faces:
        # Collect floors from boundary edges
        face_floors = None  # Will intersect
        n = len(face)

        for i in range(n):
            u = face[i]
            v = face[(i + 1) % n]
            edge_key = (min(u, v), max(u, v))
            efloors = edge_floors.get(edge_key)
            if efloors:
                if face_floors is None:
                    face_floors = set(efloors)
                else:
                    face_floors &= efloors

        if face_floors is None or len(face_floors) == 0:
            # No floor info from edges; use all floors
            face_floors = set(all_story_names) if all_story_names else {"1F"}

        # Determine if this is a foundation slab
        is_foundation = False
        if foundation_floor and foundation_floor in face_floors:
            # If all floors in this face are foundation
            is_foundation = all(
                f.startswith("B") or f == foundation_floor
                for f in face_floors
            )

        # Build corners
        corners = [[round(nodes[idx][0], 2), round(nodes[idx][1], 2)]
                    for idx in face]

        # Sort floors in story order
        floor_order = {s["name"]: i for i, s in enumerate(stories)
                       if isinstance(s, dict)}
        sorted_floors = sorted(face_floors, key=lambda f: floor_order.get(f, 999))

        slabs.append({
            "corners": corners,
            "floors": sorted_floors,
            "is_foundation": is_foundation,
            "area": round(area, 2),
        })

    return slabs


# ---------------------------------------------------------------------------
# 6. Output generation
# ---------------------------------------------------------------------------

def generate_slab_config(slabs, slab_thickness=15, raft_thickness=100):
    """Convert internal slab list to config format.

    Returns (slab_entries, new_sections).
    """
    slab_entries = []
    slab_thicknesses = set()
    raft_thicknesses = set()

    for slab in slabs:
        if slab["is_foundation"]:
            section = f"FS{raft_thickness}"
            raft_thicknesses.add(raft_thickness)
        else:
            section = f"S{slab_thickness}"
            slab_thicknesses.add(slab_thickness)

        entry = {
            "corners": slab["corners"],
            "section": section,
            "floors": slab["floors"],
        }
        slab_entries.append(entry)

    sections = {}
    if slab_thicknesses:
        sections["slab"] = sorted(slab_thicknesses)
    if raft_thicknesses:
        sections["raft"] = sorted(raft_thicknesses)

    return slab_entries, sections


# ---------------------------------------------------------------------------
# 7. Main pipeline
# ---------------------------------------------------------------------------

def generate_slabs(config, slab_thickness=15, raft_thickness=100):
    """Main entry point: config → slab entries.

    Args:
        config: Complete config dict (must contain beams, small_beams, etc.)
        slab_thickness: Default slab thickness in cm
        raft_thickness: Default raft thickness in cm

    Returns (updated_config, stats).
    """
    pool = NodePool()
    stats = {
        "total_nodes": 0,
        "total_edges": 0,
        "total_faces_raw": 0,
        "total_faces_filtered": 0,
        "total_slabs": 0,
        "foundation_slabs": 0,
        "regular_slabs": 0,
        "warnings": [],
    }

    # Step 1-2: Collect nodes and build edges
    print("  Step 1-2: Collecting nodes and building edges...")
    edges = collect_nodes_and_edges(config, pool)
    nodes = pool.nodes
    stats["total_nodes"] = len(nodes)
    stats["total_edges"] = len(edges)
    print(f"    Nodes: {len(nodes)}, Edges: {len(edges)}")

    if len(edges) < 3:
        stats["warnings"].append("Too few edges to form any face")
        return config, stats

    # Step 2b: Build adjacency
    print("  Step 3: Building adjacency and enumerating faces...")
    adj, edge_floors = build_adjacency(edges, nodes)

    # Step 3: Face enumeration
    faces = enumerate_faces(adj, nodes)
    stats["total_faces_raw"] = len(faces)
    print(f"    Raw faces: {len(faces)}")

    # Step 4: Filter faces
    print("  Step 4: Filtering faces...")
    valid_faces = filter_faces(faces, nodes, config, edge_floors)
    stats["total_faces_filtered"] = len(valid_faces)
    print(f"    Valid faces: {len(valid_faces)}")

    if not valid_faces:
        stats["warnings"].append("No valid slab faces found after filtering")
        return config, stats

    # Step 5: Assign floors
    print("  Step 5: Assigning floors...")
    slabs = assign_floors_to_faces(valid_faces, nodes, edges, edge_floors, config)

    # Step 6: Generate config entries
    slab_entries, new_sections = generate_slab_config(
        slabs, slab_thickness, raft_thickness)

    stats["total_slabs"] = len(slab_entries)
    stats["foundation_slabs"] = sum(1 for s in slabs if s["is_foundation"])
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
# 8. CLI interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate slab polygons from beam layout using graph-based face enumeration")
    parser.add_argument("--config", required=True,
                        help="Path to snapped_config.json (contains all beams)")
    parser.add_argument("--output", required=True,
                        help="Path for output config with slabs (final_config.json)")
    parser.add_argument("--slab-thickness", type=int, default=15,
                        help="Default slab thickness in cm (default: 15)")
    parser.add_argument("--raft-thickness", type=int, default=100,
                        help="Default raft thickness in cm (default: 100)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show results without writing output")
    args = parser.parse_args()

    # Load config
    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)

    print(f"Config loaded: {args.config}")
    print(f"  beams: {len(config.get('beams', []))}")
    print(f"  small_beams: {len(config.get('small_beams', []))}")
    print(f"  walls: {len(config.get('walls', []))}")
    print(f"  columns: {len(config.get('columns', []))}")
    print(f"  slab_thickness: {args.slab_thickness}cm")
    print(f"  raft_thickness: {args.raft_thickness}cm")

    # Generate slabs
    print(f"\n--- Generating slabs ---")
    updated_config, stats = generate_slabs(
        config,
        slab_thickness=args.slab_thickness,
        raft_thickness=args.raft_thickness,
    )

    # Summary
    print(f"\n--- Slab Generation Summary ---")
    print(f"  Nodes: {stats['total_nodes']}")
    print(f"  Edges: {stats['total_edges']}")
    print(f"  Raw faces: {stats['total_faces_raw']}")
    print(f"  Filtered faces: {stats['total_faces_filtered']}")
    print(f"  Total slabs: {stats['total_slabs']}")
    print(f"    Regular (S): {stats['regular_slabs']}")
    print(f"    Foundation (FS): {stats['foundation_slabs']}")

    if stats["warnings"]:
        print(f"\nWARNINGS ({len(stats['warnings'])}):")
        for w in stats["warnings"]:
            print(f"  WARNING: {w}")

    # Show sample slabs
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
