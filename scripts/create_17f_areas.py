"""
Create 17F area objects by copying 16F with Z offset = 340cm.
"""
import sys
sys.path.insert(0, r"C:\Users\User\Desktop\V22 AGENTIC MODEL\scripts")
from etabs_connection import attach_to_etabs

EtabsObject, SapModel = attach_to_etabs()
DZ = 340.0
SapModel.SetModelIsLocked(False)

# Collect 16F area data
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

print(f"Found {len(a16_unames)} areas on 16F")

areas_data = []
for uname in a16_unames:
    ret = SapModel.AreaObj.GetPoints(uname, 0, [])
    num_pts = ret[0]
    pt_names = ret[1]

    coords = []
    for pn in pt_names:
        ret = SapModel.PointObj.GetCoordCartesian(str(pn), 0.0, 0.0, 0.0)
        coords.append((ret[0], ret[1], ret[2]))

    ret = SapModel.AreaObj.GetProperty(uname, '')
    area_section = ret[0]

    try:
        ret = SapModel.AreaObj.GetModifiers(uname, [1.0]*10)
        area_mods = list(ret[0])
    except:
        area_mods = [1.0]*10

    try:
        ret = SapModel.AreaObj.GetDiaphragm(uname, '')
        diaph = ret[0] if ret[0] else ''
    except:
        diaph = ''

    uni_loads = []
    try:
        ret = SapModel.AreaObj.GetLoadUniform(uname, 0, [], [], [], [], [])
        n_loads = ret[0]
        if n_loads > 0:
            for j in range(n_loads):
                uni_loads.append({
                    'lp': ret[2][j],
                    'csys': ret[3][j],
                    'dir': ret[4][j],
                    'val': ret[5][j],
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

print(f"Collected {len(areas_data)} area records")

# Create 17F areas
created = 0
errors = 0
for a in areas_data:
    n = a['num_pts']
    X = [c[0] for c in a['coords']]
    Y = [c[1] for c in a['coords']]
    Z = [c[2] + DZ for c in a['coords']]

    ret = SapModel.AreaObj.AddByCoord(n, X, Y, Z, '', a['section'])
    # ret[3] = new name, ret[4] = retcode
    retcode = ret[4] if len(ret) > 4 else ret[-1]

    if retcode != 0:
        print(f"  ERROR creating area from {a['uname']}: ret={retcode}")
        errors += 1
        continue

    new_name = ret[3]  # Name is at index 3
    created += 1
    print(f"  Created area {new_name} (from {a['uname']}): sec={a['section']}")

    # Modifiers
    if a['mods'] != [1.0]*10:
        SapModel.AreaObj.SetModifiers(new_name, a['mods'])

    # Diaphragm
    if a['diaphragm'] and a['diaphragm'] not in ('', 'None', None):
        try:
            SapModel.AreaObj.SetDiaphragm(new_name, a['diaphragm'])
        except Exception as e:
            print(f"    Warning: diaphragm assignment failed: {e}")

    # Uniform loads
    for ld in a['uni_loads']:
        try:
            SapModel.AreaObj.SetLoadUniform(new_name, ld['lp'], ld['val'], ld['dir'], True, ld['csys'])
        except Exception as e:
            print(f"    Warning: load assignment failed for LP={ld['lp']}: {e}")

SapModel.View.RefreshView(0, False)

# Verify
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    'Area Assignments - Summary', [], 'All', 0, [], 0, [])
afields = ret[2]
anr = ret[3]
adata = ret[4]
anf = len(afields)
asi = list(afields).index('Story')
a17_count = sum(1 for i in range(anr) if adata[i*anf + asi] == '17F')

print(f"\nCreated: {created}, Errors: {errors}")
print(f"17F area count: {a17_count} (expected: 45)")
print("Done!")
