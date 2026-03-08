# RC Design Knowledge Base — ETABS Size Iteration

Complete reference for the analysis-design iteration workflow used by `design/gs_12_iterate.py`.

---

## 1. Floor Classification

| Zone | Floors | Definition |
|------|--------|------------|
| Substructure | 1F and below (B3F, B2F, B1F, 1F) | At or below 1F elevation |
| Superstructure | Above 1F (2F, 3F, ..., RF, PRF) | Above 1F elevation |

- Determined by comparing each floor's cumulative elevation to 1F elevation
- Mezzanines (e.g. 1MF) classified by their actual elevation
- Only superstructure is iterated; substructure gets a single check pass

---

## 2. ACI 318-19 Sway Frame Types

Sway type assignment via `SapModel.DesignConcrete.ACI318_19.SetOverwrite(frame, 1, value)`:
- **Item = 1** → Framing type overwrite
- **Value**: 0 = Program Default, 1 = Sway Special, 2 = Sway Intermediate, 3 = Sway Ordinary, 4 = Non-sway

### Assignment Rules

| Frame Type | Superstructure (2F~RF) | Rooftop (R2F~PRF) | Substructure (1F and below) |
|------------|----------------------|-------------------|----------------------------|
| Column (C) | Sway Special (1) | Sway Ordinary (3) | Sway Ordinary (3) |
| Beam (B, WB) | Sway Special (1) | Sway Ordinary (3) | Sway Ordinary (3) |
| Small Beam (SB) | Sway Ordinary (3) | Sway Ordinary (3) | Sway Ordinary (3) |
| Foundation (FB/FSB/FWB) | — | — | Sway Ordinary (3) |
| Wall | Not set (area object) | Not set | Not set |

**Rooftop ordinary rule**: R2F and above (including PRF) use Sway Ordinary. R1F remains Sway Special if it's superstructure.

Detection logic:
```python
def is_rooftop_ordinary(story_name):
    if story_name == "PRF": return True
    m = re.match(r'^R(\d+)F$', story_name)
    return m and int(m.group(1)) >= 2
```

---

## 3. Design Load Combinations

| Phase | Combos | Count |
|-------|--------|-------|
| Superstructure | USS01, USS02, USS68S~USS83S | 18 |
| Substructure | BUSS01~BUSS67 | 67 |

- Combos already exist in the model (created during load setup)
- `gs_12` enables/disables them via `SetComboStrength(combo_name, True/False)`
- Phase 1 enables USS, disables BUSS
- Phase 2 enables BUSS, disables USS

API:
```python
SapModel.DesignConcrete.SetComboStrength("USS01", True)   # enable
SapModel.DesignConcrete.SetComboStrength("BUSS01", False) # disable
```

---

## 4. Rebar Ratio Computation

### Column Ratio

```
ratio = PMMArea / (W_m × D_m)
```

- **PMMArea**: total longitudinal rebar area (m²) from design results
- **W_m, D_m**: column dimensions in meters (parsed from section name)
- Example: C90X90 with PMMArea=0.0081 → ratio = 0.0081 / (0.9 × 0.9) = 0.01 = 1%

### Beam Ratio

```
ratio = max(TopArea, BotArea) / (W_m × d_eff)
d_eff = D_m - cover
```

- **TopArea, BotArea**: max reinforcement areas from design results (m²)
- **cover**: 0.09m (9cm) for regular beams
- **d_eff**: effective depth
- Example: B55X80, cover=9cm → d_eff = 0.80 - 0.09 = 0.71m, denom = 0.55 × 0.71 = 0.3905

---

## 5. ETABS Design API Reference

### Run Analysis + Design

```python
SapModel.File.Save()
SapModel.Analyze.RunAnalysis()
SapModel.DesignConcrete.SetCode("ACI 318-19")
SapModel.DesignConcrete.StartDesign()
```

### GetSummaryResultsColumn

```python
ret = SapModel.DesignConcrete.GetSummaryResultsColumn(
    frame_name, 0, [], [], [], [], [], [], [], [], [], [], [], [])
```

