"""
Assign structural properties to ETABS model elements.
Covers: stiffness modifiers, rebar, rigid zones, end releases, diaphragms.

Usage: Called by the agent after elements are created. Not standalone.
"""
import sys
import os
import re
import math
sys.path.insert(0, os.path.dirname(__file__))


# ── Stiffness Modifiers ──────────────────────────────────────

# Frame modifiers: [Area, As2, As3, Torsion, I22, I33, Mass, Weight]
BEAM_MODIFIERS = [1, 1, 1, 0.0001, 0.7, 0.7, 0.8, 0.8]
COL_MODIFIERS  = [1, 1, 1, 0.0001, 0.7, 0.7, 0.95, 0.95]

# Area modifiers: [f11, f22, f12, m11, m22, m12, v13, v23, Mass, Weight]
SLAB_WALL_MODIFIERS = [0.4, 0.4, 0.4, 1, 1, 1, 1, 1, 1, 1]  # Membrane type
RAFT_MODIFIERS      = [0.4, 0.4, 0.4, 0.7, 0.7, 0.7, 1, 1, 1, 1]  # ShellThick type


def assign_frame_modifiers(SapModel, frame_names, element_type):
    """Assign stiffness modifiers to frames.
    element_type: 'beam' | 'column'
    """
    mods = BEAM_MODIFIERS if element_type == "beam" else COL_MODIFIERS
    count = 0
    for name in frame_names:
        ret = SapModel.FrameObj.SetModifiers(name, mods)
        if ret == 0:
            count += 1
    print(f"  {element_type} modifiers assigned: {count}/{len(frame_names)}")
    return count


def assign_area_modifiers(SapModel, area_names, element_type):
    """Assign stiffness modifiers to area objects.
    element_type: 'slab' | 'wall' | 'raft'
    """
    if element_type == "raft":
        mods = RAFT_MODIFIERS
    else:
        mods = SLAB_WALL_MODIFIERS
    count = 0
    for name in area_names:
        ret = SapModel.PropArea.SetModifiers(name, mods)
        if ret == 0:
            count += 1
    print(f"  {element_type} modifiers assigned: {count}/{len(area_names)}")
    return count


# ── Rebar Configuration ──────────────────────────────────────

def assign_beam_rebar(SapModel, beam_sec_name, is_foundation=False):
    """Assign beam rebar configuration to a section property.

    Cover:
        - Regular beams: top=9cm, bottom=9cm (0.09m)
        - Foundation beams (FB/FSB/FWB): top=11cm, bottom=15cm (0.11m/0.15m)
    """
    if is_foundation:
        cover_top = 0.11
        cover_bot = 0.15
    else:
        cover_top = 0.09
        cover_bot = 0.09

    ret = SapModel.PropFrame.SetRebarBeam(
        beam_sec_name,
        "SD420",       # MatLongit
        "SD420",       # MatConfine
        cover_top,     # CoverTop
        cover_bot,     # CoverBot
        0, 0, 0, 0,   # TopLeftArea, TopRightArea, BotLeftArea, BotRightArea
        True           # ToBeDesigned
    )
    return ret == 0


def assign_column_rebar(SapModel, col_sec_name, width_cm, depth_cm):
    """Assign column rebar configuration to a section property.

    Cover: 7cm (0.07m)
    Bar distribution: proportional to width:depth ratio
        Square AxA -> NumR2=3, NumR3=3
        Rect WxD: NumR2:NumR3 = W:D (min=2)
    """
    cover = 0.07  # 7cm in meters

    # Calculate bar distribution based on aspect ratio
    ratio = width_cm / depth_cm
    if abs(ratio - 1.0) < 0.1:  # square
        num_r2, num_r3 = 3, 3
    else:
        # Scale to reasonable bar counts (min=2, max=6)
        if ratio > 1:
            num_r3 = 2
            num_r2 = max(2, min(6, round(2 * ratio)))
        else:
            num_r2 = 2
            num_r3 = max(2, min(6, round(2 / ratio)))

    ret = SapModel.PropFrame.SetRebarColumn(
        col_sec_name,
        "SD420",       # MatLongit
        "SD420",       # MatConfine
        1,             # Pattern: 1=Rectangular
        1,             # ConfineType: 1=Ties
        cover,         # Cover: 7cm -> 0.07m
        4,             # NumCornerBars
        num_r3,        # NumBarsR3 (along depth)
        num_r2,        # NumBarsR2 (along width)
        "#8",          # RebarSize (placeholder, design will adjust)
        "#4",          # TieSize
        0.15,          # TieSpacing: 15cm -> 0.15m
        2,             # Num2DirTie
        2,             # Num3DirTie
        True           # ToBeDesigned = True
    )
    return ret == 0


def batch_assign_rebar(SapModel, frame_sections):
    """Assign rebar to all frame section properties.

    frame_sections: list of section names (with C{fc} suffix)
    Parses prefix to determine beam vs column, foundation vs regular.
    """
    beam_count, col_count = 0, 0
    for sec_name in frame_sections:
        m = re.match(r'^(B|SB|WB|FB|FSB|FWB|C)(\d+)X(\d+)C\d+$', sec_name)
        if not m:
            continue
        prefix = m.group(1)
        width = int(m.group(2))
        depth = int(m.group(3))

        if prefix == "C":
            if assign_column_rebar(SapModel, sec_name, width, depth):
                col_count += 1
        else:
            is_fb = prefix in ("FB", "FSB", "FWB")
            if assign_beam_rebar(SapModel, sec_name, is_foundation=is_fb):
                beam_count += 1

    print(f"  Rebar assigned: {beam_count} beams, {col_count} columns")
    return beam_count, col_count


