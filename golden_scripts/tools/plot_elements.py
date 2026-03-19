"""
Plot Elements Tool — Generate PNG visualization from element JSON files.

Renders beams, columns, walls, and small beams with their actual colors from
the legend, optionally overlaying grid lines from grid_data.json.

Usage:
    # With grid overlay (post-calibration)
    python -m golden_scripts.tools.plot_elements \
        --elements "SLIDES INFO/1F/calibrated/calibrated.json" \
        --grid-data grid_data.json \
        --output "SLIDES INFO/1F/calibrated/calibrated.png"

    # Without grid (raw PPT-meter extraction)
    python -m golden_scripts.tools.plot_elements \
        --elements "SLIDES INFO/1F/pptx_to_elements/1F.json" \
        --output "SLIDES INFO/1F/pptx_to_elements/1F.png"
"""
import json
import argparse
import re
import sys
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, Rectangle
    from matplotlib.collections import PatchCollection
except ImportError:
    print("ERROR: matplotlib is required. Install with: pip install matplotlib")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_color_map(legend: dict) -> dict:
    """Build reverse map from (element_type, section) -> '#RRGGBB'.

    legend format:
        {"FF0000": [{"element_type": "beam", "section": "B55X80", ...}], ...}
    Returns:
        {("beam", "B55X80"): "#FF0000", ...}
    """
    cmap = {}
    for hex_color, entries in legend.items():
        # Normalize to #RRGGBB
        color = f"#{hex_color.upper()}"
        if len(color) == 7:
            pass  # already #RRGGBB
        elif len(color) == 8:
            # might have extra char
            color = f"#{hex_color[-6:].upper()}"
        for entry in entries:
            et = entry.get("element_type", "")
            sec = entry.get("section", "")
            if et and sec:
                cmap[(et, sec)] = color
    return cmap


def _parse_frame_dims(section: str):
    """Parse frame section name -> (width_m, depth_m) or None.

    'C70X100' -> (0.70, 1.00)
    'B55X80'  -> (0.55, 0.80)
    'SB25X50' -> (0.25, 0.50)
    """
    m = re.match(r'^(?:B|SB|WB|FB|FSB|FWB|C)(\d+)X(\d+)(?:C\d+)?$', section)
    if m:
        return int(m.group(1)) / 100.0, int(m.group(2)) / 100.0
    return None


def _parse_wall_thickness(section: str):
    """Parse wall section name -> thickness_m or None.

    'W25' -> 0.25, 'W30C280' -> 0.30
    """
    m = re.match(r'^W(\d+)(?:C\d+)?$', section)
    if m:
        return int(m.group(1)) / 100.0
    return None


def _element_color(elem, color_map, default="#888888"):
    """Get color for an element from the color map."""
    et = elem.get("element_type", "")
    sec = elem.get("section", "")
    return color_map.get((et, sec), default)


# ---------------------------------------------------------------------------
# Grid rendering
# ---------------------------------------------------------------------------

def _draw_grid(ax, grid_data, margin=2.0):
    """Draw grid lines + labels + spacing annotations."""
    grids = grid_data.get("grids", grid_data)
    x_grids = grids.get("x", [])
    y_grids = grids.get("y", [])
    x_bubble = grids.get("x_bubble", "End")
    y_bubble = grids.get("y_bubble", "Start")

    x_coords = [g["coordinate"] for g in x_grids]
    y_coords = [g["coordinate"] for g in y_grids]
    x_labels = [g["label"] for g in x_grids]
    y_labels = [g["label"] for g in y_grids]

    if not x_coords and not y_coords:
        return None, None

    x_min = min(x_coords) if x_coords else 0
    x_max = max(x_coords) if x_coords else 0
    y_min = min(y_coords) if y_coords else 0
    y_max = max(y_coords) if y_coords else 0

    # Draw vertical grid lines (X direction)
    for coord, label in zip(x_coords, x_labels):
        ax.axvline(x=coord, color="#CCCCCC", linewidth=0.5, linestyle="--", zorder=0)
        # Label position depends on y_bubble (X grid labels are at Y extremes)
        if y_bubble == "Start":
            label_y = y_min - margin * 0.6
        else:
            label_y = y_max + margin * 0.6
        ax.text(coord, label_y, label, ha="center", va="center",
                fontsize=7, fontweight="bold", color="#666666",
                bbox=dict(boxstyle="circle,pad=0.2", fc="white", ec="#999999", lw=0.5))

    # Draw horizontal grid lines (Y direction)
    for coord, label in zip(y_coords, y_labels):
        ax.axhline(y=coord, color="#CCCCCC", linewidth=0.5, linestyle="--", zorder=0)
        if x_bubble == "End":
            label_x = x_max + margin * 0.6
        else:
            label_x = x_min - margin * 0.6
        ax.text(label_x, coord, label, ha="center", va="center",
                fontsize=7, fontweight="bold", color="#666666",
                bbox=dict(boxstyle="circle,pad=0.2", fc="white", ec="#999999", lw=0.5))

    # Spacing annotations between adjacent X grid lines
    sorted_x = sorted(zip(x_coords, x_labels))
    for i in range(len(sorted_x) - 1):
        c1, _ = sorted_x[i]
        c2, _ = sorted_x[i + 1]
        spacing = c2 - c1
        mid_x = (c1 + c2) / 2
        anno_y = y_max + margin * 0.25 if y_bubble != "Start" else y_min - margin * 0.25
        ax.text(mid_x, anno_y, f"{spacing:.2f}m", ha="center", va="center",
                fontsize=5, color="#999999")

    # Spacing annotations between adjacent Y grid lines
    sorted_y = sorted(zip(y_coords, y_labels))
    for i in range(len(sorted_y) - 1):
        c1, _ = sorted_y[i]
        c2, _ = sorted_y[i + 1]
        spacing = c2 - c1
        mid_y = (c1 + c2) / 2
        anno_x = x_min - margin * 0.25 if x_bubble != "End" else x_max + margin * 0.25
        ax.text(anno_x, mid_y, f"{spacing:.2f}m", ha="center", va="center",
                fontsize=5, color="#999999", rotation=90)

    return (x_min, x_max, y_min, y_max), (x_coords, y_coords)


