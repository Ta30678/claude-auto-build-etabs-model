# ETABS Agentic Model - Project Instructions

## Overview
This project uses Claude Code to control ETABS 22 via its COM API (Python + comtypes).
The workflow: Claude writes Python scripts -> executes via Bash -> reads output -> iterates.

---

## ETABS 操作方式（必須遵守）

### 連線方式：使用 etabs_api 套件（已安裝）
```python
from find_etabs import find_etabs
etabs, filename = find_etabs(run=False, backup=False)
```

### 禁止直接使用 comtypes
不要用 `comtypes.client.GetActiveObject()` 直接操作 SapModel。
一律透過 `etabs_api` 封裝操作，它已處理好型別轉換問題。

### 常用操作對照
```python
# 讀取資料表
df = etabs.database.read("表名", to_dataframe=True)

# 寫入資料表
etabs.database.write(table_key="表名", data=df)

# 地震力載重
ex, exn, exp, ey, eyn, eyp = etabs.load_patterns.get_seismic_load_patterns()

# 構件操作
etabs.frame_obj.方法名()
etabs.area.方法名()

# 樓層操作
etabs.story.方法名()

# 載重組合
etabs.load_combinations.方法名()

# 設計
etabs.design.方法名()

# 結果
etabs.results.方法名()

# 模型管理
etabs.lock_and_unlock_model()

# 刷新畫面
etabs.SapModel.View.RefreshView(0, False)
```

### 如果 etabs_api 沒有對應函數
可以透過 `etabs.SapModel` 存取底層 API：
```python
etabs.SapModel.Analyze.RunAnalysis()
etabs.SapModel.Results.StoryDrifts()
```
但 ByRef 參數不要手動傳值，讓 comtypes 自動處理。

## Environment
- **ETABS 22**: `C:/Program Files/Computers and Structures/ETABS 22/ETABS.exe`
- **API DLLs**: `ETABSv1.dll`, `CSiAPIv1.dll` (same folder)
- **Python**: 3.11.7 with `comtypes` 1.4.16, `numpy`, `pandas`
- **Units**: Default kgf-cm (code 14), unless user specifies otherwise

## Project Structure
```
V22 AGENTIC MODEL/
├── CLAUDE.md                          # This file - project instructions & API reference
├── ETABS REF/                         # Reference files (e2k, EDB)
├── api_docs/                          # Raw HTML API documentation (1693 files)
│   ├── CSI API ETABS v1.hhc           # Table of contents (searchable index)
│   └── html/                          # Individual method documentation files
├── api_docs_index/                    # Pre-built API index files
│   ├── categories.json                # Interface-to-category mapping
│   ├── full_toc.json                  # Complete table of contents from .hhc
│   ├── group_a_analysis.md            # Detailed: Analysis, Results, Load Cases, Design Codes
│   ├── group_b_analysis.md            # Detailed: Modeling, Properties, Database Tables
│   └── task_index.md                  # Task-oriented "How do I...?" guide
├── skills/
│   └── etabs-api-lookup.md            # Skill: how to look up API details from docs
├── scripts/
│   ├── etabs_connection.py            # Connection/attach functions
│   ├── etabs_utils.py                 # High-level API wrappers
│   ├── test_connection.py             # Connection test script
│   └── example_create_model.py        # Example: create 5-story RC building
└── models/                            # Output model files (.EDB)
```

---

## API Lookup Rule (MANDATORY)

When encountering ANY ETABS API method or operation you are not 100% certain about:

1. **FIRST** search the `api_docs/html/` directory for the relevant method documentation
2. Use Grep to search for method names in `api_docs/CSI API ETABS v1.hhc` or the HTML files
3. Read the actual HTML file to get exact parameter names, types, and descriptions
4. **NEVER** guess or assume parameter order, types, or return values
5. If unsure which interface contains a method, check `api_docs_index/categories.json` or `api_docs_index/full_toc.json`

**Search patterns:**
```
# Find a method by name in the TOC
Grep for "MethodName" in api_docs/CSI API ETABS v1.hhc

# Read method details from the HTML file listed in the .hhc entry
Read the .htm file path found in the .hhc entry

# Find by category
Check api_docs_index/categories.json for interface grouping

# Use the task index for common operations
Read api_docs_index/task_index.md
```

