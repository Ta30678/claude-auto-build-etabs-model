# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This project uses Claude Code to control ETABS 22 via its COM API (Python + comtypes). There are four workflows:

1. **Phased BTS (`/bts-structure` + `/bts-sb` + `/bts-props`)** — **Preferred.** Split into 3 phases. Reduces token bloat and improves AI quality.
   - Phase 1 `/bts-structure`: Grid + Story + Columns + Walls + Major Beams → `model_config.json`
   - Phase 2 `/bts-sb`: Small Beams + Slabs → `sb_slabs_patch.json` → merge → add to model
   - Phase 3 `/bts-props`: Properties + Loads + Diaphragms (no agent team, deterministic)
2. **Single-pass Golden Scripts (`/bts-gs`)** — All-in-one 3-agent team. May consume excessive tokens on complex projects.
3. **Legacy BTS (`/bts`)** — 4-agent team where AI generates and executes Python code directly. Slower, higher token usage.
4. **Ad-hoc scripting** — Claude writes one-off Python scripts for model modification, analysis, or data extraction.

---

## ETABS Connection (MANDATORY)

```python
from find_etabs import find_etabs
etabs, filename = find_etabs(run=False, backup=False)
SapModel = etabs.SapModel
```

**Do NOT use `comtypes.client.GetActiveObject()` directly.** Always use `etabs_api` via `find_etabs`. It handles COM type conversion issues.

For operations not covered by `etabs_api`, access the raw API through `etabs.SapModel.*`.

---

## Environment

- **ETABS 22**: `C:/Program Files/Computers and Structures/ETABS 22/ETABS.exe`
- **Python**: 3.11.7 with `comtypes` 1.4.16, `numpy`, `pandas`, `etabs_api`
- **Default units**: kgf-cm (code 14). Golden Scripts use Ton-m (code 12).

---

## Project Structure

```
claude-auto-build-etabs-model/
├── golden_scripts/
│   ├── run_all.py              # Master orchestrator (--config, --steps, --dry-run)
│   ├── constants.py            # All hardcoded rules (modifiers, rebar, parsing, story classification)
│   ├── config_schema.json      # JSON Schema for model_config.json
│   ├── example_config.json     # A21 reference config
│   ├── modeling/               # gs_01_init → gs_11_diaphragms (11 sequential build steps)
│   ├── design/                 # gs_12_iterate (analysis-design iteration)
│   ├── tools/                  # Standalone CLI tools (pptx_to_elements, affine_calibrate, beam_validate,
│   │                           #   sb_validate, slab_generator, config_build, elements_merge, plot_elements, etc.)
│   └── qc/                     # QC verification scripts
├── tests/                      # pytest suite — mock tests (no ETABS) + ETABS verification tests
│   └── conftest.py             # SapModel fixture (auto-skips when ETABS unavailable)
├── skills/                     # Skill definitions (structural-glossary, plan-reader, etabs-modeler, etc.)
├── .claude/
│   ├── agents/                 # BTS agent definitions (phase1-reader, phase2-sb-reader, config-builder, etc.)
│   └── commands/               # Slash command definitions (/bts-structure, /bts-sb, /bts-props, etc.)
├── api_docs/                   # Raw ETABS API HTML docs (1693 files)
│   ├── CSI API ETABS v1.hhc   # Searchable TOC
│   └── html/                   # Individual method documentation
├── api_docs_index/             # Pre-built API index (task_index.md, categories.json, full_toc.json)
└── models/                     # Output model files (.EDB)
```

---

## Commands

### Build a model with Golden Scripts (preferred)
```bash
# Full build
cd golden_scripts
python run_all.py --config path/to/model_config.json

# Run specific steps only (e.g., re-run columns + walls)
python run_all.py --config path/to/model_config.json --steps 4,5

# Preview without executing
python run_all.py --config path/to/model_config.json --dry-run
```

