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
├── CLAUDE.md                              # This file
├── golden_scripts/                        # Deterministic model-building pipeline
│   ├── run_all.py                         # Master orchestrator (--config, --steps, --dry-run)
│   ├── constants.py                       # All hardcoded rules (modifiers, rebar, parsing, story classification)
│   ├── config_schema.json                 # JSON Schema for model_config.json
│   ├── example_config.json                # A21 reference config
│   ├── __init__.py
│   ├── modeling/                           # 11 sequential build steps
│   │   ├── __init__.py
│   │   ├── gs_01_init.py → gs_11_diaphragms.py
│   ├── design/                            # Analysis-design iteration
│   │   ├── __init__.py
│   │   └── gs_12_iterate.py
│   └── tools/                             # E2K split/merge utilities + config tools
│       ├── __init__.py
│       ├── e2k_parser.py                  # General e2k parser (E2KModel class)
│       ├── e2k_writer.py                  # E2k output (section ordering, formatting)
│       ├── unit_converter.py              # Unit detection & conversion
│       ├── pdf_annot_extractor.py          # Extract Bluebeam annotations → annotations.json + crop PNGs
│       ├── annot_to_elements.py           # Deterministic annotation → elements JSON (columns/beams/walls/SB)
│       ├── config_merge.py                # Merge base config + SB/slab patch → merged config
│       ├── config_snap.py                 # Snap SB endpoints to nearest beams/columns/walls
│       ├── gs_split.py                    # Split multi-building → single-building e2k
│       └── gs_merge.py                    # Merge single-building e2k files → unified model
├── golden_scripts/qc/                     # QC verification scripts
│   └── qc_phase1.py                      # Phase 1 QC: config vs ETABS model comparison
├── tests/                                 # pytest verification suite (requires running ETABS)
│   ├── conftest.py                        # SapModel fixture, --config option, all_frames cache
│   ├── test_units.py                      # Units = TON/M (12)
│   ├── test_sections.py                   # D/B mapping (T3=Depth, T2=Width)
│   ├── test_modifiers.py                  # Frame + area stiffness modifiers
│   ├── test_rebar.py                      # Cover values (col=7cm, beam=9cm, FB=11/15cm)
│   ├── test_rigid_zones.py                # RZ factor = 0.75
│   ├── test_diaphragms.py                 # Diaphragm definitions exist
│   ├── test_loads.py                      # DL/LL/EQ patterns, no SDL, DL self-weight=1
│   └── test_element_counts.py             # Frames, areas, columns, beams, stories exist
├── skills/
│   ├── structural-glossary/SKILL.md       # Canonical structural terminology (上構/下構/屋突/共構)
│   ├── e2k-split/SKILL.md                 # E2K split tool SOP
│   ├── e2k-merge/SKILL.md                 # E2K merge tool SOP
│   ├── plan-reader/SKILL.md               # Structural plan image reading SOP
│   ├── etabs-modeler/SKILL.md             # Manual ETABS modeling skill (legacy)
│   ├── etabs-modeler/references/          # modifier-rebar-rules.md, section-parsing-rules.md,
│   │                                      #   verification-queries.md
│   ├── etabs-modeler/scripts/             # Legacy helper scripts (generate_sections, assign_loads, etc.)
│   └── etabs-api-lookup.md                # How to look up API docs
├── .claude/
│   ├── agents/                            # BTS agent definitions
│   │   ├── phase1-reader.md               # Phase 1 READER: grid+columns+beams+walls → folders
│   │   ├── phase1-config-builder.md       # Phase 1 CONFIG-BUILDER: folders → model_config.json (no SB/slabs)
│   │   ├── phase2-sb-reader.md            # Phase 2 SB-READER: small beam coords → SB-BEAM/ folder
│   │   ├── phase2-config-builder.md       # Phase 2 CONFIG-BUILDER: SB-BEAM/ → sb_slabs_patch.json
│   │   ├── reader.md                      # READER: reads structural plan images (bts-gs)
│   │   ├── sb-reader.md                   # SB-READER: small beam coordinate validation (bts-gs)
│   │   ├── config-builder.md              # CONFIG-BUILDER: generates model_config.json (bts-gs)
│   │   ├── modeler-a.md                   # MODELER-A: materials/sections/columns/walls (legacy bts)
│   │   ├── modeler-b.md                   # MODELER-B: beams/slabs/loads/properties (legacy bts)
│   │   ├── e2k-splitter.md               # E2K-SPLITTER: split multi-building e2k
│   │   └── e2k-merger.md                 # E2K-MERGER: merge building e2k files
│   └── commands/
│       ├── bts-structure.md               # /bts-structure slash command (Phase 1: main structure)
│       ├── bts-sb.md                      # /bts-sb slash command (Phase 2: small beams + slabs)
│       ├── bts-props.md                   # /bts-props slash command (Phase 3: properties + loads + diaphragms)
│       ├── bts-qc1.md                     # /bts-qc1 slash command (Phase 1 QC verification)
│       ├── bts-gs.md                      # /bts-gs slash command (single-pass Golden Scripts)
│       ├── bts.md                         # /bts slash command (legacy 4-agent flow)
│       ├── split.md                       # /split slash command (e2k split)
│       └── merge.md                       # /merge slash command (e2k merge)
├── api_docs/                              # Raw ETABS API HTML docs (1693 files)
│   ├── CSI API ETABS v1.hhc              # Searchable TOC
│   └── html/                              # Individual method documentation
├── api_docs_index/                        # Pre-built API index
│   ├── task_index.md                      # "How do I...?" guide
│   ├── group_a_analysis.md                # Analysis, Results, Load Cases, Design Codes
│   ├── group_b_analysis.md                # Modeling, Properties, Database Tables
│   ├── categories.json                    # Interface-to-category mapping
│   └── full_toc.json                      # Complete TOC
└── models/                                # Output model files (.EDB)
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