**Cross-reference files:**
- For a quick "how do I do X?" question -> `api_docs_index/task_index.md`
- For detailed method signatures of a specific interface -> `api_docs_index/group_a_analysis.md` or `group_b_analysis.md`
- For the lookup process itself -> `skills/etabs-api-lookup.md`

---

## How to Use ETABS API

### Connection Pattern (使用 etabs_api)
```python
from find_etabs import find_etabs
etabs, filename = find_etabs(run=False, backup=False)
# etabs.SapModel 即為 SapModel，可存取所有底層 API
```

> **舊方式（已棄用，禁止使用）：**
> ~~`from etabs_connection import attach_to_etabs`~~ — 會有型別轉換問題

### Complete Interface-to-SapModel Access Path Mapping

Below is the complete mapping of all 51 sub-interfaces accessible from `SapModel`:

#### Model Operations
| Access Path | Interface | Description |
|-------------|-----------|-------------|
| `SapModel` | cSapModel | Root object: units, model info, lock state |
| `SapModel.File` | cFile | Open, Save, New, Import, Export |
| `SapModel.View` | cView | RefreshView, RefreshWindow |
| `SapModel.SelectObj` | cSelect | Selection operations |
| `SapModel.Options` | cOptions | Program options |

#### Modeling Objects
| Access Path | Interface | Description |
|-------------|-----------|-------------|
| `SapModel.FrameObj` | cFrameObj | Frame objects: beams, columns, braces (74 methods) |
| `SapModel.AreaObj` | cAreaObj | Area objects: slabs, walls, decks (64 methods) |
| `SapModel.PointObj` | cPointObj | Point/joint objects: restraints, loads (58 methods) |
| `SapModel.LinkObj` | cLinkObj | Link objects (22 methods) |
| `SapModel.TendonObj` | cTendonObj | Tendon objects (17 methods) |

#### Element-Level Access (read-only, post-analysis)
| Access Path | Interface | Description |
|-------------|-----------|-------------|
| `SapModel.AreaElm` | cAreaElm | Area elements (meshed) |
| `SapModel.LineElm` | cLineElm | Line elements (meshed) |
| `SapModel.PointElm` | cPointElm | Point elements |
| `SapModel.LinkElm` | cLinkElm | Link elements |

#### Properties
| Access Path | Interface | Description |
|-------------|-----------|-------------|
| `SapModel.PropMaterial` | cPropMaterial | Material properties (46 methods) |
| `SapModel.PropFrame` | cPropFrame | Frame section properties (105 methods) |
| `SapModel.PropFrame.SDShape` | cPropFrameSDShape | Section Designer shapes |
| `SapModel.PropArea` | cPropArea | Area section properties (35 methods) |
| `SapModel.PropLink` | cPropLink | Link properties (39 methods) |
| `SapModel.PropRebar` | cPropRebar | Rebar properties (4 methods) |
| `SapModel.PropTendon` | cPropTendon | Tendon properties (6 methods) |
| `SapModel.PropPointSpring` | cPropPointSpring | Point spring properties |
| `SapModel.PropLineSpring` | cPropLineSpring | Line spring properties |
| `SapModel.PropAreaSpring` | cPropAreaSpring | Area spring properties |

#### Structure Definition
| Access Path | Interface | Description |
|-------------|-----------|-------------|
| `SapModel.Story` | cStory | Story definitions (17 methods) |
| `SapModel.Tower` | cTower | Tower definitions (8 methods) |
| `SapModel.GridSys` | cGridSys | Grid systems (12 methods) |
| `SapModel.Diaphragm` | cDiaphragm | Diaphragm management (5 methods) |
| `SapModel.PierLabel` | cPierLabel | Pier labels (6 methods) |
| `SapModel.SpandrelLabel` | cSpandrelLabel | Spandrel labels (6 methods) |
| `SapModel.ConstraintDef` | cConstraint | Joint constraints (4 methods) |

#### Load Definitions
| Access Path | Interface | Description |
|-------------|-----------|-------------|
| `SapModel.LoadPatterns` | cLoadPatterns | Load patterns: Dead, Live, EQ, Wind (11 methods) |
| `SapModel.LoadPatterns.AutoSeismic` | cAutoSeismic | Auto seismic parameters |
| `SapModel.LoadPatterns.AutoWind` | -- | Auto wind parameters |
| `SapModel.LoadCases` | cLoadCases | Load case management (7 methods, 12 sub-interfaces) |
| `SapModel.RespCombo` | cCombo | Load combinations (11 methods) |

