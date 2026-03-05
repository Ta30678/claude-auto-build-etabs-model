"""
Fix SRC section property modifiers and materials in MERGED_v5 ETABS model.

The SRC sections were imported as plain 'Concrete Rectangular' without their
property modifiers (JMOD, I2MOD, I3MOD, MMOD, WMOD).

Uses PropFrame.SetModifiers(Name, [A, As2, As3, J, I22, I33, Mass, Weight])
and PropFrame.SetRectangle for material changes.
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

def parse_src_modifiers_from_e2k(filepath):
    """Parse SRC section modifier data from e2k file."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    sections = {}
    for m in re.finditer(r'FRAMESECTION\s+"(SRC[^"]+)"\s+(.+)', content):
        name = m.group(1)
        rest = m.group(2)

        if name not in sections:
            sections[name] = {'AMod': 1.0, 'A2Mod': 1.0, 'A3Mod': 1.0,
                              'JMod': 1.0, 'I2Mod': 1.0, 'I3Mod': 1.0,
                              'MMod': 1.0, 'WMod': 1.0}

        mat_m = re.search(r'MATERIAL\s+"([^"]+)"', rest)
        if mat_m:
            sections[name]['material'] = mat_m.group(1)

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
    SapModel.SetPresentUnits(12)  # TON/M
    SapModel.SetModelIsLocked(False)

    # ===== STEP 1: Parse source e2k files =====
    print("\n[STEP 1] Parsing SRC section modifiers from source e2k files...")

    files = [
        'ETABS REF/大陳/A/2026-0303_A_SC_KpKvKw.e2k',
        'ETABS REF/大陳/B/2026-0303_B_SC_KpKvKw.e2k',
        'ETABS REF/大陳/C/2026-0304_C_SC_KpKvKw.e2k',
        'ETABS REF/大陳/D/2026-0303_D_SC_KpKvKw.e2k',
    ]

    all_src_mods = {}
    for filepath in files:
        mods = parse_src_modifiers_from_e2k(filepath)
        for name, data in mods.items():
            if name not in all_src_mods:
                all_src_mods[name] = data
            else:
                for k, v in data.items():
                    if k not in all_src_mods[name]:
                        all_src_mods[name][k] = v

    src_with_mods = {k: v for k, v in all_src_mods.items()
                     if v.get('JMod', 1.0) != 1.0 or v.get('I2Mod', 1.0) != 1.0}
    print(f"  Found {len(src_with_mods)} SRC sections with non-default modifiers")

    # ===== STEP 2: Get ETABS section list =====
    print("\n[STEP 2] Checking ETABS sections...")

    ret = SapModel.PropFrame.GetNameList(0, [])
    etabs_sections = set(ret[1]) if ret[0] > 0 else set()

    sections_to_fix = {}
    for name, mods in src_with_mods.items():
        if name in etabs_sections:
            sections_to_fix[name] = mods

    print(f"  SRC sections in ETABS to fix: {len(sections_to_fix)}")

    # ===== STEP 3: Create C420SRC material if needed =====
    print("\n[STEP 3] Checking materials...")

    ret = SapModel.PropMaterial.GetNameList(0, [])
    existing_mats = set(ret[1]) if ret[0] > 0 else set()

    need_c420src = any(v.get('material') == 'C420SRC' for v in sections_to_fix.values())
    if need_c420src and 'C420SRC' not in existing_mats:
        print("  Creating C420SRC material...")
        if 'C420' in existing_mats:
            ret = SapModel.PropMaterial.AddMaterial('C420SRC', 2, "", "", "")
            try:
                ret_iso = SapModel.PropMaterial.GetMPIsotropic('C420', 0, 0, 0)
                SapModel.PropMaterial.SetMPIsotropic('C420SRC', ret_iso[0], ret_iso[1], ret_iso[2])
            except:
                pass
            try:
                ret_wm = SapModel.PropMaterial.GetWeightAndMass('C420', 0, 0)
                SapModel.PropMaterial.SetWeightAndMass('C420SRC', ret_wm[0], ret_wm[1])
            except:
                pass
            print("  Created C420SRC")
    elif 'C420SRC' in existing_mats:
        print("  C420SRC already exists")

    # ===== STEP 4: Apply modifiers =====
    print("\n[STEP 4] Applying property modifiers...")

    fixed_mods = 0
    fixed_mat = 0
    errors = 0

    for name, data in sorted(sections_to_fix.items()):
        # ModValue = [Area, As2, As3, Torsion, I22, I33, Mass, Weight]
        mod_array = [
            data.get('AMod', 1.0),
            data.get('A2Mod', 1.0),
            data.get('A3Mod', 1.0),
            data.get('JMod', 1.0),
            data.get('I2Mod', 1.0),
            data.get('I3Mod', 1.0),
            data.get('MMod', 1.0),
            data.get('WMod', 1.0),
        ]

        try:
            ret = SapModel.PropFrame.SetModifiers(name, mod_array)
            if ret == 0:
                fixed_mods += 1
                print(f"  {name}: Set modifiers J={data.get('JMod',1):.4f} "
                      f"I2={data.get('I2Mod',1):.4f} I3={data.get('I3Mod',1):.4f} "
                      f"M={data.get('MMod',1):.4f} W={data.get('WMod',1):.4f}")
            else:
                print(f"  {name}: SetModifiers returned {ret}")
                errors += 1
        except Exception as e:
            print(f"  {name}: Error setting modifiers: {e}")
            errors += 1

        # Fix material if needed
        if 'material' in data and data['material'] == 'C420SRC':
            try:
                # Get current section dimensions
                ret_props = SapModel.PropFrame.GetRectangle(name, '', 0, 0)
                if isinstance(ret_props, (list, tuple)) and len(ret_props) >= 4:
                    current_mat = ret_props[0]
                    t3 = ret_props[1]
                    t2 = ret_props[2]
                    if current_mat != 'C420SRC':
                        ret = SapModel.PropFrame.SetRectangle(name, 'C420SRC', t3, t2)
                        if ret == 0:
                            fixed_mat += 1
                            print(f"    Material: {current_mat} -> C420SRC")
                        else:
                            print(f"    Material change failed: ret={ret}")
            except Exception as e:
                print(f"    Material change error: {e}")

    print(f"\n  Modifiers fixed: {fixed_mods}")
    print(f"  Materials fixed: {fixed_mat}")
    print(f"  Errors: {errors}")

    # ===== STEP 5: Verify =====
    print("\n[STEP 5] Verifying...")

    # Spot-check a few sections
    for name in ['SRC100X100C420', 'SRC120X120C420', 'SRC150X150C420', 'SRC180X80C56SD490']:
        if name in sections_to_fix:
            try:
                ret = SapModel.PropFrame.GetModifiers(name, [])
                if isinstance(ret, (list, tuple)):
                    mods = ret[0] if isinstance(ret[0], (list, tuple)) else ret
                    print(f"  {name}: {list(mods)}")
            except Exception as e:
                print(f"  {name}: Verify error: {e}")

    # ===== STEP 6: Also fix non-column SRC sections (beams, braces) =====
    # Check if there are more SRC sections in the e2k that are in ETABS but weren't processed
    all_src_in_etabs = [s for s in etabs_sections if s.startswith('SRC')]
    not_fixed = [s for s in all_src_in_etabs if s not in sections_to_fix]
    if not_fixed:
        print(f"\n  Note: {len(not_fixed)} SRC sections in ETABS without modifier data:")
        for s in sorted(not_fixed)[:10]:
            print(f"    {s}")

    # ===== STEP 7: Save =====
    output = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v5.EDB'
    SapModel.File.Save(output)
    print(f"\nSaved to: {output}")

    SapModel.View.RefreshView(0, False)
    print("Done!")

if __name__ == '__main__':
    main()
