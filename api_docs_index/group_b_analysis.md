# ETABS API Reference - Group B (Modeling, Properties, Design, Model Operations)

> **59 interfaces** covering the core modeling API: object creation/manipulation, section properties, material definitions, design operations, database tables, load definitions, story management, and utility operations.
> All methods return `int` (0=success, nonzero=failure) unless otherwise noted.
> C# `ref` parameters become output/ByRef parameters in Python COM calls.

---

## 1. cSapModel (The Root Object)

**Access**: `SapModel = EtabsObject.SapModel`
This is THE central interface. All other interfaces are accessed as properties of cSapModel.

### 1.1 Properties (Sub-Interface Access) - 51 Properties

| Property | Type | Description |
|----------|------|-------------|
| `SapModel.Analyze` | cAnalyze | Analysis operations (run, set cases) |
| `SapModel.AreaElm` | cAreaElm | Area element-level access |
| `SapModel.AreaObj` | cAreaObj | Area object manipulation (slabs, walls, floors) |
| `SapModel.ConstraintDef` | cConstraint | Constraint definitions (diaphragm, body, etc.) |
| `SapModel.DatabaseTables` | cDatabaseTables | Database table API (bulk data I/O) |
| `SapModel.DesignCompositeBeam` | cDesignCompositeBeam | Composite beam design |
| `SapModel.DesignCompositeColumn` | cDesignCompositeColumn | Composite column design |
| `SapModel.DesignConcrete` | cDesignConcrete | Concrete frame design |
| `SapModel.DesignConcreteSlab` | cDesignConcreteSlab | Concrete slab design |
| `SapModel.DesignResults` | cDesignResults | Design results access |
| `SapModel.DesignShearWall` | cDesignShearWall | Shear wall design |
| `SapModel.DesignSteel` | cDesignSteel | Steel frame design |
| `SapModel.Detailing` | cDetailing | Detailing operations |
| `SapModel.Diaphragm` | cDiaphragm | Diaphragm management |
| `SapModel.EditArea` | cEditArea | Area editing operations |
| `SapModel.EditFrame` | cEditFrame | Frame editing operations |
| `SapModel.EditGeneral` | cEditGeneral | General editing (move, etc.) |
| `SapModel.EditPoint` | cEditPoint | Point editing operations |
| `SapModel.File` | cFile | File operations (new, open, save, export) |
| `SapModel.FrameObj` | cFrameObj | Frame object manipulation (beams, columns, braces) |
| `SapModel.Func` | cFunction | Time history / function definitions |
| `SapModel.GDispl` | cGenDispl | Generalized displacements |
| `SapModel.GridSys` | cGridSys | Grid system definitions |
| `SapModel.GroupDef` | cGroup | Group management |
| `SapModel.LineElm` | cLineElm | Line element-level access |
| `SapModel.LinkElm` | cLinkElm | Link element-level access |
| `SapModel.LinkObj` | cLinkObj | Link object manipulation |
| `SapModel.LoadCases` | cLoadCases | Load case definitions |
| `SapModel.LoadPatterns` | cLoadPatterns | Load pattern definitions |
| `SapModel.Options` | cOptions | Program options |
| `SapModel.PatternDef` | cPatternDef | Joint pattern definitions |
| `SapModel.PierLabel` | cPierLabel | Pier label management |
| `SapModel.PointElm` | cPointElm | Point element-level access |
| `SapModel.PointObj` | cPointObj | Point/joint object manipulation |
| `SapModel.PropArea` | cPropArea | Area section properties |
| `SapModel.PropAreaSpring` | cPropAreaSpring | Area spring properties |
| `SapModel.PropFrame` | cPropFrame | Frame section properties (beams, columns) |
| `SapModel.PropLineSpring` | cPropLineSpring | Line spring properties |
| `SapModel.PropLink` | cPropLink | Link properties |
| `SapModel.PropMaterial` | cPropMaterial | Material properties |
| `SapModel.PropPointSpring` | cPropPointSpring | Point spring properties |
| `SapModel.PropRebar` | cPropRebar | Rebar properties |
| `SapModel.PropTendon` | cPropTendon | Tendon properties |
| `SapModel.RespCombo` | cCombo | Response/load combinations |
| `SapModel.Results` | cAnalysisResults | Analysis results extraction |
| `SapModel.SelectObj` | cSelect | Selection operations |
| `SapModel.SpandrelLabel` | cSpandrelLabel | Spandrel label management |
| `SapModel.Story` | cStory | Story definitions |
| `SapModel.TendonObj` | cTendonObj | Tendon object manipulation |
| `SapModel.Tower` | cTower | Tower definitions |
| `SapModel.View` | cView | View refresh operations |

### 1.2 Methods - 21 Methods

#### InitializeNewModel(Units)
```
int InitializeNewModel(eUnits Units = eUnits.kip_in_F)
```
- **Purpose**: Clears previous model and initializes program for a new model. Save previous model first if needed.
- **Parameters**: `Units` (optional, eUnits) - Display/present units for the new model. Default: kip_in_F
- **Returns**: 0=success
- **Remarks**: Includes ApplicationStart functionality; no need to call both.
- **Python**: `ret = SapModel.InitializeNewModel(14)` (14 = kgf_cm_C)

#### SetPresentUnits(Units) / GetPresentUnits()
```
int SetPresentUnits(eUnits Units)
eUnits GetPresentUnits()
```
- **Purpose**: Sets/gets the present units for API data transmission. Independent of GUI display units.
- **Key eUnits values**: 1=lb_in_F, 2=lb_ft_F, 3=kip_in_F, 4=kip_ft_F, 5=kN_mm_C, 6=kN_m_C, 7=kgf_mm_C, 8=kgf_m_C, 9=N_mm_C, 10=N_m_C, 11=Ton_mm_C, 12=Ton_m_C, 13=kN_cm_C, 14=kgf_cm_C, 15=N_cm_C, 16=Ton_cm_C

#### SetPresentUnits_2(forceUnits, lengthUnits, temperatureUnits)
```
int SetPresentUnits_2(eForce forceUnits, eLength lengthUnits, eTemperature temperatureUnits)
int GetPresentUnits_2(ref eForce forceUnits, ref eLength lengthUnits, ref eTemperature temperatureUnits)
```
- **Purpose**: Fine-grained unit control with separate force, length, temperature enumerations.

#### GetDatabaseUnits() / GetDatabaseUnits_2(...)
```
eUnits GetDatabaseUnits()
int GetDatabaseUnits_2(ref eForce forceUnits, ref eLength lengthUnits, ref eTemperature temperatureUnits)
```
- **Purpose**: Returns the internal database units. All data stored internally uses these units.
- **Note**: If length unit is inch or feet, database units = lb_in_F. Otherwise N_mm_C.

#### GetModelFilename(IncludePath) / GetModelFilepath()
```
string GetModelFilename(bool IncludePath = true)
string GetModelFilepath()
```
- **Purpose**: Returns current model filename (with/without path) and filepath.

#### GetModelIsLocked() / SetModelIsLocked(Lockit)
```
bool GetModelIsLocked()
int SetModelIsLocked(bool Lockit)
```
- **Purpose**: Gets/sets model lock status. When locked, most definitions/assignments cannot be changed.

#### GetVersion(Version, MyVersionNumber)
```
int GetVersion(ref string Version, ref double MyVersionNumber)
```
- **Purpose**: Returns program version string and number.

#### GetProgramInfo(ProgramName, ProgramVersion, ProgramLevel)
```
int GetProgramInfo(ref string ProgramName, ref string ProgramVersion, ref string ProgramLevel)
```

#### GetProjectInfo / SetProjectInfo
```
int GetProjectInfo(ref int NumberItems, ref string[] Item, ref string[] Data)
int SetProjectInfo(string Item, string Data)
```
- **Purpose**: Get/set project information fields (Client, Project Name, etc.)

#### GetPresentCoordSystem() / GetMergeTol / SetMergeTol
```
string GetPresentCoordSystem()
int GetMergeTol(ref double MergeTol)
int SetMergeTol(double MergeTol)
```

#### Tree Update Control
```
int TreeSuspendUpdateData(bool updateAtResume)
int TreeResumeUpdateData()
int TreeIsUpdateSuspended(ref bool IsSuspended)
```
- **Purpose**: Suspend/resume model explorer tree updates for performance during batch operations.

---

## 2. cFile (SapModel.File) - 8 Methods

File operations for creating, opening, saving, and importing/exporting models.

#### NewBlank()
```
int NewBlank()
```
- **Purpose**: Creates a new, blank model.

#### NewGridOnly(NumberStorys, TypicalStoryHeight, BottomStoryHeight, NumberLines_X, NumberLines_Y, SpacingX, SpacingY)
```
int NewGridOnly(int NumberStorys, double TypicalStoryHeight, double BottomStoryHeight, int NumberLines_X, int NumberLines_Y, double SpacingX, double SpacingY)
```
- **Purpose**: Creates a new grid-only model from template.

#### NewSteelDeck(NumberStorys, TypicalStoryHeight, BottomStoryHeight, NumberLines_X, NumberLines_Y, SpacingX, SpacingY)
```
int NewSteelDeck(int NumberStorys, double TypicalStoryHeight, double BottomStoryHeight, int NumberLines_X, int NumberLines_Y, double SpacingX, double SpacingY)
```
- **Purpose**: Creates a new steel deck model from template.

#### OpenFile(FileName)
```
int OpenFile(string FileName)
```
- **Purpose**: Opens an existing ETABS model file (.EDB).
- **Python**: `ret = SapModel.File.OpenFile(r"C:\path\to\model.EDB")`

#### Save(FileName)
```
int Save(string FileName = "")
```
- **Purpose**: Saves the current model. If FileName is empty, saves to current file.

#### ExportFile(FileName, FileType) / ImportFile(FileName, FileType, Type)
```
int ExportFile(string FileName, eFileTypeIO FileType)
int ImportFile(string FileName, eFileTypeIO FileType, int Type)
```
- **Purpose**: Export/import model to/from various file formats.

#### GetFilePath(FilePath)
```
int GetFilePath(ref string FilePath)
```

---

## 3. cFrameObj (SapModel.FrameObj) - 74 Methods

Frame object manipulation for beams, columns, and braces. This is one of the most heavily used interfaces.

