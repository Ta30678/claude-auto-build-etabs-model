"""
A21 Model Build - Step 6: Load Patterns, Modal Case, Response Spectrum Cases
Recreate the load definitions that were lost when NewBlank was called.
"""
import comtypes.client
import sys

def connect_etabs():
    try:
        etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        sm = etabs.SapModel
        return etabs, sm
    except Exception as e:
        print(f"[ERROR] Cannot connect to ETABS: {e}")
        sys.exit(1)

def main():
    etabs, sm = connect_etabs()
    sm.SetPresentUnits(12)
    sm.SetModelIsLocked(False)
    print("[OK] Connected, units=TON_M")

    # Check existing load patterns
    lp = sm.LoadPatterns.GetNameList(0, [])
    existing_lp = list(lp[1]) if lp[0] > 0 else []
    print(f"Existing load patterns: {existing_lp}")

    # ============================================================
    # Define Load Patterns
    # ============================================================
    # eLoadPatternType: Dead=1, SuperDead=2, Live=3, ReduceLive=4, Quake=5, Wind=6
    patterns = [
        ("DL",   1, 1),    # Dead with self-weight = 1
        ("LL",   3, 0),    # Live
        ("EQXP", 5, 0),    # Seismic +X
        ("EQXN", 5, 0),    # Seismic -X
        ("EQYP", 5, 0),    # Seismic +Y
        ("EQYN", 5, 0),    # Seismic -Y
    ]

    for name, lp_type, sw_mult in patterns:
        if name in existing_lp:
            print(f"  {name}: already exists, skipping")
            continue
        ret = sm.LoadPatterns.Add(name, lp_type, sw_mult)
        status = "OK" if ret == 0 else f"ret={ret}"
        print(f"  Add('{name}', type={lp_type}, SW={sw_mult}): {status}")

    # Delete the default "Dead" pattern if it exists and we have "DL"
    lp2 = sm.LoadPatterns.GetNameList(0, [])
    lp_names = list(lp2[1])
    if "Dead" in lp_names and "DL" in lp_names:
        ret = sm.LoadPatterns.Delete("Dead")
        print(f"  Deleted default 'Dead' pattern: ret={ret}")

    # Verify load patterns
    lp3 = sm.LoadPatterns.GetNameList(0, [])
    print(f"Load patterns after setup: {list(lp3[1])}")

    # ============================================================
    # Define Modal Analysis Case
    # ============================================================
    # Check if Modal case exists
    lc = sm.LoadCases.GetNameList(0, [])
    lc_names = list(lc[1]) if lc[0] > 0 else []
    print(f"\nExisting load cases: {lc_names}")

    if "Modal" not in lc_names:
        # Create modal case
        ret = sm.LoadCases.ModalEigen.SetCase("Modal")
        print(f"  SetCase('Modal'): ret={ret}")
    else:
        print("  Modal case already exists")

    # Set number of modes = 24 (3 per floor for 8 floors is typical; 24 covers well)
    ret = sm.LoadCases.ModalEigen.SetNumberModes("Modal", 24, 1)
    print(f"  SetNumberModes(24): ret={ret}")

    # ============================================================
    # Define Response Spectrum Load Cases: 0SPECX and 0SPECXY
    # ============================================================
    # These are created as ResponseSpectrum type
    for case_name in ["0SPECX", "0SPECXY"]:
        if case_name not in lc_names:
            ret = sm.LoadCases.ResponseSpectrum.SetCase(case_name)
            print(f"  SetCase('{case_name}'): ret={ret}")
        else:
            print(f"  {case_name} already exists")

    # For now, leave spectrum function assignment for later
    # (needs SPECTRUM.TXT file from model folder)

    # ============================================================
    # Define Load Combinations (U1~U19, EQV)
    # Standard RC building combinations per Taiwan code
    # ============================================================
    # First check existing combos
    rc = sm.RespCombo.GetNameList(0, [])
    existing_combos = list(rc[1]) if rc[0] > 0 else []
    print(f"\nExisting combos: {existing_combos}")

    # Basic combo definitions (simplified - will need EQV scale factor from user)
    combos = {
        "U1":  [("DL", 1.4)],
        "U2":  [("DL", 1.2), ("LL", 1.6)],
        "U3":  [("DL", 1.2), ("LL", 0.5), ("EQXP", 1.0)],
        "U4":  [("DL", 1.2), ("LL", 0.5), ("EQXN", 1.0)],
        "U5":  [("DL", 1.2), ("LL", 0.5), ("EQYP", 1.0)],
        "U6":  [("DL", 1.2), ("LL", 0.5), ("EQYN", 1.0)],
        "U7":  [("DL", 0.9), ("EQXP", 1.0)],
        "U8":  [("DL", 0.9), ("EQXN", 1.0)],
        "U9":  [("DL", 0.9), ("EQYP", 1.0)],
        "U10": [("DL", 0.9), ("EQYN", 1.0)],
    }

    for combo_name, cases in combos.items():
        if combo_name in existing_combos:
            print(f"  {combo_name}: already exists, skipping")
            continue
        ret = sm.RespCombo.Add(combo_name, 0)  # 0=Linear
        for case_name, sf in cases:
            ret2 = sm.RespCombo.SetCaseList(combo_name, 0, case_name, sf)  # 0=LoadCase
        print(f"  {combo_name}: created with {len(cases)} cases")

    # Verify
    rc2 = sm.RespCombo.GetNameList(0, [])
    print(f"\nLoad combinations: {list(rc2[1])}")

    lc2 = sm.LoadCases.GetNameList(0, [])
    print(f"Load cases: {list(lc2[1])}")

    # Save
    ret = sm.File.Save(r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\A21\MODEL\A21.EDB")
    print(f"\nFile.Save: ret={ret}")
    print("[OK] Load patterns, modal case, RS cases, and combos defined")

if __name__ == "__main__":
    main()
