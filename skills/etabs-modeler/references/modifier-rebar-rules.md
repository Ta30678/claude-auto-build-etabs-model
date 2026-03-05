# Modifier, Rebar, and Assignment Rules

## 1. Stiffness Modifiers

### Frame Modifiers (8 elements)
Array order: `[Area, As2, As3, Torsion, I22, I33, Mass, Weight]`

| Element | Area | As2 | As3 | Torsion | I22 | I33 | Mass | Weight |
|---------|------|-----|-----|---------|-----|-----|------|--------|
| Beam | 1 | 1 | 1 | 0.0001 | 0.7 | 0.7 | 0.8 | 0.8 |
| Column | 1 | 1 | 1 | 0.0001 | 0.7 | 0.7 | 0.95 | 0.95 |

```python
BEAM_MODS = [1, 1, 1, 0.0001, 0.7, 0.7, 0.8, 0.8]
COL_MODS  = [1, 1, 1, 0.0001, 0.7, 0.7, 0.95, 0.95]
SapModel.FrameObj.SetModifiers(frame_name, BEAM_MODS)
SapModel.FrameObj.SetModifiers(col_name, COL_MODS)
```

### Area Modifiers (10 elements)
Array order: `[f11, f22, f12, m11, m22, m12, v13, v23, Mass, Weight]`
- `f` = membrane (in-plane), `m` = bending (out-of-plane), `v` = shear

| Element | f11 | f22 | f12 | m11 | m22 | m12 | v13 | v23 | Mass | Wt |
|---------|-----|-----|-----|-----|-----|-----|-----|-----|------|----|
| Slab (Membrane) | 0.4 | 0.4 | 0.4 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wall (Membrane) | 0.4 | 0.4 | 0.4 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Raft (ShellThick) | 0.4 | 0.4 | 0.4 | 0.7 | 0.7 | 0.7 | 1 | 1 | 1 | 1 |

```python
SLAB_WALL_MODS = [0.4, 0.4, 0.4, 1, 1, 1, 1, 1, 1, 1]
RAFT_MODS      = [0.4, 0.4, 0.4, 0.7, 0.7, 0.7, 1, 1, 1, 1]
SapModel.PropArea.SetModifiers("S15C280", SLAB_WALL_MODS)
SapModel.PropArea.SetModifiers("FS100C350", RAFT_MODS)
```

**Note**: Modifiers are set on the **section property** (PropArea.SetModifiers), not on individual area objects. For frames, modifiers are set on **individual objects** (FrameObj.SetModifiers).

### Shell Type Rules
| Element | ShellType | Reason |
|---------|-----------|--------|
| Slab (S) | 2 = Membrane | No bending needed (rigid diaphragm) |
| Wall (W) | 2 = Membrane | In-plane stiffness only |
| Raft (FS) | 1 = ShellThick | Needs bending capacity for soil interaction |

---

## 2. Rebar Configuration

### Beam Rebar
```python
SapModel.PropFrame.SetRebarBeam(
    sec_name,      # Section property name
    "SD420",       # MatLongit
    "SD420",       # MatConfine
    cover_top,     # Top cover (m)
    cover_bot,     # Bottom cover (m)
    0, 0, 0, 0,   # TopLeftArea, TopRightArea, BotLeftArea, BotRightArea (0 = design mode)
    True           # ToBeDesigned
)
```

| Beam Type | Top Cover | Bottom Cover |
|-----------|-----------|--------------|
| Regular (B, SB, WB) | 0.09 m (9 cm) | 0.09 m (9 cm) |
| Foundation (FB, FSB, FWB) | 0.11 m (11 cm) | 0.15 m (15 cm) |

### Column Rebar
```python
SapModel.PropFrame.SetRebarColumn(
    sec_name,      # Section property name
    "SD420",       # MatLongit
    "SD420",       # MatConfine
    1,             # Pattern: 1 = Rectangular
    1,             # ConfineType: 1 = Ties
    0.07,          # Cover: 7 cm -> 0.07 m
    4,             # NumCornerBars: always 4
    num_r3,        # Bars along depth (T3 direction)
    num_r2,        # Bars along width (T2 direction)
    "#8",          # RebarSize (placeholder for design)
    "#4",          # TieSize
    0.15,          # TieSpacing: 15 cm -> 0.15 m
    2,             # Num2DirTie
    2,             # Num3DirTie
    True           # ToBeDesigned = True
)
```