#### Load Case Sub-Interfaces
| Access Path | Interface | Description |
|-------------|-----------|-------------|
| `SapModel.LoadCases.StaticLinear` | cCaseStaticLinear | Linear static (5 methods) |
| `SapModel.LoadCases.StaticNonlinear` | cCaseStaticNonlinear | Pushover (21 methods) |
| `SapModel.LoadCases.StaticNonlinearStaged` | cCaseStaticNonlinearStaged | Staged construction |
| `SapModel.LoadCases.ModalEigen` | cCaseModalEigen | Eigen modal analysis (9 methods) |
| `SapModel.LoadCases.ModalRitz` | cCaseModalRitz | Ritz modal analysis (7 methods) |
| `SapModel.LoadCases.ResponseSpectrum` | cCaseResponseSpectrum | Response spectrum (16 methods) |
| `SapModel.LoadCases.DirHistLinear` | cCaseDirectHistoryLinear | Direct linear time history |
| `SapModel.LoadCases.DirHistNonlinear` | cCaseDirectHistoryNonlinear | Direct NL time history |
| `SapModel.LoadCases.ModHistLinear` | cCaseModalHistoryLinear | Modal linear time history |
| `SapModel.LoadCases.ModHistNonlinear` | cCaseModalHistoryNonlinear | Modal NL time history |
| `SapModel.LoadCases.HyperStatic` | cCaseHyperStatic | Hyperstatic cases |

#### Analysis & Results
| Access Path | Interface | Description |
|-------------|-----------|-------------|
| `SapModel.Analyze` | cAnalyze | Run analysis, set DOF, solver options (21 methods) |
| `SapModel.Results` | cAnalysisResults | Extract results: forces, displacements, drifts (37 methods) |
| `SapModel.Results.Setup` | cAnalysisResultsSetup | Configure output cases/options (21 methods) |
| `SapModel.DatabaseTables` | cDatabaseTables | Bulk data read/write via tables (25 methods) |

#### Design
| Access Path | Interface | Description |
|-------------|-----------|-------------|
| `SapModel.DesignConcrete` | cDesignConcrete | Concrete frame design (14 methods) |
| `SapModel.DesignSteel` | cDesignSteel | Steel frame design (24 methods) |
| `SapModel.DesignCompositeBeam` | cDesignCompositeBeam | Composite beam design (22 methods) |
| `SapModel.DesignCompositeColumn` | cDesignCompositeColumn | Composite column design (22 methods) |
| `SapModel.DesignConcreteSlab` | cDesignConcreteSlab | Concrete slab design (4 methods) |
| `SapModel.DesignShearWall` | cDesignShearWall | Shear wall design (6 methods) |
| `SapModel.DesignResults` | cDesignResults | Design results access |
| `SapModel.Detailing` | cDetailing | Rebar detailing (49 methods) |

#### Editing & Utilities
| Access Path | Interface | Description |
|-------------|-----------|-------------|
| `SapModel.EditFrame` | cEditFrame | ChangeConnectivity |
| `SapModel.EditArea` | cEditArea | Area editing |
| `SapModel.EditGeneral` | cEditGeneral | Move selected objects |
| `SapModel.EditPoint` | cEditPoint | Point editing |
| `SapModel.GroupDef` | cGroup | Group management (8 methods) |
| `SapModel.Func` | cFunction | Function definitions (7 methods) |
| `SapModel.GDispl` | cGenDispl | Generalized displacements |
| `SapModel.PatternDef` | cPatternDef | Joint patterns |

---

### Key Method Signatures (Top ~50 Most-Used Methods)

All methods return `int` (0=success) unless otherwise noted. In Python COM, C# `ref` parameters become regular output parameters -- you pass initial values and the method fills them.

