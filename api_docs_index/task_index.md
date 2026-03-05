# ETABS API Task Index - "How Do I...?" Guide

> Practical guide mapping common user requests to specific ETABS v22 COM API calls.
> All examples use Python with comtypes. Return value 0 = success.
> For detailed method signatures, see `group_a_analysis.md` and `group_b_analysis.md`.
> For the lookup process, see `skills/etabs-api-lookup.md`.

---

## Table of Contents

1. [Connect to ETABS](#1-connect-to-etabs)
2. [Create a New Model](#2-create-a-new-model)
3. [Open / Save / Export a Model](#3-open--save--export-a-model)
4. [Define Materials](#4-define-materials)
5. [Define Frame Sections](#5-define-frame-sections)
6. [Define Area Sections](#6-define-area-sections)
7. [Define Stories](#7-define-stories)
8. [Define Grid Systems](#8-define-grid-systems)
9. [Add Frame Objects (Beams, Columns, Braces)](#9-add-frame-objects)
10. [Add Area Objects (Slabs, Walls)](#10-add-area-objects)
11. [Assign Supports / Restraints](#11-assign-supports--restraints)
12. [Define Load Patterns](#12-define-load-patterns)
13. [Assign Loads to Frames](#13-assign-loads-to-frames)
14. [Assign Loads to Areas](#14-assign-loads-to-areas)
15. [Assign Loads to Points](#15-assign-loads-to-points)
16. [Define Load Cases](#16-define-load-cases)
17. [Define Load Combinations](#17-define-load-combinations)
18. [Assign Diaphragms](#18-assign-diaphragms)
19. [Assign Constraints](#19-assign-constraints)
20. [Set Frame Property Modifiers](#20-set-frame-property-modifiers)
21. [Set End Releases (Pins)](#21-set-end-releases-pins)
22. [Define Response Spectrum Cases](#22-define-response-spectrum-cases)
23. [Define Modal Analysis Cases](#23-define-modal-analysis-cases)
24. [Set Seismic Parameters](#24-set-seismic-parameters)
25. [Run Analysis](#25-run-analysis)
26. [Extract Results - Story Drifts](#26-extract-results---story-drifts)
27. [Extract Results - Frame Forces](#27-extract-results---frame-forces)
28. [Extract Results - Joint Displacements](#28-extract-results---joint-displacements)
29. [Extract Results - Joint Reactions](#29-extract-results---joint-reactions)
30. [Extract Results - Base Reactions](#30-extract-results---base-reactions)
31. [Extract Results - Modal Information](#31-extract-results---modal-information)
32. [Extract Results - Area Forces](#32-extract-results---area-forces)
33. [Run Concrete Design](#33-run-concrete-design)
34. [Extract Concrete Design Results](#34-extract-concrete-design-results)
35. [Run Steel Design](#35-run-steel-design)
36. [Extract Steel Design Results](#36-extract-steel-design-results)
37. [Use Database Tables for Bulk Data](#37-use-database-tables-for-bulk-data)
38. [Define Groups](#38-define-groups)
39. [Define Pier and Spandrel Labels](#39-define-pier-and-spandrel-labels)
40. [Query Model Information](#40-query-model-information)

---

## 1. Connect to ETABS

**Interface**: cHelper, cOAPI

```python
import sys
sys.path.insert(0, r"C:\Users\User\Desktop\V22 AGENTIC MODEL\scripts")
from etabs_connection import attach_to_etabs
EtabsObject, SapModel = attach_to_etabs()
```

**Manual connection (without helper module):**
```python
import comtypes.client
helper = comtypes.client.CreateObject("ETABSv1.Helper")
helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)

# Attach to running instance
EtabsObject = helper.GetObject("CSI.ETABS.API.ETABSObject")
SapModel = EtabsObject.SapModel

# OR start new instance
EtabsObject = helper.CreateObject(r"C:\Program Files\Computers and Structures\ETABS 22\ETABS.exe")
SapModel = EtabsObject.SapModel
```

---

## 2. Create a New Model

**Interface**: cSapModel, cFile

```python
# Initialize with units (14 = kgf_cm_C)
ret = SapModel.InitializeNewModel(14)

# Option A: Blank model
ret = SapModel.File.NewBlank()

# Option B: Grid-only template
ret = SapModel.File.NewGridOnly(
    5,     # NumberStorys
    300,   # TypicalStoryHeight (cm)
    400,   # BottomStoryHeight (cm)
    4,     # NumberLines_X
    3,     # NumberLines_Y
    600,   # SpacingX (cm)
    600    # SpacingY (cm)
)

# Option C: Steel deck template
ret = SapModel.File.NewSteelDeck(5, 300, 400, 4, 3, 600, 600)
```

---

## 3. Open / Save / Export a Model

**Interface**: cFile

```python
# Open existing model
ret = SapModel.File.OpenFile(r"C:\path\to\model.EDB")

# Save current model (to current file)
ret = SapModel.File.Save()

# Save As (to new path)
ret = SapModel.File.Save(r"C:\path\to\new_model.EDB")

# Get current file path
path = SapModel.GetModelFilepath()
filename = SapModel.GetModelFilename(True)  # True = include path
```

---

## 4. Define Materials

**Interface**: cPropMaterial (`SapModel.PropMaterial`)

### Concrete
```python
# Add material
Name = ''
ret = SapModel.PropMaterial.AddMaterial(Name, 2, "User", "User", "User")
# MatType: 1=Steel, 2=Concrete, 5=Rebar

# Set isotropic properties: E (kgf/cm2), Poisson, Thermal expansion coeff
ret = SapModel.PropMaterial.SetMPIsotropic("Conc", 2.5e5, 0.2, 1e-5)

# Set weight per unit volume
ret = SapModel.PropMaterial.SetWeightAndMass("Conc", 1, 2.4e-3)  # 1=by weight

# Set concrete design properties
ret = SapModel.PropMaterial.SetOConcrete_1(
    "Conc",     # Name
    250,         # Fc (kgf/cm2)
    False,       # IsLightweight
    1,           # FcsFactor
    2,           # SSType (0=User,1=Parametric,2=Mander)
    1,           # SSHysType
    0.002,       # StrainAtFc
    0.005,       # StrainUltimate
    -0.1,        # FinalSlope
    0, 0         # FrictionAngle, DilatationalAngle
)
```

### Steel
```python
Name = ''
ret = SapModel.PropMaterial.AddMaterial(Name, 1, "User", "User", "User")
ret = SapModel.PropMaterial.SetMPIsotropic("Steel", 2.04e6, 0.3, 1.2e-5)
ret = SapModel.PropMaterial.SetOSteel_1(
    "Steel",    # Name
    2530,        # Fy (kgf/cm2)
    4080,        # Fu
    2530, 4080,  # EFy, EFu
    1, 1,        # SSType, SSHysType
    0.02,        # StrainAtHardening
    0.06,        # StrainAtMaxStress
    0.1,         # StrainAtRupture
    -0.1         # FinalSlope
)
```

### Rebar
```python
Name = ''
ret = SapModel.PropMaterial.AddMaterial(Name, 5, "User", "User", "User")
ret = SapModel.PropMaterial.SetMPIsotropic("Rebar", 2.04e6, 0.3, 1.2e-5)
ret = SapModel.PropMaterial.SetORebar_1(
    "Rebar",    # Name
    4200,        # Fy
    6300,        # Fu
    4200, 6300,  # EFy, EFu
    1, 1,        # SSType, SSHysType
    0.01, 0.09, 0.1,  # StrainHard, StrainMax, StrainRupture
    -0.1,        # FinalSlope
    False        # UseCaltransSSDefaults
)
```

---

## 5. Define Frame Sections

**Interface**: cPropFrame (`SapModel.PropFrame`)

```python
# Rectangular (T3=depth, T2=width)
ret = SapModel.PropFrame.SetRectangle("COL30x30", "Conc", 30, 30)
ret = SapModel.PropFrame.SetRectangle("BM25x50", "Conc", 50, 25)

# Circular (T3=diameter)
ret = SapModel.PropFrame.SetCircle("COL_D50", "Conc", 50)

# I-Section (T3=depth, T2=topFlangeW, Tf=topFlangeT, Tw=webT, T2b=botFlangeW, Tfb=botFlangeT)
ret = SapModel.PropFrame.SetISection("W14x30", "Steel", 35.3, 17.1, 0.99, 0.64, 17.1, 0.99)

# Pipe (T3=outerDia, TW=wallThickness)
ret = SapModel.PropFrame.SetPipe("PIPE_D30", "Steel", 30, 1.5)

# Tube/Box (T3=depth, T2=width, Tf=flangeThick, Tw=webThick)
ret = SapModel.PropFrame.SetTube("BOX20x10", "Steel", 20, 10, 1.2, 1.2)

# Tee section
ret = SapModel.PropFrame.SetTee("TEE", "Steel", 30, 20, 1.5, 1.0)

# Angle section
ret = SapModel.PropFrame.SetAngle("ANGLE", "Steel", 15, 10, 1.2, 1.2)

# Channel section
ret = SapModel.PropFrame.SetChannel("CHAN", "Steel", 25, 10, 1.5, 1.0)

# Concrete box (T3=depth, T2=width, Tf=flangeThick, Tw=webThick)
ret = SapModel.PropFrame.SetConcreteBox("CBOX", "Conc", 100, 60, 15, 15)

# General (user-defined section properties)
ret = SapModel.PropFrame.SetGeneral("GEN1", "Steel", 30, 20,
    Area, As2, As3, Torsion, I22, I33, S22, S33, Z22, Z33, R22, R33)

# Column rebar
ret = SapModel.PropFrame.SetRebarColumn("COL30x30", "Rebar", "Rebar",
    1,      # Pattern: 1=Rectangular, 2=Circular
    1,      # ConfineType: 1=Ties, 2=Spiral
    4,      # Cover (cm)
    8,      # NumberCornerBars
    3,      # NumberR3Bars (along depth)
    3,      # NumberR2Bars (along width)
    "#5",   # RebarSize
    "#3",   # TieSize
    10,     # TieSpacingLongit (cm)
    2,      # Number2DirTieBars
    2,      # Number3DirTieBars
    True    # ToBeDesigned
)

# Beam rebar
ret = SapModel.PropFrame.SetRebarBeam("BM25x50", "Rebar", "Rebar",
    4, 4,         # CoverTop, CoverBot (cm)
    3.96, 3.96,   # TopLeftArea, TopRightArea (cm2)
    3.96, 3.96    # BotLeftArea, BotRightArea (cm2)
)

# Import section from property file
ret = SapModel.PropFrame.ImportProp("W14x30", "Steel",
    r"C:\Program Files\Computers and Structures\ETABS 22\Sections\AISC14.xml",
    "W14X30")
```

---

## 6. Define Area Sections

**Interface**: cPropArea (`SapModel.PropArea`)

```python
# Slab
ret = SapModel.PropArea.SetSlab("Slab20", 0, 1, "Conc", 20)
# SlabType: 0=Slab, 1=Drop, 2=Stiff, 3=Ribbed, 4=Waffle, 5=Mat, 6=Footing
# ShellType: 0=ShellThin, 1=ShellThick, 2=Membrane, 3=Plate

# Wall
ret = SapModel.PropArea.SetWall("Wall20", 0, 1, "Conc", 20)
# WallPropType: 0=Specified

# Ribbed slab
ret = SapModel.PropArea.SetSlab("RibbedSlab", 3, 1, "Conc", 5)  # 3=Ribbed
ret = SapModel.PropArea.SetSlabRibbed("RibbedSlab",
    35,    # OverallDepth
    5,     # SlabThickness
    15,    # StemWidthTop
    10,    # StemWidthBot
    60,    # RibSpacing
    1      # RibDir (1=local-1, 2=local-2)
)

# Waffle slab
ret = SapModel.PropArea.SetSlab("WaffleSlab", 4, 1, "Conc", 5)  # 4=Waffle
ret = SapModel.PropArea.SetSlabWaffle("WaffleSlab",
    40,    # OverallDepth
    5,     # SlabThickness
    15, 10,  # StemWidthTop, StemWidthBot
    60, 60   # RibSpacingDir1, RibSpacingDir2
)

# Deck (filled composite)
ret = SapModel.PropArea.SetDeck("Deck1", 1, 1, "Conc", 15)
# Then set deck-specific properties...
```

---

## 7. Define Stories

**Interface**: cStory (`SapModel.Story`)

```python
# Set all stories at once (only when no objects exist in model)
NumStories = 5
StoryNames = ["Story1", "Story2", "Story3", "Story4", "Story5"]
StoryHeights = [400, 300, 300, 300, 300]  # cm
IsMasterStory = [True, False, False, False, False]
SimilarToStory = ["None", "Story1", "Story1", "Story1", "Story1"]
SpliceAbove = [False]*5
SpliceHeight = [0.0]*5
Color = [0]*5

ret = SapModel.Story.SetStories_2(
    0,              # BaseElevation
    NumStories,
    StoryNames,
    StoryHeights,
    IsMasterStory,
    SimilarToStory,
    SpliceAbove,
    SpliceHeight,
    Color
)

# Get all story data
BaseElev = 0.0
NumStories = 0
StoryNames = []
StoryElevs = []
StoryHeights = []
IsMaster = []
SimilarTo = []
SpliceAbove = []
SpliceHt = []
Color = []
ret = SapModel.Story.GetStories_2(BaseElev, NumStories, StoryNames, StoryElevs,
    StoryHeights, IsMaster, SimilarTo, SpliceAbove, SpliceHt, Color)

# Get individual story info
Elev = 0.0
ret = SapModel.Story.GetElevation("Story1", Elev)
Height = 0.0
ret = SapModel.Story.GetHeight("Story1", Height)

# Get story name list
NumNames = 0
Names = []
ret = SapModel.Story.GetNameList(NumNames, Names)
```

---

## 8. Define Grid Systems

**Interface**: cGridSys (`SapModel.GridSys`)

```python
# Get grid system data
ret = SapModel.GridSys.GetGridSys("Global", x, y, RZ)

# Set grid system origin and rotation
ret = SapModel.GridSys.SetGridSys("Global", 0, 0, 0)

# Use database tables for detailed grid line definition
# Table key: "Grid Lines"
```

---

## 9. Add Frame Objects

**Interface**: cFrameObj (`SapModel.FrameObj`)

```python
# Add column by coordinates (bottom to top)
Name = ''
ret = SapModel.FrameObj.AddByCoord(
    0, 0, 0,        # XI, YI, ZI (start/bottom)
    0, 0, 300,       # XJ, YJ, ZJ (end/top)
    Name,            # Returns assigned name
    "COL30x30"       # Section property name
)

# Add beam by coordinates
Name = ''
ret = SapModel.FrameObj.AddByCoord(
    0, 0, 300,       # Start point
    600, 0, 300,     # End point
    Name,
    "BM25x50"
)

# Add frame by existing point names
Name = ''
ret = SapModel.FrameObj.AddByPoint("1", "2", Name, "BM25x50")

# Get all frames (bulk query)
NumberNames = 0
MyName = []
PropName = []
StoryName = []
Pt1 = []
Pt2 = []
ret = SapModel.FrameObj.GetAllFrames(NumberNames, MyName, PropName, StoryName,
    Pt1, Pt2, Pt1X, Pt1Y, Pt1Z, Pt2X, Pt2Y, Pt2Z,
    Angle, Off1X, Off2X, Off1Y, Off2Y, Off1Z, Off2Z, CardPt)

# Get frame count by type
count = SapModel.FrameObj.Count("Column")   # "All", "Column", "Beam", "Brace"

# Get frame names on a specific story
NumNames = 0
Names = []
ret = SapModel.FrameObj.GetNameListOnStory("Story1", NumNames, Names)

# Change section assignment
ret = SapModel.FrameObj.SetSection("B1", "BM30x60")
```

---

## 10. Add Area Objects

**Interface**: cAreaObj (`SapModel.AreaObj`)

```python
# Add slab by coordinates (4-point)
X = [0, 600, 600, 0]
Y = [0, 0, 600, 600]
Z = [300, 300, 300, 300]
Name = ''
ret = SapModel.AreaObj.AddByCoord(4, X, Y, Z, Name, "Slab20")

# Add area by point names
PointNames = ["1", "2", "3", "4"]
Name = ''
ret = SapModel.AreaObj.AddByPoint(4, PointNames, Name, "Slab20")

# Set area as opening
ret = SapModel.AreaObj.SetOpening("F1", True)

# Change area property
ret = SapModel.AreaObj.SetProperty("F1", "Slab25")

# Get all areas (bulk)
ret = SapModel.AreaObj.GetAllAreas(NumberNames, MyName, DesignOrient,
    NumBoundPts, PtDelimiter, PtNames, PtX, PtY, PtZ)
```

---

## 11. Assign Supports / Restraints

**Interface**: cPointObj (`SapModel.PointObj`)

```python
# Fixed support [U1, U2, U3, R1, R2, R3]
fixed = [True, True, True, True, True, True]
ret = SapModel.PointObj.SetRestraint("1", fixed)

# Pinned support (translations fixed, rotations free)
pinned = [True, True, True, False, False, False]
ret = SapModel.PointObj.SetRestraint("1", pinned)

# Roller support (vertical + one horizontal)
roller = [True, False, True, False, False, False]
ret = SapModel.PointObj.SetRestraint("1", roller)

# Spring support [K1, K2, K3, KR1, KR2, KR3] (stiffness values)
springs = [1e6, 1e6, 1e8, 0, 0, 0]
ret = SapModel.PointObj.SetSpring("1", springs)

# Delete restraint
ret = SapModel.PointObj.DeleteRestraint("1")
```

---

## 12. Define Load Patterns

**Interface**: cLoadPatterns (`SapModel.LoadPatterns`)

```python
# Add load patterns (Name, Type, SelfWeightMultiplier)
ret = SapModel.LoadPatterns.Add("Dead", 1, 1)       # Dead with self-weight = 1
ret = SapModel.LoadPatterns.Add("SDL", 2, 0)         # SuperDead
ret = SapModel.LoadPatterns.Add("Live", 3, 0)        # Live
ret = SapModel.LoadPatterns.Add("RoofLive", 11, 0)   # Roof Live
ret = SapModel.LoadPatterns.Add("EQX", 5, 0)         # Earthquake X
ret = SapModel.LoadPatterns.Add("EQY", 5, 0)         # Earthquake Y
ret = SapModel.LoadPatterns.Add("WindX", 6, 0)        # Wind X
ret = SapModel.LoadPatterns.Add("WindY", 6, 0)        # Wind Y

# eLoadPatternType values:
# Dead=1, SuperDead=2, Live=3, ReduceLive=4, Quake=5, Wind=6, Snow=7,
# Other=8, Temperature=10, RoofLive=11

# Get pattern list
NumNames = 0
Names = []
ret = SapModel.LoadPatterns.GetNameList(NumNames, Names)

# Set self-weight multiplier
ret = SapModel.LoadPatterns.SetSelfWTMultiplier("Dead", 1.0)
```

---

## 13. Assign Loads to Frames

**Interface**: cFrameObj (`SapModel.FrameObj`)

```python
# Uniform distributed load
ret = SapModel.FrameObj.SetLoadDistributed(
    "B1",      # Frame name
    "Live",    # Load pattern
    1,         # MyType: 1=Force, 2=Moment
    11,        # Dir: 11=Projected Gravity
    0, 1,      # Dist1, Dist2 (relative: 0=start, 1=end)
    -500, -500,  # Val1, Val2 (kgf/cm for gravity)
    "Global",  # CSys
    True,      # RelDist (True=relative distances)
    True       # Replace existing loads
)

# Trapezoidal distributed load
ret = SapModel.FrameObj.SetLoadDistributed(
    "B1", "Live", 1, 11, 0, 1, -300, -600)

# Partial distributed load (from 20% to 80% of span)
ret = SapModel.FrameObj.SetLoadDistributed(
    "B1", "Live", 1, 11, 0.2, 0.8, -500, -500)

# Point load at midspan
ret = SapModel.FrameObj.SetLoadPoint(
    "B1",      # Frame name
    "Live",    # Load pattern
    1,         # MyType: 1=Force, 2=Moment
    11,        # Dir: 11=Projected Gravity
    0.5,       # Dist (relative distance from I-end)
    -1000,     # Value
    "Global",  # CSys
    True       # RelDist
)

# Temperature load
ret = SapModel.FrameObj.SetLoadTemperature("B1", "Temperature", 1, 30)
# MyType: 1=Temperature, 2=Gradient2, 3=Gradient3

# Direction codes:
# 1=local-1, 2=local-2, 3=local-3
# 4=Global-X, 5=Global-Y, 6=Global-Z
# 7=-Global-X, 8=-Global-Y, 9=-Global-Z
# 10=Gravity, 11=Projected Gravity
```

---

## 14. Assign Loads to Areas

**Interface**: cAreaObj (`SapModel.AreaObj`)

```python
# Uniform area load (pressure)
ret = SapModel.AreaObj.SetLoadUniform(
    "F1",      # Area name
    "Live",    # Load pattern
    -200,      # Value (kgf/cm2 for pressure, negative = downward)
    6,         # Dir: 6=Global-Z
    True,      # Replace
    "Global"   # CSys
)

# Wind pressure
ret = SapModel.AreaObj.SetLoadWindPressure(
    "W1",      # Area name
    "WindX",   # Load pattern
    1,         # MyType
    0.8        # Cp (pressure coefficient)
)

# Temperature load
ret = SapModel.AreaObj.SetLoadTemperature("F1", "Temperature", 1, 20)
```

---

## 15. Assign Loads to Points

**Interface**: cPointObj (`SapModel.PointObj`)

```python
# Point force [F1, F2, F3, M1, M2, M3]
forces = [0, 0, -10000, 0, 0, 0]  # 10000 kgf downward
ret = SapModel.PointObj.SetLoadForce("1", "Dead", forces, False, "Global")
# Replace=False means add to existing

# Point displacement (imposed settlement)
displ = [0, 0, -1.0, 0, 0, 0]  # 1 cm downward settlement
ret = SapModel.PointObj.SetLoadDispl("1", "Settlement", displ, False, "Global")
```

---

## 16. Define Load Cases

**Interface**: cLoadCases (`SapModel.LoadCases`) and sub-interfaces

### Static Linear Case
```python
# Create case
ret = SapModel.LoadCases.StaticLinear.SetCase("DL")

# Assign loads to case
ret = SapModel.LoadCases.StaticLinear.SetLoads("DL",
    1,              # NumberLoads
    ["Load"],       # LoadType: "Load" or "Accel"
    ["Dead"],       # LoadName (load pattern name)
    [1.0]           # ScaleFactor
)
```

### Eigen Modal Case
```python
ret = SapModel.LoadCases.ModalEigen.SetCase("Modal")
ret = SapModel.LoadCases.ModalEigen.SetNumberModes("Modal", 12, 1)  # max, min
ret = SapModel.LoadCases.ModalEigen.SetParameters("Modal", 0, 0, 1e-7, 1)
# Params: ShiftFreq, CutoffFreq, Tolerance, AllowAutoShift
```

### General
```python
# Get all load case names
NumNames = 0
Names = []
ret = SapModel.LoadCases.GetNameList(NumNames, Names)

# Delete a case
ret = SapModel.LoadCases.Delete("CaseName")
```

---

## 17. Define Load Combinations

**Interface**: cCombo (`SapModel.RespCombo`)

```python
# Add combo (ComboType: 0=Linear, 1=Envelope, 2=AbsAdd, 3=SRSS, 4=RangeAdd)
ret = SapModel.RespCombo.Add("1.4D+1.7L", 0)

# Add load cases to combo
ret = SapModel.RespCombo.SetCaseList("1.4D+1.7L", 0, "Dead", 1.4)   # 0=LoadCase
ret = SapModel.RespCombo.SetCaseList("1.4D+1.7L", 0, "Live", 1.7)

# Add another combo to a combo
ret = SapModel.RespCombo.SetCaseList("ENVELOPE", 1, "1.4D+1.7L", 1.0)  # 1=LoadCombo

# Add default design combos (DesignSteel, DesignConcrete, DesignAluminum, DesignColdFormed)
ret = SapModel.RespCombo.AddDesignDefaultCombos(False, True, False, False)

# Get combo list
NumNames = 0
Names = []
ret = SapModel.RespCombo.GetNameList(NumNames, Names)

# Get cases in a combo
NumItems = 0
CNameType = []
CName = []
SF = []
ret = SapModel.RespCombo.GetCaseList("1.4D+1.7L", NumItems, CNameType, CName, SF)
```

---

## 18. Assign Diaphragms

**Interface**: cDiaphragm (`SapModel.Diaphragm`), cAreaObj, cPointObj

```python
# Create diaphragm
ret = SapModel.Diaphragm.SetDiaphragm("D1", False)  # False = rigid

# Assign diaphragm to area object
ret = SapModel.AreaObj.SetDiaphragm("F1", "D1")

# Assign diaphragm to point
ret = SapModel.PointObj.SetDiaphragm("1", 3, "D1")
# Option 3 = constrained (diaphragm assigned)

# Get diaphragm list
NumNames = 0
Names = []
ret = SapModel.Diaphragm.GetNameList(NumNames, Names)
```

---

## 19. Assign Constraints

**Interface**: cConstraint (`SapModel.ConstraintDef`)

```python
# Note: For diaphragm constraints, use cDiaphragm instead (ConstraintDef.SetDiaphragm is deprecated)
# See section 18 above for diaphragm assignment
```

---

## 20. Set Frame Property Modifiers

**Interface**: cFrameObj (`SapModel.FrameObj`)

```python
# Property modifiers: [Area, As2, As3, Torsion, I22, I33, Mass, Weight]
# Example: cracked section (50% I)
mods = [1, 1, 1, 0.5, 0.5, 0.5, 1, 1]
ret = SapModel.FrameObj.SetModifiers("B1", mods)

# Column: 70% stiffness
col_mods = [1, 1, 1, 0.7, 0.7, 0.7, 1, 1]
ret = SapModel.FrameObj.SetModifiers("C1", col_mods)

# Apply to a group (eItemType: 0=Objects, 1=Group, 2=SelectedObjects)
ret = SapModel.FrameObj.SetModifiers("BeamGroup", mods, 1)  # 1=Group
```

---

## 21. Set End Releases (Pins)

**Interface**: cFrameObj (`SapModel.FrameObj`)

```python
# End releases: [P, V2, V3, T, M2, M3] for I-end and J-end
# True = released, False = fixed

# Pin at I-end (moment released)
II = [False, False, False, False, True, True]   # I-end: release M2 and M3
JJ = [False, False, False, False, False, False]  # J-end: all fixed
StartVal = [0.0]*6   # Partial fixity spring constants (0 = fully released)
EndVal = [0.0]*6

ret = SapModel.FrameObj.SetReleases("B1", II, JJ, StartVal, EndVal)

# Pin at both ends (truss member)
II = [False, False, False, False, True, True]
JJ = [False, False, False, False, True, True]
ret = SapModel.FrameObj.SetReleases("BR1", II, JJ, StartVal, EndVal)
```

---

## 22. Define Response Spectrum Cases

**Interface**: cCaseResponseSpectrum (`SapModel.LoadCases.ResponseSpectrum`)

```python
# Create response spectrum case
ret = SapModel.LoadCases.ResponseSpectrum.SetCase("RSX")

# Set spectrum function loads
# Args: Name, NumLoads, LoadName[], Func[], SF[], CSys[], Ang[]
ret = SapModel.LoadCases.ResponseSpectrum.SetLoads(
    "RSX",
    1,                    # NumberLoads
    ["U1"],              # LoadName (direction: U1, U2, U3)
    ["IS1893_2016"],     # Function name (must be defined)
    [9.81],              # Scale factor
    ["Global"],          # Coordinate system
    [0]                  # Angle
)

# Set modal case to use
ret = SapModel.LoadCases.ResponseSpectrum.SetModalCase("RSX", "Modal")

# Set eccentricity ratio
ret = SapModel.LoadCases.ResponseSpectrum.SetEccentricity("RSX", 0.05)

# Set damping (constant)
ret = SapModel.LoadCases.ResponseSpectrum.SetDampConstant("RSX", 0.05)

# Set modal combination (CQC)
# MyType: 1=CQC, 2=SRSS, 3=AbsSum, 4=GMC, 5=NRC10%, 6=NRCDoubleSum
ret = SapModel.LoadCases.ResponseSpectrum.SetModalComb("RSX", 1, 0, 0, 0)

# Set directional combination (SRSS)
# MyType: 1=SRSS, 2=ABS, 3=100/30/30, 4=100/40/40
ret = SapModel.LoadCases.ResponseSpectrum.SetDirComb("RSX", 1, 0)
```

---

## 23. Define Modal Analysis Cases

**Interface**: cCaseModalEigen (`SapModel.LoadCases.ModalEigen`)

```python
# Create modal case
ret = SapModel.LoadCases.ModalEigen.SetCase("Modal")

# Set number of modes (max, min)
ret = SapModel.LoadCases.ModalEigen.SetNumberModes("Modal", 12, 1)

# Set parameters (ShiftFreq, CutoffFreq, Tolerance, AllowAutoShift)
ret = SapModel.LoadCases.ModalEigen.SetParameters("Modal", 0, 0, 1e-7, 1)

# Set loads (mass source)
ret = SapModel.LoadCases.ModalEigen.SetLoads("Modal",
    2,                          # NumberLoads
    ["Accel", "Accel"],        # LoadType
    ["UX", "UY"],              # LoadName
    [0.99, 0.99],              # TargetParticipation
    [False, False]             # StaticCorrection
)

# Ritz modal case
ret = SapModel.LoadCases.ModalRitz.SetCase("ModalRitz")
ret = SapModel.LoadCases.ModalRitz.SetNumberModes("ModalRitz", 12, 1)
ret = SapModel.LoadCases.ModalRitz.SetLoads("ModalRitz",
    2,
    ["Accel", "Accel"],
    ["UX", "UY"],
    [20, 20],                  # RitzMaxCycles
    [0.99, 0.99]              # TargetParticipation
)
```

---

## 24. Set Seismic Parameters

**Interface**: cAutoSeismic (`SapModel.AutoSeismic`)

```python
# Set ASCE 7-16 seismic parameters
nDir = [True, False, False, False, False, False]  # X-direction only
ret = SapModel.AutoSeismic.SetASCE716(
    "EQX",     # Load pattern name
    nDir,      # Direction flags
    0.05,      # Eccentricity ratio
    1,         # PeriodFlag: 1=Approximate, 2=Program, 3=User
    5,         # CtType
    0,         # UserT (0 if not user-defined)
    False,     # UserZ (custom Z range)
    0, 0,      # TopZ, BottomZ
    8,         # R factor
    3,         # Omega0
    5.5,       # Cd
    1.0,       # Importance factor
    1.0,       # Ss
    0.4,       # S1
    8,         # TL (long period)
    4,         # SiteClass (1=A, 2=B, 3=C, 4=D, 5=E, 6=F)
    1.0,       # Fa
    1.5        # Fv
)

# Note: Also available via LoadPatterns.AutoSeismic property
# For code-specific parameters, check the HTML docs
```

---

## 25. Run Analysis

**Interface**: cAnalyze (`SapModel.Analyze`)

```python
# IMPORTANT: Save model before running analysis
ret = SapModel.File.Save(r"C:\path\to\model.EDB")

# Set active degrees of freedom [UX, UY, UZ, RX, RY, RZ]
DOF = [True, True, True, True, True, True]
ret = SapModel.Analyze.SetActiveDOF(DOF)

# Set all cases to run
ret = SapModel.Analyze.SetRunCaseFlag("", True, True)  # Name="", Run=True, All=True

# Or set specific cases
ret = SapModel.Analyze.SetRunCaseFlag("", False, True)  # Deselect all
ret = SapModel.Analyze.SetRunCaseFlag("Dead", True)     # Select Dead only
ret = SapModel.Analyze.SetRunCaseFlag("Modal", True)    # Select Modal

# Run analysis
ret = SapModel.Analyze.RunAnalysis()
# ret == 0 means success

# Delete results for a specific case
ret = SapModel.Analyze.DeleteResults("Dead")

# Check case status
NumItems = 0
CaseNames = []
Status = []
ret = SapModel.Analyze.GetCaseStatus(NumItems, CaseNames, Status)
# Status: 1=Not run, 2=Could not start, 3=Not finished, 4=Finished
```

---

## 26. Extract Results - Story Drifts

**Interface**: cAnalysisResults (`SapModel.Results`)

```python
# Configure output
ret = SapModel.Results.Setup.DeselectAllCasesAndCombosForOutput()
ret = SapModel.Results.Setup.SetCaseSelectedForOutput("EQX")

# Get story drifts
NumberResults = 0
Story = []
LoadCase = []
StepType = []
StepNum = []
Direction = []
Drift = []
Label = []
X = []
Y = []
Z = []
ret = SapModel.Results.StoryDrifts(NumberResults, Story, LoadCase, StepType,
    StepNum, Direction, Drift, Label, X, Y, Z)

# Alternative via database tables
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Story Drifts", [], "All", 0, [], 0, [])
```

---

## 27. Extract Results - Frame Forces

**Interface**: cAnalysisResults (`SapModel.Results`)

```python
# Configure output
ret = SapModel.Results.Setup.DeselectAllCasesAndCombosForOutput()
ret = SapModel.Results.Setup.SetCaseSelectedForOutput("Dead")

# Get frame forces for a specific frame
NumberResults = 0
Obj = []
ObjSta = []
Elm = []
ElmSta = []
LoadCase = []
StepType = []
StepNum = []
P = []     # Axial
V2 = []    # Shear (local-2)
V3 = []    # Shear (local-3)
T = []     # Torsion
M2 = []    # Moment (about local-2)
M3 = []    # Moment (about local-3)
ret = SapModel.Results.FrameForce("B1", 0, NumberResults, Obj, ObjSta, Elm, ElmSta,
    LoadCase, StepType, StepNum, P, V2, V3, T, M2, M3)
# eItemTypeElm: 0=ObjectElm, 1=Element, 2=GroupElm, 3=SelectionElm

# Alternative via database tables
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Element Forces - Frames", [], "All", 0, [], 0, [])
```

---

## 28. Extract Results - Joint Displacements

**Interface**: cAnalysisResults (`SapModel.Results`)

```python
ret = SapModel.Results.Setup.DeselectAllCasesAndCombosForOutput()
ret = SapModel.Results.Setup.SetCaseSelectedForOutput("Dead")

NumberResults = 0
Obj = []
Elm = []
LoadCase = []
StepType = []
StepNum = []
U1 = []   # Translation X
U2 = []   # Translation Y
U3 = []   # Translation Z
R1 = []   # Rotation about X
R2 = []   # Rotation about Y
R3 = []   # Rotation about Z
ret = SapModel.Results.JointDispl("1", 0, NumberResults, Obj, Elm,
    LoadCase, StepType, StepNum, U1, U2, U3, R1, R2, R3)
```

---

## 29. Extract Results - Joint Reactions

**Interface**: cAnalysisResults (`SapModel.Results`)

```python
ret = SapModel.Results.Setup.DeselectAllCasesAndCombosForOutput()
ret = SapModel.Results.Setup.SetCaseSelectedForOutput("Dead")

NumberResults = 0
Obj = []
Elm = []
LoadCase = []
StepType = []
StepNum = []
F1 = []   # Reaction force X
F2 = []   # Reaction force Y
F3 = []   # Reaction force Z
M1 = []   # Reaction moment about X
M2 = []   # Reaction moment about Y
M3 = []   # Reaction moment about Z
ret = SapModel.Results.JointReact("1", 0, NumberResults, Obj, Elm,
    LoadCase, StepType, StepNum, F1, F2, F3, M1, M2, M3)
```

---

## 30. Extract Results - Base Reactions

**Interface**: cAnalysisResults (`SapModel.Results`)

```python
ret = SapModel.Results.Setup.DeselectAllCasesAndCombosForOutput()
ret = SapModel.Results.Setup.SetCaseSelectedForOutput("Dead")

NumberResults = 0
LoadCase = []
StepType = []
StepNum = []
FX = []
FY = []
FZ = []
MX = []
MY = []
MZ = []
ret = SapModel.Results.BaseReact(NumberResults, LoadCase, StepType, StepNum,
    FX, FY, FZ, MX, MY, MZ, 0, 0, 0)
# Last 3 args: GX, GY, GZ = global coords of base reaction location
```

---

## 31. Extract Results - Modal Information

**Interface**: cAnalysisResults (`SapModel.Results`)

```python
# Modal periods and frequencies
ret = SapModel.Results.Setup.DeselectAllCasesAndCombosForOutput()
ret = SapModel.Results.Setup.SetCaseSelectedForOutput("Modal")

NumberResults = 0
LoadCase = []
StepType = []
StepNum = []
Period = []
Frequency = []
CircFreq = []
EigenValue = []
ret = SapModel.Results.ModalPeriod(NumberResults, LoadCase, StepType, StepNum,
    Period, Frequency, CircFreq, EigenValue)

# Modal participating mass ratios
NumberResults = 0
UX = []
UY = []
UZ = []
SumUX = []
SumUY = []
SumUZ = []
ret = SapModel.Results.ModalParticipatingMassRatios(NumberResults, LoadCase,
    StepType, StepNum, Period, UX, UY, UZ, SumUX, SumUY, SumUZ,
    RX, RY, RZ, SumRX, SumRY, SumRZ)

# Modal participation factors
ret = SapModel.Results.ModalParticipationFactors(NumberResults, LoadCase,
    StepType, StepNum, Period, UX, UY, UZ, RX, RY, RZ, ModalMass, ModalStiff)

# Mode shapes for a specific point
ret = SapModel.Results.ModeShape("1", 0, NumberResults, Obj, Elm,
    LoadCase, StepType, StepNum, U1, U2, U3, R1, R2, R3)
```

---

## 32. Extract Results - Area Forces

**Interface**: cAnalysisResults (`SapModel.Results`)

```python
# Area forces (shell elements)
ret = SapModel.Results.AreaForceShell("F1", 0, NumberResults, Obj, Elm, PointElm,
    LoadCase, StepType, StepNum,
    F11, F22, F12, FMax, FMin, FAngle, FVM,
    M11, M22, M12, MMax, MMin, MAngle,
    V13, V23, VMax, VAngle)

# Area stresses (shell elements)
ret = SapModel.Results.AreaStressShell("F1", 0, NumberResults, Obj, Elm, PointElm,
    LoadCase, StepType, StepNum,
    S11Top, S22Top, S12Top, SMaxTop, SMinTop, SAngleTop, SVMTop,
    S11Bot, S22Bot, S12Bot, SMaxBot, SMinBot, SAngleBot, SVMBot,
    S13Avg, S23Avg, SMaxAvg, SAngleAvg)
```

---

## 33. Run Concrete Design

**Interface**: cDesignConcrete (`SapModel.DesignConcrete`)

```python
# Set design code
ret = SapModel.DesignConcrete.SetCode("ACI 318-19")
# Other codes: "ACI 318-14", "Eurocode 2-2004", "Indian IS 456-2000", etc.

# Select combos for design
ret = SapModel.DesignConcrete.SetComboStrength("COMB1", True)

# Start design (analysis must be run first)
ret = SapModel.DesignConcrete.StartDesign()

# Check if results are available
available = SapModel.DesignConcrete.GetResultsAvailable()
```

---

## 34. Extract Concrete Design Results

**Interface**: cDesignConcrete (`SapModel.DesignConcrete`)

```python
# Beam design summary
NumberItems = 0
FrameName = []
Location = []
TopCombo = []
TopArea = []     # Required top rebar area
BotCombo = []
BotArea = []     # Required bottom rebar area
VmajorCombo = []
VmajorArea = []  # Required shear rebar area
TlCombo = []
TlArea = []
TTCombo = []
TTArea = []
ret = SapModel.DesignConcrete.GetSummaryResultsBeam(
    "B1", NumberItems, FrameName, Location,
    TopCombo, TopArea, BotCombo, BotArea,
    VmajorCombo, VmajorArea, TlCombo, TlArea, TTCombo, TTArea)

# Column design summary
NumberItems = 0
FrameName = []
MyOption = []
Location = []
PMMCombo = []
PMMArea = []    # Required rebar area
PMMRatio = []   # PMM interaction ratio
VMajorCombo = []
VmajorArea = []
VMinorCombo = []
VMinorArea = []
ret = SapModel.DesignConcrete.GetSummaryResultsColumn(
    "C1", NumberItems, FrameName, MyOption, Location,
    PMMCombo, PMMArea, PMMRatio,
    VMajorCombo, VmajorArea, VMinorCombo, VMinorArea)

# Alternative via database tables
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Concrete Beam Summary", [], "All", 0, [], 0, [])
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Concrete Column Summary", [], "All", 0, [], 0, [])
```

---

## 35. Run Steel Design

**Interface**: cDesignSteel (`SapModel.DesignSteel`)

```python
# Set design code
ret = SapModel.DesignSteel.SetCode("AISC 360-16")
# Other codes: "AISC 360-22", "Eurocode 3-2005", "Indian IS 800-2007", etc.

# Start design
ret = SapModel.DesignSteel.StartDesign()

# Check results
available = SapModel.DesignSteel.GetResultsAvailable()

# Verify all members passed
NumItems = 0
N1 = 0   # Number passed
N2 = 0   # Number NOT passed
Names = []
ret = SapModel.DesignSteel.VerifyPassed(NumItems, N1, N2, Names)
```

---

## 36. Extract Steel Design Results

**Interface**: cDesignSteel (`SapModel.DesignSteel`)

```python
# Summary results
NumberItems = 0
FrameName = []
Ratio = []      # Demand/capacity ratio
RatioType = []  # Type of governing ratio
Location = []   # Location along frame
ComboName = []  # Governing combo
ErrorSummary = []
WarningSummary = []
ret = SapModel.DesignSteel.GetSummaryResults(
    "B1", NumberItems, FrameName, Ratio, RatioType, Location,
    ComboName, ErrorSummary, WarningSummary)

# Detailed results (version 3)
ret = SapModel.DesignSteel.GetSummaryResults_3(
    "B1", NumberItems, FrameName, FrameType, DesignSect, Status,
    PMMCombo, PMMRatio, PRatio, MRatioMajor, MRatioMinor,
    VRatioMajor, VRatioMinor)

# Alternative via database tables
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Steel Frame Design Summary", [], "All", 0, [], 0, [])
```

---

## 37. Use Database Tables for Bulk Data

**Interface**: cDatabaseTables (`SapModel.DatabaseTables`)

### Read Data
```python
# Get table data as array
FieldKeyList = []      # Empty = all fields
GroupName = "All"
TableVersion = 0
FieldsKeysIncluded = []
NumberRecords = 0
TableData = []

ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Story Definitions",   # TableKey
    FieldKeyList,
    GroupName,
    TableVersion,
    FieldsKeysIncluded,
    NumberRecords,
    TableData
)

# Parse the flat array into rows
num_fields = len(FieldsKeysIncluded)
for i in range(NumberRecords):
    row = TableData[i * num_fields : (i + 1) * num_fields]
    print(dict(zip(FieldsKeysIncluded, row)))

# Export to CSV file
ret = SapModel.DatabaseTables.GetTableForDisplayCSVFile(
    "Story Definitions", [], "All", 0, r"C:\temp\stories.csv")

# Export to CSV string
CSVString = ''
ret = SapModel.DatabaseTables.GetTableForDisplayCSVString(
    "Story Definitions", [], "All", 0, CSVString)
```

### Write / Edit Data
```python
# 1. Get current data for editing
ret = SapModel.DatabaseTables.GetTableForEditingArray(
    TableKey, FieldKeyList, GroupName,
    TableVersion, FieldsKeysIncluded, NumberRecords, TableData)

# 2. Modify TableData as needed (same flat array format)

# 3. Stage the changes
ret = SapModel.DatabaseTables.SetTableForEditingArray(
    TableKey, TableVersion, FieldsKeysIncluded, NumberRecords, TableData)

# 4. Apply all staged edits
NumFatalErrors = 0
NumErrorMsgs = 0
NumWarnMsgs = 0
NumInfoMsgs = 0
ImportLog = ''
ret = SapModel.DatabaseTables.ApplyEditedTables(True, NumFatalErrors,
    NumErrorMsgs, NumWarnMsgs, NumInfoMsgs, ImportLog)

# 5. Check for errors
if NumFatalErrors > 0:
    print("ERRORS:", ImportLog)

# Cancel edits if needed
ret = SapModel.DatabaseTables.CancelTableEditing()
```

### Discover Available Tables
```python
NumTables = 0
TableKey = []
TableName = []
ImportType = []   # 0=NotImportable, 1=Importable, 2=ImportableAndBatchEditable
IsEmpty = []
ret = SapModel.DatabaseTables.GetAllTables(NumTables, TableKey, TableName, ImportType, IsEmpty)

# Get fields in a specific table
NumFields = 0
FieldKey = []
FieldName = []
Description = []
UnitsString = []
IsImportable = []
ret = SapModel.DatabaseTables.GetAllFieldsInTable("Story Definitions",
    TableVersion, NumFields, FieldKey, FieldName, Description, UnitsString, IsImportable)
```

### Common Table Keys Reference
| Table Key | Use For |
|-----------|---------|
| `"Story Definitions"` | Story names, heights, elevations |
| `"Frame Section Properties"` | All frame section data |
| `"Area Section Properties"` | All area section data |
| `"Material Properties"` | Material definitions |
| `"Load Pattern Definitions"` | Load pattern names and types |
| `"Load Case Definitions"` | Load case names and types |
| `"Grid Lines"` | Grid line definitions |
| `"Story Drifts"` | Story drift results |
| `"Story Forces"` | Story force results |
| `"Joint Displacements"` | Joint displacement results |
| `"Joint Reactions"` | Support reaction results |
| `"Element Forces - Frames"` | Frame element force results |
| `"Element Joint Forces - Frames"` | Frame joint force results |
| `"Modal Periods And Frequencies"` | Modal period/frequency data |
| `"Modal Participating Mass Ratios"` | Mass participation ratios |
| `"Concrete Column Summary"` | Concrete column design summary |
| `"Concrete Beam Summary"` | Concrete beam design summary |
| `"Concrete Column PMM Envelope"` | Column PMM envelope data |
| `"Steel Frame Design Summary"` | Steel design summary |
| `"Frame Assignments - Summary"` | Frame assignment overview |
| `"Area Assignments - Summary"` | Area assignment overview |

---

## 38. Define Groups

**Interface**: cGroup (`SapModel.GroupDef`)

```python
# Create a group
ret = SapModel.GroupDef.SetGroup("Beams")

# Add a frame to a group
ret = SapModel.FrameObj.SetGroupAssign("B1", "Beams")

# Add an area to a group
ret = SapModel.AreaObj.SetGroupAssign("F1", "Slabs")

# Remove from group
ret = SapModel.FrameObj.SetGroupAssign("B1", "Beams", True)  # True=Remove

# Get group assignments
NumItems = 0
ObjType = []    # 1=Point, 2=Frame, 3=Cable, 4=Tendon, 5=Area, 6=Solid, 7=Link
ObjName = []
ret = SapModel.GroupDef.GetAssignments("Beams", NumItems, ObjType, ObjName)

# Get group list
NumNames = 0
Names = []
ret = SapModel.GroupDef.GetNameList(NumNames, Names)
```

---

## 39. Define Pier and Spandrel Labels

**Interface**: cPierLabel (`SapModel.PierLabel`), cSpandrelLabel (`SapModel.SpandrelLabel`)

```python
# Create pier label
ret = SapModel.PierLabel.SetPier("P1")

# Assign pier to area (wall)
ret = SapModel.AreaObj.SetPier("W1", "P1")

# Assign pier to frame (column on wall)
ret = SapModel.FrameObj.SetPier("C1", "P1")

# Create spandrel label
ret = SapModel.SpandrelLabel.SetSpandrel("S1", True)  # True=multi-story

# Assign spandrel to area
ret = SapModel.AreaObj.SetSpandrel("W1", "S1")

# Get pier section properties
NumStories = 0
StoryNames = []
AxisAngle = []
NumAreaObj = []
ret = SapModel.PierLabel.GetSectionProperties("P1", NumStories, StoryNames,
    AxisAngle, NumAreaObj)
```

---

## 40. Query Model Information

**Interface**: cSapModel, various object interfaces

```python
# Get program version
Version = ''
VersionNumber = 0.0
ret = SapModel.GetVersion(Version, VersionNumber)

# Get model units
units = SapModel.GetPresentUnits()

# Get model lock status
locked = SapModel.GetModelIsLocked()

# Count objects
num_frames = SapModel.FrameObj.Count()
num_columns = SapModel.FrameObj.Count("Column")
num_beams = SapModel.FrameObj.Count("Beam")
num_areas = SapModel.AreaObj.Count()
num_points = SapModel.PointObj.Count()

# Get all point coordinates
NumNames = 0
Names = []
X = []
Y = []
Z = []
ret = SapModel.PointObj.GetAllPoints(NumNames, Names, X, Y, Z)

# Get all frame data
ret = SapModel.FrameObj.GetAllFrames(...)

# Get section property of a frame
PropName = ''
SAuto = ''
ret = SapModel.FrameObj.GetSection("B1", PropName, SAuto)

# Get frame type
MyType = ''
ret = SapModel.FrameObj.GetTypeOAPI("B1", MyType)
# Returns: "Column", "Beam", or "Brace"

# Get material list
NumNames = 0
Names = []
ret = SapModel.PropMaterial.GetNameList(NumNames, Names)

# Get frame section list
NumNames = 0
Names = []
ret = SapModel.PropFrame.GetNameList(NumNames, Names)
```

---

## Cross-References

- **CLAUDE.md**: Complete project instructions, inline API reference, access path mapping, key enumerations
- **group_a_analysis.md**: Detailed signatures for Analysis, Results, Load Cases, Design Codes (cAnalysisResults, cAnalyze, cAreaObj, cAutoSeismic, cCombo, cConstraint, cCaseModalEigen, cCaseResponseSpectrum, and all design code interfaces)
- **group_b_analysis.md**: Detailed signatures for Modeling, Properties, Database Tables (cSapModel, cFile, cFrameObj, cPointObj, cPropFrame, cPropMaterial, cPropArea, cDatabaseTables, cLoadPatterns, cLoadCases, cStory, cDesignConcrete, cDesignSteel, cDetailing, and more)
- **skills/etabs-api-lookup.md**: Step-by-step process for looking up any API detail from the raw HTML documentation
- **categories.json**: Maps interface names to functional categories