### 3.1 Creation Methods

#### AddByCoord(XI, YI, ZI, XJ, YJ, ZJ, Name, PropName, UserName, CSys)
```
int AddByCoord(double XI, double YI, double ZI, double XJ, double YJ, double ZJ, ref string Name, string PropName = "Default", string UserName = "", string CSys = "Global")
```
- **Purpose**: Adds a new frame object by specifying start (I) and end (J) coordinates.
- **Parameters**:
  - `XI, YI, ZI`: Start point coordinates
  - `XJ, YJ, ZJ`: End point coordinates
  - `Name`: Returns the assigned name
  - `PropName`: Frame section property name (default "Default")
  - `UserName`: Optional user-specified name
  - `CSys`: Coordinate system (default "Global")
- **Python**: `Name = ''; ret = SapModel.FrameObj.AddByCoord(0, 0, 0, 0, 0, 300, Name, "COL30x30")`

#### AddByPoint(Point1, Point2, Name, PropName, UserName)
```
int AddByPoint(string Point1, string Point2, ref string Name, string PropName = "Default", string UserName = "")
```
- **Purpose**: Adds a new frame object between two existing point objects.

### 3.2 Query Methods

#### GetAllFrames(...)
```
int GetAllFrames(ref int NumberNames, ref string[] MyName, ref string[] PropName, ref string[] StoryName, ref string[] PointName1, ref string[] PointName2, ref double[] Point1X, ref double[] Point1Y, ref double[] Point1Z, ref double[] Point2X, ref double[] Point2Y, ref double[] Point2Z, ref double[] Angle, ref double[] Offset1X, ref double[] Offset2X, ref double[] Offset1Y, ref double[] Offset2Y, ref double[] Offset1Z, ref double[] Offset2Z, ref int[] CardinalPoint, string csys = "Global")
```
- **Purpose**: Retrieves data for ALL frame objects at once. Very efficient for bulk queries.

#### GetNameList / GetNameListOnStory / Count
```
int GetNameList(ref int NumberNames, ref string[] MyName)
int GetNameListOnStory(string StoryName, ref int NumberNames, ref string[] MyName)
int Count(string MyType = "All")
```
- **Purpose**: Get frame names, names on a story, or count frames.
- `MyType` for Count: "All", "Column", "Beam", "Brace"

#### GetSection / SetSection
```
int GetSection(string Name, ref string PropName, ref string SAuto)
int SetSection(string Name, string PropName, eItemType ItemType = eItemType.Objects, double SVarRelStartLoc = 0, double SVarTotalLength = 0)
```
- **Purpose**: Get/set the frame section property assigned to a frame object.

#### GetPoints
```
int GetPoints(string Name, ref string Point1, ref string Point2)
```
- **Purpose**: Gets the point object names at each end of the frame.

#### GetLabelFromName / GetNameFromLabel
```
int GetLabelFromName(string Name, ref string Label, ref string Story)
int GetNameFromLabel(string Label, string Story, ref string Name)
```
- **Purpose**: Convert between unique names and label+story pairs.

#### GetDesignOrientation / SetDesignProcedure
```
int GetDesignOrientation(string Name, ref eFrameDesignOrientation DesignOrientation)
int SetDesignProcedure(string Name, int MyType, eItemType ItemType = eItemType.Objects)
```
- **Purpose**: Get/set the design orientation and procedure for frame objects.

### 3.3 Load Assignment Methods

#### SetLoadDistributed / GetLoadDistributed
```
int SetLoadDistributed(string Name, string LoadPat, int MyType, int Dir, double Dist1, double Dist2, double Val1, double Val2, string CSys = "Global", bool RelDist = true, bool Replace = true, eItemType ItemType = eItemType.Objects)
int GetLoadDistributed(string Name, ref int NumberItems, ref string[] FrameName, ref string[] LoadPat, ref int[] MyType, ref string[] CSys, ref int[] Dir, ref double[] RD1, ref double[] RD2, ref double[] Dist1, ref double[] Dist2, ref double[] Val1, ref double[] Val2, eItemType ItemType = eItemType.Objects)
```
- **Purpose**: Assign/retrieve distributed loads on frame objects.
- **MyType**: 1=Force, 2=Moment
- **Dir**: 1-6 for force/moment direction (1=local-1, 2=local-2, 3=local-3, 4=X, 5=Y, 6=Z, 7=-X, 8=-Y, 9=-Z, 10=Gravity, 11=Projected gravity)
- **Python**: `ret = SapModel.FrameObj.SetLoadDistributed("B1", "Live", 1, 11, 0, 1, -500, -500)` (500 kgf/cm gravity load)

#### SetLoadPoint / GetLoadPoint
```
int SetLoadPoint(string Name, string LoadPat, int MyType, int Dir, double Dist, double Val, string CSys = "Global", bool RelDist = true, bool Replace = true, eItemType ItemType = eItemType.Objects)
int GetLoadPoint(string Name, ref int NumberItems, ref string[] FrameName, ref string[] LoadPat, ref int[] MyType, ref string[] CSys, ref int[] Dir, ref double[] RelDist, ref double[] Dist, ref double[] Val, eItemType ItemType = eItemType.Objects)
```

#### SetLoadTemperature / GetLoadTemperature
```
int SetLoadTemperature(string Name, string LoadPat, int MyType, double Val, string PatternName = "", bool Replace = true, eItemType ItemType = eItemType.Objects)
```

### 3.4 Property Assignment Methods

#### SetReleases / GetReleases
```
int SetReleases(string Name, ref bool[] II, ref bool[] JJ, ref double[] StartValue, ref double[] EndValue, eItemType ItemType = eItemType.Objects)
int GetReleases(string Name, ref bool[] II, ref bool[] JJ, ref double[] StartValue, ref double[] EndValue)
```
- **Purpose**: Set/get end releases (moment releases for pins, etc.)
- II, JJ: 6-element bool arrays [P, V2, V3, T, M2, M3] for I-end and J-end
- StartValue, EndValue: Partial fixity spring constants

#### SetModifiers / GetModifiers
```
int SetModifiers(string Name, ref double[] Value, eItemType ItemType = eItemType.Objects)
int GetModifiers(string Name, ref double[] Value)
```
- **Purpose**: Property modifiers (8 values): [Area, As2, As3, Torsion, I22, I33, Mass, Weight]

#### SetEndLengthOffset / GetEndLengthOffset
```
int SetEndLengthOffset(string Name, bool AutoOffset, double Length1, double Length2, double RZ, eItemType ItemType = eItemType.Objects)
int GetEndLengthOffset(string Name, ref bool AutoOffset, ref double Length1, ref double Length2, ref double RZ)
```

#### SetInsertionPoint / GetInsertionPoint
```
int SetInsertionPoint(string Name, int CardinalPoint, bool Mirror2, bool StiffTransform, ref double[] Offset1, ref double[] Offset2, string CSys = "Local", eItemType ItemType = eItemType.Objects)
int GetInsertionPoint(string Name, ref int CardinalPoint, ref bool Mirror2, ref bool StiffTransform, ref double[] Offset1, ref double[] Offset2, ref string CSys)
```
- **CardinalPoint**: 1-11 (1=BottomLeft, 8=MiddleCenter/Centroid, 10=TopCenter, etc.)

#### SetLocalAxes / GetLocalAxes
```
int SetLocalAxes(string Name, double Ang, eItemType ItemType = eItemType.Objects)
int GetLocalAxes(string Name, ref double Ang, ref bool Advanced)
```

#### SetPier/GetPier, SetSpandrel/GetSpandrel
```
int SetPier(string Name, string PierName, eItemType ItemType = eItemType.Objects)
int GetPier(string Name, ref string PierName)
int SetSpandrel(string Name, string SpandrelName, eItemType ItemType = eItemType.Objects)
int GetSpandrel(string Name, ref string SpandrelName)
```

#### SetGroupAssign / GetGroupAssign
```
int SetGroupAssign(string Name, string GroupName, bool Remove = false, eItemType ItemType = eItemType.Objects)
int GetGroupAssign(string Name, ref int NumberGroups, ref string[] Groups)
```

### 3.5 Other Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `Delete` | `(string Name, eItemType ItemType)` | Delete frame objects |
| `ChangeName` | `(string Name, string NewName)` | Rename a frame object |
| `GetSelected/SetSelected` | `(string Name, ref bool/bool Selected)` | Get/set selection status |
| `GetElm` | `(string Name, ref int NElm, ref string[] Elm, ...)` | Get analysis elements |
| `GetTypeOAPI` | `(string Name, ref string MyType)` | Get frame type ("Column"/"Beam"/"Brace") |
| `GetMass/SetMass` | Mass per unit length assignments |
| `GetMaterialOverwrite/SetMaterialOverwrite` | Override material property |
| `GetOutputStations/SetOutputStations` | Output station settings |
| `GetHingeAssigns/GetHingeAssigns_1` | Get hinge assignments |
| `GetColumnSpliceOverwrite/SetColumnSpliceOverwrite` | Column splice settings |
| `GetCurved_2` | Curved frame geometry |
| `GetGUID/SetGUID` | GUID management |
| `GetSpringAssignment/SetSpringAssignment` | Spring property assignments |
| `GetTCLimits/SetTCLimits` | Tension/compression limits |
| `GetTransformationMatrix` | Local-to-global transformation matrix |
| `GetLabelNameList` | Get all labels with names and stories |
| `GetSectionNonPrismatic` | Non-prismatic section assignment data |
| `DeleteLoadDistributed/DeleteLoadPoint/DeleteLoadTemperature` | Delete load assignments |
| `DeleteMass/DeleteModifiers/DeleteSpring` | Delete property assignments |
| `DeleteLateralBracing` | Delete lateral bracing |
| `GetLateralBracing/SetLateralBracing` | Lateral bracing assignments |
| `GetSupports` | Support conditions at frame ends |

---

## 4. cPointObj (SapModel.PointObj) - 58 Methods

Point/joint object manipulation for nodes, supports, and restraints.

### 4.1 Creation and Query

#### AddCartesian(X, Y, Z, Name, ...)
```
int AddCartesian(double X, double Y, double Z, ref string Name, string UserName = "", string CSys = "Global", bool MergeOff = false, int MergeNumber = 0)
```
- **Purpose**: Adds a point object at Cartesian coordinates.

