# Phase 1 Beam Validation + slab_region_matrix Migration — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add beam connectivity validation to Phase 1 via a new `beam_validate.py` script, and move `slab_region_matrix` from Phase 1 READER to Phase 2 SB-READER.

**Architecture:** New deterministic `beam_validate.py` script imports geometry from `config_snap.py`, runs between `pptx_to_elements` and READER launch. Agent definitions updated to reflect shifted responsibilities.

**Tech Stack:** Python 3.11, JSON, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-03-13-phase1-beam-validation-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `golden_scripts/tools/beam_validate.py` | **CREATE** | Beam endpoint connectivity check + auto-snap |
| `tests/test_beam_validate.py` | **CREATE** | Tests for beam_validate.py |
| `golden_scripts/tools/config_build.py` | MODIFY | Remove `slab_region_matrix` from copy loop (line 322) |
| `tests/test_config_build.py` | MODIFY | Invert slab_region_matrix assertion (line 370-375) |
| `.claude/agents/phase1-reader.md` | MODIFY | Remove slab_region_matrix, add beam report review, update config_build path |
| `.claude/agents/phase2-sb-reader.md` | MODIFY | Add slab_region_matrix task + Step 3.5 injection |
| `.claude/commands/bts-structure.md` | MODIFY | Add Phase 0.6, update READER prompts, update RUN_CONFIG_BUILD |
| `.claude/commands/bts-sb.md` | MODIFY | Add slab_region_matrix to SB-READER prompts, update pipeline listing |
| `CLAUDE.md` | MODIFY | Update data flow docs, project structure, commands section |

---

## Chunk 1: beam_validate.py Core Script + Tests

### Task 1: Create beam_validate.py — geometry imports + target building

**Files:**
- Create: `golden_scripts/tools/beam_validate.py`
- Reference: `golden_scripts/tools/config_snap.py` (import from here)

- [ ] **Step 1: Create the file with imports and target-building logic**

```python
"""
Beam Validate Tool — Check major beam endpoint connectivity and auto-snap.

Validates that every beam endpoint in elements.json connects to a column, wall,
grid intersection, or another beam (including mid-segment T-junctions). Floating
endpoints are auto-snapped to the nearest structural element.

Usage:
    python -m golden_scripts.tools.beam_validate \
        --elements elements.json \
        --grid-data grid_data.json \
        --output elements_validated.json \
        --tolerance 0.3 \
        --report beam_validation_report.json

    # Preview without writing:
    python -m golden_scripts.tools.beam_validate ... --dry-run
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


# ── Target Building ──────────────────────────────────────────

def build_beam_targets(elements, grid_data):
    """Build snap targets from grid intersections + columns + walls + beams.

    Returns list of (SnapTarget, target_type, target_label) tuples.
    """
    targets = []

    # Grid intersections → points (no floor restriction)
    x_coords = [g["coordinate"] for g in grid_data.get("x", [])]
    y_coords = [g["coordinate"] for g in grid_data.get("y", [])]
    x_labels = [g["label"] for g in grid_data.get("x", [])]
    y_labels = [g["label"] for g in grid_data.get("y", [])]

    for ix, xc in enumerate(x_coords):
        for iy, yc in enumerate(y_coords):
            label = f"{x_labels[ix]}/{y_labels[iy]}"
            targets.append((
                SnapTarget("point", xc, yc, xc, yc, []),
                "grid_intersection", label))

    # Columns → points
    for col in elements.get("columns", []):
        x, y = col["grid_x"], col["grid_y"]
        sec = col.get("section", "")
        floors = col.get("floors", [])
        targets.append((
            SnapTarget("point", x, y, x, y, floors),
            "column", f"{sec} at ({x},{y})"))

    # Walls → segments
    for wall in elements.get("walls", []):
        floors = wall.get("floors", [])
        sec = wall.get("section", "")
        targets.append((
            SnapTarget("segment", wall["x1"], wall["y1"],
                        wall["x2"], wall["y2"], floors),
            "wall_segment", f"{sec}"))

    # Beams → segments (for T-junction snapping)
    for beam in elements.get("beams", []):
        floors = beam.get("floors", [])
        sec = beam.get("section", "")
        targets.append((
            SnapTarget("segment", beam["x1"], beam["y1"],
                        beam["x2"], beam["y2"], floors),
            "beam_segment", f"{sec}"))

    return targets


def find_nearest_target(px, py, floors, targets, tolerance):
    """Find nearest target within tolerance.

    For grid_intersection targets, floor overlap check is skipped.
    For other targets, floor overlap is required.

    Returns (snapped_x, snapped_y, distance, target_type, target_label) or None.
    """
    best = None
    best_dist = tolerance + 1

    for snap_target, ttype, tlabel in targets:
        # Grid intersections: skip floor overlap check
        if ttype != "grid_intersection":
            if not floors_overlap(floors, snap_target.floors):
                continue

        nx, ny, d = snap_target.nearest(px, py)
        if d < best_dist:
            best_dist = d
            best = (nx, ny, d, ttype, tlabel)

    if best is not None and best_dist <= tolerance:
        return best
    return None
```

- [ ] **Step 2: Verify file parses without errors**

Run: `python -c "import golden_scripts.tools.beam_validate"`
Expected: No output (clean import)

---

### Task 2: Add the core validation algorithm

**Files:**
- Modify: `golden_scripts/tools/beam_validate.py`

- [ ] **Step 3: Add validate_beams() function**

Append after `find_nearest_target`:

