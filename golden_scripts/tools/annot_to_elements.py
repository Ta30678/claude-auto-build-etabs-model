"""
Deterministic Annotation-to-Elements Script
============================================
Converts Bluebeam annotation JSON (from pdf_annot_extractor) into structural
element JSON (columns, beams, walls, small beams) with precise coordinates.

Replaces non-deterministic AI element classification. Output is always identical
for the same input.

Usage:
    # Phase 1: major beams + columns + walls
    python -m golden_scripts.tools.annot_to_elements \
        --input annotations.json --output elements.json \
        --page-floors "1=B3F, 3=1F~2F, 4=3F~14F, 5=R1F~R3F" \
        --phase phase1

    # Phase 2: small beams only
    python -m golden_scripts.tools.annot_to_elements \
        --input annotations.json --output sb_elements.json \
        --page-floors "3=1F~2F, 4=3F~14F" \
        --phase phase2

    # Both phases at once
    python -m golden_scripts.tools.annot_to_elements \
        --input annotations.json --output elements.json \
        --page-floors "1=B3F, 3=1F~2F, 4=3F~14F" \
        --phase all

    # Preview without writing
    python -m golden_scripts.tools.annot_to_elements ... --dry-run
"""

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ─── Constants ────────────────────────────────────────────────────────────────

ROUND_5CM = 5                   # Round column dimensions to nearest 5cm
COLOR_MATCH_TOLERANCE = 0.20    # RGB Euclidean distance for fallback matching
LEGEND_DISTANCE_WARN = 80       # pt — warn if legend association is far
COORD_PRECISION = 2             # decimal places (0.01m = 1cm)
DIRECTION_RATIO = 0.1           # dx/dy or dy/dx threshold for axis detection


# ─── Data Structures ─────────────────────────────────────────────────────────

@dataclass
class LegendEntry:
    """A legend item mapping a color to a structural element type."""
    element_type: str           # "beam", "small_beam", "column", "wall"
    section: Optional[str]      # e.g. "B55X80", "SB30X60", or None (generic)
    color_name: str
    color_rgb: list
    specificity: int            # 0=generic, 1=specific
    is_diaphragm: bool = False
    prefix: str = ""            # B, SB, WB, FB, FWB, FSB, C, W
    label: str = ""             # original label text


# ─── Step 1: Floor Range Expansion & Input Parsing ────────────────────────────

def expand_floor_range(range_str: str) -> list[str]:
    """Expand floor range like '3F~14F' into ['3F', '4F', ..., '14F'].

    Supported patterns:
      B3F~B1F   → [B3F, B2F, B1F]      (basement descending)
      B3F~1F    → [B3F, B2F, B1F, 1F]   (basement to ground)
      1F~14F    → [1F, 2F, ..., 14F]     (normal ascending)
      R1F~R3F   → [R1F, R2F, R3F]        (rooftop ascending)
      RF        → [RF]                    (single floor)
    """
    range_str = range_str.strip()
    if "~" not in range_str:
        return [range_str]

    start, end = [s.strip() for s in range_str.split("~", 1)]

    # Basement: B3F~B1F
    ms = re.match(r"^B(\d+)F$", start)
    me = re.match(r"^B(\d+)F$", end)
    if ms and me:
        s, e = int(ms.group(1)), int(me.group(1))
        step = -1 if s > e else 1
        return [f"B{i}F" for i in range(s, e + step, step)]

    # Basement to ground: B3F~1F  or  B3F~2F
    if ms and re.match(r"^(\d+)F$", end):
        s = int(ms.group(1))
        e = int(re.match(r"^(\d+)F$", end).group(1))
        result = [f"B{i}F" for i in range(s, 0, -1)]
        result.extend(f"{i}F" for i in range(1, e + 1))
        return result

    # Normal floors: 3F~14F
    ms = re.match(r"^(\d+)F$", start)
    me = re.match(r"^(\d+)F$", end)
    if ms and me:
        s, e = int(ms.group(1)), int(me.group(1))
        return [f"{i}F" for i in range(s, e + 1)]

    # Rooftop: R1F~R3F
    ms = re.match(r"^R(\d+)F$", start)
    me = re.match(r"^R(\d+)F$", end)
    if ms and me:
        s, e = int(ms.group(1)), int(me.group(1))
        return [f"R{i}F" for i in range(s, e + 1)]

    # Normal floor to RF: 12F~RF (we cannot enumerate without max floor)
    # Normal floor to R1F:  similar
    ms_n = re.match(r"^(\d+)F$", start)
    me_r = re.match(r"^R(\d*)F$", end)
    if ms_n and me_r:
        s = int(ms_n.group(1))
        r_num = me_r.group(1)
        result = [f"{i}F" for i in range(s, s + 1)]  # start only
        # We'll append RF / R1F etc. — caller must provide full floor list if needed
        result.append(end)
        print(f"  WARNING: Cannot fully enumerate '{range_str}'; returning [{start}, {end}]")
        return result

    # Fallback
    print(f"  WARNING: Cannot expand floor range '{range_str}'; returning as-is")
    return [start, end]