### Run tests
```bash
# Mock tests only (no ETABS needed) — tool logic, color matching, calibration, etc.
pytest tests/test_pptx_color_matching.py tests/test_beam_validate.py tests/test_sb_validate.py tests/test_slab_generator.py tests/test_affine_calibrate.py tests/test_config_build.py tests/test_elements_merge.py tests/test_sb_patch_build.py tests/test_plot_elements.py -v

# Single test file
pytest tests/test_pptx_color_matching.py -v

# Single test class or method
pytest tests/test_pptx_color_matching.py::TestBuildRectColorMap -v
pytest tests/test_beam_validate.py::TestRaySnap::test_snap_to_nearest -v

# ETABS verification tests (requires ETABS running with model open)
pytest tests/ -v
pytest tests/ -v --config path/to/model_config.json    # with config comparison

# ETABS tests auto-skip when ETABS is not running (conftest.py SapModel fixture skips gracefully)
```

### QC Phase 1 (after /bts-structure)
```bash
python -m golden_scripts.qc.qc_phase1 --config path/to/model_config.json
```

### Deterministic Element Extraction (used by /bts-structure and /bts-sb)

```bash
# Phase 1 (per-slide mode): per-slide JSONs + screenshots to SLIDES INFO/
python -m golden_scripts.tools.pptx_to_elements \
    --input 結構配置圖/plan.pptx \
    --page-floors "1=B3F, 3=1F~2F, 4=3F~14F, 5=R1F~R3F" \
    --phase phase1 \
    --crop \
    --slides-info-dir "結構配置圖/SLIDES INFO"

# Phase 1 (legacy merged mode): single merged output
python -m golden_scripts.tools.pptx_to_elements \
    --input 結構配置圖/plan.pptx \
    --output elements.json \
    --page-floors "1=B3F, 3=1F~2F, 4=3F~14F, 5=R1F~R3F" \
    --phase phase1 \
    --crop --crop-dir "結構配置圖/"

# Phase 2 (per-slide mode): per-slide SB JSONs to SB SLIDES INFO/
python -m golden_scripts.tools.pptx_to_elements \
    --input 結構配置圖/plan.pptx \
    --page-floors "3=1F~2F, 4=3F~14F" \
    --phase phase2 \
    --slides-info-dir "結構配置圖/SB SLIDES INFO"

# Phase 2 (legacy merged mode): single merged output
python -m golden_scripts.tools.pptx_to_elements \
    --input 結構配置圖/plan.pptx \
    --output sb_elements.json \
    --page-floors "3=1F~2F, 4=3F~14F" \
    --phase phase2

# Scan floors with confidence scoring + confirm
python -m golden_scripts.tools.pptx_to_elements --input plan.pptx --scan-floors
python -m golden_scripts.tools.pptx_to_elements --input plan.pptx --confirm-floors --phase phase2 --output sb_elements.json

# List slides and shape counts
python -m golden_scripts.tools.pptx_to_elements --input plan.pptx --list-slides

# Preview without writing
python -m golden_scripts.tools.pptx_to_elements ... --dry-run
```

### Affine Calibrate Tool
```bash
# Phase 1 (grid mode): per-slide JSON + grid anchors → calibrated JSON
python -m golden_scripts.tools.affine_calibrate \
    --mode grid \
    --per-slide "SLIDES INFO/1F~2F/pptx_to_elements/1F~2F.json" \
    --grid-data grid_data.json \
    --grid-anchors "SLIDES INFO/1F~2F/grid_anchors_1F~2F.json" \
    --output "SLIDES INFO/1F~2F/calibrated/calibrated.json"

# Phase 2 (grid mode): per-slide SB JSON + Phase 1 grid anchors → calibrated SB
python -m golden_scripts.tools.affine_calibrate \
    --mode grid \
    --per-slide "SB SLIDES INFO/1F~2F/pptx_to_elements/sb_1F~2F.json" \
    --grid-data grid_data.json \
    --grid-anchors "SLIDES INFO/1F~2F/grid_anchors_1F~2F.json" \
    --output "SB SLIDES INFO/1F~2F/calibrated/calibrated.json"
```

