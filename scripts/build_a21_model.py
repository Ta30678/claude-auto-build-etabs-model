"""
A21 Building Model Builder
===========================
Builds the structural model for Grid Lines 6-9, A-D (3F and above)
with basement extension to Grid 5-9, A-E (2F and below).

Grid dimensions (from architectural plans, in cm → converted to m):
X-direction:  1→2: 8.60, 2→3: 8.60, 3→4: 8.60, 4→5: 8.60,
              5→6: 9.00, 6→7: 8.60, 7→8: 10.80, 8→9: 8.60
Y-direction:  A→B: 9.15, B→C: 7.60, C→D: 9.15, D→E: 10.00,
              E→F: 9.70, F→G: 6.70, G→H: 9.70
"""

import comtypes.client
import psutil
import sys

# ============================================================
# STEP 0: Connect to ETABS
# ============================================================
pid = None
for proc in psutil.process_iter():
    if 'etabs' in proc.name().lower():
        pid = proc.pid
        break

if pid is None:
    print("ERROR: ETABS is not running!")
    sys.exit(1)

helper = comtypes.client.CreateObject('ETABSv1.Helper')
helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)
EtabsObject = helper.GetObjectProcess('CSI.ETABS.API.ETABSObject', pid)

if EtabsObject is None:
    print("ERROR: Cannot connect to ETABS!")
    sys.exit(1)

SapModel = EtabsObject.SapModel
print(f"Connected to: {SapModel.GetModelFilename()}")
print(f"Units: {SapModel.GetPresentUnits()}")

# Unlock model
SapModel.SetModelIsLocked(False)

# Set units to Ton_m_C (code 12)
SapModel.SetPresentUnits(12)

# ============================================================
# STEP 1: Define Grid Coordinates (absolute, in meters)
# ============================================================

# X-direction grid positions (cumulative from Grid 1 = 0)
grid_x = {
    '1': 0.00,
    '2': 8.60,
    '3': 17.20,
    '4': 25.80,
    '5': 34.40,
    '6': 43.40,
    '7': 52.00,
    '8': 62.80,
    '9': 71.40,
}

# Y-direction grid positions (cumulative from Grid A = 0)
grid_y = {
    'A': 0.00,
    'B': 9.15,
    'C': 16.75,
    'D': 25.90,
    'E': 35.90,
    'F': 45.60,
    'G': 52.30,
    'H': 62.00,
}

# ============================================================
# STEP 2: Define Building Zones
# ============================================================

# Upper floors (3F and above): Grid 6-9, A-D
upper_x_grids = ['6', '7', '8', '9']
upper_y_grids = ['A', 'B', 'C', 'D']

# Lower floors (2F and below): Extend one span outward
# Left: add Grid 5, Top: add Grid E
lower_x_grids = ['5', '6', '7', '8', '9']
lower_y_grids = ['A', 'B', 'C', 'D', 'E']

# Story definitions (from model)
# Lower floors = B3F, B2F, B1F, 1F, 2F
# Upper floors = 3F through PRF
lower_stories = ['B3F', 'B2F', 'B1F', '1F', '2F']
upper_stories = ['3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F',
                 '11F', '12F', '13F', '14F', 'R1F', 'R2F', 'R3F', 'PRF']

# Story elevations (from ETABS model)
story_elevations = {
    'B3F': -10.10, 'B2F': -6.90, 'B1F': -3.70,
    '1F': 0.40, '2F': 5.00,
    '3F': 8.40, '4F': 11.80, '5F': 15.20, '6F': 18.60,
    '7F': 22.00, '8F': 25.40, '9F': 28.80, '10F': 32.20,
    '11F': 35.60, '12F': 39.00, '13F': 42.40, '14F': 45.80,
    'R1F': 49.20, 'R2F': 52.20, 'R3F': 55.20, 'PRF': 58.20,
}

# Base elevation (bottom of B3F columns)
base_elev = -10.10 - 2.30  # bottom of B3F story = -12.40

# ============================================================
# STEP 3: Define Section Assignments
# ============================================================

# Default sections (can be updated later when exact sizes are known)
# For columns: use larger sections for lower floors, smaller for upper
col_sections = {
    'basement': 'C70X90C350',    # B3F-2F: 70x90 C350
    'lower': 'C70X80C350',       # 3F-7F: 70x80 C350
    'mid': 'C70X75C350',         # 8F-14F: 70x75 C350
    'upper': 'C70X70C350',       # R1F-PRF: 70x70 C350 (if exists)
}

# For beams: X-direction and Y-direction
beam_sections = {
    'basement': 'B50X80C350',    # B3F-2F
    'lower': 'B50X70C350',       # 3F-7F
    'mid': 'B45X80C350',         # 8F-14F
    'upper': 'B45X70C350',       # R1F-PRF
}

