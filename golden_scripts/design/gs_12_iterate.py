"""
Golden Script 12: Analysis-Design Iteration Loop

Automates column/beam sizing optimization based on rebar ratio feedback
from ETABS concrete design results (ACI 318-19).

Two phases:
  Phase 1 - Superstructure iteration (USS combos): resize columns/beams
            based on rebar ratios, enforce monotonic + strength boundary
            constraints on columns.
  Phase 2 - Substructure check (BUSS combos): enforce sub columns >= super.
"""
import sys
import os
import re
from collections import Counter

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_dir))      # golden_scripts/ (constants)
from constants import (
    UNITS_TON_M,
    parse_frame_section, is_foundation_beam,
    get_frame_dimensions, calc_column_bar_distribution,
    build_strength_lookup,
    BEAM_MODIFIERS, COL_MODIFIERS,
    BEAM_COVER_TOP, BEAM_COVER_BOT, FB_COVER_TOP, FB_COVER_BOT,
    COL_COVER,
    COL_CORNER_BARS, COL_TIE_SPACING,
    COL_REBAR_SIZE, COL_TIE_SIZE, COL_NUM_2DIR_TIE, COL_NUM_3DIR_TIE,
    MIN_COL_DIM, MIN_BEAM_W, MIN_BEAM_D,
    COL_REBAR_DOWNSIZE, COL_REBAR_MAX, COL_RESIZE_STEP,
    BEAM_REBAR_MIN, BEAM_REBAR_MAX, BEAM_RESIZE_STEP, BEAM_MAX_WIDTH_RATIO,
    MAX_ITERATIONS, DESIGN_CODE, ITER_SKIP_PREFIXES,
    SWAY_SPECIAL, SWAY_ORDINARY,
    SUPER_COMBOS, SUB_COMBOS,
)


# ======================================================================
# Pure Functions (testable without ETABS)
# ======================================================================

def compute_column_ratio(pmm_area_m2, w_cm, d_cm):
    """Compute column rebar ratio = PMMArea / (W * D)."""
    gross = (w_cm / 100.0) * (d_cm / 100.0)
    return pmm_area_m2 / gross if gross > 0 else 0


def compute_beam_ratio(max_rebar_area_m2, w_cm, d_cm, cover_m=BEAM_COVER_TOP):
    """Compute beam rebar ratio = max_area / (W * d_eff)."""
    w_m = w_cm / 100.0
    d_eff = d_cm / 100.0 - cover_m
    return max_rebar_area_m2 / (w_m * d_eff) if (w_m * d_eff) > 0 else 0


def propose_column_resize(ratio, w_cm, d_cm, step=COL_RESIZE_STEP,
                           down_thresh=COL_REBAR_DOWNSIZE,
                           up_thresh=COL_REBAR_MAX,
                           min_dim=MIN_COL_DIM):
    """Propose new column dimensions based on rebar ratio.

    Returns (new_w, new_d, direction) or None if no change.
    direction: 'up' or 'down'.
    """
    if ratio <= down_thresh:
        new_w = max(min_dim, w_cm - step)
        new_d = max(min_dim, d_cm - step)
        if new_w != w_cm or new_d != d_cm:
            return new_w, new_d, "down"
    elif ratio > up_thresh:
        return w_cm + step, d_cm + step, "up"
    return None


def propose_beam_resize(ratio, w_cm, d_cm, step=BEAM_RESIZE_STEP,
                         down_thresh=BEAM_REBAR_MIN,
                         up_thresh=BEAM_REBAR_MAX,
                         max_wd_ratio=BEAM_MAX_WIDTH_RATIO,
                         min_w=MIN_BEAM_W, min_d=MIN_BEAM_D):
    """Propose new beam dimensions based on rebar ratio.

    Width increases first; when W >= 1.2*D, switch to depth.
    Returns (new_w, new_d, direction) or None if no change.
    """
    if ratio < down_thresh:
        new_w = max(min_w, w_cm - step)
        if new_w != w_cm:
            return new_w, d_cm, "down"
        new_d = max(min_d, d_cm - step)
        if new_d != d_cm:
            return w_cm, new_d, "down"
        return None
    elif ratio > up_thresh:
        if (w_cm + step) / d_cm < max_wd_ratio:
            return w_cm + step, d_cm, "up"
        else:
            return w_cm, d_cm + step, "up"
    return None