def parse_page_floors(page_floors_str: str) -> dict[int, list[str]]:
    """Parse --page-floors argument.

    Format: "1=B3F, 3=1F~2F, 4=3F~14F, 5=R1F~R3F"
    Returns: {1: ["B3F"], 3: ["1F","2F"], 4: ["3F",..."14F"], ...}
    """
    result = {}
    for item in page_floors_str.split(","):
        item = item.strip()
        if "=" not in item:
            continue
        page_str, floor_range = item.split("=", 1)
        page_num = int(page_str.strip())
        floors = expand_floor_range(floor_range.strip())
        result[page_num] = floors
    return result


# ─── Step 2: Legend Label Parser & Mapping Builder ────────────────────────────

# Regex for section names like SB30x60, FB100x230, FWB60x230, B55x80
_SECTION_RE = re.compile(
    r"(FWB|FSB|FB|WB|SB|B)(\d+)[xX](\d+)", re.IGNORECASE
)

# Regex for wall thickness like "90CM 連續壁" or "25cm壁"
_WALL_CM_RE = re.compile(r"(\d+)\s*[cC][mM]\s*(?:連續壁|壁)")


def parse_legend_label(label: str):
    """Parse a legend label text.

    Returns (element_type, section_or_None, specificity, prefix, is_diaphragm).
    """
    lab = label.strip()

    # 1) Specific section: SB30x60, FB100x230, FWB60x230, B55x80 …
    m = _SECTION_RE.search(lab)
    if m:
        prefix = m.group(1).upper()
        w, d = int(m.group(2)), int(m.group(3))
        section = f"{prefix}{w}X{d}"
        if prefix in ("SB", "FSB"):
            return "small_beam", section, 1, prefix, False
        return "beam", section, 1, prefix, False

    # 2) Wall thickness: "90CM 連續壁"
    m = _WALL_CM_RE.search(lab)
    if m:
        t = int(m.group(1))
        return "wall", f"W{t}", 1, "W", True

    # 3) Generic Chinese keywords
    if "連續壁" in lab:
        return "wall", None, 0, "W", True
    if "<RC大梁>" in lab or "大梁" in lab:
        return "beam", None, 0, "B", False
    if "<RC小梁>" in lab or "小梁" in lab or "次梁" in lab:
        return "small_beam", None, 0, "SB", False
    if any(kw in lab for kw in ("<RC柱>", "邊柱", "內柱", "角柱")):
        return "column", None, 0, "C", False
    if "壁" in lab or "剪力牆" in lab:
        return "wall", None, 0, "W", False

    return "unknown", None, 0, "", False


def build_legend_mapping(page_data: dict, warnings: list) -> dict[str, list[LegendEntry]]:
    """Build color_name → [LegendEntry] from a page's legend data.

    Entries are sorted by specificity descending within each color.
    """
    legend = page_data.get("annotations", {}).get("legend", {})
    items = legend.get("items", [])
    mapping: dict[str, list[LegendEntry]] = {}

    for item in items:
        lab = item.get("label", "")
        cname = item.get("nearby_color_name", "")
        crgb = item.get("nearby_color", [])
        dist = item.get("distance_pt", 0)

        if not cname or not lab:
            continue

        etype, section, spec, prefix, diaphragm = parse_legend_label(lab)
        if etype == "unknown":
            continue

        if dist > LEGEND_DISTANCE_WARN:
            pn = page_data.get("page_num", "?")
            warnings.append(
                f"Page {pn}: '{lab}' legend distance_pt={dist} "
                f"(>{LEGEND_DISTANCE_WARN}, may be misassociation)"
            )

        entry = LegendEntry(
            element_type=etype, section=section, color_name=cname,
            color_rgb=crgb, specificity=spec, is_diaphragm=diaphragm,
            prefix=prefix, label=lab,
        )
        mapping.setdefault(cname, []).append(entry)

    # Most specific first per color
    for c in mapping:
        mapping[c].sort(key=lambda e: -e.specificity)

    return mapping


