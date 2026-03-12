"""
PPT-to-Elements Script
======================
Converts PowerPoint (.pptx) structural plan drawings into structural element
JSON (columns, beams, walls, small beams) with precise coordinates.

PPT format: FREEFORM shapes on top of PNG base images, with color-coded legend.
This bypasses the Bluebeam PDF annotation pipeline entirely.

Usage:
    # Phase 1: major beams + columns + walls
    python -m golden_scripts.tools.pptx_to_elements \
        --input plan.pptx --output elements.json \
        --page-floors "1=B3F, 3=1F~2F, 4=3F~14F" \
        --phase phase1

    # Phase 2: small beams only
    python -m golden_scripts.tools.pptx_to_elements \
        --input plan.pptx --output sb_elements.json \
        --page-floors "3=1F~2F, 4=3F~14F" \
        --phase phase2

    # List slides and their shape counts
    python -m golden_scripts.tools.pptx_to_elements --input plan.pptx --list-slides

    # Extract + crop PNGs
    python -m golden_scripts.tools.pptx_to_elements \
        --input plan.pptx --output elements.json \
        --page-floors "1=B3F" --phase phase1 \
        --crop --crop-dir "./結構配置圖/"

    # Preview without writing
    python -m golden_scripts.tools.pptx_to_elements ... --dry-run
"""

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Emu

# Import shared functions from annot_to_elements
from golden_scripts.tools.annot_to_elements import (
    LegendEntry,
    expand_floor_range,
    parse_page_floors,
    parse_legend_label,
    _direction_of,
    _round5,
    _wall_centerline,
    _elem_key,
    group_and_dedup,
    collect_sections,
    COORD_PRECISION,
    DIRECTION_RATIO,
)


# ─── Constants ────────────────────────────────────────────────────────────────

TICK_MAX_LENGTH_EMU = 300000       # Max length for a tick mark (short line)
TICK_Y_TOLERANCE_EMU = 100000     # Y-proximity for grouping tick marks
TEXT_TICK_Y_TOLERANCE_EMU = 300000 # Y-proximity for matching text to ticks
COLUMN_DEDUP_TOLERANCE_EMU = 5000 # Position tolerance for column dedup
LEGEND_KEYWORDS = [
    "RC", "大梁", "小梁", "柱", "壁", "連續壁", "剪力牆",
    "梁", "版", "板", "基礎", "FB", "WB", "SB",
]
SLIDE_AREA_RATIO_MAX = 0.50       # Exclude shapes > 50% of slide area
MIN_SCALE_MEASUREMENTS = 1        # Require at least 1 measurement per page
MIN_COLUMN_DIM_EMU = 30000        # Min column shape dimension (~3cm at typical scale)
MEASUREMENT_RE = re.compile(r"(\d+\.?\d*)\s*m\b")
# Column section pattern: C100x100, C110x140, etc.
_COLUMN_SECTION_RE = re.compile(r"C(\d+)\s*[xX]\s*(\d+)")


# ─── Scale Detection ─────────────────────────────────────────────────────────

def _get_shape_color(shape, color_type="line"):
    """Extract RGB hex string from a shape's line or fill color."""
    try:
        if color_type == "line":
            ln = shape.line
            if ln and ln.color and ln.color.type is not None and ln.color.rgb:
                return str(ln.color.rgb)
        elif color_type == "fill":
            fill = shape.fill
            if fill.type is not None:
                fc = fill.fore_color
                if fc and fc.type is not None and fc.rgb:
                    return str(fc.rgb)
    except Exception:
        pass
    return None


def _find_tick_marks(slide):
    """Find short line segments (tick marks) on a slide.

    Returns list of (orientation, x, y, length, color) where:
      orientation: 'V' (vertical, width=0) or 'H' (horizontal, height=0)
      x, y: left/top position in EMU
      length: in EMU
    """
    ticks = []
    for shape in slide.shapes:
        if shape.shape_type != MSO_SHAPE_TYPE.FREEFORM:
            continue
        w, h = shape.width, shape.height
        if w == 0 and 0 < h <= TICK_MAX_LENGTH_EMU:
            color = _get_shape_color(shape, "line")
            ticks.append(("V", shape.left, shape.top, h, color))
        elif h == 0 and 0 < w <= TICK_MAX_LENGTH_EMU:
            color = _get_shape_color(shape, "line")
            ticks.append(("H", shape.left, shape.top, w, color))
    return ticks