def enforce_column_constraints(positions, strength_lookup, story_order):
    """Enforce monotonic non-decreasing downward + strength boundary equalization.

    Args:
        positions: {(x, y): [{story, w, d, fc, frame}, ...]}
            Each list is ordered bottom-to-top by story_order.
        strength_lookup: {(story, "column"): fc_grade}
        story_order: list of story names, bottom to top.

    Modifies positions in place. Returns positions.
    """
    story_idx = {s: i for i, s in enumerate(story_order)}

    for pos_key, col_list in positions.items():
        if len(col_list) < 2:
            continue

        col_list.sort(key=lambda c: story_idx.get(c["story"], 0))

        for _pass in range(3):
            changed = False

            # Step 1: Boundary equalization
            for i in range(len(col_list) - 1):
                fc_below = strength_lookup.get((col_list[i]["story"], "column"))
                fc_above = strength_lookup.get((col_list[i + 1]["story"], "column"))
                if fc_below is not None and fc_above is not None and fc_below != fc_above:
                    max_w = max(col_list[i]["w"], col_list[i + 1]["w"])
                    max_d = max(col_list[i]["d"], col_list[i + 1]["d"])
                    if col_list[i]["w"] != max_w or col_list[i]["d"] != max_d:
                        changed = True
                    if col_list[i + 1]["w"] != max_w or col_list[i + 1]["d"] != max_d:
                        changed = True
                    col_list[i]["w"] = max_w
                    col_list[i]["d"] = max_d
                    col_list[i + 1]["w"] = max_w
                    col_list[i + 1]["d"] = max_d

            # Step 2: Monotonic sweep (lower floor >= upper floor)
            for i in range(len(col_list) - 2, -1, -1):
                new_w = max(col_list[i]["w"], col_list[i + 1]["w"])
                new_d = max(col_list[i]["d"], col_list[i + 1]["d"])
                if col_list[i]["w"] != new_w or col_list[i]["d"] != new_d:
                    changed = True
                    col_list[i]["w"] = new_w
                    col_list[i]["d"] = new_d

            if not changed:
                break

    return positions


def make_section_name(prefix, w_cm, d_cm, fc):
    """Generate section name: {PREFIX}{W}X{D}C{fc}."""
    return f"{prefix}{w_cm}X{d_cm}C{fc}"


def is_rooftop_ordinary(story_name):
    """Check if a story should use Sway Ordinary on rooftop (R2F~PRF)."""
    if story_name == "PRF":
        return True
    m = re.match(r'^R(\d+)F$', story_name)
    if m and int(m.group(1)) >= 2:
        return True
    return False


# ======================================================================
# ETABS-Dependent Functions
# ======================================================================

def classify_floors(config):
    """Classify floors into superstructure and substructure.

    Substructure: 1F and below (inclusive).
    Superstructure: above 1F elevation.

    Returns (super_stories, sub_stories, story_elevations, all_story_names).
    """
    stories = config.get("stories", [])
    all_story_names = [s["name"] for s in stories]

    base_elev = config.get("base_elevation", 0)
    cumulative = base_elev
    story_elevations = {}
    for s in stories:
        cumulative += s["height"]
        story_elevations[s["name"]] = cumulative

    elev_1f = story_elevations.get("1F", 0)

    super_stories = []
    sub_stories = []
    for name, elev in story_elevations.items():
        if elev > elev_1f:
            super_stories.append(name)
        else:
            sub_stories.append(name)

    return super_stories, sub_stories, story_elevations, all_story_names


def get_all_frames_data(SapModel):
    """Get all frame objects data from ETABS."""
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [], [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])

    if isinstance(ret[0], int) and ret[0] > 0:
        return {
            "count": ret[0],
            "names": ret[1],
            "props": ret[2],
            "stories": ret[3],
            "pt1x": ret[6],
            "pt1y": ret[7],
            "pt1z": ret[8],
            "pt2x": ret[9],
            "pt2y": ret[10],
            "pt2z": ret[11],
        }
    return {
        "count": 0, "names": [], "props": [], "stories": [],
        "pt1x": [], "pt1y": [], "pt1z": [],
        "pt2x": [], "pt2y": [], "pt2z": [],
    }


def _is_vertical(i, data):
    """Check if frame at index i is vertical (column)."""
    return (abs(data["pt1x"][i] - data["pt2x"][i]) < 0.01 and
            abs(data["pt1y"][i] - data["pt2y"][i]) < 0.01 and
            abs(data["pt1z"][i] - data["pt2z"][i]) > 0.01)


