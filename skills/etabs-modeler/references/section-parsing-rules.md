# Section Parsing Rules

## Naming Convention (All sections include concrete grade suffix)

| Element Type | Format | Example | T3 (Depth) | T2 (Width) |
|---|---|---|---|---|
| Beam | `B{W}X{D}C{fc}` | B80X70C350 | 0.70 | 0.80 |
| Small Beam | `SB{W}X{D}C{fc}` | SB35X65C280 | 0.65 | 0.35 |
| Wall Beam | `WB{W}X{D}C{fc}` | WB50X70C350 | 0.70 | 0.50 |
| Foundation Beam | `FB{W}X{D}C{fc}` | FB90X230C420 | 2.30 | 0.90 |
| Column | `C{W}X{D}C{fc}` | C150X130C420 | 1.30 | 1.50 |
| Slab | `S{T}C{fc}` | S15C280 | - | - |
| Wall | `W{T}C{fc}` | W20C350 | - | - |
| Raft Slab | `FS{T}C{fc}` | FS100C350 | - | - |

**CRITICAL**: `PropFrame.SetRectangle(Name, Material, T3, T2)` — T3=Depth, T2=Width.
The naming format is `{PREFIX}{WIDTH}X{DEPTH}`, so parsing must swap: name gives W then D, but API wants D then W.

```
B55X80C350 → W=55, D=80 → SetRectangle("B55X80C350", "C350", 0.80, 0.55)
                                                              ^^^^  ^^^^
                                                              T3=D  T2=W
```

## Parsing Algorithm

```python
import re

def parse_frame_section(name):
    """Parse frame section name -> (prefix, width_cm, depth_cm, fc).
    Returns None if not a valid frame section name.
    """
    m = re.match(r'^(B|SB|WB|FB|FSB|FWB|C)(\d+)X(\d+)C(\d+)$', name)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    return None

def parse_area_section(name):
    """Parse area section name -> (prefix, thickness_cm, fc).
    Returns None if not a valid area section name.
    """
    m = re.match(r'^(S|W|FS)(\d+)C(\d+)$', name)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))
    return None
```

## Batch Expansion Algorithm

From each base section in plan-reader output, generate +-20cm / 5cm step / all concrete grades.

```python
CONCRETE_GRADES = [280, 315, 350, 420, 490]
EXPAND_RANGE = 20  # cm
EXPAND_STEP = 5    # cm

def expand_frame_sections(prefix, base_w, base_d):
    """Expand one base section into all size+grade combinations."""
    min_dim = 30 if prefix == 'C' else (25 if prefix in ('B','SB','WB') else 25)
    min_depth = 30 if prefix == 'C' else 40

    sections = []
    for W in range(max(base_w - EXPAND_RANGE, min_dim),
                   base_w + EXPAND_RANGE + 1, EXPAND_STEP):
        for D in range(max(base_d - EXPAND_RANGE, min_depth),
                       base_d + EXPAND_RANGE + 1, EXPAND_STEP):
            for fc in CONCRETE_GRADES:
                name = f"{prefix}{W}X{D}C{fc}"
                mat = f"C{fc}"
                # API: T3=depth_m, T2=width_m
                sections.append((name, mat, D / 100.0, W / 100.0))
    return sections

def expand_slab_sections(thickness_cm):
    """Expand slab section across all grades."""
    return [(f"S{thickness_cm}C{fc}", f"C{fc}", thickness_cm / 100.0, 2)
            for fc in CONCRETE_GRADES]
    # shell_type=2 (Membrane)

def expand_wall_sections(thickness_cm):
    """Expand wall section across all grades."""
    return [(f"W{thickness_cm}C{fc}", f"C{fc}", thickness_cm / 100.0, 2)
            for fc in CONCRETE_GRADES]
    # shell_type=2 (Membrane)

def expand_raft_sections(thickness_cm):
    """Expand raft slab section across all grades."""
    return [(f"FS{thickness_cm}C{fc}", f"C{fc}", thickness_cm / 100.0, 1)
            for fc in CONCRETE_GRADES]
    # shell_type=1 (ShellThick) — raft needs bending capacity
```

## Strength Assignment by Floor

The concrete grade for each element depends on its floor. Users provide a strength allocation table (Excel `強度分配.xlsx` or verbal).

```python
def read_strength_table(filepath):
    """Read strength allocation Excel file.
    Expected columns: 樓層, 柱, 梁, 牆, 版
    Returns: dict mapping (story, element_type) -> fc_grade (int)

    Example output:
    {('B3F','column'): 490, ('B3F','beam'): 420, ...
     ('2F','column'): 420, ('2F','beam'): 350, ...}
    """
    import pandas as pd
    df = pd.read_excel(filepath)
    strength_map = {}
    for _, row in df.iterrows():
        stories = parse_story_range(row['樓層'])
        for story in stories:
            strength_map[(story, 'column')] = int(row['柱'].replace('C',''))
            strength_map[(story, 'beam')]   = int(row['梁'].replace('C',''))
            strength_map[(story, 'wall')]   = int(row['牆'].replace('C',''))
            strength_map[(story, 'slab')]   = int(row['版'].replace('C',''))
    return strength_map

def parse_story_range(range_str):
    """Parse story range like 'B3F~1F' or '2F~7F' into list of story names."""
    # Implementation depends on project's story naming convention
    pass
```

## Section Name to Section Call Mapping

When creating elements, combine base section + floor strength:
```
Plan-reader output: "B55X80" at floor "5F"
Strength table: 5F beam → C350
→ Section name: "B55X80C350"
→ Already pre-created in Phase 2
```

## Column Bar Distribution Rules

For `PropFrame.SetRebarColumn`, NumR2 and NumR3 are proportional to width and depth:

```python
def calc_bar_distribution(width_cm, depth_cm):
    """Calculate NumR2 (along width) and NumR3 (along depth).
    Proportional to dimension ratio, min=2, max=6.
    """
    ratio = width_cm / depth_cm
    if abs(ratio - 1.0) < 0.1:
        return 3, 3  # square
    if ratio > 1:
        num_r3 = 2
        num_r2 = max(2, min(6, round(2 * ratio)))
    else:
        num_r2 = 2
        num_r3 = max(2, min(6, round(2 / ratio)))
    return num_r2, num_r3
```

| Column | W:D Ratio | NumR2 | NumR3 |
|--------|-----------|-------|-------|
| C90X90 | 1:1 | 3 | 3 |
| C60X90 | 2:3 | 2 | 3 |
| C150X130 | ~1.15:1 | 3 | 3 |
| C60X120 | 1:2 | 2 | 4 |
| C120X60 | 2:1 | 4 | 2 |
