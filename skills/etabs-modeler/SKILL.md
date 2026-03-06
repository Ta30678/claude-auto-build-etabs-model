---
name: etabs-modeler
description: >
  ETABS structural modeler agent. Builds complete analysis-ready ETABS models from
  structural-config-reader (plan-reader) output. Trigger when user mentions:
  "build model", "create ETABS", "modeling", "add floors", "configure model",
  "建模", "建 ETABS", "加樓層", "配置建模".
  Covers: Grid, materials, batch section generation, stories, column/beam/wall/slab
  elements, stiffness modifiers, rebar, end releases, rigid zones, springs,
  loads, response spectrum, diaphragms, verification.
---

# ETABS Modeler Skill

## 1. Overview

This skill receives structured output from `structural-config-reader` (plan-reader) and builds a **complete, analysis-ready** ETABS model. It handles everything from grid definition to load assignment and verification.

**Two modes:**
- **New model**: Initialize blank model, define everything from scratch
- **Add to existing**: Attach to open model, **re-check and re-define EVERYTHING** (do NOT skip steps just because something already exists)

**Upstream**: `skills/plan-reader/SKILL.md` (Section 10 output format)
**Downstream**: Analysis run, design check

---

## 2. Prerequisites

Before starting, ensure:
1. **ETABS 22** is running (or will be launched)
2. **Execution method**: MCP tools (`mcp__etabs__run_python`) preferred; fallback to `Bash` + `scripts/connect_etabs.py`
3. **User must provide** (ask if missing):
   - Story heights (each floor or standard + exceptions)
   - Strength allocation table (`強度分配.xlsx` or verbal description)
   - DL / LL loads (有預設值，可覆蓋)
   - Foundation Kv (ton/m) and edge beam Kw (ton/m/m) values
   - Slab thickness (if plan-reader didn't output it; default 15cm)

**IMPORTANT**: If the user hasn't provided the strength allocation table, you MUST ask for it. Do NOT assume concrete grades.

### 2.1 Model Folder Required Files

The model folder (case folder) should contain:

| File | Description | Required |
|------|-------------|----------|
| `SPECTRUM.TXT` | Response spectrum function (Period vs Value) | Yes |
| `EQ_PARAMS.txt` | Earthquake parameters (C, scale factors) | Yes (or ask user) |
| `結構配置圖/` | Structural plan images (used by plan-reader) | Yes |

**`EQ_PARAMS.txt` format:**
```
# Earthquake Parameters
BASE_SHEAR_C=0.072
EQV_SCALE_FACTOR=4.5
```

If `EQ_PARAMS.txt` does not exist, **ask the user** for:
- Base Shear Coefficient C value
- EQV scale factor for load combinations

### 2.2 上構與下構定義

| 區分 | ETABS 樓層範圍 | 說明 |
|------|---------------|------|
| 上構 (Superstructure) | 2F 以上（不含 1F） | 地表以上的結構物 |
| 下構 (Substructure) | 1F 以下（含 1F） | 地表以下的結構物，包含 1F |

### 2.2a 樓層配置命名慣例與屋突層規則

**樓層配置表示法：**
- "24F/B6" = 上構到 24F（頂樓）+ 屋突層 R1F~PRF，下構到 B6F 含基礎層
- 每案不同，禁止從記憶推斷，必須從該 case folder 確認

**屋突層建模規則（R1F ~ PRF）：**

| 屋突層 | 梁/板配置 | 柱配置（ETABS 樓層） | 說明 |
|--------|----------|-------------------|------|
| R1F | 同頂樓 | ETABS R1F 柱 = 結構配置圖「頂樓柱」 | 柱往下長，所以 R1F story 的柱 = 頂樓圖面上的柱 |
| R2F | R1F 核心區延伸 | ETABS R2F 柱 = 結構配置圖「R1F 柱」 | 通常無圖，用 R1F 的 2x2 Grid 區間延伸 |
| R3F~PRF | 同 R2F 區間 | 同 R2F 配置 | 持續延伸到 PRF |

**R2F 以上無圖時的做法：**
1. 確認 R1F 哪些 Grid 區間有構件（通常是電梯/樓梯核心區，約 2x2 Grid 範圍）
2. 將該區間的柱/梁/板配置直接往上延伸到 PRF
3. 延伸區間以外的區域不建構件

### 2.3 各區域預設載重（ton/m2）

| 區域 | DL | LL | 說明 |
|------|-----|-----|------|
| 上構樓板 (2F~RF) | 0.45 | 0.2 | 標準樓層 |
| 下構樓板 (B_F~1F) | 0.15 | 0.5 | 地下室 |
| 1F 室內 | 0.3 | 0.5 | 上構延伸至 1F 以內的範圍 |
| 1F 室外 | 0.6 | 1.0 | 上構延伸至 1F 以外的範圍 |
| FS 基礎版 | 0.63 | — | 2.4*0.2(板厚)+0.15 |

以上為預設值。建模時可詢問使用者確切參數，或直接使用預設。

---

## 3. CRITICAL: Existing Model Handling

When building on an **existing ETABS model** (e.g., user opened an old model and wants to rebuild):

**NEVER assume existing model data is correct.** Always:

1. **Delete or redefine stories** -- the existing model may have different floors/heights
2. **Redefine materials** -- even if C280, C350 etc. exist, verify properties match
3. **Recreate all sections** -- don't skip section creation because names match
4. **Rebuild grid system** -- existing grids may not match the new design
5. **Clear and re-assign load patterns** -- existing patterns may have wrong types/names
6. **Check and update load cases** -- existing 0SPECX/0SPECXY need correct settings

**Workflow for existing model:**
```
1. Unlock model
2. Delete all existing structural objects (frames, areas, points)
3. Redefine stories from scratch
4. Redefine grid system
5. Verify/recreate all materials and sections
6. Proceed with normal modeling workflow
```

---

## 4. Input Parsing

### 4.1 Grid System

Extract grid labels + spacings from plan-reader output. Convert to absolute coordinates:
```python
# Grid spacing in cm from plan-reader -> cumulative coordinates in m
spacings_cm = [600, 800, 750, 600]  # between grid lines
coords_m = [0]
for s in spacings_cm:
    coords_m.append(coords_m[-1] + s / 100.0)
# Result: [0, 6.0, 14.0, 21.5, 27.5]
```

### 4.2 Section Name Parsing (D/B Swap Protection)

**CRITICAL RULE**: Section names use `{PREFIX}{WIDTH}X{DEPTH}` format, but the API needs `T3=Depth, T2=Width`.

```
PropFrame.SetRectangle(Name, Material, T3, T2)
                                        ^    ^
                                      DEPTH  WIDTH

B55X80 -> Width=55, Depth=80 -> SetRectangle("B55X80C350", "C350", 0.80, 0.55)
```

**Column naming**: `C{X向寬}X{Y向深}` -- X向=Global水平方向, Y向=Global垂直方向

See `references/section-parsing-rules.md` for full parsing logic.

### 4.3 Batch Section Expansion

From each plan-reader section, expand to **all size + grade combinations**:

- **Size range**: +-20cm from base, 5cm steps
- **Concrete grades**: C280, C315, C350, C420, C490
- **Every combination** becomes a separate section with grade suffix

Example: `B50X70` expands to:
- Widths: [30, 35, 40, 45, 50, 55, 60, 65, 70]
- Depths: [50, 55, 60, 65, 70, 75, 80, 85, 90]
- Grades: [C280, C315, C350, C420, C490]
- Total: 9 x 9 x 5 = **405 sections** from one base section

**Section naming with grade suffix (mandatory)**:

| Type | Format | Example |
|------|--------|---------|
| Beam | `B{W}X{D}C{fc}` | B80X70C350 |
| Small Beam | `SB{W}X{D}C{fc}` | SB35X65C280 |
| Wall Beam | `WB{W}X{D}C{fc}` | WB50X70C350 |
| Foundation Beam | `FB{W}X{D}C{fc}` | FB90X230C420 |
| Column | `C{W}X{D}C{fc}` | C150X130C420 |
| Slab | `S{T}C{fc}` | S15C280 |
| Wall | `W{T}C{fc}` | W20C350 |
| Raft | `FS{T}C{fc}` | FS100C350 |

### 4.4 Story-to-Floor Mapping

| Element | Plan Floor NF | ETABS Story |
|---------|--------------|-------------|
| Column / Wall | NF | (N+1)F -- spans from NF elevation to (N+1)F elevation |
| Beam (B/SB/WB) | NF | NF -- placed at NF elevation |
| Slab | NF | NF -- placed at NF elevation |

### 4.5 Strength Allocation by Floor

Users provide a table mapping floors to concrete grades:

```
| Floor Range | Column | Beam | Wall | Slab |
|-------------|--------|------|------|------|
| B3F~1F      | C490   | C420 | C420 | C350 |
| 2F~7F       | C420   | C350 | C350 | C280 |
| 8F~14F      | C350   | C280 | C280 | C280 |
| R1F~PRF     | C280   | C280 | C280 | C280 |
```

When creating elements: base section + floor strength = full section name.
Example: `C90X90` at 5F (column=C420) -> section name = `C90X90C420`

**Diaphragm wall (連續壁) material: always C280** unless user specifies otherwise.

---

## 5. Modeling Workflow (8 Phases)

### Phase 1: Initialize (Steps 1-2)

**Step 1**: Connect + set units + unlock
```python
# MCP preferred:
# mcp__etabs__set_units(unit_system="TON_M")
# mcp__etabs__unlock_model()

# Or via script:
SapModel.SetPresentUnits(12)  # TON/M
SapModel.SetModelIsLocked(False)
```

**Step 2**: Define materials
- Concrete: C280, C315, C350, C420, C490 (each with fc, E, Poisson, unit weight)
- Rebar: SD420, SD490

```python
# For each grade:
SapModel.PropMaterial.AddMaterial(f"C{fc}", 2, "", "", "")
SapModel.PropMaterial.SetMPIsotropic(f"C{fc}", E, 0.2, 1e-5)
SapModel.PropMaterial.SetWeightAndMass(f"C{fc}", 1, 2.4)
SapModel.PropMaterial.SetOConcrete_1(f"C{fc}", fc_tonm2, False, 1, 2, 1, 0.002, 0.005, -0.1, 0, 0)
```

### Phase 2: Batch Section Creation (Step 3)

**Step 3**: Collect all plan-reader sections -> expand -> create

- **Frame sections**: `PropFrame.SetRectangle(name, mat, T3=depth_m, T2=width_m)`
- **Walls**: `PropArea.SetWall(name, 0, 2, mat, t_m)` -- ShellType=2 (Membrane)
- **Slabs**: `PropArea.SetSlab(name, 0, 2, mat, t_m)` -- ShellType=2 (Membrane)
- **Raft slabs**: `PropArea.SetSlab(name, 0, 1, mat, t_m)` -- ShellType=1 (ShellThick)

Use `scripts/generate_sections.py` for batch generation.

### Phase 3: Grid + Stories (Steps 4-5)

**Step 4**: Create grid system
```python
# Via DatabaseTables:
SapModel.DatabaseTables.SetTableForEditingArray("Grid Lines", ...)
SapModel.DatabaseTables.ApplyEditedTables(True, 0, 0, 0, 0, "")
```

**Step 5**: Define stories (requires user-provided heights)

**IMPORTANT**: When working with existing models, ALWAYS redefine stories. Do not assume existing stories match the new design.

```python
SapModel.Story.SetStories_2(
    BaseElev, NumStories, StoryNames, StoryHeights,
    IsMasterStory, SimilarToStory, SpliceAbove, SpliceHeight, Color)
```

### Phase 4: Element Creation (Steps 6-11, per floor)

**IMPORTANT**: Select section with correct concrete grade based on strength allocation table.

**Step 6: Columns** -- Grid intersections, +1 floor rule
```python
SapModel.FrameObj.AddByCoord(x, y, z_bot, x, y, z_top, '', f"C90X90C{fc}")
```

**Step 7: Main beams** -- Along grid lines, span by span
```python
SapModel.FrameObj.AddByCoord(x1, y1, z, x2, y2, z, '', f"B55X80C{fc}")
```

**Step 8: Small beams** -- Use precise coordinates from plan-reader output

Plan-reader now provides exact coordinates (cm) for each small beam.
Convert to meters and place directly:

```python
# From plan-reader output: SB1, Y-dir, X=1290cm, from Y=0 to Y=2100cm
x = 12.90  # convert cm to m
y1, y2 = 0.0, 21.0
SapModel.FrameObj.AddByCoord(x, y1, z, x, y2, z, '', f"SB35X65C{fc}")
```

**CRITICAL: 小梁兩端連接性驗證**

每根小梁的兩個端點都必須與其他梁（大梁或小梁）或柱物件接合。
- 如果端點懸空（不接觸任何梁/柱），該小梁視為可疑
- 懸臂小梁極少見，通常只出現在陽台/露臺
- 發現懸空端點時，應懷疑對結構配置圖的理解有誤，回報讀圖階段重新確認

```python
# 驗證小梁連接性
for sb in secondary_beams:
    i_connected = point_touches_frame_or_column(sb.pt_i, all_frames)
    j_connected = point_touches_frame_or_column(sb.pt_j, all_frames)
    if not i_connected or not j_connected:
        warnings.append(f"WARNING: {sb.name} 端點懸空 - 請確認讀圖是否正確")
        # 不建立此小梁，等待確認
```

**Step 9: Shear walls** -- 4-point area, +1 floor rule
```python
X = [x1, x2, x2, x1]
Y = [y1, y2, y2, y1]
Z = [z_bot, z_bot, z_top, z_top]
SapModel.AreaObj.AddByCoord(4, X, Y, Z, '', f"W20C{fc}")
```

**Step 9b: Diaphragm walls (連續壁)** -- Same as shear walls, material = C280
```python
SapModel.AreaObj.AddByCoord(4, X, Y, Z, '', f"W80C280")  # always C280
```

**Step 10: Wall beams** -- Along wall tops
```python
SapModel.FrameObj.AddByCoord(x1, y1, z, x2, y2, z, '', f"WB50X70C{fc}")
```

**Step 11: Slabs** (樓板切割規則 — 關鍵步驟)

樓板必須以大梁和小梁為邊界進行切割，**不是**直接用 4 個 Grid Line 交點建立大板。

**切割規則：**
1. 每個樓板區域的邊界 = 大梁 + 小梁 + 牆
2. 以所有梁（大梁+小梁）作為切割線，將 Grid 圍區域分割成多個小板
3. 每個小板的頂點 = 梁的端點或梁與梁的交點

**FS 基礎版額外切割：**
- 除了與梁切割以外，每個區域再做 2x2 切割（分成 4 等分）
- 目的：讓彈簧 Kv 分布更均勻

**範例：**
一個 Grid 區域內有 2 根 Y 向小梁，則該區域被分為 3 塊板：
```
Grid 1 ──── SB1 ──── SB2 ──── Grid 2
  |          |        |          |
  |  Slab-A  | Slab-B |  Slab-C  |
  |          |        |          |
Grid A ──── SB1 ──── SB2 ──── Grid A
```

- Regular floors: Membrane section (S15C280 etc.)
- Foundation: ShellThick section (FS100C350 etc.)
```python
X = [x1, x2, x3, x4]
Y = [y1, y2, y3, y4]
Z = [z, z, z, z]
SapModel.AreaObj.AddByCoord(4, X, Y, Z, '', f"S15C{fc}")
```

### Phase 5: Property Assignment (Steps 12-18)

**Step 12: Slab/Wall modifiers** (10-element array, on section properties)
```python
# Slab + Wall (Membrane): f11=f22=f12=0.4, rest=1
SapModel.PropArea.SetModifiers("S15C280", [0.4, 0.4, 0.4, 1, 1, 1, 1, 1, 1, 1])
# Raft (ShellThick): f=0.4, m=0.7
SapModel.PropArea.SetModifiers("FS100C350", [0.4, 0.4, 0.4, 0.7, 0.7, 0.7, 1, 1, 1, 1])
```

**Step 13: Beam modifiers** (8-element array, on individual objects)
```python
SapModel.FrameObj.SetModifiers(beam_name, [1, 1, 1, 0.0001, 0.7, 0.7, 0.8, 0.8])
```

**Step 14: Column modifiers** (8-element array, on individual objects)
```python
SapModel.FrameObj.SetModifiers(col_name, [1, 1, 1, 0.0001, 0.7, 0.7, 0.95, 0.95])
```

**Step 15: Beam rebar** (on section properties)
- Regular beams: cover = 9cm / 9cm (0.09m)
- Foundation beams (FB/FSB/FWB): cover = 11cm / 15cm (0.11m / 0.15m)

**Step 16: Column rebar** (on section properties)
- Cover: 7cm (0.07m)
- NumR2:NumR3 = Width:Depth ratio (min=2, max=6)
- ToBeDesigned = True

**Step 17: Rigid zones** -- All frames, RZ=0.75
```python
# ASSIGN > Frame > End Length Offset > Rigid Zone Factor = 0.75
SapModel.FrameObj.SetEndLengthOffset(frame_name, True, 0, 0, 0.75)
```
**Apply to ALL frame objects (beams AND columns).**

**Step 18: End releases** -- Discontinuous beam ends release M2+M3
```python
# Check if each beam endpoint is shared with another frame
# If not shared -> release M2 + M3 at that end
release = [False, False, False, False, True, True]
no_release = [False, False, False, False, False, False]
SapModel.FrameObj.SetReleases(beam, i_release, j_release, [0]*6, [0]*6)
```

See `references/modifier-rebar-rules.md` for all rules and values.

### Phase 6: Foundation Support (Steps 19-21) — 基礎樓層 = BASE 上一層

**基礎樓層定義：BASE 上一層。BASE 層無任何物件。以下所有操作（鎖點/Kv/Kw）皆在基礎樓層執行。**

**Step 19: Base restraints** -- 在基礎樓層（BASE 上一層）

鎖點位置 = FS 基礎版所在樓層的節點 = 最底部柱子的底端節點
只鎖 UX, UY（水平方向），垂直方向由 Kv 彈簧處理。

```python
# 鎖點不在 BASE，而是在 BASE 上一層（FS 基礎版所在樓層）
# 等同於最底部柱子的底部端點
SapModel.PointObj.SetRestraint(pt, [True, True, False, False, False, False])
```

**Step 20: Raft slab springs + Diaphragm**

Kv 彈簧設置在 FS 基礎版的節點上。
FS 基礎版也必須設定 Diaphragm。

```python
# Kv 彈簧
SapModel.PointObj.SetSpring(raft_pt, [0, 0, Kv, 0, 0, 0])

# FS 基礎版 Diaphragm
SapModel.Diaphragm.SetDiaphragm("D_FS", False)  # rigid
for pt in raft_slab_corner_points:
    SapModel.PointObj.SetDiaphragm(pt, 3, "D_FS")
```

**Step 21: Edge beam line springs** -- Kw on edge foundation beams (ask user for Kw)
```python
SapModel.PropLineSpring.SetLineSpringProp("EdgeSpring", 0, Kw, 0, 0, 0, 0)
SapModel.FrameObj.SetSpringAssignment(beam_name, "EdgeSpring")
```

### Phase 7: Loads (Steps 22-26)

**Step 22**: Define load patterns

**IMPORTANT: Use company-internal load pattern names:**

| Load Pattern | Type Code | SW Mult | Description |
|-------------|-----------|---------|-------------|
| `DL`  | 1 (Dead)      | 1 | Dead load (自重) |
| `LL`  | 3 (Live)      | 0 | Live load |
| `EQXP` | 5 (Quake)   | 0 | Seismic +X |
| `EQXN` | 5 (Quake)   | 0 | Seismic -X |
| `EQYP` | 5 (Quake)   | 0 | Seismic +Y |
| `EQYN` | 5 (Quake)   | 0 | Seismic -Y |

**SDL 預設不建立，除非使用者明確要求。**
**Do NOT create other load pattern names** (no "Dead", "Live", "EQX", "EQY" etc.)

```python
patterns = [
    ("DL",   1, 1),    # Dead with self-weight = 1
    ("LL",   3, 0),    # Live
    ("EQXP", 5, 0),    # Seismic +X
    ("EQXN", 5, 0),    # Seismic -X
    ("EQYP", 5, 0),    # Seismic +Y
    ("EQYN", 5, 0),    # Seismic -Y
]
# SDL 預設不建立，除非使用者明確要求
```

**Step 22b**: Configure seismic load patterns (Auto Seismic)

For each EQ pattern, set User Coefficient parameters:

```python
# Parameters to set for each EQXP/EQXN/EQYP/EQYN:
# - ECC RATIO = 0.05
# - Base Shear Coefficient C = (ASK USER or read from EQ_PARAMS.txt)
# - Building Height Exp. K = 1
# - Top Story = PRF
# - Bottom Story = 1F
# - Direction: EQXP/EQXN = X, EQYP/EQYN = Y
# - Sign: P = positive (+), N = negative (-)
```

**If EQ_PARAMS.txt exists in model folder, read C value from there.**
**If not, ASK the user for the Base Shear Coefficient C value.**

**Step 23**: Slab loads — 使用 DL 和 LL，按區域套用預設值

| 區域 | DL (ton/m2) | LL (ton/m2) |
|------|-------------|-------------|
| 上構 (2F~RF) | 0.45 | 0.2 |
| 下構 (B_F~1F) | 0.15 | 0.5 |
| 1F 室內 | 0.3 | 0.5 |
| 1F 室外 | 0.6 | 1.0 |
| FS 基礎版 | 0.63 | — |

```python
SapModel.AreaObj.SetLoadUniform(slab, "DL", -dl_value, 6)  # 6=Global-Z
SapModel.AreaObj.SetLoadUniform(slab, "LL", -ll_value, 6)
# FS 基礎版只有 DL，沒有 LL
```

**Step 24**: Exterior wall beam line loads (外牆線載)

**IMPORTANT RULE**: Exterior wall line load is assigned to a main beam (大梁) ONLY when the **floor above** has a beam at the same position.

```
Formula: w = 2.4 * 0.15 * 0.6 * (story_height - beam_depth_above)

Where:
  2.4     = concrete unit weight (ton/m3)
  0.15    = wall thickness (m)
  0.6     = opening reduction factor
  story_height = height of current story (m)
  beam_depth_above = depth of the beam on the floor ABOVE (m)
```

**Logic:**
```python
for each exterior main beam at floor N:
    # Check if there is a beam at the same grid position on floor (N+1)
    if beam_exists_above(beam_grid_pos, floor_N_plus_1):
        beam_depth_above = get_beam_depth(beam_grid_pos, floor_N_plus_1)
        story_h = story_heights[floor_N]
        w = 2.4 * 0.15 * 0.6 * (story_h - beam_depth_above)
        if w > 0:
            # 方向 11 = Projected Gravity = 往下
            # 正值 = 重力方向（往下）, 負值 = 往上（錯誤！）
            SapModel.FrameObj.SetLoadDistributed(beam, "DL", 1, 11, 0, 1, w, w)
    # If NO beam above -> NO exterior wall load on this beam
```

**Step 25**: Response spectrum (from model folder `SPECTRUM.TXT`)

**IMPORTANT: Do NOT create new RSX/RSY load cases. Modify existing `0SPECX` and `0SPECXY`.**

```
Step 25a: Import spectrum function from file
  - DEFINE > Functions > Response Spectrum > Add New Function > FROM FILE
  - File: {model_folder}/SPECTRUM.TXT (Period vs Value format)
  - Function name: e.g., "SPEC_FUNC"

Step 25b: Modify existing load cases 0SPECX and 0SPECXY
  - DO NOT create new load cases
  - Modify 0SPECX:
    * Load Type = Acceleration
    * Load Name = U1
    * Function = SPEC_FUNC (the imported function name)
    * Scale Factor = 1
  - Modify 0SPECXY:
    * Load Type = Acceleration
    * Load Name = U1
    * Function = SPEC_FUNC
    * Scale Factor = 1
```

```python
# Step 25a: Create spectrum function from file
periods, sa_values = load_spectrum_file(f"{model_folder}/SPECTRUM.TXT")
SapModel.Func.FuncRS.SetUser("SPEC_FUNC", len(periods), periods, sa_values, 0.05)

# Step 25b: Modify existing 0SPECX
SapModel.LoadCases.ResponseSpectrum.SetLoads(
    "0SPECX", 1, ["U1"], ["SPEC_FUNC"], [1.0], ["Global"], [0])
SapModel.LoadCases.ResponseSpectrum.SetModalCase("0SPECX", "Modal")
SapModel.LoadCases.ResponseSpectrum.SetEccentricity("0SPECX", 0.05)

# Step 25b: Modify existing 0SPECXY
SapModel.LoadCases.ResponseSpectrum.SetLoads(
    "0SPECXY", 1, ["U1"], ["SPEC_FUNC"], [1.0], ["Global"], [0])
SapModel.LoadCases.ResponseSpectrum.SetModalCase("0SPECXY", "Modal")
SapModel.LoadCases.ResponseSpectrum.SetEccentricity("0SPECXY", 0.05)
```

**Step 26**: Load combinations

**EQV scale factor**: Read from `EQ_PARAMS.txt` or ASK the user.

```python
# Example load combination with EQV
# SapModel.RespCombo.SetCaseList("COMB_EQ", 0, "0SPECX", eqv_scale_factor)
```

### Phase 8: Diaphragm + Save + Verify (Steps 27-29)

**Step 27: Diaphragm** -- ONLY at slab corner points (含 FS 基礎版)

FS 基礎版也需要設定 Diaphragm（與一般樓層相同，設定在板角點）。

```python
SapModel.Diaphragm.SetDiaphragm(f"D_{story}", False)  # rigid
# For each slab area (including FS raft slabs):
ret = SapModel.AreaObj.GetPoints(area_name, 0, [])
for pt in ret[2]:
    SapModel.PointObj.SetDiaphragm(pt, 3, f"D_{story}")
```

**Step 28: Save**
```python
SapModel.File.Save(model_path)
```

**Step 29: Verify** -- Run `scripts/verify_model.py` or checks from `references/verification-queries.md`

---

## 6. Small Beam Position (Updated)

Plan-reader now provides precise coordinates. Simply convert cm to m:

```python
# Plan-reader output example:
# SB1 | Y | (1290, 0) | (1290, 2100) | X=1290 | Grid 2~3 | SB35X65

x = 1290 / 100.0  # = 12.9 m
y1 = 0 / 100.0     # = 0 m
y2 = 2100 / 100.0  # = 21.0 m
z = floor_elevation  # m

SapModel.FrameObj.AddByCoord(x, y1, z, x, y2, z, '', f"SB35X65C{fc}")
```

If plan-reader couldn't determine exact position, ASK USER for coordinates.

---

## 7. Parameters to Ask User

At the start of modeling, collect these from the user:

| # | Parameter | Format | Default |
|---|-----------|--------|---------|
| 1 | Story heights | per-floor list or standard+exceptions | None (must ask) |
| 2 | Strength allocation table | Excel file or verbal | None (must ask) |
| 3 | DL / LL loads | ton/m2 | 有預設值（見 Section 2.3），可覆蓋 |
| 4 | Foundation Kv | ton/m per point | None (must ask) |
| 5 | Edge beam Kw | ton/m/m | None (must ask) |
| 6 | Slab thickness | cm | 15 cm (confirm with user) |
| 7 | **Base Shear Coefficient C** | decimal | None (must ask or read EQ_PARAMS.txt) |
| 8 | **EQV Scale Factor** | decimal | None (must ask or read EQ_PARAMS.txt) |

---

## 8. Edge Cases

- **Same grid line, different spans have different beam sizes** -> create separate segments
- **SB35/40X65 dual-width notation** -> create two separate sections (SB35X65, SB40X65)
- **Irregular floor plans** -> only create elements listed in plan-reader output
- **Column size reduces at upper floors** -> each floor handled independently with its own section
- **Missing grid intersections** -> skip column at that location (don't assume)
- **Setback columns (退縮柱位)** -> plan-reader flags these; follow user's instructions
- **Diagonal columns (斜柱)** -> create as BRACE, not COLUMN
- **Diaphragm walls (連續壁)** -> always C280 material unless user says otherwise
- **共構下構範圍（多棟共用地下室只建一棟）**:
  - 情況 1：上構柱區已是最外邊 → 直接延續往下建
  - 情況 2：下構比上構大，最外邊不在 Grid Line → 按比例外推距離，最外邊不建柱
  - 情況 3：下構比上構大，最外邊在 Grid Line → 往外一跨到下一 Grid Line，最外邊不建柱
  - 同一案的不同立面（東/西/南/北）可能分別對應不同情況，需逐面判斷

---

## 9. Verification Checklist

```
[ ] Units = TON/M (12)?
[ ] All sections D/B correct? (T3=depth, T2=width)
[ ] Batch sections cover +-20cm / 5cm / all grades?
[ ] Column/wall floor = plan +1?
[ ] Every floor has slabs? (DON'T SKIP -- previously missed!)
[ ] 樓板按大小梁切割（非直接 Grid 交點建板）?
[ ] FS 基礎版額外 2x2 切割?
[ ] 小梁兩端都有接合其他梁/柱?
[ ] Slab/wall ShellType = Membrane (2)?
[ ] Raft ShellType = ShellThick (1)?
[ ] Slab/wall modifier: f11=f22=f12=0.4?
[ ] Raft modifier: f=0.4, m11=m22=m12=0.7?
[ ] Beam modifier: T=0.0001, I22/I33=0.7, Mass/Wt=0.8?
[ ] Column modifier: T=0.0001, I22/I33=0.7, Mass/Wt=0.95?
[ ] Regular beam cover = 9cm?
[ ] Foundation beam cover = top 11cm / bottom 15cm?
[ ] Column cover = 7cm?
[ ] Column bar distribution matches W:D ratio?
[ ] Column rebar = ToBeDesigned?
[ ] Rigid zone = 0.75 for all frames? (FrameObj.SetEndLengthOffset)
[ ] Discontinuous beam ends have M2+M3 release?
[ ] Base restraints = UX,UY at 基礎樓層 (BASE上一層, NOT at BASE)?
[ ] Raft points have Kv springs?
[ ] Edge beams have Kw line springs?
[ ] DL and LL loads assigned to slabs (by zone defaults)?
[ ] FS 基礎版有設 Diaphragm?
[ ] FS 基礎版有 DL=0.63 載重?
[ ] 外牆線載重方向為 GRAVITY（正值，非負值）?
[ ] Exterior wall line loads: only where beam exists above?
[ ] 載重工況無 SDL（除非使用者要求）?
[ ] Load patterns correct? (DL/LL/EQXP/EQXN/EQYP/EQYN)
[ ] EQ params: ECC=0.05, K=1, Top=PRF, Bottom=1F, C=user value?
[ ] Response spectrum imported FROM FILE (SPECTRUM.TXT)?
[ ] 0SPECX/0SPECXY modified (NOT new RSX/RSY created)?
[ ] Load combo EQV scale factor set correctly?
[ ] Diaphragm only at slab corner points (NOT all joints)?
[ ] Diaphragm walls (連續壁) use C280?
[ ] R1F 梁/板 = 頂樓配置?
[ ] R1F 柱 = 頂樓柱（+1規則）? R2F 柱 = R1F 柱?
[ ] R2F 以上用 R1F 核心區間延伸到 PRF?
[ ] 共構下構邊界逐面判斷（3種情況）? 最外邊不建柱?
[ ] Model saved?
```

---

## 10. Do's and Don'ts

### 鐵則（ABSOLUTE RULE — 違反即失敗）

1. **小梁位置絕對禁止用 1/2、1/3 grid 間距猜測！** 必須使用 plan-reader 從圖面逐根量測像素位置並等比例插值計算出的精確座標。如果 plan-reader 提供的座標全部落在等分位置，必須退回要求重新量測。小梁位置由住宅單元隔間決定，每根都不同。

2. **結構配置必須從結構配置圖讀取，禁止從舊模型複製或按比例縮放。** 新模型 = 新圖面，不是舊模型的變體。

3. **建模前必須交叉比對結構配置圖和建築平面圖**，確認實際建物範圍（可能不是完整矩形，例如 L 型缺角）。不可假設 Grid 交叉點全部有柱。

### DO
- `SetPresentUnits(12)` always first
- Parse D/B separately (T3=depth, T2=width)
- Apply +1 floor rule for columns and walls
- Process floor by floor, verify each step
- Batch-generate sections (+-20cm, 5cm step, all grades)
- **Build slabs on every floor** (missed in previous testing!)
- **樓板按大梁+小梁邊界切割**
- **FS 基礎版額外 2x2 切割**
- **小梁建立前驗證兩端連接性**
- Check beam end continuity before setting releases
- Assign diaphragm only to slab corner points
- **FS 基礎版設 Diaphragm**
- **基礎鎖點在 FS 所在樓層（非 BASE）**
- **外牆線載重方向 = GRAVITY（正值）**
- **載重分區套用預設值（上構/下構/1F/FS）**
- Use foundation beam cover 11cm/15cm (different from regular 9cm)
- Use Membrane for slabs/walls, ShellThick for raft only
- Ask user for strength table if not provided
- **Re-check everything in existing models (stories, materials, sections)**
- **Use DL/LL/EQXP/EQXN/EQYP/EQYN for load pattern names**
- **Import spectrum from SPECTRUM.TXT as FROM FILE function**
- **Modify existing 0SPECX/0SPECXY, do NOT create new RSX/RSY**
- **Set rigid zone RZ=0.75 on ALL frames via SetEndLengthOffset**
- **Assign exterior wall loads only where beam exists on floor above**
- **Use C280 for diaphragm walls (連續壁) unless user specifies otherwise**
- **Read EQ_PARAMS.txt for C and scale factors, or ask user**

### DON'T
- **用 1/2、1/3 等分假設放置小梁（鐵則禁令！必須從圖面量測像素位置計算）**
- **從舊模型複製/縮放結構配置到新模型（鐵則禁令！必須從圖面讀取）**
- **假設建物範圍是完整矩形（鐵則禁令！必須交叉比對建築平面）**
- Guess T3/T2 order -- always verify: T3=Depth, T2=Width
- Assume a complete rectangular grid -- only use plan-reader data
- Skip the +1 floor rule for columns/walls
- Use `find_etabs` -- it requires FreeCAD/PySide2
- Use full fixed restraints at foundation (only UX, UY — at 基礎樓層, NOT BASE)
- **BASE 層無任何物件 — 鎖點/Kv/Kw 全部設在基礎樓層（BASE 上一層）**
- Assign diaphragm to all joints (only slab corner points)
- Forget cm->m conversion (divide by 100)
- Skip slab creation (every beam-enclosed area needs a slab)
- **不要用 Grid 交點直接建大板（要切割）**
- **不要建立懸空小梁（端點必須接合其他構件）**
- Use ShellThick for regular slabs (use Membrane, except raft)
- Assume concrete grades -- always reference the strength allocation table
- **Skip steps when working with existing models**
- **不要建立 SDL（除非使用者要求）**
- **Create "Dead", "Live", "EQX", "EQY" load patterns (use DL/LL/EQXP...)**
- **Create new RSX/RSY load cases (modify existing 0SPECX/0SPECXY)**
- **Assign exterior wall load to beams with no beam above**
- **外牆線載重不要用負值（會變成往上）**
- **Forget to set rigid zone factor (RZ=0.75) on all frames**
- **Forget to ask for Base Shear Coefficient C and EQV scale factor**

---

## 11. Cross References

- Plan-reader output format: `skills/plan-reader/SKILL.md` Section 10
- Section parsing details: `references/section-parsing-rules.md`
- Modifier/rebar/release rules: `references/modifier-rebar-rules.md`
- Verification code snippets: `references/verification-queries.md`
- API lookup: `skills/etabs-api-lookup.md`
- Task index: `api_docs_index/task_index.md`
- Modeling interfaces: `api_docs_index/group_b_analysis.md`
- Analysis interfaces: `api_docs_index/group_a_analysis.md`

## 12. Scripts

| Script | Purpose |
|--------|---------|
| `scripts/connect_etabs.py` | comtypes connection, set TON/M, unlock |
| `scripts/generate_sections.py` | Batch expand + create all sections |
| `scripts/add_floor_elements.py` | Create columns/beams/walls/slabs per floor |
| `scripts/assign_properties.py` | Modifiers, rebar, rigid zones, releases, diaphragms |
| `scripts/assign_loads.py` | Load patterns, slab/beam loads, spectrum, springs |
| `scripts/verify_model.py` | Full model verification report |