```python
def validate_beams(elements, grid_data, tolerance=0.3):
    """Validate beam endpoints and auto-snap floating ones.

    Returns (corrected_elements, report_dict).
    """
    elements = json.loads(json.dumps(elements))  # deep copy
    beams = elements.get("beams", [])
    if not beams:
        return elements, {
            "total_beams": 0, "total_endpoints": 0,
            "snapped_endpoints": 0, "warning_endpoints": 0,
            "corrections": [], "warnings": [],
        }

    targets = build_beam_targets(elements, grid_data)
    n = len(beams)

    report = {
        "total_beams": n,
        "total_endpoints": n * 2,
        "snapped_endpoints": 0,
        "warning_endpoints": 0,
        "max_snap_distance": 0.0,
        "avg_snap_distance": 0.0,
        "corrections": [],
        "warnings": [],
    }
    sum_dist = 0.0

    # Multi-round snapping
    snapped_state = [[False, False] for _ in range(n)]  # [start, end]

    def snap_round(beam_targets, round_label):
        nonlocal sum_dist
        count = 0
        for i, beam in enumerate(beams):
            for ep in range(2):
                if snapped_state[i][ep]:
                    continue
                px = beam["x1"] if ep == 0 else beam["x2"]
                py = beam["y1"] if ep == 0 else beam["y2"]
                ep_name = "start" if ep == 0 else "end"

                # Exclude self from targets
                self_targets = [
                    (t, tt, tl) for t, tt, tl in beam_targets
                    if not (tt == "beam_segment" and
                            t.x1 == beam["x1"] and t.y1 == beam["y1"] and
                            t.x2 == beam["x2"] and t.y2 == beam["y2"])
                ]

                result = find_nearest_target(
                    px, py, beam.get("floors", []), self_targets, tolerance)

                if result:
                    nx, ny, d, ttype, tlabel = result
                    if d > 0:  # Only record if actually moved
                        nx = round(nx, 2)
                        ny = round(ny, 2)
                        report["corrections"].append({
                            "original_x1": beam["x1"],
                            "original_y1": beam["y1"],
                            "original_x2": beam["x2"],
                            "original_y2": beam["y2"],
                            "section": beam.get("section", ""),
                            "floors": beam.get("floors", []),
                            "endpoint": ep_name,
                            "original_coord": [px, py],
                            "corrected_coord": [nx, ny],
                            "snap_distance": round(d, 4),
                            "target_type": ttype,
                            "target_label": tlabel,
                        })
                        if ep == 0:
                            beam["x1"], beam["y1"] = nx, ny
                        else:
                            beam["x2"], beam["y2"] = nx, ny
                        sum_dist += d
                        report["max_snap_distance"] = max(
                            report["max_snap_distance"], d)
                        count += 1
                    snapped_state[i][ep] = True
                else:
                    # Check if already exactly on a target (d==0)
                    result_zero = find_nearest_target(
                        px, py, beam.get("floors", []), self_targets,
                        tolerance=999)
                    if result_zero and result_zero[2] < 1e-6:
                        snapped_state[i][ep] = True
        return count

    # Round 1: snap to grid intersections + columns + walls
    r1_targets = [
        (t, tt, tl) for t, tt, tl in targets
        if tt != "beam_segment"
    ]
    r1_count = snap_round(r1_targets, "R1")

    # Round 2: snap to all targets (including beams for T-junctions)
    r2_count = snap_round(targets, "R2")

    # Round 3: final pass with updated beam positions as targets
    updated_targets = build_beam_targets(elements, grid_data)
    r3_count = snap_round(updated_targets, "R3")

    report["snapped_endpoints"] = r1_count + r2_count + r3_count

    # Collect warnings for unsnapped endpoints
    for i, beam in enumerate(beams):
        for ep in range(2):
            if not snapped_state[i][ep]:
                px = beam["x1"] if ep == 0 else beam["x2"]
                py = beam["y1"] if ep == 0 else beam["y2"]
                ep_name = "start" if ep == 0 else "end"

                # Find nearest target for diagnostic
                self_targets = [
                    (t, tt, tl) for t, tt, tl in targets
                    if not (tt == "beam_segment" and
                            t.x1 == beam["x1"] and t.y1 == beam["y1"] and
                            t.x2 == beam["x2"] and t.y2 == beam["y2"])
                ]
                nearest = find_nearest_target(
                    px, py, beam.get("floors", []), self_targets,
                    tolerance=999)
                nearest_info = ""
                nearest_dist = None
                if nearest:
                    nearest_info = f"{nearest[3]} {nearest[4]} at ({nearest[0]:.2f},{nearest[1]:.2f})"
                    nearest_dist = round(nearest[2], 4)

                report["warnings"].append({
                    "original_x1": beam["x1"],
                    "original_y1": beam["y1"],
                    "original_x2": beam["x2"],
                    "original_y2": beam["y2"],
                    "section": beam.get("section", ""),
                    "floors": beam.get("floors", []),
                    "endpoint": ep_name,
                    "coord": [px, py],
                    "nearest_target": nearest_info,
                    "nearest_distance": nearest_dist,
                    "message": f"No target within {tolerance}m tolerance",
                })
                report["warning_endpoints"] += 1

    if report["snapped_endpoints"] > 0:
        report["avg_snap_distance"] = round(
            sum_dist / report["snapped_endpoints"], 4)
    report["max_snap_distance"] = round(report["max_snap_distance"], 4)

    # Check for zero-length beams after snap
    for i, beam in enumerate(beams):
        if (abs(beam["x1"] - beam["x2"]) < 1e-6 and
                abs(beam["y1"] - beam["y2"]) < 1e-6):
            report["warnings"].append({
                "original_x1": beam["x1"],
                "original_y1": beam["y1"],
                "original_x2": beam["x2"],
                "original_y2": beam["y2"],
                "section": beam.get("section", ""),
                "floors": beam.get("floors", []),
                "endpoint": "both",
                "coord": [beam["x1"], beam["y1"]],
                "nearest_target": "",
                "nearest_distance": 0,
                "message": "Beam became zero-length after snap",
            })

    return elements, report
```

- [ ] **Step 4: Verify function is importable**

Run: `python -c "from golden_scripts.tools.beam_validate import validate_beams; print('OK')"`
Expected: `OK`

---

### Task 3: Add CLI interface

**Files:**
- Modify: `golden_scripts/tools/beam_validate.py`

- [ ] **Step 5: Add main() and CLI**

Append at end of file:

