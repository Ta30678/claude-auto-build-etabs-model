"""
Copy all 16F objects (frames + areas) to 17F with all properties.
"""
import sys
import json
sys.path.insert(0, r"C:\Users\User\Desktop\V22 AGENTIC MODEL\scripts")
from etabs_connection import attach_to_etabs

EtabsObject, SapModel = attach_to_etabs()

# Story height offset from 16F to 17F
DZ = 340.0  # cm

# Unlock model
SapModel.SetModelIsLocked(False)

# =============================================================
# STEP 1: Collect all 16F frame info
# =============================================================
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    'Frame Assignments - Summary', [], 'All', 0, [], 0, [])
fields = ret[2]
nr = ret[3]
data = ret[4]
nf = len(fields)
si = list(fields).index('Story')
ui = list(fields).index('UniqueName')
li = list(fields).index('Label')
ti = list(fields).index('Type')

f16_unames = []
f16_labels = []
f16_types = []
for i in range(nr):
    row = data[i*nf:(i+1)*nf]
    if row[si] == '16F':
        f16_unames.append(row[ui])
        f16_labels.append(row[li])
        f16_types.append(row[ti])

print(f"Found {len(f16_unames)} frames on 16F")

# Collect detailed properties for each frame
frames_data = []
for idx, uname in enumerate(f16_unames):
    label = f16_labels[idx]
    ftype = f16_types[idx]

    # Get point names
    ret = SapModel.FrameObj.GetPoints(uname, '', '')
    pt1_name = ret[0]
    pt2_name = ret[1]

    # Get coordinates
    ret1 = SapModel.PointObj.GetCoordCartesian(str(pt1_name), 0.0, 0.0, 0.0)
    x1, y1, z1 = ret1[0], ret1[1], ret1[2]
    ret2 = SapModel.PointObj.GetCoordCartesian(str(pt2_name), 0.0, 0.0, 0.0)
    x2, y2, z2 = ret2[0], ret2[1], ret2[2]

    # Get section and auto-select
    ret = SapModel.FrameObj.GetSection(uname, '', '')
    section = ret[0]
    autoselect = ret[1]

    # Get end releases
    try:
        ret = SapModel.FrameObj.GetReleases(uname,
            [False]*6, [False]*6, [0.0]*6, [0.0]*6)
        ii_releases = list(ret[0])  # I-end
        jj_releases = list(ret[1])  # J-end
        ii_values = list(ret[2])
        jj_values = list(ret[3])
    except:
        ii_releases = [False]*6
        jj_releases = [False]*6
        ii_values = [0.0]*6
        jj_values = [0.0]*6

    # Get rigid end offsets (end length offsets)
    try:
        ret = SapModel.FrameObj.GetEndLengthOffset(uname, False, 0.0, 0.0, 0.0)
        auto_offset = ret[0]
        length1 = ret[1]
        length2 = ret[2]
        rigid_factor = ret[3]
    except:
        auto_offset = False
        length1 = 0.0
        length2 = 0.0
        rigid_factor = 0.0

    # Get insertion point and cardinal point
    try:
        ret = SapModel.FrameObj.GetInsertionPoint(uname, 0, False,
            [False]*3, [0.0]*3, [0.0]*3)
        cardinal_pt = ret[0]
        mirror2 = ret[1]
        stiffTransform = ret[2]
        offset1 = list(ret[3])
        offset2 = list(ret[4])
    except:
        cardinal_pt = 10  # centroid default
        mirror2 = False
        stiffTransform = True
        offset1 = [0.0]*3
        offset2 = [0.0]*3

    # Get property modifiers
    try:
        ret = SapModel.FrameObj.GetModifiers(uname, [1.0]*8)
        modifiers = list(ret[0])
    except:
        modifiers = [1.0]*8

    # Get label (pier/spandrel)
    try:
        ret = SapModel.FrameObj.GetPier(uname, '')
        pier = ret[0]
    except:
        pier = ''

    try:
        ret = SapModel.FrameObj.GetSpandrel(uname, '')
        spandrel = ret[0]
    except:
        spandrel = ''

    fd = {
        'uname': uname, 'label': label, 'type': ftype,
        'x1': x1, 'y1': y1, 'z1': z1,
        'x2': x2, 'y2': y2, 'z2': z2,
        'section': section, 'autoselect': autoselect,
        'ii_releases': ii_releases, 'jj_releases': jj_releases,
        'ii_values': ii_values, 'jj_values': jj_values,
        'auto_offset': auto_offset, 'length1': length1,
        'length2': length2, 'rigid_factor': rigid_factor,
        'cardinal_pt': cardinal_pt, 'mirror2': mirror2,
        'stiffTransform': stiffTransform,
        'offset1': offset1, 'offset2': offset2,
        'modifiers': modifiers,
        'pier': pier, 'spandrel': spandrel,
        'pt1_name': pt1_name, 'pt2_name': pt2_name,
    }
    frames_data.append(fd)