#### Model & File Operations
```python
# Initialize new model (14 = kgf_cm_C)
ret = SapModel.InitializeNewModel(14)

# Set/get present units
ret = SapModel.SetPresentUnits(14)    # eUnits: 1=lb_in, 5=kN_mm, 6=kN_m, 14=kgf_cm
units = SapModel.GetPresentUnits()

# File operations
ret = SapModel.File.NewBlank()
ret = SapModel.File.NewGridOnly(NumStories, TypHeight, BotHeight, NumX, NumY, SpacingX, SpacingY)
ret = SapModel.File.OpenFile(r"C:\path\to\model.EDB")
ret = SapModel.File.Save(r"C:\path\to\model.EDB")

# Refresh view
ret = SapModel.View.RefreshView(0, False)  # 0=all windows, False=no zoom-to-fit

# Lock/unlock model
ret = SapModel.SetModelIsLocked(False)
```

#### Material Properties
```python
# Add standard material
Name = ''
ret = SapModel.PropMaterial.AddMaterial(Name, 2, "User", "User", "User")
# MatType: 1=Steel, 2=Concrete, 5=Rebar

# Set isotropic properties (E, Poisson, ThermalCoeff)
ret = SapModel.PropMaterial.SetMPIsotropic("Conc", 2.5e5, 0.2, 1e-5)

# Set concrete design properties
ret = SapModel.PropMaterial.SetOConcrete_1("Conc", 250, False, 1, 2, 1, 0.002, 0.005, -0.1, 0, 0)
# Args: Name, Fc, IsLightweight, FcsFactor, SSType, SSHysType, StrainAtFc, StrainUlt, FinalSlope, FrictionAngle, DilatAngle

# Set steel design properties
ret = SapModel.PropMaterial.SetOSteel_1("Steel", 2530, 4080, 2530, 4080, 1, 1, 0.02, 0.06, 0.1, -0.1)
# Args: Name, Fy, Fu, EFy, EFu, SSType, SSHysType, StrainHard, StrainMaxStress, StrainRupture, FinalSlope

# Set weight and mass
ret = SapModel.PropMaterial.SetWeightAndMass("Conc", 1, 2.4e-3)  # 1=by weight per vol
```

#### Frame Section Properties
```python
# Rectangular section (T3=depth, T2=width)
ret = SapModel.PropFrame.SetRectangle("COL30x30", "Conc", 30, 30)
ret = SapModel.PropFrame.SetRectangle("BM25x50", "Conc", 50, 25)

# Circular section (T3=diameter)
ret = SapModel.PropFrame.SetCircle("COL_D50", "Conc", 50)

# I-Section (T3=depth, T2=topFlangeW, Tf=topFlangeT, Tw=webT, T2b=botFlangeW, Tfb=botFlangeT)
ret = SapModel.PropFrame.SetISection("W14x30", "Steel", 35.3, 17.1, 0.99, 0.64, 17.1, 0.99)

# Pipe (T3=outerDia, TW=wallThick)
ret = SapModel.PropFrame.SetPipe("PIPE_D30", "Steel", 30, 1.5)

# Tube/box (T3=depth, T2=width, Tf=flangeT, Tw=webT)
ret = SapModel.PropFrame.SetTube("BOX20x10", "Steel", 20, 10, 1.2, 1.2)

# Column rebar layout
ret = SapModel.PropFrame.SetRebarColumn("COL30x30", "Rebar", "Rebar", 1, 1, 4, 8, 3, 3, "#5", "#3", 10, 2, 2, True)
# Args: Name, MatLong, MatConfine, Pattern(1=rect), ConfineType(1=ties), Cover, NumCornerBars, NumR3, NumR2, BarSize, TieSize, TieSpacing, Num2Dir, Num3Dir, ToBeDesigned
```

#### Area Section Properties
```python
# Slab section
ret = SapModel.PropArea.SetSlab("Slab20", 0, 1, "Conc", 20)
# Args: Name, SlabType(0=Slab), ShellType(1=ShellThick), MatProp, Thickness

# Wall section
ret = SapModel.PropArea.SetWall("Wall20", 0, 1, "Conc", 20)
# Args: Name, WallPropType, ShellType, MatProp, Thickness
```

#### Story Definitions
```python
# Set stories (only when no objects exist)
ret = SapModel.Story.SetStories_2(BaseElev, NumStories, StoryNames, StoryHeights,
    IsMasterStory, SimilarToStory, SpliceAbove, SpliceHeight, Color)

# Get all story data
ret = SapModel.Story.GetStories_2(BaseElev, NumStories, StoryNames, StoryElevs,
    StoryHeights, IsMasterStory, SimilarToStory, SpliceAbove, SpliceHeight, Color)
```