### SB Validate Tool (Phase 2 — angle correction + snap + cluster + split)
```bash
# Full SB validation pipeline (replaces config_snap in Phase 2)
python -m golden_scripts.tools.sb_validate \
    --sb-elements sb_elements_aligned.json \
    --config model_config.json \
    --grid-data grid_data.json \
    --output sb_elements_validated.json \
    --report sb_validate_report.json

# Custom tolerances
python -m golden_scripts.tools.sb_validate \
    --sb-elements sb_elements_aligned.json \
    --config model_config.json \
    --grid-data grid_data.json \
    --output sb_elements_validated.json \
    --tolerance 1.0 --split-tolerance 0.30 --cluster-tolerance 0.30

# Disable angle correction, splitting, or clustering
python -m golden_scripts.tools.sb_validate \
    --sb-elements sb_elements_aligned.json \
    --config model_config.json \
    --grid-data grid_data.json \
    --output sb_elements_validated.json \
    --no-angle-correct --no-split --no-cluster

# Preview without writing
python -m golden_scripts.tools.sb_validate ... --dry-run
```

### Slab Generator Tool (Phase 2)
```bash
# Graph-based slab polygon generation from beam layout
python -m golden_scripts.tools.slab_generator \
    --config merged_config.json \
    --slab-thickness 15 \
    --raft-thickness 100 \
    --output final_config.json
```

### Elements Merge Tool (Phase 1 + Phase 2)
```bash
# Phase 1: Merge calibrated JSONs from SLIDES INFO
python -m golden_scripts.tools.elements_merge \
    --inputs-dir "SLIDES INFO" \
    --pattern "*/calibrated/calibrated.json" \
    --output elements.json

# Phase 2: Merge calibrated SB JSONs from SB SLIDES INFO
python -m golden_scripts.tools.elements_merge \
    --inputs-dir "SB SLIDES INFO" \
    --pattern "*/calibrated/calibrated.json" \
    --phase phase2 \
    --output sb_elements_validated.json

# Merge individual elements files
python -m golden_scripts.tools.elements_merge \
    --inputs elements_A.json elements_B.json \
    --output elements.json

# Preview without writing
python -m golden_scripts.tools.elements_merge ... --dry-run
```

### Plot Elements Tool (Visualization)
```bash
# Post-calibration with grid overlay
python -m golden_scripts.tools.plot_elements \
    --elements "SLIDES INFO/1F/calibrated/calibrated.json" \
    --grid-data grid_data.json \
    --output "SLIDES INFO/1F/calibrated/calibrated.png"

# Post-extraction (no grid, PPT-meter coords)
python -m golden_scripts.tools.plot_elements \
    --elements "SLIDES INFO/1F/pptx_to_elements/1F.json" \
    --output "SLIDES INFO/1F/pptx_to_elements/1F.png"

# Options
python -m golden_scripts.tools.plot_elements \
    --elements elements.json --output plot.png \
    --dpi 150 --no-labels --title "Custom Title"
```

### Beam Validate Tool (Phase 1 — angle correction + ray snap + clustering + split)
```bash
# Per-slide: angle-correct, ray-snap (3 rounds + clustering), split (beams+walls at crossings)
python -m golden_scripts.tools.beam_validate \
    --elements "SLIDES INFO/1F~2F/calibrated/calibrated.json" \
    --grid-data grid_data.json \
    --output "SLIDES INFO/1F~2F/calibrated/calibrated.json" \
    --tolerance 1.5 \
    --report "SLIDES INFO/1F~2F/beam_report_1F~2F.json"

# Custom angle threshold + split tolerance + cluster tolerance
python -m golden_scripts.tools.beam_validate \
    --elements elements.json \
    --grid-data grid_data.json \
    --output elements.json \
    --angle-threshold 2.0 \
    --split-tolerance 0.15 \
    --cluster-tolerance 0.50

# Disable angle correction, splitting, or clustering
python -m golden_scripts.tools.beam_validate \
    --elements elements.json \
    --grid-data grid_data.json \
    --output elements.json \
    --no-angle-correct --no-split --no-cluster

# Preview without writing
python -m golden_scripts.tools.beam_validate ... --dry-run
```

### Config Build Tool (Phase 1 — deterministic merge)
```bash
# Merge elements.json + grid_info.json → model_config.json
python -m golden_scripts.tools.config_build \
    --elements elements.json \
    --grid-info grid_info.json \
    --output model_config.json \
    --save-path "C:/path/to/model.EDB" \
    --project-name "ProjectName"

# Preview without writing
python -m golden_scripts.tools.config_build ... --dry-run
```

