"""
Golden Script 03: Grid System and Story Definitions

- Creates grid lines from config (X and Y)
- Defines stories with correct elevations
"""
import json
import sys
import os

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)                      # modeling/ (sibling imports)
sys.path.insert(0, os.path.dirname(_dir))      # golden_scripts/ (constants)
from constants import UNITS_TON_M


def define_grids(SapModel, config):
    """Define grid system from config using DatabaseTables API.

    The ETABS API only has SetGridSys(Name, x, y, RZ) which creates a grid
    system but cannot define individual grid lines. Grid lines must be
    defined via DatabaseTables.SetTableForEditingArray.
    """
    grids = config.get("grids", {})
    x_grids = grids.get("x", [])
    y_grids = grids.get("y", [])

    if not x_grids and not y_grids:
        print("  No grids defined in config, skipping.")
        return

    grid_sys_name = "G1"

    # Step 1: Create the grid system (origin + rotation only)
    try:
        ret = SapModel.GridSys.SetGridSys(grid_sys_name, 0, 0, 0)
        if ret == 0:
            print(f"  Grid system '{grid_sys_name}' created")
        else:
            print(f"  Grid system creation returned {ret} (may already exist)")
    except Exception as e:
        print(f"  Grid system creation skipped ({e}), continuing with grid lines...")

    # Step 2: Define grid lines via DatabaseTables
    _define_grids_via_database(SapModel, x_grids, y_grids, grid_sys_name)

    # Print grid summary
    print("  X grids:", ", ".join(f"{g['label']}={g['coordinate']}m" for g in x_grids))
    print("  Y grids:", ", ".join(f"{g['label']}={g['coordinate']}m" for g in y_grids))


def _define_grids_via_database(SapModel, x_grids, y_grids, grid_sys_name="G1"):
    """Define grid lines using DatabaseTables API.

    SetTableForEditingArray signature (from API docs):
      (TableKey, ref TableVersion, ref FieldsKeysIncluded, NumberRecords, ref TableData)
    comtypes returns: (retcode, table_version, fields, table_data) as tuple.
    """
    try:
        table_key = "Grid Definitions - Grid Lines"
        fields = ["Name", "Grid Line Type", "ID", "Ordinate", "Visible", "BubbleLoc"]

        data = []
        for g in x_grids:
            data.extend([grid_sys_name, "X (Cartesian)", g["label"],
                         str(g["coordinate"]), "Yes", "End"])
        for g in y_grids:
            data.extend([grid_sys_name, "Y (Cartesian)", g["label"],
                         str(g["coordinate"]), "Yes", "Start"])

        num_records = len(x_grids) + len(y_grids)
        table_version = 1

        # ref params → comtypes returns tuple (retcode, version, fields, data)
        ret = SapModel.DatabaseTables.SetTableForEditingArray(
            table_key, table_version, fields, num_records, data)
        retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
        if retcode == 0:
            apply_ret = SapModel.DatabaseTables.ApplyEditedTables(True, 0, 0, 0, 0, "")
            apply_ok = apply_ret[0] == 0 if isinstance(apply_ret, (list, tuple)) else apply_ret == 0
            print(f"  Grid lines defined: {len(x_grids)} X + {len(y_grids)} Y (applied={apply_ok})")
        else:
            print(f"  WARNING: SetTableForEditingArray returned {retcode}")
            print("  Please define grids manually in ETABS.")
    except Exception as e:
        print(f"  WARNING: Could not define grids via database tables: {e}")
        print("  Please define grids manually in ETABS.")


def define_stories(SapModel, config):
    """Define stories from config."""
    stories_config = config.get("stories", [])
    base_elev = config.get("base_elevation", 0)

    if not stories_config:
        print("  No stories defined in config, skipping.")
        return []

    num_stories = len(stories_config)
    story_names = [s["name"] for s in stories_config]
    story_heights = [s["height"] for s in stories_config]

    # Calculate elevations if not provided
    story_elevations = []
    current_elev = base_elev
    for s in stories_config:
        current_elev += s["height"]
        elev = s.get("elevation", current_elev)
        story_elevations.append(elev)

    is_master = [s.get("is_master", True) for s in stories_config]
    similar_to = ["None"] * num_stories
    splice_above = [False] * num_stories
    splice_height = [0.0] * num_stories
    color = [0] * num_stories

    try:
        ret = SapModel.Story.SetStories_2(
            base_elev, num_stories, story_names, story_heights,
            is_master, similar_to, splice_above, splice_height, color)

        retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
        if retcode == 0:
            print(f"  Stories defined: {num_stories} stories")
        else:
            print(f"  SetStories_2 returned {retcode}")
    except Exception as e:
        print(f"  WARNING: Could not define stories: {e}")
        print("  Stories may already exist. Continuing...")

    # Print summary
    elev = base_elev
    print(f"  BASE elevation: {base_elev}m")
    for i, s in enumerate(stories_config):
        elev += s["height"]
        print(f"  {s['name']}: height={s['height']}m, elevation={elev}m")

    # Return story elevation map for use by other scripts
    elev_map = {"BASE": base_elev}
    current = base_elev
    for s in stories_config:
        current += s["height"]
        elev_map[s["name"]] = current

    return elev_map


def run(SapModel, config):
    """Execute step 03: grids + stories."""
    print("=" * 60)
    print("STEP 03: Grid System + Story Definitions")
    print("=" * 60)

    define_grids(SapModel, config)
    elev_map = define_stories(SapModel, config)

    SapModel.View.RefreshView(0, False)
    print("Step 03 complete.\n")

    return elev_map


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "model_config.json"
    with open(config_path) as f:
        config = json.load(f)
    from gs_01_init import connect_etabs
    SapModel = connect_etabs(config)
    run(SapModel, config)
