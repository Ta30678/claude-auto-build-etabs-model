# gs_05 Wall Splitting at Beam/Column Intersections

**Date**: 2026-03-17
**Status**: Proposed
**Scope**: `golden_scripts/modeling/gs_05_walls.py` only

## Problem

Walls in `model_config.json` are stored as single line segments spanning multiple grid lines (e.g., a diaphragm wall from grid A to grid H = 42.8m). When `gs_05_walls.py` creates these as area objects in ETABS, each wall becomes one monolithic area per floor. ETABS requires walls to be divided at beam/column intersections for proper connectivity and meshing.

Example from A21:
- Wall: `(-4, 35.35) → (38.8, 35.35)` — one 42.8m piece
- FWB beams along the same line are already split: `(-4→0), (0→8.5), (8.5→19.5), ...`
- The wall should match the beam segmentation

ETABS GUI has "Divide wall at intersections with selected frame objects" but this is not exposed in the COM API.

## Solution

Add wall splitting logic to `gs_05_walls.py`. Before creating each wall's area objects, compute cut points from beams, columns, and other walls, then create multiple smaller area objects.

### Assumptions

- Wall coordinates are already snapped to beams (via `beam_validate.py` Step 4: wall-to-beam re-snap)
- No tolerance needed — use floating-point epsilon (0.001m) only
- Cut points come from beams, columns, and other walls that share at least one floor
- Floor overlap uses simple set intersection on the `floors` arrays. The +1 rule is irrelevant here because walls and beams at the same physical location always share at least one common floor label in the config.
- Phase 2 does NOT re-run step 5, so walls are not split at small beam positions. This is acceptable — SBs are frame objects and ETABS handles frame-to-area connectivity at the mesh level. The critical splits are at major beam/column positions.

### Cut Point Sources

| Source | Detection Method | Example |
|--------|-----------------|---------|
| Perpendicular beam | Segment-segment intersection | FB beam (0,27.35)→(0,35.35) crosses wall → cut at (0,35.35) |
| Parallel beam endpoint | Point-on-segment check | FWB (0,35.35)→(8.5,35.35) → cuts at x=0 and x=8.5 |
| Column | Point-on-segment check | Column at (8.5,35.35) → cut at x=8.5 |
| Other wall (perpendicular) | Segment-segment intersection | Wall (38.8,-3)→(38.8,35.35) crosses → cut at (38.8,35.35) |
| Other wall (parallel endpoint) | Point-on-segment check | Collinear wall endpoint projects onto this wall → cut point |

### Algorithm