# ── Rigid Zones ──────────────────────────────────────────────

def assign_rigid_zones(SapModel, frame_names, rz_factor=0.75):
    """Assign rigid zone factor to all frame objects.
    AutoOffset=True, RZ=0.75
    """
    count = 0
    for name in frame_names:
        ret = SapModel.FrameObj.SetEndLengthOffset(name, True, 0, 0, rz_factor)
        if ret == 0:
            count += 1
    print(f"  Rigid zones (RZ={rz_factor}) assigned: {count}/{len(frame_names)}")
    return count


# ── End Releases ─────────────────────────────────────────────

def determine_releases(SapModel, beam_names, all_frame_endpoints):
    """Determine and assign end releases for beams.

    Rule: If a beam end is NOT continuous (no column or other beam at that point),
    release M2 + M3 at that end.

    all_frame_endpoints: set of (x, y, z) tuples for all frame endpoints
    """
    release = [False, False, False, False, True, True]   # release M2+M3
    no_release = [False, False, False, False, False, False]
    zeros = [0.0] * 6

    count = 0
    for beam in beam_names:
        # Get beam endpoints
        ret = SapModel.FrameObj.GetPoints(beam, "", "")
        if ret[0] != 0:
            continue
        pt_i, pt_j = ret[1], ret[2]

        # Get coordinates of each end
        ret_i = SapModel.PointObj.GetCoordCartesian(pt_i, 0, 0, 0)
        ret_j = SapModel.PointObj.GetCoordCartesian(pt_j, 0, 0, 0)
        coord_i = (round(ret_i[1], 4), round(ret_i[2], 4), round(ret_i[3], 4))
        coord_j = (round(ret_j[1], 4), round(ret_j[2], 4), round(ret_j[3], 4))

        # Check continuity: does another frame share this endpoint?
        # A point is continuous if at least one OTHER frame also has this coordinate
        i_continuous = coord_i in all_frame_endpoints
        j_continuous = coord_j in all_frame_endpoints

        if not i_continuous and not j_continuous:
            SapModel.FrameObj.SetReleases(beam, release, release, zeros, zeros)
            count += 1
        elif not i_continuous:
            SapModel.FrameObj.SetReleases(beam, release, no_release, zeros, zeros)
            count += 1
        elif not j_continuous:
            SapModel.FrameObj.SetReleases(beam, no_release, release, zeros, zeros)
            count += 1

    print(f"  End releases assigned: {count}/{len(beam_names)} beams")
    return count


def collect_frame_endpoints(SapModel):
    """Collect all frame endpoint coordinates for continuity checking.
    Returns a set of (x, y, z) tuples, and a dict of beam_name -> (pt_i_coord, pt_j_coord).
    """
    endpoints = set()
    # Get all frames
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [], [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])
    if ret[0] == 0:
        return endpoints

    num = ret[0]
    names = ret[1]
    for i in range(num):
        name = names[i]
        pts = SapModel.FrameObj.GetPoints(name, "", "")
        if pts[0] != 0:
            continue
        for pt in [pts[1], pts[2]]:
            c = SapModel.PointObj.GetCoordCartesian(pt, 0, 0, 0)
            endpoints.add((round(c[1], 4), round(c[2], 4), round(c[3], 4)))
    return endpoints


# ── Diaphragm Assignment ─────────────────────────────────────

def assign_diaphragms(SapModel, story_slab_map):
    """Assign rigid diaphragm to slab corner points only.

    story_slab_map: dict mapping story_name -> list of area object names (slabs)

    IMPORTANT: Only assign diaphragm to slab corner points, NOT all joints.
    """
    count = 0
    for story, slab_names in story_slab_map.items():
        diaphragm_name = f"D_{story}"
        # Create diaphragm definition (rigid)
        SapModel.Diaphragm.SetDiaphragm(diaphragm_name, False)

        pts_assigned = set()
        for area_name in slab_names:
            # Get corner points of this slab
            ret = SapModel.AreaObj.GetPoints(area_name, 0, [])
            if ret[0] != 0:
                continue
            corner_points = ret[2] if isinstance(ret[2], (list, tuple)) else [ret[2]]
            for pt in corner_points:
                if pt not in pts_assigned:
                    SapModel.PointObj.SetDiaphragm(pt, 3, diaphragm_name)
                    pts_assigned.add(pt)
                    count += 1

        print(f"  Diaphragm {diaphragm_name}: {len(pts_assigned)} points")

    print(f"  Total diaphragm point assignments: {count}")
    return count


# ── Master Assign Function ───────────────────────────────────

def assign_all_properties(SapModel, beam_names, col_names,
                          slab_names, wall_names, raft_names,
                          frame_sections, story_slab_map):
    """Run all property assignments in sequence."""
    print("=== Assigning Stiffness Modifiers ===")
    assign_frame_modifiers(SapModel, beam_names, "beam")
    assign_frame_modifiers(SapModel, col_names, "column")
    assign_area_modifiers(SapModel, slab_names, "slab")
    assign_area_modifiers(SapModel, wall_names, "wall")
    assign_area_modifiers(SapModel, raft_names, "raft")

    print("\n=== Assigning Rebar ===")
    batch_assign_rebar(SapModel, frame_sections)

    print("\n=== Assigning Rigid Zones ===")
    all_frames = beam_names + col_names
    assign_rigid_zones(SapModel, all_frames)

    print("\n=== Assigning End Releases ===")
    endpoints = collect_frame_endpoints(SapModel)
    determine_releases(SapModel, beam_names, endpoints)

    print("\n=== Assigning Diaphragms ===")
    assign_diaphragms(SapModel, story_slab_map)

    SapModel.View.RefreshView(0, False)
    print("\nAll properties assigned.")
