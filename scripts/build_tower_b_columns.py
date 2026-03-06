"""
Build Tower B columns for A21 model.
16 column positions (Grid B-E / 5-8) from B3F to R1F,
plus 6 core columns from R2F to PRF.

Uses comtypes connection to ETABS PID 22460.
"""
import comtypes.client
import comtypes.gen.ETABSv1 as E

helper = comtypes.client.CreateObject('ETABSv1.Helper')
helper = helper.QueryInterface(E.cHelper)
etabs = helper.GetObjectProcess('CSI.ETABS.API.ETABSObject', 22460)
sm = etabs.SapModel
sm.SetPresentUnits(12)  # TON/M

# ============================================================
# Story elevations (from model)
# ============================================================
elevations = {
    'BASE': -12.40,
    'B3F':  -10.10,
    'B2F':   -6.90,
    'B1F':   -3.70,
    '1F':     0.40,
    '2F':     5.00,
    '3F':     8.40,
    '4F':    11.80,
    '5F':    15.20,
    '6F':    18.60,
    '7F':    22.00,
    '8F':    25.40,
    '9F':    28.80,
    '10F':   32.20,
    '11F':   35.60,
    '12F':   39.00,
    '13F':   42.40,
    '14F':   45.80,
    'R1F':   49.20,
    'R2F':   52.20,
    'R3F':   55.20,
    'PRF':   58.20,
}

# ============================================================
# Column positions (16 for full tower)
# ============================================================
# 4 Interior positions
interior_positions = [
    ('C', '7', 8.5,  9.0),
    ('D', '7', 19.5, 9.0),
    ('C', '6', 8.5,  17.6),
    ('D', '6', 19.5, 17.6),
]

# 12 Edge positions
edge_positions = [
    ('B', '8', 0.0,   0.0),
    ('C', '8', 8.5,   0.0),
    ('D', '8', 19.5,  0.0),
    ('E', '8', 30.5,  0.0),
    ('B', '7', 0.0,   9.0),
    ('E', '7', 30.5,  9.0),
    ('B', '6', 0.0,   17.6),
    ('E', '6', 30.5,  17.6),
    ('B', '5', 0.0,   27.35),
    ('C', '5', 8.5,   27.35),
    ('D', '5', 19.5,  27.35),
    ('E', '5', 30.5,  27.35),
]

# 6 Core positions (for R2F~PRF)
core_positions = [
    ('C', '7', 8.5,  9.0),
    ('D', '7', 19.5, 9.0),
    ('E', '7', 30.5, 9.0),
    ('E', '6', 30.5, 17.6),
    ('D', '6', 19.5, 17.6),
    ('C', '6', 8.5,  17.6),
]

# ============================================================
# Column section assignments by ETABS story
# ETABS column at story N spans from story (N-1) elevation to story N elevation
# So "ETABS story B3F" means the column from BASE(-12.4) to B3F(-10.1)
#
# Per spec:
#   Plan floor NF -> ETABS story (N+1)F
#   Plan B3F columns -> ETABS B3F story (but we DON'T build B3F story columns
#     because B3F is the foundation floor = BASE+1 layer, no columns there)
#   Plan B3F columns -> ETABS B2F story (column from B3F elev to B2F elev)
#
# Wait -- re-reading the spec carefully:
#   "B3F底=-12.4, B3F頂=-10.1" -> This means at B3F story, z_bottom=-12.4, z_top=-10.1
#   The spec says to use AddByCoord with z_bottom and z_top directly.
#
# But the base layer rule says:
#   "基礎樓層（B3F）不建柱"
#   "柱從基礎樓層的上一層 story 開始建立"
#   So B3F is the foundation floor. No columns at B3F story (BASE to B3F).
#   Columns start from B2F story (B3F to B2F).
#
# HOWEVER, looking at the user's spec more carefully:
#   The user says "B3F | C110X140C350 | C100X120C350"
#   And elevation table: B3F底=-12.4, B3F頂=-10.1
#   This means the B3F column segment goes from -12.4 to -10.1
#
# The base layer rule in system prompt says:
#   "BASE 層：純參考高程，不會有任何物件"
#   "基礎樓層（B3F）：不建立柱往 BASE"
#   "柱從基礎樓層的上一層 story 開始建立"
#
# So BASE=-12.4, 基礎樓層=B3F:
#   B3F story 不建柱 (this would be BASE->B3F segment, i.e., -12.4 to -10.1)
#   Columns start from B2F story (B3F->B2F segment, i.e., -10.1 to -6.9)
#
# BUT the user's instruction table explicitly includes B3F with sections assigned!
# The user says:
#   | B3F | C110X140C350 | C100X120C350 |
#   | B2F ~ 1F | C110X140C350 | C100X120C350 |
# And provides B3F底=-12.4, B3F頂=-10.1
#
# This looks like the user wants B3F columns built (from -12.4 to -10.1).
# The base layer rule applies when there IS a foundation slab at B3F.
# But the user explicitly listed B3F in the column table.
#
# Let me follow the USER'S EXPLICIT INSTRUCTION which takes priority.
# The user listed B3F columns with z_bottom=-12.4, z_top=-10.1.
# ============================================================

# Story sequence for full tower columns (B3F to R1F)
# Each entry: (story_name, z_bottom, z_top)
full_tower_stories = []