#### GetAllPoints(...)
```
int GetAllPoints(ref int NumberNames, ref string[] MyName, ref double[] X, ref double[] Y, ref double[] Z, string CSys = "Global")
```
- **Purpose**: Retrieves all point names and coordinates at once. Efficient for bulk queries.

#### GetNameList / GetNameListOnStory / Count
```
int GetNameList(ref int NumberNames, ref string[] MyName)
int GetNameListOnStory(string StoryName, ref int NumberNames, ref string[] MyName)
int Count()
```

#### GetCoordCartesian / GetCoordCylindrical / GetCoordSpherical
```
int GetCoordCartesian(string Name, ref double X, ref double Y, ref double Z, string CSys = "Global")
int GetCoordCylindrical(string Name, ref double R, ref double Theta, ref double Z, string CSys = "Global")
int GetCoordSpherical(string Name, ref double R, ref double A, ref double B, string CSys = "Global")
```

### 4.2 Restraints (Supports)

#### SetRestraint / GetRestraint
```
int SetRestraint(string Name, ref bool[] Value, eItemType ItemType = eItemType.Objects)
int GetRestraint(string Name, ref bool[] Value)
```
- **Purpose**: Assign/retrieve restraint (support) conditions.
- `Value`: 6-element bool array [U1, U2, U3, R1, R2, R3] (True = restrained)
- **Python** (fixed base): `Value = [True, True, True, True, True, True]; ret = SapModel.PointObj.SetRestraint("1", Value)`

#### SetSpring / GetSpring
```
int SetSpring(string Name, ref double[] K, eItemType ItemType = eItemType.Objects, bool IsLocalCSys = true, bool Replace = false)
int GetSpring(string Name, ref double[] K)
```
- `K`: 6-element array of spring stiffnesses [K1, K2, K3, KR1, KR2, KR3]

### 4.3 Loads

#### SetLoadForce / GetLoadForce
```
int SetLoadForce(string Name, string LoadPat, ref double[] Value, bool Replace = false, string CSys = "Global", eItemType ItemType = eItemType.Objects)
int GetLoadForce(string Name, ref int NumberItems, ref string[] PointName, ref string[] LoadPat, ref int[] LcStep, ref string[] CSys, ref double[] F1, ref double[] F2, ref double[] F3, ref double[] M1, ref double[] M2, ref double[] M3)
```
- `Value`: 6-element array [F1, F2, F3, M1, M2, M3]

#### SetLoadDispl / GetLoadDispl
```
int SetLoadDispl(string Name, string LoadPat, ref double[] Value, bool Replace = false, string CSys = "Local", eItemType ItemType = eItemType.Objects)
```

### 4.4 Other Methods

| Method | Purpose |
|--------|---------|
| `GetConnectivity` | Objects connected to this point |
| `GetDiaphragm/SetDiaphragm` | Diaphragm assignment |
| `GetLabelFromName/GetNameFromLabel` | Label-name conversion |
| `GetLabelNameList` | All labels with names and stories |
| `GetLocalAxes/SetLocalAxes` | Local axis angles |
| `GetMass/SetMass/SetMassByVolume/SetMassByWeight` | Mass assignments |
| `GetPanelZone/SetPanelZone` | Panel zone data |
| `GetGroupAssign/SetGroupAssign` | Group assignments |
| `GetSelected/SetSelected` | Selection status |
| `GetSpecialPoint/SetSpecialPoint` | Special point status |
| `GetSpringAssignment/SetSpringAssignment` | Named spring property |
| `GetSpringCoupled/SetSpringCoupled/IsSpringCoupled` | Coupled spring data |
| `GetGUID/SetGUID` | GUID management |
| `GetElm` | Get corresponding analysis element |
| `GetCommonTo` | Number of objects connected to point |
| `GetTransformationMatrix` | Transformation matrix |
| `DeleteLoadForce/DeleteLoadDispl/DeleteMass/DeleteRestraint/DeleteSpring/DeletePanelZone/DeleteSpecialPoint` | Delete assignments |
| `CountLoadForce/CountLoadDispl/CountPanelZone/CountRestraint/CountSpring` | Count assignments |
| `ChangeName` | Rename point object |

---

## 5. cPropFrame (SapModel.PropFrame) - 105 Methods, 1 Property

Frame section property definitions. The largest interface in Group B. Organized by section shape type.

**Property**: `SapModel.PropFrame.SDShape` -> cPropFrameSDShape (Section Designer shapes)

### 5.1 General Management

```
int Count(eFramePropType PropType = 0)                    -- Count frame properties (0=All)
int GetNameList(ref int NumberNames, ref string[] MyName, eFramePropType PropType = 0)  -- List all frame property names
int GetTypeOAPI(string Name, ref eFramePropType PropType)  -- Get property type enum
int ChangeName(string Name, string NewName)                -- Rename property
int Delete(string Name)                                    -- Delete property
int GetMaterial(string Name, ref string MatProp)           -- Get material of section
int SetMaterial(string Name, string MatProp)               -- Set material of section
int GetModifiers(string Name, ref double[] Value)          -- Get 8 property modifiers
int SetModifiers(string Name, ref double[] Value)          -- Set 8 property modifiers
int GetSectProps(string Name, ref double Area, ref double As2, ref double As3, ref double Torsion, ref double I22, ref double I33, ref double S22, ref double S33, ref double Z22, ref double Z33, ref double R22, ref double R33) -- Get calculated section properties
int GetTypeRebar(string Name, ref int MyType)              -- Get rebar type (0=column, 1=beam)
int ImportProp(string Name, string MatProp, string FileName, string PropName, int Color = -1, string Notes = "", string GUID = "") -- Import from property file
int GetPropFileNameList(string FileName, ref int NumberNames, ref string[] MyName, ref eFramePropType[] MyPropType, eFramePropType PropType = 0) -- List props in a file
int GetNameInPropFile(string Name, ref string NameInFile, ref string FileName, ref string MatProp, ref eFramePropType PropType) -- Get name in source file
```

#### GetAllFrameProperties / GetAllFrameProperties_2
```
int GetAllFrameProperties(ref int NumberNames, ref string[] MyName, ref eFramePropType[] PropType, ref double[] t3, ref double[] t2, ref double[] tf, ref double[] tw, ref double[] t2b, ref double[] tfb)
int GetAllFrameProperties_2(ref int NumberNames, ref string[] MyName, ref eFramePropType[] PropType, ref double[] t3, ref double[] t2, ref double[] tf, ref double[] tw, ref double[] t2b, ref double[] tfb, ref double[] Area)
```
- **Purpose**: Bulk retrieval of all frame section properties at once. Very efficient.

### 5.2 Rectangular Sections
```
int SetRectangle(string Name, string MatProp, double T3, double T2, int Color = -1, string Notes = "", string GUID = "")
int GetRectangle(string Name, ref string FileName, ref string MatProp, ref double T3, ref double T2, ref int Color, ref string Notes, ref string GUID)
```
- T3 = depth (local 3-axis), T2 = width (local 2-axis)
- **Python**: `ret = SapModel.PropFrame.SetRectangle("COL30x30", "Conc", 30, 30)` (30x30cm column)

### 5.3 Circular Sections
```
int SetCircle(string Name, string MatProp, double T3, int Color = -1, string Notes = "", string GUID = "")
int GetCircle(string Name, ref string FileName, ref string MatProp, ref double T3, ref int Color, ref string Notes, ref string GUID)
```
- T3 = diameter

### 5.4 I-Sections (Wide Flange)
```
int SetISection(string Name, string MatProp, double T3, double T2, double Tf, double Tw, double T2b, double Tfb, int Color = -1, string Notes = "", string GUID = "")
int GetISection(string Name, ref string FileName, ref string MatProp, ref double T3, ref double T2, ref double Tf, ref double Tw, ref double T2b, ref double Tfb, ref int Color, ref string Notes, ref string GUID)
int SetISection_1(... + double FilletRadius) -- with fillet radius
int GetISection_1(...)
```
- T3=depth, T2=top flange width, Tf=top flange thickness, Tw=web thickness, T2b=bot flange width, Tfb=bot flange thickness

### 5.5 Pipe (Hollow Circular)
```
int SetPipe(string Name, string MatProp, double T3, double TW, int Color = -1, string Notes = "", string GUID = "")
int GetPipe(string Name, ref string FileName, ref string MatProp, ref double T3, ref double TW, ...)
```
- T3 = outer diameter, TW = wall thickness

### 5.6 Tube (Hollow Rectangular / Box)
```
int SetTube(string Name, string MatProp, double T3, double T2, double Tf, double Tw, int Color = -1, string Notes = "", string GUID = "")
int GetTube(string Name, ref string FileName, ref string MatProp, ref double T3, ref double T2, ref double Tf, ref double Tw, ...)
int SetTube_1(... + double Radius) -- with corner radius
int GetTube_1(...)
```
- T3=depth, T2=width, Tf=flange thickness, Tw=web thickness

### 5.7 Tee Sections
```
int SetTee(string Name, string MatProp, double T3, double T2, double Tf, double Tw, ...)
int GetTee(...)
int SetTee_1(... + double FilletRadius, bool MirrorAbout3) -- with fillet and mirror option
int GetTee_1(...)
int SetSteelTee(string Name, string MatProp, double T3, double T2, double Tf, double Tw, double r, bool MirrorAbout3, ...)
int GetSteelTee(...)
```

### 5.8 Angle Sections
```
int SetAngle(string Name, string MatProp, double T3, double T2, double Tf, double Tw, ...)
int GetAngle(...)
int SetAngle_1(... + double FilletRadius)
int GetAngle_1(...)
int SetSteelAngle(string Name, string MatProp, double T3, double T2, double Tf, double Tw, double r, bool MirrorAbout2, bool MirrorAbout3, ...)
int GetSteelAngle(...)
```

### 5.9 Channel Sections
```
int SetChannel(string Name, string MatProp, double T3, double T2, double Tf, double Tw, ...)
int GetChannel(...)
int SetChannel_1(... + bool MirrorAbout2)
int GetChannel_1(...)
int SetChannel_2(... + double FilletRadius, bool MirrorAbout2)
int GetChannel_2(...)
```

