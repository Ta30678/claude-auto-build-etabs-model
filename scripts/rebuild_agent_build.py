"""
Rebuild AGENT BUILD model from REF e2k file.
Steps:
1. Connect to running ETABS
2. Initialize new model
3. Import REF e2k file
4. Save as AGENT BUILD.EDB
5. Run analysis
6. Run concrete design
"""
import sys
import os
import time

# Step 1: Connect to ETABS
print("=" * 60)
print("Step 1: Connecting to ETABS...")
print("=" * 60)

import etabs_obj
etabs = etabs_obj.EtabsModel(backup=False)
if not etabs.success:
    print("ERROR: Could not connect to ETABS. Make sure ETABS is running.")
    sys.exit(1)

SapModel = etabs.SapModel
print(f"Connected to ETABS.")
print(f"Current file: {SapModel.GetModelFilename()}")

# Step 2: Initialize new model (TON-M units = 12)
print("\n" + "=" * 60)
print("Step 2: Initializing new model...")
print("=" * 60)

ret = SapModel.InitializeNewModel(12)  # 12 = Ton_m_C
print(f"InitializeNewModel ret = {ret}")

ret = SapModel.File.NewBlank()
print(f"NewBlank ret = {ret}")

# Step 3: Import REF e2k file
print("\n" + "=" * 60)
print("Step 3: Importing REF e2k file...")
print("=" * 60)

e2k_path = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\Y21\REF\2025-1217.e2k"
print(f"e2k file: {e2k_path}")
print(f"File exists: {os.path.exists(e2k_path)}")

# ImportFile(FileName, FileType, Type)
# FileType: 1 = TextFile (e2k)
# Type: 1 = New Model
ret = SapModel.File.ImportFile(e2k_path, 1, 1)
print(f"ImportFile ret = {ret}")

if ret != 0:
    print("WARNING: ImportFile returned non-zero. Trying FileType=0...")
    ret = SapModel.File.ImportFile(e2k_path, 0, 1)
    print(f"ImportFile (FileType=0) ret = {ret}")

# Refresh view
SapModel.View.RefreshView(0, False)
print("View refreshed.")

# Step 4: Save as AGENT BUILD.EDB
print("\n" + "=" * 60)
print("Step 4: Saving as AGENT BUILD.EDB...")
print("=" * 60)

save_path = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\Y21\AGENTBUILD\AGENT BUILD.EDB"
ret = SapModel.File.Save(save_path)
print(f"Save ret = {ret}")

# Verify model was imported correctly
print("\n" + "=" * 60)
print("Verification: Checking imported model...")
print("=" * 60)

ret = SapModel.Story.GetStories_2(
    0.0, 0, [], [], [], [], [], [], [], []
)
if isinstance(ret, tuple) and len(ret) > 2:
    num = ret[2]
    names = ret[3]
    print(f"Number of stories: {num}")
    if names:
        print(f"Stories: {list(names)}")

ret_frames = SapModel.FrameObj.GetAllFrames(
    0, [], [], [], [], [],
    [], [], [], [], [], [],
    [], [], [], [], [], [], [], []
)
if isinstance(ret_frames, tuple) and len(ret_frames) > 1:
    print(f"Number of frame objects: {ret_frames[1]}")

num_areas = 0
area_names = []
ret_areas = SapModel.AreaObj.GetNameList(num_areas, area_names)
if isinstance(ret_areas, tuple) and len(ret_areas) > 1:
    print(f"Number of area objects: {ret_areas[1]}")

print("\n" + "=" * 60)
print("Step 5: Running analysis...")
print("=" * 60)

DOF = [True, True, True, True, True, True]
ret = SapModel.Analyze.SetActiveDOF(DOF)
print(f"SetActiveDOF ret = {ret}")

ret = SapModel.Analyze.SetRunCaseFlag("", True, True)
print(f"SetRunCaseFlag ret = {ret}")

ret = SapModel.File.Save(save_path)
print(f"Save before analysis ret = {ret}")

print("Running analysis... (this may take several minutes)")
t0 = time.time()
ret = SapModel.Analyze.RunAnalysis()
elapsed = time.time() - t0
print(f"RunAnalysis ret = {ret} (took {elapsed:.1f}s)")

if ret == 0:
    print("Analysis completed successfully!")
else:
    print(f"Analysis returned code: {ret}")

# Step 6: Run concrete design
print("\n" + "=" * 60)
print("Step 6: Running concrete design...")
print("=" * 60)

ret = SapModel.DesignConcrete.SetCode("ACI 318-19")
print(f"SetCode ACI 318-19 ret = {ret}")

print("Running concrete design...")
t0 = time.time()
ret = SapModel.DesignConcrete.StartDesign()
elapsed = time.time() - t0
print(f"StartDesign ret = {ret} (took {elapsed:.1f}s)")

if ret == 0:
    print("Concrete design completed successfully!")
else:
    print(f"Concrete design returned code: {ret}")

ret = SapModel.File.Save(save_path)
print(f"Final save ret = {ret}")

SapModel.View.RefreshView(0, False)

print("\n" + "=" * 60)
print("DONE! Model rebuilt, analyzed, and designed.")
print(f"Saved to: {save_path}")
print("=" * 60)
