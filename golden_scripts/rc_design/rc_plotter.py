"""
RC Iteration Plotter — plan and elevation ratio visualizations.

Generates matplotlib figures showing rebar ratio status for columns and beams
at key floors (plan view) and along worst-ratio grid lines (elevation view).
"""
import os
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# ======================================================================
# Color encoding
# ======================================================================

def _ratio_color(ratio, down_thresh, up_thresh):
    """Map ratio to traffic-light color.

    Red: ratio too low (<= down_thresh) or too high (> up_thresh).
    Yellow: approaching thresholds.
    Green: OK.
    """
    if ratio <= down_thresh or ratio > up_thresh:
        return "#FF4444"   # red — out of range
    elif ratio <= down_thresh * 1.5 or ratio > up_thresh * 0.85:
        return "#FFAA00"   # yellow — approaching threshold
    else:
        return "#44AA44"   # green — OK


# ======================================================================
# Key floor selection
# ======================================================================

def select_key_floors(col_results, beam_results, super_stories, sub_stories,
                      strength_lookup, all_story_names):
    """Select key floors for plan view plots.

    Rules:
    - Substructure: all floors
    - Superstructure fixed: 2F (always), 1MF (if exists)
    - Strength transition: floors where fc changes (both sides of boundary)
    - Worst ratio: floor with worst column ratio + floor with worst beam ratio

    Returns: sorted list of story names (in all_story_names order).
    """
    story_idx = {s: i for i, s in enumerate(all_story_names)}
    key_set = set()

    # All substructure floors
    key_set.update(sub_stories)

    # Fixed superstructure floors
    if "2F" in story_idx:
        key_set.add("2F")
    if "1MF" in story_idx:
        key_set.add("1MF")

    # Strength transition floors
    for i in range(len(all_story_names) - 1):
        s_below = all_story_names[i]
        s_above = all_story_names[i + 1]
        fc_below = strength_lookup.get((s_below, "column"))
        fc_above = strength_lookup.get((s_above, "column"))
        if fc_below is not None and fc_above is not None and fc_below != fc_above:
            key_set.add(s_below)
            key_set.add(s_above)

    # Worst ratio floors (superstructure only)
    super_set = set(super_stories)
    if col_results:
        worst_col = max((c for c in col_results if c["story"] in super_set),
                        key=lambda c: c["ratio"], default=None)
        if worst_col:
            key_set.add(worst_col["story"])
    if beam_results:
        worst_beam = max((b for b in beam_results if b["story"] in super_set),
                         key=lambda b: b["ratio"], default=None)
        if worst_beam:
            key_set.add(worst_beam["story"])

    # Filter to valid stories and sort by story order
    valid = key_set & set(all_story_names)
    return sorted(valid, key=lambda s: story_idx.get(s, 999))


# ======================================================================
# Top-N grid selection
# ======================================================================

def select_top_grids(col_results, beam_results, grid_lines, top_n=3):
    """Select worst-ratio grid lines per direction.

    For each grid line, compute the max ratio of all columns/beams on that grid.
    Return top_n per direction.

    Args:
        col_results: list of column result dicts (with x, y, ratio).
        beam_results: list of beam result dicts (with ratio, story).
        grid_lines: {"x": [{"label": str, "coordinate": float}, ...],
                     "y": [{"label": str, "coordinate": float}, ...]}
        top_n: number of grids per direction.

    Returns: {"x": [{"label", "coordinate", "worst_ratio"}, ...],
              "y": [...]}
    """
    tolerance = 0.5  # m — snap tolerance for matching frame to grid

    result = {}
    for direction in ("x", "y"):
        grids = grid_lines.get(direction, [])
        grid_scores = []
        for g in grids:
            coord = g["coordinate"]
            worst = 0.0
            for col in col_results:
                col_coord = col["x"] if direction == "x" else col["y"]
                if abs(col_coord - coord) < tolerance:
                    worst = max(worst, col["ratio"])
            grid_scores.append({
                "label": g["label"],
                "coordinate": coord,
                "worst_ratio": worst,
            })
        grid_scores.sort(key=lambda g: g["worst_ratio"], reverse=True)
        result[direction] = grid_scores[:top_n]

    return result


