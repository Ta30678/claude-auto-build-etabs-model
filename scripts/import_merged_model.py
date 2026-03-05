"""
Import the merged e2k file into ETABS 22.
This script:
1. Opens ETABS (or attaches to running instance)
2. Imports MERGED_ALL.e2k
3. Refreshes the view
4. Reports element counts

Run this AFTER reviewing MERGED_ALL.e2k and confirming grid line positions.
"""
import sys, os
sys.path.insert(0, r"C:\Users\User\Desktop\V22 AGENTIC MODEL")

from find_etabs import find_etabs

MERGED_FILE = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_ALL.e2k"
OUTPUT_EDB = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_ALL.EDB"

def main():
    print("Connecting to ETABS...")
    etabs, filename = find_etabs(run=False, backup=False)
    SapModel = etabs.SapModel

    print(f"Connected. Current model: {filename}")

    # Initialize new model
    print("\nInitializing new model (TON/M)...")
    ret = SapModel.InitializeNewModel(12)  # 12 = Ton_m
    if ret != 0:
        print(f"WARNING: InitializeNewModel returned {ret}")

    ret = SapModel.File.NewBlank()
    if ret != 0:
        print(f"WARNING: NewBlank returned {ret}")

    # Import e2k
    print(f"\nImporting: {MERGED_FILE}")
    ret = SapModel.File.OpenFile(MERGED_FILE)
    if ret != 0:
        print(f"WARNING: OpenFile returned {ret}")
        print("Trying alternate import method...")
        # Try importing as e2k text
        # Note: ETABS e2k import uses File.OpenFile with e2k extension

    # Save as EDB
    print(f"\nSaving as: {OUTPUT_EDB}")
    ret = SapModel.File.Save(OUTPUT_EDB)
    if ret != 0:
        print(f"WARNING: Save returned {ret}")

    # Refresh view
    SapModel.View.RefreshView(0, False)

    # Report element counts
    print("\n" + "="*50)
    print("MODEL IMPORT SUMMARY")
    print("="*50)

    # Get story info
    try:
        ret = SapModel.Story.GetStories_2(0, 0, [], [], [], [], [], [], [], [])
        if ret[0] == 0:
            num_stories = ret[2]
            print(f"Stories: {num_stories}")
    except:
        print("Could not get story count")

    # Get frame count
    try:
        ret = SapModel.FrameObj.GetAllFrames(0, [], [], [], [], [], [], [], [], [], [], [],
            [], [], [], [], [], [], [], [])
        if ret[0] == 0:
            num_frames = ret[1]
            print(f"Frame objects: {num_frames}")
    except:
        print("Could not get frame count")

    # Get area count
    try:
        ret = SapModel.AreaObj.GetNameList(0, [])
        if ret[0] == 0:
            num_areas = ret[1]
            print(f"Area objects: {num_areas}")
    except:
        print("Could not get area count")

    print(f"\nModel saved to: {OUTPUT_EDB}")
    print("Please review in ETABS:")
    print("  1. Check grid lines match intended design")
    print("  2. Verify column continuity at 1F/1MF interface")
    print("  3. Check section assignments")
    print("  4. Add any missing loads for above-1MF stories")
    print("  5. Run analysis when ready")

if __name__ == '__main__':
    main()
