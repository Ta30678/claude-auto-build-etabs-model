"""
Inspect current ETABS model state: grids, stories, materials,
sections, frame objects, area objects, load patterns, etc.
"""
import sys
import comtypes.client
comtypes.client.gen_dir = None
from collections import Counter

def connect_to_etabs():
    """Try multiple methods to connect to running ETABS."""
    # Method 1: GetActiveObject
    try:
        etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        print("Connected via GetActiveObject")
        return etabs
    except:
        print("GetActiveObject failed, trying helper...")

    # Method 2: Helper with process ID
    try:
        import psutil
        helper = comtypes.client.CreateObject("ETABSv1.Helper")
        helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)
        pid = None
        for proc in psutil.process_iter():
            if "etabs" in proc.name().lower():
                pid = proc.pid
                break
        if pid:
            print(f"Found ETABS process with PID {pid}")
            etabs = helper.GetObjectProcess("CSI.ETABS.API.ETABSObject", pid)
            print("Connected via GetObjectProcess")
            return etabs
    except Exception as e:
        print(f"Helper method failed: {e}")

    # Method 3: CreateObject with ProgID
    try:
        helper = comtypes.client.CreateObject("ETABSv1.Helper")
        helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)
        etabs = helper.GetObject("CSI.ETABS.API.ETABSObject")
        print("Connected via GetObject")
        return etabs
    except Exception as e:
        print(f"GetObject failed: {e}")

    return None


etabs = connect_to_etabs()
if etabs is None:
    print("ERROR: Could not connect to ETABS.")
    sys.exit(1)

SapModel = etabs.SapModel
filename = SapModel.GetModelFilename()
print(f"Model file: {filename}")

output_lines = []

def log(msg=""):
    print(msg)
    output_lines.append(str(msg))


# ============================================================
# 1. Current Units
# ============================================================
log("=" * 60)
log("CURRENT UNITS")
log("=" * 60)
units = SapModel.GetPresentUnits()
unit_names = {
    1: "lb_in_F", 2: "lb_ft_F", 3: "kip_in_F", 4: "kip_ft_F",
    5: "kN_mm_C", 6: "kN_m_C", 7: "kgf_mm_C", 8: "kgf_m_C",
    9: "N_mm_C", 10: "N_m_C", 11: "Ton_mm_C", 12: "Ton_m_C",
    13: "kN_cm_C", 14: "kgf_cm_C", 15: "N_cm_C", 16: "Ton_cm_C",
}
log(f"Unit code: {units} ({unit_names.get(units, 'unknown')})")

# ============================================================
# Helper to read a database table
# ============================================================
def read_table(table_name):
    """Read a database table and return (fields, records_list_of_lists)"""
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            table_name, [], "All", 0, [], 0, []
        )
        fields = list(ret[2])
        num_records = ret[3]
        data = ret[4]
        num_fields = len(fields)
        rows = []
        for i in range(num_records):
            row = list(data[i * num_fields : (i + 1) * num_fields])
            rows.append(row)
        return fields, rows
    except Exception as e:
        return None, str(e)


# ============================================================
# 2. Grid Lines
# ============================================================
log()
log("=" * 60)
log("GRID LINES")
log("=" * 60)
fields, rows = read_table("Grid Lines")
if fields is not None:
    log(f"Fields: {fields}")
    log(f"Number of records: {len(rows)}")
    for i, row in enumerate(rows):
        log(f"  Row {i}: {row}")
else:
    log(f"Error reading Grid Lines: {rows}")

# ============================================================
# 3. Story Definitions
# ============================================================
log()
log("=" * 60)
log("STORY DEFINITIONS")
log("=" * 60)
fields, rows = read_table("Story Definitions")
if fields is not None:
    log(f"Fields: {fields}")
    log(f"Number of records: {len(rows)}")
    for i, row in enumerate(rows):
        log(f"  Row {i}: {row}")
else:
    log(f"Error reading Story Definitions: {rows}")

# ============================================================
# 4. Materials
# ============================================================
log()
log("=" * 60)
log("MATERIAL PROPERTIES")
log("=" * 60)

