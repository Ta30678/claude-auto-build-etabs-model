# Phase 1 Update: Beam Connectivity Validation + slab_region_matrix Migration

**Date:** 2026-03-13
**Status:** Design approved

---

## Summary

Two changes to the Phase 1 (`/bts-structure`) workflow:

1. **Move `slab_region_matrix` from Phase 1 READER to Phase 2 SB-READER** — Phase 1 doesn't build slabs, so the slab region identification task belongs in Phase 2.
2. **Add major beam connectivity validation via new `beam_validate.py` script** — A deterministic script checks that every beam endpoint connects to a column, wall, or another beam (including mid-segment T-junctions). Floating endpoints are auto-snapped. READER reviews the report and visually confirms problematic beams.

---

## Change 1: Move slab_region_matrix to Phase 2

### Current State

- Phase 1 READER identifies `slab_region_matrix` (which grid cells get slabs) by detecting cross-hatching marks on PPT floor plans.
- This data is written to `grid_info.json` and copied into `model_config.json` by `config_build.py`.
- Phase 1 does NOT build slabs (`model_config.json` has `small_beams=[], slabs=[]`).

### Target State

- Phase 1 READER no longer has `slab_region_matrix` responsibility.
- Phase 2 SB-READER takes over `slab_region_matrix` identification.
- SB-READER outputs `slab_region_matrix` to a file that the SB Pipeline injects into the config before `slab_generator.py` runs.

### Files to Modify

| File | Action |
|------|--------|
| `.claude/agents/phase1-reader.md` | Remove `slab_region_matrix` from responsibilities (item 5), grid_info.json schema, and required fields table |
| `.claude/commands/bts-structure.md` | Remove "板區域判斷 (slab_region_matrix)" from READER-A and READER-B launch prompts |
| `.claude/agents/phase2-sb-reader.md` | Add `slab_region_matrix` as a new task (detect cross-hatching marks on PPT floor plans) |
| `.claude/commands/bts-sb.md` | Add `slab_region_matrix` to SB-READER launch prompts; update SB Pipeline to inject data |
| `golden_scripts/tools/config_build.py` | Remove `slab_region_matrix` from the optional-keys copy loop |
| `tests/test_config_build.py` | Remove/update `slab_region_matrix` assertion in `test_copies_grid_info_fields` |
| `CLAUDE.md` | Update Phase 1/Phase 2 data flow descriptions and intermediate file structure |

### Data Flow Change

**Before:**
```
Phase 1 READER → grid_info.json (includes slab_region_matrix)
    ↓
config_build.py copies slab_region_matrix → model_config.json
    ↓
Phase 2 config_merge preserves it → slab_generator.py reads from config
```

**After:**
```
Phase 2 SB-READER → slab_region_matrix.json (standalone file)
    ↓
SB Pipeline: inject slab_region_matrix into config BEFORE slab_generator.py
    ↓
slab_generator.py reads from config
```

### SB-READER slab_region_matrix Output

SB-READER writes `{Case Folder}/結構配置圖/SB-BEAM/slab_region_matrix.json`:

```json
{
  "slab_region_matrix": {
    "1F~2F": {"B~C/7~8": true, "B~C/6~7": true, "C~D/7~8": false},
    "3F~14F": {"B~C/7~8": true}
  }
}
```

Decision rule (unchanged): 四面梁圍合+有打叉→不建板；四面梁圍合+無打叉→建板。

### Two SB-READERs Merge Strategy

Since two SB-READERs each handle different floor ranges, their `slab_region_matrix` outputs cover different floor-range keys (e.g., SB-READER-A outputs `"1F~2F"`, SB-READER-B outputs `"3F~14F"`). The dict-of-dicts format naturally merges by concatenating floor-range keys:

- SB-READER-A writes its floor ranges first
- SB-READER-B appends (or the Team Lead merges after both complete)
- Since floor-range keys don't overlap, no conflict resolution needed

Alternatively, Team Lead can instruct one SB-READER to handle all slab_region_matrix identification (simpler, avoids merge entirely).

### Sequencing

SB-READER must complete `slab_region_matrix` identification **before** receiving `RUN_SB_PIPELINE`. The timeline:
1. SB-READER validates SB connectivity (existing steps 1-5)
2. SB-READER identifies slab_region_matrix from PPT images (new task, during validation phase)
3. SB-READER writes `slab_region_matrix.json` and reports completion
4. Team Lead sends `RUN_SB_PIPELINE`
5. SB Pipeline runs steps 1-4, including Step 3.5 injection