# ======================================================================
# Plan view plot
# ======================================================================

def plot_plan_ratios(col_results, beam_results, frames_data,
                     story_name, grid_lines, output_path,
                     col_thresholds=None, beam_thresholds=None, dpi=150):
    """Generate a plan view ratio plot for one story.

    Args:
        col_results: column results for this story.
        beam_results: beam results for this story.
        frames_data: all frames data dict from ETABS.
        story_name: story to plot.
        grid_lines: {"x": [...], "y": [...]}.
        output_path: path for output PNG.
        col_thresholds: (down, up) for columns. Default (0.01, 0.04).
        beam_thresholds: (down, up) for beams. Default (0.01, 0.02).
        dpi: output DPI.
    """
    if col_thresholds is None:
        col_thresholds = (0.01, 0.04)
    if beam_thresholds is None:
        beam_thresholds = (0.01, 0.02)

    story_cols = [c for c in col_results if c["story"] == story_name]
    story_beams = [b for b in beam_results if b["story"] == story_name]

    # Build beam coordinate lookup from frames_data
    beam_coords = {}
    if frames_data and frames_data["count"] > 0:
        for i in range(frames_data["count"]):
            if frames_data["stories"][i] == story_name:
                beam_coords[frames_data["names"][i]] = {
                    "x1": frames_data["pt1x"][i], "y1": frames_data["pt1y"][i],
                    "x2": frames_data["pt2x"][i], "y2": frames_data["pt2y"][i],
                }

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))

    # Draw grid lines
    x_grids = grid_lines.get("x", [])
    y_grids = grid_lines.get("y", [])
    all_x = [g["coordinate"] for g in x_grids]
    all_y = [g["coordinate"] for g in y_grids]

    x_min = min(all_x) - 2 if all_x else 0
    x_max = max(all_x) + 2 if all_x else 10
    y_min = min(all_y) - 2 if all_y else 0
    y_max = max(all_y) + 2 if all_y else 10

    for g in x_grids:
        ax.axvline(g["coordinate"], color="#CCCCCC", linewidth=0.5, zorder=0)
        ax.text(g["coordinate"], y_max + 0.5, g["label"],
                ha="center", va="bottom", fontsize=7, color="#888888")
    for g in y_grids:
        ax.axhline(g["coordinate"], color="#CCCCCC", linewidth=0.5, zorder=0)
        ax.text(x_min - 0.5, g["coordinate"], g["label"],
                ha="right", va="center", fontsize=7, color="#888888")

    # Draw beams — 6-position rebar percentage labels
    for b in story_beams:
        coords = beam_coords.get(b["frame"])
        if not coords:
            continue
        color = _ratio_color(b["ratio"], beam_thresholds[0], beam_thresholds[1])
        ax.plot([coords["x1"], coords["x2"]], [coords["y1"], coords["y2"]],
                color=color, linewidth=2, zorder=1)
        # Label at 3 positions (25%, 50%, 75% along beam)
        x1, y1 = coords["x1"], coords["y1"]
        x2, y2 = coords["x2"], coords["y2"]
        for frac, pos in [(0.25, "left"), (0.50, "center"), (0.75, "right")]:
            px = x1 + (x2 - x1) * frac
            py = y1 + (y2 - y1) * frac
            tp = b.get(f"pct_top_{pos}", 0)
            bp = b.get(f"pct_bot_{pos}", 0)
            ax.text(px, py + 0.15, f"{tp:.1f}", fontsize=4, ha="center",
                    va="bottom", color=color, zorder=3)
            ax.text(px, py - 0.15, f"{bp:.1f}", fontsize=4, ha="center",
                    va="top", color=color, alpha=0.7, zorder=3)

    # Draw columns — rebar percentage
    for c in story_cols:
        color = _ratio_color(c["ratio"], col_thresholds[0], col_thresholds[1])
        ax.plot(c["x"], c["y"], "s", color=color, markersize=8, zorder=2)
        pct = c.get("pct", c["ratio"] * 100)
        ax.text(c["x"], c["y"] + 0.3, f"{pct:.1f}%", fontsize=6,
                ha="center", va="bottom", color=color, fontweight="bold", zorder=3)

    ax.set_xlim(x_min, x_max + 1)
    ax.set_ylim(y_min, y_max + 1)
    ax.set_aspect("equal")
    ax.set_title(f"Plan View — {story_name} (Rebar %)", fontsize=12)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")

    # Legend
    patches = [
        mpatches.Patch(color="#44AA44", label="OK"),
        mpatches.Patch(color="#FFAA00", label="Near threshold"),
        mpatches.Patch(color="#FF4444", label="Out of range"),
    ]
    ax.legend(handles=patches, loc="upper right", fontsize=8)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


