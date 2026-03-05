"""Check beam sections for D/B swap issue."""
import comtypes.client
from comtypes.gen import ETABSv1
import subprocess

def connect_etabs():
    helper = comtypes.client.CreateObject('ETABSv1.Helper')
    helper = helper.QueryInterface(ETABSv1.cHelper)
    result = subprocess.run(['tasklist'], capture_output=True, text=True)
    pids = [int(line.split()[1]) for line in result.stdout.split('\n') if 'ETABS.exe' in line]
    for pid in pids:
        try:
            etabs = helper.GetObjectProcess('CSI.ETABS.API.ETABSObject', pid)
            if etabs is not None:
                return etabs.SapModel, pid
        except:
            pass
    return None, None

SapModel, pid = connect_etabs()
print(f"Connected to ETABS PID {pid}")
SapModel.SetPresentUnits(12)  # TON/M

# Sections that Agent 2 identified as potentially swapped
check_list = [
    ('FB100X300C42SD490', 3.0, 1.0),
    ('FWB60X300C42SD490', 3.0, 0.6),
    ('FSB80X300C42SD490', 3.0, 0.8),
    ('B65X80C56SD490', 0.8, 0.65),
    ('B50X70C56SD490', 0.7, 0.5),
    ('WB40X70C56SD490', 0.7, 0.4),
    ('WB100X80C56SD490', 0.8, 1.0),
    ('B50X70C28', 0.7, 0.5),
    ('B60X80C560', 0.8, 0.6),
]

# First check if these sections exist
ret = SapModel.PropFrame.GetNameList(0, [])
existing = set(ret[1]) if ret[0] > 0 else set()
print(f"Total frame sections: {ret[0]}")

for sec, exp_d, exp_b in check_list:
    if sec in existing:
        print(f"  {sec}: EXISTS")
    else:
        print(f"  {sec}: NOT FOUND")

# Try getting section properties using GetSectProps
print("\nGetting section properties...")
fix_needed = []

for sec, exp_d, exp_b in check_list:
    if sec not in existing:
        continue
    try:
        # Try GetSectProps which returns more detailed info
        ret = SapModel.PropFrame.GetSectProps(sec, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        # Returns: (A, As2, As3, I22, I33, S22, S33, Z22, Z33, R22, R33, ret)
        area = ret[0]
        i22 = ret[3]
        i33 = ret[4]
        print(f"  {sec}: A={area:.6f}, I22={i22:.6f}, I33={i33:.6f}")

        # For a rectangle: A = D*B, I33 = B*D^3/12, I22 = D*B^3/12
        # We can solve for D and B
        if area > 0:
            # I33/A = D^2/12 -> D = sqrt(12*I33/A)
            # I22/A = B^2/12 -> B = sqrt(12*I22/A)
            import math
            d_calc = math.sqrt(12 * i33 / area) if i33 > 0 else 0
            b_calc = math.sqrt(12 * i22 / area) if i22 > 0 else 0
            ok = (abs(d_calc - exp_d) < 0.01 and abs(b_calc - exp_b) < 0.01)
            status = 'OK' if ok else 'SWAPPED!'
            print(f"    Calculated: D={d_calc:.4f}, B={b_calc:.4f} (expected D={exp_d}, B={exp_b}) -> {status}")
            if not ok:
                fix_needed.append((sec, exp_d, exp_b))
    except Exception as e:
        print(f"  {sec}: GetSectProps error: {e}")
        # Try alternative approach
        try:
            # Use DatabaseTables to get section info
            ret2 = SapModel.DatabaseTables.GetTableForDisplayArray(
                "Frame Section Property Definitions - Summary", [], "All",
                0, [], 0, [])
            if isinstance(ret2, (list, tuple)) and len(ret2) >= 6:
                fields = list(ret2[4])
                num_records = ret2[5]
                data = list(ret2[6])
                num_fields = len(fields)
                print(f"    Table fields: {fields}")
                for r in range(num_records):
                    row = data[r*num_fields:(r+1)*num_fields]
                    if len(row) > 0 and row[0] == sec:
                        print(f"    Row: {dict(zip(fields, row))}")
                        break
        except Exception as e2:
            print(f"    Alt error: {e2}")

# Fix if needed
if fix_needed:
    print(f"\n{'='*60}")
    print(f"Fixing {len(fix_needed)} swapped sections...")
    SapModel.SetModelIsLocked(False)

    for sec, correct_d, correct_b in fix_needed:
        # Get current material
        try:
            ret = SapModel.PropFrame.GetNameList(0, [])
            # Get material from the section
            # Use SetRectangle with correct dimensions
            # First find what material is used
            import re
            mat = 'C280'
            if 'C56' in sec or 'C560' in sec: mat = 'C560SD490'
            elif 'C42' in sec or 'C420' in sec: mat = 'C420SD490'
            elif 'C28' in sec or 'C280' in sec: mat = 'C280SD490'

            ret = SapModel.PropFrame.SetRectangle(sec, mat, correct_d, correct_b)
            status = 'OK' if ret == 0 else f'FAIL(ret={ret})'
            print(f"  Fixed {sec}: D={correct_d}, B={correct_b}, mat={mat} -> {status}")
        except Exception as e:
            print(f"  Error fixing {sec}: {e}")

    output = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v5.EDB'
    SapModel.File.Save(output)
    print(f"\nSaved to: {output}")
else:
    print("\nAll beam sections have correct D/B! No fix needed.")