### Injection into Config

The SB Pipeline (run by SB-READER after `RUN_SB_PIPELINE` message) injects `slab_region_matrix` into the config **between `config_snap` and `slab_generator`**:

```bash
# Step 3: Snap SB coordinates
python -m golden_scripts.tools.config_snap \
    --input "{CASE_FOLDER}/merged_config.json" \
    --output "{CASE_FOLDER}/snapped_config.json" --tolerance 0.15

# Step 3.5 (NEW): Inject slab_region_matrix into config
# SB-READER reads slab_region_matrix.json and writes the field into snapped_config.json
# (simple JSON merge — read config, add slab_region_matrix key, write back)

# Step 4: Slab generation (reads slab_region_matrix from config)
python -m golden_scripts.tools.slab_generator \
    --config "{CASE_FOLDER}/snapped_config.json" \
    --slab-thickness {SLAB_THICKNESS} --raft-thickness {RAFT_THICKNESS} \
    --output "{CASE_FOLDER}/final_config.json"
```

**Implementation note:** Step 3.5 can be done by SB-READER reading snapped_config.json, adding the `slab_region_matrix` field, and writing it back. No new tool needed — just a few lines of JSON manipulation by the AI agent.

### Known Issue: slab_region_matrix Format

The current `slab_generator.py`'s `_in_slab_region()` function expects a **list-of-bounds** format, but the READER output uses a **dict-of-dicts** format keyed by floor range and grid zone strings. These formats are incompatible.

**Resolution:** This is a pre-existing bug. When implementing, either:
- Update `slab_generator.py` to parse the dict-of-dicts format (resolving grid zone strings like "B~C/7~8" to actual coordinates using the grid system), or
- Convert to the list-of-bounds format in the SB-READER or injection step.

This should be addressed during implementation, not in this spec.

---

## Change 2: Major Beam Connectivity Validation

### Problem

Phase 1 currently has **no beam endpoint validation**. Beams extracted from PPT (`pptx_to_elements.py`) may have endpoints that don't precisely align with columns, walls, or other beams due to:

- PPT coordinate extraction precision limitations
- Drift between PPT-meter coordinates and ETABS grid coordinates
- Drawing imprecision in the structural plan

In ETABS, beam endpoints must snap to points or lines. Floating beams create orphan joints and structural discontinuities.

### Solution

A new deterministic script `beam_validate.py` (in `golden_scripts/tools/`) checks beam connectivity and auto-snaps floating endpoints. READER reviews the generated report and visually confirms problematic beams against PPT images.

This follows the project's established pattern: mechanical/computational work → scripts; visual/judgment work → AI agents.

### New Script: `beam_validate.py`

**Location:** `golden_scripts/tools/beam_validate.py`

**Purpose:** Validate major beam endpoint connectivity and auto-snap floating endpoints. Produces a report + corrected elements file.

**CLI Interface:**
```bash
python -m golden_scripts.tools.beam_validate \
    --elements elements.json \
    --grid-data grid_data.json \
    --output elements_validated.json \
    --tolerance 0.3 \
    --report beam_validation_report.json

# Preview without writing:
python -m golden_scripts.tools.beam_validate ... --dry-run
```

**Inputs:**
- `elements.json` — PPT-extracted beam/column/wall coordinates (from `pptx_to_elements.py`)
- `grid_data.json` — ETABS Grid coordinates (from `read_grid.py`)

**Outputs:**
- `elements_validated.json` — Copy of elements.json with corrected beam coordinates
- `beam_validation_report.json` — Detailed report of all corrections and warnings

### Snap Target Types

| Element Type | Snap Target | Geometry | Floor Check |
|-------------|-------------|----------|-------------|
| Grid intersections | **point** | All x_grid × y_grid combinations from `grid_data.json` | Skipped (grid intersections apply to all floors) |
| Columns | **point** | Column center coordinates from `elements.json` | Must share at least one common floor |
| Walls | **segment** | Full wall line segment (any position along the wall) | Must share at least one common floor |
| Other major beams | **segment** | Full beam line segment (mid-beam = T-junction) | Must share at least one common floor |

**Note:** Grid intersections are an improvement over `config_snap.py` (which only uses columns/beams/walls). Grid intersections don't have floor lists, so floor overlap check is skipped for them. This catches beams that should land on a grid intersection where no column exists.

### Snap Algorithm