# ---------------------------------------------------------------------------
# Element rendering
# ---------------------------------------------------------------------------

def _draw_beams(ax, beams, color_map, show_labels=True):
    """Draw beams as colored line segments."""
    for b in beams:
        x1, y1 = b["x1"], b["y1"]
        x2, y2 = b["x2"], b["y2"]
        color = _element_color(b, color_map, default="#C00000")
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=2.0, solid_capstyle="round", zorder=2)
        if show_labels:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my, b.get("section", ""), fontsize=3, ha="center", va="bottom",
                    color=color, zorder=5)


def _draw_small_beams(ax, small_beams, color_map, show_labels=True):
    """Draw small beams as thinner colored line segments."""
    for sb in small_beams:
        x1, y1 = sb["x1"], sb["y1"]
        x2, y2 = sb["x2"], sb["y2"]
        color = _element_color(sb, color_map, default="#0066CC")
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=1.0, solid_capstyle="round", zorder=2)
        if show_labels:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my, sb.get("section", ""), fontsize=2.5, ha="center", va="bottom",
                    color=color, zorder=5)


def _draw_columns(ax, columns, color_map, show_labels=True):
    """Draw columns as filled rectangles at actual section size."""
    for c in columns:
        cx, cy = c["x1"], c["y1"]
        section = c.get("section", "")
        color = _element_color(c, color_map, default="#2F5597")
        dims = _parse_frame_dims(section)
        if dims:
            w, d = dims
            rect = Rectangle((cx - w / 2, cy - d / 2), w, d,
                              facecolor=color, edgecolor="black",
                              linewidth=0.3, zorder=3, alpha=0.85)
            ax.add_patch(rect)
        else:
            # Fallback: draw as point
            ax.plot(cx, cy, "s", color=color, markersize=4, zorder=3)
        if show_labels:
            ax.text(cx, cy, section, fontsize=2.5, ha="center", va="center",
                    color="white", fontweight="bold", zorder=5)


def _draw_walls(ax, walls, color_map, show_labels=True):
    """Draw walls as thick colored rectangles along their segment."""
    import math
    for w in walls:
        x1, y1 = w["x1"], w["y1"]
        x2, y2 = w["x2"], w["y2"]
        section = w.get("section", "")
        color = _element_color(w, color_map, default="#00B050")
        thickness = _parse_wall_thickness(section)
        if thickness and thickness > 0:
            dx = x2 - x1
            dy = y2 - y1
            length = math.sqrt(dx * dx + dy * dy)
            if length < 1e-6:
                continue
            # Normal direction
            nx = -dy / length * thickness / 2
            ny = dx / length * thickness / 2
            # Four corners of the wall rectangle
            xs = [x1 + nx, x2 + nx, x2 - nx, x1 - nx]
            ys = [y1 + ny, y2 + ny, y2 - ny, y1 - ny]
            ax.fill(xs, ys, facecolor=color, edgecolor="black",
                    linewidth=0.3, zorder=2, alpha=0.6)
        else:
            # Fallback: draw as line
            ax.plot([x1, x2], [y1, y2], color=color, linewidth=3, zorder=2, alpha=0.6)
        if show_labels:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my, section, fontsize=2.5, ha="center", va="center",
                    color="black", zorder=5)


# ---------------------------------------------------------------------------
# Legend panel
# ---------------------------------------------------------------------------

