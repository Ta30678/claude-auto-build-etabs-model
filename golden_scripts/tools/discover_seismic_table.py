"""Discovery script: find the exact Table Key and Field Names for Auto Seismic User Coefficient.

Usage:
    1. Open ETABS with a model that has EQXP/XN/YP/YN load patterns
       (ideally with User Coefficient already set manually on at least one)
    2. Run: python -m golden_scripts.tools.discover_seismic_table

Output: prints all seismic-related table keys and their field definitions.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from find_etabs import find_etabs


def main():
    etabs, _ = find_etabs(run=False, backup=False)
    SapModel = etabs.SapModel

    # 1. List ALL tables, filter for seismic/user/lateral/quake
    print("=" * 60)
    print("Discovering seismic-related database tables...")
    print("=" * 60)

    ret = SapModel.DatabaseTables.GetAllTables(0, [], [], [], [])
    if ret[0] == 0:
        tables = list(ret[1])
    else:
        # Some ETABS versions return differently
        tables = list(ret[1]) if len(ret) > 1 else []

    keywords = ["seismic", "user coeff", "lateral", "quake", "earthquake"]
    matched = []
    for t in tables:
        t_lower = t.lower()
        if any(kw in t_lower for kw in keywords):
            matched.append(t)
            print(f"  TABLE: {t}")

    if not matched:
        print("  No tables matched keywords. Listing ALL tables for manual search:")
        for t in sorted(tables):
            print(f"    {t}")
        return

    # 2. For each matched table, get field definitions
    print("\n" + "=" * 60)
    print("Field definitions for matched tables:")
    print("=" * 60)

    for t in matched:
        try:
            fret = SapModel.DatabaseTables.GetAllFieldsInTable(t, 0, [], [], [], [], [])
            print(f"\n--- {t} ---")
            if isinstance(fret, (list, tuple)) and len(fret) > 3:
                field_keys = list(fret[2]) if fret[2] else []
                field_names = list(fret[3]) if len(fret) > 3 and fret[3] else []
                print(f"  Field Keys:  {field_keys}")
                print(f"  Field Names: {field_names}")
            else:
                print(f"  Raw return: {fret}")
        except Exception as e:
            print(f"  ERROR reading fields for '{t}': {e}")

    # 3. Try to read current data from matched tables
    print("\n" + "=" * 60)
    print("Current data in matched tables:")
    print("=" * 60)

    for t in matched:
        try:
            ret = SapModel.DatabaseTables.GetTableForDisplayArray(
                t, [], "All", 0, [], 0, [])
            if isinstance(ret, (list, tuple)):
                retcode = ret[0] if len(ret) > 0 else -1
                if retcode == 0 and len(ret) > 4:
                    fields = list(ret[2]) if ret[2] else []
                    num_records = ret[3]
                    data = list(ret[4]) if ret[4] else []
                    nf = len(fields)
                    print(f"\n--- {t} ({num_records} records) ---")
                    print(f"  Fields: {fields}")
                    for i in range(num_records):
                        row = data[i * nf:(i + 1) * nf]
                        print(f"  Row {i}: {row}")
                else:
                    print(f"\n--- {t} --- (no data or retcode={retcode})")
        except Exception as e:
            print(f"\n--- {t} --- ERROR: {e}")


if __name__ == "__main__":
    main()
