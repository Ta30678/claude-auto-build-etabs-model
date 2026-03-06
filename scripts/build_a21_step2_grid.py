"""
A21 Model Build - Step 2: Fix Grid System
Read the actual grid table structure and set it correctly.
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
    print("[OK] Connected, units=TON_M, unlocked")

    # First, read the current grid table to understand field names
    ret = sm.DatabaseTables.GetTableForDisplayArray(
        "Grid Definitions - Grid Lines", [], "", 0, [], 0, []
    )
    print(f"GetTableForDisplayArray return length: {len(ret)}")
    for i, v in enumerate(ret):
        if isinstance(v, (tuple, list)):
            print(f"  ret[{i}]: len={len(v)} -> {list(v)[:20]}")
        else:
            print(f"  ret[{i}]: {v}")

    # Also try to get the editing array to see expected fields
    ret2 = sm.DatabaseTables.GetTableForEditingArray(
        "Grid Definitions - Grid Lines", "", 0, [], 0, []
    )
    print(f"\nGetTableForEditingArray return length: {len(ret2)}")
    for i, v in enumerate(ret2):
        if isinstance(v, (tuple, list)):
            print(f"  ret2[{i}]: len={len(v)} -> {list(v)[:20]}")
        else:
            print(f"  ret2[{i}]: {v}")

if __name__ == "__main__":
    main()