# ======================================================================
# Elevation view plot
# ======================================================================

def plot_elevation_ratios(col_results, beam_results, frames_data,
                          grid_label, grid_coord, grid_direction,
                          story_elevations, target_stories,
                          output_path, col_thresholds=None,
                          beam_thresholds=None, dpi=150):
    """Generate an elevation view ratio plot for one grid line.

    Args:
        col_results: all column results.
        beam_results: all beam results.
        frames_data: all frames data dict.
        grid_label: grid line label (e.g. "3" or "B").
        grid_coord: grid line coordinate (m).
        grid_direction: "x" or "y".
        story_elevations: {story_name: elevation_m}.
        target_stories: list of story names to include.
        output_path: output PNG path.
        col_thresholds: (down, up) for columns.
        beam_thresholds: (down, up) for beams.
        dpi: output DPI.
    """
    if col_thresholds is None:
        col_thresholds = (0.01, 0.04)
    if beam_thresholds is None:
        beam_thresholds = (0.01, 0.02)

    tolerance = 0.5
    target_set = set(target_stories)

    # Filter columns on this grid line
    grid_cols = []
    for c in col_results:
        if c["story"] not in target_set:
            continue
        coord = c["x"] if grid_direction == "x" else c["y"]
        if abs(coord - grid_coord) < tolerance:
            grid_cols.append(c)

    # Build frame coordinate lookup
    frame_coords = {}
    if frames_data and frames_data["count"] > 0:
        for i in range(frames_data["count"]):
            frame_coords[frames_data["names"][i]] = {
                "x1": frames_data["pt1x"][i], "y1": frames_data["pt1y"][i],
                "z1": frames_data["pt1z"][i],
                "x2": frames_data["pt2x"][i], "y2": frames_data["pt2y"][i],
                "z2": frames_data["pt2z"][i],
            }

    # Filter beams on this grid
    grid_beams = []
    for b in beam_results:
        if b["story"] not in target_set:
            continue
        coords = frame_coords.get(b["frame"])
        if not coords:
            continue
        if grid_direction == "x":
            if abs(coords["y1"] - grid_coord) < tolerance or \
               abs(coords["y2"] - grid_coord) < tolerance:
                grid_beams.append({**b, **coords})
        else:
            if abs(coords["x1"] - grid_coord) < tolerance or \
               abs(coords["x2"] - grid_coord) < tolerance:
                grid_beams.append({**b, **coords})

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))

    # Horizontal axis = position along the grid line
    # Vertical axis = elevation

    # Story lines
    sorted_stories = sorted(target_set, key=lambda s: story_elevations.get(s, 0))
    for s in sorted_stories:
        elev = story_elevations.get(s, 0)
        ax.axhline(elev, color="#DDDDDD", linewidth=0.5, linestyle="--", zorder=0)
        ax.text(-0.5, elev, s, ha="right", va="center", fontsize=7, color="#888888")

    # Draw columns (vertical lines) — rebar percentage
    for c in grid_cols:
        elev = story_elevations.get(c["story"], 0)
        pos = c["y"] if grid_direction == "x" else c["x"]
        color = _ratio_color(c["ratio"], col_thresholds[0], col_thresholds[1])
        # Column spans from this story to next story above
        above_elevs = [story_elevations[s] for s in sorted_stories
                       if story_elevations[s] > elev]
        top = min(above_elevs) if above_elevs else elev + 3
        ax.plot([pos, pos], [elev, top], color=color, linewidth=3, zorder=1)
        pct = c.get("pct", c["ratio"] * 100)
        ax.text(pos + 0.15, (elev + top) / 2, f"{pct:.1f}%",
                fontsize=5, va="center", color=color, zorder=3)

    # Draw beams (horizontal lines at story elevation) — 6-position rebar %
    for b in grid_beams:
        elev = story_elevations.get(b["story"], 0)
        if grid_direction == "x":
            p1 = b["y1"]
            p2 = b["y2"]
        else:
            p1 = b["x1"]
            p2 = b["x2"]
        color = _ratio_color(b["ratio"], beam_thresholds[0], beam_thresholds[1])
        ax.plot([p1, p2], [elev, elev], color=color, linewidth=2, zorder=1)
        # Label at 3 positions along beam
        for frac, pos in [(0.25, "left"), (0.50, "center"), (0.75, "right")]:
            px = p1 + (p2 - p1) * frac
            tp = b.get(f"pct_top_{pos}", 0)
            bp = b.get(f"pct_bot_{pos}", 0)
            ax.text(px, elev + 0.15, f"{tp:.1f}", fontsize=4, ha="center",
                    va="bottom", color=color, zorder=3)
            ax.text(px, elev - 0.15, f"{bp:.1f}", fontsize=4, ha="center",
                    va="top", color=color, alpha=0.7, zorder=3)

    dir_label = "Y" if grid_direction == "x" else "X"
    ax.set_title(f"Elevation — Grid {grid_label} (direction={grid_direction.upper()}, "
                 f"coord={grid_coord:.2f}m)", fontsize=12)
    ax.set_xlabel(f"{dir_label} position (m)")
    ax.set_ylabel("Elevation (m)")

    patches = [
        mpatches.Patch(color="#44AA44", label="OK"),
        mpatches.Patch(color="#FFAA00", label="Near threshold"),
        mpatches.Patch(color="#FF4444", label="Out of range"),
    ]
    ax.legend(handles=patches, loc="upper right", fontsize=8)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


