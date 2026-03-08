"""
Golden Script 11: Diaphragm Assignments

- Creates rigid diaphragm definition per story
- Assigns diaphragm ONLY to slab corner points (not all joints)
- FS raft slabs also get diaphragm
"""
import json
import sys
import os

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)                      # modeling/ (sibling imports)
sys.path.insert(0, os.path.dirname(_dir))      # golden_scripts/ (constants)


def assign_diaphragms(SapModel, config):
    """Create diaphragms and assign to slab corner points.

    IMPORTANT: Only slab corner points get diaphragm, NOT all floor joints.
    """
    try:
        # Get all area objects with their stories
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Area Assignments - Summary", [], "All", 0, [], 0, [])

        if ret[0] != 0 or ret[5] <= 0:
            print("  No area objects found.")
            return

        fields = list(ret[4])
        data = list(ret[6])
        nf = len(fields)

        name_idx = fields.index("UniqueName") if "UniqueName" in fields else 0
        story_idx = fields.index("Story") if "Story" in fields else -1
        sec_idx = fields.index("Section") if "Section" in fields else -1

        # Group slab areas by story
        story_slabs = {}  # story -> list of area names
        for i in range(ret[5]):
            row = data[i*nf:(i+1)*nf]
            area_name = row[name_idx]
            story = row[story_idx] if story_idx >= 0 else "Unknown"
            section = row[sec_idx] if sec_idx >= 0 else ""

            # Only slabs (S*) and raft (FS*) get diaphragm, not walls (W*)
            if section.startswith("S") or section.startswith("FS"):
                story_slabs.setdefault(story, []).append(area_name)

        # Create diaphragm for each story and assign to slab corner points
        total_points = 0
        for story, slab_names in story_slabs.items():
            diaphragm_name = f"D_{story}"

            # Create diaphragm definition (rigid)
            SapModel.Diaphragm.SetDiaphragm(diaphragm_name, False)

            pts_assigned = set()
            for area_name in slab_names:
                # Get corner points of this slab
                area_ret = SapModel.AreaObj.GetPoints(area_name, 0, [])
                if area_ret[0] != 0:
                    continue

                corner_points = area_ret[2]
                if isinstance(corner_points, (list, tuple)):
                    for pt in corner_points:
                        if pt not in pts_assigned:
                            SapModel.PointObj.SetDiaphragm(pt, 3, diaphragm_name)
                            pts_assigned.add(pt)

            total_points += len(pts_assigned)
            print(f"  {diaphragm_name}: {len(slab_names)} slabs, {len(pts_assigned)} corner points")

        print(f"  Total diaphragm assignments: {total_points} points across {len(story_slabs)} stories")

    except Exception as e:
        print(f"  WARNING: Diaphragm assignment failed: {e}")


def run(SapModel, config):
    """Execute step 11: diaphragm assignments."""
    print("=" * 60)
    print("STEP 11: Diaphragm Assignments")
    print("=" * 60)

    assign_diaphragms(SapModel, config)

    SapModel.View.RefreshView(0, False)
    print("Step 11 complete.\n")


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "model_config.json"
    with open(config_path) as f:
        config = json.load(f)
    from gs_01_init import connect_etabs
    SapModel = connect_etabs(config)
    run(SapModel, config)