### SB Patch Build Tool (Phase 2 — deterministic extraction)
```bash
# Extract small beams from sb_elements_validated.json → sb_patch.json
python -m golden_scripts.tools.sb_patch_build \
    --sb-elements sb_elements_validated.json \
    --config model_config.json \
    --output sb_patch.json

# Preview without writing
python -m golden_scripts.tools.sb_patch_build ... --dry-run
```

### Read Grid from ETABS (Phase 1 prerequisite)
```bash
# Read pre-built Grid System from running ETABS instance
python -m golden_scripts.tools.read_grid --output grid_data.json
```

### Diagnose Elevation Mismatch (debugging)
```bash
# Compare config elev_map vs ETABS actual elevations
python -m golden_scripts.tools.diagnose_elev --config model_config.json
```

### Slash commands (BTS Agent Teams — Phased, preferred)
- `/bts-structure [description]` — Phase 1: 2 Readers + 1 Config-Builder → Grid+Story+柱+牆+大梁
- `/bts-qc1 <config>` — Phase 1 QC: 比對 ETABS 模型 vs model_config.json（8 項檢查）
- `/bts-sb [floor ranges]` — Phase 2: 2 SB-Readers + 1 Config-Builder → 小梁+版（含 affine 校正 + 自動算板）
- `/bts-props` — Phase 3: Properties + Loads + Diaphragms (no agent team, runs gs_09~gs_11)

### Slash commands (BTS Agent Teams — Single-pass)
- `/bts-gs [description]` — 3-agent team + Golden Scripts (READER + SB-READER + CONFIG-BUILDER)
- `/bts [description]` — Legacy 4-agent team (READER + SB-READER + MODELER-A + MODELER-B)

### Config Merge Tool (Phase 2)
```bash
# Merge Phase 1 base config with Phase 2 SB patch
python -m golden_scripts.tools.config_merge --base model_config.json --patch sb_patch.json --output merged_config.json
```

### Config Snap Tool (Phase 2)
```bash
# Snap SB coordinates to nearest structural elements
python -m golden_scripts.tools.config_snap --input merged_config.json --output snapped_config.json

# Preview changes without writing
python -m golden_scripts.tools.config_snap --input merged_config.json --output snapped_config.json --dry-run
```

### E2K Split/Merge Tools
```bash
# Split: extract single building from multi-building e2k
python -m golden_scripts.tools.gs_split --input all.e2k --building DA --output A.e2k
python -m golden_scripts.tools.gs_split --input all.e2k --list-buildings

# Merge: combine building e2k files into one model
python -m golden_scripts.tools.gs_merge --base sub.e2k --buildings A=A.e2k B=B.e2k --output merged.e2k
```

### Slash commands (E2K Tools)
- `/split [input] [building_id] [output]` — Split multi-building e2k
- `/merge [base] [PREFIX=path ...] [output]` — Merge building e2k files

---

## Structural Terminology (see `skills/structural-glossary/SKILL.md`)

| 術語 | English | 判斷邏輯 | Python function |
|------|---------|---------|-----------------|
| 下構 | substructure | `B*F`, `1F`, `BASE` | `constants.is_substructure_story()` |
| 上構 | superstructure | `1MF`, `2F`~`RF` | `constants.is_superstructure_story()` |
| 屋突 | rooftop | `R*F`, `PRF` | `constants.is_rooftop_story()` |
| 共構 | shared sub | 多棟共用下構 | — |
| 分棟 | building split | 靠 Diaphragm Name 辨識 | `gs_split.discover_buildings()` |

---

## Golden Scripts Architecture

The golden scripts are split into three sub-packages under `golden_scripts/`:
- **`modeling/`** (gs_01–gs_11): Deterministic model construction — reads `model_config.json` and executes ETABS API calls with no AI reasoning.
- **`design/`** (gs_12+): Analysis-design iteration and optimization.
- **`tools/`**: E2K split/merge utilities, config tools — e2k parser, writer, unit converter, split, merge, config_build, sb_patch_build, config_merge, config_snap, sb_validate, affine_calibrate, slab_generator.

All structural engineering rules are hardcoded in `golden_scripts/constants.py`.