def _rgb_dist(a: list, b: list) -> float:
    if len(a) < 3 or len(b) < 3:
        return float("inf")
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a[:3], b[:3])))


def resolve_legend(color_name: str, color_rgb: list, geom_type: str,
                   legend: dict[str, list[LegendEntry]]) -> Optional[LegendEntry]:
    """Resolve an annotation's color to a legend entry.

    geom_type: "line" | "rectangle" | "polygon"
    """
    # 1) Direct color-name match
    entries = legend.get(color_name, [])
    if entries:
        # Prefer geometry-compatible match
        compat = {
            "line": ("beam", "small_beam"),
            "rectangle": ("column",),
            "polygon": ("wall",),
        }
        for e in entries:
            if e.element_type in compat.get(geom_type, ()):
                return e
        return entries[0]  # fallback to most specific

    # 2) RGB distance fallback (handles hex color names)
    if color_rgb:
        best, best_d = None, float("inf")
        for elist in legend.values():
            for e in elist:
                d = _rgb_dist(color_rgb, e.color_rgb)
                if d < best_d:
                    best_d, best = d, e
        if best is not None and best_d < COLOR_MATCH_TOLERANCE:
            return best

    return None


# ─── Step 3: Legend Area Boundary ─────────────────────────────────────────────

def _legend_boundary(page_data: dict) -> dict:
    """Compute legend exclusion zone from actual legend text positions.

    Strategy:
    1. Find legend item labels in the texts array to get their positions.
    2. Build a tight bounding box around those texts (+ 50pt padding).
    3. Only annotations within that box are excluded.
    4. If legend texts are outside page bounds (common with rotated pages),
       no exclusion is needed (structural annotations are within page bounds).
    """
    pw, ph = page_data.get("page_size_pt", [1191, 842])
    annots = page_data.get("annotations", {})
    legend = annots.get("legend", {})
    legend_labels = {item["label"] for item in legend.get("items", [])
                     if item.get("label")}

    if not legend_labels:
        return {"mode": "none"}

    # Find positions of legend texts
    legend_rects = []
    for txt in annots.get("texts", []):
        content = txt.get("content", "").strip()
        if content in legend_labels:
            rpt = txt.get("rect_pt", [])
            if len(rpt) >= 4:
                cx = (rpt[0] + rpt[2]) / 2
                cy = (rpt[1] + rpt[3]) / 2
                legend_rects.append((cx, cy))

    if not legend_rects:
        return {"mode": "none"}

    # Check if legend texts are outside page bounds
    all_outside = all(cy > ph or cx > pw or cx < 0 or cy < 0
                      for cx, cy in legend_rects)
    if all_outside:
        # Legend is drawn outside page bounds (rotated PDF) — no exclusion needed
        return {"mode": "none"}

    # Build tight bounding box around legend texts
    xs = [p[0] for p in legend_rects]
    ys = [p[1] for p in legend_rects]
    pad = 50  # pt padding
    return {
        "mode": "bbox",
        "x_min": min(xs) - pad,
        "y_min": min(ys) - pad,
        "x_max": max(xs) + pad,
        "y_max": max(ys) + pad,
    }


def _in_legend(cx: float, cy: float, bnd: dict) -> bool:
    """True if (cx, cy) in pt coords falls inside the legend exclusion zone."""
    if bnd.get("mode") == "none":
        return False
    if bnd.get("mode") == "bbox":
        return (bnd["x_min"] <= cx <= bnd["x_max"]
                and bnd["y_min"] <= cy <= bnd["y_max"])
    return False


# ─── Step 4: Coordinate Conversion ───────────────────────────────────────────

