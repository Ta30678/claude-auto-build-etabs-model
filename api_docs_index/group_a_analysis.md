# ETABS API Reference - Group A (Analysis, Results, Load Cases, Design Codes)

> Auto-generated from ETABS v22 COM API documentation.
> Access path notation: `SapModel.X.Method()` where X is the sub-object.

---

## Table of Contents

### Core Analysis Interfaces
1. [cAnalysisResults](#1-canalysisresults) - SapModel.Results
2. [cAnalysisResultsSetup](#2-canalysisresultssetup) - SapModel.Results.Setup
3. [cAnalyze](#3-canalyze) - SapModel.Analyze
4. [cAreaElm](#4-careaelm) - SapModel.AreaElm
5. [cAreaObj](#5-careaobj) - SapModel.AreaObj
6. [cAutoSeismic](#6-cautoseismic) - SapModel.AutoSeismic
7. [cCombo](#7-ccombo) - SapModel.RespCombo
8. [cConstraint](#8-cconstraint) - SapModel.ConstraintDef

### Load Case Interfaces
9. [cCaseModalEigen](#9-ccasemodalEigen) - SapModel.LoadCases.ModalEigen
10. [cCaseModalRitz](#10-ccasemodalritz) - SapModel.LoadCases.ModalRitz
11. [cCaseStaticLinear](#11-ccasestaticlinear) - SapModel.LoadCases.StaticLinear
12. [cCaseStaticNonlinear](#12-ccasestaticnonlinear) - SapModel.LoadCases.StaticNonlinear
13. [cCaseStaticNonlinearStaged](#13-ccasestaticnonlinearstaged)
14. [cCaseResponseSpectrum](#14-ccaseresponsespectrum)
15. [Other Load Case Interfaces](#15-other-load-case-interfaces)

### Design Code Interfaces
16. [Concrete Design Codes (cDCo*)](#16-concrete-design-codes)
17. [Composite Column Design (cDCompCol*)](#17-composite-column-design-codes)
18. [Concrete Slab Design (cDConcSlab*)](#18-concrete-slab-design-codes)
19. [Steel Design Codes (cDSt*)](#19-steel-design-codes)

---

## 1. cAnalysisResults
**Access**: `SapModel.Results`

**Description**: Primary interface for extracting analysis results. Provides methods to retrieve forces, displacements, reactions, modal data, story drifts, and more. All result methods follow a common pattern: pass Name + ItemTypeElm, get back arrays of results.

### Properties
- **Setup**: 

### Methods

#### AreaForceShell
- **Purpose**: Reports the area forces for the specified area elements that are assigned 
 shell section properties (not plane or asolid properties). 
 Note that the forces reported are per unit of in-plane length.
- **Signature**: `int AreaForceShell( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] PointElm, string[] LoadCase, string[] StepType, double[] StepNum, double[] F11, double[] F22, double[] F12, double[] FMax, double[] FMin, double[] FAngle, double[] FVM, double[] M11, double[] M22, double[] M12, double[] MMax, double[] MMin, double[] MAngle, double[] V13, double[] V23, double[] VMax, double[] VAngle )`
- **Parameters**: 26 params (see HTML for full details)
  - `Name` (string): The name of an existing area object, area element or group of objects, depending on the value of the ItemTypeElm item
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the area elements correspondi...
  - `NumberResults` (int): The total number of results returned by the program
  - `Obj` (string[]): AddLanguageSpecificTextSet("LSTBCB27CA5_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the area object name associated with each result, if ...
  - ... and 22 more output arrays
- **Returns**: Returns zero if the forces are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/cc92bdd3-f712-d741-1805-4c7c9bbbb2d7.htm`

#### AreaJointForceShell
- **Purpose**: Reports the area joint forces for the point elements 
 at each corner of the specified area elements that have shell-type properties
- **Signature**: `int AreaJointForceShell( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] PointElm, string[] LoadCase, string[] StepType, double[] StepNum, double[] F1, double[] F2, double[] F3, double[] M1, double[] M2, double[] M3 )`
- **Parameters**: 15 params (see HTML for full details)
  - `Name` (string): The name of an existing area object, area element or group of objects, depending on the value of the ItemTypeElm item
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the area elements correspondi...
  - `NumberResults` (int): The total number of results returned by the program
  - `Obj` (string[]): AddLanguageSpecificTextSet("LSTF22BCCA_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the area object name associated with each result, if a...
  - ... and 11 more output arrays
- **Returns**: Returns zero if the forces are successfully recovered, otherwise it returns a nonzero value.
- **Remarks**: See Results for more information.
- **HTML**: `html/e83ea1bd-2d2c-a16d-1f82-230a5507d21d.htm`

#### AreaStrainShell
- **Purpose**: No description
- **Signature**: `int AreaStrainShell( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] obj, string[] elm, string[] PointElm, string[] LoadCase, string[] StepType, double[] StepNum, double[] e11top, double[] e22top, double[] g12top, double[] emaxtop, double[] emintop, double[] eangletop, double[] evmtop, double[] e11bot, double[] e22bot, double[] g12bot, double[] emaxbot, double[] eminbot, double[] eanglebot, double[] evmbot, double[] g13avg, double[] g23avg, double[] gmaxavg, double[] gangleavg )`
- **Parameters**: 27 params (see HTML for full details)
  - `Name` (string): 
  - `ItemTypeElm` (eItemTypeElm): 
  - `NumberResults` (int): 
  - `obj` (string[]): AddLanguageSpecificTextSet("LSTF7FC7A01_7?cpp=&gt;|vb=()|nu=[]");
  - ... and 23 more output arrays
- **HTML**: `html/e3af8854-2722-5c0b-0b64-f89c3bde3ae9.htm`

#### AreaStrainShellLayered
- **Purpose**: No description
- **Signature**: `int AreaStrainShellLayered( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] obj, string[] elm, string[] Layer, int[] IntPtNum, double[] IntPtLoc, string[] PointElm, string[] LoadCase, string[] StepType, double[] StepNum, double[] E11, double[] E22, double[] G12, double[] EMax, double[] EMin, double[] EAngle, double[] EVM, double[] G13avg, double[] G23avg, double[] GMaxavg, double[] GAngleavg )`
- **Parameters**: 23 params (see HTML for full details)
  - `Name` (string): 
  - `ItemTypeElm` (eItemTypeElm): 
  - `NumberResults` (int): 
  - `obj` (string[]): AddLanguageSpecificTextSet("LSTF79B4D03_7?cpp=&gt;|vb=()|nu=[]");
  - ... and 19 more output arrays
- **HTML**: `html/cc09c570-9398-aa93-04e3-a140cb43a56e.htm`

#### AreaStressShell
- **Purpose**: Reports the area stresses for the specified area elements that are assigned shell section properties. 
 Stresses are reported at each point element associated with the area element
- **Signature**: `int AreaStressShell( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] PointElm, string[] LoadCase, string[] StepType, double[] StepNum, double[] S11Top, double[] S22Top, double[] S12Top, double[] SMaxTop, double[] SMinTop, double[] SAngleTop, double[] SVMTop, double[] S11Bot, double[] S22Bot, double[] S12Bot, double[] SMaxBot, double[] SMinBot, double[] SAngleBot, double[] SVMBot, double[] S13Avg, double[] S23Avg, double[] SMaxAvg, double[] SAngleAvg )`
- **Parameters**: 27 params (see HTML for full details)
  - `Name` (string): The name of an existing area object, area element or group of objects, depending on the value of the ItemTypeElm item
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the area elements correspondi...
  - `NumberResults` (int): The total number of results returned by the program
  - `Obj` (string[]): AddLanguageSpecificTextSet("LST92287A83_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the area object name associated with each result, if ...
  - ... and 23 more output arrays
- **Returns**: Returns zero if the stresses are successfully recovered, otherwise it returns a nonzero value.
- **Remarks**: See Results for more information.
- **HTML**: `html/23519273-ad66-603c-48a3-b4bba4a42f89.htm`

#### AreaStressShellLayered
- **Purpose**: Reports the area stresses for the specified area elements that are assigned layered shell section properties
- **Signature**: `int AreaStressShellLayered( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] Layer, int[] IntPtNum, double[] IntPtLoc, string[] PointElm, string[] LoadCase, string[] StepType, double[] StepNum, double[] S11, double[] S22, double[] S12, double[] SMax, double[] SMin, double[] SAngle, double[] SVM, double[] S13Avg, double[] S23Avg, double[] SMaxAvg, double[] SAngleAvg )`
- **Parameters**: 23 params (see HTML for full details)
  - `Name` (string): The name of an existing area object, area element or group of objects, depending on the value of the ItemTypeElm item
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the area elements correspondi...
  - `NumberResults` (int): The total number of results returned by the program
  - `Obj` (string[]): AddLanguageSpecificTextSet("LST3F02C79C_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the area object name associated with each result, if ...
  - ... and 19 more output arrays
- **Returns**: Returns zero if the stresses are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/650241c3-e7c4-f4ab-b291-a264031c3a1a.htm`

#### AssembledJointMass
- **Purpose**: Reports the assembled joint masses for the specified point elements
- **Signature**: `int AssembledJointMass( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] PointElm, double[] U1, double[] U2, double[] U3, double[] R1, double[] R2, double[] R3 )`
- **Parameters**:
  - `Name` (string): The name of an existing point object, point element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the point element corresponding to the point object specified by the Name item....
  - `NumberResults` (int): The total number of results returned by the program.
  - `PointElm` (string[]): AddLanguageSpecificTextSet("LSTE5113990_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the point element name associated with each result
  - `U1` (double[]): AddLanguageSpecificTextSet("LSTE5113990_11?cpp=&gt;|vb=()|nu=[]"); This array contains the translational mass in the point element local 1 direction for each result. [M]
  - `U2` (double[]): AddLanguageSpecificTextSet("LSTE5113990_15?cpp=&gt;|vb=()|nu=[]"); This array contains the translational mass in the point element local 2 direction for each result. [M]
  - `U3` (double[]): AddLanguageSpecificTextSet("LSTE5113990_19?cpp=&gt;|vb=()|nu=[]"); This array contains the translational mass in the point element local 3 direction for each result. [M]
  - `R1` (double[]): AddLanguageSpecificTextSet("LSTE5113990_23?cpp=&gt;|vb=()|nu=[]"); This array contains the rotational mass moment of inertia about the point element local 1 axis for each result. [ML2]
  - `R2` (double[]): AddLanguageSpecificTextSet("LSTE5113990_27?cpp=&gt;|vb=()|nu=[]"); This array contains the rotational mass moment of inertia about the point element local 2 axis for each result. [ML2]
  - `R3` (double[]): AddLanguageSpecificTextSet("LSTE5113990_31?cpp=&gt;|vb=()|nu=[]"); This array contains the rotational mass moment of inertia about the point element local 3 axis for each result. [ML2]
- **Returns**: Returns zero if the masses are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/fc9f1192-cb22-44d9-b8ae-65e824d41f30.htm`

#### AssembledJointMass_1
- **Purpose**: Reports the assembled joint masses for the specified point elements
- **Signature**: `int AssembledJointMass_1( string MassSourceName, string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] PointElm, string[] MassSource, double[] U1, double[] U2, double[] U3, double[] R1, double[] R2, double[] R3 )`
- **Parameters**: 12 params (see HTML for full details)
  - `MassSourceName` (string): The name of an existing mass source definition. If this value is left empty or unrecognized, data for all mass sources will be returned.
  - `Name` (string): The name of an existing point object, point element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the point element correspondi...
  - `NumberResults` (int): The total number of results returned by the program.
  - ... and 8 more output arrays
- **Returns**: Returns zero if the masses are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/87cf0f6a-b145-4788-620b-4b5e0d377ef0.htm`

#### BaseReact
- **Purpose**: Reports the structure total base reactions
- **Signature**: `int BaseReact( int NumberResults, string[] LoadCase, string[] StepType, double[] StepNum, double[] FX, double[] FY, double[] FZ, double[] MX, double[] ParamMy, double[] MZ, double GX, double GY, double GZ )`
- **Parameters**: 13 params (see HTML for full details)
  - `NumberResults` (int): The total number of results returned by the program
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LSTAE68B025_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the analysis case or load combination ass...
  - `StepType` (string[]): AddLanguageSpecificTextSet("LSTAE68B025_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step type, if any, for each result
  - `StepNum` (double[]): AddLanguageSpecificTextSet("LSTAE68B025_13?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step number, if any, for each result
  - ... and 9 more output arrays
- **Returns**: Returns zero if the reactions are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/b1254c38-a9f8-0f7b-3aa4-e7bde8a96e3a.htm`

#### BaseReactWithCentroid
- **Purpose**: Reports the structure total base reactions and includes information on the centroid of the translational reaction forces
- **Signature**: `int BaseReactWithCentroid( int NumberResults, string[] LoadCase, string[] StepType, double[] StepNum, double[] FX, double[] FY, double[] FZ, double[] MX, double[] ParamMy, double[] MZ, double GX, double GY, double GZ, double[] XCentroidForFX, double[] YCentroidForFX, double[] ZCentroidForFX, double[] XCentroidForFY, double[] YCentroidForFY, double[] ZCentroidForFY, double[] XCentroidForFZ, double[] YCentroidForFZ, double[] ZCentroidForFZ )`
- **Parameters**: 22 params (see HTML for full details)
  - `NumberResults` (int): The total number of results returned by the program
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LST323958BB_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the analysis case or load combination ass...
  - `StepType` (string[]): AddLanguageSpecificTextSet("LST323958BB_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step type, if any, for each result
  - `StepNum` (double[]): AddLanguageSpecificTextSet("LST323958BB_13?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step number, if any, for each result
  - ... and 18 more output arrays
- **Returns**: Returns zero if the reactions are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information. Note that the reported base reaction centroids are not the same as the centroid of the applied loads
- **HTML**: `html/e2cbc77a-9631-e2bc-b6ad-83d31c727360.htm`

#### BucklingFactor
- **Purpose**: Reports buckling factors obtained from buckling load cases
- **Signature**: `int BucklingFactor( int NumberResults, string[] LoadCase, string[] StepType, double[] StepNum, double[] Factor )`
- **Parameters**:
  - `NumberResults` (int): The total number of results returned by the program
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LSTF34E86BD_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the analysis case or load combination associated with each result
  - `StepType` (string[]): AddLanguageSpecificTextSet("LSTF34E86BD_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step type for each result. For buckling factors, the step type is always Mode
  - `StepNum` (double[]): AddLanguageSpecificTextSet("LSTF34E86BD_13?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step number for each result. For buckling factors, the step number is always the buckling mode num...
  - `Factor` (double[]): AddLanguageSpecificTextSet("LSTF34E86BD_17?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the buckling factors
- **Returns**: Returns zero if the factors are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/4c601f77-172b-00c9-8ac2-bd528c32a3ff.htm`

#### FrameForce
- **Purpose**: Reports the frame forces for the specified line elements
- **Signature**: `int FrameForce( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, double[] ObjSta, string[] Elm, double[] ElmSta, string[] LoadCase, string[] StepType, double[] StepNum, double[] P, double[] V2, double[] V3, double[] T, double[] M2, double[] M3 )`
- **Parameters**: 16 params (see HTML for full details)
  - `Name` (string): The name of an existing line object, line element or group of objects, depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the line elements correspondi...
  - `NumberResults` (int): The total number of results returned by the program
  - `Obj` (string[]): AddLanguageSpecificTextSet("LSTE88ADBAD_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the line object name associated with each result, if ...
  - ... and 12 more output arrays
- **Returns**: Returns zero if the forces are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/5efb0061-e25c-363c-1191-6fb001f48978.htm`

#### FrameJointForce
- **Purpose**: Reports the frame joint forces for the point elements at each end of the specified line elements
- **Signature**: `int FrameJointForce( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] PointElm, string[] LoadCase, string[] StepType, double[] StepNum, double[] F1, double[] F2, double[] F3, double[] M1, double[] M2, double[] M3 )`
- **Parameters**: 15 params (see HTML for full details)
  - `Name` (string): The name of an existing line object, line element or group of objects, depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the line elements correspondi...
  - `NumberResults` (int): The total number of results returned by the program
  - `Obj` (string[]): AddLanguageSpecificTextSet("LST8AF6F3DC_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the line object name associated with each result, if ...
  - ... and 11 more output arrays
- **Returns**: Returns zero if the forces are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/548786a1-f0ec-a2d0-a63f-006270f14a2a.htm`

#### GeneralizedDispl
- **Purpose**: Reports the displacement values for the specified generalized displacements
- **Signature**: `int GeneralizedDispl( string Name, int NumberResults, string[] GD, string[] LoadCase, string[] StepType, double[] StepNum, string[] DType, double[] Value )`
- **Parameters**:
  - `Name` (string): The name of an existing generalized displacement for which results are returned. If the program does not recognize this name as a defined generalized displacement, it returns results for all selected ...
  - `NumberResults` (int): The total number of results returned by the program
  - `GD` (string[]): AddLanguageSpecificTextSet("LST95D3B2B2_6?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the generalized displacement name associated with each result
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LST95D3B2B2_10?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the analysis case or load combination associated with each result
  - `StepType` (string[]): AddLanguageSpecificTextSet("LST95D3B2B2_14?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step type, if any, for each result
  - `StepNum` (double[]): AddLanguageSpecificTextSet("LST95D3B2B2_18?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step number, if any, for each result
  - `DType` (string[]): AddLanguageSpecificTextSet("LST95D3B2B2_22?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the generalized displacement type for each result. It is either Translation or Rotation
  - `Value` (double[]): AddLanguageSpecificTextSet("LST95D3B2B2_26?cpp=&gt;|vb=()|nu=[]"); This is an array of the generalized displacement values for each result. [L] when DType is Translation , [rad] when DType is Rotation
- **Returns**: Returns zero if the displacements are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/519448d1-d939-0e13-78b6-277524f006d3.htm`

#### JointAcc
- **Purpose**: Reports the joint accelerations for the specified point elements. 
 The accelerations reported by this function are relative accelerations.
- **Signature**: `int JointAcc( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] LoadCase, string[] StepType, double[] StepNum, double[] U1, double[] U2, double[] U3, double[] R1, double[] R2, double[] R3 )`
- **Parameters**: 14 params (see HTML for full details)
  - `Name` (string): The name of an existing point object, point element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the point element correspondi...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Obj` (string[]): AddLanguageSpecificTextSet("LST3AA45527_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the point object name associated with each result, if...
  - ... and 10 more output arrays
- **Returns**: Returns zero if the accelerations are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/ec67238a-c59c-b8ca-6173-0abc1d78bd3a.htm`

#### JointAccAbs
- **Purpose**: Reports the joint absolute accelerations for the specified point elements. 
 Absolute and relative accelerations are the same, except when reported for time history load cases 
 subjected to acceleration loading
- **Signature**: `int JointAccAbs( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] LoadCase, string[] StepType, double[] StepNum, double[] U1, double[] U2, double[] U3, double[] R1, double[] R2, double[] R3 )`
- **Parameters**: 14 params (see HTML for full details)
  - `Name` (string): The name of an existing point object, point element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the point element correspondi...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Obj` (string[]): AddLanguageSpecificTextSet("LST3C11481C_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the point object name associated with each result, if...
  - ... and 10 more output arrays
- **Returns**: Returns zero if the accelerations are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/ef3a4790-6beb-f608-92cf-95ebcfdfcaad.htm`

#### JointDispl
- **Purpose**: Reports the joint displacements for the specified point elements. 
 The displacements reported by this function are relative displacements
- **Signature**: `int JointDispl( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] LoadCase, string[] StepType, double[] StepNum, double[] U1, double[] U2, double[] U3, double[] R1, double[] R2, double[] R3 )`
- **Parameters**: 14 params (see HTML for full details)
  - `Name` (string): The name of an existing point object, point element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the point element correspondi...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Obj` (string[]): AddLanguageSpecificTextSet("LSTF7776B28_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the point object name associated with each result, if...
  - ... and 10 more output arrays
- **Returns**: Returns zero if the displacements are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/993054d6-91df-b03c-5f1f-79ab0dfce583.htm`

#### JointDisplAbs
- **Purpose**: Reports the absolute joint displacements for the specified point elements. 
 Absolute and relative displacements are the same except when reported for time history load cases 
 subjected to acceleration loading
- **Signature**: `int JointDisplAbs( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] LoadCase, string[] StepType, double[] StepNum, double[] U1, double[] U2, double[] U3, double[] R1, double[] R2, double[] R3 )`
- **Parameters**: 14 params (see HTML for full details)
  - `Name` (string): The name of an existing point object, point element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the point element correspondi...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Obj` (string[]): AddLanguageSpecificTextSet("LSTFAAA6B20_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the point object name associated with each result, if...
  - ... and 10 more output arrays
- **Returns**: Returns zero if the displacements are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/b34d2e86-416a-2fa7-0d85-5dd976de9485.htm`

#### JointDrifts
- **Purpose**: Reports the joint drifts
- **Signature**: `int JointDrifts( int NumberResults, string[] Story, string[] Label, string[] Name, string[] LoadCase, string[] StepType, double[] StepNum, double[] DisplacementX, double[] DisplacementY, double[] DriftX, double[] DriftY )`
- **Parameters**: 11 params (see HTML for full details)
  - `NumberResults` (int): The total number of results returned by the program
  - `Story` (string[]): AddLanguageSpecificTextSet("LSTA0913002_5?cpp=&gt;|vb=()|nu=[]"); This is an array of the story levels associated with each result
  - `Label` (string[]): AddLanguageSpecificTextSet("LSTA0913002_9?cpp=&gt;|vb=()|nu=[]"); This is an array of the point labels for each result
  - `Name` (string[]): AddLanguageSpecificTextSet("LSTA0913002_13?cpp=&gt;|vb=()|nu=[]"); This is an array of the unique point names for each result
  - ... and 7 more output arrays
- **Returns**: Returns zero if the results are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: ReferencecAnalysisResults InterfaceETABSv1 Namespace
- **HTML**: `html/b2807bfa-64f8-514d-c61a-9840d6cd6712.htm`

#### JointReact
- **Purpose**: Reports the joint reactions for the specified point elements. The reactions reported are from
 restraints, springs and grounded (one-joint) links.
- **Signature**: `int JointReact( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] LoadCase, string[] StepType, double[] StepNum, double[] F1, double[] F2, double[] F3, double[] M1, double[] M2, double[] M3 )`
- **Parameters**: 14 params (see HTML for full details)
  - `Name` (string): The name of an existing point object, point element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the point element correspondi...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Obj` (string[]): AddLanguageSpecificTextSet("LST4DDB8F6E_7?cpp=&gt;|vb=()|nu=[]");This is an array that includes the point object name associated with each result, if ...
  - ... and 10 more output arrays
- **Returns**: Returns zero if the reactions are successfully recovered; otherwise it returns a nonzero value.
- **Remarks**: See Results for more information.
- **HTML**: `html/10645966-190c-ff74-46f2-a87da774df65.htm`

#### JointVel
- **Purpose**: Reports the joint velocities for the specified point elements. 
 The velocities reported by this function are relative velocities
- **Signature**: `int JointVel( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] LoadCase, string[] StepType, double[] StepNum, double[] U1, double[] U2, double[] U3, double[] R1, double[] R2, double[] R3 )`
- **Parameters**: 14 params (see HTML for full details)
  - `Name` (string): The name of an existing point object, point element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the point element correspondi...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Obj` (string[]): AddLanguageSpecificTextSet("LSTF88A5226_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the point object name associated with each result, if...
  - ... and 10 more output arrays
- **Returns**: Returns zero if the velocities are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/5fe1fc79-a7a5-20b9-0e10-f15c5e1527c5.htm`

#### JointVelAbs
- **Purpose**: Reports the joint absolute velocities for the specified point elements. 
 Absolute and relative velocities are the same, except when reported for time history load cases 
 subjected to acceleration loading
- **Signature**: `int JointVelAbs( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] LoadCase, string[] StepType, double[] StepNum, double[] U1, double[] U2, double[] U3, double[] R1, double[] R2, double[] R3 )`
- **Parameters**: 14 params (see HTML for full details)
  - `Name` (string): The name of an existing point object, point element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the point element correspondi...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Obj` (string[]): AddLanguageSpecificTextSet("LST634644C5_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the point object name associated with each result, if...
  - ... and 10 more output arrays
- **Returns**: Returns zero if the velocities are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/80dc677c-8a12-6eac-9fde-52aa5a7c73b3.htm`

#### LinkDeformation
- **Purpose**: Reports the link internal deformations
- **Signature**: `int LinkDeformation( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] LoadCase, string[] StepType, double[] StepNum, double[] U1, double[] U2, double[] U3, double[] R1, double[] R2, double[] R3 )`
- **Parameters**: 14 params (see HTML for full details)
  - `Name` (string): The name of an existing link object, link element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the link element correspondin...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Obj` (string[]): AddLanguageSpecificTextSet("LSTD65BD0B8_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the link object name associated with each result, if ...
  - ... and 10 more output arrays
- **Returns**: Returns zero if the deformations are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/f9d1cea0-6835-a029-e1ad-c5cb15cb3646.htm`

#### LinkForce
- **Purpose**: Reports the link forces at the point elements at the ends of the specified link elements
- **Signature**: `int LinkForce( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] PointElm, string[] LoadCase, string[] StepType, double[] StepNum, double[] P, double[] V2, double[] V3, double[] T, double[] M2, double[] M3 )`
- **Parameters**: 15 params (see HTML for full details)
  - `Name` (string): The name of an existing link object, link element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the link element correspondin...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Obj` (string[]): AddLanguageSpecificTextSet("LST24198FA0_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the link object name associated with each result, if ...
  - ... and 11 more output arrays
- **Returns**: Returns zero if the forces are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/d2d21dfe-986f-d503-0684-a464aad70a41.htm`

#### LinkJointForce
- **Purpose**: Reports the joint forces at the point elements at the ends of the specified link elements
- **Signature**: `int LinkJointForce( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] PointElm, string[] LoadCase, string[] StepType, double[] StepNum, double[] F1, double[] F2, double[] F3, double[] M1, double[] M2, double[] M3 )`
- **Parameters**: 15 params (see HTML for full details)
  - `Name` (string): The name of an existing link object, link element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the link element correspondin...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Obj` (string[]): AddLanguageSpecificTextSet("LSTC337E357_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the link object name associated with each result, if ...
  - ... and 11 more output arrays
- **Returns**: Returns zero if the forces are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/9bd1b7db-a41e-e6b8-72de-bcd26f0b3cbb.htm`

#### ModalLoadParticipationRatios
- **Purpose**: Reports the modal load participation ratios for each selected modal analysis case
- **Signature**: `int ModalLoadParticipationRatios( int NumberResults, string[] LoadCase, string[] ItemType, string[] Item, double[] Stat, double[] Dyn )`
- **Parameters**:
  - `NumberResults` (int): The total number of results returned by the program
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LSTB3192730_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the modal load case associated with each result
  - `ItemType` (string[]): AddLanguageSpecificTextSet("LSTB3192730_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes Load Pattern, Acceleration, Link or Panel Zone. It specifies the type of item for which the modal load ...
  - `Item` (string[]): AddLanguageSpecificTextSet("LSTB3192730_13?cpp=&gt;|vb=()|nu=[]"); This is an array whose values depend on the ItemType. If the ItemType is Load Pattern, this is the name of the load pattern. If the I...
  - `Stat` (double[]): AddLanguageSpecificTextSet("LSTB3192730_17?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the percent static load participation ratio
  - `Dyn` (double[]): AddLanguageSpecificTextSet("LSTB3192730_21?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the percent dynamic load participation ratio
- **Returns**: Returns zero if the data is successfully recovered; otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/d4a55aa7-88e9-b9ec-64a2-76d1afa84314.htm`

#### ModalParticipatingMassRatios
- **Purpose**: Reports the modal participating mass ratios for each mode of each selected modal analysis case
- **Signature**: `int ModalParticipatingMassRatios( int NumberResults, string[] LoadCase, string[] StepType, double[] StepNum, double[] Period, double[] UX, double[] UY, double[] UZ, double[] SumUX, double[] SumUY, double[] SumUZ, double[] RX, double[] RY, double[] RZ, double[] SumRX, double[] SumRY, double[] SumRZ )`
- **Parameters**: 17 params (see HTML for full details)
  - `NumberResults` (int): The total number of results returned by the program
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LST9DFC350A_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the modal load case associated with each ...
  - `StepType` (string[]): AddLanguageSpecificTextSet("LST9DFC350A_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step type, if any, for each result. For modal res...
  - `StepNum` (double[]): AddLanguageSpecificTextSet("LST9DFC350A_13?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step number for each result. For modal results, ...
  - ... and 13 more output arrays
- **Returns**: Returns zero if the data is successfully recovered; otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/97d6a0a9-ed2e-ce1c-061b-ea0791157e7b.htm`

#### ModalParticipationFactors
- **Purpose**: Reports the modal participation factors for each mode of each selected modal analysis case
- **Signature**: `int ModalParticipationFactors( int NumberResults, string[] LoadCase, string[] StepType, double[] StepNum, double[] Period, double[] UX, double[] UY, double[] UZ, double[] RX, double[] RY, double[] RZ, double[] ModalMass, double[] ModalStiff )`
- **Parameters**: 13 params (see HTML for full details)
  - `NumberResults` (int): The total number of results returned by the program
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LST7673A124_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the modal load case associated with each ...
  - `StepType` (string[]): AddLanguageSpecificTextSet("LST7673A124_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step type, if any, for each result. For modal res...
  - `StepNum` (double[]): AddLanguageSpecificTextSet("LST7673A124_13?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step number for each result. For modal results, ...
  - ... and 9 more output arrays
- **Returns**: Returns zero if the data is successfully recovered; otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/967c4d0a-8c94-890c-55af-bb4169411ea4.htm`

#### ModalPeriod
- **Purpose**: Reports the modal period, cyclic frequency, circular frequency and eigenvalue for each selected modal load case
- **Signature**: `int ModalPeriod( int NumberResults, string[] LoadCase, string[] StepType, double[] StepNum, double[] Period, double[] Frequency, double[] CircFreq, double[] EigenValue )`
- **Parameters**:
  - `NumberResults` (int): The total number of results returned by the program
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LST2D417329_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the modal load case associated with each result
  - `StepType` (string[]): AddLanguageSpecificTextSet("LST2D417329_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step type, if any, for each result. For modal results, this will always be Mode
  - `StepNum` (double[]): AddLanguageSpecificTextSet("LST2D417329_13?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step number for each result. For modal results, this is always the mode number
  - `Period` (double[]): AddLanguageSpecificTextSet("LST2D417329_17?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the period for each result. [s]
  - `Frequency` (double[]): AddLanguageSpecificTextSet("LST2D417329_21?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the cyclic frequency for each result. [1/s]
  - `CircFreq` (double[]): AddLanguageSpecificTextSet("LST2D417329_25?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the circular frequency for each result. [rad/s]
  - `EigenValue` (double[]): AddLanguageSpecificTextSet("LST2D417329_29?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the eigenvalue for the specified mode for each result. [rad2/s2]
- **Returns**: Returns zero if the data is successfully recovered; otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/c0865d18-6586-a23a-b8dd-f25e132845b2.htm`

#### ModeShape
- **Purpose**: Reports the modal displacements (mode shapes) for the specified point elements
- **Signature**: `int ModeShape( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Obj, string[] Elm, string[] LoadCase, string[] StepType, double[] StepNum, double[] U1, double[] U2, double[] U3, double[] R1, double[] R2, double[] R3 )`
- **Parameters**: 14 params (see HTML for full details)
  - `Name` (string): The name of an existing point object, point element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the point element correspondi...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Obj` (string[]): AddLanguageSpecificTextSet("LST59F47D0D_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the point object name associated with each result, if...
  - ... and 10 more output arrays
- **Returns**: Returns zero if the displacements are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/92a9bfef-a6f8-8252-8097-4b09423e10a7.htm`

#### PanelZoneDeformation
- **Purpose**: Reports the panel zone (link) internal deformations
- **Signature**: `int PanelZoneDeformation( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Elm, string[] LoadCase, string[] StepType, double[] StepNum, double[] U1, double[] U2, double[] U3, double[] R1, double[] R2, double[] R3 )`
- **Parameters**: 13 params (see HTML for full details)
  - `Name` (string): The name of an existing link object, link element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the panel zone (link) element...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Elm` (string[]): AddLanguageSpecificTextSet("LST9394533A_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the panel zone (link) element name associated with ea...
  - ... and 9 more output arrays
- **Returns**: Returns zero if the deformations are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/7a2b313c-fc1d-8ee7-51b6-5872f473f6d5.htm`

#### PanelZoneForce
- **Purpose**: Reports the panel zone (link) forces at the point elements at the ends of the specified panel zone (link) elements
- **Signature**: `int PanelZoneForce( string Name, eItemTypeElm ItemTypeElm, int NumberResults, string[] Elm, string[] PointElm, string[] LoadCase, string[] StepType, double[] StepNum, double[] P, double[] V2, double[] V3, double[] T, double[] M2, double[] M3 )`
- **Parameters**: 14 params (see HTML for full details)
  - `Name` (string): The name of an existing point object, point element, or group of objects depending on the value of the ItemTypeElm item.
  - `ItemTypeElm` (eItemTypeElm): This is one of the following items in the eItemTypeElm enumeration. If this item is ObjectElm, the result request is for the panel zone (link) element...
  - `NumberResults` (int): The total number of results returned by the program.
  - `Elm` (string[]): AddLanguageSpecificTextSet("LST2992F718_7?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the panel zone (link) element name associated with ea...
  - ... and 10 more output arrays
- **Returns**: Returns zero if the forces are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/0d526d7d-7435-16c8-0ccb-13fd534f3458.htm`

#### PierForce
- **Purpose**: Retrieves pier forces for any defined pier objects in the model
- **Signature**: `int PierForce( int NumberResults, string[] StoryName, string[] PierName, string[] LoadCase, string[] Location, double[] P, double[] V2, double[] V3, double[] T, double[] M2, double[] M3 )`
- **Parameters**: 11 params (see HTML for full details)
  - `NumberResults` (int): The total number of results returned by the program
  - `StoryName` (string[]): AddLanguageSpecificTextSet("LST278848F0_5?cpp=&gt;|vb=()|nu=[]"); The story name of the pier object
  - `PierName` (string[]): AddLanguageSpecificTextSet("LST278848F0_9?cpp=&gt;|vb=()|nu=[]"); The name of the pier object
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LST278848F0_13?cpp=&gt;|vb=()|nu=[]"); The names of the load case
  - ... and 7 more output arrays
- **Returns**: Returns zero if the results are successfully retrieved; otherwise returns nonzero
- **Remarks**: ReferencecAnalysisResults InterfaceETABSv1 Namespace
- **HTML**: `html/a724ff58-b1e9-5faa-621d-de7b535c1afe.htm`

#### SectionCutAnalysis
- **Purpose**: Reports the section cut force for sections cuts that are specified to have an Analysis (F1, F2, F3, M1, M2, M3) result type
- **Signature**: `int SectionCutAnalysis( int NumberResults, string[] SCut, string[] LoadCase, string[] StepType, double[] StepNum, double[] F1, double[] F2, double[] F3, double[] M1, double[] M2, double[] M3 )`
- **Parameters**: 11 params (see HTML for full details)
  - `NumberResults` (int): The number total of results returned by the program
  - `SCut` (string[]): AddLanguageSpecificTextSet("LSTE5A39D7E_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the section cut associated with each resu...
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LSTE5A39D7E_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the analysis case or load combination ass...
  - `StepType` (string[]): AddLanguageSpecificTextSet("LSTE5A39D7E_13?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step type, if any, for each result.
  - ... and 7 more output arrays
- **Returns**: Returns zero if the section cut forces are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/c10bd12f-ed43-cb2b-4fc9-95922251b017.htm`

#### SectionCutDesign
- **Purpose**: Reports the section cut force for sections cuts that are specified to have a Design (P, V2, V3, T, M2, M3) result type
- **Signature**: `int SectionCutDesign( int NumberResults, string[] SCut, string[] LoadCase, string[] StepType, double[] StepNum, double[] P, double[] V2, double[] V3, double[] T, double[] M2, double[] M3 )`
- **Parameters**: 11 params (see HTML for full details)
  - `NumberResults` (int): The number total of results returned by the program
  - `SCut` (string[]): AddLanguageSpecificTextSet("LST9377EF91_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the section cut associated with each resu...
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LST9377EF91_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the analysis case or load combination ass...
  - `StepType` (string[]): AddLanguageSpecificTextSet("LST9377EF91_13?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the step type, if any, for each result.
  - ... and 7 more output arrays
- **Returns**: Returns zero if the section cut forces are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: See Results for more information.
- **HTML**: `html/f0710aaf-08b4-6dfc-2c67-29b27bb9acbb.htm`

#### SpandrelForce
- **Purpose**: Retrieves spandrel forces for any defined spandrel objects in the model
- **Signature**: `int SpandrelForce( int NumberResults, string[] StoryName, string[] SpandrelName, string[] LoadCase, string[] Location, double[] P, double[] V2, double[] V3, double[] T, double[] M2, double[] M3 )`
- **Parameters**: 11 params (see HTML for full details)
  - `NumberResults` (int): The total number of results returned by the program
  - `StoryName` (string[]): AddLanguageSpecificTextSet("LST32059737_5?cpp=&gt;|vb=()|nu=[]"); The story name of the spandrel object
  - `SpandrelName` (string[]): AddLanguageSpecificTextSet("LST32059737_9?cpp=&gt;|vb=()|nu=[]"); The name of the spandrel object
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LST32059737_13?cpp=&gt;|vb=()|nu=[]"); The names of the load case
  - ... and 7 more output arrays
- **Returns**: Returns zero if the results are successfully retrieved; otherwise returns nonzero
- **Remarks**: ReferencecAnalysisResults InterfaceETABSv1 Namespace
- **HTML**: `html/67d2885e-e75b-b11b-8e2b-6912d697c336.htm`

#### StoryDrifts
- **Purpose**: Reports the story drifts
- **Signature**: `int StoryDrifts( int NumberResults, string[] Story, string[] LoadCase, string[] StepType, double[] StepNum, string[] Direction, double[] Drift, string[] Label, double[] X, double[] Y, double[] Z )`
- **Parameters**: 11 params (see HTML for full details)
  - `NumberResults` (int): The total number of results returned by the program
  - `Story` (int): AddLanguageSpecificTextSet("LST7E4EFB4_5?cpp=&gt;|vb=()|nu=[]"); This is an array of the story levels for each result
  - `LoadCase` (string[]): AddLanguageSpecificTextSet("LST7E4EFB4_9?cpp=&gt;|vb=()|nu=[]"); This is an array of the names of the analysis case or load combination associated wit...
  - `StepType` (string[]): AddLanguageSpecificTextSet("LST7E4EFB4_13?cpp=&gt;|vb=()|nu=[]"); This is an array of the step types, if any, for each result
  - ... and 7 more output arrays
- **Returns**: Returns zero if the results are successfully recovered, otherwise it returns a nonzero value
- **Remarks**: ReferencecAnalysisResults InterfaceETABSv1 Namespace
- **HTML**: `html/34ebac17-0e58-0071-0ec1-81f3b572cf75.htm`

---

## 2. cAnalysisResultsSetup
**Access**: `SapModel.Results.Setup`

**Description**: Configures which load cases/combos are selected for output, and sets result output options (envelopes, step-by-step, etc.). Must be configured before calling result extraction methods.

### Methods

#### DeselectAllCasesAndCombosForOutput
- **Purpose**: Deselects all load cases and response combinations for output.
- **Signature**: `int DeselectAllCasesAndCombosForOutput()`
- **Returns**: Returns zero if the cases and combos are successfully deselected; otherwise it returns a nonzero value.
- **HTML**: `html/59e98a30-56bc-d6b7-00ff-e622b8f38224.htm`

#### GetCaseSelectedForOutput
- **Purpose**: Checks if a load case is selected for output.
- **Signature**: `int GetCaseSelectedForOutput( string Name, bool Selected )`
- **Parameters**:
  - `Name` (string): The name of an existing load case.
  - `Selected` (bool): This item is True if the specified load case is to be selected for output, otherwise it is False.
- **Returns**: Returns zero if the selected flag is successfully retrieved; otherwise it returns nonzero.
- **HTML**: `html/76ee3052-9f18-fd0a-368c-828ff880318d.htm`

#### GetComboSelectedForOutput
- **Purpose**: Checks if a load combination is selected for output
- **Signature**: `int GetComboSelectedForOutput( string Name, bool Selected )`
- **Parameters**:
  - `Name` (string): The name of an existing load combination
  - `Selected` (bool): This item is True if the specified load combination is selected for output
- **Returns**: Returns 0 if the selected flag is successfully retrieved, otherwise it returns nonzero
- **HTML**: `html/a079962d-9455-ecc8-6667-f8bc6bf40317.htm`

#### GetOptionBaseReactLoc
- **Purpose**: Retrieves the global coordinates of the location at which the base reactions are reported
- **Signature**: `int GetOptionBaseReactLoc( double GX, double GY, double GZ )`
- **Parameters**:
  - `GX` (double): The global X coordinate of the location at which the base reactions are reported
  - `GY` (double): The global Y coordinate of the location at which the base reactions are reported
  - `GZ` (double): The global Z coordinate of the location at which the base reactions are reported
- **Returns**: Returns zero if the coordinates are successfully retrieved, otherwise it returns nonzero
- **HTML**: `html/13d5546b-9997-5097-0f36-4c20eb88a54b.htm`

#### GetOptionBucklingMode
- **Purpose**: No description
- **Signature**: `int GetOptionBucklingMode( int BuckModeStart, int BuckModeEnd, bool BuckModeAll )`
- **Parameters**:
  - `BuckModeStart` (int): 
  - `BuckModeEnd` (int): 
  - `BuckModeAll` (bool): 
- **HTML**: `html/cc52d5f2-f222-4442-5e84-58393d112a8d.htm`

#### GetOptionDirectHist
- **Purpose**: Retrieves the output option for direct history results.
- **Signature**: `int GetOptionDirectHist( int Value )`
- **Parameters**:
  - `Value` (int): This item is 1, 2 or 3 EnvelopesStep-by-StepLast Step
- **Returns**: Returns zero if the output option is successfully retrieved, otherwise it returns nonzero.
- **HTML**: `html/a6f3b13b-1c0d-f8d4-2050-92365655df5d.htm`

#### GetOptionModalHist
- **Purpose**: Retrieves the output option for modal history results.
- **Signature**: `int GetOptionModalHist( int Value )`
- **Parameters**:
  - `Value` (int): This item is 1, 2 or 3 EnvelopesStep-by-StepLast Step
- **Returns**: Returns zero if the output option is successfully retrieved, otherwise it returns nonzero.
- **HTML**: `html/503e9679-30d3-0826-6505-c08bd9a2f2f8.htm`

#### GetOptionModeShape
- **Purpose**: No description
- **Signature**: `int GetOptionModeShape( int ModeShapeStart, int ModeShapeEnd, bool ModeShapesAll )`
- **Parameters**:
  - `ModeShapeStart` (int): 
  - `ModeShapeEnd` (int): 
  - `ModeShapesAll` (bool): 
- **HTML**: `html/fc4249b0-7abc-6a81-a81d-b6f34233b0ec.htm`

#### GetOptionMultiStepStatic
- **Purpose**: No description
- **Signature**: `int GetOptionMultiStepStatic( int Value )`
- **Parameters**:
  - `Value` (int): 
- **HTML**: `html/59a5a183-5d00-3734-2c6a-a82516839872.htm`

#### GetOptionMultiValuedCombo
- **Purpose**: No description
- **Signature**: `int GetOptionMultiValuedCombo( int Value )`
- **Parameters**:
  - `Value` (int): 
- **HTML**: `html/2e7a93d5-4dd6-7b49-8825-47a8dafa1fc1.htm`

#### GetOptionNLStatic
- **Purpose**: No description
- **Signature**: `int GetOptionNLStatic( int Value )`
- **Parameters**:
  - `Value` (int): 
- **HTML**: `html/c860a7a1-9ebb-e0c5-249a-ae3c4e88f208.htm`

#### SetCaseSelectedForOutput
- **Purpose**: Sets a load case selected for output flag.
- **Signature**: `int SetCaseSelectedForOutput( string Name, bool Selected = true )`
- **Parameters**:
  - `Name` (string): The name of an existing load case.
- **Returns**: Returns zero if the selected flag is successfully set; otherwise it returns nonzero.
- **HTML**: `html/9a897e48-fbcd-d8cc-90f3-8aab80ae0e51.htm`

#### SetComboSelectedForOutput
- **Purpose**: Sets a load combination selected for output flag
- **Signature**: `int SetComboSelectedForOutput( string Name, bool Selected = true )`
- **Parameters**:
  - `Name` (string): The name of an existing load combination
- **Returns**: Returns 0 if the selected flag is successfully set, otherwise it returns nonzero
- **Remarks**: ReferencecAnalysisResultsSetup InterfaceETABSv1 Namespace
- **HTML**: `html/50252dbb-7c20-eee8-ac7f-a58d8d50a695.htm`

#### SetOptionBaseReactLoc
- **Purpose**: No description
- **Signature**: `int SetOptionBaseReactLoc( double GX, double GY, double GZ )`
- **Parameters**:
  - `GX` (double): 
  - `GY` (double): 
  - `GZ` (double): 
- **HTML**: `html/e97dc297-8881-1400-795c-8a3dcd4250c8.htm`

#### SetOptionBucklingMode
- **Purpose**: No description
- **Signature**: `int SetOptionBucklingMode( int BuckModeStart, int BuckModeEnd, bool BuckModeAll = false )`
- **Parameters**:
  - `BuckModeStart` (int): 
  - `BuckModeEnd` (int): 
- **HTML**: `html/4e7ecd46-19ce-4334-33c9-ce00fec190f8.htm`

#### SetOptionDirectHist
- **Purpose**: No description
- **Signature**: `int SetOptionDirectHist( int Value )`
- **Parameters**:
  - `Value` (int): 
- **HTML**: `html/18e76e12-b578-e6dd-e1c2-0fc065dcebae.htm`

#### SetOptionModalHist
- **Purpose**: Sets the output option for modal history results.
- **Signature**: `int SetOptionModalHist( int Value )`
- **Parameters**:
  - `Value` (int): This item is 1, 2 or 3 EnvelopesStep-by-StepLast Step
- **Returns**: Returns 0 if the output option is successfully set, otherwise it returns nonzero.
- **Remarks**: ReferencecAnalysisResultsSetup InterfaceETABSv1 Namespace
- **HTML**: `html/0f2ce067-2764-ca48-83ef-4ef8c2e7c0f2.htm`

#### SetOptionModeShape
- **Purpose**: No description
- **Signature**: `int SetOptionModeShape( int ModeShapeStart, int ModeShapeEnd, bool ModeShapesAll = false )`
- **Parameters**:
  - `ModeShapeStart` (int): 
  - `ModeShapeEnd` (int): 
- **HTML**: `html/7e39a7f0-7090-87fc-ad6f-b4c252733246.htm`

#### SetOptionMultiStepStatic
- **Purpose**: No description
- **Signature**: `int SetOptionMultiStepStatic( int Value )`
- **Parameters**:
  - `Value` (int): 
- **HTML**: `html/d11ccc1a-11c1-84a9-ae06-76581f787e44.htm`

#### SetOptionMultiValuedCombo
- **Purpose**: No description
- **Signature**: `int SetOptionMultiValuedCombo( int Value )`
- **Parameters**:
  - `Value` (int): 
- **HTML**: `html/aa1ed7b4-1be1-638e-8050-bc38910a550c.htm`

#### SetOptionNLStatic
- **Purpose**: No description
- **Signature**: `int SetOptionNLStatic( int Value )`
- **Parameters**:
  - `Value` (int): 
- **HTML**: `html/70ee8920-c6e4-ae91-d223-4320b1090ca5.htm`

---

## 3. cAnalyze
**Access**: `SapModel.Analyze`

**Description**: Controls analysis execution, active DOF, solver options, and run case flags. Core workflow: set DOF -> set run flags -> save file -> run analysis.

### Methods

#### CreateAnalysisModel
- **Purpose**: Creates the analysis model. If the analysis model is already created 
 and current, nothing is done.
- **Signature**: `int CreateAnalysisModel()`
- **Returns**: Returns zero if the analysis model is successfully created or it already exists and is current, otherwise it returns a nonzero value.
- **Remarks**: It is not necessary to call this function before running an analysis. The analysis model is automatically created, if necessary, when the model is run.
- **HTML**: `html/4e608741-8192-d3b4-84e3-e6c550a1c2db.htm`

#### DeleteResults
- **Purpose**: Deletes results for load cases.
- **Signature**: `int DeleteResults( string Name, bool All = false )`
- **Parameters**:
  - `Name` (string): The name of an existing load case that is to have its results deleted. This item is ignored when the All item is True.
- **Returns**: Returns zero if the results are successfully deleted; otherwise it returns a nonzero value.
- **HTML**: `html/78802e8a-ceff-bb3b-4f27-a805ef90d148.htm`

#### GetActiveDOF
- **Purpose**: Retrieves the model global degrees of freedom.
- **Signature**: `int GetActiveDOF( bool[] DOF )`
- **Parameters**:
  - `DOF` (bool[]): AddLanguageSpecificTextSet("LST6CDFB02F_3?cpp=&gt;|vb=()|nu=[]");
- **Returns**: Returns zero if the degrees of freedom are successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/95b62dec-d494-53d7-1c3d-5d4b77cc51bf.htm`

#### GetCaseStatus
- **Purpose**: Retrieves the status for all load cases.
- **Signature**: `int GetCaseStatus( int NumberItems, string[] CaseName, int[] Status )`
- **Parameters**:
  - `NumberItems` (int): The number of load cases for which the status is reported.
  - `CaseName` (string[]): AddLanguageSpecificTextSet("LST711F6396_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of each analysis case for which the status is reported.
  - `Status` (int[]): AddLanguageSpecificTextSet("LST711F6396_9?cpp=&gt;|vb=()|nu=[]"); This is an array containing integers from 1 to 4, indicating the load case status. Not runCould not startNot finishedFinished
- **Returns**: Returns zero if the status is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/94fc4a33-5784-228c-62ad-edcc74eaf034.htm`

#### GetDesignResponseOption
- **Purpose**: Retrieves the design and response recovery options.
- **Signature**: `int GetDesignResponseOption( int NumberDesignThreads, int NumberResponseRecoveryThreads, int UseMemoryMappedFilesForResponseRecovery, bool ModelDifferencesOKWhenMergingResults )`
- **Parameters**:
  - `NumberDesignThreads` (int): Number of threads that design can use. Positive if user specified, negative if program determined.
  - `NumberResponseRecoveryThreads` (int): Number of threads that response recovery can use. Positive if user specified, negative if program determined.
  - `UseMemoryMappedFilesForResponseRecovery` (int): Flag for using memory mapped files for response recovery. -2 = Not using memory mapped files (Program Determined).-1 = Not using memory mapped files (user specified).1 = Using memory mapped files (use...
  - `ModelDifferencesOKWhenMergingResults` (bool): Flag for merging results in presence of any model differences. True if results from two models that are not identical are OK to merge, false otherwise.
- **Returns**: Returns zero if the options are successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/5be30001-f29e-f709-abf2-a9ec6ca1b958.htm`

#### GetRunCaseFlag
- **Purpose**: Retrieves the run flags for all analysis cases.
- **Signature**: `int GetRunCaseFlag( int NumberItems, string[] CaseName, bool[] Run )`
- **Parameters**:
  - `NumberItems` (int): The number of load cases for which the run flag is reported.
  - `CaseName` (string[]): AddLanguageSpecificTextSet("LSTCC9B853B_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of each analysis case for which the run flag is reported.
  - `Run` (bool[]): AddLanguageSpecificTextSet("LSTCC9B853B_9?cpp=&gt;|vb=()|nu=[]"); This is an array of boolean values indicating if the specified load case is to be run.
- **Returns**: Returns zero if the flags are successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/b3d6546c-93c6-fc1a-d017-21984aa3bc12.htm`

#### GetSolverOption
- **Purpose**: DEPRECATED. 
 Please see GetSolverOption_2(Int32AddLanguageSpecificTextSet("LST530E329A_1?cpp=%");, Int32AddLanguageSpecificTextSet("LST530E329A_2?cpp=%");, Int32AddLanguageSpecificTextSet("LST530E329A_3?cpp=%");, StringAddLanguageSpecificTextSet("LST530E329A_4?cpp=%");) or GetSolverOption_3(Int32AddLanguageSpecificTextSet("LST530E329A_5?cpp=%");, Int32AddLanguageSpecificTextSet("LST530E329A_6?cpp=%");, Int32AddLanguageSpecificTextSet("LST530E329A_7?cpp=%");, Int32AddLanguageSpecificTextSet("LST530E329A_8?cpp=%");, Int32AddLanguageSpecificTextSet("LST530E329A_9?cpp=%");, StringAddLanguageSpecificTextSet("LST530E329A_10?cpp=%");)
- **Signature**: `int GetSolverOption( int SolverType, bool Force32BitSolver, string StiffCase )`
- **Parameters**:
  - `SolverType` (int): 
  - `Force32BitSolver` (bool): 
  - `StiffCase` (string): 
- **HTML**: `html/64847815-d20b-32b8-42fd-b2dc2e9a126b.htm`

#### GetSolverOption_1
- **Purpose**: DEPRECATED. 
 Please see GetSolverOption_2(Int32AddLanguageSpecificTextSet("LST48EFAFF5_1?cpp=%");, Int32AddLanguageSpecificTextSet("LST48EFAFF5_2?cpp=%");, Int32AddLanguageSpecificTextSet("LST48EFAFF5_3?cpp=%");, StringAddLanguageSpecificTextSet("LST48EFAFF5_4?cpp=%");) or GetSolverOption_3(Int32AddLanguageSpecificTextSet("LST48EFAFF5_5?cpp=%");, Int32AddLanguageSpecificTextSet("LST48EFAFF5_6?cpp=%");, Int32AddLanguageSpecificTextSet("LST48EFAFF5_7?cpp=%");, Int32AddLanguageSpecificTextSet("LST48EFAFF5_8?cpp=%");, Int32AddLanguageSpecificTextSet("LST48EFAFF5_9?cpp=%");, StringAddLanguageSpecificTextSet("LST48EFAFF5_10?cpp=%");)
- **Signature**: `int GetSolverOption_1( int SolverType, int SolverProcessType, bool Force32BitSolver, string StiffCase )`
- **Parameters**:
  - `SolverType` (int): 
  - `SolverProcessType` (int): 
  - `Force32BitSolver` (bool): 
  - `StiffCase` (string): 
- **HTML**: `html/d0def199-7ee4-873f-5016-a1d8a11f7b1f.htm`

#### GetSolverOption_2
- **Purpose**: Retrieves the model solver options.
- **Signature**: `int GetSolverOption_2( int SolverType, int SolverProcessType, int NumberParallelRuns, string StiffCase )`
- **Parameters**:
  - `SolverType` (int): This is 0, 1 or 2, indicating the solver type. 0 = Standard solver1 = Advanced solver2 = Multi-threaded solver
  - `SolverProcessType` (int): This is 0, 1 or 2, indicating the process the analysis is run. 0 = Auto (program determined)1 = GUI process2 = Separate process
  - `NumberParallelRuns` (int): This is an integer not including -1 or 0. Less than -1 = The negative of the program determined value when the assigned value is 0 = Auto parallel (use up to all physical cores - limited by license).1...
  - `StiffCase` (string): The name of the load case used when outputting the mass and stiffness matrices to text files. If this item is blank, no matrices are output.
- **Returns**: Returns zero if the options are successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/f07d0feb-6508-0ec3-b47a-f5186f578689.htm`

#### GetSolverOption_3
- **Purpose**: Retrieves the model solver options.
- **Signature**: `int GetSolverOption_3( int SolverType, int SolverProcessType, int NumberParallelRuns, int ResponseFileSizeMaxMB, int NumberAnalysisThreads, string StiffCase )`
- **Parameters**:
  - `SolverType` (int): This is 0, 1 or 2, indicating the solver type. 0 = Standard solver1 = Advanced solver2 = Multi-threaded solver
  - `SolverProcessType` (int): This is 0, 1 or 2, indicating the process the analysis is run. 0 = Auto (program determined)1 = GUI process2 = Separate process
  - `NumberParallelRuns` (int): This is an integer not including -1 or 0. Less than -1 = The negative of the program determined value when the assigned value is 0 = Auto parallel (use up to all physical cores - limited by license).1...
  - `ResponseFileSizeMaxMB` (int): The maximum size of a response file in MB before a new response file is created. Positive if user specified, negative if program determined.
  - `NumberAnalysisThreads` (int): Number of threads that the analysis can use. Positive if user specified, negative if program determined.
  - `StiffCase` (string): The name of the load case used when outputting the mass and stiffness matrices to text files. If this item is blank, no matrices are output.
- **Returns**: Returns zero if the options are successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/be3d8ebc-bc94-8008-4c90-24bc79442266.htm`

#### MergeAnalysisResults
- **Purpose**: Merges analysis results from a given model.
- **Signature**: `int MergeAnalysisResults( string SourceFileName )`
- **Parameters**:
  - `SourceFileName` (string): Full path to the model file to import results from.
- **Returns**: Returns zero if the results are successfully merged; otherwise it returns a nonzero value.
- **Remarks**: The analysis model is automatically created as part of this function. See “Merging Analysis Results” section in program help file for requirements and limitations. IMPORTANT NOTE: Your model must have a file path defined before merging analysis results. If the model is opened from an existing file, 
- **HTML**: `html/26af0e87-c842-7e4d-a961-4da0a6c10252.htm`

#### ModifyUndeformedGeometry
- **Purpose**: Modifies the undeformed geometry based on displacements obtained from 
 a specified load case
- **Signature**: `int ModifyUndeformedGeometry( string CaseName, double SF, int Stage = -1, bool Original = false )`
- **Parameters**:
  - `CaseName` (string): The name of the static load case from which displacements are obtained.
  - `SF` (double): The scale factor applied to the displacements.
- **Returns**: Returns zero if it is successful; otherwise it returns a nonzero value
- **HTML**: `html/a9bbb6f9-14eb-b4ee-1605-7c12b76194a5.htm`

#### ModifyUndeformedGeometryModeShape
- **Purpose**: Modifies the undeformed geometry based on the shape of a specified mode
- **Signature**: `int ModifyUndeformedGeometryModeShape( string CaseName, int Mode, double MaxDispl, int Direction, bool Original = false )`
- **Parameters**:
  - `CaseName` (string): The name of a load case
  - `Mode` (int): The mode shape
  - `MaxDispl` (double): The maximum displacement to which the mode shape will be scaled
  - `Direction` (int): The direction in which to apply the geometry modification XYZResultant
- **Returns**: Returns zero if it is successful; otherwise it returns a nonzero value
- **HTML**: `html/e3fc25af-bf08-962f-a11a-000ceecb4191.htm`

#### RunAnalysis
- **Purpose**: Runs the analysis.
- **Signature**: `int RunAnalysis()`
- **Returns**: Returns zero if the analysis model is successfully run; otherwise it returns a nonzero value.
- **Remarks**: The analysis model is automatically created as part of this function. IMPORTANT NOTE: Your model must have a file path defined before running the analysis. If the model is opened from an existing file, a file path is defined. If the model is created from scratch, the File.Save function must be calle
- **HTML**: `html/516e7b74-8cb4-af27-31d5-38bb95b3c1d1.htm`

#### SetActiveDOF
- **Purpose**: Sets the model global degrees of freedom.
- **Signature**: `int SetActiveDOF( bool[] DOF )`
- **Parameters**:
  - `DOF` (bool[]): AddLanguageSpecificTextSet("LST284D793B_3?cpp=&gt;|vb=()|nu=[]");
- **Returns**: Returns zero if the degrees of freedom are successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/a4c9b05e-c2cc-364a-7f26-63cc50d098ba.htm`

#### SetDesignResponseOption
- **Purpose**: Sets the design and response recovery options.
- **Signature**: `int SetDesignResponseOption( int NumberDesignThreads, int NumberResponseRecoveryThreads, int UseMemoryMappedFilesForResponseRecovery, bool ModelDifferencesOKWhenMergingResults )`
- **Parameters**:
  - `NumberDesignThreads` (int): Number of threads that design can use. Set to positive for user specified, non-positice for program determined.
  - `NumberResponseRecoveryThreads` (int): Number of threads that response recovery can use. Set to positive for user specified, non-positive for program determined.
  - `UseMemoryMappedFilesForResponseRecovery` (int): Flag for using memory mapped files for response recovery. Set to -1 = Do not use memory mapped files.0 = Program determined.1 = Use memory mapped files.
  - `ModelDifferencesOKWhenMergingResults` (bool): Flag for merging results in presence of any model differences. Set to true to enable merging of results from two models that are not identical, to false otherwise.
- **Returns**: Returns zero if the options are successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/24f58704-0fea-a875-67f9-d1f4d4b68044.htm`

#### SetRunCaseFlag
- **Purpose**: Sets the run flag for load cases.
- **Signature**: `int SetRunCaseFlag( string Name, bool Run, bool All = false )`
- **Parameters**:
  - `Name` (string): The name of an existing load case that is to have its run flag set. This item is ignored when the All item is True.
  - `Run` (bool): If this item is True, the specified load case is to be run.
- **Returns**: Returns zero if the flag is successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/7ff1159c-d38b-1c69-1eaa-a25957f5abe8.htm`

#### SetSolverOption
- **Purpose**: DEPRECATED. 
 Please see SetSolverOption_2(Int32, Int32, Int32, String) or SetSolverOption_3(Int32, Int32, Int32, Int32, Int32, String)
- **Signature**: `int SetSolverOption( int SolverType, bool Force32BitSolver, string StiffCase = "" )`
- **Parameters**:
  - `SolverType` (int): 
  - `Force32BitSolver` (bool): 
- **HTML**: `html/cbc26a3c-b6e6-d05f-494d-9b7b2d2f15bc.htm`

#### SetSolverOption_1
- **Purpose**: DEPRECATED. 
 Please see SetSolverOption_2(Int32, Int32, Int32, String) or SetSolverOption_3(Int32, Int32, Int32, Int32, Int32, String)
- **Signature**: `int SetSolverOption_1( int SolverType, int SolverProcessType, bool Force32BitSolver, string StiffCase = "" )`
- **Parameters**:
  - `SolverType` (int): 
  - `SolverProcessType` (int): 
  - `Force32BitSolver` (bool): 
- **HTML**: `html/e3777e3a-2d74-9045-aeef-e98c78c5f14f.htm`

#### SetSolverOption_2
- **Purpose**: Sets the model solver options.
- **Signature**: `int SetSolverOption_2( int SolverType, int SolverProcessType, int NumberParallelRuns, string StiffCase = "" )`
- **Parameters**:
  - `SolverType` (int): This is 0, 1 or 2, indicating the solver type. 0 = Standard solver1 = Advanced solver2 = Multi-threaded solver
  - `SolverProcessType` (int): This is 0, 1 or 2, indicating the process the analysis is run. 0 = Auto (program determined)1 = GUI process2 = Separate process
  - `NumberParallelRuns` (int): This is an integer not including -1. -Less than -1 = Auto parallel (use up to all physical cores - limited by license). Treated the same as 0.-1 = Illegal value; will return an error0 = Auto parallel ...
- **Returns**: Returns zero if the options are successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/ff5e11c8-9a3f-a8aa-859b-663d8a11804e.htm`

#### SetSolverOption_3
- **Purpose**: Sets the model solver options.
- **Signature**: `int SetSolverOption_3( int SolverType, int SolverProcessType, int NumberParallelRuns, int ResponseFileSizeMaxMB, int NumberAnalysisThreads, string StiffCase = "" )`
- **Parameters**:
  - `SolverType` (int): This is 0, 1 or 2, indicating the solver type. 0 = Standard solver1 = Advanced solver2 = Multi-threaded solver
  - `SolverProcessType` (int): This is 0, 1 or 2, indicating the process the analysis is run. 0 = Auto (program determined)1 = GUI process2 = Separate process
  - `NumberParallelRuns` (int): This is an integer not including -1. Less than -1 = Auto parallel (use up to all physical cores - limited by license). Treated the same as 0.-1 = Illegal value; will return an error0 = Auto parallel (...
  - `ResponseFileSizeMaxMB` (int): The maximum size of a response file in MB before a new response file is created. Non-positive means program determined.
  - `NumberAnalysisThreads` (int): Number of threads that the analysis can use. Non-positive means program determined.
- **Returns**: Returns zero if the options are successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/1c3fbc28-90b1-2cf7-ebad-cce5f53883ba.htm`

---

## 4. cAreaElm
**Access**: `SapModel.AreaElm`

**Description**: Read-only access to area element (analysis model) data. Area elements are created from area objects during analysis. Use for element-level queries after analysis.

### Methods

#### Count
- **Purpose**: No description
- **Signature**: `int Count()`
- **HTML**: `html/3386ce79-de99-2031-38c4-c533e0fe1055.htm`

#### GetLoadTemperature
- **Purpose**: No description
- **Signature**: `int GetLoadTemperature( string Name, int NumberItems, string[] AreaName, string[] LoadPat, int[] MyType, double[] Value, string[] PatternName, eItemTypeElm ItemTypeElm = eItemTypeElm.Element )`
- **Parameters**:
  - `Name` (string): 
  - `NumberItems` (int): 
  - `AreaName` (string[]): AddLanguageSpecificTextSet("LST5556A0EC_6?cpp=&gt;|vb=()|nu=[]");
  - `LoadPat` (string[]): AddLanguageSpecificTextSet("LST5556A0EC_10?cpp=&gt;|vb=()|nu=[]");
  - `MyType` (int[]): AddLanguageSpecificTextSet("LST5556A0EC_14?cpp=&gt;|vb=()|nu=[]");
  - `Value` (double[]): AddLanguageSpecificTextSet("LST5556A0EC_18?cpp=&gt;|vb=()|nu=[]");
  - `PatternName` (string[]): AddLanguageSpecificTextSet("LST5556A0EC_22?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/936908e7-9a69-ae27-82e1-8d1bd50fd83c.htm`

#### GetLoadUniform
- **Purpose**: No description
- **Signature**: `int GetLoadUniform( string Name, int NumberItems, string[] AreaName, string[] LoadPat, string[] CSys, int[] Dir, double[] Value, eItemTypeElm ItemTypeElm = eItemTypeElm.Element )`
- **Parameters**:
  - `Name` (string): 
  - `NumberItems` (int): 
  - `AreaName` (string[]): AddLanguageSpecificTextSet("LSTDBFCBDBD_6?cpp=&gt;|vb=()|nu=[]");
  - `LoadPat` (string[]): AddLanguageSpecificTextSet("LSTDBFCBDBD_10?cpp=&gt;|vb=()|nu=[]");
  - `CSys` (string[]): AddLanguageSpecificTextSet("LSTDBFCBDBD_14?cpp=&gt;|vb=()|nu=[]");
  - `Dir` (int[]): AddLanguageSpecificTextSet("LSTDBFCBDBD_18?cpp=&gt;|vb=()|nu=[]");
  - `Value` (double[]): AddLanguageSpecificTextSet("LSTDBFCBDBD_22?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/a68cab9e-7ce5-9834-b555-8272e9c453d7.htm`

#### GetLocalAxes
- **Purpose**: No description
- **Signature**: `int GetLocalAxes( string Name, double Ang )`
- **Parameters**:
  - `Name` (string): 
  - `Ang` (double): 
- **HTML**: `html/219cafa5-3fbe-822d-64fb-5ee4fd47c16b.htm`

#### GetMaterialOverwrite
- **Purpose**: No description
- **Signature**: `int GetMaterialOverwrite( string Name, string PropName )`
- **Parameters**:
  - `Name` (string): 
  - `PropName` (string): 
- **HTML**: `html/bf62ac17-aa04-b15e-e981-59bd39b6b9bd.htm`

#### GetModifiers
- **Purpose**: No description
- **Signature**: `int GetModifiers( string Name, double[] Value )`
- **Parameters**:
  - `Name` (string): 
  - `Value` (double[]): AddLanguageSpecificTextSet("LST3900F5F1_4?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/b9c837fb-9bd0-7718-10bb-6f3570e79452.htm`

#### GetNameList
- **Purpose**: No description
- **Signature**: `int GetNameList( int NumberNames, string[] MyName )`
- **Parameters**:
  - `NumberNames` (int): 
  - `MyName` (string[]): AddLanguageSpecificTextSet("LST44128A78_5?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/1d7aed8e-8bf9-d709-89b9-74d8bd2a6419.htm`

#### GetObj
- **Purpose**: No description
- **Signature**: `int GetObj( string Name, string Obj )`
- **Parameters**:
  - `Name` (string): 
  - `Obj` (string): 
- **HTML**: `html/d3b6abc1-eded-1b1f-72f5-81d6e419018b.htm`

#### GetOffsets
- **Purpose**: No description
- **Signature**: `int GetOffsets( string Name, int OffsetType, string OffsetPattern, double OffsetPatternSF, double[] Offset )`
- **Parameters**:
  - `Name` (string): 
  - `OffsetType` (int): 
  - `OffsetPattern` (string): 
  - `OffsetPatternSF` (double): 
  - `Offset` (int): AddLanguageSpecificTextSet("LSTE5B6C21E_10?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/ab68d7b3-193c-40b5-5b4e-d54a7fe50f2d.htm`

#### GetPoints
- **Purpose**: No description
- **Signature**: `int GetPoints( string Name, int NumberPoints, string[] Point )`
- **Parameters**:
  - `Name` (string): 
  - `NumberPoints` (int): 
  - `Point` (string[]): AddLanguageSpecificTextSet("LST26D692D8_6?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/95a1c079-a280-a948-f914-0524808565fa.htm`

#### GetProperty
- **Purpose**: No description
- **Signature**: `int GetProperty( string Name, string PropName )`
- **Parameters**:
  - `Name` (string): 
  - `PropName` (string): 
- **HTML**: `html/20bb09b1-ff5f-deff-0c09-357ae2fdd55b.htm`

#### GetThickness
- **Purpose**: No description
- **Signature**: `int GetThickness( string Name, int ThicknessType, string ThicknessPattern, double ThicknessPatternSF, double[] Thickness )`
- **Parameters**:
  - `Name` (string): 
  - `ThicknessType` (int): 
  - `ThicknessPattern` (string): 
  - `ThicknessPatternSF` (double): 
  - `Thickness` (int): AddLanguageSpecificTextSet("LSTB1949E5B_10?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/893716e6-a788-96ad-1b48-3b2ad639a5a8.htm`

#### GetTransformationMatrix
- **Purpose**: No description
- **Signature**: `int GetTransformationMatrix( string Name, double[] Value )`
- **Parameters**:
  - `Name` (string): 
  - `Value` (double[]): AddLanguageSpecificTextSet("LST7E49F76B_4?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/4307a2bb-de1e-c04b-f42a-9b36f6329cdd.htm`

---

## 5. cAreaObj
**Access**: `SapModel.AreaObj`

**Description**: Primary interface for creating and manipulating area objects (slabs, walls, decks, openings). 64 methods covering geometry creation, property assignment, load application, pier/spandrel labels, diaphragm assignment, and queries.

### Methods

#### AddByCoord
- **Purpose**: Adds a new area object, defining points at the specified coordinates.
- **Signature**: `int AddByCoord( int NumberPoints, double[] X, double[] Y, double[] Z, string Name, string PropName = "Default", string UserName = "", string CSys = "Global" )`
- **Parameters**: 5 params
- **Returns**: Returns zero if the area object is successfully added, otherwise it returns a nonzero value.
- **HTML**: `html/71ca5d8f-4d86-1446-4ff7-65dbdf9c08f6.htm`

#### AddByPoint
- **Purpose**: Adds a new area object whose defining points are specified by name.
- **Signature**: `int AddByPoint( int NumberPoints, string[] Point, string Name, string PropName = "Default", string UserName = "" )`
- **Parameters**: 3 params
- **Returns**: Returns zero if the area object is successfully added; otherwise it returns a nonzero value.
- **HTML**: `html/6a404e6a-2795-2581-4a79-2affd4575f71.htm`

#### ChangeName
- **Purpose**: No description
- **Signature**: `int ChangeName( string Name, string NewName )`
- **Parameters**: 2 params
- **HTML**: `html/5a9929b5-e100-ddcf-d8f5-9707861e9783.htm`

#### Count
- **Purpose**: No description
- **Signature**: `int Count()`
- **HTML**: `html/bb5826b4-6eea-b9c5-b920-92fe46ffe295.htm`

#### Delete
- **Purpose**: Deletes area objects.
- **Signature**: `int Delete( string Name, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 1 params
- **Returns**: Returns zero if the area objects are successfully deleted; otherwise it returns a nonzero value.
- **HTML**: `html/a9c44534-4aaa-9e2b-a000-cd6704fd5c64.htm`

#### DeleteLoadTemperature
- **Purpose**: No description
- **Signature**: `int DeleteLoadTemperature( string Name, string LoadPat, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **HTML**: `html/1cd839e0-1578-adc3-d21b-54c7bd3fe615.htm`

#### DeleteLoadUniform
- **Purpose**: Deletes the uniform load assignments to the specified area objects 
 for the specified load pattern.
- **Signature**: `int DeleteLoadUniform( string Name, string LoadPat, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the load assignments are successfully deleted, otherwise it returns a nonzero value.
- **HTML**: `html/7e5c58ca-096c-6128-57a1-ffc15ebabf6d.htm`

#### DeleteLoadUniformToFrame
- **Purpose**: No description
- **Signature**: `int DeleteLoadUniformToFrame( string Name, string LoadPat, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **HTML**: `html/bd4f27fb-70ba-0532-234a-45b0e02dc720.htm`

#### DeleteLoadWindPressure
- **Purpose**: No description
- **Signature**: `int DeleteLoadWindPressure( string Name, string LoadPat, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **HTML**: `html/5709d569-db1e-5230-b3d3-14b8ef2a5932.htm`

#### DeleteMass
- **Purpose**: No description
- **Signature**: `int DeleteMass( string Name, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 1 params
- **HTML**: `html/f2455243-044f-e7b5-ad91-abea49a3cbfa.htm`

#### DeleteModifiers
- **Purpose**: No description
- **Signature**: `int DeleteModifiers( string Name, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 1 params
- **HTML**: `html/e80b1442-9f05-4c4c-3476-c4c5924db9f9.htm`

#### DeleteSpring
- **Purpose**: No description
- **Signature**: `int DeleteSpring( string Name, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 1 params
- **HTML**: `html/8c7cc164-a774-dd0f-e88b-b6047bd10c8a.htm`

#### GetAllAreas
- **Purpose**: Retrieves select data for all area objects in the model
- **Signature**: `int GetAllAreas( int NumberNames, string[] MyName, eAreaDesignOrientation[] DesignOrientation, int NumberBoundaryPts, int[] PointDelimiter, string[] PointNames, double[] PointX, double[] PointY, double[] PointZ )`
- **Parameters**: 9 params
- **Remarks**: ReferencecAreaObj InterfaceETABSv1 Namespace
- **HTML**: `html/f3d7a53a-260c-c290-ab5b-47d49ea40c9d.htm`

#### GetCurvedEdges
- **Purpose**: Retrieves curve data for all edges of an area object
- **Signature**: `int GetCurvedEdges( string Name, int NumEdges, int[] CurveType, double[] Tension, int[] NumPoints, double[] gx, double[] gy, double[] gz )`
- **Parameters**: 8 params
- **Returns**: Returns zero if the data is successfully retrieved, otherwise it returns a nonzero value
- **HTML**: `html/57627146-e5b1-9303-0272-6daf623aaec6.htm`

#### GetDesignOrientation
- **Purpose**: Retrieves the design orientation of an area object.
- **Signature**: `int GetDesignOrientation( string Name, eAreaDesignOrientation DesignOrientation )`
- **Parameters**: 2 params
- **HTML**: `html/b666f884-88f7-3037-8eb7-05b64d8d2460.htm`

#### GetDiaphragm
- **Purpose**: Retrieves the diaphragm assignment to the specified area object
- **Signature**: `int GetDiaphragm( string Name, string DiaphragmName )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the diaphragm is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/de2770ec-9c94-c3e2-d633-3e7a98787fd2.htm`

#### GetEdgeConstraint
- **Purpose**: No description
- **Signature**: `int GetEdgeConstraint( string Name, bool ConstraintExists )`
- **Parameters**: 2 params
- **HTML**: `html/cc997487-53b8-2dfa-b7f9-47b1b1e7119d.htm`

#### GetElm
- **Purpose**: No description
- **Signature**: `int GetElm( string Name, int NElm, string[] Elm )`
- **Parameters**: 3 params
- **HTML**: `html/ee969854-eb6e-b6a8-02c8-c4bb6c66991d.htm`

#### GetGroupAssign
- **Purpose**: Retrieves the groups to which an area object is assigned.
- **Signature**: `int GetGroupAssign( string Name, int NumberGroups, string[] Groups )`
- **Parameters**: 3 params
- **Returns**: Returns zero if the group assignments are successfully retrieved, otherwise it returns a nonzero value.
- **HTML**: `html/8776baf9-d226-ea7f-17ec-cc6d569d220c.htm`

#### GetGUID
- **Purpose**: No description
- **Signature**: `int GetGUID( string Name, string GUID )`
- **Parameters**: 2 params
- **HTML**: `html/ffb6ef94-eb13-970b-8272-87062de64cff.htm`

#### GetLabelFromName
- **Purpose**: Retrieves the label and story for a unique area object name
- **Signature**: `int GetLabelFromName( string Name, string Label, string Story )`
- **Parameters**: 3 params
- **Returns**: Returns zero if the data is successfully retrieved, otherwise it returns nonzero.
- **HTML**: `html/8a01f576-f427-d98e-5e2c-0750f5cc33ee.htm`

#### GetLabelNameList
- **Purpose**: Retrieves the names and labels of all defined area objects.
- **Signature**: `int GetLabelNameList( int NumberNames, string[] MyName, string[] MyLabel, string[] MyStory )`
- **Parameters**: 4 params
- **Returns**: Returns zero if the data is successfully retrieved, otherwise it returns nonzero.
- **HTML**: `html/3dfa558d-3fe7-5770-3396-20d991af442f.htm`

#### GetLoadTemperature
- **Purpose**: Retrieves the temperature load assignments to area objects.
- **Signature**: `int GetLoadTemperature( string Name, int NumberItems, string[] AreaName, string[] LoadPat, int[] MyType, double[] Value, string[] PatternName, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 7 params
- **Returns**: Returns zero if the load assignments are successfully retrieved; otherwise it returns a nonzero value.
- **Remarks**: ReferencecAreaObj InterfaceETABSv1 Namespace
- **HTML**: `html/242cede3-2e07-5344-8264-fb80aee8064e.htm`

#### GetLoadUniform
- **Purpose**: Retrieves the uniform load assignments to area objects.
- **Signature**: `int GetLoadUniform( string Name, int NumberItems, string[] AreaName, string[] LoadPat, string[] CSys, int[] Dir, double[] Value, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 7 params
- **Returns**: Returns zero if the load assignments are successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/f4d14f8a-2e07-8f09-314e-263eed7ac6b3.htm`

#### GetLoadUniformToFrame
- **Purpose**: NOT APPLICABLE - Retrieves the uniform to frame load assignments to area objects.
- **Signature**: `int GetLoadUniformToFrame( string Name, int NumberItems, string[] AreaName, string[] LoadPat, string[] CSys, int[] Dir, double[] Value, int[] DistType, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 8 params
- **Returns**: Returns zero if the load assignments are successfully retrieved; otherwise it returns a nonzero value.
- **Remarks**: ReferencecAreaObj InterfaceETABSv1 Namespace
- **HTML**: `html/968cf2dd-a72d-871e-fbbd-d78483fed1fd.htm`

#### GetLoadWindPressure
- **Purpose**: Retrieves the wind pressure load assignments to area objects.
- **Signature**: `int GetLoadWindPressure( string Name, int NumberItems, string[] AreaName, string[] LoadPat, int[] MyType, double[] Cp, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 6 params
- **Returns**: Returns zero if the load assignments are successfully retrieved; it returns a nonzero value.
- **Remarks**: ReferencecAreaObj InterfaceETABSv1 Namespace
- **HTML**: `html/b57bf34a-aa5a-4a6a-0251-18e6ce2b65be.htm`

#### GetLocalAxes
- **Purpose**: No description
- **Signature**: `int GetLocalAxes( string Name, double Ang, bool Advanced )`
- **Parameters**: 3 params
- **HTML**: `html/e9f531b3-191a-3000-e81f-dcf6f6744bb1.htm`

#### GetMass
- **Purpose**: No description
- **Signature**: `int GetMass( string Name, double MassOverL2 )`
- **Parameters**: 2 params
- **HTML**: `html/5d115da2-1fd2-5426-6915-20291230777b.htm`

#### GetMaterialOverwrite
- **Purpose**: No description
- **Signature**: `int GetMaterialOverwrite( string Name, string PropName )`
- **Parameters**: 2 params
- **HTML**: `html/43c95fc0-4ba7-d784-857b-99a68d0498c3.htm`

#### GetModifiers
- **Purpose**: No description
- **Signature**: `int GetModifiers( string Name, double[] Value )`
- **Parameters**: 2 params
- **HTML**: `html/841eeab5-f16c-06d3-9b6b-fae39c983622.htm`

#### GetNameFromLabel
- **Purpose**: Retrieves the unique name of an area object, given the label and story level
- **Signature**: `int GetNameFromLabel( string Label, string Story, string Name )`
- **Parameters**: 3 params
- **Returns**: Returns zero if the data is successfully retrieved, otherwise it returns nonzero.
- **HTML**: `html/311df7a9-c5c4-deec-252f-fc195e54a721.htm`

#### GetNameList
- **Purpose**: Retrieves the names of all defined area objects.
- **Signature**: `int GetNameList( int NumberNames, string[] MyName )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the names are successfully retrieved, otherwise it returns nonzero.
- **HTML**: `html/dc5d348b-7836-c2a9-b6ef-25c4cf6c312a.htm`

#### GetNameListOnStory
- **Purpose**: Retrieves the names of the defined area objects on a given story.
- **Signature**: `int GetNameListOnStory( string StoryName, int NumberNames, string[] MyName )`
- **Parameters**: 3 params
- **Returns**: Returns zero if the names are successfully retrieved, otherwise it returns nonzero.
- **HTML**: `html/6cc08826-586d-7069-d336-aac9d985cf2c.htm`

#### GetOffsets3
- **Purpose**: No description
- **Signature**: `int GetOffsets3( string Name, int NumberPoints, double[] Offsets )`
- **Parameters**: 3 params
- **HTML**: `html/df102335-11c9-c868-b2f7-c9f78b992cf6.htm`

#### GetOpening
- **Purpose**: Retrieves whether the specified area object is an opening.
- **Signature**: `int GetOpening( string Name, bool IsOpening )`
- **Parameters**: 2 params
- **Returns**: The function returns zero if the assignment is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/67b55aaa-ec09-e7da-4f3e-c23c2e296956.htm`

#### GetPier
- **Purpose**: Retrieves the pier label assignments of an area object
- **Signature**: `int GetPier( string Name, string PierName )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the assignment is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/4a1c04ab-dd28-8548-c880-c47895234adc.htm`

#### GetPoints
- **Purpose**: Retrieves the names of the point objects that define an area object.
- **Signature**: `int GetPoints( string Name, int NumberPoints, string[] Point )`
- **Parameters**: 3 params
- **Returns**: Returns zero if the point object names are successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/82ce0995-7c27-e15e-7ebd-91107c59a20a.htm`

#### GetProperty
- **Purpose**: Retrieves the area property assigned to an area object.
- **Signature**: `int GetProperty( string Name, string PropName )`
- **Parameters**: 2 params
- **HTML**: `html/b7fb5305-2031-436c-2188-12e8de9ec260.htm`

#### GetRebarDataPier
- **Purpose**: Retrieves rebar data for an area pier object
- **Signature**: `int GetRebarDataPier( string Name, int NumberRebarLayers, string[] LayerID, eWallPierRebarLayerType[] LayerType, double[] ClearCover, string[] BarSizeName, double[] BarArea, double[] BarSpacing, int[] NumberBars, bool[] Confined, double[] EndZoneLength, double[] EndZoneThickness, double[] EndZoneOffset )`
- **Parameters**: 13 params
- **Remarks**: ReferencecAreaObj InterfaceETABSv1 Namespace
- **HTML**: `html/49c31649-f9ef-d966-ae4f-205b4cb63c17.htm`

#### GetRebarDataSpandrel
- **Purpose**: Retrieves rebar data for an area spandrel object
- **Signature**: `int GetRebarDataSpandrel( string Name, int NumberRebarLayers, string[] LayerID, eWallSpandrelRebarLayerType[] LayerType, double[] ClearCover, int[] BarSizeIndex, double[] BarArea, double[] BarSpacing, int[] NumberBars, bool[] Confined )`
- **Parameters**: 10 params
- **Remarks**: ReferencecAreaObj InterfaceETABSv1 Namespace
- **HTML**: `html/5111a570-abfa-e500-e7df-daa14679d672.htm`

#### GetSelected
- **Purpose**: No description
- **Signature**: `int GetSelected( string Name, bool Selected )`
- **Parameters**: 2 params
- **HTML**: `html/687a6bb7-9c2c-d3ac-6049-bcbd607c4cab.htm`

#### GetSelectedEdge
- **Purpose**: No description
- **Signature**: `int GetSelectedEdge( string Name, int NumberEdges, bool[] Selected )`
- **Parameters**: 3 params
- **HTML**: `html/97a23f78-51ca-8e02-1c41-78090832050c.htm`

#### GetSpandrel
- **Purpose**: Retrieves the Spandrel label assignments of an area object
- **Signature**: `int GetSpandrel( string Name, string SpandrelName )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the assignment is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/a9235924-2019-efed-6151-cdc77235d922.htm`

#### GetSpringAssignment
- **Purpose**: Retrieves the named area spring property assignment for an area object
- **Signature**: `int GetSpringAssignment( string Name, string SpringProp )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the assignment is successfully retrieved, otherwise it returns a nonzero value
- **HTML**: `html/a0e0b8ca-0cf9-a240-25d9-3176ccb3efa2.htm`

#### GetTransformationMatrix
- **Purpose**: No description
- **Signature**: `int GetTransformationMatrix( string Name, double[] Value, bool IsGlobal = true )`
- **Parameters**: 2 params
- **HTML**: `html/1661c84a-6c48-b705-cfa6-cf7fbe3bf05a.htm`

#### SetDiaphragm
- **Purpose**: Assigns a diaphragm to a specified area object
- **Signature**: `int SetDiaphragm( string Name, string DiaphragmName )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the diaphragm is successfully assigned; otherwise it returns a nonzero value.
- **HTML**: `html/042d1a7d-080b-3f5d-22ef-92e7eefa6dac.htm`

#### SetEdgeConstraint
- **Purpose**: Makes generated edge constraint assignments to area objects.
- **Signature**: `int SetEdgeConstraint( string Name, bool ConstraintExists, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the edge constraint option is successfully assigned; otherwise it returns a nonzero value.
- **HTML**: `html/ccc21efb-1ce3-6330-64e3-5bb958248629.htm`

#### SetGroupAssign
- **Purpose**: No description
- **Signature**: `int SetGroupAssign( string Name, string GroupName, bool Remove = false, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **HTML**: `html/c8b85bd3-0091-4475-a4eb-3f4b1db96641.htm`

#### SetGUID
- **Purpose**: No description
- **Signature**: `int SetGUID( string Name, string GUID = "" )`
- **Parameters**: 1 params
- **HTML**: `html/5f5c48af-66dd-6d13-bfc5-c174e573c98e.htm`

#### SetLoadTemperature
- **Purpose**: No description
- **Signature**: `int SetLoadTemperature( string Name, string LoadPat, int MyType, double Value, string PatternName = "", bool Replace = true, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 4 params
- **HTML**: `html/c7d8dd6e-0404-d30d-6c0a-7f5962a37f91.htm`

#### SetLoadUniform
- **Purpose**: Assigns uniform loads to area objects.
- **Signature**: `int SetLoadUniform( string Name, string LoadPat, double Value, int Dir, bool Replace = true, string CSys = "Global", eItemType ItemType = eItemType.Objects )`
- **Parameters**: 4 params
- **Returns**: Returns zero if the loads are successfully assigned; otherwise it returns a nonzero value.
- **HTML**: `html/447c25fc-5ce3-322e-b34b-2482d2ae9126.htm`

#### SetLoadUniformToFrame
- **Purpose**: NOT APPLICABLE - Assigns uniform to frame load to area objects.
- **Signature**: `int SetLoadUniformToFrame( string Name, string LoadPat, double Value, int Dir, int DistType, bool Replace = true, string CSys = "Global", eItemType ItemType = eItemType.Objects )`
- **Parameters**: 5 params
- **Returns**: Returns zero if the loads are successfully assigned; otherwise it returns a nonzero value.
- **HTML**: `html/7980160a-749b-ae20-20d5-f111b11c946b.htm`

#### SetLoadWindPressure
- **Purpose**: No description
- **Signature**: `int SetLoadWindPressure( string Name, string LoadPat, int MyType, double Cp, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 4 params
- **HTML**: `html/0593a517-720b-6b42-3f0a-70757810c3c4.htm`

#### SetLocalAxes
- **Purpose**: Assigns a local axis angle to area objects.
- **Signature**: `int SetLocalAxes( string Name, double Ang, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the local axis angle is successfully assigned; otherwise it returns a nonzero value.
- **HTML**: `html/a7e5e395-0910-7b29-fbfc-3eb692e27666.htm`

#### SetMass
- **Purpose**: No description
- **Signature**: `int SetMass( string Name, double MassOverL2, bool Replace = false, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **HTML**: `html/7a0bb225-e73f-47c9-e47d-3f2eab7c756a.htm`

#### SetMaterialOverwrite
- **Purpose**: No description
- **Signature**: `int SetMaterialOverwrite( string Name, string PropName, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **HTML**: `html/4e718a9f-1f08-25bb-5334-74cb682a4338.htm`

#### SetModifiers
- **Purpose**: No description
- **Signature**: `int SetModifiers( string Name, double[] Value, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **HTML**: `html/f6ca6db1-2fc2-9d16-cdd9-b59758c628a8.htm`

#### SetOpening
- **Purpose**: Designates an area object(s) as an opening.
- **Signature**: `int SetOpening( string Name, bool IsOpening, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the opening is successfully assigned; otherwise it returns a nonzero value.
- **HTML**: `html/0c885ca6-e280-084d-04eb-833995481056.htm`

#### SetPier
- **Purpose**: Sets the pier label assignment of one or more area objects
- **Signature**: `int SetPier( string Name, string PierName, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the assignment is successful; otherwise it returns a nonzero value.
- **HTML**: `html/74d7d02e-9e30-eaf4-f127-55a7dcc839cc.htm`

#### SetProperty
- **Purpose**: Assigns an area property to area objects.
- **Signature**: `int SetProperty( string Name, string PropName, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the property is successfully assigned; otherwise it returns a nonzero value.
- **HTML**: `html/02c0c7ca-1bab-7787-c5c0-eb1ba791d2e9.htm`

#### SetSelected
- **Purpose**: No description
- **Signature**: `int SetSelected( string Name, bool Selected, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **HTML**: `html/7ab72494-730b-e1b8-3064-d0ddf78cf692.htm`

#### SetSelectedEdge
- **Purpose**: No description
- **Signature**: `int SetSelectedEdge( string Name, int EdgeNum, bool Selected )`
- **Parameters**: 3 params
- **HTML**: `html/9d16276a-fac7-104f-21ec-8e5e1265fbdf.htm`

#### SetSpandrel
- **Purpose**: Sets the Spandrel label assignment of one or more area objects
- **Signature**: `int SetSpandrel( string Name, string SpandrelName, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the assignment is successful; otherwise it returns a nonzero value.
- **HTML**: `html/8132524d-9eea-23d6-7204-a267cbdd0d4d.htm`

#### SetSpringAssignment
- **Purpose**: Assigns an existing named area spring property to area objects
- **Signature**: `int SetSpringAssignment( string Name, string SpringProp, eItemType ItemType = eItemType.Objects )`
- **Parameters**: 2 params
- **Returns**: Returns zero if the property is successfully assigned, otherwise it returns a nonzero value
- **HTML**: `html/31a68107-e914-b7cc-6068-735c4101a64c.htm`

---

## 6. cAutoSeismic
**Access**: `SapModel.AutoSeismic`

**Description**: Get and set automatic seismic load code parameters. Supports ASCE 7-16 and IBC 2006 seismic codes.

### Methods

#### GetASCE716
- **Purpose**: Retrieves auto seismic loading parameters for the 2016 ASCE 7 code
- **Signature**: `int GetASCE716( string Name, bool[] nDir, double Eccen, int PeriodFlag, int CtType, double UserT, bool UserZ, double TopZ, double BottomZ, double R, double Omega, double Cd, double I, double Ss, double S1, double TL, int SiteClass, double Fa, double Fv )`
- **Parameters**: 19 params (see HTML for full details)
  - `Name` (string): The name of an existing Seismic-type load pattern with ASCE 7-16 auto seismic load assignment
  - `nDir` (bool[]): AddLanguageSpecificTextSet("LST1FBBDA56_4?cpp=&gt;|vb=()|nu=[]"); This is an array with 6 inputs that indicates the seismic load directions nDir(1) = ...
  - `Eccen` (double): The eccentricity ratio that applies to all diaphragms
  - `PeriodFlag` (int): This is 1, 2 or 3, indicating the time period option ApproximateProgram calculatedUser defined
  - ... and 15 more output arrays
- **Returns**: returns zero if the function is successfully retrieved; otherwise it returns a nonzero value
- **HTML**: `html/47c131d2-9867-3385-ca4c-798e79f18985.htm`

#### GetASCE716_1
- **Purpose**: Retrieves auto seismic loading parameters for the 2016 ASCE 7 code
- **Signature**: `int GetASCE716_1( string Name, bool[] nDir, double Eccen, int PeriodFlag, int CtType, double UserT, bool UserZ, double TopZ, double BottomZ, double R, double Omega, double Cd, double I, double Ss, double S1, double TL, int SiteClass, double Fa, double Fv )`
- **Parameters**: 19 params (see HTML for full details)
  - `Name` (string): The name of an existing Seismic-type load pattern with ASCE 7-16 auto seismic load assignment
  - `nDir` (bool[]): AddLanguageSpecificTextSet("LST673FF730_4?cpp=&gt;|vb=()|nu=[]"); This is an array with 6 inputs that indicates the seismic load directions nDir(0) = ...
  - `Eccen` (double): The eccentricity ratio that applies to all diaphragms
  - `PeriodFlag` (int): This is 1, 2 or 3, indicating the time period option ApproximateProgram calculatedUser defined
  - ... and 15 more output arrays
- **Returns**: returns zero if the function is successfully retrieved; otherwise it returns a nonzero value
- **HTML**: `html/f060c877-713c-d5ff-8fec-68936d2625bc.htm`

#### GetIBC2006
- **Purpose**: No description
- **Signature**: `int GetIBC2006( string Name, int DirFlag, double Eccen, int PeriodFlag, int CtType, double UserT, bool UserZ, double TopZ, double BottomZ, double R, double Omega, double Cd, double I, int IBC2006Option, double Latitude, double Longitude, string ZipCode, double Ss, double S1, double Tl, int SiteClass, double Fa, double Fv )`
- **Parameters**: 23 params (see HTML for full details)
  - `Name` (string): 
  - `DirFlag` (int): 
  - `Eccen` (double): 
  - `PeriodFlag` (int): 
  - ... and 19 more output arrays
- **HTML**: `html/7c11ed7e-a605-0bdc-a235-2daf28f2abee.htm`

#### SetASCE716
- **Purpose**: Defines auto seismic loading parameters for the 2016 ASCE 7 code
- **Signature**: `int SetASCE716( string Name, bool[] nDir, double Eccen, int PeriodFlag, int CtType, double UserT, bool UserZ, double TopZ, double BottomZ, double R, double Omega, double Cd, double I, double Ss, double S1, double TL, int SiteClass, double Fa, double Fv )`
- **Parameters**: 19 params (see HTML for full details)
  - `Name` (string): The name of an existing Seismic-type load pattern
  - `nDir` (bool[]): AddLanguageSpecificTextSet("LSTD0695138_4?cpp=&gt;|vb=()|nu=[]"); This is an array with 6 inputs that indicates the seismic load directions nDir(1) = ...
  - `Eccen` (double): The eccentricity ratio that applies to all diaphragms
  - `PeriodFlag` (int): This is 1, 2 or 3, indicating the time period option ApproximateProgram calculatedUser defined
  - ... and 15 more output arrays
- **Returns**: returns zero if the function is successfully retrieved; otherwise it returns a nonzero value
- **HTML**: `html/59f6c93d-0ffa-90fc-81a1-6d25344087c3.htm`

#### SetASCE716_1
- **Purpose**: Defines auto seismic loading parameters for the 2016 ASCE 7 code
- **Signature**: `int SetASCE716_1( string Name, bool[] nDir, double Eccen, int PeriodFlag, int CtType, double UserT, bool UserZ, double TopZ, double BottomZ, double R, double Omega, double Cd, double I, double Ss, double S1, double TL, int SiteClass, double Fa, double Fv )`
- **Parameters**: 19 params (see HTML for full details)
  - `Name` (string): The name of an existing Seismic-type load pattern
  - `nDir` (bool[]): AddLanguageSpecificTextSet("LSTBD9D9D74_4?cpp=&gt;|vb=()|nu=[]"); This is an array with 6 inputs that indicates the seismic load directions nDir(0) = ...
  - `Eccen` (double): The eccentricity ratio that applies to all diaphragms
  - `PeriodFlag` (int): This is 1, 2 or 3, indicating the time period option ApproximateProgram calculatedUser defined
  - ... and 15 more output arrays
- **Returns**: returns zero if the function is successfully retrieved; otherwise it returns a nonzero value
- **HTML**: `html/38c53b37-92a1-cb91-e0bb-18a06168850e.htm`

#### SetIBC2006
- **Purpose**: No description
- **Signature**: `int SetIBC2006( string Name, int DirFlag, double Eccen, int PeriodFlag, int CtType, double UserT, bool UserZ, double TopZ, double BottomZ, double R, double Omega, double Cd, double I, int IBC2006Option, double Latitude, double Longitude, string ZipCode, double Ss, double S1, double Tl, int SiteClass, double Fa, double Fv )`
- **Parameters**: 23 params (see HTML for full details)
  - `Name` (string): 
  - `DirFlag` (int): 
  - `Eccen` (double): 
  - `PeriodFlag` (int): 
  - ... and 19 more output arrays
- **HTML**: `html/ecea74c8-8fa2-7dfb-63db-e85b38bba662.htm`

---

## 7. cCombo
**Access**: `SapModel.RespCombo`

**Description**: Create and manage load combinations. Add combos, add cases/combos to combos, get case lists, manage combo types, add design defaults.

### Methods

#### Add
- **Purpose**: Adds a new load combination.
- **Signature**: `int Add( string Name, int ComboType )`
- **Parameters**:
  - `Name` (string): The name of a new load combination.
  - `ComboType` (int): This is 0, 1, 2, 3 or 4 indicating the load combination type. 0 = Linear Additive1 = Envelope2 = Absolute Additive3 = SRSS4 = Range Additive
- **Returns**: Returns zero if the load combination is successfully added, otherwise it returns a nonzero value.
- **Remarks**: The new load combination must have a different name from all other load combinations and all load cases. If the name is not unique, an error will be returned.
- **HTML**: `html/a709a568-c718-34d2-34dd-3733e8d1c557.htm`

#### AddDesignDefaultCombos
- **Purpose**: No description
- **Signature**: `int AddDesignDefaultCombos( bool DesignSteel, bool DesignConcrete, bool DesignAluminum, bool DesignColdFormed )`
- **Parameters**:
  - `DesignSteel` (bool): 
  - `DesignConcrete` (bool): 
  - `DesignAluminum` (bool): 
  - `DesignColdFormed` (bool): 
- **HTML**: `html/8e66f9a6-58b9-f13e-86e3-c75bd2e74701.htm`

#### Delete
- **Purpose**: Deletes the specified load combination.
- **Signature**: `int Delete( string Name )`
- **Parameters**:
  - `Name` (string): The name of an existing load combination.
- **Returns**: Returns zero if the combination is successfully deleted, otherwise it returns a nonzero value.
- **HTML**: `html/72196c83-36bb-5a07-431e-a018f4e0de9a.htm`

#### DeleteCase
- **Purpose**: Deletes one load case or load combination from the list of cases 
 included in the specified load combination.
- **Signature**: `int DeleteCase( string Name, eCNameType CNameType, string CName )`
- **Parameters**:
  - `Name` (string): The name of an existing load combination.
  - `CNameType` (eCNameType): eCNameType This is one of the following items in the eCNameType enumeration: LoadCase = 0LoadCombo = 1 This item indicates whether the CName item is an analysis case (LoadCase) or a load combination (...
  - `CName` (eCNameType): The name of the load case or load combination to be deleted from the specified combination.
- **Returns**: Returns zero if the item is successfully deleted, otherwise it returns a nonzero value.
- **HTML**: `html/f32f05ff-f188-83ad-73fd-4d215c5c3b52.htm`

#### GetCaseList
- **Purpose**: Retrieves all load cases and response combinations included in the 
 load combination specified by the Name item.
- **Signature**: `int GetCaseList( string Name, int NumberItems, eCNameType[] CNameType, string[] CName, double[] SF )`
- **Parameters**:
  - `Name` (string): The name of an existing load combination.
  - `NumberItems` (int): The total number of load cases and load combinations included in the load combination specified by the Name item.
  - `CNameType` (eCNameType[]): eCNameTypeAddLanguageSpecificTextSet("LST11E0ACC2_6?cpp=&gt;|vb=()|nu=[]"); This is one of the following items in the eCNameType enumeration: LoadCase = 0LoadCombo = 1 This item indicates whether the ...
  - `CName` (eCNameType[]): AddLanguageSpecificTextSet("LST11E0ACC2_10?cpp=&gt;|vb=()|nu=[]"); This is an array of the names of the load cases or load combinations included in the load combination specified by the Name item.
  - `SF` (double[]): AddLanguageSpecificTextSet("LST11E0ACC2_14?cpp=&gt;|vb=()|nu=[]"); The scale factor multiplying the case or combination indicated by the CName item.
- **Returns**: Returns zero if the data is successfully retrieved, otherwise it returns a nonzero value.
- **HTML**: `html/b730838d-9040-2b9e-dc16-ea8acac60325.htm`

#### GetCaseList_1
- **Purpose**: Retrieves all load cases and response combinations included in the 
 load combination specified by the Name item.
- **Signature**: `int GetCaseList_1( string Name, int NumberItems, eCNameType[] CNameType, string[] CName, int[] ModeNumber, double[] SF )`
- **Parameters**:
  - `Name` (string): The name of an existing load combination.
  - `NumberItems` (int): The total number of load cases and load combinations included in the load combination specified by the Name item.
  - `CNameType` (eCNameType[]): eCNameTypeAddLanguageSpecificTextSet("LST3F0EF5BE_6?cpp=&gt;|vb=()|nu=[]"); This is one of the following items in the eCNameType enumeration: LoadCase = 0LoadCombo = 1 This item indicates whether the ...
  - `CName` (eCNameType[]): AddLanguageSpecificTextSet("LST3F0EF5BE_10?cpp=&gt;|vb=()|nu=[]"); This is an array of the names of the load cases or load combinations included in the load combination specified by the Name item.
  - `ModeNumber` (int[]): AddLanguageSpecificTextSet("LST3F0EF5BE_14?cpp=&gt;|vb=()|nu=[]"); The mode number for the case indicated by the CName item. This item applies when by the CNameType item is LoadCase and the type of lo...
  - `SF` (double[]): AddLanguageSpecificTextSet("LST3F0EF5BE_18?cpp=&gt;|vb=()|nu=[]"); The scale factor multiplying the case or combination indicated by the CName item.
- **Returns**: Returns zero if the data is successfully retrieved, otherwise it returns a nonzero value.
- **Remarks**: This function supersedes GetCaseList(String, Int32AddLanguageSpecificTextSet("LST3F0EF5BE_20?cpp=%");, AddLanguageSpecificTextSet("LST3F0EF5BE_21?cpp=array&lt;");eCNameTypeAddLanguageSpecificTextSet("LST3F0EF5BE_22?cpp=&gt;|cs=[]|vb=()|nu=[]|fs=[]");AddLanguageSpecificTextSet("LST3F0EF5BE_23?cpp=%")
- **HTML**: `html/bfa3a317-c450-7776-09e9-05f14a2df7f5.htm`

#### GetNameList
- **Purpose**: Retrieves the names of all defined response combinations.
- **Signature**: `int GetNameList( int NumberNames, string[] MyName )`
- **Parameters**:
  - `NumberNames` (int): The number of load combination names retrieved by the program.
  - `MyName` (string[]): AddLanguageSpecificTextSet("LSTC3CDC584_5?cpp=&gt;|vb=()|nu=[]"); This is a one-dimensional array of load combination names. The MyName array is created as a dynamic, zero-based, array by the API user...
- **Returns**: Returns zero if the names are successfully retrieved, otherwise it returns nonzero.
- **HTML**: `html/deb0f8fc-5299-e233-3747-9d051a0a31f8.htm`

#### GetTypeCombo
- **Purpose**: Retrieves the combination type for specified load combination.
- **Signature**: `int GetTypeCombo( string Name, int ComboType )`
- **Parameters**:
  - `Name` (string): The name of an existing load combination.
  - `ComboType` (int): This is 0, 1, 2, 3 or 4 indicating the load combination type. 0 = Linear Additive1 = Envelope2 = Absolute Additive3 = SRSS4 = Range Additive
- **Returns**: Returns zero if the type is successfully retrieved, otherwise it returns a nonzero value.
- **HTML**: `html/f8046636-92a5-0c11-14a1-90bc006c4c7a.htm`

#### GetTypeOAPI
- **Purpose**: No description
- **Signature**: `int GetTypeOAPI( string name, int ComboType )`
- **Parameters**:
  - `name` (string): 
  - `ComboType` (int): 
- **HTML**: `html/a2eb25a7-77f9-f4ff-25af-8ef51f3c06ac.htm`

#### SetCaseList
- **Purpose**: Adds or modifies one load case or response combination in the list of cases 
 included in the load combination specified by the Name item.
- **Signature**: `int SetCaseList( string Name, eCNameType CNameType, string CName, double SF )`
- **Parameters**:
  - `Name` (string): The name of an existing load combination.
  - `CNameType` (eCNameType): eCNameType This is one of the following items in the eCNameType enumeration: LoadCase = 0LoadCombo = 1 This item indicates whether the CName item is an analysis case (LoadCase) or a load combination (...
  - `CName` (eCNameType): The name of the load case or load combination to be added to or modified in the combination specified by the Name item. If the load case or combination already exists in the combination specified by t...
  - `SF` (double): The scale factor multiplying the case or combination indicated by the CName item.
- **Returns**: Returns zero if the item is successfully added or modified, otherwise it returns a nonzero value.
- **HTML**: `html/1e0b79da-c352-43f5-11aa-570a850ea0c0.htm`

#### SetCaseList_1
- **Purpose**: Adds or modifies one load case or response combination in the list of cases 
 included in the load combination specified by the Name item.
- **Signature**: `int SetCaseList_1( string Name, eCNameType CNameType, string CName, int ModeNumber, double SF )`
- **Parameters**:
  - `Name` (string): The name of an existing load combination.
  - `CNameType` (eCNameType): eCNameType This is one of the following items in the eCNameType enumeration: LoadCase = 0LoadCombo = 1 This item indicates whether the CName item is an analysis case (LoadCase) or a load combination (...
  - `CName` (eCNameType): The name of the load case or load combination to be added to or modified in the combination specified by the Name item. If the load case or combination already exists in the combination specified by t...
  - `ModeNumber` (int): The mode number for the case indicated by the CName item. This item applies when by the CNameType item is LoadCase and the type of load case specified by the CName item is either Modal or Buckling. An...
  - `SF` (double): The scale factor multiplying the case or combination indicated by the CName item.
- **Returns**: Returns zero if the item is successfully added or modified, otherwise it returns a nonzero value.
- **Remarks**: This function supersedes SetCaseList(String, eCNameTypeAddLanguageSpecificTextSet("LST6B7F1CE4_7?cpp=%");, String, Double)
- **HTML**: `html/d8916b66-1705-c8be-bcdf-ef1104d4a959.htm`

---

## 8. cConstraint
**Access**: `SapModel.ConstraintDef`

**Description**: Joint constraints interface, primarily for diaphragm constraints in ETABS.

### Methods

#### Delete
- **Purpose**: No description
- **Signature**: `int Delete( string Name )`
- **Parameters**:
  - `Name` (string): 
- **HTML**: `html/6f121d91-7e39-8093-44ef-1c710dd5ace8.htm`

#### GetDiaphragm
- **Purpose**: No description
- **Signature**: `int GetDiaphragm( string Name, eConstraintAxis Axis, string CSys )`
- **Parameters**:
  - `Name` (string): 
  - `Axis` (eConstraintAxis): eConstraintAxis
  - `CSys` (string): 
- **HTML**: `html/77251fb1-8041-f191-1845-45a67c805819.htm`

#### GetNameList
- **Purpose**: No description
- **Signature**: `int GetNameList( int NumberNames, string[] MyName )`
- **Parameters**:
  - `NumberNames` (int): 
  - `MyName` (string[]): AddLanguageSpecificTextSet("LST9D7EA0A0_5?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/e5825611-2ba8-6876-a197-82753ddd3eae.htm`

#### SetDiaphragm
- **Purpose**: DEPRECATED. Defines a Diaphragm constraint.
- **Signature**: `int SetDiaphragm( string Name, eConstraintAxis Axis = eConstraintAxis.AutoAxis, string CSys = "Global" )`
- **Parameters**:
  - `Name` (string): The name of a constraint.
- **Returns**: Returns zero if the constraint data is successfully added or modified, otherwise it returns a nonzero value.
- **Remarks**: This function is DEPRECATED. Please refer to cDiaphragm.
- **HTML**: `html/eff6b91e-6ba0-2c75-f13c-ec51f50d41aa.htm`

---

## 9. cCaseModalEigen
**Access**: `SapModel.LoadCases.ModalEigen`

**Description**: Eigen modal analysis case. Configure number of modes, frequency shift, convergence tolerance, mass source, and initial stiffness from another case.

### Methods

#### GetInitialCase
- **Purpose**: This function retrieves the initial condition assumed for the specified load case.
- **Signature**: `int GetInitialCase( string Name, string InitialCase )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Eigen load case.
  - `InitialCase` (string): This is blank, None, or the name of an existing analysis case. This item specifies if the load case starts from zero initial conditions, that is, an unstressed state, or if it starts using the stiffne...
- **Returns**: Returns zero if the initial condition is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/41d57552-6645-ac71-0edd-42845a5d998e.htm`

#### GetLoads
- **Purpose**: This function retrieves the load data for the specified load case.
- **Signature**: `int GetLoads( string Name, int NumberLoads, string[] LoadType, string[] LoadName, double[] TargetPar, bool[] StaticCorrect )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Eigen load case.
  - `NumberLoads` (int): The number of loads assigned to the specified analysis case.
  - `LoadType` (string[]): AddLanguageSpecificTextSet("LST60DD382A_6?cpp=&gt;|vb=()|nu=[]"); This is an array that includes Load, Accel or Link, indicating the type of each load assigned to the load case.
  - `LoadName` (string[]): AddLanguageSpecificTextSet("LST60DD382A_10?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of each load assigned to the load case. If the LoadType item is Load, this item is the name o...
  - `TargetPar` (double[]): AddLanguageSpecificTextSet("LST60DD382A_14?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the target mass participation ratio.
  - `StaticCorrect` (bool[]): AddLanguageSpecificTextSet("LST60DD382A_18?cpp=&gt;|vb=()|nu=[]"); This is an array that includes either 0 or 1, indicating if static correction modes are to be calculated.
- **Returns**: The function returns zero if the data is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/199c8deb-64b2-af34-18e9-f647266d1807.htm`

#### GetNumberModes
- **Purpose**: This function retrieves the number of modes requested for the specified load case.
- **Signature**: `int GetNumberModes( string Name, int MaxModes, int MinModes )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Eigen load case.
  - `MaxModes` (int): The maximum number of modes requested.
  - `MinModes` (int): The minimum number of modes requested.
- **Returns**: The function returns zero if the number of modes is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/52e23119-6f71-8023-b99e-192fabdc1d62.htm`

#### GetParameters
- **Purpose**: This function retrieves various parameters for the specified load case.
- **Signature**: `int GetParameters( string Name, double EigenShiftFreq, double EigenCutOff, double EigenTol, int AllowAutoFreqShift )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Eigen load case.
  - `EigenShiftFreq` (double): The Eigenvalue shift frequency. [cyc/s]
  - `EigenCutOff` (double): The Eigencutoff frequency radius. [cyc/s]
  - `EigenTol` (double): The relative convergence tolerance for Eigenvalues.
  - `AllowAutoFreqShift` (int): This is either 0 or 1, indicating if automatic frequency shifting is allowed. 0 = Automatic frequency shifting is NOT allowed 1 = Automatic frequency shifting Is allowed
- **Returns**: The function returns zero if the parameters are successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/5a80f41e-dbc7-85bb-e5fd-51f9c3b751d5.htm`

#### SetCase
- **Purpose**: This function initializes a modal Eigen load case. If this function is called for an existing load case, all items for the case are reset to their default value.
- **Signature**: `int SetCase( string Name )`
- **Parameters**:
  - `Name` (string): The name of an existing or new load case. If this is an existing case, that case is modified; otherwise, a new case is added.
- **Returns**: The function returns zero if the load case is successfully initialized; otherwise it returns a nonzero value.
- **HTML**: `html/a8d131ae-b6b5-4d62-8bca-1c81ffd4ccbc.htm`

#### SetInitialCase
- **Purpose**: This function sets the initial condition for the specified load case.
- **Signature**: `int SetInitialCase( string Name, string InitialCase )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Eigen load case.
  - `InitialCase` (string): This is blank, None, or the name of an existing analysis case. This item specifies if the load case starts from zero initial conditions, that is, an unstressed state, or if it starts using the stiffne...
- **Returns**: Returns zero if the initial condition is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/1ebd4652-968f-75de-e5d7-a7bca7838d64.htm`

#### SetLoads
- **Purpose**: This function sets the load data for the specified load case.
- **Signature**: `int SetLoads( string Name, int NumberLoads, string[] LoadType, string[] LoadName, double[] TargetPar, bool[] StaticCorrect )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Eigen load case.
  - `NumberLoads` (int): The number of loads assigned to the specified analysis case.
  - `LoadType` (string[]): AddLanguageSpecificTextSet("LSTA8A01C44_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes Load, Accel or Link, indicating the type of each load assigned to the load case.
  - `LoadName` (string[]): AddLanguageSpecificTextSet("LSTA8A01C44_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of each load assigned to the load case. If the LoadType item is Load, this item is the name of...
  - `TargetPar` (double[]): AddLanguageSpecificTextSet("LSTA8A01C44_13?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the target mass participation ratio.
  - `StaticCorrect` (bool[]): AddLanguageSpecificTextSet("LSTA8A01C44_17?cpp=&gt;|vb=()|nu=[]"); This is an array that includes either 0 or 1, indicating if static correction modes are to be calculated.
- **Returns**: The function returns zero if the data is successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/a5b40286-ea3e-3627-85ff-ad4a260371ca.htm`

#### SetNumberModes
- **Purpose**: This function sets the number of modes requested for the specified load case.
- **Signature**: `int SetNumberModes( string Name, int MaxModes, int MinModes )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Eigen load case.
  - `MaxModes` (int): The maximum number of modes requested.
  - `MinModes` (int): The minimum number of modes requested.
- **Returns**: The function returns zero if the number of modes is successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/db67005d-4dfd-578b-174b-507ac8ca7291.htm`

#### SetParameters
- **Purpose**: This function sets various parameters for the specified load case.
- **Signature**: `int SetParameters( string Name, double EigenShiftFreq, double EigenCutOff, double EigenTol, int AllowAutoFreqShift )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Eigen load case.
  - `EigenShiftFreq` (double): The Eigenvalue shift frequency. [cyc/s]
  - `EigenCutOff` (double): The Eigencutoff frequency radius. [cyc/s]
  - `EigenTol` (double): The relative convergence tolerance for Eigenvalues.
  - `AllowAutoFreqShift` (int): This is either 0 or 1, indicating if automatic frequency shifting is allowed. 0 = Automatic frequency shifting is NOT allowed 1 = Automatic frequency shifting Is allowed
- **Returns**: The function returns zero if the parameters are successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/618a0e83-e694-c99d-7669-3f8cbc80f86f.htm`

---

## 10. cCaseModalRitz
**Access**: `SapModel.LoadCases.ModalRitz`

**Description**: Ritz modal analysis case. Configure starting load vectors, number of modes, and initial stiffness case.

### Methods

#### GetInitialCase
- **Purpose**: This function retrieves the initial condition assumed for the specified load case.
- **Signature**: `int GetInitialCase( string Name, string InitialCase )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Ritz load case.
  - `InitialCase` (string): This is blank, None, or the name of an existing analysis case. This item specifies if the load case starts from zero initial conditions, that is, an unstressed state, or if it starts using the stiffne...
- **Returns**: Returns zero if the initial condition is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/efb9379d-e229-3fcd-8fcd-e7e47b78ad6e.htm`

#### GetLoads
- **Purpose**: This function retrieves the load data for the specified load case.
- **Signature**: `int GetLoads( string Name, int NumberLoads, string[] LoadType, string[] LoadName, int[] RitzMaxCyc, double[] TargetPar )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Ritz load case.
  - `NumberLoads` (int): The number of loads assigned to the specified analysis case.
  - `LoadType` (string[]): AddLanguageSpecificTextSet("LST70B0A51C_6?cpp=&gt;|vb=()|nu=[]"); This is an array that includes Load, Accel or Link, indicating the type of each load assigned to the load case.
  - `LoadName` (string[]): AddLanguageSpecificTextSet("LST70B0A51C_10?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of each load assigned to the load case. If the LoadType item is Load, this item is the name o...
  - `RitzMaxCyc` (int[]): AddLanguageSpecificTextSet("LST70B0A51C_14?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the maximum number of generation cycles to be performed for the specified ritz starting vector. A valu...
  - `TargetPar` (double[]): AddLanguageSpecificTextSet("LST70B0A51C_18?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the target mass participation ratio.
- **Returns**: The function returns zero if the data is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/2c49fe76-6841-5ff1-c738-90b06d729719.htm`

#### GetNumberModes
- **Purpose**: This function retrieves the number of modes requested for the specified load case.
- **Signature**: `int GetNumberModes( string Name, int MaxModes, int MinModes )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Ritz load case.
  - `MaxModes` (int): The maximum number of modes requested.
  - `MinModes` (int): The minimum number of modes requested.
- **Returns**: The function returns zero if the number of modes is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/cf7df130-bf0f-c2d1-b390-b89e5f88f53c.htm`

#### SetCase
- **Purpose**: This function initializes a modal Ritz load case. If this function is called for an existing load case, all items for the case are reset to their default value.
- **Signature**: `int SetCase( string Name )`
- **Parameters**:
  - `Name` (string): The name of an existing or new load case. If this is an existing case, that case is modified; otherwise, a new case is added.
- **Returns**: The function returns zero if the load case is successfully initialized; otherwise it returns a nonzero value.
- **HTML**: `html/6f29c2a3-de59-5e51-67cb-5b77bc79ae97.htm`

#### SetInitialCase
- **Purpose**: This function sets the initial condition for the specified load case.
- **Signature**: `int SetInitialCase( string Name, string InitialCase )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Ritz load case.
  - `InitialCase` (string): This is blank, None, or the name of an existing analysis case. This item specifies if the load case starts from zero initial conditions, that is, an unstressed state, or if it starts using the stiffne...
- **Returns**: Returns zero if the initial condition is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/3310cfea-974e-c2e3-316c-ecf61f1420e8.htm`

#### SetLoads
- **Purpose**: This function sets the load data for the specified load case.
- **Signature**: `int SetLoads( string Name, int NumberLoads, string[] LoadType, string[] LoadName, int[] RitzMaxCyc, double[] TargetPar )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Ritz load case.
  - `NumberLoads` (int): The number of loads assigned to the specified analysis case.
  - `LoadType` (string[]): AddLanguageSpecificTextSet("LST31E06942_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes Load, Accel or Link, indicating the type of each load assigned to the load case.
  - `LoadName` (string[]): AddLanguageSpecificTextSet("LST31E06942_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of each load assigned to the load case. If the LoadType item is Load, this item is the name of...
  - `RitzMaxCyc` (int[]): AddLanguageSpecificTextSet("LST31E06942_13?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the maximum number of generation cycles to be performed for the specified ritz starting vector. A valu...
  - `TargetPar` (double[]): AddLanguageSpecificTextSet("LST31E06942_17?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the target mass participation ratio.
- **Returns**: The function returns zero if the data is successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/128ef1d6-77da-0985-5429-396661797440.htm`

#### SetNumberModes
- **Purpose**: This function sets the number of modes requested for the specified load case.
- **Signature**: `int SetNumberModes( string Name, int MaxModes, int MinModes )`
- **Parameters**:
  - `Name` (string): The name of an existing modal Ritz load case.
  - `MaxModes` (int): The maximum number of modes requested.
  - `MinModes` (int): The minimum number of modes requested.
- **Returns**: The function returns zero if the number of modes is successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/d4146d8b-ce42-c966-eb5f-374327b0d4db.htm`

---

## 11. cCaseStaticLinear
**Access**: `SapModel.LoadCases.StaticLinear`

**Description**: Linear static load case. Configure load patterns with scale factors and initial conditions.

### Methods

#### GetInitialCase
- **Purpose**: Retrieves the initial condition assumed for the specified load case.
- **Signature**: `int GetInitialCase( string Name, string InitialCase )`
- **Parameters**:
  - `Name` (string): The name of an existing static linear load case.
  - `InitialCase` (string): This is blank, None, or the name of an existing analysis case. This item specifies if the load case starts from zero initial conditions, that is, an unstressed state, or if it starts using the stiffne...
- **Returns**: Returns zero if the initial condition is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/f7701fac-9d31-4e45-be6b-57a3ac47745b.htm`

#### GetLoads
- **Purpose**: Retrieves the load data for the specified load case
- **Signature**: `int GetLoads( string Name, int NumberLoads, string[] LoadType, string[] LoadName, double[] SF )`
- **Parameters**:
  - `Name` (string): The name of an existing static linear load case.
  - `NumberLoads` (int): The number of loads assigned to the specified analysis case.
  - `LoadType` (string[]): AddLanguageSpecificTextSet("LST4E7196BC_6?cpp=&gt;|vb=()|nu=[]"); This is an array that includes either Load or Accel, indicating the type of each load assigned to the load case.
  - `LoadName` (string[]): AddLanguageSpecificTextSet("LST4E7196BC_10?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of each load assigned to the load case. If the LoadType item is Load, this item is the name o...
  - `SF` (double[]): AddLanguageSpecificTextSet("LST4E7196BC_14?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the scale factor of each load assigned to the load case. [L/s^2] for Accel UX UY and UZ; otherwise uni...
- **Returns**: Returns zero if the data is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/19a889e9-08f7-22a6-6216-8092541bc6fe.htm`

#### SetCase
- **Purpose**: Initializes a static linear load case.
- **Signature**: `int SetCase( string Name )`
- **Parameters**:
  - `Name` (string): The name of an existing or new load case. If this is an existing case, that case is modified; otherwise, a new case is added.
- **Returns**: Returns zero if the load case is successfully initialized; otherwise it returns a nonzero value.
- **Remarks**: If this function is called for an existing load case, all items for the case are reset to their default value.
- **HTML**: `html/312cebd3-88ff-24aa-51ff-8d3aba210890.htm`

#### SetInitialCase
- **Purpose**: Sets the initial condition for the specified load case.
- **Signature**: `int SetInitialCase( string Name, string InitialCase )`
- **Parameters**:
  - `Name` (string): The name of an existing static linear load case.
  - `InitialCase` (string): This is blank, None, or the name of an existing analysis case. This item specifies if the load case starts from zero initial conditions, that is, an unstressed state, or if it starts using the stiffne...
- **Returns**: Returns zero if the initial condition is successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/7c3ea9e0-50a0-2585-4460-415fb47c6db6.htm`

#### SetLoads
- **Purpose**: Sets the load data for the specified analysis case.
- **Signature**: `int SetLoads( string Name, int NumberLoads, string[] LoadType, string[] LoadName, double[] SF )`
- **Parameters**:
  - `Name` (string): The name of an existing static linear load case.
  - `NumberLoads` (int): The number of loads assigned to the specified analysis case.
  - `LoadType` (string[]): AddLanguageSpecificTextSet("LST21A7A9FB_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes either Load or Accel, indicating the type of each load assigned to the load case.
  - `LoadName` (string[]): AddLanguageSpecificTextSet("LST21A7A9FB_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of each load assigned to the load case. If the LoadType item is Load, this item is the name of...
  - `SF` (double[]): AddLanguageSpecificTextSet("LST21A7A9FB_13?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the scale factor of each load assigned to the load case. [L/s^2] for Accel UX UY and UZ; otherwise uni...
- **Returns**: Returns zero if the data is successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/4b79ff00-70ba-a026-338d-77a3f144c678.htm`

---

## 12. cCaseStaticNonlinear
**Access**: `SapModel.LoadCases.StaticNonlinear`

**Description**: Nonlinear static (pushover) analysis. Configure geometric nonlinearity, hinge unloading, load application (force/displacement control), solution control parameters, target force parameters, mass source, and modal case for P-Delta.

### Methods

#### GetGeometricNonlinearity
- **Purpose**: No description
- **Signature**: `int GetGeometricNonlinearity( string Name, int NLGeomType )`
- **Parameters**:
  - `Name` (string): 
  - `NLGeomType` (int): 
- **HTML**: `html/343070dd-bd74-80ac-a209-01d56a517ae3.htm`

#### GetHingeUnloading
- **Purpose**: No description
- **Signature**: `int GetHingeUnloading( string Name, int UnloadType )`
- **Parameters**:
  - `Name` (string): 
  - `UnloadType` (int): 
- **HTML**: `html/14c6dcb8-f788-62c2-4ff2-a841ceb433fe.htm`

#### GetInitialCase
- **Purpose**: No description
- **Signature**: `int GetInitialCase( string Name, string InitialCase )`
- **Parameters**:
  - `Name` (string): 
  - `InitialCase` (string): 
- **HTML**: `html/640dc198-e4b0-b57f-d571-8397cb048a39.htm`

#### GetLoadApplication
- **Purpose**: No description
- **Signature**: `int GetLoadApplication( string Name, int LoadControl, int DispType, double Displ, int Monitor, int DOF, string PointName, string GDispl )`
- **Parameters**:
  - `Name` (string): 
  - `LoadControl` (int): 
  - `DispType` (int): 
  - `Displ` (double): 
  - `Monitor` (int): 
  - `DOF` (int): 
  - `PointName` (string): 
  - `GDispl` (string): 
- **HTML**: `html/a48c44f4-0bd6-b973-ad02-85e312c33faf.htm`

#### GetLoads
- **Purpose**: Retrieves the load data for the specified load case
- **Signature**: `int GetLoads( string Name, int NumberLoads, string[] LoadType, string[] LoadName, double[] SF )`
- **Parameters**:
  - `Name` (string): The name of an existing static nonlinear load case.
  - `NumberLoads` (int): The number of loads assigned to the specified analysis case.
  - `LoadType` (string[]): AddLanguageSpecificTextSet("LSTE0206169_6?cpp=&gt;|vb=()|nu=[]"); This is an array that includes either Load or Accel, indicating the type of each load assigned to the load case.
  - `LoadName` (string[]): AddLanguageSpecificTextSet("LSTE0206169_10?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of each load assigned to the load case. If the LoadType item is Load, this item is the name o...
  - `SF` (double[]): AddLanguageSpecificTextSet("LSTE0206169_14?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the scale factor of each load assigned to the load case. [L/s^2] for Accel UX UY and UZ; otherwise uni...
- **Returns**: Returns zero if the data is successfully retrieved; otherwise it returns a nonzero value.
- **HTML**: `html/01eb6b02-4c25-f9b5-8961-a8a3b0760697.htm`

#### GetMassSource
- **Purpose**: No description
- **Signature**: `int GetMassSource( string Name, string mSource )`
- **Parameters**:
  - `Name` (string): 
  - `mSource` (string): 
- **HTML**: `html/73c2cc5e-c8c3-be6b-62c8-095fd7aef3c2.htm`

#### GetModalCase
- **Purpose**: No description
- **Signature**: `int GetModalCase( string Name, string ModalCase )`
- **Parameters**:
  - `Name` (string): 
  - `ModalCase` (string): 
- **HTML**: `html/36817530-a753-c765-fe88-9ecfa71892ab.htm`

#### GetResultsSaved
- **Purpose**: No description
- **Signature**: `int GetResultsSaved( string Name, bool SaveMultipleSteps, int MinSavedStates, int MaxSavedStates, bool PositiveOnly )`
- **Parameters**:
  - `Name` (string): 
  - `SaveMultipleSteps` (bool): 
  - `MinSavedStates` (int): 
  - `MaxSavedStates` (int): 
  - `PositiveOnly` (bool): 
- **HTML**: `html/a996e37b-6f9e-0ace-1e9f-d6a345b3eb9a.htm`

#### GetSolControlParameters
- **Purpose**: No description
- **Signature**: `int GetSolControlParameters( string Name, int MaxTotalSteps, int MaxFailedSubSteps, int MaxIterCS, int MaxIterNR, double TolConvD, bool UseEventStepping, double TolEventD, int MaxLineSearchPerIter, double TolLineSearch, double LineSearchStepFact )`
- **Parameters**: 11 params (see HTML for full details)
  - `Name` (string): 
  - `MaxTotalSteps` (int): 
  - `MaxFailedSubSteps` (int): 
  - `MaxIterCS` (int): 
  - ... and 7 more output arrays
- **HTML**: `html/2ae6b8fb-540a-da21-61ce-cf10cdec6c2a.htm`

#### GetTargetForceParameters
- **Purpose**: No description
- **Signature**: `int GetTargetForceParameters( string Name, double TolConvF, int MaxIter, double AccelFact, bool NoStop )`
- **Parameters**:
  - `Name` (string): 
  - `TolConvF` (double): 
  - `MaxIter` (int): 
  - `AccelFact` (double): 
  - `NoStop` (bool): 
- **HTML**: `html/f150a464-1c37-b18d-f2be-6824b93fc303.htm`

#### SetCase
- **Purpose**: Initializes a static nonlinear load case.
- **Signature**: `int SetCase( string Name )`
- **Parameters**:
  - `Name` (string): The name of an existing or new load case. If this is an existing case, that case is modified; otherwise, a new case is added.
- **Returns**: Returns zero if the load case is successfully initialized; otherwise it returns a nonzero value.
- **Remarks**: If this function is called for an existing load case, all items for the case are reset to their default value.
- **HTML**: `html/662d94dd-3461-64b6-7597-855ecf848dcd.htm`

#### SetGeometricNonlinearity
- **Purpose**: Sets the geometric nonlinearity option for the specified load case.
- **Signature**: `int SetGeometricNonlinearity( string Name, int NLGeomType )`
- **Parameters**:
  - `Name` (string): The name of an existing static nonlinear load case.
  - `NLGeomType` (int): 
- **Returns**: Returns zero if the option is successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/d6143c78-dcee-0c6c-6055-7eb2ff1b623d.htm`

#### SetHingeUnloading
- **Purpose**: No description
- **Signature**: `int SetHingeUnloading( string Name, int UnloadType )`
- **Parameters**:
  - `Name` (string): 
  - `UnloadType` (int): 
- **HTML**: `html/aac8206d-2cd1-cc84-d80a-023586822b08.htm`

#### SetInitialCase
- **Purpose**: No description
- **Signature**: `int SetInitialCase( string Name, string InitialCase )`
- **Parameters**:
  - `Name` (string): 
  - `InitialCase` (string): 
- **HTML**: `html/ba263306-9154-f893-166e-9cfb7cd22eac.htm`

#### SetLoadApplication
- **Purpose**: No description
- **Signature**: `int SetLoadApplication( string Name, int LoadControl, int DispType, double Displ, int Monitor, int DOF, string PointName, string GDispl )`
- **Parameters**:
  - `Name` (string): 
  - `LoadControl` (int): 
  - `DispType` (int): 
  - `Displ` (double): 
  - `Monitor` (int): 
  - `DOF` (int): 
  - `PointName` (string): 
  - `GDispl` (string): 
- **HTML**: `html/b2a1e257-7338-66bf-4eba-0e1d67168e79.htm`

#### SetLoads
- **Purpose**: Sets the load data for the specified analysis case.
- **Signature**: `int SetLoads( string Name, int NumberLoads, string[] LoadType, string[] LoadName, double[] SF )`
- **Parameters**:
  - `Name` (string): The name of an existing static nonlinear load case.
  - `NumberLoads` (int): The number of loads assigned to the specified analysis case.
  - `LoadType` (string[]): AddLanguageSpecificTextSet("LSTA64293D8_5?cpp=&gt;|vb=()|nu=[]"); This is an array that includes either Load or Accel, indicating the type of each load assigned to the load case.
  - `LoadName` (string[]): AddLanguageSpecificTextSet("LSTA64293D8_9?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of each load assigned to the load case. If the LoadType item is Load, this item is the name of...
  - `SF` (double[]): AddLanguageSpecificTextSet("LSTA64293D8_13?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the scale factor of each load assigned to the load case. [L/s^2] for Accel UX UY and UZ; otherwise uni...
- **Returns**: Returns zero if the data is successfully set; otherwise it returns a nonzero value.
- **HTML**: `html/41c8854b-6e37-0b44-36e3-cb622b49b591.htm`

#### SetMassSource
- **Purpose**: No description
- **Signature**: `int SetMassSource( string Name, string mSource )`
- **Parameters**:
  - `Name` (string): 
  - `mSource` (string): 
- **HTML**: `html/e7871c09-bf0d-29ef-ed9a-349d6c09914b.htm`

#### SetModalCase
- **Purpose**: No description
- **Signature**: `int SetModalCase( string Name, string ModalCase )`
- **Parameters**:
  - `Name` (string): 
  - `ModalCase` (string): 
- **HTML**: `html/2186488c-7163-3c75-6ec2-90ebe2e3ebd7.htm`

#### SetResultsSaved
- **Purpose**: No description
- **Signature**: `int SetResultsSaved( string Name, bool SaveMultipleSteps, int MinSavedStates = 10, int MaxSavedStates = 100, bool PositiveOnly = true )`
- **Parameters**:
  - `Name` (string): 
  - `SaveMultipleSteps` (bool): 
- **HTML**: `html/ee310e1d-6624-29fc-f566-bf5910e9fda4.htm`

#### SetSolControlParameters
- **Purpose**: No description
- **Signature**: `int SetSolControlParameters( string Name, int MaxTotalSteps, int MaxFailedSubSteps, int MaxIterCS, int MaxIterNR, double TolConvD, bool UseEventStepping, double TolEventD, int MaxLineSearchPerIter, double TolLineSearch, double LineSearchStepFact )`
- **Parameters**: 11 params (see HTML for full details)
  - `Name` (string): 
  - `MaxTotalSteps` (int): 
  - `MaxFailedSubSteps` (int): 
  - `MaxIterCS` (int): 
  - ... and 7 more output arrays
- **HTML**: `html/d752e14c-a906-638e-b384-7f8b75029f1d.htm`

#### SetTargetForceParameters
- **Purpose**: No description
- **Signature**: `int SetTargetForceParameters( string Name, double TolConvF, int MaxIter, double AccelFact, bool NoStop )`
- **Parameters**:
  - `Name` (string): 
  - `TolConvF` (double): 
  - `MaxIter` (int): 
  - `AccelFact` (double): 
  - `NoStop` (bool): 
- **HTML**: `html/b43c1d0d-7224-52c1-2950-b1a71782d22f.htm`

---

## 13. cCaseStaticNonlinearStaged
**Access**: `SapModel.LoadCases.StaticNonlinearStaged`

**Description**: Staged construction nonlinear static case. Configure stages (add/remove objects, load application), geometric nonlinearity, material nonlinearity, hinge unloading, solution control, and time-dependent properties.

### Methods

#### GetGeometricNonlinearity
- **Purpose**: No description
- **Signature**: `int GetGeometricNonlinearity( string Name, int NLGeomType )`
- **Parameters**:
  - `Name` (string): 
  - `NLGeomType` (int): 
- **HTML**: `html/119f1686-8e34-56fe-1a12-837ee9408508.htm`

#### GetHingeUnloading
- **Purpose**: No description
- **Signature**: `int GetHingeUnloading( string Name, int UnloadType )`
- **Parameters**:
  - `Name` (string): 
  - `UnloadType` (int): 
- **HTML**: `html/7fc2c8a5-d398-26a2-1408-8b7d1d6fb590.htm`

#### GetInitialCase
- **Purpose**: No description
- **Signature**: `int GetInitialCase( string Name, string InitialCase )`
- **Parameters**:
  - `Name` (string): 
  - `InitialCase` (string): 
- **HTML**: `html/75188402-d930-30b3-d332-e25fbcadf54f.htm`

#### GetMassSource
- **Purpose**: No description
- **Signature**: `int GetMassSource( string Name, string mSource )`
- **Parameters**:
  - `Name` (string): 
  - `mSource` (string): 
- **HTML**: `html/3c41dc56-7aed-8a4e-6731-6af960c3eebf.htm`

#### GetMaterialNonlinearity
- **Purpose**: No description
- **Signature**: `int GetMaterialNonlinearity( string Name, bool TimeDepMatProp )`
- **Parameters**:
  - `Name` (string): 
  - `TimeDepMatProp` (bool): 
- **HTML**: `html/193d0d7c-c34e-d9e3-4178-061c3e3c0e8e.htm`

#### GetResultsSaved
- **Purpose**: No description
- **Signature**: `int GetResultsSaved( string Name, int StagedSaveOption, int StagedMinSteps, int StagedMinStepsTD )`
- **Parameters**:
  - `Name` (string): 
  - `StagedSaveOption` (int): 
  - `StagedMinSteps` (int): 
  - `StagedMinStepsTD` (int): 
- **HTML**: `html/ffd3c8c0-24aa-a72f-66fd-3e1ba242f528.htm`

#### GetSolControlParameters
- **Purpose**: No description
- **Signature**: `int GetSolControlParameters( string Name, int MaxTotalSteps, int MaxFailedSubSteps, int MaxIterCS, int MaxIterNR, double TolConvD, bool UseEventStepping, double TolEventD, int MaxLineSearchPerIter, double TolLineSearch, double LineSearchStepFact )`
- **Parameters**: 11 params (see HTML for full details)
  - `Name` (string): 
  - `MaxTotalSteps` (int): 
  - `MaxFailedSubSteps` (int): 
  - `MaxIterCS` (int): 
  - ... and 7 more output arrays
- **HTML**: `html/4f90d84a-87f9-3e4f-438e-efdfbd719679.htm`

#### GetStageData
- **Purpose**: No description
- **Signature**: `int GetStageData( string Name, int Stage, int NumberOperations, int[] Operation, string[] GroupName, int[] Age, string[] LoadType, string[] LoadName, double[] SF )`
- **Parameters**:
  - `Name` (string): 
  - `Stage` (int): 
  - `NumberOperations` (int): 
  - `Operation` (int[]): AddLanguageSpecificTextSet("LST2CF21D52_8?cpp=&gt;|vb=()|nu=[]");
  - `GroupName` (string[]): AddLanguageSpecificTextSet("LST2CF21D52_12?cpp=&gt;|vb=()|nu=[]");
  - `Age` (int[]): AddLanguageSpecificTextSet("LST2CF21D52_16?cpp=&gt;|vb=()|nu=[]");
  - `LoadType` (string[]): AddLanguageSpecificTextSet("LST2CF21D52_20?cpp=&gt;|vb=()|nu=[]");
  - `LoadName` (string[]): AddLanguageSpecificTextSet("LST2CF21D52_24?cpp=&gt;|vb=()|nu=[]");
  - `SF` (double[]): AddLanguageSpecificTextSet("LST2CF21D52_28?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/c8b70a4c-cf92-67d2-a2e8-f00d67f568cd.htm`

#### GetStageData_1
- **Purpose**: Retrieves stage data for the specified stage in the specified load case
- **Signature**: `int GetStageData_1( string Name, int Stage, int NumberOperations, int[] Operation, string[] ObjectType, string[] ObjectName, int[] Age, string[] MyType, string[] MyName, double[] SF )`
- **Parameters**:
  - `Name` (string): The name of an existing static nonlinear staged load case
  - `Stage` (int): The stage in the specified load case for which data is requested. Stages are numbered sequentially starting from 1
  - `NumberOperations` (int): The number of operations in the specified stage
  - `Operation` (int[]): AddLanguageSpecificTextSet("LST899863FF_8?cpp=&gt;|vb=()|nu=[]"); This is an array that includes 1, 2, 3, 4, 5, 6, 7, or 11, indicating an operation type. 1Add structure2Remove structure3Load objects ...
  - `ObjectType` (string[]): AddLanguageSpecificTextSet("LST899863FF_12?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the object type associated with the specified operation. The object type may be one of the following: ...
  - `ObjectName` (string[]): AddLanguageSpecificTextSet("LST899863FF_16?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the object associated with the specified operation. This is the name of a Group, Frame obj...
  - `Age` (int[]): AddLanguageSpecificTextSet("LST899863FF_20?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the age of the added structure, at the time it is added, in days. This item applies only to operations...
  - `MyType` (string[]): AddLanguageSpecificTextSet("LST899863FF_24?cpp=&gt;|vb=()|nu=[]"); This is an array that includes a load type or an object type, depending on what is specified for the Operation item. This item applie...
  - `MyName` (string[]): AddLanguageSpecificTextSet("LST899863FF_28?cpp=&gt;|vb=()|nu=[]"); This is an array that includes a load assignment or an object name, depending on what is specified for the Operation item. This item ...
  - `SF` (double[]): AddLanguageSpecificTextSet("LST899863FF_32?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the scale factor for the load assigned to the operation, if any. [L/s2] for Accel UX UY and UZ; otherw...
- **Returns**: Returns zero if the data is successfully retrieved; otherwise, it returns a nonzero value
- **Remarks**: ReferencecCaseStaticNonlinearStaged InterfaceETABSv1 Namespace
- **HTML**: `html/39237b66-a2d5-6104-399f-036c1672634e.htm`

#### GetStageData_2
- **Purpose**: Retrieves stage data for the specified stage in the specified load case
- **Signature**: `int GetStageData_2( string Name, int Stage, int NumberOperations, int[] Operation, string[] ObjectType, string[] ObjectName, double[] Age, string[] MyType, string[] MyName, double[] SF )`
- **Parameters**:
  - `Name` (string): The name of an existing static nonlinear staged load case
  - `Stage` (int): The stage in the specified load case for which data is requested. Stages are numbered sequentially starting from 1
  - `NumberOperations` (int): The number of operations in the specified stage
  - `Operation` (int[]): AddLanguageSpecificTextSet("LSTDC458461_8?cpp=&gt;|vb=()|nu=[]"); This is an array that includes 1, 2, 3, 4, 5, 6, 7, or 11, indicating an operation type. 1Add structure2Remove structure3Load objects ...
  - `ObjectType` (string[]): AddLanguageSpecificTextSet("LSTDC458461_12?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the object type associated with the specified operation. The object type may be one of the following: ...
  - `ObjectName` (string[]): AddLanguageSpecificTextSet("LSTDC458461_16?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the name of the object associated with the specified operation. This is the name of a Group, Frame obj...
  - `Age` (double[]): AddLanguageSpecificTextSet("LSTDC458461_20?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the age of the added structure, at the time it is added, in days. This item applies only to operations...
  - `MyType` (string[]): AddLanguageSpecificTextSet("LSTDC458461_24?cpp=&gt;|vb=()|nu=[]"); This is an array that includes a load type or an object type, depending on what is specified for the Operation item. This item applie...
  - `MyName` (string[]): AddLanguageSpecificTextSet("LSTDC458461_28?cpp=&gt;|vb=()|nu=[]"); This is an array that includes a load assignment or an object name, depending on what is specified for the Operation item. This item ...
  - `SF` (double[]): AddLanguageSpecificTextSet("LSTDC458461_32?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the scale factor for the load assigned to the operation, if any. [L/s2] for Accel UX UY and UZ; otherw...
- **Returns**: Returns zero if the data is successfully retrieved; otherwise, it returns a nonzero value
- **Remarks**: ReferencecCaseStaticNonlinearStaged InterfaceETABSv1 Namespace
- **HTML**: `html/e7a62f45-6944-1f26-ca31-08c55389ed2b.htm`

#### GetStageDefinitions
- **Purpose**: No description
- **Signature**: `int GetStageDefinitions( string Name, int NumberStages, int[] Duration, string[] Comment )`
- **Parameters**:
  - `Name` (string): 
  - `NumberStages` (int): 
  - `Duration` (int[]): AddLanguageSpecificTextSet("LST47EB00F5_6?cpp=&gt;|vb=()|nu=[]");
  - `Comment` (string[]): AddLanguageSpecificTextSet("LST47EB00F5_10?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/bc2c30e2-a81f-51c7-9db8-d6b8a6256160.htm`

#### GetStageDefinitions_1
- **Purpose**: Retrieves the stage definition data for the specified load case
- **Signature**: `int GetStageDefinitions_1( string Name, int NumberStages, int[] Duration, bool[] Output, string[] OutputName, string[] Comment )`
- **Parameters**:
  - `Name` (string): The name of an existing static nonlinear staged load case
  - `NumberStages` (int): The number of stages defined for the specified load case
  - `Duration` (int[]): AddLanguageSpecificTextSet("LST5829E959_6?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the duration in days for each stage
  - `Output` (bool[]): AddLanguageSpecificTextSet("LST5829E959_10?cpp=&gt;|vb=()|nu=[]"); This is an array that includes True or False, indicating if analysis output is to be saved for each stage
  - `OutputName` (string[]): AddLanguageSpecificTextSet("LST5829E959_14?cpp=&gt;|vb=()|nu=[]"); This is an array that includes a user-specified output name for each stage
  - `Comment` (string[]): AddLanguageSpecificTextSet("LST5829E959_18?cpp=&gt;|vb=()|nu=[]"); This is an array that includes a comment for each stage. The comment may be a blank string.
- **Returns**: Returns zero if the data is successfully retrieved; otherwise it returns a nonzero value
- **Remarks**: ReferencecCaseStaticNonlinearStaged InterfaceETABSv1 Namespace
- **HTML**: `html/633ce791-1c9f-4278-9350-12bddac2c7ff.htm`

#### GetStageDefinitions_2
- **Purpose**: Retrieves the stage definition data for the specified load case
- **Signature**: `int GetStageDefinitions_2( string Name, int NumberStages, double[] Duration, bool[] Output, string[] OutputName, string[] Comment )`
- **Parameters**:
  - `Name` (string): The name of an existing static nonlinear staged load case
  - `NumberStages` (int): The number of stages defined for the specified load case
  - `Duration` (double[]): AddLanguageSpecificTextSet("LSTF2FBA534_6?cpp=&gt;|vb=()|nu=[]"); This is an array that includes the duration in days for each stage
  - `Output` (bool[]): AddLanguageSpecificTextSet("LSTF2FBA534_10?cpp=&gt;|vb=()|nu=[]"); This is an array that includes True or False, indicating if analysis output is to be saved for each stage
  - `OutputName` (string[]): AddLanguageSpecificTextSet("LSTF2FBA534_14?cpp=&gt;|vb=()|nu=[]"); This is an array that includes a user-specified output name for each stage
  - `Comment` (string[]): AddLanguageSpecificTextSet("LSTF2FBA534_18?cpp=&gt;|vb=()|nu=[]"); This is an array that includes a comment for each stage. The comment may be a blank string.
- **Returns**: Returns zero if the data is successfully retrieved; otherwise it returns a nonzero value
- **Remarks**: ReferencecCaseStaticNonlinearStaged InterfaceETABSv1 Namespace
- **HTML**: `html/294c97c9-90c9-881e-3ec3-78b26355730a.htm`

#### GetTargetForceParameters
- **Purpose**: No description
- **Signature**: `int GetTargetForceParameters( string Name, double TolConvF, int MaxIter, double AccelFact, bool NoStop )`
- **Parameters**:
  - `Name` (string): 
  - `TolConvF` (double): 
  - `MaxIter` (int): 
  - `AccelFact` (double): 
  - `NoStop` (bool): 
- **HTML**: `html/01fbfb22-54b2-06b0-a81e-7e444cb5fd0a.htm`

#### SetCase
- **Purpose**: No description
- **Signature**: `int SetCase( string Name )`
- **Parameters**:
  - `Name` (string): 
- **HTML**: `html/e8d6a8e9-0c66-8707-60d5-aaf804241daf.htm`

#### SetGeometricNonlinearity
- **Purpose**: No description
- **Signature**: `int SetGeometricNonlinearity( string Name, int NLGeomType )`
- **Parameters**:
  - `Name` (string): 
  - `NLGeomType` (int): 
- **HTML**: `html/7f89fd6c-0181-0cb8-5854-da1db24c27a9.htm`

#### SetHingeUnloading
- **Purpose**: No description
- **Signature**: `int SetHingeUnloading( string Name, int UnloadType )`
- **Parameters**:
  - `Name` (string): 
  - `UnloadType` (int): 
- **HTML**: `html/6483d877-af45-a829-965f-cb6d0c0eb74e.htm`

#### SetInitialCase
- **Purpose**: No description
- **Signature**: `int SetInitialCase( string Name, string InitialCase )`
- **Parameters**:
  - `Name` (string): 
  - `InitialCase` (string): 
- **HTML**: `html/405fec32-48cd-a5d3-9e17-1a9dc6fac7de.htm`

#### SetMassSource
- **Purpose**: No description
- **Signature**: `int SetMassSource( string Name, string mSource )`
- **Parameters**:
  - `Name` (string): 
  - `mSource` (string): 
- **HTML**: `html/3548f9e4-6b01-e4b2-cd42-b0d206bfff88.htm`

#### SetMaterialNonlinearity
- **Purpose**: No description
- **Signature**: `int SetMaterialNonlinearity( string Name, bool TimeDepMatProp )`
- **Parameters**:
  - `Name` (string): 
  - `TimeDepMatProp` (bool): 
- **HTML**: `html/c1c36d69-15ab-42a4-5a41-78878a314761.htm`

#### SetResultsSaved
- **Purpose**: No description
- **Signature**: `int SetResultsSaved( string Name, int StagedSaveOption, int StagedMinSteps = 1, int StagedMinStepsTD = 1 )`
- **Parameters**:
  - `Name` (string): 
  - `StagedSaveOption` (int): 
- **HTML**: `html/40445c24-ca6a-68f0-2800-5f939b1c172d.htm`

#### SetSolControlParameters
- **Purpose**: No description
- **Signature**: `int SetSolControlParameters( string Name, int MaxTotalSteps, int MaxFailedSubSteps, int MaxIterCS, int MaxIterNR, double TolConvD, bool UseEventStepping, double TolEventD, int MaxLineSearchPerIter, double TolLineSearch, double LineSearchStepFact )`
- **Parameters**: 11 params (see HTML for full details)
  - `Name` (string): 
  - `MaxTotalSteps` (int): 
  - `MaxFailedSubSteps` (int): 
  - `MaxIterCS` (int): 
  - ... and 7 more output arrays
- **HTML**: `html/f8e926e8-188c-6039-bddc-cc6a455a28b2.htm`

#### SetStageData
- **Purpose**: No description
- **Signature**: `int SetStageData( string Name, int Stage, int NumberOperations, int[] Operation, string[] GroupName, int[] Age, string[] LoadType, string[] LoadName, double[] SF )`
- **Parameters**:
  - `Name` (string): 
  - `Stage` (int): 
  - `NumberOperations` (int): 
  - `Operation` (int[]): AddLanguageSpecificTextSet("LST9B6F70B1_6?cpp=&gt;|vb=()|nu=[]");
  - `GroupName` (string[]): AddLanguageSpecificTextSet("LST9B6F70B1_10?cpp=&gt;|vb=()|nu=[]");
  - `Age` (int[]): AddLanguageSpecificTextSet("LST9B6F70B1_14?cpp=&gt;|vb=()|nu=[]");
  - `LoadType` (string[]): AddLanguageSpecificTextSet("LST9B6F70B1_18?cpp=&gt;|vb=()|nu=[]");
  - `LoadName` (string[]): AddLanguageSpecificTextSet("LST9B6F70B1_22?cpp=&gt;|vb=()|nu=[]");
  - `SF` (double[]): AddLanguageSpecificTextSet("LST9B6F70B1_26?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/d15cf517-ab44-9fd9-bd3f-b127ff219f80.htm`

#### SetStageData_1
- **Purpose**: No description
- **Signature**: `int SetStageData_1( string Name, int Stage, int NumberOperations, int[] Operation, string[] ObjectType, string[] ObjectName, int[] Age, string[] MyType, string[] MyName, double[] SF )`
- **Parameters**:
  - `Name` (string): 
  - `Stage` (int): 
  - `NumberOperations` (int): 
  - `Operation` (int[]): AddLanguageSpecificTextSet("LST54C503AE_6?cpp=&gt;|vb=()|nu=[]");
  - `ObjectType` (string[]): AddLanguageSpecificTextSet("LST54C503AE_10?cpp=&gt;|vb=()|nu=[]");
  - `ObjectName` (string[]): AddLanguageSpecificTextSet("LST54C503AE_14?cpp=&gt;|vb=()|nu=[]");
  - `Age` (int[]): AddLanguageSpecificTextSet("LST54C503AE_18?cpp=&gt;|vb=()|nu=[]");
  - `MyType` (string[]): AddLanguageSpecificTextSet("LST54C503AE_22?cpp=&gt;|vb=()|nu=[]");
  - `MyName` (string[]): AddLanguageSpecificTextSet("LST54C503AE_26?cpp=&gt;|vb=()|nu=[]");
  - `SF` (double[]): AddLanguageSpecificTextSet("LST54C503AE_30?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/93afd346-1131-be7c-2921-6c8b6b4cb79d.htm`

#### SetStageData_2
- **Purpose**: No description
- **Signature**: `int SetStageData_2( string Name, int Stage, int NumberOperations, int[] Operation, string[] ObjectType, string[] ObjectName, double[] Age, string[] MyType, string[] MyName, double[] SF )`
- **Parameters**:
  - `Name` (string): 
  - `Stage` (int): 
  - `NumberOperations` (int): 
  - `Operation` (int[]): AddLanguageSpecificTextSet("LST40579E74_6?cpp=&gt;|vb=()|nu=[]");
  - `ObjectType` (string[]): AddLanguageSpecificTextSet("LST40579E74_10?cpp=&gt;|vb=()|nu=[]");
  - `ObjectName` (string[]): AddLanguageSpecificTextSet("LST40579E74_14?cpp=&gt;|vb=()|nu=[]");
  - `Age` (double[]): AddLanguageSpecificTextSet("LST40579E74_18?cpp=&gt;|vb=()|nu=[]");
  - `MyType` (string[]): AddLanguageSpecificTextSet("LST40579E74_22?cpp=&gt;|vb=()|nu=[]");
  - `MyName` (string[]): AddLanguageSpecificTextSet("LST40579E74_26?cpp=&gt;|vb=()|nu=[]");
  - `SF` (double[]): AddLanguageSpecificTextSet("LST40579E74_30?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/44d53218-5da8-837d-b0fd-968042e4ac51.htm`

#### SetStageDefinitions
- **Purpose**: No description
- **Signature**: `int SetStageDefinitions( string Name, int NumberStages, int[] Duration, string[] Comment )`
- **Parameters**:
  - `Name` (string): 
  - `NumberStages` (int): 
  - `Duration` (int[]): AddLanguageSpecificTextSet("LSTEBBB2BEC_5?cpp=&gt;|vb=()|nu=[]");
  - `Comment` (string[]): AddLanguageSpecificTextSet("LSTEBBB2BEC_9?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/2cff128c-67fc-a982-1c51-f79432adfd04.htm`

#### SetStageDefinitions_1
- **Purpose**: No description
- **Signature**: `int SetStageDefinitions_1( string Name, int NumberStages, int[] Duration, bool[] Output, string[] OutputName, string[] Comment )`
- **Parameters**:
  - `Name` (string): 
  - `NumberStages` (int): 
  - `Duration` (int[]): AddLanguageSpecificTextSet("LST3C640CC9_5?cpp=&gt;|vb=()|nu=[]");
  - `Output` (bool[]): AddLanguageSpecificTextSet("LST3C640CC9_9?cpp=&gt;|vb=()|nu=[]");
  - `OutputName` (string[]): AddLanguageSpecificTextSet("LST3C640CC9_13?cpp=&gt;|vb=()|nu=[]");
  - `Comment` (string[]): AddLanguageSpecificTextSet("LST3C640CC9_17?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/0f61ff65-f9f9-f0c4-0434-c0b894448d5d.htm`

#### SetStageDefinitions_2
- **Purpose**: No description
- **Signature**: `int SetStageDefinitions_2( string Name, int NumberStages, double[] Duration, bool[] Output, string[] OutputName, string[] Comment )`
- **Parameters**:
  - `Name` (string): 
  - `NumberStages` (int): 
  - `Duration` (double[]): AddLanguageSpecificTextSet("LST72DD2128_5?cpp=&gt;|vb=()|nu=[]");
  - `Output` (bool[]): AddLanguageSpecificTextSet("LST72DD2128_9?cpp=&gt;|vb=()|nu=[]");
  - `OutputName` (string[]): AddLanguageSpecificTextSet("LST72DD2128_13?cpp=&gt;|vb=()|nu=[]");
  - `Comment` (string[]): AddLanguageSpecificTextSet("LST72DD2128_17?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/fdd842d9-b1d8-c6ec-7eb2-e58929e3e946.htm`

#### SetTargetForceParameters
- **Purpose**: No description
- **Signature**: `int SetTargetForceParameters( string Name, double TolConvF, int MaxIter, double AccelFact, bool NoStop )`
- **Parameters**:
  - `Name` (string): 
  - `TolConvF` (double): 
  - `MaxIter` (int): 
  - `AccelFact` (double): 
  - `NoStop` (bool): 
- **HTML**: `html/59d51a3d-2708-6a41-dcfc-bddd709ff1b8.htm`

---

## 14. cCaseResponseSpectrum
**Access**: `SapModel.LoadCases.ResponseSpectrum`

**Description**: Response spectrum analysis case. Configure damping type/values, directional combination rule, eccentricity override, modal combination method (CQC/SRSS/etc.), applied spectrum functions with direction and scale factors.

### Methods

#### GetDampConstant
- **Purpose**: No description
- **Signature**: `int GetDampConstant( string Name, double Damp )`
- **Parameters**:
  - `Name` (string): 
  - `Damp` (double): 
- **HTML**: `html/7785948f-e10a-d61f-ec12-bf58c541a5cf.htm`

#### GetDampInterpolated
- **Purpose**: No description
- **Signature**: `int GetDampInterpolated( string Name, int DampType, int NumberItems, double[] Time, double[] Damp )`
- **Parameters**:
  - `Name` (string): 
  - `DampType` (int): 
  - `NumberItems` (int): 
  - `Time` (double[]): AddLanguageSpecificTextSet("LST506E8574_8?cpp=&gt;|vb=()|nu=[]");
  - `Damp` (int): AddLanguageSpecificTextSet("LST506E8574_12?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/0482c0ea-30a7-4469-87cb-6c63e7c52c99.htm`

#### GetDampOverrides
- **Purpose**: No description
- **Signature**: `int GetDampOverrides( string Name, int NumberItems, int[] Mode, double[] Damp )`
- **Parameters**:
  - `Name` (string): 
  - `NumberItems` (int): 
  - `Mode` (int[]): AddLanguageSpecificTextSet("LST29703570_6?cpp=&gt;|vb=()|nu=[]");
  - `Damp` (double[]): AddLanguageSpecificTextSet("LST29703570_10?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/6a70f842-ba8e-494d-31d8-b1c59c5a2834.htm`

#### GetDampProportional
- **Purpose**: No description
- **Signature**: `int GetDampProportional( string Name, int DampType, double DampA, double DampB, double DampF1, double DampF2, double DampD1, double DampD2 )`
- **Parameters**:
  - `Name` (string): 
  - `DampType` (int): 
  - `DampA` (double): 
  - `DampB` (double): 
  - `DampF1` (double): 
  - `DampF2` (double): 
  - `DampD1` (double): 
  - `DampD2` (double): 
- **HTML**: `html/9ec73221-8075-d719-9dae-c417f59554c0.htm`

#### GetDampType
- **Purpose**: No description
- **Signature**: `int GetDampType( string Name, int DampType )`
- **Parameters**:
  - `Name` (string): 
  - `DampType` (int): 
- **HTML**: `html/da3ea47a-969f-37e1-6348-2a71ab4e35f6.htm`

#### GetDiaphragmEccentricityOverride
- **Purpose**: No description
- **Signature**: `int GetDiaphragmEccentricityOverride( string Name, int Num, string[] Diaph, double[] Eccen )`
- **Parameters**:
  - `Name` (string): 
  - `Num` (int): 
  - `Diaph` (string[]): AddLanguageSpecificTextSet("LST8DE0A492_6?cpp=&gt;|vb=()|nu=[]");
  - `Eccen` (double[]): AddLanguageSpecificTextSet("LST8DE0A492_10?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/531e5934-b9ad-3cee-aa21-8d44c18129d5.htm`

#### GetDirComb
- **Purpose**: No description
- **Signature**: `int GetDirComb( string Name, int MyType, double SF )`
- **Parameters**:
  - `Name` (string): 
  - `MyType` (int): 
  - `SF` (double): 
- **HTML**: `html/2f6e176e-bce1-349c-a7dc-a05266c77aba.htm`

#### GetEccentricity
- **Purpose**: No description
- **Signature**: `int GetEccentricity( string Name, double Eccen )`
- **Parameters**:
  - `Name` (string): 
  - `Eccen` (double): 
- **HTML**: `html/4468cb04-8848-6333-c557-5664f05c28af.htm`

#### GetLoads
- **Purpose**: No description
- **Signature**: `int GetLoads( string Name, int NumberLoads, string[] LoadName, string[] Func, double[] SF, string[] CSys, double[] Ang )`
- **Parameters**:
  - `Name` (string): 
  - `NumberLoads` (int): 
  - `LoadName` (string[]): AddLanguageSpecificTextSet("LST991BE939_6?cpp=&gt;|vb=()|nu=[]");
  - `Func` (string[]): AddLanguageSpecificTextSet("LST991BE939_10?cpp=&gt;|vb=()|nu=[]");
  - `SF` (double[]): AddLanguageSpecificTextSet("LST991BE939_14?cpp=&gt;|vb=()|nu=[]");
  - `CSys` (string[]): AddLanguageSpecificTextSet("LST991BE939_18?cpp=&gt;|vb=()|nu=[]");
  - `Ang` (double[]): AddLanguageSpecificTextSet("LST991BE939_22?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/06e7c71e-e419-bc28-6164-4cba88ce1d18.htm`

#### GetModalCase
- **Purpose**: No description
- **Signature**: `int GetModalCase( string Name, string ModalCase )`
- **Parameters**:
  - `Name` (string): 
  - `ModalCase` (string): 
- **HTML**: `html/1554f0e6-1ac3-baae-f0d1-d69e955d57ed.htm`

#### GetModalComb
- **Purpose**: No description
- **Signature**: `int GetModalComb( string Name, int MyType, double F1, double F2, double Td )`
- **Parameters**:
  - `Name` (string): 
  - `MyType` (int): 
  - `F1` (double): 
  - `F2` (double): 
  - `Td` (double): 
- **HTML**: `html/db6f22f7-a0df-f11c-c531-4039357a25b2.htm`

#### GetModalComb_1
- **Purpose**: No description
- **Signature**: `int GetModalComb_1( string Name, int MyType, double F1, double F2, int PeriodicRigidCombType, double Td )`
- **Parameters**:
  - `Name` (string): 
  - `MyType` (int): 
  - `F1` (double): 
  - `F2` (double): 
  - `PeriodicRigidCombType` (int): 
  - `Td` (double): 
- **HTML**: `html/6c0c7293-0592-d018-2cce-2364982c7677.htm`

#### SetCase
- **Purpose**: No description
- **Signature**: `int SetCase( string Name )`
- **Parameters**:
  - `Name` (string): 
- **HTML**: `html/d457f415-bda6-d865-8d4d-1d5cb09967d8.htm`

#### SetEccentricity
- **Purpose**: No description
- **Signature**: `int SetEccentricity( string Name, double Eccen )`
- **Parameters**:
  - `Name` (string): 
  - `Eccen` (double): 
- **HTML**: `html/b3fcdb01-8d3b-9d81-ec54-f8d774bae4b1.htm`

#### SetLoads
- **Purpose**: No description
- **Signature**: `int SetLoads( string Name, int NumberLoads, string[] LoadName, string[] Func, double[] SF, string[] CSys, double[] Ang )`
- **Parameters**:
  - `Name` (string): 
  - `NumberLoads` (int): 
  - `LoadName` (string[]): AddLanguageSpecificTextSet("LST85A9DCF5_5?cpp=&gt;|vb=()|nu=[]");
  - `Func` (string[]): AddLanguageSpecificTextSet("LST85A9DCF5_9?cpp=&gt;|vb=()|nu=[]");
  - `SF` (double[]): AddLanguageSpecificTextSet("LST85A9DCF5_13?cpp=&gt;|vb=()|nu=[]");
  - `CSys` (string[]): AddLanguageSpecificTextSet("LST85A9DCF5_17?cpp=&gt;|vb=()|nu=[]");
  - `Ang` (double[]): AddLanguageSpecificTextSet("LST85A9DCF5_21?cpp=&gt;|vb=()|nu=[]");
- **HTML**: `html/1df947e1-e04d-483f-6dc8-f4986513e0a3.htm`

#### SetModalCase
- **Purpose**: No description
- **Signature**: `int SetModalCase( string Name, string ModalCase )`
- **Parameters**:
  - `Name` (string): 
  - `ModalCase` (string): 
- **HTML**: `html/6a062987-bf6f-2be3-4e5e-2fca843ba87f.htm`

---

## 15. Other Load Case Interfaces

These interfaces follow similar patterns to the main load case interfaces.

### cCaseDirectHistoryLinear
- **Access**: `SapModel.LoadCases.DirHistLinear`
- **Description**: Direct integration linear time history
- **Methods** (1): GetLoads

### cCaseDirectHistoryNonlinear
- **Access**: `SapModel.LoadCases.DirHistNonlinear`
- **Description**: Direct integration nonlinear time history
- **Methods** (1): GetLoads

### cCaseModalHistoryLinear
- **Access**: `SapModel.LoadCases.ModHistLinear`
- **Description**: Modal linear time history
- **Methods** (3): GetLoads, SetCase, SetLoads

### cCaseModalHistoryNonlinear
- **Access**: `SapModel.LoadCases.ModHistNonlinear`
- **Description**: Modal nonlinear time history
- **Methods** (1): GetLoads

### cCaseHyperStatic
- **Access**: `SapModel.LoadCases.HyperStatic`
- **Description**: Hyperstatic (secondary) load case
- **Methods** (3): GetBaseCase, SetBaseCase, SetCase

---

## 16. Concrete Design Codes (cDCo*)

**Access**: `SapModel.DesignConcrete.{CodeName}`

### Common Pattern
All concrete design code interfaces expose 4 methods:

| Method | Signature | Purpose |
|--------|-----------|---------|
| GetOverwrite | `int GetOverwrite(string Name, int Item, ref double Value)` | Get design overwrite for a frame object |
| SetOverwrite | `int SetOverwrite(string Name, int Item, double Value)` | Set design overwrite for a frame object |
| GetPreference | `int GetPreference(int Item, ref double Value)` | Get design preference value |
| SetPreference | `int SetPreference(int Item, double Value)` | Set design preference value |

**Notes**:
- `Item` is an integer index specific to each code. Consult the HTML docs for item meanings.
- `Value=0` for overwrites typically means "use program-determined value".
- `Name` refers to a frame object name (for overwrites).

### Example: cDCoACI318_19

#### GetOverwrite
- **Purpose**: Retrieves the value of a concrete design overwrite item.
- **Signature**: `int GetOverwrite( string Name, int Item, double Value, bool ProgDet )`
- **Parameters**:
  - `Name` (string): The name of a frame object with a concrete frame design procedure.
  - `Item` (int): This is an integer between 1 and 13, inclusive, indicating the overwrite item considered. Framing typeLive load reduction factorUnbraced length ratio, MajorUnbraced length ratio, MinorEffective length factor, K MajorEffective length factor, K MinorMoment coefficient, Cm MajorMoment coefficient, Cm M...
  - `Value` (double): The value of the considered overwrite item. Framing type 0 = Program Default1 = Sway special2 = Sway Intermediate3 = Sway Ordinary4 = Non-sway Live load reduction factor Value &gt;= 0; 0 means use program determined value Unbraced length ratio, Major Value &gt;= 0; 0 means use program determined val...
  - `ProgDet` (bool): If this item is True, the specified value is program determined.
- **Returns**: Returns zero if the item is successfully retrieved; otherwise it returns a nonzero value.

#### GetPreference
- **Purpose**: Retrieves the value of a concrete design preference item.
- **Signature**: `int GetPreference( int Item, double Value )`
- **Parameters**:
  - `Item` (int): This is an integer between 1 and 18, inclusive, indicating the preference item considered. Number of interaction curvesNumber of interaction pointsConsider minimum eccentricityDesign for B/C Capacity Ratio?Seismic design categoryDesign System Omega0Design System RhoDesign System SdsConsider ICC_ESR ...
  - `Value` (double): The value of the considered preference item. Number of interaction curves Value &gt;= 4 and divisable by 4 Number of interaction points Value &gt;= 5 and odd Consider minimum eccentricity 0 = No Any other value = Yes Design for B/C Capacity Ratio? 1 = No 2 = Yes Seismic design category 1 = A2 = B3 =...
- **Returns**: Returns zero if the item is successfully retrieved; otherwise it returns a nonzero value.

#### SetOverwrite
- **Purpose**: Sets the value of a concrete design overwrite item.
- **Signature**: `int SetOverwrite( string Name, int Item, double Value, eItemType ItemType = eItemType.Objects )`
- **Parameters**:
  - `Name` (string): The name of an existing frame object or group, depending on the value of the ItemType
  - `Item` (int): This is an integer between 1 and 13, inclusive, indicating the overwrite item considered. Framing typeLive load reduction factorUnbraced length ratio, MajorUnbraced length ratio, MinorEffective length factor, K MajorEffective length factor, K MinorMoment coefficient, Cm MajorMoment coefficient, Cm M...
  - `Value` (double): The value of the considered overwrite item. Framing type 0 = Program Default1 = Sway special2 = Sway Intermediate3 = Sway Ordinary4 = Non-sway Live load reduction factor Value &gt;= 0; 0 means use program determined value Unbraced length ratio, Major Value &gt;= 0; 0 means use program determined val...
- **Returns**: Returns zero if the item is successfully set; otherwise it returns a nonzero value.

#### SetPreference
- **Purpose**: Sets the value of a concrete design preference item.
- **Signature**: `int SetPreference( int Item, double Value )`
- **Parameters**:
  - `Item` (int): This is an integer between 1 and 18, inclusive, indicating the preference item considered. Number of interaction curvesNumber of interaction pointsConsider minimum eccentricityDesign for B/C Capacity Ratio?Seismic design categoryDesign System Omega0Design System RhoDesign System SdsConsider ICC_ESR ...
  - `Value` (double): The value of the considered preference item. Number of interaction curves Value &gt;= 4 and divisable by 4 Number of interaction points Value &gt;= 5 and odd Consider minimum eccentricity 0 = No Any other value = Yes Design for B/C Capacity Ratio? 1 = No 2 = Yes Seismic design category 1 = A2 = B3 =...
- **Returns**: Returns zero if the item is successfully set; otherwise it returns a nonzero value.

### All Available Concrete Design Codes

- **cDCoACI318_08_IBC2009**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoACI318_11**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoACI318_14**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoACI318_19**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoAS_3600_09**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoAS_3600_2018**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoBS8110_97**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoChinese_2010**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoEurocode_2_2004**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoHong_Kong_CP_2013**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoIndian_IS_456_2000**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoItalianNTC2008C**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoMexican_RCDF_2004**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoMexican_RCDF_2017**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoNZS_3101_2006**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoSP63133302011**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoTS_500_2000**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCoTS_500_2000_R2018**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCompColAISC360_22**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCompColCSAS16_19**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDCompColEurocode_4_2004**: 4 methods (GetOverwrite, GetPreference, SetOverwrite, SetPreference)
- **cDConcShellACI350_20**: no methods
- **cDConcSlabACI318_14**: 1 methods (GetPreference)
- **cDConcSlabACI318_19**: 1 methods (GetPreference)
- **cDConcreteShellDesignRequest**: no methods

---

## 17. Composite Column Design Codes (cDCompCol*)

**Access**: `SapModel.DesignCompositeColumn.{CodeName}`

Same 4-method pattern as concrete codes.

- **cDCompColAISC360_22**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDCompColCSAS16_19**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDCompColEurocode_4_2004**: GetOverwrite, GetPreference, SetOverwrite, SetPreference

---

## 18. Concrete Slab Design Codes (cDConcSlab*)

**Access**: `SapModel.DesignConcreteSlab.{CodeName}`

Slab design interfaces typically only expose GetPreference (no overwrite methods).

- **cDConcSlabACI318_14**: GetPreference
- **cDConcSlabACI318_19**: GetPreference

### Related: Concrete Shell Design
- **cDConcShellACI350_20**: no methods exposed
- **cDConcreteShellDesignRequest**: no methods exposed

---

## 19. Steel Design Codes (cDSt*)

**Access**: `SapModel.DesignSteel.{CodeName}`

Same 4-method pattern: GetOverwrite, SetOverwrite, GetPreference, SetPreference.

### Available Codes

- **cDStAISC360_05_IBC2006**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStAISC360_10**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStAISC360_16**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStAISC360_22**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStAISC_ASD89**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStAISC_LRFD93**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStAustralian_AS4100_2020**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStAustralian_AS4100_98**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStBS5950_2000**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStCanadian_S16_09**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStCanadian_S16_14**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStCanadian_S16_19**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStCanadian_S16_24**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStChinese_2010**: GetOverwrite, GetPreference, SetOverwrite, SetPreference
- **cDStChinese_2018**: GetOverwrite, GetPreference, SetOverwrite, SetPreference

---

## Quick Reference: Common Workflows

### Running Analysis and Getting Results
```python
# 1. Save model first (required before analysis)
ret = SapModel.File.Save(filepath)

# 2. Set active DOF if needed
ret = SapModel.Analyze.SetActiveDOF(DOF)  # bool array [UX,UY,UZ,RX,RY,RZ]

# 3. Set which cases to run
ret = SapModel.Analyze.SetRunCaseFlag("", True, True)  # run all cases

# 4. Run analysis
ret = SapModel.Analyze.RunAnalysis()

# 5. Configure output
ret = SapModel.Results.Setup.DeselectAllCasesAndCombosForOutput()
ret = SapModel.Results.Setup.SetCaseSelectedForOutput("DEAD")

# 6. Get results
ret = SapModel.Results.FrameForce(name, eItemTypeElm.ObjectElm,
    NumberResults, Obj, ObjSta, Elm, ElmSta, LoadCase, StepType, StepNum,
    P, V2, V3, T, M2, M3)
```

### Creating and Modifying Area Objects
```python
# Add by coordinates
ret = SapModel.AreaObj.AddByCoord(NumPoints, x, y, z, Name, PropName)

# Add by point names
ret = SapModel.AreaObj.AddByPoint(NumPoints, PointNames, Name, PropName)

# Assign loads
ret = SapModel.AreaObj.SetLoadUniform(Name, LoadPat, Value, Dir)

# Assign diaphragm
ret = SapModel.AreaObj.SetDiaphragm(Name, DiaphragmName)

# Set pier/spandrel labels
ret = SapModel.AreaObj.SetPier(Name, PierName)
ret = SapModel.AreaObj.SetSpandrel(Name, SpandrelName)
```

### Response Spectrum Case Setup
```python
ret = SapModel.LoadCases.ResponseSpectrum.SetCase("RSX")
ret = SapModel.LoadCases.ResponseSpectrum.SetLoads("RSX", ...)
ret = SapModel.LoadCases.ResponseSpectrum.SetModalCase("RSX", "Modal")
ret = SapModel.LoadCases.ResponseSpectrum.SetEccentricity("RSX", 0.05)
```

### Load Combinations
```python
ret = SapModel.RespCombo.Add("COMB1", ComboType)
ret = SapModel.RespCombo.SetCaseList("COMB1", CaseType, CaseName, SF)
ret = SapModel.RespCombo.AddDesignDefaultCombos(DesignAct)
```

---

## Appendix: Key Enumerations

### eItemTypeElm (result methods)
| Value | Name | Description |
|-------|------|-------------|
| 0 | ObjectElm | Results for elements from the named object |
| 1 | Element | Results for the specific named element |
| 2 | GroupElm | Results for all elements in the named group |
| 3 | SelectionElm | Results for all selected elements (Name ignored) |

### eItemType (object assignment methods)
| Value | Name | Description |
|-------|------|-------------|
| 0 | Objects | Apply to the named object |
| 1 | Group | Apply to all objects in the named group |
| 2 | SelectedObjects | Apply to all selected objects (Name ignored) |

---

## Appendix: Complete Interface Summary

| Interface | Access Path | Methods | Description |
|-----------|-------------|---------|-------------|
| cAnalysisResults | `SapModel.Results` | 37 | Analysis results extraction |
| cAnalysisResultsSetup | `SapModel.Results.Setup` | 21 | Result output configuration |
| cAnalyze | `SapModel.Analyze` | 21 | Analysis execution and settings |
| cAreaElm | `SapModel.AreaElm` | 13 | Area element queries (read-only) |
| cAreaObj | `SapModel.AreaObj` | 64 | Area object manipulation |
| cAutoSeismic | `SapModel.AutoSeismic` | 6 | Seismic code parameters |
| cCaseDirectHistoryLinear | `SapModel.LoadCases.DirHistLinear` | 1 | Direct linear time history |
| cCaseDirectHistoryNonlinear | `SapModel.LoadCases.DirHistNonlinear` | 1 | Direct NL time history |
| cCaseHyperStatic | `SapModel.LoadCases.HyperStatic` | 3 | Hyperstatic load case |
| cCaseModalEigen | `SapModel.LoadCases.ModalEigen` | 9 | Eigen modal analysis |
| cCaseModalHistoryLinear | `SapModel.LoadCases.ModHistLinear` | 3 | Modal linear time history |
| cCaseModalHistoryNonlinear | `SapModel.LoadCases.ModHistNonlinear` | 1 | Modal NL time history |
| cCaseModalRitz | `SapModel.LoadCases.ModalRitz` | 7 | Ritz modal analysis |
| cCaseResponseSpectrum | `SapModel.LoadCases.ResponseSpectrum` | 16 | Response spectrum |
| cCaseStaticLinear | `SapModel.LoadCases.StaticLinear` | 5 | Linear static case |
| cCaseStaticNonlinear | `SapModel.LoadCases.StaticNonlinear` | 21 | Pushover analysis |
| cCaseStaticNonlinearStaged | `SapModel.LoadCases.StaticNonlinearStaged` | 29 | Staged construction |
| cCombo | `SapModel.RespCombo` | 11 | Load combinations |
| cConstraint | `SapModel.ConstraintDef` | 4 | Joint constraints |

### Design Code Interfaces (all follow Get/SetOverwrite + Get/SetPreference pattern)

Total design code interfaces: 40

| Category | Count | Interfaces |
|----------|-------|------------|
| Concrete (cDCo*) | 25 | cDCoACI318_08_IBC2009, cDCoACI318_11, cDCoACI318_14, cDCoACI318_19, cDCoAS_3600_09, cDCoAS_3600_2018, cDCoBS8110_97, cDCoChinese_2010, cDCoEurocode_2_2004, cDCoHong_Kong_CP_2013, cDCoIndian_IS_456_2000, cDCoItalianNTC2008C, cDCoMexican_RCDF_2004, cDCoMexican_RCDF_2017, cDCoNZS_3101_2006, cDCoSP63133302011, cDCoTS_500_2000, cDCoTS_500_2000_R2018, cDCompColAISC360_22, cDCompColCSAS16_19, cDCompColEurocode_4_2004, cDConcShellACI350_20, cDConcSlabACI318_14, cDConcSlabACI318_19, cDConcreteShellDesignRequest |
| Composite Column (cDCompCol*) | 3 | cDCompColAISC360_22, cDCompColCSAS16_19, cDCompColEurocode_4_2004 |
| Concrete Slab (cDConcSlab*) | 2 | cDConcSlabACI318_14, cDConcSlabACI318_19 |
| Concrete Shell | 2 | cDConcShellACI350_20, cDConcreteShellDesignRequest |
| Steel (cDSt*) | 15 | cDStAISC360_05_IBC2006, cDStAISC360_10, cDStAISC360_16, cDStAISC360_22, cDStAISC_ASD89, cDStAISC_LRFD93, cDStAustralian_AS4100_2020, cDStAustralian_AS4100_98, cDStBS5950_2000, cDStCanadian_S16_09, cDStCanadian_S16_14, cDStCanadian_S16_19, cDStCanadian_S16_24, cDStChinese_2010, cDStChinese_2018 |
