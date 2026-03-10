"""
Golden Script 09: Structural Properties Assignment

- Frame modifiers (beam: T=0.0001,I=0.7,M/W=0.8; column: T=0.0001,I=0.7,M/W=0.95)
- Rigid zones (factor=0.75) for ALL frame objects
- End releases (M2+M3 at discontinuous beam ends)

All values are HARDCODED constants - no AI reasoning needed.
"""
import json
import sys
import os

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)                      # modeling/ (sibling imports)
sys.path.insert(0, os.path.dirname(_dir))      # golden_scripts/ (constants)
from constants import (
    BEAM_MODIFIERS, COL_MODIFIERS,
    RIGID_ZONE_FACTOR,
    RELEASE_M2M3, NO_RELEASE, ZERO_SPRINGS,
)


def assign_frame_modifiers(SapModel):
    """Assign stiffness modifiers to ALL frame objects.

    Beams: [1, 1, 1, 0.0001, 0.7, 0.7, 0.8, 0.8]
    Columns: [1, 1, 1, 0.0001, 0.7, 0.7, 0.95, 0.95]
    """
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [], [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])

    if not isinstance(ret[0], int) or ret[0] <= 0:
        print("  No frames found.")
        return 0, 0

    num = ret[0]
    names = ret[1]
    props = ret[2]

    beam_count, col_count = 0, 0

    for i in range(num):
        prop = props[i]
        # Columns start with 'C' followed by digits and 'X'
        is_col = (prop.startswith('C') and 'X' in prop and
                  not prop.startswith('CB'))  # avoid false positives

        if is_col:
            r = SapModel.FrameObj.SetModifiers(names[i], COL_MODIFIERS)
            retcode = r[-1] if isinstance(r, (list, tuple)) else r
            if retcode == 0:
                col_count += 1
        else:
            r = SapModel.FrameObj.SetModifiers(names[i], BEAM_MODIFIERS)
            retcode = r[-1] if isinstance(r, (list, tuple)) else r
            if retcode == 0:
                beam_count += 1

    print(f"  Frame modifiers: {beam_count} beams, {col_count} columns")
    return beam_count, col_count


def assign_rigid_zones(SapModel):
    """Assign rigid zone factor=0.75 to ALL frame objects."""
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [], [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])

    if not isinstance(ret[0], int) or ret[0] <= 0:
        print("  No frames found.")
        return 0

    names = ret[1]
    count = 0

    for name in names:
        r = SapModel.FrameObj.SetEndLengthOffset(name, False, 0.0, 0.0, RIGID_ZONE_FACTOR)
        if r == 0:
            count += 1

    print(f"  Rigid zones (RZ={RIGID_ZONE_FACTOR}): {count}/{len(names)} frames")
    return count


def assign_end_releases(SapModel):
    """Assign end releases to beam ends that are NOT continuous.

    Rule: A beam end is released (M2+M3) if no other frame shares that endpoint.
    """
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [], [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])

    if not isinstance(ret[0], int) or ret[0] <= 0:
        print("  No frames found.")
        return 0

    num = ret[0]
    names = ret[1]
    props = ret[2]

    # Collect all frame endpoint coordinates
    endpoint_counts = {}  # coord -> count of frame endpoints at that coord
    frame_endpoints = {}  # frame_name -> (coord_i, coord_j)

    for i in range(num):
        name = names[i]
        pts = SapModel.FrameObj.GetPoints(name, "", "")
        if pts[0] != 0:
            continue

        for pt in [pts[1], pts[2]]:
            c = SapModel.PointObj.GetCoordCartesian(pt, 0, 0, 0)
            coord = (round(c[1], 4), round(c[2], 4), round(c[3], 4))
            endpoint_counts[coord] = endpoint_counts.get(coord, 0) + 1

        c_i = SapModel.PointObj.GetCoordCartesian(pts[1], 0, 0, 0)
        c_j = SapModel.PointObj.GetCoordCartesian(pts[2], 0, 0, 0)
        frame_endpoints[name] = (
            (round(c_i[1], 4), round(c_i[2], 4), round(c_i[3], 4)),
            (round(c_j[1], 4), round(c_j[2], 4), round(c_j[3], 4))
        )

    # Assign releases to beams (not columns)
    release_count = 0
    for i in range(num):
        name = names[i]
        prop = props[i]

        # Skip columns
        if prop.startswith('C') and 'X' in prop and not prop.startswith('CB'):
            continue

        if name not in frame_endpoints:
            continue

        coord_i, coord_j = frame_endpoints[name]

        # A point is "continuous" if more than one frame endpoint shares it
        i_continuous = endpoint_counts.get(coord_i, 0) > 1
        j_continuous = endpoint_counts.get(coord_j, 0) > 1

        if not i_continuous and not j_continuous:
            SapModel.FrameObj.SetReleases(name, RELEASE_M2M3, RELEASE_M2M3,
                                          ZERO_SPRINGS, ZERO_SPRINGS)
            release_count += 1
        elif not i_continuous:
            SapModel.FrameObj.SetReleases(name, RELEASE_M2M3, NO_RELEASE,
                                          ZERO_SPRINGS, ZERO_SPRINGS)
            release_count += 1
        elif not j_continuous:
            SapModel.FrameObj.SetReleases(name, NO_RELEASE, RELEASE_M2M3,
                                          ZERO_SPRINGS, ZERO_SPRINGS)
            release_count += 1

    print(f"  End releases assigned: {release_count} beams")
    return release_count


def run(SapModel, config):
    """Execute step 09: properties assignment."""
    print("=" * 60)
    print("STEP 09: Structural Properties (Modifiers, RZ, Releases)")
    print("=" * 60)

    print("\n--- Frame Modifiers ---")
    assign_frame_modifiers(SapModel)

    print("\n--- Rigid Zones ---")
    assign_rigid_zones(SapModel)

    print("\n--- End Releases ---")
    assign_end_releases(SapModel)

    SapModel.View.RefreshView(0, False)
    print("Step 09 complete.\n")


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "model_config.json"
    with open(config_path) as f:
        config = json.load(f)
    from gs_01_init import connect_etabs
    SapModel = connect_etabs(config)
    run(SapModel, config)