#### Frame Objects
```python
# Add frame by coordinates (XI,YI,ZI -> XJ,YJ,ZJ)
Name = ''
ret = SapModel.FrameObj.AddByCoord(0, 0, 0, 0, 0, 300, Name, "COL30x30")

# Add frame between existing points
Name = ''
ret = SapModel.FrameObj.AddByPoint("1", "2", Name, "BM25x50")

# Assign distributed load (Name, LoadPat, Type, Dir, Dist1, Dist2, Val1, Val2)
ret = SapModel.FrameObj.SetLoadDistributed("B1", "Live", 1, 11, 0, 1, -500, -500)
# Type: 1=Force, 2=Moment. Dir: 11=Projected Gravity

# Assign point load
ret = SapModel.FrameObj.SetLoadPoint("B1", "Live", 1, 11, 0.5, -1000)

# Set end releases (pin connections)
II = [False, False, False, False, False, False]  # I-end: [P, V2, V3, T, M2, M3]
JJ = [False, False, False, False, False, True]   # J-end: release M3
StartVal = [0]*6
EndVal = [0]*6
ret = SapModel.FrameObj.SetReleases("B1", II, JJ, StartVal, EndVal)

# Set property modifiers [Area, As2, As3, Torsion, I22, I33, Mass, Weight]
mods = [1, 1, 1, 1, 0.5, 0.5, 1, 1]  # 50% cracked I
ret = SapModel.FrameObj.SetModifiers("B1", mods)

# Get all frames at once (bulk query)
ret = SapModel.FrameObj.GetAllFrames(NumberNames, MyName, PropName, StoryName,
    PointName1, PointName2, Pt1X, Pt1Y, Pt1Z, Pt2X, Pt2Y, Pt2Z,
    Angle, Off1X, Off2X, Off1Y, Off2Y, Off1Z, Off2Z, CardinalPt)
```

#### Area Objects
```python
# Add area by coordinates
X = [0, 600, 600, 0]
Y = [0, 0, 600, 600]
Z = [300, 300, 300, 300]
Name = ''
ret = SapModel.AreaObj.AddByCoord(4, X, Y, Z, Name, "Slab20")

# Assign uniform load (Name, LoadPat, Value, Dir)
ret = SapModel.AreaObj.SetLoadUniform("F1", "Live", -200, 6)  # Dir: 6=Global-Z

# Assign diaphragm
ret = SapModel.AreaObj.SetDiaphragm("F1", "D1")

# Assign pier/spandrel
ret = SapModel.AreaObj.SetPier("W1", "P1")
ret = SapModel.AreaObj.SetSpandrel("W1", "S1")
```

#### Point Objects (Joints)
```python
# Set restraints (fixed support) [U1, U2, U3, R1, R2, R3]
restraint = [True, True, True, True, True, True]  # fixed
ret = SapModel.PointObj.SetRestraint("1", restraint)

# Apply point load [F1, F2, F3, M1, M2, M3]
forces = [0, 0, -1000, 0, 0, 0]
ret = SapModel.PointObj.SetLoadForce("1", "Dead", forces)

# Set spring stiffnesses [K1, K2, K3, KR1, KR2, KR3]
springs = [1e6, 1e6, 1e6, 0, 0, 0]
ret = SapModel.PointObj.SetSpring("1", springs)

# Assign diaphragm to joint
ret = SapModel.PointObj.SetDiaphragm("1", 3, "D1")  # 3=constrained
```

#### Load Patterns
```python
# Add load pattern (Name, Type, SelfWeightMultiplier)
ret = SapModel.LoadPatterns.Add("Dead", 1, 1)    # Dead with SW=1
ret = SapModel.LoadPatterns.Add("Live", 3, 0)    # Live
ret = SapModel.LoadPatterns.Add("EQX", 5, 0)     # Seismic
ret = SapModel.LoadPatterns.Add("Wind", 6, 0)    # Wind
# eLoadPatternType: Dead=1, SuperDead=2, Live=3, Quake=5, Wind=6, Snow=7
```