```python
def main():
    parser = argparse.ArgumentParser(
        description="Validate beam endpoint connectivity and auto-snap floating endpoints")
    parser.add_argument("--elements", required=True,
                        help="Path to elements.json (pptx_to_elements output)")
    parser.add_argument("--grid-data", required=True,
                        help="Path to grid_data.json (read_grid output)")
    parser.add_argument("--output", required=True,
                        help="Path for corrected elements output")
    parser.add_argument("--tolerance", type=float, default=0.3,
                        help="Snap tolerance in meters (default: 0.3)")
    parser.add_argument("--report",
                        help="Path for validation report JSON (optional)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing output")
    args = parser.parse_args()

    # Load inputs
    with open(args.elements, encoding="utf-8") as f:
        elements = json.load(f)
    with open(args.grid_data, encoding="utf-8") as f:
        grid_data = json.load(f)

    beams = elements.get("beams", [])
    print(f"Elements loaded: {args.elements}")
    print(f"  columns: {len(elements.get('columns', []))}")
    print(f"  beams: {len(beams)}")
    print(f"  walls: {len(elements.get('walls', []))}")
    print(f"Grid data loaded: {args.grid_data}")
    x_grids = grid_data.get("x", [])
    y_grids = grid_data.get("y", [])
    print(f"  x grids: {len(x_grids)}, y grids: {len(y_grids)}")
    print(f"  tolerance: {args.tolerance}m")

    if not beams:
        print("\nNo beams to validate. Copying input to output.")
        if not args.dry_run:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(elements, f, ensure_ascii=False, indent=2)
            print(f"Output written to: {args.output}")
        return

    # Run validation
    corrected, report = validate_beams(elements, grid_data, args.tolerance)

    # Console summary
    print(f"\n--- Beam Validation Summary ---")
    print(f"  Total beams: {report['total_beams']}")
    print(f"  Total endpoints: {report['total_endpoints']}")
    print(f"  Snapped endpoints: {report['snapped_endpoints']}")
    print(f"  Warning endpoints: {report['warning_endpoints']}")
    if report["snapped_endpoints"] > 0:
        print(f"  Max snap distance: {report['max_snap_distance']}m")
        print(f"  Avg snap distance: {report['avg_snap_distance']}m")

    if report["corrections"]:
        print(f"\nCorrections ({len(report['corrections'])}):")
        for c in report["corrections"]:
            print(f"  {c['section']} {c['endpoint']}: "
                  f"({c['original_coord'][0]},{c['original_coord'][1]}) → "
                  f"({c['corrected_coord'][0]},{c['corrected_coord'][1]}) "
                  f"d={c['snap_distance']}m → {c['target_type']} {c['target_label']}")

    if report["warnings"]:
        print(f"\nWARNINGS ({len(report['warnings'])}):")
        for w in report["warnings"]:
            print(f"  WARNING: {w['section']} {w['endpoint']} "
                  f"at ({w['coord'][0]},{w['coord'][1]}): {w['message']}")

    if args.dry_run:
        print(f"\n[DRY RUN] No output written.")
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(corrected, f, ensure_ascii=False, indent=2)
        print(f"\nValidated elements written to: {args.output}")

        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"Report written to: {args.report}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Verify CLI help works**

Run: `cd "C:/Users/User/Desktop/workflow dev/V22 AGENTIC MODEL" && python -m golden_scripts.tools.beam_validate --help`
Expected: Shows help text with `--elements`, `--grid-data`, `--output`, `--tolerance`, `--report`, `--dry-run` arguments.

- [ ] **Step 7: Commit beam_validate.py**

```bash
git add golden_scripts/tools/beam_validate.py
git commit -m "feat: add beam_validate.py — beam endpoint connectivity validation + auto-snap"
```

---

### Task 4: Write tests for beam_validate.py

**Files:**
- Create: `tests/test_beam_validate.py`

- [ ] **Step 8: Write test file**

```python
"""Tests for golden_scripts.tools.beam_validate."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.beam_validate import (
    build_beam_targets,
    find_nearest_target,
    validate_beams,
)


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def grid_data():
    """Simple 3x3 grid: X = 0, 8, 16; Y = 0, 6, 12."""
    return {
        "x": [
            {"label": "A", "coordinate": 0.0},
            {"label": "B", "coordinate": 8.0},
            {"label": "C", "coordinate": 16.0},
        ],
        "y": [
            {"label": "1", "coordinate": 0.0},
            {"label": "2", "coordinate": 6.0},
            {"label": "3", "coordinate": 12.0},
        ],
    }


@pytest.fixture
def simple_elements():
    """Columns at grid intersections + beams along grid lines."""
    return {
        "columns": [
            {"grid_x": 0.0, "grid_y": 0.0, "section": "C80X80",
             "floors": ["1F", "2F"]},
            {"grid_x": 8.0, "grid_y": 0.0, "section": "C80X80",
             "floors": ["1F", "2F"]},
            {"grid_x": 16.0, "grid_y": 0.0, "section": "C80X80",
             "floors": ["1F", "2F"]},
            {"grid_x": 0.0, "grid_y": 6.0, "section": "C80X80",
             "floors": ["1F", "2F"]},
            {"grid_x": 8.0, "grid_y": 6.0, "section": "C80X80",
             "floors": ["1F", "2F"]},
        ],
        "beams": [
            # Beam on grid line, exact coords
            {"x1": 0.0, "y1": 0.0, "x2": 8.0, "y2": 0.0,
             "section": "B55X80", "floors": ["1F", "2F"]},
            # Beam on grid line, exact coords
            {"x1": 8.0, "y1": 0.0, "x2": 16.0, "y2": 0.0,
             "section": "B55X80", "floors": ["1F", "2F"]},
            # Beam along Y
            {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 6.0,
             "section": "B40X70", "floors": ["1F", "2F"]},
        ],
        "walls": [
            {"x1": 8.0, "y1": 0.0, "x2": 8.0, "y2": 6.0,
             "section": "W25", "floors": ["1F", "2F"]},
        ],
    }


# ── Target Building ──────────────────────────────────────────

class TestBuildBeamTargets:
    def test_grid_intersections_count(self, simple_elements, grid_data):
        targets = build_beam_targets(simple_elements, grid_data)
        grid_targets = [t for t, tt, tl in targets if tt == "grid_intersection"]
        assert len(grid_targets) == 9  # 3x3

    def test_column_targets(self, simple_elements, grid_data):
        targets = build_beam_targets(simple_elements, grid_data)
        col_targets = [t for t, tt, tl in targets if tt == "column"]
        assert len(col_targets) == 5

    def test_beam_segment_targets(self, simple_elements, grid_data):
        targets = build_beam_targets(simple_elements, grid_data)
        beam_targets = [t for t, tt, tl in targets if tt == "beam_segment"]
        assert len(beam_targets) == 3

    def test_wall_segment_targets(self, simple_elements, grid_data):
        targets = build_beam_targets(simple_elements, grid_data)
        wall_targets = [t for t, tt, tl in targets if tt == "wall_segment"]
        assert len(wall_targets) == 1


# ── Snap to Grid Intersection ────────────────────────────────

class TestSnapToGridIntersection:
    def test_beam_endpoint_snaps_to_grid(self, grid_data):
        """Beam endpoint slightly off grid should snap to grid intersection."""
        elements = {
            "columns": [],
            "beams": [
                {"x1": 0.05, "y1": -0.03, "x2": 7.98, "y2": 0.02,
                 "section": "B55X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        corrected, report = validate_beams(elements, grid_data, tolerance=0.3)
        beam = corrected["beams"][0]
        assert beam["x1"] == 0.0
        assert beam["y1"] == 0.0
        assert beam["x2"] == 8.0
        assert beam["y2"] == 0.0
        assert report["snapped_endpoints"] >= 2

    def test_grid_intersection_no_floor_check(self, grid_data):
        """Grid intersection targets should work regardless of floor lists."""
        elements = {
            "columns": [],
            "beams": [
                {"x1": 0.05, "y1": 0.0, "x2": 8.0, "y2": 0.0,
                 "section": "B55X80", "floors": ["99F"]},
            ],
            "walls": [],
        }
        corrected, report = validate_beams(elements, grid_data, tolerance=0.3)
        assert corrected["beams"][0]["x1"] == 0.0


# ── Snap to Beam Mid-Segment (T-junction) ────────────────────

class TestTJunction:
    def test_beam_endpoint_snaps_to_beam_midpoint(self, grid_data):
        """A beam endpoint near the middle of another beam should snap to it."""
        elements = {
            "columns": [
                {"grid_x": 0.0, "grid_y": 0.0, "section": "C80X80",
                 "floors": ["1F"]},
                {"grid_x": 16.0, "grid_y": 0.0, "section": "C80X80",
                 "floors": ["1F"]},
                {"grid_x": 8.0, "grid_y": 6.0, "section": "C80X80",
                 "floors": ["1F"]},
            ],
            "beams": [
                # Horizontal beam from (0,0) to (16,0)
                {"x1": 0.0, "y1": 0.0, "x2": 16.0, "y2": 0.0,
                 "section": "B55X80", "floors": ["1F"]},
                # Vertical beam that should T-connect at (8.0, 0.0)
                # but has slight drift at start endpoint
                {"x1": 8.05, "y1": 0.12, "x2": 8.0, "y2": 6.0,
                 "section": "B40X70", "floors": ["1F"]},
            ],
            "walls": [],
        }
        corrected, report = validate_beams(elements, grid_data, tolerance=0.3)
        t_beam = corrected["beams"][1]
        # Should snap start to (8.0, 0.0) — on the horizontal beam
        assert abs(t_beam["x1"] - 8.0) < 0.01
        assert abs(t_beam["y1"] - 0.0) < 0.01


# ── Floor Overlap Check ──────────────────────────────────────

class TestFloorOverlap:
    def test_column_requires_floor_overlap(self, grid_data):
        """Column target should only snap if floors overlap."""
        elements = {
            "columns": [
                {"grid_x": 0.0, "grid_y": 0.0, "section": "C80X80",
                 "floors": ["1F"]},
            ],
            "beams": [
                {"x1": 0.05, "y1": 0.0, "x2": 8.0, "y2": 0.0,
                 "section": "B55X80", "floors": ["99F"]},
            ],
            "walls": [],
        }
        corrected, report = validate_beams(elements, grid_data, tolerance=0.3)
        # Should still snap to grid intersection (no floor check)
        # but NOT to column (floor mismatch)
        assert corrected["beams"][0]["x1"] == 0.0


# ── Warning for Floating Beams ───────────────────────────────

class TestWarnings:
    def test_floating_beam_produces_warning(self):
        """Beam far from any target should produce a warning."""
        grid_data = {
            "x": [{"label": "A", "coordinate": 0.0}],
            "y": [{"label": "1", "coordinate": 0.0}],
        }
        elements = {
            "columns": [],
            "beams": [
                {"x1": 50.0, "y1": 50.0, "x2": 60.0, "y2": 50.0,
                 "section": "B55X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        _, report = validate_beams(elements, grid_data, tolerance=0.3)
        assert report["warning_endpoints"] >= 1
        assert len(report["warnings"]) >= 1

    def test_zero_length_beam_warning(self, grid_data):
        """Beam that becomes zero-length after snap should warn."""
        elements = {
            "columns": [
                {"grid_x": 8.0, "grid_y": 0.0, "section": "C80X80",
                 "floors": ["1F"]},
            ],
            "beams": [
                # Both endpoints near the same column
                {"x1": 8.02, "y1": 0.01, "x2": 7.99, "y2": -0.01,
                 "section": "B55X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        _, report = validate_beams(elements, grid_data, tolerance=0.3)
        zero_len_warnings = [
            w for w in report["warnings"]
            if "zero-length" in w.get("message", "")]
        assert len(zero_len_warnings) >= 1


# ── Multi-Round Chain Dependency ─────────────────────────────

class TestMultiRoundChain:
    def test_chain_snap_across_rounds(self, grid_data):
        """Beam C snaps to Beam B, which was itself snapped in R1.

        Setup: Beam A is on-grid. Beam B has drifted start (snaps to grid in R1).
        Beam C endpoint is near Beam B's pre-snap position — should snap to
        Beam B's *corrected* position in R2/R3.
        """
        elements = {
            "columns": [
                {"grid_x": 0.0, "grid_y": 0.0, "section": "C80X80",
                 "floors": ["1F"]},
                {"grid_x": 8.0, "grid_y": 0.0, "section": "C80X80",
                 "floors": ["1F"]},
            ],
            "beams": [
                # Beam B: horizontal, start slightly off grid → snaps in R1
                {"x1": 0.08, "y1": 0.0, "x2": 8.0, "y2": 0.0,
                 "section": "B55X80", "floors": ["1F"]},
                # Beam C: vertical, end near Beam B midpoint (4.0, 0.1)
                # Should snap to (4.0, 0.0) on Beam B after Beam B is corrected
                {"x1": 4.0, "y1": 6.0, "x2": 4.0, "y2": 0.12,
                 "section": "B40X70", "floors": ["1F"]},
            ],
            "walls": [],
        }
        corrected, report = validate_beams(elements, grid_data, tolerance=0.3)
        # Beam B start should be snapped to grid (0.0, 0.0)
        assert corrected["beams"][0]["x1"] == 0.0
        # Beam C end should snap to (4.0, 0.0) on Beam B
        assert abs(corrected["beams"][1]["y2"] - 0.0) < 0.01


# ── No Changes Needed ────────────────────────────────────────

class TestNoChanges:
    def test_all_endpoints_exact(self, simple_elements, grid_data):
        """When all endpoints are exactly on targets, no corrections."""
        _, report = validate_beams(simple_elements, grid_data, tolerance=0.3)
        assert report["snapped_endpoints"] == 0
        assert report["warning_endpoints"] == 0
        assert len(report["corrections"]) == 0

    def test_empty_beams(self, grid_data):
        """Empty beams list should produce empty report."""
        elements = {"columns": [], "beams": [], "walls": []}
        corrected, report = validate_beams(elements, grid_data, tolerance=0.3)
        assert report["total_beams"] == 0
        assert corrected["beams"] == []


# ── Report Format ────────────────────────────────────────────

class TestReportFormat:
    def test_correction_has_required_fields(self, grid_data):
        """Each correction should have all required fields."""
        elements = {
            "columns": [],
            "beams": [
                {"x1": 0.1, "y1": 0.1, "x2": 8.0, "y2": 0.0,
                 "section": "B55X80", "floors": ["1F"]},
            ],
            "walls": [],
        }
        _, report = validate_beams(elements, grid_data, tolerance=0.3)
        assert len(report["corrections"]) >= 1
        c = report["corrections"][0]
        required = [
            "original_x1", "original_y1", "original_x2", "original_y2",
            "section", "floors", "endpoint", "original_coord",
            "corrected_coord", "snap_distance", "target_type", "target_label",
        ]
        for field in required:
            assert field in c, f"Missing field: {field}"

    def test_report_summary_fields(self, grid_data):
        """Report should have all summary fields."""
        elements = {"columns": [], "beams": [], "walls": []}
        _, report = validate_beams(elements, grid_data, tolerance=0.3)
        for field in ["total_beams", "total_endpoints", "snapped_endpoints",
                       "warning_endpoints", "corrections", "warnings"]:
            assert field in report
```

- [ ] **Step 9: Run tests and verify they pass**

Run: `cd "C:/Users/User/Desktop/workflow dev/V22 AGENTIC MODEL" && python -m pytest tests/test_beam_validate.py -v`
Expected: All tests PASS.

- [ ] **Step 10: Commit tests**

```bash
git add tests/test_beam_validate.py
git commit -m "test: add tests for beam_validate.py"
```

---

## Chunk 2: config_build.py — Remove slab_region_matrix

### Task 5: Remove slab_region_matrix from config_build.py

**Files:**
- Modify: `golden_scripts/tools/config_build.py:321-322`
- Modify: `tests/test_config_build.py:370-375`

- [ ] **Step 11: Update config_build.py — remove slab_region_matrix from copy loop**

In `golden_scripts/tools/config_build.py`, change line 321-322:

```python
# BEFORE:
    for key in ("building_outline", "substructure_outline",
                "core_grid_area", "slab_region_matrix"):

# AFTER:
    for key in ("building_outline", "substructure_outline",
                "core_grid_area"):
```

- [ ] **Step 12: Update test_config_build.py — invert slab_region_matrix assertion**

In `tests/test_config_build.py`, change `test_copies_grid_info_fields` (lines 367-375):

```python
# BEFORE:
    def test_copies_grid_info_fields(self, mock_elements, mock_grid_info):
        mock_grid_info["building_outline"] = [[0, 0], [10, 0], [10, 10], [0, 10]]
        mock_grid_info["core_grid_area"] = {"x_range": [3, 7], "y_range": [3, 7]}
        mock_grid_info["slab_region_matrix"] = {"1F": {"1~2/A~B": True}}
        config, _ = build_config(
            mock_elements, mock_grid_info, "Test", "C:/test.EDB")
        assert config["building_outline"] == [[0, 0], [10, 0], [10, 10], [0, 10]]
        assert "core_grid_area" in config
        assert "slab_region_matrix" in config

# AFTER:
    def test_copies_grid_info_fields(self, mock_elements, mock_grid_info):
        mock_grid_info["building_outline"] = [[0, 0], [10, 0], [10, 10], [0, 10]]
        mock_grid_info["core_grid_area"] = {"x_range": [3, 7], "y_range": [3, 7]}
        config, _ = build_config(
            mock_elements, mock_grid_info, "Test", "C:/test.EDB")
        assert config["building_outline"] == [[0, 0], [10, 0], [10, 10], [0, 10]]
        assert "core_grid_area" in config

    def test_slab_region_matrix_not_copied(self, mock_elements, mock_grid_info):
        mock_grid_info["slab_region_matrix"] = {"1F": {"1~2/A~B": True}}
        config, _ = build_config(
            mock_elements, mock_grid_info, "Test", "C:/test.EDB")
        assert "slab_region_matrix" not in config
```

- [ ] **Step 13: Run config_build tests**

Run: `cd "C:/Users/User/Desktop/workflow dev/V22 AGENTIC MODEL" && python -m pytest tests/test_config_build.py -v`
Expected: All tests PASS.

- [ ] **Step 14: Commit config_build changes**

```bash
git add golden_scripts/tools/config_build.py tests/test_config_build.py
git commit -m "refactor: remove slab_region_matrix from config_build.py (moved to Phase 2)"
```

---

## Chunk 3: Agent Definition Updates

### Task 6: Update phase1-reader.md

**Files:**
- Modify: `.claude/agents/phase1-reader.md`

- [ ] **Step 15: Remove slab_region_matrix + add beam validation review**

Apply these changes to `.claude/agents/phase1-reader.md`:

**a) Line 3 — Update description:**
```
# BEFORE:
description: "Phase 1 結構配置圖判讀 (PHASE1-READER)。解讀結構平面圖中的 Grid 名稱/座標、建物外框、樓板區域、強度分配。輸出 grid_info.json。用於 /bts-structure。"

# AFTER:
description: "Phase 1 結構配置圖判讀 (PHASE1-READER)。解讀結構平面圖中的 Grid 名稱/座標、建物外框、強度分配、大梁驗證報告審閱。輸出 grid_info.json。用於 /bts-structure。"
```

**b) Line 17 — Update summary:**
```
# BEFORE:
**你只處理**：Grid 驗證（比對 ETABS 資料 vs PPT）、建物外框、樓板區域判斷、強度分配、Story 高度。

# AFTER:
**你只處理**：Grid 驗證（比對 ETABS 資料 vs PPT）、建物外框、強度分配、Story 高度、大梁驗證報告審閱。
```

**c) Lines 50-51 — Replace slab_region_matrix with beam validation:**
```
# BEFORE:
5. **樓板區域判斷 (slab_region_matrix)**：每個 Grid 區域是否建板
   - 決策矩陣：四面梁圍合+有打叉→不建板；四面梁圍合+無打叉→建板

# AFTER:
5. **大梁驗證報告審閱 (beam validation review)**：審閱 `beam_validation_report.json`
   - 檢查修正摘要（snapped endpoints 數量、最大 snap 距離）
   - 對 WARNING 項目（超出容差的懸空梁）視覺交叉比對 PPT 圖面
   - 向 Team Lead 報告驗證結果（OK / WARN / issues found）
```

**d) Lines 83-86 — Remove slab_region_matrix from JSON schema:**
Delete these lines from the JSON example:
```
  "slab_region_matrix": {
    "1F~2F": {"B~C/7~8": true, "B~C/6~7": true, "C~D/7~8": false},
    "3F~14F": {"B~C/7~8": true}
  },
```

**e) Line 104 — Remove from required fields table:**
```
# BEFORE:
| slab_region_matrix | ✅ | 圖面打叉判斷 |

# AFTER:
(delete this row entirely)
```

**f) Line 134 — Update config_build command to use elements_validated.json:**
```
# BEFORE:
    --elements "{CASE_FOLDER}/elements.json" \

# AFTER:
    --elements "{CASE_FOLDER}/elements_validated.json" \
```

**g) Line 155 — Update Resume Protocol (remove 板區域):**
```
# BEFORE:
3. **處理新頁面**：讀取新頁面的 Grid / 建物外框 / 板區域資訊

# AFTER:
3. **處理新頁面**：讀取新頁面的 Grid / 建物外框資訊
```

**h) Line 32 — Update startup step to read elements_validated.json:**
```
# BEFORE:
2. **讀取 `elements.json`**

# AFTER:
2. **讀取 `elements_validated.json`**
```

- [ ] **Step 16: Verify the file is well-formed markdown**

Read the file back and confirm all edits are correct.

---

### Task 7: Update phase2-sb-reader.md

**Files:**
- Modify: `.claude/agents/phase2-sb-reader.md`

- [ ] **Step 17: Add slab_region_matrix task + Step 3.5 injection**

**a) After line 54 (after 步驟 5: 視覺交叉比對), add new step:**
```markdown
### 步驟 6：樓板區域判斷 (slab_region_matrix)（NEW）
從 PPT 圖面判斷每個 Grid 區域是否建板：
- 決策矩陣：四面梁圍合+有打叉→不建板；四面梁圍合+無打叉→建板
- 輸出 `{Case Folder}/結構配置圖/SB-BEAM/slab_region_matrix.json`：
```json
{
  "slab_region_matrix": {
    "1F~2F": {"B~C/7~8": true, "B~C/6~7": true},
    "3F~14F": {"B~C/7~8": true}
  }
}
```
- 只處理你負責驗證的樓層範圍
```

**b) Between Step 3 and Step 4 in SB Pipeline (line 117-118), add Step 3.5:**
```bash
# Step 3.5 (NEW): Inject slab_region_matrix into config
# Read slab_region_matrix.json, add field to snapped_config.json
python -c "
import json
with open('{CASE_FOLDER}/snapped_config.json', encoding='utf-8') as f:
    config = json.load(f)
with open('{CASE_FOLDER}/結構配置圖/SB-BEAM/slab_region_matrix.json', encoding='utf-8') as f:
    srm = json.load(f)
config['slab_region_matrix'] = srm.get('slab_region_matrix', {})
with open('{CASE_FOLDER}/snapped_config.json', 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)
print('slab_region_matrix injected into snapped_config.json')
"
```

**c) Add implementation note about slab_region_matrix format:**

After the Step 3.5 code block in the SB Pipeline, add this note:

```markdown
**⚠ 已知格式問題**：`slab_generator.py` 的 `_in_slab_region()` 目前預期 list-of-bounds 格式，
但 SB-READER 輸出的是 dict-of-dicts 格式（以樓層範圍和 Grid 區域字串為 key）。
執行此計畫時，需在 Step 3.5 injection 中加入格式轉換，或更新 `slab_generator.py` 以解析 dict-of-dicts 格式。
此為既存問題，不在本計畫範圍內，但執行者需注意。
```

- [ ] **Step 18: Verify the file is well-formed markdown**

Read the file back and confirm all edits are correct.

---

### Task 8: Update bts-structure.md

**Files:**
- Modify: `.claude/commands/bts-structure.md`

- [ ] **Step 19: Add Phase 0.6 + update READER prompts + update RUN_CONFIG_BUILD**

**a) After Phase 0.5 (line 141), add Phase 0.6:**
```markdown
### Phase 0.6: 大梁座標驗證（beam_validate.py）

PPT 提取的大梁座標可能與 ETABS Grid 座標有微小偏差。執行確定性驗證腳本：

```bash
python -m golden_scripts.tools.beam_validate \
    --elements "{Case Folder}/elements.json" \
    --grid-data "{Case Folder}/grid_data.json" \
    --output "{Case Folder}/elements_validated.json" \
    --report "{Case Folder}/beam_validation_report.json"
```

**驗證結果**：
- 檢查 console 輸出的 snapped endpoints 數量
- 如有 WARNING（懸空梁），記錄後傳給 READER 視覺確認
- `elements_validated.json` 將取代 `elements.json` 用於後續步驟
```

**b) READER-A prompt (line 192-197) — remove 板區域, add beam review:**
```
# BEFORE:
你的職責（Reduced）：
1. Grid 驗證：比對 ETABS Grid 資料與 PPT 圖面上的 Grid 線位置，確認一致性
2. 建物外框 (building_outline) polygon
3. 板區域判斷 (slab_region_matrix)
4. 強度分配 (strength_map) — 如圖面有標註
5. 屋突核心區 (core_grid_area) — 如 READER-B 未涵蓋，從標準層圖面辨識電梯/樓梯 Grid 範圍

# AFTER:
你的職責（Reduced）：
1. Grid 驗證：比對 ETABS Grid 資料與 PPT 圖面上的 Grid 線位置，確認一致性
2. 建物外框 (building_outline) polygon
3. 強度分配 (strength_map) — 如圖面有標註
4. 屋突核心區 (core_grid_area) — 如 READER-B 未涵蓋，從標準層圖面辨識電梯/樓梯 Grid 範圍
5. 大梁驗證報告審閱 — 讀取 beam_validation_report.json，對 WARNING 項目視覺確認
```

**c) READER-B prompt (line 234-239) — same change:**
```
# BEFORE:
你的職責（Reduced）：
1. Grid 驗證：比對 ETABS Grid 資料與 PPT 圖面上的 Grid 線位置，確認一致性
2. 建物外框 (building_outline) polygon（如與 READER-A 不同範圍）
3. 板區域判斷 (slab_region_matrix) — 你的樓層範圍
4. 強度分配 (strength_map) — 如圖面有標註
5. 屋突核心區 (core_grid_area) — 從標準層圖面辨識電梯井和樓梯間的 Grid 範圍（必要）

# AFTER:
你的職責（Reduced）：
1. Grid 驗證：比對 ETABS Grid 資料與 PPT 圖面上的 Grid 線位置，確認一致性
2. 建物外框 (building_outline) polygon（如與 READER-A 不同範圍）
3. 強度分配 (strength_map) — 如圖面有標註
4. 屋突核心區 (core_grid_area) — 從標準層圖面辨識電梯井和樓梯間的 Grid 範圍（必要）
5. 大梁驗證報告審閱 — 讀取 beam_validation_report.json，對 WARNING 項目視覺確認
```

**d) READER-A/B prompts — update elements.json path + add beam_validation_report.json path:**
In both READER-A and READER-B prompts, update:
```
# BEFORE:
elements.json 路徑：{Case Folder}/elements.json（供交叉比對）

# AFTER:
elements_validated.json 路徑：{Case Folder}/elements_validated.json（已通過大梁驗證，供交叉比對）
beam_validation_report.json 路徑：{Case Folder}/beam_validation_report.json（審閱大梁驗證結果）
```

**e) READER-A description (line 177) — update:**
```
# BEFORE:
description="讀取 Grid/建物外框/板區域（樓層組 1）",

# AFTER:
description="讀取 Grid/建物外框/強度/大梁驗證（樓層組 1）",
```

**f) READER-B description (line 219) — update:**
```
# BEFORE:
description="讀取 Grid/建物外框/板區域（樓層組 2）",

# AFTER:
description="讀取 Grid/建物外框/強度/大梁驗證（樓層組 2）",
```

**g) Step D: RUN_CONFIG_BUILD (line 300) — update text:**
```
# BEFORE:
READER 會執行 `config_build.py` 腳本，將 `elements.json` + `grid_info.json` 合併為 `model_config.json`。

# AFTER:
READER 會執行 `config_build.py` 腳本，將 `elements_validated.json` + `grid_info.json` 合併為 `model_config.json`。
```

- [ ] **Step 20: Verify the file is well-formed markdown**

Read the file back and confirm all edits are correct.

---

### Task 9: Update bts-sb.md

**Files:**
- Modify: `.claude/commands/bts-sb.md`

- [ ] **Step 21: Add slab_region_matrix to SB-READER prompts + update pipeline listing**

**a) SB-READER-A prompt (after line 145) — add slab_region_matrix responsibility:**
Add to the "驗證項目" list:
```
5. 樓板區域判斷 (slab_region_matrix) — 讀取 PPT 圖面判斷哪些 Grid 區域建板（打叉=不建板）
   輸出路徑：{Case Folder}/結構配置圖/SB-BEAM/slab_region_matrix.json
   注意：只處理你負責的樓層範圍。如 SB-READER-B 也有板區域結果，Team Lead 會合併。
```

**b) SB-READER-B prompt (after line 183) — same addition:**
```
5. 樓板區域判斷 (slab_region_matrix) — 讀取 PPT 圖面判斷哪些 Grid 區域建板（打叉=不建板）
   輸出路徑：{Case Folder}/結構配置圖/SB-BEAM/slab_region_matrix_B.json
   注意：只處理你負責的樓層範圍。Team Lead 會將兩份結果合併為 slab_region_matrix.json。
```

**b2) Team Lead merge note — add after SB-READER launches (before RUN_SB_PIPELINE):**
Add a comment in the bts-sb.md flow noting:
```
# slab_region_matrix 合併：
# 如兩個 SB-READER 分別輸出 slab_region_matrix.json 和 slab_region_matrix_B.json，
# Team Lead 在發送 RUN_SB_PIPELINE 前合併兩份 dict-of-dicts（floor-range keys 不重疊，直接合併）。
```

**c) Pipeline listing (lines 232-236) — add Step 3.5:**
```
# BEFORE:
SB-READER 會依序執行 4 步腳本（見 phase2-sb-reader.md「SB Pipeline Step」）：
1. `sb_patch_build.py` → sb_patch.json
2. `config_merge` → merged_config.json
3. `config_snap` → snapped_config.json
4. `slab_generator` → final_config.json

# AFTER:
SB-READER 會依序執行 5 步腳本（見 phase2-sb-reader.md「SB Pipeline Step」）：
1. `sb_patch_build.py` → sb_patch.json
2. `config_merge` → merged_config.json
3. `config_snap` → snapped_config.json
3.5. inject `slab_region_matrix` → snapped_config.json (updated)
4. `slab_generator` → final_config.json
```

**d) Pipeline summary (lines 347-349) — add Step 3.5:**
```
# BEFORE:
Step 3: SB-READER 執行 SB Pipeline（4 步腳本，秒級完成）：
        sb_patch_build → config_merge → config_snap → slab_generator

# AFTER:
Step 3: SB-READER 執行 SB Pipeline（5 步腳本，秒級完成）：
        sb_patch_build → config_merge → config_snap → inject slab_region_matrix → slab_generator
```

**e) 中間檔案結構 (line 361) — add slab_region_matrix.json:**
Add under `SB-BEAM/`:
```
│   │   ├── slab_region_matrix.json  # SB-READER 板區域判斷結果
```

- [ ] **Step 22: Verify the file is well-formed markdown**

Read the file back and confirm all edits are correct.

- [ ] **Step 23: Commit all agent definition changes**

```bash
git add .claude/agents/phase1-reader.md .claude/agents/phase2-sb-reader.md .claude/commands/bts-structure.md .claude/commands/bts-sb.md
git commit -m "refactor: move slab_region_matrix to Phase 2, add beam validation to Phase 1"
```

---

## Chunk 4: CLAUDE.md Updates

### Task 10: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 24: Add beam_validate.py to Commands section**

Add after the "### Config Build Tool" section:

```markdown
### Beam Validate Tool (Phase 1 — beam endpoint check)
```bash
# Validate beam endpoints and auto-snap floating ones
python -m golden_scripts.tools.beam_validate \
    --elements elements.json \
    --grid-data grid_data.json \
    --output elements_validated.json \
    --report beam_validation_report.json

# Custom tolerance (default 0.3m):
python -m golden_scripts.tools.beam_validate ... --tolerance 0.3

# Preview without writing:
python -m golden_scripts.tools.beam_validate ... --dry-run
```
```

- [ ] **Step 25: Update Project Structure**

Add `beam_validate.py` to the tools listing:
```
│       ├── beam_validate.py              # Phase 1: beam endpoint connectivity check + auto-snap
```

- [ ] **Step 26: Update Intermediate File Structure**

Add new files:
```
├── elements_validated.json     # Phase 0.6 beam-validated elements
├── beam_validation_report.json # Phase 0.6 beam validation report
```

And under `SB-BEAM/`:
```
│   ├── slab_region_matrix.json  # Phase 2 SB-READER: 板區域判斷
```

- [ ] **Step 27: Update Phase 1 and Phase 2 data flow descriptions**

In the `### Phase 1: /bts-structure` section, update:

```
# BEFORE (Data flow line):
- **Data flow**: `grid_data.json` + `elements.json` + Readers → `grid_info.json` → `config_build.py` (deterministic merge, run by READER) → `model_config.json` → **Config-Builder executes** `run_all.py --steps 1,2,3,4,5,6` → ETABS model

# AFTER:
- **Pre-steps**:
  1. `read_grid.py` → `grid_data.json` (read Grid from ETABS as ground truth)
  2. `pptx_to_elements.py --phase phase1` → `elements.json` (deterministic element extraction)
  3. `beam_validate.py` → `elements_validated.json` + `beam_validation_report.json` (beam endpoint validation + auto-snap)
- **Data flow**: `grid_data.json` + `elements_validated.json` + Readers → `grid_info.json` → `config_build.py` (deterministic merge, run by READER) → `model_config.json` → **Config-Builder executes** `run_all.py --steps 1,2,3,4,5,6` → ETABS model
```

In the `### Phase 2: /bts-sb` section, update:

```
# BEFORE (Data flow line):
- **Data flow**: SB-Readers validate `sb_elements_aligned.json` → SB-Reader runs pipeline: `sb_patch_build.py` → `config_merge` → `config_snap` (0.15m) → `slab_generator.py` → `final_config.json` → ...

# AFTER:
- **Data flow**: SB-Readers validate `sb_elements_aligned.json` + identify `slab_region_matrix` → SB-Reader runs pipeline: `sb_patch_build.py` → `config_merge` → `config_snap` (0.15m) → inject `slab_region_matrix` → `slab_generator.py` → `final_config.json` → ...
```

Also add `slab_region_matrix` note:
```
- **Note**: `slab_region_matrix` (板區域判斷) moved from Phase 1 READER to Phase 2 SB-READER
```

- [ ] **Step 28: Commit CLAUDE.md changes**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for beam_validate.py + slab_region_matrix migration"
```

---

## Final Verification

- [ ] **Step 29: Run all tests**

```bash
cd "C:/Users/User/Desktop/workflow dev/V22 AGENTIC MODEL"
python -m pytest tests/test_beam_validate.py tests/test_config_build.py -v
```

Expected: All tests PASS.
