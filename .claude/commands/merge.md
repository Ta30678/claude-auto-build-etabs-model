# /merge — Merge building e2k files

Merge multiple single-building ETABS e2k files into one unified model.
Handles unit conversion and section deduplication.

## Usage

```
/merge [base.e2k] [A=a.e2k] [B=b.e2k] ... [output.e2k]
```

## Arguments

- `base.e2k` — Base e2k file containing substructure
- `PREFIX=path.e2k` — Building files with prefix labels
- `output.e2k` — Output file path (last positional argument)

## Examples

```
/merge base.e2k A=building_A.e2k B=building_B.e2k merged.e2k
/merge sub.e2k A=A.e2k B=B.e2k C=C.e2k D=D.e2k all.e2k
```

## What It Does

1. Reads base model and all building models
2. Auto-detects and converts units to match base
3. Extracts superstructure from each building
4. Renames element labels with building prefix
5. Deduplicates section/material definitions
6. Verifies column connectivity at interface
7. Writes merged e2k

## Implementation

Uses `golden_scripts/tools/gs_merge.py`. See `skills/e2k-merge/SKILL.md` for details.