def _pt_to_m(x_pt: float, y_pt: float, scale: float,
             page_h: float) -> tuple[float, float]:
    """PDF pt → meters (origin = bottom-left, Y up)."""
    return (round(x_pt * scale, COORD_PRECISION),
            round((page_h - y_pt) * scale, COORD_PRECISION))


def _round5(val_m: float) -> int:
    """Round meter value to nearest 5 cm (returns cm)."""
    cm = val_m * 100
    return max(5, round(cm / ROUND_5CM) * ROUND_5CM)


def _direction_of(x1, y1, x2, y2) -> str:
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    if dx < 0.01 and dy < 0.01:
        return ""
    if dy < 0.01 or (dx > 0 and dy / max(dx, 1e-9) < DIRECTION_RATIO):
        return "X"
    if dx < 0.01 or (dy > 0 and dx / max(dy, 1e-9) < DIRECTION_RATIO):
        return "Y"
    return ""


# ─── Step 5: Wall Geometry Extraction ─────────────────────────────────────────

def _wall_centerline(verts):
    """Extract (x1,y1,x2,y2) centerline and thickness from wall polygon.

    For a 4-vertex polygon: centerline = midpoints of the shorter pair of
    opposite edges; thickness = average of that shorter pair's lengths.
    For other polygons: bounding-box heuristic.

    Returns ((x1,y1,x2,y2), thickness_m) or (None, 0).
    """
    if len(verts) < 3:
        return None, 0

    if len(verts) == 4:
        def elen(i, j):
            return math.hypot(verts[j][0] - verts[i][0],
                              verts[j][1] - verts[i][1])

        e01, e12, e23, e30 = elen(0, 1), elen(1, 2), elen(2, 3), elen(3, 0)
        pair1 = (e01 + e23) / 2   # edges 0-1, 2-3
        pair2 = (e12 + e30) / 2   # edges 1-2, 3-0

        if pair1 > pair2:
            # pair2 = short edges → thickness; centerline through pair2 midpoints
            thickness = pair2
            m1 = ((verts[3][0] + verts[0][0]) / 2,
                  (verts[3][1] + verts[0][1]) / 2)
            m2 = ((verts[1][0] + verts[2][0]) / 2,
                  (verts[1][1] + verts[2][1]) / 2)
        else:
            thickness = pair1
            m1 = ((verts[0][0] + verts[1][0]) / 2,
                  (verts[0][1] + verts[1][1]) / 2)
            m2 = ((verts[2][0] + verts[3][0]) / 2,
                  (verts[2][1] + verts[3][1]) / 2)

        return ((round(m1[0], COORD_PRECISION), round(m1[1], COORD_PRECISION),
                 round(m2[0], COORD_PRECISION), round(m2[1], COORD_PRECISION)),
                thickness)

    # Fallback: bounding box
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    mn_x, mx_x = min(xs), max(xs)
    mn_y, mx_y = min(ys), max(ys)
    w, h = mx_x - mn_x, mx_y - mn_y
    if w > h:
        thickness = h
        cy = (mn_y + mx_y) / 2
        return ((round(mn_x, COORD_PRECISION), round(cy, COORD_PRECISION),
                 round(mx_x, COORD_PRECISION), round(cy, COORD_PRECISION)),
                thickness)
    else:
        thickness = w
        cx = (mn_x + mx_x) / 2
        return ((round(cx, COORD_PRECISION), round(mn_y, COORD_PRECISION),
                 round(cx, COORD_PRECISION), round(mx_y, COORD_PRECISION)),
                thickness)


# ─── Steps 4-5: Classify Page Annotations ────────────────────────────────────