| Index | Content | Type |
|-------|---------|------|
| ret[0] | NumberItems | int |
| ret[1] | FrameName (list) | str[] |
| ret[2] | (reserved) | — |
| ret[3] | (reserved) | — |
| ret[4] | (reserved) | — |
| ret[5] | **PMMArea** (list) | float[] (m²) |

Use `max(ret[5])` to get the governing rebar area.

### GetSummaryResultsBeam

```python
ret = SapModel.DesignConcrete.GetSummaryResultsBeam(
    frame_name, 0, [], [], [], [], [], [], [], [], [], [], [], [], [], [])
```

| Index | Content | Type |
|-------|---------|------|
| ret[0] | NumberItems | int |
| ret[4] | **TopArea** (list) | float[] (m²) |
| ret[6] | **BottomArea** (list) | float[] (m²) |

Use `max(max(ret[4]), max(ret[6]))` for worst rebar area.

### COM Return Convention

**IMPORTANT**: ret[0] is the first **ref parameter** (NumberItems), NOT the method return code. This matches the conftest.py pattern for `GetAllFrames`.

---

## 6. Resize Thresholds & Logic

### Column Resize

| Condition | Action |
|-----------|--------|
| ratio <= 1% (COL_REBAR_DOWNSIZE) | Downsize: W-10, D-10 |
| 1% < ratio <= 4% | No change |
| ratio > 4% (COL_REBAR_MAX) | Upsize: W+10, D+10 |

- Step: 10cm (both W and D change together)
- Minimum dimension: 30cm × 30cm
- If already at minimum, no downsize possible → skip

### Beam Resize

| Condition | Action |
|-----------|--------|
| ratio < 1% (BEAM_REBAR_MIN) | Downsize: W-5 first, then D-5 if W at min |
| 1% <= ratio <= 2% | No change |
| ratio > 2% (BEAM_REBAR_MAX) | Upsize: W+5 first; if (W+5)/D >= 1.2, D+5 instead |

- Step: 5cm
- Minimum: W=25cm, D=40cm
- Width changes first (both up and down)
- Width-to-depth ratio cap: 1.2 — prevents overly wide beams
- Foundation beams (FB, FSB, FWB) are **excluded** from iteration

### Threshold Boundaries (Edge Cases)

- Column downsize: `<=` 1% (includes exactly 1%)
- Column upsize: `>` 4% (excludes exactly 4%)
- Beam downsize: `<` 1% (excludes exactly 1%)
- Beam upsize: `>` 2% (excludes exactly 2%)

---

## 7. Column Constraints

### Rule 1: Monotonic Non-Decreasing Downward

Lower floors must have column dimensions >= upper floors:
```
B3F.w >= B2F.w >= B1F.w >= 1F.w >= 2F.w >= ... >= RF.w
```

### Rule 2: Strength Boundary Equalization

At floors where concrete grade (fc) changes, column sizes on both sides must be **equal**:
```
If fc(7F) = 420 and fc(8F) = 350:
  → 7F and 8F columns at same position must have same W and D
  → Take max(W_7F, W_8F) and max(D_7F, D_8F) for both
```

### Constraint Propagation Algorithm

```
repeat up to 3 passes:
  1. Boundary equalization sweep:
     For each adjacent pair where fc differs:
       max_w = max(below.w, above.w)
       max_d = max(below.d, above.d)
       Set both to (max_w, max_d)

  2. Monotonic sweep (top to bottom):
     For i from top-1 down to bottom:
       lower.w = max(lower.w, upper.w)
       lower.d = max(lower.d, upper.d)

  3. If no changes occurred, break early
```

The multi-pass is needed because boundary equalization can create new monotonic violations, and monotonic enforcement can create new boundary mismatches.

### Column Position Grouping

Columns are grouped by `(round(x, 2), round(y, 2))` — same grid position across floors.

---

## 8. Beam Grouping & Resize

- Beams grouped by `(section_name, story)` — all beams with same section on same floor
- **Worst ratio** in the group drives the resize decision for all members in that group
- This ensures consistency: all B55X80C350 beams on 3F either all resize or all stay