### 5.10 Double Angle / Double Channel
```
int SetDblAngle(string Name, string MatProp, double T3, double T2, double Tf, double Tw, double Dis, ...)
int SetDblAngle_1(... + bool MirrorAbout3)
int SetDblAngle_2(... + double FilletRadius, bool MirrorAbout3)
int SetDblChannel(string Name, string MatProp, double T3, double T2, double Tf, double Tw, double Dis, ...)
int SetDblChannel_1(... + double FilletRadius)
```
- `Dis` = back-to-back distance

### 5.11 Concrete Sections
```
int SetConcreteBox(string Name, string MatProp, double T3, double T2, double Tf, double Tw, ...)
int SetConcreteCross(string Name, string MatProp, double T3, double T2, double Tf, double Tw, ...)
int SetConcreteL(string Name, string MatProp, double T3, double T2, double Tf, double TwC, double TwT, bool MirrorAbout2, bool MirrorAbout3, ...)
int SetConcretePipe(string Name, string MatProp, double Diameter, double Tw, ...)
int SetConcreteTee(string Name, string MatProp, double T3, double T2, double Tf, double TwF, double TwT, bool MirrorAbout3, ...)
```
- Each has corresponding Get method.

### 5.12 Cold-Formed Sections
```
int SetColdC / GetColdC / SetColdC_1 / GetColdC_1     -- Cold-formed C
int SetColdHat / GetColdHat / SetColdHat_1 / GetColdHat_1  -- Cold-formed Hat
int SetColdZ / GetColdZ / SetColdZ_1 / GetColdZ_1     -- Cold-formed Z
```
- Parameters: T3, T2, Thickness, Radius, LipDepth (and optional LipAngle for Z)

### 5.13 Other Section Types
```
int SetPlate(Name, MatProp, T3, T2, ...)              -- Plate section
int SetRod(Name, MatProp, T3, ...)                     -- Solid rod
int SetTrapezoidal(Name, MatProp, T3, T2, T2b, ...)   -- Trapezoidal section
int SetCoverPlatedI(Name, SectName, FyTopFlange, FyWeb, FyBotFlange, Tc, Bc, MatPropTop, ...) -- Cover-plated I-section
int SetPrecastI(Name, MatProp, b[], d[], ...)          -- Precast I-section
int SetSDSection(Name, MatProp, DesignType, ...)       -- Section Designer section
int GetSDSection(Name, ref MatProp, ref NumberItems, ref ShapeName[], ref MyType[], ...)
```

### 5.14 General Section (User-Defined Properties)
```
int SetGeneral(string Name, string MatProp, double T3, double T2, double Area, double As2, double As3, double Torsion, double I22, double I33, double S22, double S33, double Z22, double Z33, double R22, double R33, int Color = -1, string Notes = "", string GUID = "")
int GetGeneral(string Name, ref string FileName, ref string MatProp, ref double T3, ref double T2, ref double Area, ref double As2, ref double As3, ref double Torsion, ref double I22, ref double I33, ref double S22, ref double S33, ref double Z22, ref double Z33, ref double R22, ref double R33, ...)
int SetGeneral_1 / GetGeneral_1 -- Extended version
```
- **Purpose**: Define arbitrary section by specifying all section properties directly.

### 5.15 Non-Prismatic Sections
```
int SetNonPrismatic(string Name, int NumberItems, ref string[] StartSec, ref string[] EndSec, ref double[] MyLength, ref int[] MyType, ref int[] EI33, ref int[] EI22, int Color = -1, ...)
int GetNonPrismatic(string Name, ref int NumberItems, ref string[] StartSec, ref string[] EndSec, ref double[] MyLength, ref int[] MyType, ref int[] EI33, ref int[] EI22, ...)
```

### 5.16 Auto Select Steel Lists
```
int SetAutoSelectSteel(string Name, int NumberItems, ref string[] SectName, string AutoStartSection = "Median", ...)
int GetAutoSelectSteel(string Name, ref int NumberItems, ref string[] SectName, ref string AutoStartSection, ...)
```

### 5.17 Rebar Data
```
int SetRebarBeam(string Name, string MatPropLong, string MatPropConfine, double CoverTop, double CoverBot, double TopLeftArea, double TopRightArea, double BotLeftArea, double BotRightArea)
int GetRebarBeam(string Name, ref string MatPropLong, ref string MatPropConfine, ref double CoverTop, ref double CoverBot, ref double TopLeftArea, ref double TopRightArea, ref double BotLeftArea, ref double BotRightArea)

int SetRebarColumn(string Name, string MatPropLong, string MatPropConfine, int Pattern, int ConfineType, double Cover, int NumberCBars, int NumberR3Bars, int NumberR2Bars, string RebarSize, string TieSize, double TieSpacingLongit, int Number2DirTieBars, int Number3DirTieBars, bool ToBeDesigned)
int GetRebarColumn(string Name, ref string MatPropLong, ref string MatPropConfine, ref int Pattern, ref int ConfineType, ref double Cover, ref int NumberCBars, ref int NumberR3Bars, ref int NumberR2Bars, ref string RebarSize, ref string TieSize, ref double TieSpacingLongit, ref int Number2DirTieBars, ref int Number3DirTieBars, ref bool ToBeDesigned)
int GetRebarColumn_1(...) -- Extended version
```
- **Pattern**: 1=Rectangular, 2=Circular
- **ConfineType**: 1=Ties, 2=Spiral

---

## 6. cPropMaterial (SapModel.PropMaterial) - 46 Methods, 1 Property

Material property definitions for concrete, steel, rebar, tendon, and other materials.

**Property**: `SapModel.PropMaterial.TimeDep` -> Time-dependent material properties

### 6.1 General Management

#### AddMaterial
```
int AddMaterial(ref string Name, eMatType MatType, string Region, string Standard, string Grade, string UserName = "")
```
- **Purpose**: Adds a new material using predefined standards.
- **MatType**: 1=Steel, 2=Concrete, 3=NoDesign, 4=Tendon, 5=Rebar, 6=Aluminum, 7=ColdFormed, 8=Masonry
- **Python**: `Name = ''; ret = SapModel.PropMaterial.AddMaterial(Name, 2, "India", "IS 456", "M25")`

#### SetMaterial (DEPRECATED)
```
int SetMaterial(string Name, eMatType MatType, int Color = -1, string Notes = "", string GUID = "")
```
- Initializes a material property. Use AddMaterial for standard materials.

```
int Count(eMatType MatType = 0)           -- Count materials (0=All)
int GetNameList(ref int NumberNames, ref string[] MyName, eMatType MatType = 0)
int ChangeName(string Name, string NewName)
int Delete(string Name)
int GetMaterial(string Name, ref eMatType MatType, ref int Color, ref string Notes, ref string GUID)
int GetTypeOAPI(string Name, ref eMatType MatType, ref int SymType)
```

### 6.2 Mechanical Properties (Isotropic - Most Common)

#### SetMPIsotropic / GetMPIsotropic
```
int SetMPIsotropic(string Name, double E, double U, double A, double Temp = 0)
int GetMPIsotropic(string Name, ref double E, ref double U, ref double A, ref double G, double Temp = 0)
```
- **E**: Modulus of elasticity
- **U**: Poisson's ratio
- **A**: Coefficient of thermal expansion
- **G**: Shear modulus (returned, computed from E and U)
- **Python**: `ret = SapModel.PropMaterial.SetMPIsotropic("Conc", 2.5e5, 0.2, 1e-5)` (E=250000 kgf/cm2)

#### Other Symmetry Types
```
int SetMPOrthotropic / GetMPOrthotropic  -- E[], U[], A[], G[] (array-based)
int SetMPAnisotropic / GetMPAnisotropic  -- Full anisotropic
int SetMPUniaxial / GetMPUniaxial        -- E, A only
```

### 6.3 Design Properties

#### Concrete
```
int SetOConcrete_1(string Name, double Fc, bool IsLightweight, double FcsFactor, int SSType, int SSHysType, double StrainAtFc, double StrainUltimate, double FinalSlope, double FrictionAngle, double DilatationalAngle, double Temp = 0)
int GetOConcrete_1(string Name, ref double Fc, ref bool IsLightweight, ref double FcsFactor, ref int SSType, ref int SSType, ...)
```
- **Fc**: Compressive strength
- **SSType**: Stress-strain curve type (0=user, 1=Parametric-Simple, 2=Mander, etc.)

#### Steel
```
int SetOSteel_1(string Name, double Fy, double Fu, double EFy, double EFu, int SSType, int SSHysType, double StrainAtHardening, double StrainAtMaxStress, double StrainAtRupture, double FinalSlope, double Temp = 0)
int GetOSteel_1(...)
```
- **Fy**: Yield stress, **Fu**: Ultimate stress

#### Rebar
```
int SetORebar_1(string Name, double Fy, double Fu, double EFy, double EFu, int SSType, int SSHysType, double StrainAtHardening, double StrainAtMaxStress, double StrainAtRupture, double FinalSlope, bool UseCaltransSSDefaults, double Temp = 0)
int GetORebar_1(...)
```

#### Tendon
```
int SetOTendon_1 / GetOTendon_1
```

### 6.4 Other Methods
```
int GetWeightAndMass(string Name, ref double W, ref double M, double Temp = 0)
int SetWeightAndMass(string Name, int MyOption, double Value, double Temp = 0) -- MyOption: 1=by weight, 2=by mass
int GetDamping / SetDamping -- Modal damping ratio and Rayleigh coefficients
int GetSSCurve / SetSSCurve -- User-defined stress-strain curves
int GetTemp / SetTemp -- Temperature-dependent property definitions
int GetMassSource_1 / SetMassSource_1 -- Mass source definition
int GetONoDesign / SetONoDesign -- No-design material properties
```

---

## 7. cPropArea (SapModel.PropArea) - 35 Methods

Area section properties for slabs, walls, and decks.

### 7.1 General
```
int Count(int PropType = 0)                -- 0=All, 1=Shell, 2=Plane, 3=ASolid
int GetNameList(ref int NumberNames, ref string[] MyName, int PropType = 0)
int GetTypeOAPI(string Name, ref int PropType)
int ChangeName / Delete
int GetModifiers / SetModifiers  -- 10 modifiers for shells
```

