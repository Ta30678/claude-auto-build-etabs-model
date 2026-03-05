"""
Create 17F objects by copying 16F with Z offset = 340cm.
All properties preserved: sections, end releases, rigid zones, modifiers, loads, etc.
"""
import sys
sys.path.insert(0, r"C:\Users\User\Desktop\V22 AGENTIC MODEL\scripts")
from etabs_connection import attach_to_etabs

EtabsObject, SapModel = attach_to_etabs()

DZ = 340.0  # Story height offset

# Unlock model
ret = SapModel.SetModelIsLocked(False)
print(f"Model unlocked: ret={ret}")

# =============================================================
# STEP 1: Collect 16F frame data
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

f16_info = []
for i in range(nr):
    row = data[i*nf:(i+1)*nf]
    if row[si] == '16F':
        f16_info.append({
            'uname': row[ui],
            'label': row[li],
            'type': row[ti]
        })

print(f"\n=== Collecting 16F frame data ({len(f16_info)} frames) ===")

frames_data = []
for fi in f16_info:
    uname = fi['uname']
    ftype = fi['type']
    label = fi['label']

    # Coordinates
    ret = SapModel.FrameObj.GetPoints(uname, '', '')
    pt1_name, pt2_name = ret[0], ret[1]

    ret1 = SapModel.PointObj.GetCoordCartesian(str(pt1_name), 0.0, 0.0, 0.0)
    x1, y1, z1 = ret1[0], ret1[1], ret1[2]
    ret2 = SapModel.PointObj.GetCoordCartesian(str(pt2_name), 0.0, 0.0, 0.0)
    x2, y2, z2 = ret2[0], ret2[1], ret2[2]

    # Section
    ret = SapModel.FrameObj.GetSection(uname, '', '')
    section, autoselect = ret[0], ret[1]

    # End releases
    try:
        ret = SapModel.FrameObj.GetReleases(uname, [False]*6, [False]*6, [0.0]*6, [0.0]*6)
        ii_rel, jj_rel = list(ret[0]), list(ret[1])
        ii_val, jj_val = list(ret[2]), list(ret[3])
    except:
        ii_rel = jj_rel = [False]*6
        ii_val = jj_val = [0.0]*6

    # Rigid end offsets
    try:
        ret = SapModel.FrameObj.GetEndLengthOffset(uname, False, 0.0, 0.0, 0.0)
        auto_off, len1, len2, rfactor = ret[0], ret[1], ret[2], ret[3]
    except:
        auto_off, len1, len2, rfactor = False, 0.0, 0.0, 0.0

    # Insertion point
    try:
        ret = SapModel.FrameObj.GetInsertionPoint(uname, 0, False, [False]*3, [0.0]*3, [0.0]*3)
        card_pt = ret[0]
        mirror2 = ret[1]
        stiff_tf = ret[2]
        off1 = list(ret[3])
        off2 = list(ret[4])
    except:
        card_pt = 10
        mirror2 = False
        stiff_tf = True
        off1 = off2 = [0.0]*3

    # Property modifiers
    try:
        ret = SapModel.FrameObj.GetModifiers(uname, [1.0]*8)
        mods = list(ret[0])
    except:
        mods = [1.0]*8

    # Distributed loads
    dist_loads = []
    try:
        ret = SapModel.FrameObj.GetLoadDistributed(uname, 0, [], [], [], [], [], [], [], [], [], [], [])
        n_loads = ret[0]
        if n_loads > 0:
            for j in range(n_loads):
                dist_loads.append({
                    'lp': ret[2][j],      # load pattern
                    'mytype': ret[3][j],   # 1=force, 2=moment
                    'csys': ret[4][j],     # coord system
                    'dir': ret[5][j],      # direction
                    'rd1': ret[6][j],      # rel dist start
                    'rd2': ret[7][j],      # rel dist end
                    'val1': ret[10][j],    # value start
                    'val2': ret[11][j],    # value end
                })
    except:
        pass

    frames_data.append({
        'uname': uname, 'label': label, 'type': ftype,
        'x1': x1, 'y1': y1, 'z1': z1,
        'x2': x2, 'y2': y2, 'z2': z2,
        'section': section, 'autoselect': autoselect,
        'ii_rel': ii_rel, 'jj_rel': jj_rel,
        'ii_val': ii_val, 'jj_val': jj_val,
        'auto_off': auto_off, 'len1': len1, 'len2': len2, 'rfactor': rfactor,
        'card_pt': card_pt, 'mirror2': mirror2, 'stiff_tf': stiff_tf,
        'off1': off1, 'off2': off2,
        'mods': mods,
        'dist_loads': dist_loads,
    })

