---
name: rc-design
description: >
  ETABS RC analysis & design knowledge base. Covers ACI 318-19 sway types,
  rebar ratio computation, section resize iteration, column constraints,
  design combos (USS/BUSS), and the full gs_12 iteration workflow.
  Trigger: "rc design", "分析設計", "配筋檢討", "斷面迭代", "RC設計",
  "rebar ratio", "sway type", "/rc-design".
---

# RC Design Skill

## 1. Overview

This skill automates the column/beam sizing optimization loop after an ETABS model has been built (gs_01~gs_11). It wraps `gs_12_iterate.run(SapModel, config)` with pre-flight validation and post-run verification.

**What it does:**
1. Classifies floors into superstructure / substructure
2. Assigns ACI 318-19 sway frame types
3. Iterates superstructure: analyze → design → check rebar ratios → resize sections → repeat (max 5 rounds)
4. Enforces column constraints: monotonic downward + strength boundary equalization
5. Checks substructure columns >= superstructure

**Source**: `golden_scripts/design/gs_12_iterate.py`

---

## 2. Prerequisites

Before invoking this skill, ensure:

| Requirement | How to Verify |
|-------------|--------------|
| ETABS 22 running | Process visible in taskbar |
| Model built (gs_01~11 complete) | Frames, areas, stories exist in model |
| `model_config.json` available | File path known, has `stories` + `strength_map` |
| Load combos exist | USS01, USS02, USS68S~USS83S, BUSS01~BUSS67 in model |
| Model saved | No unsaved changes |

---

## 3. Pre-flight Checks

Before calling `gs_12_iterate.run()`, verify:

```python
# 1. Connect to ETABS
from find_etabs import find_etabs
etabs, _ = find_etabs(run=False, backup=False)
SapModel = etabs.SapModel

# 2. Load config
import json
with open("model_config.json") as f:
    config = json.load(f)

# 3. Verify config has required keys
assert "stories" in config, "Config missing 'stories'"
assert "strength_map" in config, "Config missing 'strength_map'"

# 4. Verify model has frames
ret = SapModel.FrameObj.GetAllFrames(
    0, [], [], [], [], [], [], [], [], [], [], [],
    [], [], [], [], [], [], [], [])
assert ret[0] > 0, f"Model has no frames (count={ret[0]})"

# 5. Verify at least one design combo exists
ret_combo = SapModel.DesignConcrete.SetComboStrength("USS01", True)
assert ret_combo == 0, "USS01 combo not found — run gs_10_loads first"
```

### Optional: User Overrides

Ask the user if they want to customize iteration parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_iterations` | 5 | Max iteration rounds |
| `col_rebar_downsize` | 0.01 | Column downsize threshold (<=) |
| `col_rebar_max` | 0.04 | Column upsize threshold (>) |
| `beam_rebar_min` | 0.01 | Beam downsize threshold (<) |
| `beam_rebar_max` | 0.02 | Beam upsize threshold (>) |

If user provides overrides, add them to `config["iteration"]` before calling run.

---

## 4. Execution

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "golden_scripts"))
from design.gs_12_iterate import run

run(SapModel, config)
```

This runs the full two-phase process:
- **Phase 1**: Superstructure iteration (USS combos, up to 5 rounds)
- **Phase 2**: Substructure check (BUSS combos, single pass)

Console output shows per-iteration stats: rebar ratio min/max/avg, change counts, convergence status.

---

## 5. Post-run Verification

After `run()` completes, verify the results:

### 5.1 Check Rebar Ratios

```python
from design.gs_12_iterate import (
    get_all_frames_data, _classify_frames, classify_floors,
    extract_column_results, extract_beam_results
)

super_stories, sub_stories, _, all_stories = classify_floors(config)
frames_data = get_all_frames_data(SapModel)
columns, beams = _classify_frames(frames_data, super_stories, ["FB", "FSB", "FWB"])

col_results = extract_column_results(SapModel, columns)
beam_results = extract_beam_results(SapModel, beams)

# Column ratios should be between 1% and 4%
col_out_of_range = [c for c in col_results if c["ratio"] <= 0.01 or c["ratio"] > 0.04]
print(f"Columns out of range: {len(col_out_of_range)}/{len(col_results)}")

# Beam ratios should be between 1% and 2%
beam_out_of_range = [b for b in beam_results if b["ratio"] < 0.01 or b["ratio"] > 0.02]
print(f"Beams out of range: {len(beam_out_of_range)}/{len(beam_results)}")
```