---

## 9. Oscillation Prevention

Without prevention, a column might oscillate: upsize in iteration 1, downsize in iteration 2, upsize in iteration 3, forever.

### Tracking

```python
osc_history = {
    frame_or_group_key: {
        "last_dir": "up" | "down",
        "toggles": int
    }
}
```

### Logic

1. On each resize proposal, check if direction differs from `last_dir`
2. If direction changed, increment `toggles`
3. If `toggles >= 2`, **freeze** the member:
   - If proposing downsize, revert to larger size (add step back)
   - Skip the change entirely
4. This guarantees convergence within max iterations

---

## 10. Section Creation During Iteration

When a resize produces a section that doesn't exist yet:

```python
def ensure_section_exists(SapModel, prefix, w_cm, d_cm, fc):
    name = f"{prefix}{w_cm}X{d_cm}C{fc}"  # e.g. C100X100C420
    mat = f"C{fc}"

    # CRITICAL: T3=Depth, T2=Width
    SapModel.PropFrame.SetRectangle(name, mat, d_cm/100, w_cm/100)

    if prefix == "C":
        SapModel.PropFrame.SetRebarColumn(
            name, "SD420", "SD420",
            1, 1, 0.07,          # cover = 7cm
            4,                    # corner bars
            num_r3, num_r2,      # bar distribution
            "#8", "#4", 0.15,    # rebar/tie sizes, spacing
            2, 2, True)          # tie counts, ToBeDesigned
    else:
        SapModel.PropFrame.SetRebarBeam(
            name, "SD420", "SD420",
            0.09, 0.09,          # cover top/bot = 9cm
            0, 0, 0, 0, True)   # ToBeDesigned
```

After section change, modifiers must be re-applied:
- Column: `[1, 1, 1, 0.0001, 0.7, 0.7, 0.95, 0.95]`
- Beam: `[1, 1, 1, 0.0001, 0.7, 0.7, 0.8, 0.8]`

---

## 11. Two-Phase Design Process

### Phase 1: Superstructure Iteration

1. Enable USS combos (18), disable BUSS combos (67)
2. Assign sway types to all frames
3. Loop up to 5 iterations:
   a. Save → RunAnalysis → SetCode → StartDesign
   b. Extract column results (PMMArea) and beam results (TopArea/BotArea)
   c. Compute rebar ratios
   d. Propose column resizes (with oscillation check)
   e. Enforce column constraints (boundary + monotonic)
   f. Propose beam resizes (with oscillation check)
   g. Apply all section changes
   h. If no changes → **CONVERGED**, break
4. Track final superstructure column sizes by position

### Phase 2: Substructure Check

1. Enable BUSS combos (67), disable USS combos (18)
2. For each substructure column, ensure its size >= the lowest superstructure column at same (x, y)
3. Apply any upsizes
4. Run one final analysis + design (no iteration)

---

## 12. Configurable Parameters

All defaults live in `constants.py`. Override via `config["iteration"]`:

```json
{
  "iteration": {
    "max_iterations": 5,
    "col_rebar_downsize": 0.01,
    "col_rebar_max": 0.04,
    "col_resize_step": 10,
    "beam_rebar_min": 0.01,
    "beam_rebar_max": 0.02,
    "beam_resize_step": 5,
    "beam_max_width_ratio": 1.2,
    "design_code": "ACI 318-19",
    "skip_prefixes": ["FB", "FSB", "FWB"]
  }
}
```

---

## 13. Section Naming Convention

Format: `{PREFIX}{WIDTH}X{DEPTH}C{fc}`

| Prefix | Element | Example |
|--------|---------|---------|
| C | Column | C90X90C420 |
| B | Beam | B55X80C350 |
| SB | Small Beam | SB30X50C280 |
| WB | Wall Beam | WB50X70C350 |
| FB | Foundation Beam | FB90X230C420 |

- WIDTH = X-direction dimension (cm)
- DEPTH = Y-direction dimension (cm)
- fc = concrete compressive strength (kgf/cm²)
- API mapping: T3 = Depth, T2 = Width (SetRectangle)