def _draw_legend(ax, legend, stats, color_map):
    """Auto-generated legend from metadata."""
    handles = []
    seen = set()
    for hex_color, entries in legend.items():
        color = f"#{hex_color.upper()}"
        if len(color) != 7:
            color = f"#{hex_color[-6:].upper()}"
        for entry in entries:
            et = entry.get("element_type", "")
            sec = entry.get("section", "")
            label_text = entry.get("label", sec)
            key = (et, sec)
            if key in seen:
                continue
            seen.add(key)
            if et in ("beam", "small_beam"):
                h = plt.Line2D([0], [0], color=color,
                               linewidth=2 if et == "beam" else 1,
                               label=f"{label_text} ({et})")
            elif et == "column":
                h = mpatches.Patch(facecolor=color, edgecolor="black",
                                   linewidth=0.5, label=f"{label_text} (column)")
            elif et == "wall":
                h = mpatches.Patch(facecolor=color, edgecolor="black",
                                   linewidth=0.5, alpha=0.6, label=f"{label_text} (wall)")
            else:
                h = mpatches.Patch(facecolor=color, label=f"{label_text} ({et})")
            handles.append(h)

    # Add stats text
    if stats:
        stats_text = "  ".join(f"{k}={v}" for k, v in stats.items() if v > 0)
        handles.append(mpatches.Patch(facecolor="none", edgecolor="none",
                                       label=f"Counts: {stats_text}"))

    if handles:
        ax.legend(handles=handles, loc="upper left", fontsize=5,
                  framealpha=0.9, ncol=min(len(handles), 4),
                  bbox_to_anchor=(0.0, 1.0))


# ---------------------------------------------------------------------------
# Main plot function
# ---------------------------------------------------------------------------

def plot_elements(elements_path, output, grid_data_path=None,
                  dpi=300, show_labels=True, title=None):
    """Generate a PNG plot from an element JSON file.

    Args:
        elements_path: Path to element JSON file.
        output: Output PNG path.
        grid_data_path: Optional path to grid_data.json.
        dpi: Output DPI (default 300).
        show_labels: Whether to show section labels on elements.
        title: Plot title (defaults to floor_label from metadata).
    """
    elements_path = Path(elements_path)
    output = Path(output)

    with open(elements_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("_metadata", {})
    legend = meta.get("legend", {})
    stats = meta.get("stats", {})
    floor_label = meta.get("floor_label", elements_path.stem)

    if title is None:
        title = floor_label

    color_map = _build_color_map(legend)

    # Load grid data if provided
    grid_data = None
    if grid_data_path:
        grid_data_path = Path(grid_data_path)
        if grid_data_path.exists():
            with open(grid_data_path, "r", encoding="utf-8") as f:
                grid_data = json.load(f)

    # Collect all coordinates for extent calculation
    all_x, all_y = [], []
    for cat in ("columns", "beams", "walls", "small_beams"):
        for elem in data.get(cat, []):
            all_x.extend([elem.get("x1", 0), elem.get("x2", 0)])
            all_y.extend([elem.get("y1", 0), elem.get("y2", 0)])

    if not all_x or not all_y:
        print(f"  WARNING: No elements to plot in {elements_path}")
        return str(output)

    # Figure setup
    margin = 3.0
    grid_extent = None
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))

    # Draw grid first (background)
    if grid_data:
        grid_extent, _ = _draw_grid(ax, grid_data, margin=margin)

    # Calculate extent
    if grid_extent:
        x_min, x_max, y_min, y_max = grid_extent
        # Expand to include elements outside grid
        x_min = min(x_min, min(all_x))
        x_max = max(x_max, max(all_x))
        y_min = min(y_min, min(all_y))
        y_max = max(y_max, max(all_y))
    else:
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)

    # Draw elements (order: walls bottom, beams, small beams, columns on top)
    _draw_walls(ax, data.get("walls", []), color_map, show_labels)
    _draw_beams(ax, data.get("beams", []), color_map, show_labels)
    _draw_small_beams(ax, data.get("small_beams", []), color_map, show_labels)
    _draw_columns(ax, data.get("columns", []), color_map, show_labels)

    # Legend
    _draw_legend(ax, legend, stats, color_map)

    # Axis setup
    ax.set_xlim(x_min - margin, x_max + margin)
    ax.set_ylim(y_min - margin, y_max + margin)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.set_xlabel("X (m)", fontsize=7)
    ax.set_ylabel("Y (m)", fontsize=7)
    ax.tick_params(labelsize=6)

    # Save
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output), dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved plot: {output}")
    return str(output)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate PNG visualization from element JSON files."
    )
    parser.add_argument(
        "--elements", required=True,
        help="Path to element JSON file",
    )
    parser.add_argument(
        "--grid-data",
        help="Path to grid_data.json (optional — draws grid lines + labels)",
    )
    parser.add_argument(
        "--output", required=True,
        help="Output PNG file path",
    )
    parser.add_argument(
        "--dpi", type=int, default=300,
        help="Output DPI (default: 300)",
    )
    parser.add_argument(
        "--no-labels", action="store_true",
        help="Suppress section labels on elements",
    )
    parser.add_argument(
        "--title",
        help="Plot title (defaults to floor_label from metadata)",
    )
    args = parser.parse_args()

    plot_elements(
        elements_path=args.elements,
        output=args.output,
        grid_data_path=args.grid_data,
        dpi=args.dpi,
        show_labels=not args.no_labels,
        title=args.title,
    )


if __name__ == "__main__":
    main()
