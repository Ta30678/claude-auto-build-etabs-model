"""
Fix ALL column section property modifiers in MERGED_v5 ETABS model.
This includes both SRC sections (already fixed) and regular C sections.
"""
import comtypes.client
from comtypes.gen import ETABSv1
import subprocess
import re

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

def parse_all_section_modifiers(filepath):
    """Parse ALL frame section modifier data from e2k file."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    sections = {}
    for m in re.finditer(r'FRAMESECTION\s+"([^"]+)"\s+(.+)', content):
        name = m.group(1)
        rest = m.group(2)

        if name not in sections:
            sections[name] = {}

        for e2k_key, db_key in [
            ('JMOD', 'JMod'), ('I2MOD', 'I2Mod'), ('I3MOD', 'I3Mod'),
            ('MMOD', 'MMod'), ('WMOD', 'WMod'),
            ('AMOD', 'AMod'), ('A2MOD', 'A2Mod'), ('A3MOD', 'A3Mod'),
        ]:
            mod_m = re.search(e2k_key + r'\s+([\d.E+-]+)', rest, re.IGNORECASE)
            if mod_m:
                sections[name][db_key] = float(mod_m.group(1))

    return sections

def main():
    SapModel, pid = connect_etabs()
    if not SapModel:
        print("ERROR: Cannot connect to ETABS")
        return
    print(f"Connected to ETABS PID {pid}")
    SapModel.SetPresentUnits(12)
    SapModel.SetModelIsLocked(False)

    # Parse ALL source e2k files
    print("\n[STEP 1] Parsing section modifiers from all source e2k files...")

    files = [
        'ETABS REF/大陳/A/2026-0303_A_SC_KpKvKw.e2k',
        'ETABS REF/大陳/B/2026-0303_B_SC_KpKvKw.e2k',
        'ETABS REF/大陳/C/2026-0304_C_SC_KpKvKw.e2k',
        'ETABS REF/大陳/D/2026-0303_D_SC_KpKvKw.e2k',
    ]

    all_mods = {}
    for filepath in files:
        mods = parse_all_section_modifiers(filepath)
        for name, data in mods.items():
            if name not in all_mods:
                all_mods[name] = data
            else:
                for k, v in data.items():
                    if k not in all_mods[name]:
                        all_mods[name][k] = v

    # Filter to sections with non-default modifiers
    sections_with_mods = {k: v for k, v in all_mods.items()
                          if v.get('JMod', 1.0) != 1.0 or v.get('I2Mod', 1.0) != 1.0
                          or v.get('I3Mod', 1.0) != 1.0}
    print(f"  Found {len(sections_with_mods)} sections with non-default modifiers")

    # Get ETABS section list
    ret = SapModel.PropFrame.GetNameList(0, [])
    etabs_sections = set(ret[1]) if ret[0] > 0 else set()

    # Find sections that exist in ETABS and need fixing
    to_fix = {}
    for name, mods in sections_with_mods.items():
        if name in etabs_sections:
            to_fix[name] = mods

    print(f"  Sections in ETABS to fix: {len(to_fix)}")

    # Check which ones already have correct modifiers
    already_correct = 0
    needs_update = {}

    for name, expected_mods in to_fix.items():
        try:
            ret = SapModel.PropFrame.GetModifiers(name, [])
            current = list(ret[0]) if isinstance(ret[0], (list, tuple)) else list(ret)

            # ModValue = [Area, As2, As3, Torsion, I22, I33, Mass, Weight]
            expected_array = [
                expected_mods.get('AMod', 1.0),
                expected_mods.get('A2Mod', 1.0),
                expected_mods.get('A3Mod', 1.0),
                expected_mods.get('JMod', 1.0),
                expected_mods.get('I2Mod', 1.0),
                expected_mods.get('I3Mod', 1.0),
                expected_mods.get('MMod', 1.0),
                expected_mods.get('WMod', 1.0),
            ]

            # Check if already matching
            match = all(abs(current[i] - expected_array[i]) < 0.001 for i in range(8))
            if match:
                already_correct += 1
            else:
                needs_update[name] = expected_array
        except:
            needs_update[name] = [
                expected_mods.get('AMod', 1.0),
                expected_mods.get('A2Mod', 1.0),
                expected_mods.get('A3Mod', 1.0),
                expected_mods.get('JMod', 1.0),
                expected_mods.get('I2Mod', 1.0),
                expected_mods.get('I3Mod', 1.0),
                expected_mods.get('MMod', 1.0),
                expected_mods.get('WMod', 1.0),
            ]

    print(f"  Already correct: {already_correct}")
    print(f"  Need updating: {len(needs_update)}")

    # Apply modifiers
    if needs_update:
        print(f"\n[STEP 2] Applying modifiers to {len(needs_update)} sections...")

        success = 0
        fail = 0
        for name, mod_array in sorted(needs_update.items()):
            ret = SapModel.PropFrame.SetModifiers(name, mod_array)
            # ret is a tuple: (returned_mods_tuple, return_code)
            ret_code = ret[-1] if isinstance(ret, (list, tuple)) else ret
            if ret_code == 0:
                success += 1
                j = mod_array[3]
                i2 = mod_array[4]
                i3 = mod_array[5]
                mm = mod_array[6]
                print(f"  {name}: J={j}, I2={i2}, I3={i3}, M={mm}")
            else:
                fail += 1
                print(f"  {name}: FAILED (ret={ret_code})")

        print(f"\n  Success: {success}, Fail: {fail}")

    # Verify
    print(f"\n[STEP 3] Verifying all column sections...")

    all_correct = 0
    still_wrong = 0

    for name, expected_mods in sorted(to_fix.items()):
        try:
            ret = SapModel.PropFrame.GetModifiers(name, [])
            current = list(ret[0]) if isinstance(ret[0], (list, tuple)) else list(ret)

            expected_j = expected_mods.get('JMod', 1.0)
            expected_i2 = expected_mods.get('I2Mod', 1.0)
            expected_i3 = expected_mods.get('I3Mod', 1.0)

            if (abs(current[3] - expected_j) < 0.001 and
                abs(current[4] - expected_i2) < 0.001 and
                abs(current[5] - expected_i3) < 0.001):
                all_correct += 1
            else:
                still_wrong += 1
                print(f"  WRONG: {name}: got J={current[3]}, I2={current[4]}, I3={current[5]}, "
                      f"expected J={expected_j}, I2={expected_i2}, I3={expected_i3}")
        except Exception as e:
            still_wrong += 1
            print(f"  ERROR: {name}: {e}")

    print(f"\n  All correct: {all_correct}")
    print(f"  Still wrong: {still_wrong}")

    # Save
    output = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v5.EDB'
    SapModel.File.Save(output)
    print(f"\nSaved to: {output}")
    SapModel.View.RefreshView(0, False)
    print("Done!")

if __name__ == '__main__':
    main()