def get_col_section(story):
    if story in lower_stories:
        return col_sections['basement']
    elif story in ['3F', '4F', '5F', '6F', '7F']:
        return col_sections['lower']
    elif story in ['8F', '9F', '10F', '11F', '12F', '13F', '14F']:
        return col_sections['mid']
    else:
        return col_sections['upper']

def get_beam_section(story):
    if story in lower_stories:
        return beam_sections['basement']
    elif story in ['3F', '4F', '5F', '6F', '7F']:
        return beam_sections['lower']
    elif story in ['8F', '9F', '10F', '11F', '12F', '13F', '14F']:
        return beam_sections['mid']
    else:
        return beam_sections['upper']

# ============================================================
# STEP 4: Create Grid Lines via Database Tables
# ============================================================
print("\n=== Setting up Grid Lines ===")

# We'll set grid lines using the database table approach
# First, let's try to set them via the GridSys interface
try:
    # Check if a grid system exists
    ret = SapModel.GridSys.GetNameList(0, [])
    existing_grids = ret[1] if ret[0] > 0 else []
    print(f"Existing grid systems: {existing_grids}")
except:
    existing_grids = []

# Create a Cartesian grid system if none exists
grid_sys_name = "Grid1"
if grid_sys_name not in existing_grids:
    # Set grid system using database tables
    # First get the table for editing
    TableKey = "Grid Lines"
    FieldKeyList = []
    GroupName = ""
    TableVersion = 0
    FieldsKeysIncluded = []
    NumberRecords = 0
    TableData = []

    # Build grid line data
    # Format: GridSysName, LineDir(X/Y), GridID, XorY_Ordinate, LineType(Primary/Secondary), Visible, BubbleLoc
    grid_data = []

    # X-direction grid lines (these are vertical lines at X positions)
    for name, x_val in grid_x.items():
        grid_data.append([grid_sys_name, "X (Cartesian)", name, str(x_val), "Primary", "Yes", "End"])

    # Y-direction grid lines (horizontal lines at Y positions)
    for name, y_val in grid_y.items():
        grid_data.append([grid_sys_name, "Y (Cartesian)", name, str(y_val), "Primary", "Yes", "Start"])

    print(f"Grid data prepared: {len(grid_data)} grid lines")

    # Try setting via DatabaseTables
    try:
        fields = ["Name", "Line Direction", "Grid ID", "Ordinate", "Line Type", "Visible", "Bubble Location"]
        num_records = len(grid_data)
        flat_data = []
        for row in grid_data:
            flat_data.extend(row)

        ret = SapModel.DatabaseTables.SetTableForEditingArray(
            TableKey, TableVersion, fields, num_records, flat_data
        )
        print(f"SetTableForEditingArray: {ret}")

        ret = SapModel.DatabaseTables.ApplyEditedTables(True, 0, 0, 0, 0, "")
        print(f"ApplyEditedTables: ret={ret[0]}, errors={ret[1]}, error_msgs={ret[2]}, warns={ret[3]}")
        if ret[2] > 0:
            print(f"  Error log: {ret[5]}")
    except Exception as e:
        print(f"Database table approach failed: {e}")
        print("Will set grid lines individually...")

print("Grid lines setup complete.")

# ============================================================
# STEP 5: Create Columns
# ============================================================
print("\n=== Creating Columns ===")

all_stories_ordered = ['B3F', 'B2F', 'B1F', '1F', '2F',
                       '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F',
                       '11F', '12F', '13F', '14F', 'R1F', 'R2F', 'R3F', 'PRF']

# Get the bottom elevation for columns (base of B3F)
base_z = story_elevations['B3F'] - 2.30  # -12.40

col_count = 0
beam_count = 0

# Track column top points for beam creation
# column_points[story][(gx, gy)] = point_name or coordinates

