"""
A21 Model Build - Step 3: Materials + Sections
Since we started from NewBlank, we need to create all materials and sections.
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
    sm.SetPresentUnits(12)  # TON_M
    sm.SetModelIsLocked(False)
    print("[OK] Connected, units=TON_M")

    # Check existing materials
    mat = sm.PropMaterial.GetNameList(0, [])
    existing_mats = list(mat[1]) if mat[0] > 0 else []
    print(f"Existing materials: {existing_mats}")

    # ============================================================
    # Define Concrete Materials: C280, C315, C350, C420, C490
    # Units: TON/M -> fc in ton/m2, E in ton/m2
    # ============================================================
    concrete_grades = {
        # name: (fc_kgf_cm2, E_kgf_cm2)
        "C280": (280, 251498),   # E = 15000*sqrt(280) = 251498 kgf/cm2
        "C315": (315, 266625),   # E = 15000*sqrt(315)
        "C350": (350, 281069),   # E = 15000*sqrt(350)
        "C420": (420, 307594),   # E = 15000*sqrt(420)
        "C490": (490, 332265),   # E = 15000*sqrt(490)
    }

    for name, (fc_kgf, E_kgf) in concrete_grades.items():
        # Convert kgf/cm2 to ton/m2: multiply by 10 (1 kgf/cm2 = 10 ton/m2 is WRONG)
        # Actually: 1 kgf/cm2 = 0.001 ton / (0.01m)^2 = 0.001 / 0.0001 = 10 ton/m2
        fc_ton_m2 = fc_kgf * 10.0   # e.g. 280 kgf/cm2 = 2800 ton/m2
        E_ton_m2 = E_kgf * 10.0     # e.g. 251498 kgf/cm2 = 2514980 ton/m2

        # Use SetMaterial (not AddMaterial) to control the name
        ret = sm.PropMaterial.SetMaterial(name, 2)  # 2=Concrete
        print(f"  SetMaterial('{name}', Concrete): ret={ret}")

        # Set isotropic properties: E, Poisson, ThermalCoeff
        ret = sm.PropMaterial.SetMPIsotropic(name, E_ton_m2, 0.2, 1e-5)
        print(f"  SetMPIsotropic('{name}', E={E_ton_m2:.0f}): ret={ret}")

        # Set weight and mass: 1 = by weight per volume
        # Concrete unit weight = 2.4 ton/m3
        ret = sm.PropMaterial.SetWeightAndMass(name, 1, 2.4)
        print(f"  SetWeightAndMass('{name}', 2.4): ret={ret}")

        # Set concrete design properties
        # SetOConcrete_1(Name, fc, IsLightweight, FcsFactor, SSType, SSHysType,
        #                StrainAtFc, StrainUlt, FinalSlope, FrictionAngle, DilatAngle)
        ret = sm.PropMaterial.SetOConcrete_1(name, fc_ton_m2, False, 1, 2, 1,
                                              0.002, 0.005, -0.1, 0, 0)
        print(f"  SetOConcrete_1('{name}', fc={fc_ton_m2:.0f}): ret={ret}")

    # ============================================================
    # Define Rebar Materials: SD420, SD490
    # ============================================================
    rebar_grades = {
        # name: (fy_kgf_cm2, fu_kgf_cm2)
        "SD420": (4200, 6300),
        "SD490": (4900, 7350),
    }

    for name, (fy_kgf, fu_kgf) in rebar_grades.items():
        fy_ton_m2 = fy_kgf * 10.0
        fu_ton_m2 = fu_kgf * 10.0
        E_ton_m2 = 2.04e6 * 10.0  # 2.04e6 kgf/cm2 = 2.04e7 ton/m2

        ret = sm.PropMaterial.SetMaterial(name, 5)  # 5=Rebar
        print(f"  SetMaterial('{name}', Rebar): ret={ret}")

        ret = sm.PropMaterial.SetMPIsotropic(name, E_ton_m2, 0.3, 1.2e-5)
        print(f"  SetMPIsotropic('{name}', E={E_ton_m2:.0f}): ret={ret}")

        ret = sm.PropMaterial.SetWeightAndMass(name, 1, 7.85)
        print(f"  SetWeightAndMass('{name}', 7.85): ret={ret}")

        # SetORebar_1(Name, Fy, Fu, EFy, EFu, SSType, SSHysType, StrainHard, StrainMaxStress, StrainRupture, FinalSlope)
        ret = sm.PropMaterial.SetORebar_1(name, fy_ton_m2, fu_ton_m2, fy_ton_m2, fu_ton_m2,
                                           1, 1, 0.01, 0.09, 0.1, -0.1)
        print(f"  SetORebar_1('{name}', fy={fy_ton_m2:.0f}): ret={ret}")

    # Verify
    mat = sm.PropMaterial.GetNameList(0, [])
    print(f"\nAll materials after creation: {list(mat[1])}")

    # ============================================================
    # Define Frame Sections
    # ============================================================
    # SetRectangle(Name, Material, T3=depth_m, T2=width_m)
    # Column: C{Xwidth}X{Ydepth} -> T2=Xwidth, T3=Ydepth
    # Beam: B{width}X{depth} -> T2=width, T3=depth

    frame_sections = [
        # (name, material, depth_m, width_m)
        # -- Columns --
        ("C120X180C350", "C350", 1.8, 1.2),    # C120(X-width)X180(Y-depth): T3=1.8, T2=1.2
        ("C120X150C350", "C350", 1.5, 1.2),    # C120X150: T3=1.5, T2=1.2
        ("C120X150C280", "C280", 1.5, 1.2),
        ("C120X120C280", "C280", 1.2, 1.2),
        ("C100X100C280", "C280", 1.0, 1.0),
        # -- Main Beams --
        ("B50X70C350",  "C350", 0.70, 0.50),   # basement beam
        ("B90X120C280", "C280", 1.20, 0.90),   # 2F-3F transition
        ("B85X100C280", "C280", 1.00, 0.85),   # 4F-14F typical
        ("B70X95C280",  "C280", 0.95, 0.70),   # R2F-PRF
        # -- Small Beams --
        ("SB45X65C280", "C280", 0.65, 0.45),
        ("SB45X65C350", "C350", 0.65, 0.45),
        ("SB30X60C280", "C280", 0.60, 0.30),
        ("SB30X60C350", "C350", 0.60, 0.30),
        ("SB25X50C280", "C280", 0.50, 0.25),
        ("SB25X50C350", "C350", 0.50, 0.25),
        # -- Wall Beam (basement) --
        ("WB50X70C350", "C350", 0.70, 0.50),
    ]

    print("\n--- Frame Sections ---")
    for name, mat_name, depth, width in frame_sections:
        ret = sm.PropFrame.SetRectangle(name, mat_name, depth, width)
        status = "OK" if ret == 0 else f"FAIL({ret})"
        print(f"  {name}: T3(depth)={depth}, T2(width)={width}, mat={mat_name} -> {status}")

    # ============================================================
    # Define Area Sections (Slabs)
    # ============================================================
    # SetSlab(Name, SlabType, ShellType, Material, Thickness)
    # SlabType=0 (Slab), ShellType=2 (Membrane)

    slab_sections = [
        # (name, material, thickness_m, shell_type)
        ("S15C280", "C280", 0.15, 2),   # Membrane
        ("S20C280", "C280", 0.20, 2),   # Membrane
        ("S15C350", "C350", 0.15, 2),   # Membrane (basement)
    ]

    print("\n--- Slab Sections ---")
    for name, mat_name, thick, shell_type in slab_sections:
        ret = sm.PropArea.SetSlab(name, 0, shell_type, mat_name, thick)
        status = "OK" if ret == 0 else f"FAIL({ret})"
        print(f"  {name}: t={thick}m, mat={mat_name}, ShellType={shell_type} -> {status}")

    # Verify frame sections
    fs = sm.PropFrame.GetNameList(0, [])
    print(f"\nAll frame sections: {list(fs[1])}")

    # Verify area sections
    asec = sm.PropArea.GetNameList(0, [])
    print(f"All area sections: {list(asec[1])}")

    # Save
    ret = sm.File.Save(r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\A21\MODEL\A21.EDB")
    print(f"\nFile.Save: ret={ret}")
    print(f"[OK] Materials ({len(concrete_grades)+len(rebar_grades)}) and sections ({len(frame_sections)} frame + {len(slab_sections)} slab) defined")

if __name__ == "__main__":
    main()