def _classify_page(page_data: dict, legend: dict[str, list[LegendEntry]],
                   global_scale: float, floors: list[str],
                   phase: str, warnings: list) -> list[dict]:
    """Classify annotations on one page into structural element dicts.

    Returns list of element dicts (not dataclass, for JSON serialization).
    """
    pn = page_data.get("page_num", 0)
    pw, ph = page_data.get("page_size_pt", [1191, 842])

    # Page-level or global scale
    pscale = page_data.get("scale", {}).get("meters_per_point")
    scale = pscale or global_scale
    if not scale:
        warnings.append(f"Page {pn}: no scale available, skipping")
        return []

    bnd = _legend_boundary(page_data)
    annots = page_data.get("annotations", {})
    elements = []

    # ── Lines → beams / small beams ──────────────────────────────────────
    for line in annots.get("lines", []):
        cname = line.get("color_name", "")
        crgb = line.get("color_rgb", [])
        entry = resolve_legend(cname, crgb, "line", legend)
        if not entry:
            continue

        # Phase filter
        if phase == "phase1" and entry.element_type == "small_beam":
            continue
        if phase == "phase2" and entry.element_type != "small_beam":
            continue

        # Coordinates: prefer meters, fallback to pt conversion
        meters = line.get("meters")
        pt = line.get("pt", {})

        if meters:
            x1 = round(meters["start"]["x"], COORD_PRECISION)
            y1 = round(meters["start"]["y"], COORD_PRECISION)
            x2 = round(meters["end"]["x"], COORD_PRECISION)
            y2 = round(meters["end"]["y"], COORD_PRECISION)
        elif pt:
            x1, y1 = _pt_to_m(pt["x1"], pt["y1"], scale, ph)
            x2, y2 = _pt_to_m(pt["x2"], pt["y2"], scale, ph)
        else:
            continue

        # Legend exclusion (always check in pt space)
        if pt:
            cx = (pt.get("x1", 0) + pt.get("x2", 0)) / 2
            cy = (pt.get("y1", 0) + pt.get("y2", 0)) / 2
            if _in_legend(cx, cy, bnd):
                continue

        direction = _direction_of(x1, y1, x2, y2)

        elem = {
            "element_type": entry.element_type,
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "section": entry.section or "",
            "floors": list(floors),
            "direction": direction,
            "page_num": pn,
        }
        if not entry.section:
            elem["section_uncertain"] = True

        elements.append(elem)

    # ── Rectangles → columns ─────────────────────────────────────────────
    if phase in ("phase1", "all"):
        for rect in annots.get("rectangles", []):
            cname = rect.get("color_name", "")
            crgb = rect.get("color_rgb", [])
            entry = resolve_legend(cname, crgb, "rectangle", legend)
            if not entry or entry.element_type != "column":
                continue

            # Center coordinate
            center_m = rect.get("center_m")
            center_pt = rect.get("center_pt", [])
            if center_pt and _in_legend(center_pt[0], center_pt[1], bnd):
                continue

            if center_m:
                cx = round(center_m["x"], COORD_PRECISION)
                cy = round(center_m["y"], COORD_PRECISION)
            elif center_pt:
                cx, cy = _pt_to_m(center_pt[0], center_pt[1], scale, ph)
            else:
                continue

            # Section from size
            size_m = rect.get("size_m")
            size_pt = rect.get("size_pt", [])
            if size_m and len(size_m) >= 2:
                w_cm = _round5(size_m[0])
                d_cm = _round5(size_m[1])
            elif size_pt and len(size_pt) >= 2:
                w_cm = _round5(size_pt[0] * scale)
                d_cm = _round5(size_pt[1] * scale)
            else:
                w_cm, d_cm = 0, 0

            if w_cm > 0 and d_cm > 0:
                lo, hi = sorted([w_cm, d_cm])
                section = f"C{lo}X{hi}"
            else:
                section = ""

            # Override from content field if present
            content = rect.get("content", "")
            if content:
                mc = re.search(r"C(\d+)[xX](\d+)", content)
                if mc:
                    section = f"C{mc.group(1)}X{mc.group(2)}"

            elements.append({
                "element_type": "column",
                "x1": cx, "y1": cy, "x2": cx, "y2": cy,
                "section": section,
                "floors": list(floors),
                "direction": "",
                "page_num": pn,
            })

    # ── Polygons → walls ─────────────────────────────────────────────────
    if phase in ("phase1", "all"):
        for poly in annots.get("polygons", []):
            cname = poly.get("color_name", "")
            crgb = poly.get("color_rgb", [])
            entry = resolve_legend(cname, crgb, "polygon", legend)
            if not entry or entry.element_type != "wall":
                continue

            vm = poly.get("vertices_m")
            vpt = poly.get("vertices_pt", [])

            # Legend exclusion in pt space
            if vpt:
                avg_x = sum(v[0] for v in vpt) / len(vpt)
                avg_y = sum(v[1] for v in vpt) / len(vpt)
                if _in_legend(avg_x, avg_y, bnd):
                    continue

            if vm:
                verts = [(round(v["x"], COORD_PRECISION),
                          round(v["y"], COORD_PRECISION)) for v in vm]
            elif vpt:
                verts = [_pt_to_m(v[0], v[1], scale, ph) for v in vpt]
            else:
                continue

            cl, thickness = _wall_centerline(verts)
            if cl is None:
                continue

            x1, y1, x2, y2 = cl

            if entry.section:
                section = entry.section
            else:
                t_cm = round(thickness * 100)
                t_cm = max(5, round(t_cm / 5) * 5)
                section = f"W{t_cm}"

            elements.append({
                "element_type": "wall",
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "section": section,
                "floors": list(floors),
                "direction": _direction_of(x1, y1, x2, y2),
                "is_diaphragm_wall": entry.is_diaphragm,
                "page_num": pn,
            })

    return elements