### Modeling Steps (01–11)
| Step | Script | What it does |
|------|--------|-------------|
| 01 | modeling/gs_01_init.py | New model + materials (C280–C490, SD420/SD490) |
| 02 | modeling/gs_02_sections.py | Batch section expansion + D/B swap + rebar + area modifiers |
| 03 | modeling/gs_03_grid_stories.py | Grid system (skip if pre-built) + story definitions |
| 04 | modeling/gs_04_columns.py | Columns with +1 floor rule built-in |
| 05 | modeling/gs_05_walls.py | Walls with +1 floor rule, diaphragm walls → C280 |
| 06 | modeling/gs_06_beams.py | Beams (B, WB, FB) |
| 07 | modeling/gs_07_small_beams.py | Small beams (SB) from explicit coordinates |
| 08 | modeling/gs_08_slabs.py | Slabs (S=Membrane, FS=ShellThick) |
| 09 | modeling/gs_09_properties.py | Modifiers + rigid zone (0.75) + end releases |
| 10 | modeling/gs_10_loads.py | DL/LL/EQ + response spectrum + foundation springs |
| 11 | modeling/gs_11_diaphragms.py | Diaphragm assignment at slab corner points |

### Design Steps (12)
| Step | Script | What it does |
|------|--------|-------------|
| 12 | design/gs_12_iterate.py | Analysis-design iteration (ACI 318-19 rebar ratio optimization) |

### Key Constants (from `constants.py`)
```
Frame modifiers (beam):   [1, 1, 1, 0.0001, 0.7, 0.7, 0.8, 0.8]
Frame modifiers (column): [1, 1, 1, 0.0001, 0.7, 0.7, 0.95, 0.95]
Area modifiers (slab/wall): [0.4, 0.4, 0.4, 1, 1, 1, 1, 1, 1, 1]
Area modifiers (raft):      [0.4, 0.4, 0.4, 0.7, 0.7, 0.7, 1, 1, 1, 1]
Rigid zone factor: 0.75
Beam cover: 9cm (regular), 11cm top / 15cm bot (foundation)
Column cover: 7cm
Section naming: {PREFIX}{WIDTH}X{DEPTH}[C{fc}]  (e.g. B55X80C350)
API D/B swap: T3=Depth, T2=Width (SetRectangle)
+1 floor rule: column/wall on plan NF spans from NF elevation to (N+1)F elevation
Shell types: Membrane (2) for slabs/walls, ShellThick (1) for raft/FS
Stories order: config may be either top-to-bottom or bottom-to-top;
  normalize_stories_order() auto-detects and returns bottom-to-top.
  Phase 2 cross-verifies elev_map against ETABS when step 3 is skipped.
```

### Foundation Floor Rules (MANDATORY)

Foundation floor = BASE 上一層 (e.g. B3F). BASE has NO objects.

| Rule | Detail |
|------|--------|
| Columns INCLUDE foundation floor | Column `floors` start from foundation floor (e.g. B3F). Column at B3F spans B3F→B2F via +1 rule. |
| Beams OK at foundation floor | FB/FWB/FSB beams are placed at foundation floor |
| FS slab at foundation floor | ShellThick, RAFT_MODIFIERS, DL=0.63, LL=0 |
| Restraints at foundation floor | UX/UY only (no UZ, no rotations) |
| Kv springs at foundation floor | Vertical springs on all foundation floor joints |
| Kw springs on edge FB beams | Lateral line springs on perimeter foundation beams |
| Diaphragm on FS corners | FS slab corner points get diaphragm assignment |
| FS 2x2 subdivision | Each FS slab auto-split into 4 for uniform Kv distribution |
| No SDL | SDL load pattern is NEVER created. All additional dead loads use DL pattern. |
| BS slab not modeled | 20cm BS slab above FS is not modeled; its weight included in FS DL=0.63 |

### Section Naming Convention
- `B` = beam, `SB` = small beam, `WB` = wall beam, `FB` = foundation beam
- `C` = column, `W` = wall, `S` = slab, `FS` = foundation slab
- Format: `{PREFIX}{WIDTH}X{DEPTH}C{fc}` → e.g. `B55X80C350` = 55cm wide, 80cm deep, fc'=350

---

## Phased BTS Workflow (`/bts-structure` + `/bts-sb` + `/bts-props`)

Splits the single-pass `/bts-gs` into 3 phased commands to reduce token consumption and improve AI quality.

