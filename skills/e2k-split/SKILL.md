# E2K Split Tool (分棟拆分)

Split a multi-building ETABS e2k model into a single-building model while
preserving the shared substructure (共構下構).

## Prerequisites

- Source `.e2k` file (exported from ETABS or directly available)
- Know the building identifier (Diaphragm Name, e.g. `DA`, `DB`)

## When to Use

- Multi-building projects with shared basement (共構案)
- Need to modify one building's superstructure independently
- Before per-building design iteration

## Quick Start

```bash
# List available buildings in an e2k file
python -m golden_scripts.tools.gs_split --input all.e2k --list-buildings

# Split out building A
python -m golden_scripts.tools.gs_split \
    --input all.e2k \
    --building DA \
    --output building_A.e2k
```

## How It Works

1. **Parse** the source e2k file
2. **Discover buildings** by reading Diaphragm assignments on superstructure floors
3. **Classify stories** using `golden_scripts.constants.is_substructure_story()`
4. **Keep**: all substructure elements + target building's superstructure elements
5. **Clean up**: remove unused material/section definitions
6. **Write** the filtered e2k

## Building Identification Logic

- Superstructure floors: any story NOT matching `B*F`, `1F`, or `BASE`
- Each area object's `DIAPHRAGM` assignment on superstructure floors identifies its building
- All frame/area objects on substructure floors are kept regardless
- Lines (beams/columns) on superstructure floors are kept if assigned to target building stories

## Options

| Flag | Description |
|------|------------|
| `--input`, `-i` | Source e2k file path |
| `--building`, `-b` | Building diaphragm ID (e.g. DA) |
| `--output`, `-o` | Output e2k file path |
| `--keep-all-defs` | Don't clean up unused definitions |
| `--list-buildings` | List available buildings and exit |

## Verification Checklist

After splitting, verify:
- [ ] Substructure element count matches original
- [ ] Only target building's superstructure elements remain
- [ ] No orphan section/material definitions (unless `--keep-all-defs`)
- [ ] Output file can be imported into ETABS without errors

## Reference

- Glossary: `skills/structural-glossary/SKILL.md`
- Code: `golden_scripts/tools/gs_split.py`
- Parser: `golden_scripts/tools/e2k_parser.py`