### Run verification tests
```bash
# Requires ETABS running with the model open
cd tests
pytest -v
pytest -v --config path/to/model_config.json    # with config comparison
pytest -v -k test_sections                        # run single test
```

### QC Phase 1 (after /bts-structure)
```bash
python -m golden_scripts.qc.qc_phase1 --config path/to/model_config.json
```

### Deterministic Annotation → Elements (used by /bts-structure and /bts-sb)
```bash
# Phase 1: major beams + columns + walls
python -m golden_scripts.tools.annot_to_elements \
    --input 結構配置圖/annotations.json \
    --output elements.json \
    --page-floors "1=B3F, 3=1F~2F, 4=3F~14F, 5=R1F~R3F" \
    --phase phase1

# Phase 2: small beams only
python -m golden_scripts.tools.annot_to_elements \
    --input 結構配置圖/annotations.json \
    --output sb_elements.json \
    --page-floors "3=1F~2F, 4=3F~14F" \
    --phase phase2

# Preview without writing
python -m golden_scripts.tools.annot_to_elements ... --dry-run
```

### Slash commands (BTS Agent Teams — Phased, preferred)
- `/bts-structure [description]` — Phase 1: 2 Readers + 1 Config-Builder → Grid+Story+柱+牆+大梁
- `/bts-qc1 <config>` — Phase 1 QC: 比對 ETABS 模型 vs model_config.json（8 項檢查）
- `/bts-sb [floor ranges]` — Phase 2: 2 SB-Readers + 1 Config-Builder → 小梁+版
- `/bts-props` — Phase 3: Properties + Loads + Diaphragms (no agent team, runs gs_09~gs_11)

### Slash commands (BTS Agent Teams — Single-pass)
- `/bts-gs [description]` — 3-agent team + Golden Scripts (READER + SB-READER + CONFIG-BUILDER)
- `/bts [description]` — Legacy 4-agent team (READER + SB-READER + MODELER-A + MODELER-B)

### Config Merge Tool (Phase 2)
```bash
# Merge Phase 1 base config with Phase 2 SB/slab patch
python -m golden_scripts.tools.config_merge --base model_config.json --patch sb_slabs_patch.json --output merged_config.json
```

### Config Snap Tool (Phase 2)
```bash
# Snap SB coordinates to nearest structural elements
python -m golden_scripts.tools.config_snap --input merged_config.json --output snapped_config.json

# Preview changes without writing
python -m golden_scripts.tools.config_snap --input merged_config.json --output snapped_config.json --dry-run
```

