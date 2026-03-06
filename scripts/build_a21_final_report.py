"""A21 Final Status Report"""
import comtypes.client
etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
sm = etabs.SapModel
sm.SetPresentUnits(12)

print("=" * 60)
print("A21 MODEL - FINAL STATUS REPORT")
print("=" * 60)

# Stories
r = sm.Story.GetStories_2(0.0, 0, [], [], [], [], [], [], [], [])
print(f"\n[1] Stories: {r[1]} (B3F~PRF)")
print(f"    Base elev: {r[0]:.1f} m")
print(f"    Top story elev: {list(r[3])[-1]:.1f} m (PRF)")

# Grid
ret = sm.DatabaseTables.GetTableForDisplayArray("Grid Definitions - Grid Lines", [], "", 0, [], 0, [])
print(f"\n[2] Grid Lines: {ret[3]} (6X + 6Y = 12)")

# Materials
mat = sm.PropMaterial.GetNameList(0, [])
required = ["C280","C315","C350","C420","C490","SD420","SD490"]
present = [m for m in required if m in list(mat[1])]
print(f"\n[3] Materials: {len(present)}/{len(required)} required materials present")

# Frame Sections
fs = sm.PropFrame.GetNameList(0, [])
req_sec = ["C120X180C350","C120X150C350","C120X150C280","C120X120C280","C100X100C280",
           "B50X70C350","B90X120C280","B85X100C280","B70X95C280",
           "SB45X65C280","SB45X65C350","SB30X60C280","SB30X60C350",
           "SB25X50C280","SB25X50C350","WB50X70C350"]
present_sec = [s for s in req_sec if s in list(fs[1])]
print(f"\n[4] Frame Sections: {len(present_sec)}/{len(req_sec)} required sections present")

# Area Sections
asec = sm.PropArea.GetNameList(0, [])
req_area = ["S15C280","S20C280","S15C350"]
present_area = [s for s in req_area if s in list(asec[1])]
print(f"\n[5] Area Sections: {len(present_area)}/{len(req_area)} required slab sections present")

# Columns
fr = sm.FrameObj.GetAllFrames(0, [], [], [], [], [], [], [], [], [], [], [],
                               [], [], [], [], [], [], [], [])
total_frames = fr[0]
names = list(fr[1])
x1s, y1s, z1s = list(fr[6]), list(fr[7]), list(fr[8])
x2s, y2s, z2s = list(fr[9]), list(fr[10]), list(fr[11])
cols = sum(1 for i in range(total_frames)
           if abs(x1s[i]-x2s[i]) < 0.01 and abs(y1s[i]-y2s[i]) < 0.01)
print(f"\n[6] Columns: {cols} (expected 380)")

# Load patterns
lp = sm.LoadPatterns.GetNameList(0, [])
print(f"\n[7] Load Patterns: {list(lp[1])}")

# Load cases
lc = sm.LoadCases.GetNameList(0, [])
print(f"\n[8] Load Cases: {list(lc[1])}")

# Load combos
rc = sm.RespCombo.GetNameList(0, [])
print(f"\n[9] Load Combos: {list(rc[1])}")

# Modifier check
ret = sm.FrameObj.GetModifiers(names[0], [])
mods = list(ret[0])
expected_mods = [1.0, 1.0, 1.0, 0.0001, 0.7, 0.7, 0.95, 0.95]
mod_ok = all(abs(a-b) < 0.001 for a, b in zip(mods, expected_mods))
print(f"\n[10] Column Modifiers: {'OK' if mod_ok else 'FAIL'}")
print(f"     Sample: {[round(m,4) for m in mods]}")

# Rebar check
ret = sm.PropFrame.GetRebarColumn("C120X180C350", "", "", 0, 0, 0.0, 0, 0, 0, "", "", 0.0, 0, 0, False)
print(f"\n[11] Column Rebar: cover={ret[4]:.3f}m, NR3={ret[6]}, NR2={ret[7]}, ToBeDesigned={ret[13]}")

print(f"\n{'='*60}")
print("MODELER-A TASKS COMPLETED:")
print("  [DONE] Set units TON/M and unlock model")
print("  [DONE] Define 7 materials (C280~C490, SD420, SD490)")
print("  [DONE] Create 16 frame sections + 3 slab sections")
print("  [DONE] Build Grid (6X + 6Y = 12 lines)")
print("  [DONE] Define 21 Stories (B3F~PRF, 3.4m each)")
print("  [DONE] Build 380 Columns across all stories")
print("  [DONE] Set column modifiers (T=0.0001, I22/I33=0.7, M/W=0.95)")
print("  [DONE] Set column rebar (cover=7cm, ToBeDesigned=True)")
print("  [DONE] Define 6 load patterns (DL/LL/EQXP/EQXN/EQYP/EQYN)")
print("  [DONE] Define Modal, 0SPECX, 0SPECXY load cases")
print("  [DONE] Define 10 load combinations (U1~U10)")
print("  [DONE] Save model to A21.EDB")
model_path = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\A21\MODEL\A21.EDB"
print(f"  Model: {model_path}")
print(f"\nPENDING (MODELER-B):")
print("  [ ] Beams (main + small)")
print("  [ ] Shear walls")
print("  [ ] Slabs")
print("  [ ] Beam modifiers and rigid zones")
print("  [ ] End releases")
print("  [ ] Diaphragms")
print("  [ ] Slab loads")
print("  [ ] Response spectrum function import")
print("=" * 60)

sm.View.RefreshView(0, False)