Reuses `config_snap.py`'s geometric utilities (`point_to_segment_nearest`, `SnapTarget`):

1. Build snap targets from grid intersections + columns + walls + beams
2. For each beam, check both endpoints:
   a. Calculate distance to all snap targets (point-to-point for columns/grid, point-to-segment for beams/walls)
   b. For non-grid targets, require floor overlap
   c. Find nearest target within **tolerance = 0.3m**
3. If target found: snap endpoint, record correction
4. If no target within tolerance: flag as WARNING (truly floating beam)
5. Round corrected coordinates to 1cm precision (0.01m)

**Multi-round snapping** (same as `config_snap.py`):
- Round 1: Snap to columns, walls, grid intersections
- Round 2: Snap to already-snapped beams (catches chain dependencies)
- Round 3: Final pass with all targets

### Validation Report Format

`beam_validation_report.json`:
```json
{
  "total_beams": 85,
  "total_endpoints": 170,
  "snapped_endpoints": 12,
  "warning_endpoints": 2,
  "max_snap_distance": 0.18,
  "avg_snap_distance": 0.07,
  "corrections": [
    {
      "original_x1": 8.50, "original_y1": 3.21,
      "original_x2": 8.50, "original_y2": 10.80,
      "section": "B55X80",
      "floors": ["1F~2F", "3F~14F"],
      "endpoint": "start",
      "original_coord": [8.50, 3.21],
      "corrected_coord": [8.40, 3.20],
      "snap_distance": 0.14,
      "target_type": "grid_intersection",
      "target_label": "C/7"
    }
  ],
  "warnings": [
    {
      "original_x1": 22.10, "original_y1": 5.55,
      "original_x2": 22.10, "original_y2": 12.00,
      "section": "B40X70",
      "floors": ["1F~2F"],
      "endpoint": "start",
      "coord": [22.10, 5.55],
      "nearest_target": "Column at (22.40, 5.60)",
      "nearest_distance": 0.31,
      "message": "No target within 0.3m tolerance"
    }
  ]
}
```

### Updated Phase 1 Pipeline

```
pptx_to_elements.py --phase phase1 → elements.json
read_grid.py → grid_data.json
                    ↓
beam_validate.py → elements_validated.json + beam_validation_report.json  (NEW)
                    ↓
READER-A/B: Grid驗證 + 外框 + 核心區 + 強度 + 【審閱 beam validation report】
                    ↓
grid_info.json (NO slab_region_matrix, NO beam_corrections — corrections already in elements_validated.json)
                    ↓
config_build.py: elements_validated.json + grid_info.json → model_config.json
                    ↓
CONFIG-BUILDER: run_all.py --steps 1,2,3,4,5,6
```

**Key change:** The call sites (`bts-structure.md` and `phase1-reader.md`) pass `elements_validated.json` to `config_build.py` instead of raw `elements.json`. The `config_build.py` script itself needs no code changes for beam validation (the input filename is a CLI argument `--elements`). No `beam_corrections` field needed in `grid_info.json`.

### READER's Role (Review Only)

READER no longer performs the computational validation. Instead:

1. **Review report**: Read `beam_validation_report.json`, check corrections summary
2. **Visual confirmation**: For WARNING items (floating beams beyond tolerance), cross-reference against PPT crop images to determine if the beam is real or extraction error
3. **Report to Team Lead**: Via SendMessage, report validation result (OK/WARN/issues found)

If READER identifies issues that `beam_validate.py` missed or misjudged, they notify Team Lead who can manually adjust `elements_validated.json`.

### Where `beam_validate.py` Runs in the Flow

**Run by Team Lead** (in `bts-structure.md` Phase 0.5, after `pptx_to_elements.py`):

```bash
# Phase 0.5: Extract elements from PPT
python -m golden_scripts.tools.pptx_to_elements ... --output elements.json

# Phase 0.6 (NEW): Validate and snap beam endpoints
python -m golden_scripts.tools.beam_validate \
    --elements "{Case Folder}/elements.json" \
    --grid-data "{Case Folder}/grid_data.json" \
    --output "{Case Folder}/elements_validated.json" \
    --report "{Case Folder}/beam_validation_report.json"

# Team Lead reviews summary, then passes elements_validated.json to Readers + config_build
```

### Edge Cases

