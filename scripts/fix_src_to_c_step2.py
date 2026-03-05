"""
Step 2: Fix remaining issues from SRC->C conversion.
1. Revert C section modifiers back to original (I2=1.4, I3=1.4, M=1.25, W=1.25)
2. Create C120X120C420 section
3. Reassign remaining SRC120X120C420 frames
"""
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

def main():
    SapModel, pid = connect_etabs()
    if not SapModel:
        print("ERROR: Cannot connect to ETABS")
        return
    print(f"Connected to ETABS PID {pid}")
    SapModel.SetPresentUnits(12)  # TON/M
    SapModel.SetModelIsLocked(False)

    # Correct modifiers for C~C420 sections (from C building source)
    correct_mods = [1.0, 1.0, 1.0, 0.0001, 1.4, 1.4, 1.25, 1.25]
    # [Area, As2, As3, J, I22, I33, Mass, Weight]

    # Step 1: Revert C section modifiers
    print("\n[STEP 1] Reverting C section modifiers to correct values...")
    for sec in ['C100X100C420', 'C130X130C420', 'C150X150C420']:
        ret = SapModel.PropFrame.GetModifiers(sec, [])
        current = list(ret[0]) if isinstance(ret[0], (list, tuple)) else list(ret)
        print(f"  {sec} current: {current}")

        ret2 = SapModel.PropFrame.SetModifiers(sec, correct_mods)
        ret_code = ret2[-1] if isinstance(ret2, (list, tuple)) else ret2
        print(f"  {sec} set to {correct_mods} -> ret={ret_code}")

    # Step 2: Create C120X120C420
    print("\n[STEP 2] Creating C120X120C420...")

    # Check if it exists
    ret = SapModel.PropFrame.GetNameList(0, [])
    etabs_sections = set(ret[1]) if ret[0] > 0 else set()

    if 'C120X120C420' not in etabs_sections:
        # Create with material C420, D=1.2m, B=1.2m
        ret = SapModel.PropFrame.SetRectangle('C120X120C420', 'C420', 1.2, 1.2)
        print(f"  SetRectangle ret={ret}")

        # Set modifiers
        ret2 = SapModel.PropFrame.SetModifiers('C120X120C420', correct_mods)
        ret_code = ret2[-1] if isinstance(ret2, (list, tuple)) else ret2
        print(f"  SetModifiers ret={ret_code}")
    else:
        print("  Already exists, setting modifiers...")
        ret2 = SapModel.PropFrame.SetModifiers('C120X120C420', correct_mods)
        ret_code = ret2[-1] if isinstance(ret2, (list, tuple)) else ret2
        print(f"  SetModifiers ret={ret_code}")

    # Step 3: Reassign remaining SRC120X120C420 frames
    print("\n[STEP 3] Reassigning SRC120X120C420 frames...")
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [],
        [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])
    num_frames = ret[0]

    reassigned = 0
    errors = 0
    for i in range(num_frames):
        if ret[2][i] == 'SRC120X120C420':
            frame_name = ret[1][i]
            ret2 = SapModel.FrameObj.SetSection(frame_name, 'C120X120C420')
            if ret2 == 0:
                reassigned += 1
            else:
                errors += 1
                if errors <= 5:
                    print(f"    FAIL: {frame_name}, ret={ret2}")

    print(f"  Reassigned: {reassigned}")
    print(f"  Errors: {errors}")

    # Step 4: Verify no SRC frames remain
    print("\n[STEP 4] Final verification...")
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [],
        [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])
    src_count = 0
    for i in range(ret[0]):
        if ret[2][i].startswith('SRC'):
            src_count += 1
    print(f"  Frames still using SRC sections: {src_count}")

    # Verify modifiers
    print("\n  Section modifiers verification:")
    for sec in ['C100X100C420', 'C120X120C420', 'C130X130C420', 'C150X150C420']:
        try:
            ret = SapModel.PropFrame.GetModifiers(sec, [])
            mods = list(ret[0]) if isinstance(ret[0], (list, tuple)) else list(ret)
            j, i2, i3, m, w = mods[3], mods[4], mods[5], mods[6], mods[7]
            print(f"  {sec}: J={j}, I2={i2}, I3={i3}, M={m}, W={w}")
        except Exception as e:
            print(f"  {sec}: ERROR {e}")

    # Save
    output = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_v5.EDB'
    SapModel.File.Save(output)
    print(f"\nSaved to: {output}")
    SapModel.View.RefreshView(0, False)
    print("Done!")

if __name__ == '__main__':
    main()
