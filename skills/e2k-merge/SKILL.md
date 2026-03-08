# E2K Merge Tool (合棟合併)

Merge multiple single-building e2k files into one unified model.
Handles unit conversion, label deduplication, and section merging.

## Prerequisites

- Base e2k file (containing substructure / shared basement)
- One or more building e2k files (containing superstructure)
- All files must share the same grid system and story definitions

## When to Use

- After per-building modifications need to be integrated
- Combining separately-modeled buildings into one analysis model
- Round-trip: split → modify → merge workflow

## Quick Start

```bash
python -m golden_scripts.tools.gs_merge \
    --base substructure.e2k \
    --buildings A=building_A.e2k B=building_B.e2k C=building_C.e2k \
    --output merged_all.e2k
```

## How It Works

1. **Read** base model (substructure) and all building models
2. **Detect units** in each file (`CONTROLS` section)
3. **Convert** building data to target units if needed
4. **Extract** superstructure elements from each building
5. **Rename** element labels with building prefix to avoid conflicts
6. **Deduplicate** materials and section definitions (same name = same def)
7. **Verify** column connectivity at substructure/superstructure interface
8. **Write** merged e2k

## Unit Conversion

The tool auto-detects units from each file's `CONTROLS` section and converts to
the target unit system (defaults to base model's units).

Supported units: `KGF-CM`, `KGF-M`, `TON-M`, `KN-M`

Converted quantities:
- Coordinates (length)
- Section dimensions (length)
- Section areas (length²)
- Moments of inertia (length⁴)

## Options

| Flag | Description |
|------|------------|
| `--base`, `-b` | Base e2k file (with substructure) |
| `--buildings`, `-B` | Building files as `PREFIX=PATH` pairs |
| `--output`, `-o` | Output e2k file path |
| `--target-units` | Target units: `FORCE LENGTH` (default: base units) |

## Verification Checklist

After merging, verify:
- [ ] Total element count = base elements + sum of building superstructure
- [ ] No duplicate element labels
- [ ] Section definitions are correctly deduplicated
- [ ] Column connectivity passes (matched > 90%)
- [ ] Output file can be imported into ETABS without errors

## Round-trip Test

```
original.e2k → split(DA) → A.e2k
             → split(DB) → B.e2k
A.e2k + B.e2k → merge → roundtrip.e2k
# roundtrip.e2k should match original.e2k in element counts
```

## Reference

- Glossary: `skills/structural-glossary/SKILL.md`
- Code: `golden_scripts/tools/gs_merge.py`
- Parser: `golden_scripts/tools/e2k_parser.py`
- Unit converter: `golden_scripts/tools/unit_converter.py`