mat_tables = [
    "Material Properties - Summary",
    "Material Properties - Basic Mechanical Properties",
]
for tname in mat_tables:
    log(f"--- {tname} ---")
    fields, rows = read_table(tname)
    if fields is not None:
        log(f"  Fields: {fields}")
        log(f"  Number of records: {len(rows)}")
        for i, row in enumerate(rows):
            log(f"    Row {i}: {row}")
    else:
        log(f"  Error: {rows}")

# ============================================================
# 5. Frame Section Properties
# ============================================================
log()
log("=" * 60)
log("FRAME SECTION PROPERTIES")
log("=" * 60)

frame_sec_tables = [
    "Frame Section Property Definitions - Summary",
    "Frame Section Property Definitions - Concrete Rectangular",
    "Frame Section Property Definitions - Concrete Column Rebar",
    "Frame Section Property Definitions - Concrete Beam Rebar",
]
for tname in frame_sec_tables:
    log(f"--- {tname} ---")
    fields, rows = read_table(tname)
    if fields is not None:
        log(f"  Fields: {fields}")
        log(f"  Number of records: {len(rows)}")
        for i, row in enumerate(rows):
            log(f"    Row {i}: {row}")
    else:
        log(f"  (not available or error: {rows})")

# ============================================================
# 6. Area Section Properties
# ============================================================
log()
log("=" * 60)
log("AREA SECTION PROPERTIES")
log("=" * 60)

area_sec_tables = [
    "Area Section Property Definitions - Summary",
    "Area Section Property Definitions - Slab",
]
for tname in area_sec_tables:
    log(f"--- {tname} ---")
    fields, rows = read_table(tname)
    if fields is not None:
        log(f"  Fields: {fields}")
        log(f"  Number of records: {len(rows)}")
        for i, row in enumerate(rows):
            log(f"    Row {i}: {row}")
    else:
        log(f"  (not available or error: {rows})")

# ============================================================
# 7. Frame Objects Summary
# ============================================================
log()
log("=" * 60)
log("FRAME OBJECTS")
log("=" * 60)
try:
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [], [], [], [], [], [], [],
        [], [], [], [], [], [], [], []
    )
    num_frames = ret[0]
    names = ret[1] if num_frames > 0 else []
    props = ret[2] if num_frames > 0 else []
    stories = ret[3] if num_frames > 0 else []
    pt1names = ret[4] if num_frames > 0 else []
    pt2names = ret[5] if num_frames > 0 else []
    log(f"Total frame objects: {num_frames}")
    if num_frames > 0:
        prop_counts = Counter(props)
        log("Frames by section property:")
        for prop, count in sorted(prop_counts.items()):
            log(f"  {prop}: {count}")

        story_counts = Counter(stories)
        log("Frames by story:")
        for story, count in sorted(story_counts.items()):
            log(f"  {story}: {count}")

        log(f"First 30 frames (of {num_frames}):")
        for i in range(min(30, num_frames)):
            log(f"  {names[i]}: Section={props[i]}, Story={stories[i]}, P1={pt1names[i]}, P2={pt2names[i]}")
except Exception as e:
    log(f"Error getting frame objects: {e}")

# ============================================================
# 8. Area Objects Summary
# ============================================================
log()
log("=" * 60)
log("AREA OBJECTS")
log("=" * 60)
try:
    ret = SapModel.AreaObj.GetNameList(0, [])
    num_areas = ret[0]
    area_names = ret[1] if num_areas > 0 else []
    log(f"Total area objects: {num_areas}")
    if num_areas > 0:
        log(f"Area object names (first 30): {list(area_names[:30])}")
        area_props = []
        for i in range(num_areas):
            try:
                prop_ret = SapModel.AreaObj.GetProperty(area_names[i], "")
                area_props.append(prop_ret[0])
            except:
                area_props.append("?")
        prop_counts = Counter(area_props)
        log("Area objects by section property:")
        for prop, count in sorted(prop_counts.items()):
            log(f"  {prop}: {count}")
except Exception as e:
    log(f"Error getting area objects: {e}")

# ============================================================
# 9. Point Objects (joints)
# ============================================================
log()
log("=" * 60)
log("POINT OBJECTS (JOINTS)")
log("=" * 60)
try:
    ret = SapModel.PointObj.GetNameList(0, [])
    num_pts = ret[0]
    log(f"Total point objects: {num_pts}")
