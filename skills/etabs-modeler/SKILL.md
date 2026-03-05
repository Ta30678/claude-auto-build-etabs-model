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
- **Add to existing**: Attach to open model, add elements to specific floors

**Upstream**: `skills/plan-reader/SKILL.md` (Section 7 output format)
**Downstream**: Analysis run, design check

---

## 2. Prerequisites

Before starting, ensure:
1. **ETABS 22** is running (or will be launched)
2. **Execution method**: MCP tools (`mcp__etabs__run_python`) preferred; fallback to `Bash` + `scripts/connect_etabs.py`
3. **User must provide** (ask if missing):
   - Story heights (each floor or standard + exceptions)
   - Strength allocation table (`強度分配.xlsx` or verbal description)
   - SDL and Live load values (ton/m2)
   - Foundation Kv (ton/m) and edge beam Kw (ton/m/m) values
   - Response spectrum file path (`spectrum.txt`)
   - Slab thickness (if plan-reader didn't output it; default 15cm)

**IMPORTANT**: If the user hasn't provided the strength allocation table, you MUST ask for it. Do NOT assume concrete grades.

---

## 3. Input Parsing

### 3.1 Grid System

Extract grid labels + spacings from plan-reader output. Convert to absolute coordinates:
```python
# Grid spacing in cm from plan-reader -> cumulative coordinates in m
spacings_cm = [600, 800, 750, 600]  # between grid lines
coords_m = [0]
for s in spacings_cm:
    coords_m.append(coords_m[-1] + s / 100.0)
# Result: [0, 6.0, 14.0, 21.5, 27.5]
```

### 3.2 Section Name Parsing (D/B Swap Protection)

**CRITICAL RULE**: Section names use `{PREFIX}{WIDTH}X{DEPTH}` format, but the API needs `T3=Depth, T2=Width`.

```
PropFrame.SetRectangle(Name, Material, T3, T2)
                                        ^    ^
                                      DEPTH  WIDTH

B55X80 → Width=55, Depth=80 → SetRectangle("B55X80C350", "C350", 0.80, 0.55)
```

See `references/section-parsing-rules.md` for full parsing logic.

### 3.3 Batch Section Expansion

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

### 3.4 Story-to-Floor Mapping

| Element | Plan Floor NF | ETABS Story |
|---------|--------------|-------------|
| Column / Wall | NF | (N+1)F — spans from NF elevation to (N+1)F elevation |
| Beam (B/SB/WB) | NF | NF — placed at NF elevation |
| Slab | NF | NF — placed at NF elevation |

### 3.5 Strength Allocation by Floor

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
Example: `C90X90` at 5F (column=C420) → section name = `C90X90C420`

---

## 4. Modeling Workflow (8 Phases)

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

**Step 3**: Collect all plan-reader sections → expand → create

- **Frame sections**: `PropFrame.SetRectangle(name, mat, T3=depth_m, T2=width_m)`
- **Walls**: `PropArea.SetWall(name, 0, 2, mat, t_m)` — ShellType=2 (Membrane)
- **Slabs**: `PropArea.SetSlab(name, 0, 2, mat, t_m)` — ShellType=2 (Membrane)
- **Raft slabs**: `PropArea.SetSlab(name, 0, 1, mat, t_m)` — ShellType=1 (ShellThick)

Use `scripts/generate_sections.py` for batch generation.

### Phase 3: Grid + Stories (Steps 4-5)

**Step 4**: Create grid system
```python
# Via DatabaseTables:
SapModel.DatabaseTables.SetTableForEditingArray("Grid Lines", ...)
SapModel.DatabaseTables.ApplyEditedTables(True, 0, 0, 0, 0, "")
```

**Step 5**: Define stories (requires user-provided heights)
```python
SapModel.Story.SetStories_2(
    BaseElev, NumStories, StoryNames, StoryHeights,
    IsMasterStory, SimilarToStory, SpliceAbove, SpliceHeight, Color)
```

### Phase 4: Element Creation (Steps 6-11, per floor)

**IMPORTANT**: Select section with correct concrete grade based on strength allocation table.

**Step 6: Columns** — Grid intersections, +1 floor rule
```python
SapModel.FrameObj.AddByCoord(x, y, z_bot, x, y, z_top, '', f"C90X90C{fc}")
```

**Step 7: Main beams** — Along grid lines, span by span
```python
SapModel.FrameObj.AddByCoord(x1, y1, z, x2, y2, z, '', f"B55X80C{fc}")
```

**Step 8: Small beams** — Calculate position from span description
```
"Grid X1~X2 / along Y" → x = midpoint(X1,X2), beam runs in Y direction
"2 per span" → at 1/3 and 2/3 points
"midspan" → at 0.5
```

**Step 9: Shear walls** — 4-point area, +1 floor rule
```python
X = [x1, x2, x2, x1]
Y = [y1, y2, y2, y1]
Z = [z_bot, z_bot, z_top, z_top]
SapModel.AreaObj.AddByCoord(4, X, Y, Z, '', f"W20C{fc}")
```

**Step 10: Wall beams** — Along wall tops
```python
SapModel.FrameObj.AddByCoord(x1, y1, z, x2, y2, z, '', f"WB50X70C{fc}")
```

**Step 11: Slabs** (DO NOT SKIP — previously missed in testing!)
- Every beam-enclosed region needs a slab
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

**Step 17: Rigid zones** — All frames, RZ=0.75
```python
SapModel.FrameObj.SetEndLengthOffset(frame_name, True, 0, 0, 0.75)
```

**Step 18: End releases** — Discontinuous beam ends release M2+M3
```python
# Check if each beam endpoint is shared with another frame
# If not shared → release M2 + M3 at that end
release = [False, False, False, False, True, True]
no_release = [False, False, False, False, False, False]
SapModel.FrameObj.SetReleases(beam, i_release, j_release, [0]*6, [0]*6)
```

See `references/modifier-rebar-rules.md` for all rules and values.

### Phase 6: Foundation Support (Steps 19-21)

**Step 19: Base restraints** — UX, UY ONLY (not full fixed)
```python
SapModel.PointObj.SetRestraint(pt, [True, True, False, False, False, False])
```

**Step 20: Raft slab springs** — Kv at each raft slab point (ask user for Kv)
```python
SapModel.PointObj.SetSpring(pt, [0, 0, Kv, 0, 0, 0])
```

**Step 21: Edge beam line springs** — Kw on edge foundation beams (ask user for Kw)
```python
SapModel.PropLineSpring.SetLineSpringProp("EdgeSpring", 0, Kw, 0, 0, 0, 0)
SapModel.FrameObj.SetSpringAssignment(beam_name, "EdgeSpring")
```

### Phase 7: Loads (Steps 22-25)

**Step 22**: Define load patterns (Dead SW=1, SDL SW=0, Live SW=0, EQX, EQY)

**Step 23**: Slab uniform loads (ask user for SDL and Live values)
```python
SapModel.AreaObj.SetLoadUniform(slab, "SDL", -sdl_value, 6)   # 6=Global-Z
SapModel.AreaObj.SetLoadUniform(slab, "Live", -live_value, 6)
```

**Step 24**: Beam line loads (wall weight, auto-calculated)
```
w = 2.4 * 0.15 * 0.6 * (story_height - beam_depth)
```
```python
SapModel.FrameObj.SetLoadDistributed(beam, "SDL", 1, 11, 0, 1, -w, -w)
```

**Step 25**: Response spectrum from user-provided `spectrum.txt`
```python
# Read Period-Sa pairs from text file
# Create RS function: SapModel.Func.FuncRS.SetUser(name, n, periods, sa, damping)
# Create RS cases: RSX (U1), RSY (U2) with 5% eccentricity
```

### Phase 8: Diaphragm + Save + Verify (Steps 26-28)

**Step 26: Diaphragm** — ONLY at slab corner points
```python
SapModel.Diaphragm.SetDiaphragm(f"D_{story}", False)  # rigid
# For each slab area:
ret = SapModel.AreaObj.GetPoints(area_name, 0, [])
for pt in ret[2]:
    SapModel.PointObj.SetDiaphragm(pt, 3, f"D_{story}")
```

**Step 27: Save**
```python
SapModel.File.Save(model_path)
```

**Step 28: Verify** — Run `scripts/verify_model.py` or checks from `references/verification-queries.md`

---

## 5. Small Beam Position Decision Tree

```
Input from plan-reader          Action
─────────────────────────────   ──────────────────────────────
"Grid X1~X2 / along Y"       → x = midpoint(X1, X2), beam runs Y
"Grid Y1~Y2 / along X"       → y = midpoint(Y1, Y2), beam runs X
"2 per span"                  → place at 1/3 and 2/3 of span
"midspan"                     → place at 0.5 of span
"@3m spacing"                 → calculate count = span/3, distribute evenly
unclear description           → ASK USER for coordinates
```

---

## 6. Parameters to Ask User

At the start of modeling, collect these from the user:

| # | Parameter | Format | Default |
|---|-----------|--------|---------|
| 1 | Story heights | per-floor list or standard+exceptions | None (must ask) |
| 2 | Strength allocation table | Excel file or verbal | None (must ask) |
| 3 | SDL load | ton/m2 | None (must ask) |
| 4 | Live load | ton/m2 | None (must ask) |
| 5 | Foundation Kv | ton/m per point | None (must ask) |
| 6 | Edge beam Kw | ton/m/m | None (must ask) |
| 7 | spectrum.txt path | file path | model_dir/spectrum.txt |
| 8 | Slab thickness | cm | 15 cm (confirm with user) |

---

## 7. Edge Cases

- **Same grid line, different spans have different beam sizes** → create separate segments
- **SB35/40X65 dual-width notation** → create two separate sections (SB35X65, SB40X65)
- **Irregular floor plans** → only create elements listed in plan-reader output
- **Column size reduces at upper floors** → each floor handled independently with its own section
- **Missing grid intersections** → skip column at that location (don't assume)

---

## 8. Verification Checklist

```
[ ] Units = TON/M (12)?
[ ] All sections D/B correct? (T3=depth, T2=width)
[ ] Batch sections cover +-20cm / 5cm / all grades?
[ ] Column/wall floor = plan +1?
[ ] Every floor has slabs? (DON'T SKIP — previously missed!)
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
[ ] Rigid zone = 0.75 for all frames?
[ ] Discontinuous beam ends have M2+M3 release?
[ ] Base restraints = UX,UY only (NOT full fixed)?
[ ] Raft points have Kv springs?
[ ] Edge beams have Kw line springs?
[ ] SDL and Live loads assigned to slabs?
[ ] Beam line loads (wall weight) assigned?
[ ] Response spectrum created from spectrum.txt?
[ ] Diaphragm only at slab corner points (NOT all joints)?
[ ] Model saved?
```

---

## 9. Do's and Don'ts

### DO
- `SetPresentUnits(12)` always first
- Parse D/B separately (T3=depth, T2=width)
- Apply +1 floor rule for columns and walls
- Process floor by floor, verify each step
- Batch-generate sections (+-20cm, 5cm step, all grades)
- **Build slabs on every floor** (missed in previous testing!)
- Check beam end continuity before setting releases
- Assign diaphragm only to slab corner points
- Use foundation beam cover 11cm/15cm (different from regular 9cm)
- Use Membrane for slabs/walls, ShellThick for raft only
- Ask user for strength table if not provided

### DON'T
- Guess T3/T2 order — always verify: T3=Depth, T2=Width
- Assume a complete rectangular grid — only use plan-reader data
- Skip the +1 floor rule for columns/walls
- Use `find_etabs` — it requires FreeCAD/PySide2
- Use full fixed restraints at foundation (only UX, UY)
- Assign diaphragm to all joints (only slab corner points)
- Forget cm→m conversion (divide by 100)
- Skip slab creation (every beam-enclosed area needs a slab)
- Use ShellThick for regular slabs (use Membrane, except raft)
- Assume concrete grades — always reference the strength allocation table

---

## 10. Cross References

- Plan-reader output format: `skills/plan-reader/SKILL.md` Section 7
- Section parsing details: `references/section-parsing-rules.md`
- Modifier/rebar/release rules: `references/modifier-rebar-rules.md`
- Verification code snippets: `references/verification-queries.md`
- API lookup: `skills/etabs-api-lookup.md`
- Task index: `api_docs_index/task_index.md`
- Modeling interfaces: `api_docs_index/group_b_analysis.md`
- Analysis interfaces: `api_docs_index/group_a_analysis.md`

## 11. Scripts

| Script | Purpose |
|--------|---------|
| `scripts/connect_etabs.py` | comtypes connection, set TON/M, unlock |
| `scripts/generate_sections.py` | Batch expand + create all sections |
| `scripts/add_floor_elements.py` | Create columns/beams/walls/slabs per floor |
| `scripts/assign_properties.py` | Modifiers, rebar, rigid zones, releases, diaphragms |
| `scripts/assign_loads.py` | Load patterns, slab/beam loads, spectrum, springs |
| `scripts/verify_model.py` | Full model verification report |
