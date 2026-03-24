# /rc-iteration — RC Iteration Analysis-Design (Both Phases)

Runs both superstructure (USS) and substructure (BUSS) phases.
Zero-argument command. Reads all info from the current ETABS model automatically.

For running phases independently, use `/rc-super` (USS only) or `/rc-sub` (BUSS only).

## Important

Do NOT ask the user to confirm parameters, thresholds, or settings before running.
All iteration parameters use defaults from constants.py (or from config if provided).
Just execute the script directly.

## Execution

```python
import sys, os
sys.path.insert(0, os.path.join(r"$ARGUMENTS" or ".", "golden_scripts"))
sys.path.insert(0, r"C:/Users/qazxs/OneDrive/圖片/桌面/WORKFLOW  DEV/claude-auto-build-etabs-model/golden_scripts")

from find_etabs import find_etabs
etabs, filename = find_etabs(run=False, backup=False)
SapModel = etabs.SapModel

from rc_design import gs_12_iterate
gs_12_iterate.run(SapModel, config=None, phase="both")
```

Run the above script. `config=None` triggers automatic extraction from the ETABS model:
- Stories from `SapModel.Story.GetStories_2()`
- Strength map inferred from existing frame section names (e.g. `C80X80C350` -> fc=350)
- All iteration thresholds use defaults from `constants.py`

The extraction happens **once** at the start; all iterations + substructure phase reuse the same data.

## Output

Iteration results are saved to `rc_iterations/`:
- `iteration_N/ratio_report.json` — full ratio data for each iteration
- `iteration_N/summary.txt` — human-readable summary
- `iteration_N/plans/plan_{floor}.png` — plan view ratio plots (key floors only)
- `iteration_N/elevations/elev_{dir}_{grid}.png` — elevation ratio plots (Top-3 per direction)
- `final_summary.json` — convergence status and final statistics

## Post-run Report

After execution, report to the user:
- Convergence status (converged / max iterations reached)
- Number of iterations used
- Column and beam rebar ratio statistics (min/max/avg)
- Number of section changes applied (ratio vs constraint breakdown)
- Whether substructure columns needed upsizing