### 5.2 Check Column Monotonicity

```python
from constants import build_strength_lookup, parse_frame_section
from design.gs_12_iterate import _build_column_positions

col_positions = _build_column_positions(col_results)
story_idx = {s: i for i, s in enumerate(all_stories)}

violations = []
for pos, cols in col_positions.items():
    cols.sort(key=lambda c: story_idx.get(c["story"], 0))
    for i in range(len(cols) - 1):
        if cols[i]["w"] < cols[i+1]["w"] or cols[i]["d"] < cols[i+1]["d"]:
            violations.append((pos, cols[i]["story"], cols[i+1]["story"]))

print(f"Monotonic violations: {len(violations)}")
```

### 5.3 Check Convergence

If console output shows "WARNING: Max iterations reached", review the remaining out-of-range members. Common causes:
- Members oscillating between up/down (should be caught by oscillation prevention)
- Column constraints forcing sizes that conflict with ratio targets
- Very high/low ratios that need multiple resize steps

---

## 6. Manual Partial Runs

For debugging, individual steps can be run separately:

### Sway Assignment Only

```python
from design.gs_12_iterate import classify_floors, get_all_frames_data, assign_sway_types

super_s, sub_s, _, _ = classify_floors(config)
frames = get_all_frames_data(SapModel)
assign_sway_types(SapModel, frames, super_s, sub_s)
```

### Single Analysis + Design Cycle

```python
from design.gs_12_iterate import run_analysis_and_design
run_analysis_and_design(SapModel, "ACI 318-19")
```

### Extract Results Without Resizing

```python
from design.gs_12_iterate import (
    get_all_frames_data, _classify_frames, classify_floors,
    extract_column_results, extract_beam_results
)

super_s, _, _, _ = classify_floors(config)
frames = get_all_frames_data(SapModel)
cols, beams = _classify_frames(frames, super_s, ["FB", "FSB", "FWB"])

col_results = extract_column_results(SapModel, cols)
beam_results = extract_beam_results(SapModel, beams)

# Print summary
for c in sorted(col_results, key=lambda x: -x["ratio"])[:10]:
    print(f"  {c['frame']} {c['prop']} @ {c['story']}: ratio={c['ratio']:.4f}")
```

### Enforce Column Constraints Manually

```python
from design.gs_12_iterate import _build_column_positions, enforce_column_constraints
from constants import build_strength_lookup

strength = build_strength_lookup(config["strength_map"], all_stories)
positions = _build_column_positions(col_results)
enforce_column_constraints(positions, strength, all_stories)
```

---

## 7. Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "Model has no frames" | gs_01~11 not run | Run `python run_all.py --config config.json` first |
| "USS01 combo not found" | Load combos not created | Run gs_10_loads step |
| RunAnalysis returns non-zero | Model errors (unstable, missing restraints) | Check model in ETABS GUI |
| StartDesign returns non-zero | Design code not set, no combos selected | Verify SetCode + SetComboStrength |
| No convergence after 5 iterations | Large initial mismatch or constraint conflicts | Increase `max_iterations` or review column constraints |
| Many oscillating members | Thresholds too tight | Widen gap between downsize/upsize thresholds |
| Substructure columns too large | Super column at boundary got enlarged | Expected — monotonic + boundary rules cascade |

### Adjusting Thresholds

Add to `model_config.json`:
```json
{
  "iteration": {
    "max_iterations": 8,
    "col_rebar_max": 0.035,
    "beam_rebar_max": 0.018
  }
}
```

---

## 8. Cross References

| Resource | Path |
|----------|------|
| Knowledge base (full concepts) | `skills/rc-design/references/rc-design-knowledge.md` |
| Implementation | `golden_scripts/design/gs_12_iterate.py` |
| Constants & thresholds | `golden_scripts/constants.py` |
| Config schema (`iteration` section) | `golden_scripts/config_schema.json` |
| Pure logic tests (39 tests) | `tests/test_iteration.py` |
| Modeling skill (upstream) | `skills/etabs-modeler/SKILL.md` |