| Case | Handling |
|------|----------|
| Duplicate beams at same coordinates (different floor ranges) | Same correction applied to all — coordinates are identical so the same snap applies |
| Beams with empty section | Snap targets don't use section, only coordinates + floors. Section is only in the report for human readability |
| Beam endpoint connects to another beam's mid-segment | Handled by segment-type snap target (`point_to_segment_nearest`) |
| All beam endpoints already within tolerance | Report shows 0 corrections, script copies elements.json unchanged |
| Zero-length beam after snap | Flagged as WARNING, not auto-removed (Team Lead decides) |

---

## Updated Phase 1 READER Responsibilities

After these changes:

1. **Grid 驗證**: Compare ETABS Grid data vs PPT Grid lines (unchanged)
2. **Story 定義**: Floor names and heights (unchanged)
3. **建築外框 (building_outline)**: Polygon coordinates (unchanged)
4. **屋突核心區 (core_grid_area)**: Elevator/stairwell Grid range (unchanged)
5. ~~**樓板區域判斷 (slab_region_matrix)**~~: **REMOVED** — moved to Phase 2 SB-READER
6. **強度分配 (strength_map)**: Concrete grades by floor range (unchanged)
7. **大梁驗證報告審閱 (beam validation review)**: **NEW** — Review `beam_validation_report.json`, visually confirm WARNING items, report to Team Lead

---

## Updated Phase 2 SB-READER Responsibilities

After these changes:

1. **SB 連接性驗證**: Validate small beam connectivity (unchanged)
2. **等分模式檢查**: Check for equal-spacing patterns (unchanged)
3. **Grid 邊界檢查**: SB coordinates within Grid bounds (unchanged)
4. **視覺交叉比對**: Visual cross-reference against PPT (unchanged)
5. **樓板區域判斷 (slab_region_matrix)**: **NEW** — Read PPT images to identify which grid cells get slabs (detect cross-hatching marks)
6. **SB Pipeline**: Execute sb_patch_build → config_merge → config_snap → **inject slab_region_matrix** → slab_generator (updated)

---

## Complete Files to Modify

| File | Change 1 (slab) | Change 2 (beam) | Specific Locations |
|------|-----------------|-----------------|-------------------|
| `.claude/agents/phase1-reader.md` | Remove slab_region_matrix from: responsibilities item 5, grid_info.json schema, required fields table row | Add "大梁驗證報告審閱" responsibility; Update Config Build Step to use `elements_validated.json` instead of `elements.json` | Lines 50-51, 83-84, 104, 134 |
| `.claude/agents/phase2-sb-reader.md` | Add slab_region_matrix task + output step; Add Step 3.5 injection to SB Pipeline | — | After line 54 (new task), between lines 113-122 (pipeline step) |
| `.claude/commands/bts-structure.md` | Remove "板區域判斷" from READER-A/B launch prompts | Add Phase 0.6 `beam_validate.py` step; Add "大梁驗證報告審閱" to READER-A/B launch prompts; Update RUN_CONFIG_BUILD to pass `elements_validated.json` | Lines 195-197, 237-239, 293-298 |
| `.claude/commands/bts-sb.md` | Add "板區域判斷" to SB-READER launch prompts; Update SB Pipeline listing to include Step 3.5 | — | READER prompts + pipeline step listing |
| `golden_scripts/tools/config_build.py` | Remove `slab_region_matrix` from optional-keys copy loop | No code changes (input filename passed via CLI `--elements` arg) | Line 321-323 |
| `golden_scripts/tools/beam_validate.py` | — | **NEW FILE** — deterministic beam connectivity validator. Import geometric utilities from `config_snap.py` (`point_to_segment_nearest`, `SnapTarget`, `floors_overlap`). | — |
| `tests/test_config_build.py` | Invert `slab_region_matrix` assertion to `assert "slab_region_matrix" not in config` | — | Lines 370-375 |
| `tests/test_beam_validate.py` | — | **NEW FILE** — tests for beam_validate.py | — |
| `CLAUDE.md` | Update Phase 1/2 data flow; Update intermediate file structure (add `slab_region_matrix.json`) | Add `beam_validate.py` to commands + project structure; Add `elements_validated.json` and `beam_validation_report.json` to intermediate file structure | Multiple sections |

---

## Test Considerations

- `tests/test_beam_validate.py`: Test snap to grid intersection, snap to beam mid-segment (T-junction), floor overlap filtering, WARNING for beams beyond tolerance, zero-length beam detection.
- `tests/test_config_build.py`: Update `test_copies_grid_info_fields` to not expect `slab_region_matrix`.
- Manual testing: Run Phase 1 on an existing project and verify beam endpoints connect properly in ETABS.