#### Load Combinations
```python
# Add combination (ComboType: 0=Linear, 1=Envelope)
ret = SapModel.RespCombo.Add("COMB1", 0)

# Add cases to combination (Name, CNameType, CaseName, ScaleFactor)
ret = SapModel.RespCombo.SetCaseList("COMB1", 0, "Dead", 1.4)    # 0=LoadCase
ret = SapModel.RespCombo.SetCaseList("COMB1", 0, "Live", 1.7)

# Add default design combos
ret = SapModel.RespCombo.AddDesignDefaultCombos(False, True, False, False)  # concrete design
```

#### Analysis
```python
# Set active DOF [UX, UY, UZ, RX, RY, RZ]
DOF = [True, True, True, True, True, True]
ret = SapModel.Analyze.SetActiveDOF(DOF)

# Set run flags (run all cases)
ret = SapModel.Analyze.SetRunCaseFlag("", True, True)

# Save model before analysis (required)
ret = SapModel.File.Save(r"C:\path\to\model.EDB")

# Run analysis
ret = SapModel.Analyze.RunAnalysis()
```

#### Results Extraction
```python
# Configure output selection
ret = SapModel.Results.Setup.DeselectAllCasesAndCombosForOutput()
ret = SapModel.Results.Setup.SetCaseSelectedForOutput("Dead")
ret = SapModel.Results.Setup.SetComboSelectedForOutput("COMB1")

# Frame forces
ret = SapModel.Results.FrameForce(Name, 0, NumberResults, Obj, ObjSta, Elm, ElmSta,
    LoadCase, StepType, StepNum, P, V2, V3, T, M2, M3)
# eItemTypeElm: 0=ObjectElm, 1=Element, 2=GroupElm, 3=SelectionElm

# Joint displacements
ret = SapModel.Results.JointDispl(Name, 0, NumberResults, Obj, Elm,
    LoadCase, StepType, StepNum, U1, U2, U3, R1, R2, R3)

# Joint reactions
ret = SapModel.Results.JointReact(Name, 0, NumberResults, Obj, Elm,
    LoadCase, StepType, StepNum, F1, F2, F3, M1, M2, M3)

# Base reactions
ret = SapModel.Results.BaseReact(NumberResults, LoadCase, StepType, StepNum,
    FX, FY, FZ, MX, MY, MZ, 0, 0, 0)

# Story drifts
ret = SapModel.Results.StoryDrifts(NumberResults, Story, LoadCase, StepType, StepNum,
    Direction, Drift, Label, X, Y, Z)

# Modal periods
ret = SapModel.Results.ModalPeriod(NumberResults, LoadCase, StepType, StepNum,
    Period, Frequency, CircFreq, EigenValue)

# Modal participating mass ratios
ret = SapModel.Results.ModalParticipatingMassRatios(NumberResults, LoadCase, StepType, StepNum,
    Period, UX, UY, UZ, SumUX, SumUY, SumUZ, RX, RY, RZ, SumRX, SumRY, SumRZ)
```

#### Design
```python
# Concrete design
ret = SapModel.DesignConcrete.SetCode("ACI 318-19")
ret = SapModel.DesignConcrete.StartDesign()
available = SapModel.DesignConcrete.GetResultsAvailable()

# Beam design summary
ret = SapModel.DesignConcrete.GetSummaryResultsBeam(Name, NumberItems, FrameName,
    Location, TopCombo, TopArea, BotCombo, BotArea, VmajorCombo, VmajorArea,
    TlCombo, TlArea, TTCombo, TTArea)

# Column design summary
ret = SapModel.DesignConcrete.GetSummaryResultsColumn(Name, NumberItems, FrameName,
    MyOption, Location, PMMCombo, PMMArea, PMMRatio, VMajorCombo, VmajorArea,
    VMinorCombo, VMinorArea)

# Steel design
ret = SapModel.DesignSteel.SetCode("AISC 360-16")
ret = SapModel.DesignSteel.StartDesign()
ret = SapModel.DesignSteel.GetSummaryResults(Name, NumberItems, FrameName, Ratio,
    RatioType, Location, ComboName, ErrorSummary, WarningSummary)
```

#### Modal Analysis Setup
```python
# Set up Eigen modal case
ret = SapModel.LoadCases.ModalEigen.SetCase("Modal")
ret = SapModel.LoadCases.ModalEigen.SetNumberModes("Modal", 12, 1)  # max=12, min=1
ret = SapModel.LoadCases.ModalEigen.SetParameters("Modal", 0, 0, 1e-7, 1)
```