### PDF Annotation Extraction + Page Cropping
```bash
# Extract Bluebeam annotations to JSON
python -m golden_scripts.tools.pdf_annot_extractor --input "plan.pdf" --pages 5 --output annotations.json

# Extract + crop page images (full + zoomed regions for agent reading)
python -m golden_scripts.tools.pdf_annot_extractor --input "plan.pdf" --pages 5 --output annotations.json --crop --crop-dir "./結構配置圖/"
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
- **`tools/`**: E2K split/merge utilities, config merge — e2k parser, writer, unit converter, split, merge, config_merge.

All structural engineering rules are hardcoded in `golden_scripts/constants.py`.

### Modeling Steps (01–11)
| Step | Script | What it does |
|------|--------|-------------|
| 01 | modeling/gs_01_init.py | New model + materials (C280–C490, SD420/SD490) |
| 02 | modeling/gs_02_sections.py | Batch section expansion + D/B swap + rebar + area modifiers |
| 03 | modeling/gs_03_grid_stories.py | Grid system + story definitions |
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
- **Team**: 2 Readers (split by floor range) + 1 Config-Builder
- **Builds**: Grid, Story, Columns, Walls, Major Beams (B/WB/FB/FWB)
- **Pre-step**: `annot_to_elements.py --phase phase1` → `elements.json` (deterministic element extraction)
- **Data flow**: `elements.json` (columns/beams/walls) + Readers → `grid_info.json` (grid/outline/stories) → Config-Builder merges → `model_config.json`
- **Execution**: `run_all.py --steps 1,2,3,4,5,6`
- **Output**: `model_config.json` (small_beams=[], slabs=[])

### Phase 2: `/bts-sb`
- **Team**: 2 SB-Readers (validation only) + 1 Config-Builder
- **Builds**: Small Beams (SB/FSB) + Slabs (S/FS)
- **Pre-step**: `annot_to_elements.py --phase phase2` → `sb_elements.json` (deterministic SB extraction)
- **Data flow**: SB-Readers validate `sb_elements.json` → Config-Builder reads `sb_elements.json` + `model_config.json` → `sb_slabs_patch.json`
- **Merge**: `config_merge.py --base model_config.json --patch sb_slabs_patch.json --output merged_config.json`
- **Snap**: `config_snap.py --input merged_config.json --output snapped_config.json` (corrects SB endpoints)
- **Execution**: `run_all.py --config snapped_config.json --steps 2,7,8`
- **Output**: `snapped_config.json` (complete config with corrected SB coordinates)

### Phase 3: `/bts-props`
- **Team**: None (Team Lead direct execution)
- **Builds**: Frame modifiers, rigid zones, end releases, load patterns, slab loads, seismic, spectrum, Kv/Kw springs, diaphragms
- **Execution**: `run_all.py --config snapped_config.json --steps 9,10,11`
- **Kw auto-detection**: All FWB (基礎壁梁) beams automatically receive Kw line springs
- **Load defaults**: Uses `constants.py DEFAULT_LOADS` unless overridden in config `loads.zone_defaults`

### Intermediate File Structure
```
{Case Folder}/
├── 結構配置圖/
│   ├── annotations.json
│   ├── BEAM/          # Phase 1: READER grid/outline data
│   ├── COLUMN/        # Phase 1: READER grid/outline data
│   ├── WALL/          # Phase 1: READER grid/outline data
│   └── SB-BEAM/       # Phase 2: SB-READER validation results
├── elements.json           # Phase 1 script output (columns/beams/walls — deterministic)
├── grid_info.json          # Phase 1 READER output (grids/outline/stories — AI)
├── sb_elements.json        # Phase 2 script output (small beams — deterministic)
├── model_config.json       # Phase 1 output (no SB/slabs)
├── sb_slabs_patch.json     # Phase 2 output (SB + slabs only)
├── merged_config.json      # Merged (base + patch)
└── snapped_config.json     # Final config with corrected SB coordinates
```

---

## BTS Agent Team Rules (ABSOLUTE)

1. **Small beam positions must never be guessed.** `annot_to_elements.py` extracts coordinates deterministically from annotation.json. SB-READER validates (not extracts).
2. **Structural layout comes from plan images, never copied from old models.**
3. **Building extents must be cross-referenced between structural and architectural plans.**
4. **Mechanically equal-spaced small beam coordinates must be rejected and re-measured.**
5. **No SDL load pattern.** NEVER create SDL. All additional dead loads go under DL.
6. **Each project is independent** — never infer from memory of other projects.
7. **Grid line names, direction, and order must be read from the structural plan.** Do not assume X=numbers, Y=letters, or that grids increase left-to-right / bottom-to-top.
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
