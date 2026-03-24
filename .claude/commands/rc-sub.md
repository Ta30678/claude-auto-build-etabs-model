# /rc-sub — RC Substructure Check (BUSS)

Runs Phase 2 only: substructure column check with BUSS combos.
Reads current superstructure column sizes from ETABS as baseline.

## Important

Do NOT ask the user to confirm parameters, thresholds, or settings before running.
All iteration parameters use defaults from constants.py (or from config if provided).
Just execute the script directly.

## Execution

```python
import sys, os
sys.path.insert(0, os.path.join(r"$ARGUMENTS".strip().split()[0] if "$ARGUMENTS".strip() else ".", "golden_scripts"))
sys.path.insert(0, r"C:/Users/qazxs/OneDrive/圖片/桌面/WORKFLOW  DEV/claude-auto-build-etabs-model/golden_scripts")

from find_etabs import find_etabs
etabs, filename = find_etabs(run=False, backup=False)
SapModel = etabs.SapModel

import json
from rc_design import gs_12_iterate

args = "$ARGUMENTS".strip().split()
config_path = args[0] if args else None
config = None
if config_path and os.path.isfile(config_path):
    with open(config_path) as f:
        config = json.load(f)

gs_12_iterate.run(SapModel, config=config, phase="sub")
```

## Post-run Report

After execution, report:
- Number of substructure columns upsized
- Whether all sub columns >= super columns
- Final BUSS design run status

Also available: `/rc-super` for superstructure iteration, `/rc-iteration` for both phases.
