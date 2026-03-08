# /split — Split multi-building e2k model

Split a multi-building ETABS e2k model into a single-building model,
preserving the shared substructure (共構下構).

## Usage

```
/split [input.e2k] [building_id] [output.e2k]
```

## Arguments

- `input.e2k` — Source multi-building e2k file
- `building_id` — Diaphragm name identifying the building (e.g. DA, DB)
- `output.e2k` — Output file path (optional, defaults to `{building_id}.e2k`)

## Examples

```
/split all_buildings.e2k DA
/split C:/models/project.e2k DB C:/output/building_B.e2k
```

## What It Does

1. Reads the source e2k and discovers buildings by Diaphragm Name
2. Keeps all substructure (B*F, 1F, BASE) + target building's superstructure
3. Removes unused section/material definitions
4. Writes the filtered e2k

## Implementation

Uses `golden_scripts/tools/gs_split.py`. See `skills/e2k-split/SKILL.md` for details.
