"""
Fix B building columns: change SRC~ sections to C~ sections in MERGED_v5.
Only B building uses SRC-prefixed column sections (SRC100X100C420, etc.)
The other buildings (A/C/D) already use C-prefixed sections.
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

def parse_src_modifiers(filepath):
    """Parse SRC section modifier data from B building e2k file."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    sections = {}
    for m in re.finditer(r'FRAMESECTION\s+"(SRC[^"]+)"\s+(.+)', content):
        name = m.group(1)
        rest = m.group(2)

        if name not in sections:
            sections[name] = {}

        mat_m = re.search(r'MATERIAL\s+"([^"]+)"', rest)
        if mat_m:
            sections[name]['material'] = mat_m.group(1)

        d_m = re.search(r'\bD\s+([\d.]+)', rest)
        b_m = re.search(r'\bB\s+([\d.]+)', rest)
        if d_m:
            sections[name]['D'] = float(d_m.group(1))
        if b_m:
            sections[name]['B'] = float(b_m.group(1))

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

    # SRC sections used in B building columns
    src_names = ['SRC100X100C420', 'SRC120X120C420', 'SRC130X130C420', 'SRC150X150C420']
    c_names = ['C100X100C420', 'C120X120C420', 'C130X130C420', 'C150X150C420']
    src_to_c = dict(zip(src_names, c_names))

    # Parse SRC section data from B building e2k
    print("\n[STEP 1] Parsing SRC section data from B building e2k...")
    src_data = parse_src_modifiers('ETABS REF/大陳/B/2026-0303_B_SC_KpKvKw.e2k')
    for name in src_names:
        if name in src_data:
            d = src_data[name]
            print(f"  {name}: D={d.get('D')}, B={d.get('B')}, mat={d.get('material')}")
            mods = {k: v for k, v in d.items() if 'Mod' in k and v != 1.0}
            if mods:
                print(f"    Modifiers: {mods}")
        else:
            print(f"  {name}: NOT FOUND in e2k")

    # Check which sections exist in ETABS
    print("\n[STEP 2] Checking existing sections in ETABS...")
    ret = SapModel.PropFrame.GetNameList(0, [])
    etabs_sections = set(ret[1]) if ret[0] > 0 else set()

    for src, c in src_to_c.items():
        src_exists = src in etabs_sections
        c_exists = c in etabs_sections
        print(f"  {src}: {'EXISTS' if src_exists else 'MISSING'}  ->  {c}: {'EXISTS' if c_exists else 'MISSING'}")

    # Create C sections if they don't exist (copy from SRC)
    print("\n[STEP 3] Creating missing C sections...")
    for src, c in src_to_c.items():
        if c not in etabs_sections and src in etabs_sections:
            # Get SRC section properties
            try:
                ret = SapModel.PropFrame.GetRectangle(src, '', 0, 0)
                mat = ret[0]
                t3 = ret[1]
                t2 = ret[2]
                print(f"  Creating {c}: mat={mat}, t3={t3}, t2={t2}")
                ret2 = SapModel.PropFrame.SetRectangle(c, mat, t3, t2)
                print(f"    SetRectangle ret={ret2}")

                # Copy modifiers from SRC
                ret_mod = SapModel.PropFrame.GetModifiers(src, [])
                src_mods = list(ret_mod[0]) if isinstance(ret_mod[0], (list, tuple)) else list(ret_mod)
                ret3 = SapModel.PropFrame.SetModifiers(c, src_mods)
                ret_code = ret3[-1] if isinstance(ret3, (list, tuple)) else ret3
                print(f"    SetModifiers ret={ret_code}, mods={src_mods}")
            except Exception as e:
                print(f"    ERROR creating {c}: {e}")
        elif c in etabs_sections:
            print(f"  {c} already exists - checking modifiers match SRC...")
            # Make sure C section has same modifiers as SRC
            try:
                ret_src = SapModel.PropFrame.GetModifiers(src, [])
                src_mods = list(ret_src[0]) if isinstance(ret_src[0], (list, tuple)) else list(ret_src)
                ret_c = SapModel.PropFrame.GetModifiers(c, [])
                c_mods = list(ret_c[0]) if isinstance(ret_c[0], (list, tuple)) else list(ret_c)
                if src_mods != c_mods:
                    print(f"    SRC mods: {src_mods}")
                    print(f"    C   mods: {c_mods}")
                    print(f"    Copying SRC modifiers to C section...")
                    ret3 = SapModel.PropFrame.SetModifiers(c, src_mods)
                    ret_code = ret3[-1] if isinstance(ret3, (list, tuple)) else ret3
                    print(f"    SetModifiers ret={ret_code}")
                else:
                    print(f"    Modifiers already match")
            except Exception as e:
                print(f"    ERROR: {e}")

    # Find all frames using SRC sections and reassign to C
    print("\n[STEP 4] Reassigning frames from SRC to C sections...")

    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [],
        [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])
    num_frames = ret[0]
    print(f"  Total frames: {num_frames}")

    reassigned = 0
    errors = 0
    reassign_by_section = {}

    for i in range(num_frames):
        frame_name = ret[1][i]
        section_name = ret[2][i]

        if section_name in src_to_c:
            new_section = src_to_c[section_name]
            try:
                ret2 = SapModel.FrameObj.SetSection(frame_name, new_section)
                if ret2 == 0:
                    reassigned += 1
                    if section_name not in reassign_by_section:
                        reassign_by_section[section_name] = 0
                    reassign_by_section[section_name] += 1
                else:
                    errors += 1
                    print(f"    FAIL: {frame_name} ({section_name} -> {new_section}), ret={ret2}")
            except Exception as e:
                errors += 1
                print(f"    ERROR: {frame_name}: {e}")

    print(f"\n  Reassigned: {reassigned}")
    print(f"  Errors: {errors}")
    for src, count in sorted(reassign_by_section.items()):
        print(f"    {src} -> {src_to_c[src]}: {count} frames")

    # Verify - check no frames still use SRC sections
    print("\n[STEP 5] Verifying no frames use SRC sections...")
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [],
        [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])
    still_src = 0
    for i in range(ret[0]):
        if ret[2][i].startswith('SRC'):
            still_src += 1
            print(f"  STILL SRC: {ret[1][i]} -> {ret[2][i]}")

    if still_src == 0:
        print("  All SRC sections replaced!")
    else:
        print(f"  WARNING: {still_src} frames still use SRC sections")

    # Save
    output = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v5.EDB'
    SapModel.File.Save(output)
    print(f"\nSaved to: {output}")
    SapModel.View.RefreshView(0, False)
    print("Done!")

if __name__ == '__main__':
    main()