for story_idx, story in enumerate(all_stories_ordered):
    elev = story_elevations[story]

    # Determine which grids to use for this story
    if story in lower_stories:
        x_grids = lower_x_grids
        y_grids = lower_y_grids
    else:
        x_grids = upper_x_grids
        y_grids = upper_y_grids

    col_section = get_col_section(story)

    # Get the bottom elevation of this story's columns
    if story_idx == 0:
        bot_z = base_z
    else:
        bot_z = story_elevations[all_stories_ordered[story_idx - 1]]
        # But we need to check if this column existed in the previous story
        # For simplicity, column bottom = previous story elevation (top of column below)

    top_z = elev

    for gx in x_grids:
        for gy in y_grids:
            x = grid_x[gx]
            y = grid_y[gy]

            # Check if this column existed in the previous story
            # If story transitions from lower to upper and grid is outside upper range, skip
            if story_idx > 0:
                prev_story = all_stories_ordered[story_idx - 1]
                if prev_story in lower_stories:
                    prev_bot_z = story_elevations[prev_story] if story_idx > 1 else base_z
                else:
                    prev_bot_z = story_elevations[all_stories_ordered[story_idx - 1]]

            # Create column (vertical frame from bot_z to top_z)
            name = ''
            try:
                ret = SapModel.FrameObj.AddByCoord(x, y, bot_z, x, y, top_z, name, col_section)
                if ret[0] == 0:
                    col_count += 1
                    frame_name = ret[1] if len(ret) > 1 else ''
                else:
                    print(f"  Column at ({gx},{gy}) story {story}: ret={ret[0]}")
            except Exception as e:
                print(f"  Error creating column at ({gx},{gy}) story {story}: {e}")

print(f"Columns created: {col_count}")

# ============================================================
# STEP 6: Create Beams
# ============================================================
print("\n=== Creating Beams ===")

for story in all_stories_ordered:
    elev = story_elevations[story]

    # Determine which grids to use
    if story in lower_stories:
        x_grids = lower_x_grids
        y_grids = lower_y_grids
    else:
        x_grids = upper_x_grids
        y_grids = upper_y_grids

    beam_section = get_beam_section(story)

    # X-direction beams (along X, between adjacent X grids at each Y grid)
    for gy in y_grids:
        y = grid_y[gy]
        for i in range(len(x_grids) - 1):
            x1 = grid_x[x_grids[i]]
            x2 = grid_x[x_grids[i + 1]]
            name = ''
            try:
                ret = SapModel.FrameObj.AddByCoord(x1, y, elev, x2, y, elev, name, beam_section)
                if ret[0] == 0:
                    beam_count += 1
            except Exception as e:
                print(f"  Error beam X ({x_grids[i]}-{x_grids[i+1]},{gy}) {story}: {e}")

    # Y-direction beams (along Y, between adjacent Y grids at each X grid)
    for gx in x_grids:
        x = grid_x[gx]
        for j in range(len(y_grids) - 1):
            y1 = grid_y[y_grids[j]]
            y2 = grid_y[y_grids[j + 1]]
            name = ''
            try:
                ret = SapModel.FrameObj.AddByCoord(x, y1, elev, x, y2, elev, name, beam_section)
                if ret[0] == 0:
                    beam_count += 1
            except Exception as e:
                print(f"  Error beam Y ({gx},{y_grids[j]}-{y_grids[j+1]}) {story}: {e}")

print(f"Beams created: {beam_count}")

# ============================================================
# STEP 7: Assign Restraints at Base
# ============================================================
print("\n=== Assigning Base Restraints ===")

# Find all points at the base elevation and assign fixed supports
base_points = []
ret = SapModel.PointObj.GetNameList(0, [])
if ret[0] > 0:
    for pt_name in ret[1]:
        coord = SapModel.PointObj.GetCoordCartesian(pt_name, 0, 0, 0)
        z = coord[2]
        if abs(z - base_z) < 0.01:  # at base level
            base_points.append(pt_name)

print(f"Found {len(base_points)} base points")

restraint_count = 0
for pt_name in base_points:
    restraint = [True, True, True, True, True, True]  # Fixed
    try:
        ret = SapModel.PointObj.SetRestraint(pt_name, restraint)
        if ret == 0:
            restraint_count += 1
    except Exception as e:
        print(f"  Error setting restraint for {pt_name}: {e}")

print(f"Restraints assigned: {restraint_count}")

# ============================================================
# STEP 8: Refresh and Save
# ============================================================
print("\n=== Refreshing View and Saving ===")
SapModel.View.RefreshView(0, False)

model_path = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\A21\A21 TEST.EDB'
ret = SapModel.File.Save(model_path)
print(f"Save result: {ret}")

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 50)
print("MODEL BUILD SUMMARY")
print("=" * 50)
print(f"Grid Lines: X={list(grid_x.keys())}, Y={list(grid_y.keys())}")
print(f"Columns created: {col_count}")
print(f"Beams created: {beam_count}")
print(f"Base restraints: {restraint_count}")
print(f"Upper floors (3F-PRF): Grid 6-9, A-D")
print(f"Lower floors (B3F-2F): Grid 5-9, A-E")
print(f"Column sections: {col_sections}")
print(f"Beam sections: {beam_sections}")

# Final check
ret = SapModel.FrameObj.GetNameList(0, [])
print(f"\nTotal frame objects in model: {ret[0]}")
ret = SapModel.PointObj.GetNameList(0, [])
print(f"Total point objects in model: {ret[0]}")