#### Response Spectrum Setup
```python
# Create response spectrum case
ret = SapModel.LoadCases.ResponseSpectrum.SetCase("RSX")
# Set loads: Name, NumLoads, LoadName[], Func[], SF[], CSys[], Ang[]
ret = SapModel.LoadCases.ResponseSpectrum.SetLoads("RSX", 1, ["U1"],
    ["FuncRS"], [9.81], ["Global"], [0])
ret = SapModel.LoadCases.ResponseSpectrum.SetModalCase("RSX", "Modal")
ret = SapModel.LoadCases.ResponseSpectrum.SetEccentricity("RSX", 0.05)
```

---

### Database Tables (Recommended for Bulk Data)

Use `SapModel.DatabaseTables.GetTableForDisplayArray()` for bulk data extraction. This is often more reliable and efficient than individual API calls.

**Usage Pattern:**
```python
FieldKeyList = []
GroupName = "All"
TableVersion = 0
FieldsKeysIncluded = []
NumberRecords = 0
TableData = []
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Story Definitions", FieldKeyList, GroupName,
    TableVersion, FieldsKeysIncluded, NumberRecords, TableData
)
# TableData is a flat 1D array: reshape as [NumberRecords x len(FieldsKeysIncluded)]
num_fields = len(FieldsKeysIncluded)
for i in range(NumberRecords):
    row = TableData[i*num_fields : (i+1)*num_fields]
```

**Table Editing Workflow:**
```python
# 1. Get current data
ret = SapModel.DatabaseTables.GetTableForEditingArray(TableKey, FieldKeyList, GroupName,
    TableVersion, FieldsKeysIncluded, NumberRecords, TableData)
# 2. Modify TableData as needed
# 3. Stage changes
ret = SapModel.DatabaseTables.SetTableForEditingArray(TableKey, TableVersion,
    FieldsKeysIncluded, NumberRecords, TableData)
# 4. Apply all staged edits
ret = SapModel.DatabaseTables.ApplyEditedTables(True, NumFatalErrors, NumErrorMsgs,
    NumWarnMsgs, NumInfoMsgs, ImportLog)
```

**Common Table Keys:**

| Category | Table Key |
|----------|-----------|
| **Model Definition** | |
| Stories | `"Story Definitions"` |
| Frame Sections | `"Frame Section Properties"` |
| Area Sections | `"Area Section Properties"` |
| Materials | `"Material Properties"` |
| Load Patterns | `"Load Pattern Definitions"` |
| Load Cases | `"Load Case Definitions"` |
| Load Combos | `"Load Combination Definitions"` |
| Grid Lines | `"Grid Lines"` |
| **Assignments** | |
| Frame Assignments | `"Frame Assignments - Summary"` |
| Area Assignments | `"Area Assignments - Summary"` |
| **Analysis Results** | |
| Story Drifts | `"Story Drifts"` |
| Story Forces | `"Story Forces"` |
| Joint Displacements | `"Joint Displacements"` |
| Joint Reactions | `"Joint Reactions"` |
| Frame Forces | `"Element Forces - Frames"` |
| Element Joint Forces | `"Element Joint Forces - Frames"` |
| Modal Periods | `"Modal Periods And Frequencies"` |
| Modal Participation | `"Modal Participating Mass Ratios"` |
| **Design Results** | |
| Concrete Column | `"Concrete Column Summary"` |
| Concrete Beam | `"Concrete Beam Summary"` |
| Concrete Column PMM | `"Concrete Column PMM Envelope"` |
| Steel Frame | `"Steel Frame Design Summary"` |

Use `SapModel.DatabaseTables.GetAllTables()` to discover all available table names.

---

### Key Enumerations

**eUnits (unit codes):**
1=lb_in_F, 2=lb_ft_F, 3=kip_in_F, 4=kip_ft_F, 5=kN_mm_C, 6=kN_m_C, 7=kgf_mm_C, 8=kgf_m_C, 9=N_mm_C, 10=N_m_C, 11=Ton_mm_C, 12=Ton_m_C, 13=kN_cm_C, 14=kgf_cm_C, 15=N_cm_C, 16=Ton_cm_C

**eLoadPatternType:**
Dead=1, SuperDead=2, Live=3, ReduceLive=4, Quake=5, Wind=6, Snow=7, Other=8, Temperature=10