def assign_sway_types(SapModel, frames_data, super_stories, sub_stories):
    """Assign ACI318-19 sway frame types to all frames."""
    super_set = set(super_stories)
    count = 0

    for i in range(frames_data["count"]):
        frame = frames_data["names"][i]
        prop = frames_data["props"][i]
        story = frames_data["stories"][i]

        prefix, _, _, _ = parse_frame_section(prop)
        if not prefix:
            continue

        if story in super_set:
            if is_rooftop_ordinary(story):
                sway_type = SWAY_ORDINARY
            elif prefix in ("C", "B", "WB"):
                sway_type = SWAY_SPECIAL
            else:
                sway_type = SWAY_ORDINARY
        else:
            sway_type = SWAY_ORDINARY

        ret = SapModel.DesignConcrete.ACI318_19.SetOverwrite(
            frame, 1, float(sway_type))
        if ret == 0:
            count += 1

    print(f"  Sway types assigned: {count} frames")


def setup_combos(SapModel, enable_list, disable_list):
    """Enable one set of combos and disable another."""
    enabled = disabled = 0
    for combo in enable_list:
        if SapModel.DesignConcrete.SetComboStrength(combo, True) == 0:
            enabled += 1
    for combo in disable_list:
        if SapModel.DesignConcrete.SetComboStrength(combo, False) == 0:
            disabled += 1
    return enabled, disabled


def run_analysis_and_design(SapModel, design_code=DESIGN_CODE):
    """Save, run analysis, set design code, run design."""
    SapModel.File.Save()
    print("    Running analysis...")
    ret = SapModel.Analyze.RunAnalysis()
    if ret != 0:
        print(f"    WARNING: RunAnalysis returned {ret}")

    SapModel.DesignConcrete.SetCode(design_code)
    print("    Running concrete design...")
    ret = SapModel.DesignConcrete.StartDesign()
    if ret != 0:
        print(f"    WARNING: StartDesign returned {ret}")


def _classify_frames(frames_data, super_stories, skip_prefixes):
    """Classify all frames into column/beam lists for superstructure.

    Returns (columns, beams) where:
      columns: [{frame, prop, story, x, y, prefix, w_cm, d_cm, fc}, ...]
      beams:   [{frame, prop, story, prefix, w_cm, d_cm, fc}, ...]
    """
    super_set = set(super_stories)
    skip = set(skip_prefixes)
    columns = []
    beams = []

    for i in range(frames_data["count"]):
        story = frames_data["stories"][i]
        if story not in super_set:
            continue

        prop = frames_data["props"][i]
        prefix, w_cm, d_cm, fc = parse_frame_section(prop)
        if not prefix or not w_cm or not d_cm:
            continue

        frame = frames_data["names"][i]

        if prefix == "C" and _is_vertical(i, frames_data):
            columns.append({
                "frame": frame, "prop": prop, "story": story,
                "x": round(frames_data["pt1x"][i], 2),
                "y": round(frames_data["pt1y"][i], 2),
                "prefix": prefix, "w_cm": w_cm, "d_cm": d_cm, "fc": fc,
            })
        elif prefix in skip:
            continue
        elif prefix in ("B", "WB", "SB"):
            beams.append({
                "frame": frame, "prop": prop, "story": story,
                "prefix": prefix, "w_cm": w_cm, "d_cm": d_cm, "fc": fc,
            })

    return columns, beams


def extract_column_results(SapModel, columns):
    """Get design results for columns and compute rebar ratios."""
    results = []
    for col in columns:
        try:
            ret = SapModel.DesignConcrete.GetSummaryResultsColumn(
                col["frame"], 0, [], [], [], [], [], [], [], [], [], [], [], [])
            n_items = ret[0]
            if isinstance(n_items, int) and n_items > 0:
                pmm_areas = ret[5]
                max_pmm = max(pmm_areas) if pmm_areas else 0.0
                ratio = compute_column_ratio(max_pmm, col["w_cm"], col["d_cm"])
                results.append({**col, "pmm_area": max_pmm, "ratio": ratio})
        except Exception:
            pass
    return results


