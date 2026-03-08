# /rc-iteration — RC Iteration Analysis-Design

Zero-argument command. Reads all info from the current ETABS model automatically.

## Pre-flight Checks

Before running, verify:
1. ETABS 22 is running with a model open
2. Model has columns and beams (frames exist)
3. Load combinations exist (USS01, BUSS01)
4. Model is saved

## Execution

```python
import sys, os
sys.path.insert(0, os.path.join(r"$ARGUMENTS" or ".", "golden_scripts"))
sys.path.insert(0, r"C:/Users/qazxs/OneDrive/圖片/桌面/WORKFLOW  DEV/claude-auto-build-etabs-model/golden_scripts")

from find_etabs import find_etabs
etabs, filename = find_etabs(run=False, backup=False)
SapModel = etabs.SapModel

from design import gs_12_iterate
gs_12_iterate.run(SapModel, config=None)
```

Run the above script. `config=None` triggers automatic extraction from the ETABS model:
- Stories from `SapModel.Story.GetStories_2()`
- Strength map inferred from existing frame section names (e.g. `C80X80C350` -> fc=350)
- All iteration thresholds use defaults from `constants.py`

The extraction happens **once** at the start; all 5 iterations + substructure phase reuse the same data.

## Post-run Report

After execution, report to the user:
- Convergence status (converged / max iterations reached)
- Number of iterations used
- Column and beam rebar ratio statistics (min/max/avg)
- Number of section changes applied
- Whether substructure columns needed upsizing