Cover: **7 cm (0.07 m)** for all columns.

Bar distribution rule: NumR2:NumR3 proportional to Width:Depth. See `section-parsing-rules.md` for calculation.

---

## 3. Rigid Zone (End Length Offset)

All frame members get rigid zone factor = 0.75.

```python
# AutoOffset=True: ETABS calculates end lengths from connected members
# RZ=0.75: 75% of the calculated rigid zone is effective
SapModel.FrameObj.SetEndLengthOffset(frame_name, True, 0, 0, 0.75)
```

Apply to ALL frame objects (beams and columns).

---

## 4. End Releases

### Rule
A beam end is released (M2 + M3) if it is **not continuous** — meaning no column or other beam shares that endpoint.

### Release Array
`[P, V2, V3, T, M2, M3]` — True = released

```python
RELEASE = [False, False, False, False, True, True]   # Release M2+M3
NO_REL  = [False, False, False, False, False, False]  # No release
ZEROS   = [0.0] * 6  # Spring stiffness (zero = fully released)
```

### Continuity Check Logic
```python
def is_continuous(point_coord, all_frame_endpoints):
    """A point is continuous if another frame also has this coordinate."""
    return point_coord in all_frame_endpoints

# Apply:
# I-end not continuous, J-end continuous:
SapModel.FrameObj.SetReleases(beam, RELEASE, NO_REL, ZEROS, ZEROS)

# I-end continuous, J-end not continuous:
SapModel.FrameObj.SetReleases(beam, NO_REL, RELEASE, ZEROS, ZEROS)

# Both ends not continuous:
SapModel.FrameObj.SetReleases(beam, RELEASE, RELEASE, ZEROS, ZEROS)

# Both ends continuous: no release needed (default)
```

---

## 5. Diaphragm Assignment

### Rule
Assign rigid diaphragm **only to slab corner points**, NOT to all joints on the floor.

```python
# 1. Create diaphragm definition (one per story)
SapModel.Diaphragm.SetDiaphragm(f"D_{story}", False)  # False = rigid

# 2. For each slab area on this story, get its corner points
ret = SapModel.AreaObj.GetPoints(area_name, 0, [])
corner_points = ret[2]

# 3. Assign diaphragm to corner points only
SapModel.PointObj.SetDiaphragm(pt_name, 3, f"D_{story}")
# DiaphragmOption=3 means "constrained to diaphragm"
```

---

## 6. Foundation Support

### Base Restraints (NOT full fixed)
Only lock horizontal translations (UX, UY). Vertical handled by springs.

```python
restraint = [True, True, False, False, False, False]  # UX, UY only
SapModel.PointObj.SetRestraint(base_pt, restraint)
```

### Raft Slab Point Springs (Kv)
Vertical spring at each raft slab point.

```python
springs = [0, 0, Kv, 0, 0, 0]  # K3 = Kv
SapModel.PointObj.SetSpring(pt_name, springs)
```

### Edge Beam Line Springs (Kw)
Lateral spring on edge foundation beams.

```python
SapModel.PropLineSpring.SetLineSpringProp("EdgeSpring", 0, Kw, 0, 0, 0, 0)
SapModel.FrameObj.SetSpringAssignment(beam_name, "EdgeSpring")
```

---

## Quick Reference: What Gets Applied Where

| Property | Applied To | Method | Scope |
|----------|-----------|--------|-------|
| Frame modifier | Individual frame objects | `FrameObj.SetModifiers` | Per object |
| Area modifier | Area section properties | `PropArea.SetModifiers` | Per property |
| Beam rebar | Frame section properties | `PropFrame.SetRebarBeam` | Per property |
| Column rebar | Frame section properties | `PropFrame.SetRebarColumn` | Per property |
| Rigid zone | Individual frame objects | `FrameObj.SetEndLengthOffset` | Per object |
| End release | Individual beam objects | `FrameObj.SetReleases` | Per object |
| Diaphragm | Individual point objects | `PointObj.SetDiaphragm` | Per point |
| Restraint | Individual point objects | `PointObj.SetRestraint` | Per point |
| Point spring | Individual point objects | `PointObj.SetSpring` | Per point |
| Line spring | Individual frame objects | `FrameObj.SetSpringAssignment` | Per object |