def extract_beam_results(SapModel, beams):
    """Get design results for beams and compute rebar ratios."""
    results = []
    for beam in beams:
        try:
            ret = SapModel.DesignConcrete.GetSummaryResultsBeam(
                beam["frame"], 0, [], [], [], [], [], [], [], [],
                [], [], [], [], [], [])
            n_items = ret[0]
            if isinstance(n_items, int) and n_items > 0:
                top_areas = ret[4]
                bot_areas = ret[6]
                max_top = max(top_areas) if top_areas else 0.0
                max_bot = max(bot_areas) if bot_areas else 0.0
                max_area = max(max_top, max_bot)
                ratio = compute_beam_ratio(max_area, beam["w_cm"], beam["d_cm"])
                results.append({**beam, "max_area": max_area, "ratio": ratio})
        except Exception:
            pass
    return results


def ensure_section_exists(SapModel, prefix, num1, num2, fc):
    """Create a frame section if it doesn't already exist.

    Args:
        num1, num2: raw parsed numbers from section name.
            Beams: num1=width, num2=depth.
            Columns: num1=depth, num2=width.
    """
    name = make_section_name(prefix, num1, num2, fc)
    mat = f"C{fc}"
    width_cm, depth_cm = get_frame_dimensions(prefix, num1, num2)
    depth_m = depth_cm / 100.0
    width_m = width_cm / 100.0

    SapModel.PropFrame.SetRectangle(name, mat, depth_m, width_m)

    if prefix == "C":
        num_r3, num_r2 = calc_column_bar_distribution(width_cm, depth_cm)
        SapModel.PropFrame.SetRebarColumn(
            name, "SD420", "SD420",
            1, 1, COL_COVER, COL_CORNER_BARS,
            num_r3, num_r2,
            COL_REBAR_SIZE, COL_TIE_SIZE, COL_TIE_SPACING,
            COL_NUM_2DIR_TIE, COL_NUM_3DIR_TIE, True)
    else:
        is_fb = is_foundation_beam(prefix)
        cover_top = FB_COVER_TOP if is_fb else BEAM_COVER_TOP
        cover_bot = FB_COVER_BOT if is_fb else BEAM_COVER_BOT
        SapModel.PropFrame.SetRebarBeam(
            name, "SD420", "SD420",
            cover_top, cover_bot,
            0, 0, 0, 0)

    return name


def apply_frame_changes(SapModel, changes):
    """Apply section changes to frames.

    changes: [{frame, new_section, prefix}, ...]
    Returns number of frames changed.
    """
    count = 0
    for ch in changes:
        ret = SapModel.FrameObj.SetSection(ch["frame"], ch["new_section"])
        if ret != 0:
            continue
        mods = COL_MODIFIERS if ch["prefix"] == "C" else BEAM_MODIFIERS
        SapModel.FrameObj.SetModifiers(ch["frame"], mods)
        count += 1
    return count


# ======================================================================
# Iteration Logic
# ======================================================================

def _build_column_positions(col_results):
    """Group column results by (x, y) position.

    Returns {(x, y): [{story, w, d, fc, frame, ratio}, ...]}
    """
    positions = {}
    for col in col_results:
        key = (col["x"], col["y"])
        positions.setdefault(key, []).append({
            "story": col["story"],
            "w": col["w_cm"],
            "d": col["d_cm"],
            "fc": col["fc"],
            "frame": col["frame"],
            "ratio": col["ratio"],
        })
    return positions


def _build_beam_groups(beam_results):
    """Group beam results by (section_name, story), track worst ratio.

    Returns {(section, story): {frames, worst_ratio, prefix, w_cm, d_cm, fc}}
    """
    groups = {}
    for b in beam_results:
        key = (b["prop"], b["story"])
        if key not in groups:
            groups[key] = {
                "frames": [],
                "worst_ratio": 0,
                "prefix": b["prefix"],
                "w_cm": b["w_cm"],
                "d_cm": b["d_cm"],
                "fc": b["fc"],
            }
        groups[key]["frames"].append(b["frame"])
        if b["ratio"] > groups[key]["worst_ratio"]:
            groups[key]["worst_ratio"] = b["ratio"]
    return groups