### 7.2 Slab Sections
```
int SetSlab(string Name, eSlabType SlabType, eShellType ShellType, string MatProp, double Thickness, int color = -1, string Notes = "", string GUID = "")
int GetSlab(string Name, ref eSlabType SlabType, ref eShellType ShellType, ref string MatProp, ref double Thickness, ...)
```
- **eSlabType**: Slab, Drop, Stiff, Ribbed, Waffle, Mat, Footing
- **eShellType**: ShellThin, ShellThick, Membrane, Plate
- **Python**: `ret = SapModel.PropArea.SetSlab("Slab20", 0, 1, "Conc", 20)` (20cm slab)

```
int SetSlabRibbed(string Name, double OverallDepth, double SlabThickness, double StemWidthTop, double StemWidthBot, double RibSpacing, int RibDir)
int GetSlabRibbed(...)
int SetSlabWaffle(string Name, double OverallDepth, double SlabThickness, double StemWidthTop, double StemWidthBot, double RibSpacingDir1, double RibSpacingDir2)
int GetSlabWaffle(...)
```

### 7.3 Wall Sections
```
int SetWall(string Name, eWallPropType WallPropType, eShellType ShellType, string MatProp, double Thickness, int color = -1, ...)
int GetWall(string Name, ref eWallPropType WallPropType, ref eShellType ShellType, ref string MatProp, ref double Thickness, ...)
int SetWallAutoSelectList(string Name, string[] AutoSelectList, string StartingProperty = "Median")
int GetWallAutoSelectList(string Name, ref string[] AutoSelectList, ref string StartingProperty)
```

### 7.4 Deck Sections
```
int SetDeck / GetDeck / SetDeck_1 / GetDeck_1          -- General deck initialization
int SetDeckFilled / GetDeckFilled                       -- Filled deck (composite)
int SetDeckUnfilled / GetDeckUnfilled                   -- Unfilled deck
int SetDeckSolidSlab / GetDeckSolidSlab                 -- Solid slab deck
```

### 7.5 Shell Layers and Design
```
int SetShellLayer / GetShellLayer / SetShellLayer_1 / GetShellLayer_1 / SetShellLayer_2 / GetShellLayer_2
int SetShellDesign / GetShellDesign  -- Design parameters for shell areas
```

---

## 8. cDatabaseTables (SapModel.DatabaseTables) - 25 Methods

**CRITICAL INTERFACE** for bulk data extraction and import. The most powerful way to read/write model data.

### 8.1 Table Discovery

#### GetAllTables
```
int GetAllTables(ref int NumberTables, ref string[] TableKey, ref string[] TableName, ref int[] ImportType, ref bool[] IsEmpty)
```
- **Purpose**: Lists ALL available tables with their import type and emptiness status.
- **ImportType**: 0=NotImportable, 1=Importable, 2=ImportableAndBatchEditable
- **Python**: Use this to discover available table names.

#### GetAvailableTables
```
int GetAvailableTables(ref int NumberTables, ref string[] TableKey, ref string[] TableName, ref int[] ImportType, ref bool[] IsEmpty)
```

#### GetAllFieldsInTable
```
int GetAllFieldsInTable(string TableKey, ref int TableVersion, ref int NumberFields, ref string[] FieldKey, ref string[] FieldName, ref string[] Description, ref string[] UnitsString, ref bool[] IsImportable)
```
- **Purpose**: Returns field metadata for a table (column names, units, importability).

### 8.2 Data Retrieval (READ) - Most Important Methods

#### GetTableForDisplayArray (PRIMARY METHOD)
```
int GetTableForDisplayArray(string TableKey, ref string[] FieldKeyList, string GroupName, ref int TableVersion, ref string[] FieldsKeysIncluded, ref int NumberRecords, ref string[] TableData)
```
- **Purpose**: Returns table data as a flat 1D string array. THE main method for data extraction.
- **Parameters**:
  - `TableKey`: Table name (e.g., "Story Definitions", "Frame Forces", "Joint Displacements")
  - `FieldKeyList`: Empty array to get all fields, or specify field keys to filter
  - `GroupName`: Group filter ("All" or a specific group name)
  - `TableVersion`: Returns version number
  - `FieldsKeysIncluded`: Returns the field keys included in the output
  - `NumberRecords`: Number of data rows returned
  - `TableData`: 1D array of all values, row-major order (NumFields * NumberRecords elements)