**eMatType (material type):**
1=Steel, 2=Concrete, 3=NoDesign, 4=Tendon, 5=Rebar, 6=Aluminum, 7=ColdFormed, 8=Masonry

**eItemTypeElm (for result methods):**
0=ObjectElm, 1=Element, 2=GroupElm, 3=SelectionElm

**eItemType (for assignment methods):**
0=Objects, 1=Group, 2=SelectedObjects

**Load direction codes (for SetLoadDistributed/SetLoadUniform):**
1=local-1, 2=local-2, 3=local-3, 4=Global-X, 5=Global-Y, 6=Global-Z, 7=-Global-X, 8=-Global-Y, 9=-Global-Z, 10=Gravity (proj), 11=Projected Gravity

---

### Python COM-Specific Notes

1. **ref parameters**: C# `ref` parameters become regular parameters in Python COM. Pass initial values (empty string `''`, zero `0`, empty list `[]`) and the method fills them.
2. **Arrays**: Pass Python lists where C# expects arrays. COM returns tuples or lists.
3. **Boolean arrays**: Pass Python lists of `True`/`False`.
4. **Return values**: Most methods return `int`. Check `ret == 0` for success.
5. **String out parameters**: Initialize as empty string `''` before calling.
6. **Performance**: Use `TreeSuspendUpdateData(True)` / `TreeResumeUpdateData()` to suppress GUI updates during batch operations.

---

### Important Notes
- ETABS must be running before executing scripts (or use start_new_etabs)
- After modifying the model, call `SapModel.View.RefreshView(0, False)`
- Lock the model before analysis: `SapModel.Analyze.SetRunCaseFlag("", True, True)`
- Return value 0 = success for most API calls
- Use `SapModel.SetPresentUnits(unit_code)` to switch units mid-script
- **Save the model before running analysis** -- RunAnalysis requires a file path

---

## Common Workflow Patterns

### Pattern 1: Create a Complete RC Building
```
1. Initialize model: SapModel.InitializeNewModel(14)
2. Create blank: SapModel.File.NewBlank()
3. Define materials: PropMaterial.AddMaterial / SetMPIsotropic / SetOConcrete_1
4. Define sections: PropFrame.SetRectangle (columns, beams) / PropArea.SetSlab
5. Define stories: Story.SetStories_2
6. Add columns: FrameObj.AddByCoord (vertical members)
7. Add beams: FrameObj.AddByCoord (horizontal members)
8. Add slabs: AreaObj.AddByCoord
9. Assign restraints: PointObj.SetRestraint (base supports)
10. Define load patterns: LoadPatterns.Add
11. Assign loads: FrameObj.SetLoadDistributed / AreaObj.SetLoadUniform
12. Define combinations: RespCombo.Add / SetCaseList
13. Save model: File.Save
14. Run analysis: Analyze.RunAnalysis
15. Extract results: Results.FrameForce / StoryDrifts / via DatabaseTables
16. Run design: DesignConcrete.StartDesign
17. Extract design results: DesignConcrete.GetSummaryResultsColumn/Beam
```

### Pattern 2: Modify Existing Model
```
1. Attach: attach_to_etabs()
2. Unlock: SapModel.SetModelIsLocked(False)
3. Make changes
4. Refresh view: View.RefreshView(0, False)
5. Save: File.Save()
6. Rerun analysis if needed: Analyze.RunAnalysis()
```

### Pattern 3: Extract Results from Existing Model
```
1. Attach: attach_to_etabs()
2. Configure output: Results.Setup.DeselectAllCasesAndCombosForOutput()
3. Select cases: Results.Setup.SetCaseSelectedForOutput("CaseName")
4. Extract via API: Results.FrameForce / JointDispl / StoryDrifts
   OR extract via tables: DatabaseTables.GetTableForDisplayArray("Table Key", ...)
```

---

## Workflow for Claude Code
1. User describes what they want (create model / modify / analyze / check)
2. Claude writes a Python script using the connection module
3. Claude executes the script via Bash and reads output
4. Claude iterates based on results or errors
5. For complex tasks, break into smaller scripts (define -> assign -> analyze -> extract)
6. **When unsure about any API method, ALWAYS look it up first** (see API Lookup Rule above)
