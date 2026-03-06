"""
A21 Model Build - Step 2b: Set Grid Lines correctly
Fields: Name, LineType, ID, Ordinate, Angle, X1, Y1, X2, Y2, BubbleLoc, Visible
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
    print("[OK] Connected")

    # Grid coordinates (m):
    # X: A=-8.5, B=0, C=8.5, D=19.5, E=30.5, F=41.5
    # Y: 4=-9.0, 5=0, 6=9.0, 7=17.6, 8=27.4, 9=37.2
    x_grids = [("A", -8.5), ("B", 0.0), ("C", 8.5), ("D", 19.5), ("E", 30.5), ("F", 41.5)]
    y_grids = [("4", -9.0), ("5", 0.0), ("6", 9.0), ("7", 17.6), ("8", 27.4), ("9", 37.2)]

    # Fields: Name, LineType, ID, Ordinate, Angle, X1, Y1, X2, Y2, BubbleLoc, Visible
    fields = ["Name", "LineType", "ID", "Ordinate", "Angle", "X1", "Y1", "X2", "Y2", "BubbleLoc", "Visible"]
    data = []

    for label, coord in x_grids:
        data.extend([
            "G1",                # Name (grid system name)
            "X (Cartesian)",     # LineType
            label,               # ID (grid label)
            str(coord),          # Ordinate
            "",                  # Angle (not used for Cartesian)
            "",                  # X1 (not used for Cartesian)
            "",                  # Y1
            "",                  # X2
            "",                  # Y2
            "End",               # BubbleLoc
            "Yes"                # Visible
        ])

    for label, coord in y_grids:
        data.extend([
            "G1",
            "Y (Cartesian)",
            label,
            str(coord),
            "",
            "",
            "",
            "",
            "",
            "End",
            "Yes"
        ])

    num_records = len(x_grids) + len(y_grids)
    print(f"Grid records: {num_records} (6X + 6Y)")
    print(f"Fields: {fields}")
    print(f"Data length: {len(data)} (should be {num_records * len(fields)})")

    # Set grid data
    ret = sm.DatabaseTables.SetTableForEditingArray(
        "Grid Definitions - Grid Lines", 0, fields, num_records, data
    )
    print(f"SetTableForEditingArray: ret={ret[0] if isinstance(ret, (list,tuple)) else ret}")

    # Apply
    ret2 = sm.DatabaseTables.ApplyEditedTables(True, 0, 0, 0, 0, "")
    if isinstance(ret2, (list, tuple)):
        print(f"ApplyEditedTables: ret={ret2[0]}, fatal={ret2[1]}, errors={ret2[2]}, warnings={ret2[3]}")
        log = ret2[4] if len(ret2) > 4 else ""
        if log:
            # Print just the summary line
            for line in str(log).split('\n'):
                line = line.strip()
                if 'successfully' in line.lower() or 'error' in line.lower():
                    print(f"  {line}")
    else:
        print(f"ApplyEditedTables: ret={ret2}")

    # Verify by reading grid back
    ret3 = sm.DatabaseTables.GetTableForDisplayArray(
        "Grid Definitions - Grid Lines", [], "", 0, [], 0, []
    )
    if len(ret3) >= 5:
        num_fields_r = len(ret3[2]) if isinstance(ret3[2], (list, tuple)) else 0
        num_recs = ret3[3]
        print(f"\nVerification: {num_recs} grid lines found")
        if num_recs > 0 and num_fields_r > 0:
            data_r = list(ret3[4])
            for i in range(num_recs):
                row = data_r[i*num_fields_r:(i+1)*num_fields_r]
                print(f"  {row}")

    sm.View.RefreshView(0, False)

    # Save
    ret = sm.File.Save(r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\A21\MODEL\A21.EDB")
    print(f"\nFile.Save: ret={ret}")
    print("[OK] Grid system defined and saved")

if __name__ == "__main__":
    main()