def _iterate_superstructure(SapModel, config, strength_lookup,
                            super_stories, all_story_names, iter_cfg):
    """Run the superstructure iteration loop. Returns final column sizes by position."""
    max_iter = iter_cfg["max_iterations"]
    col_down = iter_cfg["col_rebar_downsize"]
    col_up = iter_cfg["col_rebar_max"]
    col_step = iter_cfg["col_resize_step"]
    beam_down = iter_cfg["beam_rebar_min"]
    beam_up = iter_cfg["beam_rebar_max"]
    beam_step = iter_cfg["beam_resize_step"]
    beam_wd = iter_cfg["beam_max_width_ratio"]
    skip = iter_cfg["skip_prefixes"]
    design_code = iter_cfg["design_code"]

    # Oscillation tracking: {frame_name: {"last_dir": str, "toggles": int}}
    osc_history = {}

    final_col_sizes = {}  # {(x, y): {story: (w, d)}}

    for iteration in range(1, max_iter + 1):
        print(f"\n  --- Iteration {iteration}/{max_iter} ---")

        run_analysis_and_design(SapModel, design_code)

        frames_data = get_all_frames_data(SapModel)
        columns, beams = _classify_frames(frames_data, super_stories, skip)

        col_results = extract_column_results(SapModel, columns)
        beam_results = extract_beam_results(SapModel, beams)

        print(f"    Columns with results: {len(col_results)}")
        print(f"    Beams with results:   {len(beam_results)}")

        # ── Column resizing ──
        col_positions = _build_column_positions(col_results)
        col_changes = []

        for pos_key, col_list in col_positions.items():
            for col in col_list:
                proposal = propose_column_resize(
                    col["ratio"], col["w"], col["d"],
                    step=col_step, down_thresh=col_down, up_thresh=col_up)
                if proposal:
                    col["w"], col["d"] = proposal[0], proposal[1]
                    direction = proposal[2]
                    # Oscillation check
                    hist = osc_history.get(col["frame"])
                    if hist and hist["last_dir"] != direction:
                        hist["toggles"] += 1
                        if hist["toggles"] >= 2:
                            # Freeze at larger size (revert downsize)
                            if direction == "down":
                                col["w"] += col_step
                                col["d"] += col_step
                            continue
                    osc_history[col["frame"]] = {
                        "last_dir": direction,
                        "toggles": hist["toggles"] if hist else 0,
                    }

        # Enforce column constraints
        enforce_column_constraints(col_positions, strength_lookup, all_story_names)

        # Collect column changes
        for pos_key, col_list in col_positions.items():
            for col in col_list:
                old_prefix, old_w, old_d, old_fc = parse_frame_section(
                    next((c["prop"] for c in col_results
                          if c["frame"] == col["frame"]), ""))
                if old_w and (col["w"] != old_w or col["d"] != old_d):
                    new_sec = ensure_section_exists(
                        SapModel, "C", col["w"], col["d"], col["fc"])
                    col_changes.append({
                        "frame": col["frame"],
                        "new_section": new_sec,
                        "prefix": "C",
                    })
            # Track final sizes
            if col_list:
                final_col_sizes[pos_key] = {
                    c["story"]: (c["w"], c["d"]) for c in col_list
                }

        # ── Beam resizing ──
        beam_groups = _build_beam_groups(beam_results)
        beam_changes = []

        for (sec_name, story), grp in beam_groups.items():
            proposal = propose_beam_resize(
                grp["worst_ratio"], grp["w_cm"], grp["d_cm"],
                step=beam_step, down_thresh=beam_down, up_thresh=beam_up,
                max_wd_ratio=beam_wd)
            if proposal:
                new_w, new_d, direction = proposal
                # Oscillation check on group key
                osc_key = f"beam_{sec_name}_{story}"
                hist = osc_history.get(osc_key)
                if hist and hist["last_dir"] != direction:
                    hist["toggles"] += 1
                    if hist["toggles"] >= 2:
                        continue
                osc_history[osc_key] = {
                    "last_dir": direction,
                    "toggles": hist["toggles"] if hist else 0,
                }

                new_sec = ensure_section_exists(
                    SapModel, grp["prefix"], new_w, new_d, grp["fc"])
                for frame in grp["frames"]:
                    beam_changes.append({
                        "frame": frame,
                        "new_section": new_sec,
                        "prefix": grp["prefix"],
                    })

        # ── Apply changes ──
        total_changes = len(col_changes) + len(beam_changes)
        if total_changes == 0:
            print(f"    CONVERGED - no changes needed")
            break

        n_col = apply_frame_changes(SapModel, col_changes)
        n_beam = apply_frame_changes(SapModel, beam_changes)
        print(f"    Applied: {n_col} column + {n_beam} beam changes")

        # Summary stats
        if col_results:
            col_ratios = [c["ratio"] for c in col_results]
            print(f"    Column ratios: min={min(col_ratios):.4f} "
                  f"max={max(col_ratios):.4f} avg={sum(col_ratios)/len(col_ratios):.4f}")
        if beam_results:
            beam_ratios = [b["ratio"] for b in beam_results]
            print(f"    Beam ratios:   min={min(beam_ratios):.4f} "
                  f"max={max(beam_ratios):.4f} avg={sum(beam_ratios)/len(beam_ratios):.4f}")

    else:
        print(f"\n  WARNING: Max iterations ({max_iter}) reached without convergence")

    return final_col_sizes


