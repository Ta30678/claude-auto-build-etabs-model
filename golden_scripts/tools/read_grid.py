"""
Read Grid System from ETABS model.

Connects to a running ETABS instance, reads grid line definitions
via DatabaseTables, and outputs a JSON file compatible with
model_config.json's grids section.

Usage:
    python -m golden_scripts.tools.read_grid --output grid_data.json
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def read_grid_from_etabs(SapModel):
    """Read grid system from ETABS via DatabaseTables.

    Returns dict compatible with model_config.json grids section:
    {
        "x": [{"label": "A", "coordinate": 0.00}, ...],
        "y": [{"label": "1", "coordinate": 0.00}, ...],
        "x_bubble": "End",
        "y_bubble": "Start"
    }
    """
    from constants import UNITS_TON_M
    SapModel.SetPresentUnits(UNITS_TON_M)

    table_key = "Grid Definitions - Grid Lines"
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        table_key, [], "All", 0, [], 0, [])

    # Raw COM returns: [FieldKeyList_out, TableVersion, FieldKeysIncluded,
    #                    NumberRecords, TableData, retcode]
    # etabs_api returns: (retcode, FieldKeysIncluded, ..., NumberRecords, TableData)
    if not ret or len(ret) < 4:
        print(f"ERROR: GetTableForDisplayArray returned {ret}")
        sys.exit(1)

    # Detect format: raw COM has retcode at end, etabs_api at start
    if isinstance(ret[-1], int) and isinstance(ret[0], (list, tuple)):
        # Raw COM format
        retcode = ret[-1]
        fields = list(ret[2]) if len(ret) > 2 else []
        num_records = ret[3] if len(ret) > 3 else 0
        table_data = list(ret[4]) if len(ret) > 4 else []
    else:
        # etabs_api format
        retcode = ret[0]
        fields = list(ret[1]) if len(ret) > 1 else []
        num_records = ret[3] if len(ret) > 3 else 0
        table_data = list(ret[4]) if len(ret) > 4 else []

    if retcode != 0:
        print(f"ERROR: GetTableForDisplayArray returned code {retcode}")
        sys.exit(1)

    if num_records == 0:
        print("ERROR: No grid lines found in ETABS model.")
        print("Please create grid lines in ETABS before running this tool.")
        sys.exit(1)

    # Build column index
    col_idx = {name: i for i, name in enumerate(fields)}
    num_fields = len(fields)

    x_grids = []
    y_grids = []
    x_bubble = "End"
    y_bubble = "Start"

    for row in range(num_records):
        offset = row * num_fields
        row_data = {f: table_data[offset + col_idx[f]] for f in fields if f in col_idx}

        grid_type = row_data.get("LineType", row_data.get("Grid Line Type", ""))
        label = row_data.get("ID", "")
        ordinate_str = row_data.get("Ordinate", "0")
        bubble_loc = row_data.get("BubbleLoc", "")

        try:
            coordinate = round(float(ordinate_str), 4)
        except (ValueError, TypeError):
            coordinate = 0.0

        entry = {"label": label, "coordinate": coordinate}

        if "X" in grid_type:
            x_grids.append(entry)
            if bubble_loc:
                x_bubble = bubble_loc
        elif "Y" in grid_type:
            y_grids.append(entry)
            if bubble_loc:
                y_bubble = bubble_loc

    # Sort by coordinate
    x_grids.sort(key=lambda g: g["coordinate"])
    y_grids.sort(key=lambda g: g["coordinate"])

    result = {
        "grids": {
            "x": x_grids,
            "y": y_grids,
            "x_bubble": x_bubble,
            "y_bubble": y_bubble
        }
    }

    print(f"  Grid lines read: {len(x_grids)} X + {len(y_grids)} Y")
    x_str = ', '.join(f'{g["label"]}={g["coordinate"]}m' for g in x_grids)
    y_str = ', '.join(f'{g["label"]}={g["coordinate"]}m' for g in y_grids)
    print(f"  X grids: {x_str}")
    print(f"  Y grids: {y_str}")
    print(f"  Bubble: X={x_bubble}, Y={y_bubble}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Read Grid System from ETABS model")
    parser.add_argument("--output", "-o", required=True,
                        help="Output JSON file path")
    args = parser.parse_args()

    try:
        from find_etabs import find_etabs
        etabs, filename = find_etabs(run=False, backup=False)
        SapModel = etabs.SapModel
        print(f"Connected to ETABS: {filename}")
    except (ImportError, ModuleNotFoundError):
        import comtypes.client
        comtypes.client.gen_dir = None
        etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        SapModel = etabs.SapModel
        filename = SapModel.GetModelFilename()
        print(f"Connected to ETABS (COM): {filename}")

    result = read_grid_from_etabs(SapModel)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Grid data written to: {args.output}")


if __name__ == "__main__":
    main()