print(f"Collected {len(frames_data)} frames")
beams = [f for f in frames_data if f['type'] == 'Beam']
cols = [f for f in frames_data if f['type'] == 'Column']
print(f"  Beams: {len(beams)}, Columns: {len(cols)}")

# =============================================================
# STEP 2: Collect 16F area data
# =============================================================
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    'Area Assignments - Summary', [], 'All', 0, [], 0, [])
afields = ret[2]
anr = ret[3]
adata = ret[4]
anf = len(afields)
asi = list(afields).index('Story')
aui = list(afields).index('UniqueName')

a16_unames = []
for i in range(anr):
    row = adata[i*anf:(i+1)*anf]
    if row[asi] == '16F':
        a16_unames.append(row[aui])

print(f"\n=== Collecting 16F area data ({len(a16_unames)} areas) ===")

areas_data = []
for uname in a16_unames:
    # Points and coordinates
    ret = SapModel.AreaObj.GetPoints(uname, 0, [])
    num_pts = ret[0]
    pt_names = ret[1]

    coords = []
    for pn in pt_names:
        ret = SapModel.PointObj.GetCoordCartesian(str(pn), 0.0, 0.0, 0.0)
        coords.append((ret[0], ret[1], ret[2]))

    # Section
    ret = SapModel.AreaObj.GetProperty(uname, '')
    area_section = ret[0]

    # Modifiers
    try:
        ret = SapModel.AreaObj.GetModifiers(uname, [1.0]*10)
        area_mods = list(ret[0])
    except:
        area_mods = [1.0]*10

    # Diaphragm
    try:
        ret = SapModel.AreaObj.GetDiaphragm(uname, '')
        diaph = ret[0] if ret[0] else ''
    except:
        diaph = ''

    # Uniform loads
    uni_loads = []
    try:
        ret = SapModel.AreaObj.GetLoadUniform(uname, 0, [], [], [], [], [])
        n_loads = ret[0]
        if n_loads > 0:
            for j in range(n_loads):
                uni_loads.append({
                    'lp': ret[2][j],    # load pattern
                    'csys': ret[3][j],  # coord system
                    'dir': ret[4][j],   # direction
                    'val': ret[5][j],   # value
                })
    except:
        pass

    areas_data.append({
        'uname': uname,
        'num_pts': num_pts, 'coords': coords,
        'section': area_section,
        'mods': area_mods,
        'diaphragm': diaph,
        'uni_loads': uni_loads,
    })

print(f"Collected {len(areas_data)} areas")

# =============================================================
# STEP 3: Create 17F columns (bottom at 16F elev, top at 17F elev)
# =============================================================
print(f"\n=== Creating 17F columns ({len(cols)}) ===")
col_new_names = {}
col_errors = 0
for c in cols:
    # 16F columns: z1=5140 (15F), z2=5480 (16F)
    # 17F columns: z1=5480 (16F), z2=5820 (17F)
    new_z1 = c['z1'] + DZ
    new_z2 = c['z2'] + DZ

    new_name = ''
    sec_to_use = c['section']

    ret = SapModel.FrameObj.AddByCoord(
        c['x1'], c['y1'], new_z1,
        c['x2'], c['y2'], new_z2,
        new_name, sec_to_use)

    if ret[-1] != 0:
        print(f"  ERROR creating column at ({c['x1']},{c['y1']},{new_z1})->({c['x2']},{c['y2']},{new_z2}): ret={ret[-1]}")
        col_errors += 1
        continue

    new_name = ret[0]
    col_new_names[c['uname']] = new_name
    print(f"  Created column {new_name} (from {c['label']}): sec={sec_to_use}")

    # Apply properties
    # End releases
    if any(c['ii_rel']) or any(c['jj_rel']):
        SapModel.FrameObj.SetReleases(new_name, c['ii_rel'], c['jj_rel'], c['ii_val'], c['jj_val'])

    # Rigid end offsets
    SapModel.FrameObj.SetEndLengthOffset(new_name, c['auto_off'], c['len1'], c['len2'], c['rfactor'])

    # Insertion point
    SapModel.FrameObj.SetInsertionPoint(new_name, c['card_pt'], c['mirror2'], c['stiff_tf'], c['off1'], c['off2'])

    # Modifiers (only if non-default)
    if c['mods'] != [1.0]*8:
        SapModel.FrameObj.SetModifiers(new_name, c['mods'])

print(f"Columns created: {len(col_new_names)}, errors: {col_errors}")