def _enforce_sub_column_sizes(SapModel, config, super_col_sizes,
                               sub_stories, all_story_names, strength_lookup):
    """Ensure substructure columns are >= the lowest superstructure column at same position."""
    frames_data = get_all_frames_data(SapModel)
    sub_set = set(sub_stories)
    changes = []

    for i in range(frames_data["count"]):
        story = frames_data["stories"][i]
        if story not in sub_set:
            continue

        prop = frames_data["props"][i]
        prefix, w_cm, d_cm, fc = parse_frame_section(prop)
        if prefix != "C" or not _is_vertical(i, frames_data):
            continue

        x = round(frames_data["pt1x"][i], 2)
        y = round(frames_data["pt1y"][i], 2)
        pos_key = (x, y)

        if pos_key not in super_col_sizes:
            continue

        # Get the smallest (lowest floor) superstructure column at this position
        super_sizes = super_col_sizes[pos_key]
        if not super_sizes:
            continue

        # Find the lowest superstructure story (smallest elevation)
        story_idx = {s: i for i, s in enumerate(all_story_names)}
        lowest_super = min(super_sizes.keys(), key=lambda s: story_idx.get(s, 999))
        req_w, req_d = super_sizes[lowest_super]

        if w_cm < req_w or d_cm < req_d:
            new_w = max(w_cm, req_w)
            new_d = max(d_cm, req_d)
            fc_sub = strength_lookup.get((story, "column"), fc)
            new_sec = ensure_section_exists(SapModel, "C", new_w, new_d, fc_sub)
            changes.append({
                "frame": frames_data["names"][i],
                "new_section": new_sec,
                "prefix": "C",
            })

    if changes:
        n = apply_frame_changes(SapModel, changes)
        print(f"  Substructure columns upsized: {n}")
    else:
        print(f"  Substructure columns: all OK (>= superstructure)")


# ======================================================================
# Auto-Extract Config from ETABS Model
# ======================================================================

def build_config_from_etabs(SapModel):
    """One-time extraction of iteration config from the live ETABS model.

    Reads stories and frame sections to infer all parameters needed
    for the iteration loop. Called once; result reused across all iterations.
    """
    SapModel.SetPresentUnits(UNITS_TON_M)

    # 1. Read stories
    ret = SapModel.Story.GetStories_2(0.0, 0, [], [], [], [], [], [], [], [])
    base_elev = ret[0]
    num_stories = ret[1]
    raw_names = list(ret[2])
    raw_elevs = list(ret[3])
    raw_heights = list(ret[4])

    # Sort bottom-to-top by elevation
    order = sorted(range(num_stories), key=lambda i: raw_elevs[i])
    stories = [{"name": raw_names[i], "height": raw_heights[i]} for i in order]
    all_story_names = [s["name"] for s in stories]

    # 2. Scan frames to infer strength_map
    frames_data = get_all_frames_data(SapModel)

    story_fc = {}  # {(story, elem_type): Counter({fc: count})}
    for i in range(frames_data["count"]):
        prop = frames_data["props"][i]
        story = frames_data["stories"][i]
        prefix, w, d, fc = parse_frame_section(prop)
        if not prefix or not fc:
            continue

        if prefix == "C" and _is_vertical(i, frames_data):
            elem_type = "column"
        elif prefix in ("B", "WB", "SB", "FB", "FSB", "FWB"):
            elem_type = "beam"
        else:
            continue

        key = (story, elem_type)
        if key not in story_fc:
            story_fc[key] = Counter()
        story_fc[key][fc] += 1

    # Build strength_map: per-story format (compatible with build_strength_lookup)
    strength_map = {}
    for (story, elem_type), counter in story_fc.items():
        if story not in strength_map:
            strength_map[story] = {}
        strength_map[story][elem_type] = counter.most_common(1)[0][0]

    config = {
        "base_elevation": base_elev,
        "stories": stories,
        "strength_map": strength_map,
        "iteration": {},  # use all defaults from constants
    }

    print(f"  Auto-extracted config from ETABS model:")
    print(f"    Stories: {num_stories} ({all_story_names[0]} ~ {all_story_names[-1]})")
    print(f"    Base elevation: {base_elev}m")
    print(f"    Strength zones: {len(strength_map)} stories with fc data")

    return config