# ─── Step 6: Grouping & Deduplication ─────────────────────────────────────────

def _elem_key(e: dict) -> tuple:
    """Key for deduplication: type + coordinates + section."""
    return (
        e["element_type"],
        round(e["x1"], COORD_PRECISION),
        round(e["y1"], COORD_PRECISION),
        round(e["x2"], COORD_PRECISION),
        round(e["y2"], COORD_PRECISION),
        e.get("section", ""),
    )


def group_and_dedup(all_elements: list[dict]) -> dict[str, list[dict]]:
    """Group elements by type; merge floors for duplicates (same position+section).

    Returns {"columns": [...], "beams": [...], "walls": [...], "small_beams": [...]}.
    """
    merged: dict[tuple, dict] = {}

    for e in all_elements:
        key = _elem_key(e)
        if key in merged:
            # Merge floors (union, preserve order)
            existing_floors = merged[key]["floors"]
            for f in e["floors"]:
                if f not in existing_floors:
                    existing_floors.append(f)
        else:
            merged[key] = dict(e)  # shallow copy

    # Split into typed arrays
    result = {"columns": [], "beams": [], "walls": [], "small_beams": []}
    for elem in merged.values():
        etype = elem.pop("element_type")
        elem.pop("page_num", None)
        elem.pop("section_uncertain", None)
        target_key = {
            "column": "columns",
            "beam": "beams",
            "wall": "walls",
            "small_beam": "small_beams",
        }.get(etype)
        if target_key:
            # For columns: use grid_x/grid_y naming
            if etype == "column":
                out = {
                    "grid_x": elem["x1"],
                    "grid_y": elem["y1"],
                    "section": elem["section"],
                    "floors": elem["floors"],
                }
                result["columns"].append(out)
            else:
                out = {
                    "x1": elem["x1"], "y1": elem["y1"],
                    "x2": elem["x2"], "y2": elem["y2"],
                    "section": elem["section"],
                    "floors": elem["floors"],
                    "direction": elem.get("direction", ""),
                }
                if etype == "wall" and elem.get("is_diaphragm_wall"):
                    out["is_diaphragm_wall"] = True
                result[target_key].append(out)

    return result


# ─── Step 7: Collect Sections ─────────────────────────────────────────────────

def collect_sections(grouped: dict) -> dict:
    """Gather all unique section names by type."""
    frame_set = set()
    wall_set = set()

    for c in grouped.get("columns", []):
        if c["section"]:
            frame_set.add(c["section"])
    for b in grouped.get("beams", []):
        if b["section"]:
            frame_set.add(b["section"])
    for sb in grouped.get("small_beams", []):
        if sb["section"]:
            frame_set.add(sb["section"])
    for w in grouped.get("walls", []):
        s = w["section"]
        if s:
            m = re.match(r"^W(\d+)$", s)
            if m:
                wall_set.add(int(m.group(1)))

    return {
        "frame": sorted(frame_set),
        "wall": sorted(wall_set),
    }


# ─── Main Pipeline ────────────────────────────────────────────────────────────