story_order = ['B3F', 'B2F', 'B1F', '1F', '2F', '3F', '4F', '5F',
               '6F', '7F', '8F', '9F', '10F', '11F', '12F', '13F', '14F', 'R1F']

elev_order = ['BASE', 'B3F', 'B2F', 'B1F', '1F', '2F', '3F', '4F', '5F',
              '6F', '7F', '8F', '9F', '10F', '11F', '12F', '13F', '14F', 'R1F']

for i, story in enumerate(story_order):
    z_bot = elevations[elev_order[i]]
    z_top = elevations[story]
    full_tower_stories.append((story, z_bot, z_top))

# Core stories (R2F to PRF)
core_stories = []
core_story_order = ['R2F', 'R3F', 'PRF']
core_elev_below = ['R1F', 'R2F', 'R3F']
for i, story in enumerate(core_story_order):
    z_bot = elevations[core_elev_below[i]]
    z_top = elevations[story]
    core_stories.append((story, z_bot, z_top))

# Section assignment by ETABS story for interior and edge
def get_section(story_name, col_type):
    """
    col_type: 'interior' or 'edge'
    Returns the section name for this story.
    """
    if col_type == 'interior':
        if story_name in ['B3F']:
            return 'C110X140C350'
        elif story_name in ['B2F', 'B1F', '1F']:
            return 'C110X140C350'
        elif story_name in ['2F', '3F']:
            return 'C100X120C350'
        elif story_name in ['4F']:
            return 'C100X120C350'
        elif story_name in ['5F']:
            return 'C100X100C350'
        elif story_name in ['6F', '7F', '8F', '9F', '10F']:
            return 'C100X100C280'
        elif story_name in ['11F', '12F', '13F', '14F', 'R1F']:
            return 'C90X90C280'
        elif story_name in ['R2F', 'R3F', 'PRF']:
            return 'C90X90C280'
    else:  # edge
        if story_name in ['B3F']:
            return 'C100X120C350'
        elif story_name in ['B2F', 'B1F', '1F']:
            return 'C100X120C350'
        elif story_name in ['2F', '3F']:
            return 'C100X110C350'
        elif story_name in ['4F']:
            return 'C90X90C350'
        elif story_name in ['5F']:
            return 'C90X90C350'
        elif story_name in ['6F', '7F', '8F', '9F', '10F']:
            return 'C90X90C280'
        elif story_name in ['11F', '12F', '13F', '14F', 'R1F']:
            return 'C90X90C280'
        elif story_name in ['R2F', 'R3F', 'PRF']:
            return 'C90X90C280'
    return None

# ============================================================
# Build columns
# ============================================================
total_columns = 0
errors = []

print("Building Tower B columns...")
print("=" * 60)

# 1. Full tower columns (16 positions x 18 stories = up to 288 columns)
for story_name, z_bot, z_top in full_tower_stories:
    story_count = 0
    # Interior columns
    for gx, gy, x, y in interior_positions:
        section = get_section(story_name, 'interior')
        if section is None:
            errors.append(f"No section for interior col at {story_name}")
            continue
        ret = sm.FrameObj.AddByCoord(x, y, z_bot, x, y, z_top, '', section)
        if ret[-1] == 0:
            total_columns += 1
            story_count += 1
        else:
            errors.append(f"Failed: interior ({gx},{gy}) at {story_name}, ret={ret[-1]}")

    # Edge columns
    for gx, gy, x, y in edge_positions:
        section = get_section(story_name, 'edge')
        if section is None:
            errors.append(f"No section for edge col at {story_name}")
            continue
        ret = sm.FrameObj.AddByCoord(x, y, z_bot, x, y, z_top, '', section)
        if ret[-1] == 0:
            total_columns += 1
            story_count += 1
        else:
            errors.append(f"Failed: edge ({gx},{gy}) at {story_name}, ret={ret[-1]}")

    print(f"  {story_name:5s}: {story_count:3d} columns  (z={z_bot:.2f} to {z_top:.2f})")

# 2. Core columns (6 positions x 3 stories = 18 columns)
print("\nBuilding core columns (R2F~PRF)...")
for story_name, z_bot, z_top in core_stories:
    story_count = 0
    for gx, gy, x, y in core_positions:
        section = 'C90X90C280'
        ret = sm.FrameObj.AddByCoord(x, y, z_bot, x, y, z_top, '', section)
        if ret[-1] == 0:
            total_columns += 1
            story_count += 1
        else:
            errors.append(f"Failed: core ({gx},{gy}) at {story_name}, ret={ret[-1]}")
    print(f"  {story_name:5s}: {story_count:3d} columns  (z={z_bot:.2f} to {z_top:.2f})")

print("=" * 60)
print(f"TOTAL COLUMNS BUILT: {total_columns}")
print(f"  Full tower: 16 pos x 18 stories = {16*18} expected")
print(f"  Core: 6 pos x 3 stories = {6*3} expected")
print(f"  Grand total expected: {16*18 + 6*3}")

if errors:
    print(f"\nERRORS ({len(errors)}):")
    for e in errors:
        print(f"  {e}")
else:
    print("\nNo errors.")

# Verify total frame count
ret_frames = sm.FrameObj.GetNameList(0, [])
print(f"\nTotal frames in model: {ret_frames[0]}")

# Refresh view
sm.View.RefreshView(0, False)