# ======================================================================
# Integration helper — generate all plots for one iteration
# ======================================================================

def generate_iteration_plots(col_results, beam_results, frames_data,
                             grid_lines, strength_lookup,
                             super_stories, sub_stories, all_story_names,
                             story_elevations, iter_dir,
                             col_thresholds=None, beam_thresholds=None,
                             top_n=3, dpi=150):
    """Generate plan + elevation plots for one iteration.

    Args:
        iter_dir: base directory for this iteration (e.g. rc_iterations/iteration_1).

    Returns: dict with key_floors and top_grids for the ratio_report.
    """
    key_floors = select_key_floors(
        col_results, beam_results, super_stories, sub_stories,
        strength_lookup, all_story_names)

    top_grids = select_top_grids(col_results, beam_results, grid_lines, top_n)

    # Plan views
    plans_dir = os.path.join(iter_dir, "plans")
    os.makedirs(plans_dir, exist_ok=True)
    for floor in key_floors:
        out = os.path.join(plans_dir, f"plan_{floor}.png")
        plot_plan_ratios(col_results, beam_results, frames_data,
                         floor, grid_lines, out,
                         col_thresholds=col_thresholds,
                         beam_thresholds=beam_thresholds, dpi=dpi)

    # Elevation views
    elev_dir = os.path.join(iter_dir, "elevations")
    os.makedirs(elev_dir, exist_ok=True)
    for direction in ("x", "y"):
        for grid in top_grids[direction]:
            out = os.path.join(elev_dir,
                               f"elev_{direction.upper()}_{grid['label']}.png")
            plot_elevation_ratios(
                col_results, beam_results, frames_data,
                grid["label"], grid["coordinate"], direction,
                story_elevations, all_story_names, out,
                col_thresholds=col_thresholds,
                beam_thresholds=beam_thresholds, dpi=dpi)

    return {
        "key_floors": key_floors,
        "top_elevations": {
            "x": [g["label"] for g in top_grids["x"]],
            "y": [g["label"] for g in top_grids["y"]],
        },
    }