def process(data: dict, page_floors: dict[int, list[str]],
            phase: str) -> dict:
    """Main processing pipeline: annotation JSON → elements JSON.

    Args:
        data: Parsed annotations.json content.
        page_floors: {page_num: [floor_names]}.
        phase: "phase1", "phase2", or "all".

    Returns:
        Complete output dict ready for JSON serialization.
    """
    warnings: list[str] = []

    # Global scale
    global_scale = data.get("scale", {}).get("meters_per_point")
    if not global_scale:
        # Try to get from first page that has scale
        for pd in data.get("pages", []):
            s = pd.get("scale", {}).get("meters_per_point")
            if s:
                global_scale = s
                break
    if not global_scale:
        print("ERROR: No scale factor found in annotations.json")
        sys.exit(1)

    # Validate page references
    available_pages = {pd["page_num"] for pd in data.get("pages", [])}
    for pn in page_floors:
        if pn not in available_pages:
            warnings.append(f"Page {pn} referenced in --page-floors but not in JSON")

    # Process each page
    all_elements = []
    per_page_stats = {}

    for pd in data.get("pages", []):
        pn = pd["page_num"]
        if pn not in page_floors:
            continue
        floors = page_floors[pn]

        # Build page-specific legend
        legend = build_legend_mapping(pd, warnings)

        # Fall back to previous page's legend if empty
        if not legend and pn > 1:
            for prev_pd in data.get("pages", []):
                if prev_pd["page_num"] < pn:
                    prev_legend = build_legend_mapping(prev_pd, warnings)
                    if prev_legend:
                        legend = prev_legend

        if not legend:
            warnings.append(f"Page {pn}: no legend detected, skipping")
            continue

        page_elems = _classify_page(pd, legend, global_scale, floors,
                                     phase, warnings)
        all_elements.extend(page_elems)

        # Per-page stats
        stats = {"beams": 0, "columns": 0, "walls": 0, "small_beams": 0}
        for e in page_elems:
            key = e["element_type"] + "s"
            if key in stats:
                stats[key] += 1
        per_page_stats[str(pn)] = stats

    # Group & dedup
    grouped = group_and_dedup(all_elements)
    sections = collect_sections(grouped)

    # Build output
    output = {
        "_metadata": {
            "source": "annot_to_elements.py",
            "input_file": data.get("file", ""),
            "generated_at": datetime.now(timezone.utc)
                            .strftime("%Y-%m-%dT%H:%M:%S"),
            "phase": phase,
            "page_floors": {str(k): v for k, v in page_floors.items()},
            "global_scale": global_scale,
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


# ─── Summary Report ───────────────────────────────────────────────────────────

def print_summary(output: dict):
    """Print human-readable summary to stdout."""
    meta = output["_metadata"]
    print(f"\n{'='*60}")
    print(f"annot_to_elements.py — Summary")
    print(f"{'='*60}")
    print(f"Input:  {meta['input_file']}")
    print(f"Phase:  {meta['phase']}")
    print(f"Scale:  {meta['global_scale']} m/pt")

    print(f"\nPer-page element counts:")
    for pn, stats in meta.get("per_page_stats", {}).items():
        floors = meta.get("page_floors", {}).get(pn, [])
        floor_desc = f"{floors[0]}~{floors[-1]}" if len(floors) > 1 else (floors[0] if floors else "?")
        parts = [f"{k}={v}" for k, v in stats.items() if v > 0]
        print(f"  Page {pn} ({floor_desc}): {', '.join(parts) or 'none'}")

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


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Deterministic annotation → structural elements JSON"
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to annotations.json (from pdf_annot_extractor)")
    parser.add_argument(
        "--output", "-o", required=True,
        help="Output JSON file path (elements.json or sb_elements.json)")
    parser.add_argument(
        "--page-floors", required=True,
        help='Page-to-floor mapping, e.g. "1=B3F, 3=1F~2F, 4=3F~14F"')
    parser.add_argument(
        "--phase", choices=["phase1", "phase2", "all"], default="all",
        help="phase1=beams+columns+walls, phase2=small_beams, all=both")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show summary without writing output file")

    args = parser.parse_args()

    # Load input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"Loaded: {input_path.name} ({len(data.get('pages', []))} pages)")

    # Parse page-floors
    page_floors = parse_page_floors(args.page_floors)
    if not page_floors:
        print("ERROR: No valid page-floor mappings in --page-floors")
        sys.exit(1)
    print(f"Page-floor mappings: {len(page_floors)} pages")

    # Process
    output = process(data, page_floors, args.phase)

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