print(f"Collected {len(frames_data)} frame records with all properties")

# Show some sample data
for f in frames_data[:3]:
    print(f"\n{f['label']} ({f['type']}): sec={f['section']}")
    print(f"  ({f['x1']},{f['y1']},{f['z1']})->({f['x2']},{f['y2']},{f['z2']})")
    print(f"  releases I={f['ii_releases']} J={f['jj_releases']}")
    print(f"  rigid: auto={f['auto_offset']}, L1={f['length1']}, L2={f['length2']}, factor={f['rigid_factor']}")
    print(f"  cardinal={f['cardinal_pt']}, modifiers={f['modifiers']}")
    print(f"  pier={f['pier']}, spandrel={f['spandrel']}")

# =============================================================
# STEP 2: Collect 16F area object info
# =============================================================
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    'Area Assignments - Summary', [], 'All', 0, [], 0, [])
afields = ret[2]
anr = ret[3]
adata = ret[4]
anf = len(afields)
asi = list(afields).index('Story')
aui = list(afields).index('UniqueName')
ali = list(afields).index('Label')
asect_i = list(afields).index('SectProp')

a16_unames = []
a16_labels = []
a16_sections = []
for i in range(anr):
    row = adata[i*anf:(i+1)*anf]
    if row[asi] == '16F':
        a16_unames.append(row[aui])
        a16_labels.append(row[ali])
        a16_sections.append(row[asect_i])

print(f"\nFound {len(a16_unames)} areas on 16F")

areas_data = []
for idx, uname in enumerate(a16_unames):
    # Get number of points
    ret = SapModel.AreaObj.GetPoints(uname, 0, [])
    num_pts = ret[0]
    pt_names = ret[1]

    # Get coordinates of all points
    coords = []
    for pn in pt_names:
        ret = SapModel.PointObj.GetCoordCartesian(str(pn), 0.0, 0.0, 0.0)
        coords.append((ret[0], ret[1], ret[2]))

    # Get section
    ret = SapModel.AreaObj.GetProperty(uname, '')
    area_section = ret[0]

    # Get property modifiers
    try:
        ret = SapModel.AreaObj.GetModifiers(uname, [1.0]*10)
        area_mods = list(ret[0])
    except:
        area_mods = [1.0]*10

    # Get diaphragm
    try:
        ret = SapModel.AreaObj.GetDiaphragm(uname, '')
        diaphragm = ret[0]
    except:
        diaphragm = ''

    # Get pier
    try:
        ret = SapModel.AreaObj.GetPier(uname, '')
        area_pier = ret[0]
    except:
        area_pier = ''

    # Get spandrel
    try:
        ret = SapModel.AreaObj.GetSpandrel(uname, '')
        area_spandrel = ret[0]
    except:
        area_spandrel = ''

    ad = {
        'uname': uname, 'label': a16_labels[idx],
        'section': area_section,
        'num_pts': num_pts, 'pt_names': list(pt_names),
        'coords': coords,
        'modifiers': area_mods,
        'diaphragm': diaphragm,
        'pier': area_pier, 'spandrel': area_spandrel,
    }
    areas_data.append(ad)

print(f"Collected {len(areas_data)} area records")
for a in areas_data[:3]:
    print(f"\n{a['label']}: sec={a['section']}, pts={a['num_pts']}")
    for c in a['coords']:
        print(f"  ({c[0]},{c[1]},{c[2]})")
    print(f"  diaphragm={a['diaphragm']}, pier={a['pier']}, spandrel={a['spandrel']}")

# Save collected data
with open(r"C:\Users\User\Desktop\V22 AGENTIC MODEL\scripts\f16_data.json", 'w') as f:
    json.dump({'frames': frames_data, 'areas': areas_data}, f, indent=2, default=str)
print("\nData saved to f16_data.json")