# ======================================================================
# Main Entry Point
# ======================================================================

def run(SapModel, config=None):
    """Execute step 12: analysis-design iteration loop.

    If config is None, automatically extracts all needed parameters
    from the current ETABS model (one-time read).
    """
    print("=" * 60)
    print("STEP 12: Analysis-Design Iteration")
    print("=" * 60)

    SapModel.SetPresentUnits(UNITS_TON_M)

    if config is None:
        print("\n  No config provided — reading from ETABS model...")
        config = build_config_from_etabs(SapModel)

    # Build iteration config with defaults
    ic = config.get("iteration", {})
    iter_cfg = {
        "max_iterations": ic.get("max_iterations", MAX_ITERATIONS),
        "col_rebar_downsize": ic.get("col_rebar_downsize", COL_REBAR_DOWNSIZE),
        "col_rebar_max": ic.get("col_rebar_max", COL_REBAR_MAX),
        "col_resize_step": ic.get("col_resize_step", COL_RESIZE_STEP),
        "beam_rebar_min": ic.get("beam_rebar_min", BEAM_REBAR_MIN),
        "beam_rebar_max": ic.get("beam_rebar_max", BEAM_REBAR_MAX),
        "beam_resize_step": ic.get("beam_resize_step", BEAM_RESIZE_STEP),
        "beam_max_width_ratio": ic.get("beam_max_width_ratio", BEAM_MAX_WIDTH_RATIO),
        "design_code": ic.get("design_code", DESIGN_CODE),
        "skip_prefixes": ic.get("skip_prefixes", ITER_SKIP_PREFIXES),
    }

    # Classify floors
    super_stories, sub_stories, story_elevations, all_story_names = \
        classify_floors(config)
    print(f"  Superstructure floors: {super_stories}")
    print(f"  Substructure floors:   {sub_stories}")

    # Build strength lookup
    strength_lookup = build_strength_lookup(
        config.get("strength_map", {}), all_story_names)

    # Get frames and assign sway types
    frames_data = get_all_frames_data(SapModel)
    print(f"  Total frames in model: {frames_data['count']}")

    print("\n  Assigning sway types...")
    assign_sway_types(SapModel, frames_data, super_stories, sub_stories)

    # ── Phase 1: Superstructure Iteration (USS combos) ──
    print("\n" + "=" * 60)
    print("  PHASE 1: Superstructure Iteration")
    print("=" * 60)

    enabled, disabled = setup_combos(SapModel, SUPER_COMBOS, SUB_COMBOS)
    print(f"  Combos: {enabled} USS enabled, {disabled} BUSS disabled")

    super_col_sizes = _iterate_superstructure(
        SapModel, config, strength_lookup,
        super_stories, all_story_names, iter_cfg)

    # ── Phase 2: Substructure Check (BUSS combos) ──
    print("\n" + "=" * 60)
    print("  PHASE 2: Substructure Check")
    print("=" * 60)

    enabled, disabled = setup_combos(SapModel, SUB_COMBOS, SUPER_COMBOS)
    print(f"  Combos: {enabled} BUSS enabled, {disabled} USS disabled")

    _enforce_sub_column_sizes(
        SapModel, config, super_col_sizes,
        sub_stories, all_story_names, strength_lookup)

    # Final design run for substructure
    print("\n  Final substructure design run...")
    run_analysis_and_design(SapModel, iter_cfg["design_code"])

    SapModel.View.RefreshView(0, False)
    print("\nStep 12 complete.\n")


if __name__ == "__main__":
    import json
    from modeling.gs_01_init import connect_etabs
    SapModel = connect_etabs(None)

    config = None
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            config = json.load(f)

    run(SapModel, config)
