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
    """Define grid system from config."""
    grids = config.get("grids", {})
    x_grids = grids.get("x", [])
    y_grids = grids.get("y", [])

    if not x_grids and not y_grids:
        print("  No grids defined in config, skipping.")
        return

    # Use DatabaseTables to define grids
    # Build grid data for X direction
    grid_data = []
    for g in x_grids:
        grid_data.append({
            "label": g["label"],
            "direction": "X",
            "coordinate": g["coordinate"],
            "visible": True,
            "bubble_loc": "End"
        })
    for g in y_grids:
        grid_data.append({
            "label": g["label"],
            "direction": "Y",
            "coordinate": g["coordinate"],
            "visible": True,
            "bubble_loc": "Start"
        })

    # Use the ETABS grid system API
    grid_sys_name = "G1"
    try:
        # Try to create/modify the default Cartesian grid system
        num_x = len(x_grids)
        num_y = len(y_grids)

        x_coords = [g["coordinate"] for g in x_grids]
        y_coords = [g["coordinate"] for g in y_grids]
        x_labels = [g["label"] for g in x_grids]
        y_labels = [g["label"] for g in y_grids]

        # Calculate spacings from coordinates
        x_spacings = [x_coords[i+1] - x_coords[i] for i in range(len(x_coords)-1)]
        y_spacings = [y_coords[i+1] - y_coords[i] for i in range(len(y_coords)-1)]

        # Use SetGridSys_2 for direct coordinate-based definition
        ret = SapModel.GridSys.SetGridSys_2(
            grid_sys_name,
            x_coords[0], y_coords[0], 0,  # origin x, y, rotation
            num_x, num_y,
            x_spacings if x_spacings else [1],
            y_spacings if y_spacings else [1],
            x_labels,
            y_labels,
            True  # visible
        )

        if ret == 0:
            print(f"  Grid system created: {num_x} X-lines, {num_y} Y-lines")
        else:
            print(f"  Grid system creation returned {ret}, trying alternative method...")
            _define_grids_via_database(SapModel, x_grids, y_grids)
    except Exception as e:
        print(f"  Grid API failed ({e}), trying database tables...")
        _define_grids_via_database(SapModel, x_grids, y_grids)

    # Print grid summary
    print("  X grids:", ", ".join(f"{g['label']}={g['coordinate']}m" for g in x_grids))
    print("  Y grids:", ", ".join(f"{g['label']}={g['coordinate']}m" for g in y_grids))


def _define_grids_via_database(SapModel, x_grids, y_grids):
    """Fallback: define grids using DatabaseTables API."""
    try:
        table_key = "Grid Definitions - Grid Lines"
        fields = ["Name", "Grid Line Type", "ID", "Ordinate", "Visible", "BubbleLoc"]

        data = []
        for g in x_grids:
            data.extend(["G1", "X (Cartesian)", g["label"],
                         str(g["coordinate"]), "Yes", "End"])
        for g in y_grids:
            data.extend(["G1", "Y (Cartesian)", g["label"],
                         str(g["coordinate"]), "Yes", "Start"])

        num_records = len(x_grids) + len(y_grids)
        table_version = 1

        ret = SapModel.DatabaseTables.SetTableForEditingArray(
            table_key, table_version, fields, num_records, data)
        if ret == 0:
            apply_ret = SapModel.DatabaseTables.ApplyEditedTables(True, 0, 0, 0, 0, "")
            print(f"  Grids defined via database tables (applied={apply_ret[0]==0})")
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

        if ret == 0:
            print(f"  Stories defined: {num_stories} stories")
        else:
            print(f"  SetStories_2 returned {ret}")
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