### Phase 1: `/bts-structure`
- **Prerequisite**: User has pre-built Grid System in ETABS
- **Team**: 2 Readers (split by floor range) + 1 Config-Builder
- **Builds**: Grid (skip if pre-built), Story, Columns, Walls, Major Beams (B/WB/FB/FWB)
- **Pre-steps**:
  1. `read_grid.py` → `grid_data.json` (read Grid from ETABS as ground truth)
  2. `pptx_to_elements.py --scan-floors` → `PAGE_FLOOR_MAPPING` (floor label detection)
- **Data flow**:
  READER-A: `pptx_to_elements.py --slides-info-dir "SLIDES INFO" --page-floors "{上構}"` → `SLIDES INFO/{fl}/pptx_to_elements/{fl}.json` + `.png` (parallel)
  READER-B: `pptx_to_elements.py --slides-info-dir "SLIDES INFO" --page-floors "{下構}"` → `SLIDES INFO/{fl}/pptx_to_elements/{fl}.json` + `.png` (parallel)
  READERs: Grid anchor identification → `affine_calibrate.py --mode grid` → `beam_validate.py` → `plot_elements.py` → `SLIDES INFO/{fl}/calibrated/calibrated.json` + `.png` (parallel)
  Readers → `grid_info.json` (Grid驗證 + outline + core_area)
  Team Lead: `elements_merge.py --inputs-dir "SLIDES INFO" --pattern "*/calibrated/calibrated.json"` → `elements.json` → `config_build.py` → `model_config.json`
  CONFIG-BUILDER: `run_all.py --steps 1,2,3,4,5,6` → ETABS model
- **Output**: `model_config.json` (small_beams=[], slabs=[]) + ETABS model with Grid+Story+柱+牆+大梁

### Phase 2: `/bts-sb`
- **Team**: 2 SB-Readers (calibration + validation) + 1 Config-Builder
- **Builds**: Small Beams (SB/FSB) + Slabs (S/FS)
- **Pre-steps** (Team Lead):
  1. Verify Phase 1 outputs: `model_config.json`, `grid_data.json`, `SLIDES INFO/` (grid_anchors + screenshots)
  2. `pptx_to_elements.py --phase phase2 --slides-info-dir "SB SLIDES INFO"` → per-slide SB JSONs + `.png`
- **Data flow**:
  SB-READER-A ∥ SB-READER-B: per-slide `affine_calibrate.py --mode grid` (reusing Phase 1 grid_anchors) → `SB SLIDES INFO/{fl}/calibrated/calibrated.json`
  SB-READERs: per-slide `sb_validate.py` → overwrite `SB SLIDES INFO/{fl}/calibrated/calibrated.json` + `plot_elements.py` → `.png` + AI validation → `sb_validation_{fl}.json`
  Team Lead: `elements_merge.py --inputs-dir "SB SLIDES INFO" --pattern "*/calibrated/calibrated.json" --phase phase2` → `sb_elements_validated.json`
  Team Lead: `sb_patch_build.py` → `config_merge` → `slab_generator.py` → `final_config.json`
  CONFIG-BUILDER: `run_all.py --steps 2,7,8` → ETABS model
- **Output**: `final_config.json` (complete config with validated SB + auto-generated slabs) + ETABS model with +小梁+版

### Phase 3: `/bts-props`
- **Team**: None (Team Lead direct execution)
- **Builds**: Frame modifiers, rigid zones, end releases, load patterns, slab loads, seismic, spectrum, Kv/Kw springs, diaphragms
- **Execution**: `run_all.py --config final_config.json --steps 9,10,11`
- **Kw auto-detection**: All FWB (基礎壁梁) beams automatically receive Kw line springs
- **Load defaults**: Uses `constants.py DEFAULT_LOADS` unless overridden in config `loads.zone_defaults`