```python
def split_wall_at_intersections(wall, beams, columns, other_walls):
    """Split a wall line segment at beam/column/wall intersections.

    Parameters
    ----------
    wall : dict
        Wall with x1, y1, x2, y2, floors.
    beams : list[dict]
        All beams from config.
    columns : list[dict]
        All columns from config.
    other_walls : list[dict]
        All other walls from config (excluding self).

    Returns
    -------
    list[tuple[float, float, float, float]]
        List of (x1, y1, x2, y2) sub-wall segments.
    """
    EPS = 0.001  # 1mm floating-point epsilon
    T_MIN = 0.01  # skip cuts within 1% of wall endpoints

    wall_floors = set(wall["floors"])
    bx1, by1 = wall["x1"], wall["y1"]
    bx2, by2 = wall["x2"], wall["y2"]
    bdx, bdy = bx2 - bx1, by2 - by1
    b_len_sq = bdx * bdx + bdy * bdy
    if b_len_sq < EPS * EPS:
        return [(bx1, by1, bx2, by2)]

    cut_ts = []  # parameter values along wall [0, 1]

    # --- 1. Beams: intersection + endpoint projection ---
    for beam in beams:
        if not (wall_floors & set(beam["floors"])):
            continue
        # Segment intersection (catches perpendicular crossings)
        ix = segment_intersection(bx1, by1, bx2, by2,
                                  beam["x1"], beam["y1"],
                                  beam["x2"], beam["y2"])
        if ix:
            _, _, t_wall, _ = ix
            if T_MIN < t_wall < 1 - T_MIN:
                cut_ts.append(t_wall)
        # Endpoint projection (catches parallel beam endpoints)
        for px, py in [(beam["x1"], beam["y1"]),
                       (beam["x2"], beam["y2"])]:
            t = ((px - bx1) * bdx + (py - by1) * bdy) / b_len_sq
            if t <= T_MIN or t >= 1 - T_MIN:
                continue
            proj_x = bx1 + t * bdx
            proj_y = by1 + t * bdy
            if abs(px - proj_x) < EPS and abs(py - proj_y) < EPS:
                cut_ts.append(t)

    # --- 2. Columns: point projection ---
    for col in columns:
        if not (wall_floors & set(col["floors"])):
            continue
        cx = col.get("grid_x", col.get("x1", 0))
        cy = col.get("grid_y", col.get("y1", 0))
        t = ((cx - bx1) * bdx + (cy - by1) * bdy) / b_len_sq
        if t <= T_MIN or t >= 1 - T_MIN:
            continue
        proj_x = bx1 + t * bdx
        proj_y = by1 + t * bdy
        if abs(cx - proj_x) < EPS and abs(cy - proj_y) < EPS:
            cut_ts.append(t)

    # --- 3. Other walls: intersection + endpoint projection ---
    for other in other_walls:
        if not (wall_floors & set(other["floors"])):
            continue
        # Segment intersection (perpendicular walls)
        ix = segment_intersection(bx1, by1, bx2, by2,
                                  other["x1"], other["y1"],
                                  other["x2"], other["y2"])
        if ix:
            _, _, t_wall, _ = ix
            if T_MIN < t_wall < 1 - T_MIN:
                cut_ts.append(t_wall)
        # Endpoint projection (parallel/collinear walls)
        for px, py in [(other["x1"], other["y1"]),
                       (other["x2"], other["y2"])]:
            t = ((px - bx1) * bdx + (py - by1) * bdy) / b_len_sq
            if t <= T_MIN or t >= 1 - T_MIN:
                continue
            proj_x = bx1 + t * bdx
            proj_y = by1 + t * bdy
            if abs(px - proj_x) < EPS and abs(py - proj_y) < EPS:
                cut_ts.append(t)

    # --- Sort + dedup ---
    if not cut_ts:
        return [(bx1, by1, bx2, by2)]

    cut_ts = sorted(set(round(t, 6) for t in cut_ts))
    deduped = [cut_ts[0]]
    for t in cut_ts[1:]:
        if t - deduped[-1] > 0.005:
            deduped.append(t)
    cut_ts = deduped

    # --- Build sub-walls ---
    points = [0.0] + cut_ts + [1.0]
    segments = []
    for i in range(len(points) - 1):
        t0, t1 = points[i], points[i + 1]
        sx1 = round(bx1 + t0 * bdx, 2)
        sy1 = round(by1 + t0 * bdy, 2)
        sx2 = round(bx1 + t1 * bdx, 2)
        sy2 = round(by1 + t1 * bdy, 2)
        segments.append((sx1, sy1, sx2, sy2))
    return segments
```

### Integration in `place_walls()`

```python
def place_walls(SapModel, config, elev_map, strength_lookup, all_stories=None):
    walls = config.get("walls", [])
    beams = config.get("beams", []) + config.get("small_beams", [])
    columns = config.get("columns", [])

    for i, wall in enumerate(walls):
        other_walls = walls[:i] + walls[i + 1:]
        sub_walls = split_wall_at_intersections(wall, beams, columns, other_walls)

        for sx1, sy1, sx2, sy2 in sub_walls:
            for plan_floor in wall["floors"]:
                # ... existing area creation logic using sx1,sy1,sx2,sy2
```

### Expected A21 Results

| Wall | Before | After |
|------|--------|-------|
| (-4,35.35)→(38.8,35.35) | 1 piece × 3 floors = 3 areas | 5 pieces × 3 floors = 15 areas |
| (-4,-3)→(38.8,-3) | 1 × 3 = 3 | 5 × 3 = 15 |
| (38.8,-3)→(38.8,35.35) | 1 × 3 = 3 | 5 × 3 = 15 |
| (-4,-3)→(-4,35.35) | 1 × 3 = 3 | 5 × 3 = 15 |
| **Total** | **12 areas** | **60 areas** |

### Dependencies

`segment_intersection()` is defined in `beam_validate.py`. To avoid coupling the modeling layer to the tools layer, define a local copy in `gs_05_walls.py` (20 lines, pure math, no external dependencies).

### Files Changed

- `golden_scripts/modeling/gs_05_walls.py` — add `segment_intersection()` (local copy), `split_wall_at_intersections()`, modify `place_walls()`
- `tests/test_gs05_wall_split.py` — new test file (mock data, no ETABS)

### Not Changed

- `model_config.json` schema — walls remain as full-length segments
- `beam_validate.py` — existing wall splitting remains (defense in depth)
- `config_build.py` — no changes

### Edge Cases

- **Zero-length walls**: Detected by `b_len_sq < EPS^2`, returned as-is
- **Walls with no intersections**: Returned as single segment (no cut points)
- **Wall endpoints at grid corners**: T_MIN (0.01) prevents cuts at wall start/end, avoiding zero-length segments
- **Collinear walls**: Endpoint projection handles shared junction points; if no beam/column exists at the junction, walls remain unsplit there (acceptable — structurally there must be a beam or column at any wall junction)