def _find_measurement_texts(slide):
    """Find TEXT_BOX shapes containing measurement values like '8.5 m'.

    Returns list of (meters_value, center_x, center_y, text).
    """
    measurements = []
    for shape in slide.shapes:
        if shape.shape_type != MSO_SHAPE_TYPE.TEXT_BOX:
            continue
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text.strip()
        # Only match simple single-value measurement texts
        # Skip multi-line texts like "27.4 m\n9.0 m\t8.6 m\t9.8 m"
        lines = text.split("\n")
        for line in lines:
            # Skip lines with tabs (multi-value)
            if "\t" in line:
                continue
            m = MEASUREMENT_RE.match(line.strip())
            if m:
                val = float(m.group(1))
                if val < 1.0 or val > 100.0:
                    continue  # Skip unreasonable values
                cx = shape.left + shape.width // 2
                cy = shape.top + shape.height // 2
                measurements.append((val, cx, cy, line.strip()))
    return measurements


def detect_slide_scale(slide, slide_num):
    """Detect the EMU-per-meter scale for a slide.

    Strategy:
    1. Find measurement texts (e.g., "8.5 m", "11.0 m")
    2. Find vertical tick marks (short vertical lines near measurements)
    3. Group V-ticks by similar Y into dimension lines
    4. For each measurement text, find the best matching V-tick pair
    5. Return the average scale (EMU per meter)

    Returns (emu_per_meter, details_dict) or (None, error_msg).
    """
    measurements = _find_measurement_texts(slide)
    if not measurements:
        return None, f"Slide {slide_num}: no measurement texts found (need 'X.X m' TEXT_BOX)"

    ticks = _find_tick_marks(slide)
    v_ticks = [(x, y, length) for orient, x, y, length, _ in ticks if orient == "V"]

    if len(v_ticks) < 2:
        return None, f"Slide {slide_num}: fewer than 2 vertical tick marks found"

    # Sort V-ticks by X position
    v_ticks.sort(key=lambda t: t[0])

    # Try to match each measurement text to a pair of V-ticks
    scales = []
    details = []

    for meters, text_cx, text_cy, text_str in measurements:
        best_pair = None
        best_score = float("inf")

        for i in range(len(v_ticks)):
            for j in range(i + 1, len(v_ticks)):
                x_i, y_i, _ = v_ticks[i]
                x_j, y_j, _ = v_ticks[j]

                # V-ticks should be at similar Y
                if abs(y_i - y_j) > TICK_Y_TOLERANCE_EMU:
                    continue

                # Text should be between the ticks (X-wise) or close
                tick_cx = (x_i + x_j) / 2
                tick_cy = (y_i + y_j) / 2

                # Text should be near the tick Y
                if abs(text_cy - tick_cy) > TEXT_TICK_Y_TOLERANCE_EMU:
                    continue

                # Text center should be between ticks (with margin)
                margin = (x_j - x_i) * 0.3
                if text_cx < x_i - margin or text_cx > x_j + margin:
                    continue

                # Score: prefer pair where text is centered between ticks
                dx = abs(text_cx - tick_cx)
                dy = abs(text_cy - tick_cy)
                score = dx + dy

                if score < best_score:
                    best_score = score
                    best_pair = (x_i, x_j, meters)

        if best_pair:
            x_left, x_right, m = best_pair
            emu_dist = x_right - x_left
            scale = emu_dist / m
            scales.append(scale)
            details.append({
                "text": text_str,
                "meters": m,
                "emu_distance": emu_dist,
                "emu_per_meter": round(scale, 1),
            })

    if not scales:
        return None, f"Slide {slide_num}: could not pair any measurement text with tick marks"

    # Use median scale for robustness
    scales.sort()
    median_scale = scales[len(scales) // 2]

    return median_scale, {
        "slide": slide_num,
        "measurements": details,
        "emu_per_meter": round(median_scale, 1),
        "num_measurements": len(scales),
    }


# ─── Coordinate Conversion ───────────────────────────────────────────────────

def _emu_to_m(x_emu, y_emu, scale, slide_h):
    """Convert EMU coordinates to meters.

    PPT origin is top-left, Y increases downward.
    Structural origin is bottom-left, Y increases upward.
    """
    x_m = round(x_emu / scale, COORD_PRECISION)
    y_m = round((slide_h - y_emu) / scale, COORD_PRECISION)
    return x_m, y_m


# ─── PNG Extraction ──────────────────────────────────────────────────────────

def extract_base_png(slide, slide_num, floor_label, crop_dir):
    """Extract PNG images from GROUP shapes on the slide.

    Saves as {floor_label}_full.png in crop_dir.
    Returns list of saved file paths.
    """
    saved = []
    crop_path = Path(crop_dir)
    crop_path.mkdir(parents=True, exist_ok=True)

    for shape in slide.shapes:
        if shape.shape_type != MSO_SHAPE_TYPE.GROUP:
            continue
        for idx, child in enumerate(shape.shapes):
            if child.shape_type == MSO_SHAPE_TYPE.PICTURE:
                img = child.image
                ext = {
                    "image/png": ".png",
                    "image/jpeg": ".jpg",
                    "image/gif": ".gif",
                }.get(img.content_type, ".png")

                fname = f"{floor_label}_full{ext}" if idx == 0 else f"{floor_label}_full_{idx}{ext}"
                fpath = crop_path / fname
                with open(fpath, "wb") as f:
                    f.write(img.blob)
                saved.append(str(fpath))
                print(f"  Saved: {fpath} ({len(img.blob)} bytes)")
    return saved


# ─── Legend Parsing ──────────────────────────────────────────────────────────

def _detect_legend_region(slide, slide_w, slide_h):
    """Detect whether the legend is on the left or right side of the slide.

    Strategy: Count structural keywords in TEXT_BOX shapes on each side.
    The side with more keywords is the legend side.

    Returns ("left", x_boundary) or ("right", x_boundary).
    """
    mid_x = slide_w // 2
    left_score = 0
    right_score = 0

    for shape in slide.shapes:
        if shape.shape_type != MSO_SHAPE_TYPE.TEXT_BOX:
            continue
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text
        cx = shape.left + shape.width // 2

        score = sum(1 for kw in LEGEND_KEYWORDS if kw in text)
        if score > 0:
            if cx < mid_x * 0.6:  # Clearly on left side
                left_score += score
            elif cx > mid_x * 1.4:  # Clearly on right side
                right_score += score

    # Default to left if can't determine
    if left_score >= right_score:
        # Legend on left: find the rightmost legend text to set boundary
        max_right = 0
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.TEXT_BOX and shape.has_text_frame:
                text = shape.text_frame.text
                if any(kw in text for kw in LEGEND_KEYWORDS):
                    r = shape.left + shape.width
                    if r > max_right and shape.left < mid_x:
                        max_right = r
        boundary = max_right + 200000 if max_right > 0 else int(slide_w * 0.25)
        return "left", boundary
    else:
        min_left = slide_w
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.TEXT_BOX and shape.has_text_frame:
                text = shape.text_frame.text
                if any(kw in text for kw in LEGEND_KEYWORDS):
                    if shape.left > mid_x:
                        min_left = min(min_left, shape.left)
        boundary = min_left - 200000 if min_left < slide_w else int(slide_w * 0.75)
        return "right", boundary


def parse_legend(slide, slide_w, slide_h):
    """Parse the legend area to build color → LegendEntry mapping.

    Strategy:
    1. Detect legend region (left or right)
    2. In the legend region, find colored FREEFORM shapes (color swatches)
    3. For each swatch, find the nearest TEXT_BOX to its right
    4. Parse the text as a legend label

    Returns dict[color_hex, list[LegendEntry]].
    """
    side, boundary = _detect_legend_region(slide, slide_w, slide_h)

    # Collect legend TEXT_BOX shapes
    legend_texts = []
    for shape in slide.shapes:
        if shape.shape_type != MSO_SHAPE_TYPE.TEXT_BOX:
            continue
        if not shape.has_text_frame:
            continue
        cx = shape.left + shape.width // 2
        if side == "left" and cx > boundary:
            continue
        if side == "right" and cx < boundary:
            continue
        text = shape.text_frame.text.strip()
        if text:
            legend_texts.append({
                "text": text,
                "left": shape.left,
                "top": shape.top,
                "right": shape.left + shape.width,
                "bottom": shape.top + shape.height,
                "cx": cx,
                "cy": shape.top + shape.height // 2,
            })

    if not legend_texts:
        return {}

    # Parse all legend text blocks into individual label lines
    label_entries = []
    for lt in legend_texts:
        text = lt["text"]
        lines = text.split("\n")
        y_offset = 0
        line_height = (lt["bottom"] - lt["top"]) / max(len(lines), 1)
        for line in lines:
            line = line.strip()
            if not line:
                y_offset += 1
                continue
            etype, section, spec, prefix, is_diaphragm = parse_legend_label(line)
            # PPT-specific: handle column section labels like "C100x100 C100x120"
            if etype == "unknown":
                cm = _COLUMN_SECTION_RE.search(line)
                if cm:
                    w_val, d_val = int(cm.group(1)), int(cm.group(2))
                    lo, hi = sorted([w_val, d_val])
                    etype = "column"
                    section = f"C{lo}X{hi}"
                    spec = 1
                    prefix = "C"
                    is_diaphragm = False
            if etype != "unknown":
                label_entries.append({
                    "label": line,
                    "element_type": etype,
                    "section": section,
                    "specificity": spec,
                    "prefix": prefix,
                    "is_diaphragm": is_diaphragm,
                    "cx": lt["cx"],
                    "cy": int(lt["top"] + y_offset * line_height + line_height / 2),
                    "left": lt["left"],
                })
            y_offset += 1

    # Collect colored FREEFORM swatches in legend region
    # Swatches are short lines or small shapes with distinct colors
    legend_swatches = []
    for shape in slide.shapes:
        if shape.shape_type != MSO_SHAPE_TYPE.FREEFORM:
            continue
        cx = shape.left + shape.width // 2
        if side == "left" and cx > boundary:
            continue
        if side == "right" and cx < boundary:
            continue

        # Skip very large shapes (borders, backgrounds)
        if shape.width > slide_w * 0.5 or shape.height > slide_h * 0.5:
            continue

        line_color = _get_shape_color(shape, "line")
        fill_color = _get_shape_color(shape, "fill")
        color = line_color or fill_color
        if color and color != "FFFFFF":  # Skip white (background)
            legend_swatches.append({
                "color": color,
                "left": shape.left,
                "top": shape.top,
                "cx": shape.left + shape.width // 2,
                "cy": shape.top + shape.height // 2,
                "right": shape.left + shape.width,
            })

    # Match each label to the nearest swatch by proximity.
    # Strategy: swatch should be near the label vertically and to its left
    # (or overlapping). We use a generous tolerance since PPT layouts vary.
    mapping: dict[str, list[LegendEntry]] = {}

    for lbl in label_entries:
        best_swatch = None
        best_dist = float("inf")

        for sw in legend_swatches:
            # Swatch should be roughly at the same Y as the label
            dy = abs(sw["cy"] - lbl["cy"])
            if dy > 300000:  # Too far vertically
                continue
            # Swatch center should not be far to the right of label center
            dx = sw["cx"] - lbl["cx"]
            if dx > 500000:  # Swatch center too far right
                continue
            dist = math.sqrt(dx ** 2 + dy ** 2)
            if dist < best_dist:
                best_dist = dist
                best_swatch = sw

        if best_swatch:
            color_hex = best_swatch["color"]
            rgb = [int(color_hex[i:i+2], 16) for i in (0, 2, 4)]
            entry = LegendEntry(
                element_type=lbl["element_type"],
                section=lbl["section"],
                color_name=color_hex,
                color_rgb=rgb,
                specificity=lbl["specificity"],
                is_diaphragm=lbl["is_diaphragm"],
                prefix=lbl["prefix"],
                label=lbl["label"],
            )
            mapping.setdefault(color_hex, []).append(entry)

    # Sort by specificity descending within each color
    for c in mapping:
        mapping[c].sort(key=lambda e: -e.specificity)

    return mapping


# ─── Shape Extraction & Classification ────────────────────────────────────────

def _resolve_pptx_legend(color_hex, geom_type, legend):
    """Resolve a shape's color to a legend entry.

    geom_type: 'line' | 'rectangle'
    """
    entries = legend.get(color_hex, [])
    if not entries:
        return None

    compat = {
        "line": ("beam", "small_beam", "wall"),
        "rectangle": ("column",),
    }
    for e in entries:
        if e.element_type in compat.get(geom_type, ()):
            return e
    return entries[0]


def extract_and_classify_shapes(slide, slide_num, legend, scale, floors,
                                phase, slide_w, slide_h, legend_boundary,
                                legend_side, warnings):
    """Extract FREEFORM shapes and classify them into structural elements.

    Returns list of element dicts.
    """
    elements = []
    slide_area = slide_w * slide_h

    # Collect all freeforms for column dedup
    filled_rects = []
    outline_rects = []
    lines = []

    for shape in slide.shapes:
        if shape.shape_type != MSO_SHAPE_TYPE.FREEFORM:
            continue

        w, h = shape.width, shape.height
        left, top = shape.left, shape.top

        # Skip shapes in legend region
        cx = left + w // 2
        if legend_side == "left" and cx < legend_boundary:
            continue
        if legend_side == "right" and cx > legend_boundary:
            continue

        # Skip extremely large shapes (background/border)
        if w > 0 and h > 0 and (w * h) > slide_area * SLIDE_AREA_RATIO_MAX:
            continue

        line_color = _get_shape_color(shape, "line")
        fill_color = _get_shape_color(shape, "fill")

        if w == 0 or h == 0:
            # Line shape (beam candidate)
            length = max(w, h)
            if length <= TICK_MAX_LENGTH_EMU:
                continue  # Skip tick marks
            lines.append({
                "left": left, "top": top, "width": w, "height": h,
                "color": line_color or fill_color,
                "orientation": "H" if h == 0 else "V",
            })
        elif w > 0 and h > 0 and w < 500000 and h < 500000:
            # Small rectangle (column candidate)
            if fill_color:
                filled_rects.append({
                    "left": left, "top": top, "width": w, "height": h,
                    "color": fill_color,
                })
            elif line_color:
                outline_rects.append({
                    "left": left, "top": top, "width": w, "height": h,
                    "color": line_color,
                })

    # ── Deduplicate columns (fill + outline pairs) ──────────────────
    columns = _deduplicate_columns(filled_rects, outline_rects)

    # ── Classify columns ──────────────────────────────────────────────
    if phase in ("phase1", "all"):
        for col in columns:
            entry = _resolve_pptx_legend(col["color"], "rectangle", legend)
            if not entry or entry.element_type != "column":
                continue

            # Skip shapes too small to be columns
            if col["width"] < MIN_COLUMN_DIM_EMU or col["height"] < MIN_COLUMN_DIM_EMU:
                continue

            cx_emu = col["left"] + col["width"] // 2
            cy_emu = col["top"] + col["height"] // 2
            cx_m, cy_m = _emu_to_m(cx_emu, cy_emu, scale, slide_h)

            # Use legend section if specific; otherwise leave empty
            # (PPT column shapes are not drawn to scale, so dimension-based
            #  section names are unreliable)
            section = entry.section or ""

            elements.append({
                "element_type": "column",
                "x1": cx_m, "y1": cy_m, "x2": cx_m, "y2": cy_m,
                "section": section,
                "floors": list(floors),
                "direction": "",
                "page_num": slide_num,
            })

    # ── Classify lines (beams) ────────────────────────────────────────
    for line in lines:
        color = line["color"]
        if not color:
            continue

        entry = _resolve_pptx_legend(color, "line", legend)
        if not entry:
            continue

        # Phase filter
        if phase == "phase1" and entry.element_type == "small_beam":
            continue
        if phase == "phase2" and entry.element_type != "small_beam":
            continue

        if line["orientation"] == "H":
            # Horizontal line: Y-direction beam
            x1_emu = line["left"]
            x2_emu = line["left"] + line["width"]
            y_emu = line["top"]
            x1_m, y1_m = _emu_to_m(x1_emu, y_emu, scale, slide_h)
            x2_m, y2_m = _emu_to_m(x2_emu, y_emu, scale, slide_h)
        else:
            # Vertical line: X-direction beam
            x_emu = line["left"]
            y1_emu = line["top"]
            y2_emu = line["top"] + line["height"]
            x1_m, y1_m = _emu_to_m(x_emu, y1_emu, scale, slide_h)
            x2_m, y2_m = _emu_to_m(x_emu, y2_emu, scale, slide_h)

        direction = _direction_of(x1_m, y1_m, x2_m, y2_m)

        elem = {
            "element_type": entry.element_type,
            "x1": x1_m, "y1": y1_m, "x2": x2_m, "y2": y2_m,
            "section": entry.section or "",
            "floors": list(floors),
            "direction": direction,
            "page_num": slide_num,
        }
        if entry.element_type == "wall" and entry.is_diaphragm:
            elem["is_diaphragm_wall"] = True
        if not entry.section:
            elem["section_uncertain"] = True
        elements.append(elem)

    return elements


def _deduplicate_columns(filled_rects, outline_rects):
    """Merge fill + outline FREEFORM pairs into single column entries.

    Two freeforms at the same position (within tolerance) represent one column:
    one with solid fill, one with outline only.
    """
    # Start with filled rects as the primary set
    columns = list(filled_rects)

    # Mark outline rects that overlap with a filled rect
    used_fills = set()
    for orect in outline_rects:
        ox, oy = orect["left"], orect["top"]
        matched = False
        for i, frect in enumerate(filled_rects):
            if i in used_fills:
                continue
            fx, fy = frect["left"], frect["top"]
            if (abs(ox - fx) < COLUMN_DEDUP_TOLERANCE_EMU and
                    abs(oy - fy) < COLUMN_DEDUP_TOLERANCE_EMU):
                matched = True
                used_fills.add(i)
                break
        if not matched:
            # Outline-only rect without matching fill — still a column
            columns.append(orect)

    return columns


# ─── Summary Report ──────────────────────────────────────────────────────────

def print_summary(output: dict):
    """Print human-readable summary to stdout."""
    meta = output["_metadata"]
    print(f"\n{'='*60}")
    print(f"pptx_to_elements.py — Summary")
    print(f"{'='*60}")
    print(f"Input:  {meta['input_file']}")
    print(f"Phase:  {meta['phase']}")

    if meta.get("scale_details"):
        for sd in meta["scale_details"]:
            if isinstance(sd, dict):
                print(f"Scale:  Slide {sd.get('slide', '?')}: "
                      f"{sd.get('emu_per_meter', '?')} EMU/m "
                      f"({sd.get('num_measurements', 0)} measurements)")

    print(f"\nPer-slide element counts:")
    for pn, stats in meta.get("per_page_stats", {}).items():
        floors = meta.get("page_floors", {}).get(pn, [])
        floor_desc = (f"{floors[0]}~{floors[-1]}" if len(floors) > 1
                      else (floors[0] if floors else "?"))
        parts = [f"{k}={v}" for k, v in stats.items() if v > 0]
        print(f"  Slide {pn} ({floor_desc}): {', '.join(parts) or 'none'}")

    totals = meta.get("totals", {})
    print(f"\nTotals (after dedup):")
    for k, v in totals.items():
        print(f"  {k}: {v}")

    secs = output.get("sections", {})
    if secs.get("frame"):
        print(f"\nFrame sections: {', '.join(secs['frame'])}")
    if secs.get("wall"):
        print(f"Wall thicknesses (cm): {', '.join(str(w) for w in secs['wall'])}")

    if meta.get("warnings"):
        print(f"\nWARNINGS ({len(meta['warnings'])}):")
        for w in meta["warnings"]:
            print(f"  ! {w}")

    print(f"{'='*60}\n")


# ─── Slide Listing ───────────────────────────────────────────────────────────

def list_slides(prs):
    """Print slide overview with shape type counts."""
    print(f"\nSlides: {len(prs.slides)}")
    print(f"Slide size: {prs.slide_width} x {prs.slide_height} EMU "
          f"({prs.slide_width / 914400:.1f} x {prs.slide_height / 914400:.1f} in)")
    print()
    for i, slide in enumerate(prs.slides):
        counts = {}
        for shape in slide.shapes:
            stype = str(shape.shape_type).split(".")[-1].split("(")[0].strip()
            counts[stype] = counts.get(stype, 0) + 1
        parts = [f"{k}={v}" for k, v in sorted(counts.items())]
        # Find floor label texts
        floor_texts = []
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.TEXT_BOX and shape.has_text_frame:
                t = shape.text_frame.text.strip()
                if re.match(r"^[BR]?\d+F$", t):
                    floor_texts.append(t)
        floor_info = f" (floors: {', '.join(floor_texts)})" if floor_texts else ""
        print(f"  Slide {i+1}: {', '.join(parts)}{floor_info}")
    print()


# ─── Main Pipeline ───────────────────────────────────────────────────────────

def process(prs, page_floors, phase, crop=False, crop_dir=None):
    """Main processing pipeline: PPTX → elements dict.

    Args:
        prs: python-pptx Presentation object.
        page_floors: {slide_num: [floor_names]}.
        phase: "phase1", "phase2", or "all".
        crop: Whether to extract PNG images.
        crop_dir: Directory for extracted PNGs.

    Returns:
        Complete output dict ready for JSON serialization.
    """
    warnings = []
    slide_w = prs.slide_width
    slide_h = prs.slide_height

    # Validate slide references
    num_slides = len(prs.slides)
    for sn in page_floors:
        if sn < 1 or sn > num_slides:
            warnings.append(
                f"Slide {sn} referenced in --page-floors but only {num_slides} slides exist"
            )

    all_elements = []
    per_page_stats = {}
    scale_details = []

    # Pre-compute scales for all requested slides; allow fallback
    slide_scales = {}
    for sn in sorted(page_floors.keys()):
        if sn < 1 or sn > num_slides:
            continue
        scale_val, scale_info = detect_slide_scale(prs.slides[sn - 1], sn)
        if scale_val is not None:
            slide_scales[sn] = (scale_val, scale_info)

    # Fallback scale: use median of all detected scales
    fallback_scale = None
    if slide_scales:
        all_scales = sorted(v[0] for v in slide_scales.values())
        fallback_scale = all_scales[len(all_scales) // 2]

    for sn, floors in sorted(page_floors.items()):
        if sn < 1 or sn > num_slides:
            continue
        slide = prs.slides[sn - 1]  # 1-based to 0-based
        print(f"\n--- Processing Slide {sn} ({', '.join(floors)}) ---")

        # 1) Detect scale (per-slide, with fallback)
        if sn in slide_scales:
            scale, scale_info = slide_scales[sn]
            print(f"  Scale: {scale:.1f} EMU/m ({scale_info.get('num_measurements', 0)} measurements)")
        elif fallback_scale:
            scale = fallback_scale
            scale_info = {"slide": sn, "emu_per_meter": round(scale, 1),
                          "num_measurements": 0, "fallback": True}
            warnings.append(
                f"Slide {sn}: no measurement texts, using fallback scale "
                f"{scale:.1f} EMU/m from other slides"
            )
            print(f"  Scale: {scale:.1f} EMU/m (FALLBACK from other slides)")
        else:
            warnings.append(f"Slide {sn}: no scale available, skipping")
            print(f"  ERROR: no scale available")
            continue
        scale_details.append(scale_info)

        # 2) Extract PNG (optional)
        if crop and crop_dir:
            floor_label = (f"{floors[0]}~{floors[-1]}" if len(floors) > 1
                           else floors[0])
            extract_base_png(slide, sn, floor_label, crop_dir)

        # 3) Parse legend
        legend = parse_legend(slide, slide_w, slide_h)
        if not legend:
            warnings.append(f"Slide {sn}: no legend detected, skipping")
            print(f"  WARNING: no legend detected")
            continue
        print(f"  Legend: {len(legend)} colors → "
              f"{sum(len(v) for v in legend.values())} entries")
        for color, entries in legend.items():
            for e in entries:
                print(f"    #{color} → {e.element_type}: {e.section or '(generic)'} [{e.label}]")

        # 4) Detect legend region for exclusion
        legend_side, legend_boundary = _detect_legend_region(slide, slide_w, slide_h)

        # 5) Extract & classify shapes
        slide_elems = extract_and_classify_shapes(
            slide, sn, legend, scale, floors, phase,
            slide_w, slide_h, legend_boundary, legend_side, warnings)
        all_elements.extend(slide_elems)

        # Per-slide stats
        stats = {"beams": 0, "columns": 0, "walls": 0, "small_beams": 0}
        for e in slide_elems:
            key = e["element_type"] + "s"
            if key in stats:
                stats[key] += 1
        per_page_stats[str(sn)] = stats
        print(f"  Elements: {', '.join(f'{k}={v}' for k, v in stats.items() if v > 0) or 'none'}")

    # Group & dedup
    grouped = group_and_dedup(all_elements)
    sections = collect_sections(grouped)

    # Build output (identical format to annot_to_elements)
    output = {
        "_metadata": {
            "source": "pptx_to_elements.py",
            "input_file": str(getattr(prs, '_pptx_path', '')),
            "generated_at": datetime.now(timezone.utc)
                            .strftime("%Y-%m-%dT%H:%M:%S"),
            "phase": phase,
            "page_floors": {str(k): v for k, v in page_floors.items()},
            "scale_details": scale_details,
            "per_page_stats": per_page_stats,
            "totals": {
                "columns": len(grouped["columns"]),
                "beams": len(grouped["beams"]),
                "walls": len(grouped["walls"]),
                "small_beams": len(grouped["small_beams"]),
            },
            "warnings": warnings,
        },
        "columns": grouped["columns"],
        "beams": grouped["beams"],
        "walls": grouped["walls"],
        "small_beams": grouped["small_beams"],
        "sections": sections,
    }
    return output


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="PPT structural plan → elements JSON"
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to .pptx file")
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file path (elements.json or sb_elements.json)")
    parser.add_argument(
        "--page-floors",
        help='Slide-to-floor mapping, e.g. "1=B3F, 3=1F~2F, 4=3F~14F"')
    parser.add_argument(
        "--phase", choices=["phase1", "phase2", "all"], default="all",
        help="phase1=beams+columns+walls, phase2=small_beams, all=both")
    parser.add_argument(
        "--crop", action="store_true",
        help="Extract PNG base images from slides")
    parser.add_argument(
        "--crop-dir",
        help="Directory for extracted PNGs")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show summary without writing output file")
    parser.add_argument(
        "--list-slides", action="store_true",
        help="List slides and exit")

    args = parser.parse_args()

    # Load PPTX
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    prs = Presentation(str(input_path))
    prs._pptx_path = str(input_path)
    print(f"Loaded: {input_path.name} ({len(prs.slides)} slides)")

    # List mode
    if args.list_slides:
        list_slides(prs)
        return

    # Require --page-floors and --output for processing
    if not args.page_floors:
        print("ERROR: --page-floors is required for processing")
        sys.exit(1)
    if not args.output:
        print("ERROR: --output is required for processing")
        sys.exit(1)

    # Parse page-floors
    page_floors = parse_page_floors(args.page_floors)
    if not page_floors:
        print("ERROR: No valid slide-floor mappings in --page-floors")
        sys.exit(1)
    print(f"Slide-floor mappings: {len(page_floors)} slides")

    # Process
    output = process(prs, page_floors, args.phase,
                     crop=args.crop, crop_dir=args.crop_dir)

    # Summary
    print_summary(output)

    # Write
    if args.dry_run:
        print("[DRY RUN] No output written.")
    else:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Output written to: {out_path}")


if __name__ == "__main__":
    main()