- **Python Usage Pattern**:
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
# TableData is a flat array: reshape as [NumberRecords x len(FieldsKeysIncluded)]
```

**Common Table Keys** (use these string values):
- Model Definition: "Story Definitions", "Frame Section Properties", "Area Section Properties", "Material Properties", "Load Pattern Definitions", "Load Case Definitions", "Grid Lines"
- Analysis Results: "Story Drifts", "Story Forces", "Joint Displacements", "Joint Reactions", "Frame Forces", "Element Forces - Frames", "Element Joint Forces - Frames"
- Design Results: "Concrete Column Summary", "Concrete Beam Summary", "Steel Frame Design Summary", "Concrete Column PMM Envelope"

#### GetTableForDisplayCSVFile / GetTableForDisplayCSVString / GetTableForDisplayXMLString
```
int GetTableForDisplayCSVFile(string TableKey, ref string[] FieldKeyList, string GroupName, ref int TableVersion, string FileName)
int GetTableForDisplayCSVString(string TableKey, ref string[] FieldKeyList, string GroupName, ref int TableVersion, ref string CSVString)
int GetTableForDisplayXMLString(string TableKey, ref string[] FieldKeyList, string GroupName, ref int TableVersion, ref string XMLString)
```
- Alternative output formats for the same data.

### 8.3 Data Import (WRITE/EDIT)

#### Table Editing Workflow
1. Call `GetTableForEditingArray` or `GetTableForEditingCSVFile/String` to get current data
2. Modify the data
3. Call `SetTableForEditingArray` or `SetTableForEditingCSVFile/String` to stage changes
4. Call `ApplyEditedTables` to commit all staged changes
5. If errors, call `CancelTableEditing` to discard

```
int GetTableForEditingArray(string TableKey, ref string[] FieldKeyList, string GroupName, ref int TableVersion, ref string[] FieldsKeysIncluded, ref int NumberRecords, ref string[] TableData)
int SetTableForEditingArray(string TableKey, ref int TableVersion, ref string[] FieldsKeysIncluded, int NumberRecords, ref string[] TableData)
int GetTableForEditingCSVFile / SetTableForEditingCSVFile
int GetTableForEditingCSVString / SetTableForEditingCSVString
```

#### ApplyEditedTables
```
int ApplyEditedTables(bool FillImportLog, ref int NumFatalErrors, ref int NumErrorMsgs, ref int NumWarnMsgs, ref int NumInfoMsgs, ref string ImportLog)
```
- **Purpose**: Applies ALL staged table edits. Check NumFatalErrors for success.

#### CancelTableEditing
```
int CancelTableEditing()
```
- **Purpose**: Discards all staged edits.

### 8.4 Display Configuration
```
int GetLoadCasesSelectedForDisplay / SetLoadCasesSelectedForDisplay
int GetLoadCombinationsSelectedForDisplay / SetLoadCombinationsSelectedForDisplay
int GetLoadPatternsSelectedForDisplay / SetLoadPatternsSelectedForDisplay
int GetOutputOptionsForDisplay / SetOutputOptionsForDisplay
int ShowTablesInExcel  -- Open tables in Excel
int GetObsoleteTableKeyList  -- List obsolete table keys
```

---

## 9. cLoadPatterns (SapModel.LoadPatterns) - 11 Methods, 2 Properties

Load pattern definitions (Dead, Live, Wind, Seismic, etc.)

**Properties**:
- `SapModel.LoadPatterns.AutoSeismic` -> Auto seismic parameters
- `SapModel.LoadPatterns.AutoWind` -> Auto wind parameters

### Methods

#### Add
```
int Add(string Name, eLoadPatternType MyType, double SelfWTMultiplier = 0, bool AddAnalysisCase = true)
```
- **Purpose**: Adds a new load pattern.
- **eLoadPatternType**: Dead=1, SuperDead=2, Live=3, ReduceLive=4, Quake=5, Wind=6, Snow=7, Other=8, Move=9, Temperature=10, Roof Live=11, Notional=12, PatternLive=13, Wave=14, Braking=15, Centrifugal=16, Friction=17, Ice=18, WindOnIce=19, HypStatic=20, Bouyancy=21, SteamPressure=22, StreamFlow=23, Debris=24, VehicleLive=25, VehicleCollision=26, VesselCollision=27, TemperatureGradient=28, Settlement=29, ShrinkageConcrete=30, CreepConcrete=31, Waterload=32, LiveWall=33, EarthPressure=34, EarthSurcharge=35, DownDrag=36, VehLiveRed=37, EQDrift=38
- **Python**: `ret = SapModel.LoadPatterns.Add("Dead", 1, 1)` (Dead load with self-weight multiplier = 1)

```
int Count()
int Delete(string Name)
int ChangeName(string Name, string NewName)
int GetNameList(ref int NumberNames, ref string[] MyName)
int GetLoadType(string Name, ref eLoadPatternType MyType)
int SetLoadType(string Name, eLoadPatternType MyType)
int GetSelfWTMultiplier(string Name, ref double SelfWTMultiplier)
int SetSelfWTMultiplier(string Name, double SelfWTMultiplier)
int GetAutoSeismicCode(string Name, ref string CodeName)
int GetAutoWindCode(string Name, ref string CodeName)
```

---

## 10. cLoadCases (SapModel.LoadCases) - 7 Methods, 12 Properties

Load case definitions and sub-interfaces for each case type.

### Properties (Sub-Interfaces for Case Types)
| Property | Type | Description |
|----------|------|-------------|
| `StaticLinear` | cCaseStaticLinear | Static linear analysis cases |
| `StaticNonlinear` | cCaseStaticNonlinear | Static nonlinear (pushover) |
| `StaticNonlinearStaged` | cCaseStaticNonlinearStaged | Staged construction |
| `ModalEigen` | cCaseModalEigen | Eigen modal analysis |
| `ModalRitz` | cCaseModalRitz | Ritz modal analysis |
| `ResponseSpectrum` | cCaseResponseSpectrum | Response spectrum cases |
| `DirHistLinear` | cCaseDirHistLinear | Direct integration time history (linear) |
| `DirHistNonlinear` | cCaseDirHistNonlinear | Direct integration time history (nonlinear) |
| `ModHistLinear` | cCaseModHistLinear | Modal time history (linear) |
| `ModHistNonlinear` | cCaseModHistNonlinear | Modal time history (nonlinear) |
| `HyperStatic` | cCaseHyperStatic | Hyperstatic cases |
| `Buckling` | cCaseBuckling | Buckling analysis |

### Methods
```
int GetNameList(ref int NumberNames, ref string[] MyName, eLoadCaseType CaseType = 0) -- 0=All
int GetTypeOAPI(string Name, ref eLoadCaseType CaseType, ref int SubType)
int GetTypeOAPI_1(string Name, ref eLoadCaseType CaseType, ref int SubType, ref eLoadPatternType DesignType, ref int DesignTypeOption, ref int AutoCreatedCase)
int SetDesignType(string Name, int DesignTypeOption, eLoadPatternType DesignType = ...)
int Count(eLoadCaseType CaseType = 0)
int Delete(string Name)
int ChangeName(string Name, string NewName)
```
- **eLoadCaseType**: 0=All, 1=LinearStatic, 2=NonlinearStatic, 3=Modal, 4=ResponseSpectrum, 5=LinearHistoryModal, 6=NonlinearHistoryModal, 7=LinearHistoryDirect, 8=NonlinearHistoryDirect, 9=MovingLoad, 10=Buckling, 11=SteadyState, 12=PowerSpectral, 14=StagedConstruction, 15=HyperStatic

---

## 11. cStory (SapModel.Story) - 17 Methods

Story (floor level) definitions for the building model.

### Key Methods

#### GetStories_2 (Primary - supersedes GetStories)
```
int GetStories_2(ref double BaseElevation, ref int NumberStories, ref string[] StoryNames, ref double[] StoryElevations, ref double[] StoryHeights, ref bool[] IsMasterStory, ref string[] SimilarToStory, ref bool[] SpliceAbove, ref double[] SpliceHeight, ref int[] Color)
```
- **Purpose**: Retrieves ALL story information for the current tower.

#### SetStories_2 (Primary - supersedes SetStories)
```
int SetStories_2(double BaseElevation, int NumberStories, ref string[] StoryNames, ref double[] StoryHeights, ref bool[] IsMasterStory, ref string[] SimilarToStory, ref bool[] SpliceAbove, ref double[] SpliceHeight, ref int[] Color)
```
- **Note**: Can only be used when no objects exist in the model.

#### Individual Story Operations
```
int GetNameList(ref int NumberNames, ref string[] MyName)
int GetElevation(string Name, ref double Elevation) / SetElevation(string Name, double Elevation)
int GetHeight(string Name, ref double Height) / SetHeight(string Name, double Height)
int GetMasterStory(string Name, ref bool IsMasterStory) / SetMasterStory(string Name, bool IsMasterStory)
int GetSimilarTo(string Name, ref bool IsMasterStory, ref string SimilarToStory) / SetSimilarTo(string Name, string SimilarToStory)
int GetSplice(string Name, ref bool SpliceAbove, ref double SpliceHeight) / SetSplice(string Name, bool SpliceAbove, double SpliceHeight)
int GetGUID / SetGUID
```

---

## 12. cDesignConcrete (SapModel.DesignConcrete) - 14 Methods, 12 Properties

Concrete frame design operations.

### Properties (Design Code Sub-Interfaces)
Each property gives access to code-specific overwrite/preference methods:
`ACI318_08_IBC2009`, `ACI318_14`, `ACI318_19`, `AS_3600_09`, `AS_3600_2018`, `BS8110_97`, `Chinese_2010`, `Eurocode_2_2004`, `Indian_IS_456_2000`, `Mexican_RCDF_2017`, `SP63_13330_2012`, `TS_500_2000_R2018`

### Key Methods

#### StartDesign
```
int StartDesign()
```
- **Purpose**: Starts the concrete frame design. Analysis must be run first.

#### GetCode / SetCode
```
int GetCode(ref string CodeName)
int SetCode(string CodeName)
```
- **CodeName examples**: "ACI 318-19", "Eurocode 2-2004", "Indian IS 456-2000"

#### GetResultsAvailable
```
bool GetResultsAvailable()
```
- Returns True if design results are available.

#### GetSummaryResultsBeam / GetSummaryResultsBeam_2
```
int GetSummaryResultsBeam(string Name, ref int NumberItems, ref string[] FrameName, ref double[] Location, ref string[] TopCombo, ref double[] TopArea, ref string[] BotCombo, ref double[] BotArea, ref string[] VmajorCombo, ref double[] VmajorArea, ref string[] TlCombo, ref double[] TlArea, ref string[] TTCombo, ref double[] TTArea, eItemType ItemType = eItemType.Objects)
```
- **Purpose**: Beam design summary: required reinforcement areas at each location.
- **Returns**: Top/bottom rebar areas, shear rebar, torsion rebar at each output station.

#### GetSummaryResultsColumn
```
int GetSummaryResultsColumn(string Name, ref int NumberItems, ref string[] FrameName, ref int[] MyOption, ref double[] Location, ref string[] PMMCombo, ref double[] PMMArea, ref double[] PMMRatio, ref string[] VMajorCombo, ref double[] VmajorArea, ref string[] VMinorCombo, ref double[] VMinorArea, eItemType ItemType = eItemType.Objects)
```
- **Purpose**: Column design summary: PMM interaction ratios and required rebar.

#### GetSummaryResultsJoint
```
int GetSummaryResultsJoint(string Name, ref int NumberItems, ref string[] FrameName, ref string[] LCJSRatioMajor, ref double[] JSRatioMajor, ref string[] LCJSRatioMinor, ref double[] JSRatioMinor, ref string[] LCBCCRatioMajor, ref double[] BCCRatioMajor, ref string[] LCBCCRatioMinor, ref double[] BCCRatioMinor, eItemType ItemType = eItemType.Objects)
```

#### Other Methods
```
int SetComboStrength(string Name, bool Selected)          -- Select/deselect strength combo
int GetDesignSection / SetDesignSection                   -- Design section overrides
int GetRebarPrefsBeam(int Item, ref string Value)         -- Rebar selection rules for beams
int GetRebarPrefsColumn(int Item, ref string Value)       -- Rebar selection rules for columns
int GetSeismicFramingType(...)                             -- Seismic framing type
```

---

## 13. cDesignSteel (SapModel.DesignSteel) - 24 Methods, 21 Properties

Steel frame design operations.

### Properties (Design Code Sub-Interfaces)
21 code-specific interfaces: `AISC_LRFD93`, `AISC360_05_IBC2006`, `AISC360_10`, `AISC360_16`, `AISC360_22`, `Australian_AS4100_2020`, `Australian_AS4100_98`, `BS5950_2000`, `Canadian_S16_09`, `Canadian_S16_14`, `Canadian_S16_19`, `Canadian_S16_24`, `Chinese_2010`, `Chinese_2018`, `EN1993_1_1_2005`, `Eurocode_3_2005`, `Indian_IS_800_2007`, `Italian_NTC_2008`, `Italian_NTC_2018`, `NewZealand_NZS3404_97`, `SP16_13330_2011`

### Key Methods

```
int StartDesign()                                          -- Start steel design
int GetCode(ref string CodeName) / SetCode(string CodeName)
bool GetResultsAvailable()
int GetSummaryResults(string Name, ref int NumberItems, ref string[] FrameName, ref double[] Ratio, ref int[] RatioType, ref double[] Location, ref string[] ComboName, ref string[] ErrorSummary, ref string[] WarningSummary, eItemType ItemType = eItemType.Objects)
int GetSummaryResults_3(string Name, ref int NumberItems, ref string[] FrameName, ref eFrameDesignOrientation[] FrameType, ref string[] DesignSect, ref string[] Status, ref string[] PMMCombo, ref double[] PMMRatio, ref string[] PRatio, ref string[] MRatioMajor, ref string[] MRatioMinor, ref string[] VRatioMajor, ref string[] VRatioMinor, eItemType ItemType = eItemType.Objects)
int DeleteResults()
int ResetOverwrites()
int VerifyPassed(ref int NumberItems, ref int N1, ref int N2, ref string[] MyName)   -- N1=passed, N2=not passed
int VerifySections(ref int NumberItems, ref string[] MyName)                         -- Sections that did not pass
int GetDesignSection / SetDesignSection
int GetComboStrength / SetComboStrength / GetComboDeflection / SetComboDeflection
int GetGroup / SetGroup
int SetAutoSelectNull(string Name, eItemType ItemType)     -- Clear auto-select
int GetTargetDispl / SetTargetDispl / GetTargetPeriod / SetTargetPeriod
```

---

## 14. cDetailing (SapModel.Detailing) - 49 Methods

Detailed rebar output for beams, columns, slabs, and walls.

### Key Methods
```
int StartDetailing()                                       -- Start detailing process
int GetDetailingAvailable()                                -- Check if detailing results exist
int ClearDetailing()                                       -- Clear detailing results
```

### Beam Detailing
```
int GetBeamLongRebarData(...)                              -- Longitudinal rebar data
int GetBeamTieRebarData(...)                               -- Tie/shear rebar data
int GetDetailedBeamLines / GetDetailedBeamLines_1          -- Detailed beam line info
int GetDetailedBeamLineData / _1 / _2                      -- Beam line detailed data
int GetDetailedBeamLineGuidData(...)                       -- GUID-based beam data
int GetSimilarBeamLines / GetSimilarBeamLines_1            -- Similar beam line groups
```

### Column Detailing
```
int GetColumnLongRebarData(...)                            -- Longitudinal rebar data
int GetColumnTieRebarData(...)                             -- Tie/confinement rebar data
int GetDetailedColumnStacks / GetDetailedColumnStackData / _1 / _2
int GetDetailedColumnStackGuidData(...)
int GetSimilarColumnStacks(...)
```

### Slab Detailing
```
int GetNumberDetailedSlabs(...)                            -- Count of detailed slabs
int GetDetailedSlabs(...)                                  -- List detailed slabs
int GetDetailedSlab_OneDetailingOutputInfo(...)             -- One slab detailing output
int GetDetailedSlabTopBarData / _1                         -- Top bar data
int GetDetailedSlabBotBarData / _1                         -- Bottom bar data
int GetSimilarSlabs(...)
int GetOneDetailedSlab_OneDetailingOutput_StripInfo(...)
int GetOneDetailedSlab_OneDetailingOutput_StripGUID(...)
int GetOneDetailedSlab_OneDetailingOutput_OneStrip_OneDetailingRegionInfo(...)
int GetOneDetailedSlab_OneDetailingOutput_OneStrip_OneDetailingRegion_OneTopRebarInfo(...)
int GetOneDetailedSlab_OneDetailingOutput_OneStrip_OneDetailingRegion_OneTopRebar_Bar1Info(...)
int GetOneDetailedSlab_OneDetailingOutput_OneStrip_OneDetailingRegion_OneTopRebar_Bar2Info(...)
int GetOneDetailedSlab_OneDetailingOutput_OneStrip_OneDetailingRegion_OneBottomRebarInfo(...)
int GetOneDetailedSlab_OneDetailingOutput_OneStrip_OneDetailingRegion_OneBottomRebar_Bar1Info(...)
int GetOneDetailedSlab_OneDetailingOutput_OneStrip_OneDetailingRegion_OneBottomRebar_Bar2Info(...)
```

### Wall Detailing
```
int GetNumberDetailedWallStacks(...)
int GetDetailed_OneWallStack(...)
int GetDetailedWall_OneWallStack_OnePierOutputInfo(...)
int GetDetailedWall_OneWallStack_OnePier_OneDesignLegOutputInfo(...)
int GetDetailedWall_OneWallStack_OnePier_OneDesignLeg_OneVerticalBarInfo(...)
int GetDetailedWall_OneWallStack_OnePier_OneDesignLeg_OneTieBarInfo(...)
int GetDetailedWall_OneWallStack_OnePier_OneDesignLeg_OneTieBar_OneTiePlineInfo(...)
int GetDetailedWall_OneWallStack_OnePier_OneDesignLeg_OneTieBar_OneTiePline_OnePoint(...)
int GetDetailedWall_OneWallStack_OneSpandrelOutputInfo(...)
int GetDetailedWall_OneWallStack_OneSpandrel_OneLongBarInfo(...)
int GetDetailedWall_OneWallStack_OneSpandrel_OneStirrupsInfo(...)
```

---

## 15. cOAPI (EtabsObject) - 9 Methods, 1 Property

The top-level application object. Obtained via cHelper.

**Property**: `EtabsObject.SapModel` -> cSapModel (the root model object)

### Methods
```
int ApplicationStart()                                     -- Start the ETABS application
int ApplicationExit(bool FileSave)                         -- Exit application (FileSave=True to save first)
double GetOAPIVersionNumber()                              -- Get API version number
int Hide() / Unhide()                                      -- Show/hide application window
bool Visible()                                             -- Check if application is visible
int SetAsActiveObject() / UnsetAsActiveObject()             -- Register/unregister in Running Object Table (ROT)
int InternalExec(int operation)                             -- Internal use only
```

---

## 16. cHelper - 11 Methods

Helper/utility functions for creating and connecting to ETABS instances.

### Starting ETABS
```
cOAPI CreateObject(string fullPath)                        -- Start ETABS at given exe path
cOAPI CreateObjectProgID(string progID)                    -- Start ETABS by program ID ("CSI.ETABS.API.ETABSObject")
cOAPI CreateObjectHost(string hostName, string fullPath)   -- Start on remote computer
cOAPI CreateObjectHostPort(string hostName, int portNumber, string fullPath)
cOAPI CreateObjectProgIDHost(string hostName, string progID)
cOAPI CreateObjectProgIDHostPort(string hostName, int portNumber, string progID)
```

### Attaching to Running ETABS
```
cOAPI GetObject(string typeName)                           -- Attach to active ETABS instance
cOAPI GetObjectHost(string hostName, string progID)        -- Attach on remote computer
cOAPI GetObjectHostPort(string hostName, int portNumber, string progID)
cOAPI GetObjectProcess(string typeName, int pid)           -- Attach by process ID
double GetOAPIVersionNumber()                              -- Get API version
```
- **Python**: `EtabsObject = helper.GetObject("CSI.ETABS.API.ETABSObject")`

---

## 17. cGroup (SapModel.GroupDef) - 8 Methods

Group management for organizing objects.

```
int Count()
int GetNameList(ref int NumberNames, ref string[] MyName)
int Delete(string Name)
int SetGroup(string Name, int Color = -1, bool SpecifiedForSelection = true, bool SpecifiedForSectionCutDefinition = true, bool SpecifiedForSteelDesign = true, bool SpecifiedForConcreteDesign = true, bool SpecifiedForAluminumDesign = true, bool SpecifiedForStaticNLActiveStage = true, bool SpecifiedForBridgeResponseOutput = true)
int SetGroup_1(string Name, int color = -1, ...) -- Extended for ETABS-specific options
int GetGroup(string Name, ref int Color, ref bool SpecifiedForSelection, ...)
int GetGroup_1(string Name, ref int color, ...) -- Extended for ETABS
int GetAssignments(string Name, ref int NumberItems, ref int[] ObjectType, ref string[] ObjectName)
```
- **ObjectType values**: 1=Point, 2=Frame, 3=Cable, 4=Tendon, 5=Area, 6=Solid, 7=Link

---

## 18. cSelect (SapModel.SelectObj) - 6 Methods

Selection operations for objects.

```
int All(bool Deselect = false)                             -- Select/deselect all objects
int ClearSelection()                                       -- Deselect all
int Group(string Name, bool Deselect = false)              -- Select/deselect by group
int InvertSelection()                                      -- Invert selection
int PreviousSelection()                                    -- Restore previous selection
int GetSelected(ref int NumberItems, ref int[] ObjectType, ref string[] ObjectName) -- Get selected objects
```

---

## 19. cView (SapModel.View) - 2 Methods

View refresh operations.

```
int RefreshView(int Window = 0, bool Zoom = true)          -- Refresh view (0=all windows)
int RefreshWindow(int Window = 0)                          -- Refresh window only
```
- **Python**: `SapModel.View.RefreshView(0, False)` -- Refresh all windows without zoom-to-fit

---

## 20. cStory-Related: cTower, cDiaphragm, cPierLabel, cSpandrelLabel

### cTower (SapModel.Tower) - 8 Methods
```
int AddNewTower(string TowerName, int NumberStories, double TypicalStoryHeight, double BottomStoryHeight)
int AddCopyOfTower(string TowerName, string NewTowerName)
int DeleteTower(string TowerName, bool Associate, string AssocWithTower = "")
int RenameTower(string TowerName, string NewTowerName)
int GetActiveTower(ref string TowerName) / SetActiveTower(string TowerName)
int GetNameList(ref int NumberNames, ref string[] MyName)
int AllowMultipleTowers(bool AllowMultTowers, string RetainedTower = "", bool Combine = true)
```

### cDiaphragm (SapModel.Diaphragm) - 5 Methods
```
int SetDiaphragm(string Name, bool SemiRigid)              -- Add/modify diaphragm
int GetDiaphragm(string Name, ref bool SemiRigid)
int GetNameList(ref int NumberNames, ref string[] MyName)
int ChangeName(string Name, string NewName)
int Delete(string Name)
```

### cPierLabel (SapModel.PierLabel) - 6 Methods
```
int SetPier(string Name)                                   -- Create pier label
int GetPier(string Name)                                   -- Verify pier exists
int GetNameList(ref int NumberNames, ref string[] MyName)
int GetSectionProperties(string Name, ref int NumberStories, ref string[] StoryName, ref double[] AxisAngle, ref int[] NumAreaObj, ...)
int ChangeName / Delete
```

### cSpandrelLabel (SapModel.SpandrelLabel) - 6 Methods
```
int SetSpandrel(string Name, bool IsMultiStory)
int GetSpandrel(string Name, ref bool IsMultiStory)
int GetNameList(ref int NumberNames, ref string[] MyName, ref bool[] IsMultiStory)
int GetSectionProperties(string Name, ref int NumberStories, ref string[] StoryName, ref int[] NumAreaObj, ref int[] NumLineObj, ...)
int ChangeName / Delete
```

---

## 21. Other Design Interfaces

### cDesignCompositeBeam (SapModel.DesignCompositeBeam) - 22 Methods
Same pattern as cDesignSteel: `StartDesign`, `GetCode/SetCode`, `GetResultsAvailable`, `GetSummaryResults`, `GetDesignSection/SetDesignSection`, `GetComboStrength/SetComboStrength`, `GetComboDeflection/SetComboDeflection`, `GetGroup/SetGroup`, `DeleteResults`, `ResetOverwrites`, `SetAutoSelectNull`, `VerifyPassed`, `VerifySections`, `GetTargetDispl/SetTargetDispl`, `GetTargetPeriod/SetTargetPeriod`.

### cDesignCompositeColumn (SapModel.DesignCompositeColumn) - 22 Methods, 3 Properties
Properties: `AISC360_22`, `CSAS16_19`, `Eurocode_4_2004`
Same method pattern as cDesignSteel.

### cDesignConcreteSlab (SapModel.DesignConcreteSlab) - 4 Methods, 2 Properties
```
int StartSlabDesign()
int GetFlexureAndShear(ref string[] StoryName, ref string[] DesignStripName, ref double[] Station, ...)
int GetSummaryResultsFlexureAndShear(...)
int GetSummaryResultsSpanDefinition(...)
```

### cDesignShearWall (SapModel.DesignShearWall) - 6 Methods
```
int GetPierSummaryResults(ref string[] Story, ref string[] PierLabel, ref string[] Station, ref string[] DesignType, ...)
int GetSpandrelSummaryResults(ref string[] Story, ref string[] Spandrel, ...)
int GetRebar(ref string[] AreaObjName, ref string[] StoryName, ref string[] PierLabel, ...)
int GetRebarPrefsPier(int Item, ref string Value)
int GetRebarPrefsSpandrel(int Item, ref string Value)
int SetComboStrength(string Name, bool Selected)
```

### cDesignForces - 5 Methods
```
int BeamDesignForces(string Name, ref int NumberResults, ref string[] FrameName, ref string[] ComboName, ref double[] Station, ref double[] P, ref double[] V2, ref double[] V3, ref double[] T, ref double[] M2, ref double[] M3)
int ColumnDesignForces(...)
int BraceDesignForces(...)
int PierDesignForces(...)
int SpandrelDesignForces(...)
```

### cDesignStrip - 7 Methods
```
int GetDesignStrip / GetDesignStrip_1  -- Get design strip geometry
int GetNameList / GetGUID / SetGUID / ChangeName / Delete
```

---

## 22. Secondary Object Interfaces

### cLinkObj (SapModel.LinkObj) - 22 Methods
```
int AddByCoord(XI, YI, ZI, XJ, YJ, ZJ, ref Name, bool IsSingleJoint, ...)
int AddByPoint(Point1, Point2, ref Name, bool IsSingleJoint = false, ...)
int Count / Delete / ChangeName
int GetNameList / GetNameListOnStory
int GetPoints / GetElm / GetProperty / SetProperty
int GetLocalAxes / SetLocalAxes / GetLocalAxesAdvanced / SetLocalAxesAdvanced
int GetGroupAssign / SetGroupAssign
int GetGUID / SetGUID / GetSelected / SetSelected
int GetTransformationMatrix
```

### cTendonObj (SapModel.TendonObj) - 17 Methods
```
int Count / ChangeName
int GetNameList / GetNameListOnStory
int GetProperty / GetSelected / SetSelected
int GetGroupAssign / SetGroupAssign
int GetTendonGeometry(string Name, ref int NumberPoints, ref double[] X, ref double[] Y, ref double[] Z, ...)
int GetDrawingPoint(...)
int GetNumberStrands(...)
int GetDatumOffset(...)
int GetLoadForceStress_1(...)
int GetLossesDetailed / GetLossesFixed / GetLossesPercent
```

### cGridSys (SapModel.GridSys) - 12 Methods
```
int Count / GetNameList / GetNameTypeList / ChangeName / Delete
int GetGridSys(string Name, ref double x, ref double y, ref double RZ)
int SetGridSys(string Name, double x, double y, double RZ)
int GetGridSys_2(string Name, ref double Xo, ref double Yo, ref double RZ, ref string GridSysType, ref int NumXLines, ref int NumYLines, ...)
int GetGridSysCartesian / GetGridSysCylindrical / GetGridSysType
int GetTransformationMatrix
```

---

## 23. Link/Spring Property Interfaces

### cPropLink (SapModel.PropLink) - 39 Methods
Properties for link elements: Linear, MultiLinear, Damper, Gap, Hook, Rubber Isolator, Friction Isolator, etc.
```
int Count / GetNameList / GetTypeOAPI / ChangeName / Delete
int SetLinear / GetLinear                    -- Linear link
int SetMultiLinearElastic / GetMultiLinearElastic
int SetMultiLinearPlastic / GetMultiLinearPlastic
int SetMultiLinearPoints / GetMultiLinearPoints
int SetDamper / GetDamper / SetDamperBilinear / GetDamperBilinear
int SetDamperFrictionSpring / GetDamperFrictionSpring
int SetGap / GetGap
int SetHook / GetHook
int SetPlasticWen / GetPlasticWen
int SetRubberIsolator / GetRubberIsolator
int SetFrictionIsolator / GetFrictionIsolator
int SetSpringData / GetSpringData
int SetPDelta / GetPDelta
int SetWeightAndMass / GetWeightAndMass
```

### cPropAreaSpring / cPropLineSpring / cPropPointSpring
Spring property definitions for areas, lines, and points. Each has Get/Set/GetNameList/ChangeName/Delete methods.

---

## 24. Rebar and Tendon Property Interfaces

### cPropRebar (SapModel.PropRebar) - 4 Methods
```
int GetNameList(ref int NumberNames, ref string[] MyName)
int GetNameListWithData(ref int NumberNames, ref string[] MyName, ref double[] Areas, ref double[] Diameters)
int GetRebarProps(string Name, ref double Area, ref double Diameter)
int GetRebarPropsWithGUID(string Name, ref double Area, ref double Diameter, ref string MyGUID)
```

### cPropTendon (SapModel.PropTendon) - 6 Methods
```
int Count / GetNameList / ChangeName / Delete
int SetProp(string Name, string MatProp, int ModelingOption, double Area, ...)
int GetProp(string Name, ref string MatProp, ref int ModelingOption, ref double Area, ...)
```

---

## 25. Steel Design Code Interfaces (Pattern: GetOverwrite/SetOverwrite/GetPreference/SetPreference)

All steel design code interfaces follow the same pattern with 4 methods:

```
int GetOverwrite(string Name, int Item, ref double Value, ref bool ProgDet)
int SetOverwrite(string Name, int Item, double Value, eItemType ItemType = eItemType.Objects)
int GetPreference(int Item, ref double Value)
int SetPreference(int Item, double Value)
```

**Available codes**: `cDStEN1993_1_1_2005`, `cDStEN1993_1_1_2022`, `cDStEurocode_3_2005`, `cDStIndian_IS_800_2007`, `cDStItalianNTC2008S`, `cDStItalianNTC2018S`, `cDStNewZealand_NZS3404_97`, `cDStSP16_13330_2011`, `cDStSP16_13330_2017`

Access via: `SapModel.DesignSteel.EN1993_1_1_2005.GetOverwrite(...)` etc.

---

## 26. Element-Level Interfaces (vs Object-Level)

### cLineElm - 16 Methods
Provides element-level (meshed) access to frame elements. Key methods mirror cFrameObj but work on analysis elements:
`Count`, `GetNameList`, `GetObj` (get parent object), `GetPoints`, `GetProperty`, `GetLocalAxes`, `GetModifiers`, `GetReleases`, `GetEndLengthOffset`, `GetInsertionPoint`, `GetMaterialOverwrite`, `GetTCLimits`, `GetTransformationMatrix`, `GetLoadDistributed`, `GetLoadPoint`, `GetLoadTemperature`

### cPointElm - 20 Methods
Element-level point access: `Count`, `GetNameList`, `GetObj`, `GetCoordCartesian`, `GetConnectivity`, `GetConstraint`, `GetLocalAxes`, `GetPatternValue`, `GetRestraint`, `GetSpring`, `GetSpringCoupled`, `IsSpringCoupled`, `GetTransformationMatrix`, `GetLoadForce`, `GetLoadDispl`, `CountConstraint`, `CountLoadForce`, `CountLoadDispl`, `CountRestraint`, `CountSpring`

---

## 27. Utility Interfaces

### cEditFrame (SapModel.EditFrame) - 1 Method
```
int ChangeConnectivity(string Name, string Point1, string Point2)
```

### cEditGeneral (SapModel.EditGeneral) - 1 Method
```
int Move(double DX, double DY, double DZ)  -- Moves selected objects
```

### cFunction (SapModel.Func) - 7 Methods, 2 Properties
```
int Count(int FuncType = 0) / GetNameList / GetTypeOAPI / ChangeName / Delete
int ConvertToUser(string Name)  -- Convert to user-defined function
int GetValues(string Name, ref int NumberItems, ref double[] MyTime, ref double[] Value)
```
Properties: `RS` (response spectrum functions), and additional sub-interfaces.

### cFunctionRS (SapModel.Func.RS) - 4 Methods
Italian NTC response spectrum functions: `GetNTC2008`, `SetNTC2008`, `GetNTC2018`, `SetNTC2018`

### cGenDispl (SapModel.GDispl) - 13 Methods
Generalized displacement definitions: `Add`, `Count`, `GetNameList`, `ChangeName`, `Delete`, `CountPoint`, `DeletePoint`, `GetPoint`, `SetPoint`, `GetTypeGenDispl`, `GetTypeOAPI`, `SetType`, `SetTypeOAPI`

### cOptions (SapModel.Options) - 2 Methods
```
int GetDefaultFunctionFolder(ref string Path)
int SetDefaultFunctionFolder(string Path)
```

### cPropFrameSDShape (SapModel.PropFrame.SDShape) - 13 Methods
Section Designer shapes for user-defined composite sections:
`GetSolidRect`, `GetSolidCircle`, `GetISection`, `GetAngle`, `GetTee`, `GetConcreteTee`, `GetConcreteL`, `GetReinfSingle`, `GetReinfLine`, `GetReinfRectangular`, `GetReinfCircle`, `GetReinfCorner`, `GetReinfEdge`

### cPluginCallback / cPluginContract - Plugin System
For developing ETABS plugins. `cPluginContract.Main(ref SapModel, ref ISapPlugin)` is the entry point.

---

## Quick Reference: Python COM Access Patterns

### Creating and Connecting
```python
import comtypes.client
helper = comtypes.client.CreateObject("ETABSv1.Helper")
helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)
EtabsObject = helper.GetObject("CSI.ETABS.API.ETABSObject")
SapModel = EtabsObject.SapModel
```

### Common Workflow
```python
# Set units
SapModel.SetPresentUnits(14)  # kgf_cm_C

# Define materials
SapModel.PropMaterial.AddMaterial(Name, 2, "User", "User", "User")
SapModel.PropMaterial.SetMPIsotropic("Conc", 2.5e5, 0.2, 1e-5)
SapModel.PropMaterial.SetOConcrete_1("Conc", 250, False, 1, 2, 1, 0.002, 0.005, -0.1, 0, 0)

# Define sections
SapModel.PropFrame.SetRectangle("COL30x30", "Conc", 30, 30)
SapModel.PropFrame.SetRectangle("BM25x50", "Conc", 50, 25)

# Add frame objects
Name = ''
SapModel.FrameObj.AddByCoord(0, 0, 0, 0, 0, 300, Name, "COL30x30")

# Assign loads
SapModel.FrameObj.SetLoadDistributed("B1", "Live", 1, 11, 0, 1, -500, -500)

# Get data via DatabaseTables
TableData = []
ret = SapModel.DatabaseTables.GetTableForDisplayArray("Story Definitions", [], "All", 0, [], 0, TableData)

# Refresh view
SapModel.View.RefreshView(0, False)
```