# =============================================================
# STEP 4: Create 17F beams (at 17F elevation)
# =============================================================
print(f"\n=== Creating 17F beams ({len(beams)}) ===")
beam_new_names = {}
beam_errors = 0
for b in beams:
    # Beams: offset z by DZ
    new_z1 = b['z1'] + DZ
    new_z2 = b['z2'] + DZ

    new_name = ''
    # If autoselect is set, use that; otherwise use section
    sec_to_use = b['section']

    ret = SapModel.FrameObj.AddByCoord(
        b['x1'], b['y1'], new_z1,
        b['x2'], b['y2'], new_z2,
        new_name, sec_to_use)

    if ret[-1] != 0:
        print(f"  ERROR creating beam at ({b['x1']},{b['y1']},{new_z1})->({b['x2']},{b['y2']},{new_z2}): ret={ret[-1]}")
        beam_errors += 1
        continue

    new_name = ret[0]
    beam_new_names[b['uname']] = new_name
    print(f"  Created beam {new_name} (from {b['label']}): sec={sec_to_use}")

    # If autoselect was set, assign the auto-select list
    if b['autoselect'] and b['autoselect'] != 'N.A.' and b['autoselect'] != 'None':
        try:
            SapModel.FrameObj.SetSection(new_name, b['autoselect'])
        except:
            pass

    # End releases
    if any(b['ii_rel']) or any(b['jj_rel']):
        SapModel.FrameObj.SetReleases(new_name, b['ii_rel'], b['jj_rel'], b['ii_val'], b['jj_val'])

    # Rigid end offsets
    SapModel.FrameObj.SetEndLengthOffset(new_name, b['auto_off'], b['len1'], b['len2'], b['rfactor'])

    # Insertion point
    SapModel.FrameObj.SetInsertionPoint(new_name, b['card_pt'], b['mirror2'], b['stiff_tf'], b['off1'], b['off2'])

    # Modifiers (only if non-default)
    if b['mods'] != [1.0]*8:
        SapModel.FrameObj.SetModifiers(new_name, b['mods'])

    # Distributed loads
    for ld in b['dist_loads']:
        SapModel.FrameObj.SetLoadDistributed(
            new_name, ld['lp'], ld['mytype'], ld['dir'],
            ld['rd1'], ld['rd2'], ld['val1'], ld['val2'],
            ld['csys'])

print(f"Beams created: {len(beam_new_names)}, errors: {beam_errors}")

# =============================================================
# STEP 5: Create 17F areas (at 17F elevation)
# =============================================================
print(f"\n=== Creating 17F areas ({len(areas_data)}) ===")
area_new_names = {}
area_errors = 0
for a in areas_data:
    n = a['num_pts']
    # Offset Z coordinates by DZ
    X = [c[0] for c in a['coords']]
    Y = [c[1] for c in a['coords']]
    Z = [c[2] + DZ for c in a['coords']]

    new_name = ''
    ret = SapModel.AreaObj.AddByCoord(n, X, Y, Z, new_name, a['section'])

    if ret[-1] != 0:
        print(f"  ERROR creating area: ret={ret[-1]}")
        area_errors += 1
        continue

    new_name = ret[0]
    area_new_names[a['uname']] = new_name
    print(f"  Created area {new_name} (from {a['uname']}): sec={a['section']}")

    # Modifiers
    if a['mods'] != [1.0]*10:
        SapModel.AreaObj.SetModifiers(new_name, a['mods'])

    # Diaphragm
    if a['diaphragm'] and a['diaphragm'] not in ('', 'None', None):
        try:
            SapModel.AreaObj.SetDiaphragm(new_name, a['diaphragm'])
        except:
            pass

    # Uniform loads
    for ld in a['uni_loads']:
        SapModel.AreaObj.SetLoadUniform(new_name, ld['lp'], ld['val'], ld['dir'], True, ld['csys'])

print(f"Areas created: {len(area_new_names)}, errors: {area_errors}")

# =============================================================
# STEP 6: Refresh and verify
# =============================================================
SapModel.View.RefreshView(0, False)

# Verify 17F now has objects
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    'Frame Assignments - Summary', [], 'All', 0, [], 0, [])
fields = ret[2]
nr = ret[3]
data = ret[4]
nf = len(fields)
si = list(fields).index('Story')
f17_count = sum(1 for i in range(nr) if data[i*nf + si] == '17F')

ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    'Area Assignments - Summary', [], 'All', 0, [], 0, [])
afields = ret[2]
anr = ret[3]
adata = ret[4]
anf = len(afields)
asi = list(afields).index('Story')
a17_count = sum(1 for i in range(anr) if adata[i*anf + asi] == '17F')

print(f"\n=== VERIFICATION ===")
print(f"17F frames: {f17_count} (expected: 82)")
print(f"17F areas: {a17_count} (expected: 45)")
print(f"\nTotal created: {len(col_new_names)} columns + {len(beam_new_names)} beams + {len(area_new_names)} areas")
print("Done!")