### Intermediate File Structure
```
{Case Folder}/
├── 結構配置圖/
│   ├── SLIDES INFO/                        # ═══ Phase 1 專用 ═══
│   │   └── {floor_label}/
│   │       ├── pptx_to_elements/           # 原始提取
│   │       │   ├── {floor_label}.json      # Phase 1: 大梁/柱/牆 (PPT-meter)
│   │       │   └── {floor_label}.png       # 提取結果繪圖 (auto-generated)
│   │       ├── calibrated/                 # 校正後
│   │       │   ├── calibrated.json         # 校正+驗證後的構件
│   │       │   └── calibrated.png          # 校正結果繪圖
│   │       ├── grid_anchors_{fl}.json      # Phase 1: grid anchors (Phase 2 讀取複用)
│   │       ├── beam_report_{fl}.json       # Phase 1: beam validation report
│   │       └── screenshots/                # Phase 1: 截圖 (Phase 2 讀取複用)
│   │
│   ├── SB SLIDES INFO/                     # ═══ Phase 2 專用 ═══
│   │   └── {floor_label}/
│   │       ├── pptx_to_elements/           # 原始提取
│   │       │   ├── sb_{floor_label}.json   # Phase 2: 小梁 (PPT-meter)
│   │       │   └── sb_{floor_label}.png    # 提取結果繪圖 (auto-generated)
│   │       ├── calibrated/                 # 校正後
│   │       │   ├── calibrated.json         # 校正+驗證後的小梁
│   │       │   └── calibrated.png          # 校正結果繪圖
│   │       ├── sb_report_{fl}.json         # Phase 2: sb_validate report
│   │       └── sb_validation_{fl}.json     # Phase 2: AI validation result (OK/WARN/REJECT)
│   │
│   └── grid_info.json                      # Phase 1 READER output (outline/stories — AI)
│
├── elements.json                           # Phase 1 merged
├── grid_data.json                          # Phase 0.3 ETABS Grid (ground truth)
├── model_config.json                       # Phase 1 output (no SB/slabs)
├── sb_elements_validated.json              # Phase 2 merged SBs (elements_merge --phase phase2)
├── sb_patch.json                           # Phase 2 SB patch
├── merged_config.json                      # Phase 2 merged (base + SB patch)
└── final_config.json                       # Phase 2 final (含自動生成的板)
```

---

## BTS Agent Team Rules (ABSOLUTE)

1. **Small beam positions must never be guessed.** `pptx_to_elements.py` extracts coordinates deterministically from PPTX. SB-READER validates (not extracts).
2. **Structural layout comes from plan images, never copied from old models.**
3. **Building extents must be cross-referenced between structural and architectural plans.**
4. **Mechanically equal-spaced small beam coordinates must be rejected and re-measured.**
   > **例外**：`/bts-sb-eq` 是刻意使用等分座標的獨立系統，不受本規則約束。
   > 等分座標由 `eq_sb_generator.py` 從 `model_config.json` 的大梁位置數學計算得出，
   > 是工程師明確宣告等分設計意圖，不是 AI 猜測。
5. **No SDL load pattern.** NEVER create SDL. All additional dead loads go under DL.
6. **Each project is independent** — never infer from memory of other projects.
7. **Grid line names, direction, and order must be read from the ETABS pre-built model (`grid_data.json`).** PPT is used for validation only. Do not assume X=numbers, Y=letters, or that grids increase left-to-right / bottom-to-top.
8. **Diaphragm walls (連續壁) are walls, not beams.** They use existing grid coordinates — never add extra grid lines for them.
9. **Slabs must be cut along every beam including small beams.** Every SB fixed-axis coordinate is a slab cutting line.
10. **L-shaped / non-rectangular buildings must define a building_outline polygon.** No columns, beams, or slabs outside the outline.

---

## API Lookup Rule (MANDATORY)

When encountering ANY ETABS API method you are not 100% certain about:

1. Search `api_docs/CSI API ETABS v1.hhc` for the method name
2. Read the actual `.htm` file for exact parameter names, types, and order
3. **Never guess parameter order, types, or return values**

Quick references:
- "How do I...?" → `api_docs_index/task_index.md`
- Method signatures → `api_docs_index/group_a_analysis.md` or `group_b_analysis.md`
- Interface grouping → `api_docs_index/categories.json`

---

## ETABS API Quick Reference

### Connection
```python
from find_etabs import find_etabs
etabs, filename = find_etabs(run=False, backup=False)
SapModel = etabs.SapModel

# etabs_api high-level wrappers
df = etabs.database.read("表名", to_dataframe=True)
etabs.database.write(table_key="表名", data=df)
```