except Exception as e:
    log(f"Error: {e}")

# ============================================================
# 10. Load Patterns
# ============================================================
log()
log("=" * 60)
log("LOAD PATTERNS")
log("=" * 60)
fields, rows = read_table("Load Pattern Definitions")
if fields is not None:
    log(f"Fields: {fields}")
    log(f"Number of records: {len(rows)}")
    for i, row in enumerate(rows):
        log(f"  Row {i}: {row}")
else:
    log(f"Error: {rows}")

# ============================================================
# 11. Load Cases
# ============================================================
log()
log("=" * 60)
log("LOAD CASES")
log("=" * 60)
fields, rows = read_table("Load Case Definitions")
if fields is not None:
    log(f"Fields: {fields}")
    log(f"Number of records: {len(rows)}")
    for i, row in enumerate(rows):
        log(f"  Row {i}: {row}")
else:
    log(f"Error: {rows}")

# ============================================================
# 12. Load Combinations
# ============================================================
log()
log("=" * 60)
log("LOAD COMBINATIONS")
log("=" * 60)
fields, rows = read_table("Load Combination Definitions")
if fields is not None:
    log(f"Fields: {fields}")
    log(f"Number of records: {len(rows)}")
    for i, row in enumerate(rows[:50]):
        log(f"  Row {i}: {row}")
    if len(rows) > 50:
        log(f"  ... ({len(rows) - 50} more rows)")
else:
    log(f"Error: {rows}")

# ============================================================
# 13. Diaphragms
# ============================================================
log()
log("=" * 60)
log("DIAPHRAGM DEFINITIONS")
log("=" * 60)
try:
    ret = SapModel.Diaphragm.GetNameList(0, [])
    num_dia = ret[0]
    dia_names = ret[1] if num_dia > 0 else []
    log(f"Diaphragms ({num_dia}): {list(dia_names)}")
except Exception as e:
    log(f"Error: {e}")

# ============================================================
# 14. Pier Labels
# ============================================================
log()
log("=" * 60)
log("PIER LABELS")
log("=" * 60)
try:
    ret = SapModel.PierLabel.GetNameList(0, [])
    num_piers = ret[0]
    pier_names = ret[1] if num_piers > 0 else []
    log(f"Piers ({num_piers}): {list(pier_names)}")
except Exception as e:
    log(f"Error: {e}")

# ============================================================
# 15. Spandrel Labels
# ============================================================
log()
log("=" * 60)
log("SPANDREL LABELS")
log("=" * 60)
try:
    ret = SapModel.SpandrelLabel.GetNameList(0, [])
    num_sp = ret[0]
    sp_names = ret[1] if num_sp > 0 else []
    log(f"Spandrels ({num_sp}): {list(sp_names)}")
except Exception as e:
    log(f"Error: {e}")

# ============================================================
# 16. Groups
# ============================================================
log()
log("=" * 60)
log("GROUPS")
log("=" * 60)
try:
    ret = SapModel.GroupDef.GetNameList(0, [])
    num_groups = ret[0]
    group_names = ret[1] if num_groups > 0 else []
    log(f"Groups ({num_groups}): {list(group_names)}")
except Exception as e:
    log(f"Error: {e}")

# ============================================================
# 17. Available Tables (for reference)
# ============================================================
log()
log("=" * 60)
log("ALL AVAILABLE DATABASE TABLES")
log("=" * 60)
try:
    ret = SapModel.DatabaseTables.GetAllTables(0, [], 0, [])
    num_tables = ret[0]
    table_names = ret[1]
    log(f"Total available tables: {num_tables}")
    for i in range(num_tables):
        log(f"  {table_names[i]}")
except Exception as e:
    log(f"Error: {e}")

# ============================================================
# Save output to markdown file
# ============================================================
output_path = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\etabs_current_state.md"
with open(output_path, "w", encoding="utf-8") as f:
    f.write("# ETABS Model Current State\n\n")
    f.write(f"**Model file:** {filename}\n\n")
    f.write("```\n")
    for line in output_lines:
        f.write(line + "\n")
    f.write("```\n")

log()
log(f"Output saved to: {output_path}")
log("DONE - Model state inspection complete.")