### Units
```python
SapModel.SetPresentUnits(12)  # 12=Ton_m, 14=kgf_cm
```

### Key Interfaces
| Path | Purpose |
|------|---------|
| `SapModel.File` | Open, Save, New |
| `SapModel.Story` | Story definitions (SetStories_2, GetStories_2) |
| `SapModel.GridSys` | Grid systems |
| `SapModel.PropMaterial` | Materials (AddMaterial, SetMPIsotropic, SetOConcrete_1) |
| `SapModel.PropFrame` | Frame sections (SetRectangle, SetRebarColumn) |
| `SapModel.PropArea` | Area sections (SetSlab, SetWall) |
| `SapModel.FrameObj` | Frame objects (AddByCoord, SetModifiers, SetReleases) |
| `SapModel.AreaObj` | Area objects (AddByCoord, SetLoadUniform, SetDiaphragm) |
| `SapModel.PointObj` | Joints (SetRestraint, SetSpring, SetDiaphragm) |
| `SapModel.LoadPatterns` | Load patterns (Add) |
| `SapModel.RespCombo` | Load combinations |
| `SapModel.Analyze` | RunAnalysis, SetActiveDOF |
| `SapModel.Results` | FrameForce, StoryDrifts, JointDispl |
| `SapModel.DatabaseTables` | Bulk read/write via GetTableForDisplayArray |
| `SapModel.Diaphragm` | Diaphragm management |
| `SapModel.DesignConcrete` | Concrete design (StartDesign, GetSummaryResults*) |

### Critical Method Signatures
```python
# Frame section: T3=depth, T2=width (WATCH THE ORDER)
SapModel.PropFrame.SetRectangle(Name, Material, T3_depth, T2_width)

# Frame object by coordinates
SapModel.FrameObj.AddByCoord(x1, y1, z1, x2, y2, z2, Name='', PropName='')

# Area object by coordinates
SapModel.AreaObj.AddByCoord(NumPoints, X_list, Y_list, Z_list, Name='', PropName='')

# Modifiers: frame=[Area,As2,As3,Torsion,I22,I33,Mass,Weight]
SapModel.FrameObj.SetModifiers(Name, Modifiers_8)

# Area modifiers: [f11,f22,f12,m11,m22,m12,v13,v23,Mass,Weight]
SapModel.AreaObj.SetModifiers(Name, Modifiers_10)

# End releases: [P, V2, V3, T, M2, M3]
SapModel.FrameObj.SetReleases(Name, II, JJ, StartVal, EndVal)

# Stories (only when no objects exist)
SapModel.Story.SetStories_2(BaseElev, NumStories, Names, Heights,
    IsMaster, SimilarTo, SpliceAbove, SpliceHeight, Color)

# Load pattern: type codes — Dead=1, Live=3, Quake=5, Wind=6
SapModel.LoadPatterns.Add(Name, Type, SelfWeightMult)

# Database table bulk read
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    TableKey, [], "All", 0, [], 0, [])
# ret = (retcode, ..., FieldsKeysIncluded, NumberRecords, TableData)
```

### Common Table Keys
`"Story Definitions"`, `"Frame Section Properties"`, `"Area Section Properties"`,
`"Material Properties"`, `"Load Pattern Definitions"`, `"Frame Assignments - Summary"`,
`"Area Assignments - Summary"`, `"Story Drifts"`, `"Modal Periods And Frequencies"`,
`"Concrete Column Summary"`, `"Concrete Beam Summary"`

### Python COM Notes
- `ref` parameters: pass initial values (`''`, `0`, `[]`), COM fills them
- Return `0` = success for most methods
- Use `View.RefreshView(0, False)` after modifications
- Save before `Analyze.RunAnalysis()`

### Key Enumerations
```
eUnits: 6=kN_m, 8=kgf_m, 12=Ton_m, 14=kgf_cm
eLoadPatternType: Dead=1, SuperDead=2, Live=3, Quake=5, Wind=6
eMatType: Steel=1, Concrete=2, Rebar=5
eItemType: Objects=0, Group=1, SelectedObjects=2
Load direction: 6=Global-Z, 10=Gravity(proj), 11=Projected Gravity
Shell type: ShellThick=1, Membrane=2
```
