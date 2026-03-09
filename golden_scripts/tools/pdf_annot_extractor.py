"""
Bluebeam PDF Annotation Extractor
==================================
Extracts structural annotations from Bluebeam-annotated PDFs with precise
coordinate data. Converts PDF-point coordinates to real-world meters using
scale factors derived from Length Measurement annotations.

Usage:
    python -m golden_scripts.tools.pdf_annot_extractor \
        --input "path/to/annotated.pdf" \
        --pages 5 \
        --output annotations.json

Dependencies:
    PyMuPDF (fitz) >= 1.27.0
"""

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF (fitz) is required. Install with: pip install PyMuPDF")
    sys.exit(1)


# ─── Color name mapping ───────────────────────────────────────────────────────

# Common Bluebeam annotation colors → human-readable names
# RGB values are normalized 0-1, matched with tolerance
COLOR_MAP = [
    ((1.0, 0.0, 0.0), "red"),
    ((0.0, 0.0, 1.0), "blue"),
    ((0.0, 1.0, 0.0), "green"),
    ((1.0, 1.0, 0.0), "yellow"),
    ((1.0, 0.5, 0.0), "orange"),
    ((0.5, 0.0, 0.5), "purple"),
    ((0.0, 0.5, 1.0), "sky_blue"),
    ((0.0, 1.0, 1.0), "cyan"),
    ((1.0, 0.0, 1.0), "magenta"),
    ((1.0, 0.5, 0.5), "pink"),
    ((0.5, 0.25, 0.0), "brown"),
    ((0.0, 0.5, 0.0), "dark_green"),
    ((0.5, 0.5, 0.5), "gray"),
    ((0.0, 0.0, 0.0), "black"),
    ((1.0, 1.0, 1.0), "white"),
]

COLOR_TOLERANCE = 0.15


def _color_name(rgb: tuple) -> str:
    """Map an RGB tuple (0-1 range) to a human-readable color name."""
    if not rgb or len(rgb) < 3:
        return "unknown"
    best_name = "unknown"
    best_dist = float("inf")
    for ref, name in COLOR_MAP:
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(rgb[:3], ref)))
        if dist < best_dist:
            best_dist = dist
            best_name = name
    if best_dist > COLOR_TOLERANCE * math.sqrt(3):
        # No close match — return hex
        r, g, b = [int(c * 255) for c in rgb[:3]]
        return f"#{r:02x}{g:02x}{b:02x}"
    return best_name


# ─── Measurement parsing ──────────────────────────────────────────────────────

# Patterns for parsing real-world distances from measurement content
_MEASURE_PATTERNS = [
    # "8.5 m", "8.5m", "8,500 mm", etc.
    re.compile(r"([\d,]+\.?\d*)\s*m(?:m)?(?:\s|$)", re.IGNORECASE),
    # "850 cm"
    re.compile(r"([\d,]+\.?\d*)\s*cm", re.IGNORECASE),
    # Just a number (assume meters if > 0.1, cm if > 100)
    re.compile(r"^([\d,]+\.?\d*)\s*$"),
]


def _parse_measurement_value(content: str) -> Optional[float]:
    """Parse a real-world distance in meters from measurement content text.

    Returns the value in meters, or None if unparsable.
    """
    if not content:
        return None

    content = content.strip()

    # Try "X m" or "X mm"
    m = re.search(r"([\d,]+\.?\d*)\s*mm", content, re.IGNORECASE)
    if m:
        val = float(m.group(1).replace(",", ""))
        return val / 1000.0  # mm → m

    m = re.search(r"([\d,]+\.?\d*)\s*m\b", content, re.IGNORECASE)
    if m:
        val = float(m.group(1).replace(",", ""))
        return val  # already meters

    m = re.search(r"([\d,]+\.?\d*)\s*cm", content, re.IGNORECASE)
    if m:
        val = float(m.group(1).replace(",", ""))
        return val / 100.0  # cm → m

    # Bare number — heuristic: if < 50, likely meters; otherwise cm
    m = re.match(r"^([\d,]+\.?\d*)\s*$", content)
    if m:
        val = float(m.group(1).replace(",", ""))
        if val < 50:
            return val  # meters
        else:
            return val / 100.0  # cm → m

    return None


def _pt_distance(x1, y1, x2, y2) -> float:
    """Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def _direction(x1, y1, x2, y2) -> str:
    """Determine if a line is primarily horizontal (H) or vertical (V)."""
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    if dy > dx * 2:
        return "V"
    elif dx > dy * 2:
        return "H"
    return "D"  # diagonal


# ─── Annotation extraction ────────────────────────────────────────────────────

@dataclass
class RawAnnotation:
    """Raw annotation data extracted from a PDF page."""
    index: int
    type: str           # fitz annot type name: "Line", "Square", "Polygon", etc.
    type_code: int      # fitz annot type code
    subject: str        # Bluebeam subject (e.g. "Length Measurement", "Rectangle")
    content: str        # Text content (UTF-8)
    rect: list          # Bounding rectangle [x0, y0, x1, y1] in PDF points
    vertices: list      # Vertex coordinates (for Line, Polygon, PolyLine)
    stroke_color: list  # Stroke color RGB (0-1)
    fill_color: list    # Fill color RGB (0-1)
    stroke_name: str    # Human-readable stroke color name
    fill_name: str      # Human-readable fill color name
    opacity: float
    width: float        # Line width
    flags: int
    info: dict          # Bluebeam metadata (title, subject, creator, etc.)


def _extract_raw_annotations(page: "fitz.Page") -> list[RawAnnotation]:
    """Extract all annotations from a PDF page."""
    annotations = []
    for i, annot in enumerate(page.annots()):
        try:
            atype = annot.type[1] if annot.type else "Unknown"
            atype_code = annot.type[0] if annot.type else -1

            # Get vertices for Line, Polygon, PolyLine
            vertices = []
            try:
                verts = annot.vertices
                if verts:
                    for p in verts:
                        if hasattr(p, 'x') and hasattr(p, 'y'):
                            vertices.append([round(p.x, 2), round(p.y, 2)])
                        elif isinstance(p, (tuple, list)) and len(p) >= 2:
                            vertices.append([round(p[0], 2), round(p[1], 2)])
            except Exception:
                pass

            # Colors
            stroke = None
            fill = None
            try:
                stroke = annot.colors.get("stroke")
                fill = annot.colors.get("fill")
            except Exception:
                pass
            stroke_list = list(stroke) if stroke else []
            fill_list = list(fill) if fill else []

            # Content (UTF-8)
            content = ""
            try:
                content = annot.info.get("content", "") or ""
                if not content:
                    content = annot.get_text() or ""
            except Exception:
                pass

            # Subject
            subject = ""
            try:
                subject = annot.info.get("subject", "") or ""
            except Exception:
                pass

            # Rect
            r = annot.rect
            rect = [round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)]

            # Info dict
            info = {}
            try:
                info = dict(annot.info) if annot.info else {}
            except Exception:
                pass

            # Opacity
            opacity = 1.0
            try:
                opacity = annot.opacity if annot.opacity is not None else 1.0
            except Exception:
                pass

            # Width
            width = 1.0
            try:
                border = annot.border
                if border and "width" in border:
                    width = border["width"]
            except Exception:
                pass

            annotations.append(RawAnnotation(
                index=i,
                type=atype,
                type_code=atype_code,
                subject=subject,
                content=content,
                rect=rect,
                vertices=vertices,
                stroke_color=stroke_list,
                fill_color=fill_list,
                stroke_name=_color_name(tuple(stroke_list)) if stroke_list else "",
                fill_name=_color_name(tuple(fill_list)) if fill_list else "",
                opacity=round(opacity, 3),
                width=round(width, 2),
                flags=annot.flags,
                info=info,
            ))
        except Exception as e:
            print(f"  Warning: Failed to extract annotation {i}: {e}")
    return annotations


# ─── Scale factor computation ─────────────────────────────────────────────────

@dataclass
class ScaleResult:
    meters_per_point: float
    source_count: int
    variance_pct: float
    measurements: list  # individual measurement details


def _compute_scale(annotations: list[RawAnnotation], page_height: float) -> Optional[ScaleResult]:
    """Compute scale factor from Length Measurement annotations.

    Returns ScaleResult or None if insufficient data.
    """
    measurements = []

    for annot in annotations:
        # Identify measurement annotations
        is_measurement = (
            "measurement" in annot.subject.lower()
            or "length" in annot.subject.lower()
            or "dimension" in annot.subject.lower()
        )
        if not is_measurement:
            continue

        # Parse real-world value
        real_m = _parse_measurement_value(annot.content)
        if real_m is None or real_m <= 0:
            continue

        # Get PDF-point distance from vertices
        verts = annot.vertices
        # Filter out empty/malformed vertices
        valid_verts = [v for v in (verts or []) if isinstance(v, (list, tuple)) and len(v) >= 2]

        if len(valid_verts) < 2:
            # Fall back to rect diagonal
            r = annot.rect
            pt_dist = _pt_distance(r[0], r[1], r[2], r[3])
            end_pts = [[r[0], r[1]], [r[2], r[3]]]
        elif len(valid_verts) == 2:
            pt_dist = _pt_distance(valid_verts[0][0], valid_verts[0][1],
                                   valid_verts[1][0], valid_verts[1][1])
            end_pts = [valid_verts[0], valid_verts[1]]
        else:
            # Try all consecutive pairs, pick the longest (the actual dimension line)
            max_dist = 0
            best_pair = (0, 1)
            for j in range(len(valid_verts) - 1):
                d = _pt_distance(valid_verts[j][0], valid_verts[j][1],
                                 valid_verts[j + 1][0], valid_verts[j + 1][1])
                if d > max_dist:
                    max_dist = d
                    best_pair = (j, j + 1)
            pt_dist = max_dist
            end_pts = [valid_verts[best_pair[0]], valid_verts[best_pair[1]]]

        if pt_dist < 1:
            continue

        ratio = real_m / pt_dist  # meters per PDF point
        direction = _direction(end_pts[0][0], end_pts[0][1], end_pts[1][0], end_pts[1][1])

        measurements.append({
            "content": annot.content.strip(),
            "value_m": round(real_m, 4),
            "pt_distance": round(pt_dist, 2),
            "meters_per_point": round(ratio, 6),
            "direction": direction,
            "pt": {
                "x1": end_pts[0][0], "y1": end_pts[0][1],
                "x2": end_pts[1][0], "y2": end_pts[1][1],
            },
        })

    if not measurements:
        return None

    ratios = [m["meters_per_point"] for m in measurements]
    mean_ratio = sum(ratios) / len(ratios)

    # Compute variance
    if len(ratios) > 1:
        variance = sum((r - mean_ratio) ** 2 for r in ratios) / len(ratios)
        std_dev = math.sqrt(variance)
        cv_pct = (std_dev / mean_ratio) * 100 if mean_ratio > 0 else 0
    else:
        cv_pct = 0.0

    return ScaleResult(
        meters_per_point=round(mean_ratio, 6),
        source_count=len(measurements),
        variance_pct=round(cv_pct, 2),
        measurements=measurements,
    )


# ─── Coordinate conversion ────────────────────────────────────────────────────

def _pt_to_meters(x_pt: float, y_pt: float, scale: float,
                  origin_x: float, origin_y: float,
                  page_height: float) -> dict:
    """Convert PDF point coordinates to meters with Y-axis flip.

    PDF origin is top-left, Y increases downward.
    Structural origin is bottom-left, Y increases upward.
    """
    # Flip Y axis
    y_flipped = page_height - y_pt
    # Apply origin offset and scale
    x_m = round((x_pt - origin_x) * scale, 4)
    y_m = round((y_flipped - (page_height - origin_y)) * scale, 4)
    return {"x": x_m, "y": y_m}


# ─── Legend detection ─────────────────────────────────────────────────────────

def _detect_legend(annotations: list[RawAnnotation], page_width: float,
                   page_height: float) -> dict:
    """Auto-detect legend area and extract label→color mappings.

    Strategy: Look for clusters of FreeText annotations in the bottom 20%
    or left/right 15% of the page, near colored shapes.
    """
    # Define candidate legend regions
    bottom_y = page_height * 0.80  # bottom 20%
    left_x = page_width * 0.15     # left 15%
    right_x = page_width * 0.85    # right 15%

    # Find text annotations in legend regions
    legend_texts = []
    for annot in annotations:
        if annot.type not in ("FreeText", "Text"):
            continue
        cx = (annot.rect[0] + annot.rect[2]) / 2
        cy = (annot.rect[1] + annot.rect[3]) / 2
        in_bottom = cy > bottom_y
        in_left = cx < left_x
        in_right = cx > right_x
        if in_bottom or in_left or in_right:
            region = "bottom" if in_bottom else ("left" if in_left else "right")
            legend_texts.append({
                "content": annot.content.strip(),
                "rect": annot.rect,
                "cx": cx, "cy": cy,
                "region": region,
            })

    if not legend_texts:
        return {"area": "none_detected", "items": []}

    # For each legend text, find the nearest colored annotation
    non_text_annots = [a for a in annotations
                       if a.type in ("Line", "Square", "Polygon", "PolyLine", "Circle")
                       and (a.stroke_color or a.fill_color)]

    items = []
    for lt in legend_texts:
        if not lt["content"]:
            continue
        best_annot = None
        best_dist = float("inf")
        for a in non_text_annots:
            acx = (a.rect[0] + a.rect[2]) / 2
            acy = (a.rect[1] + a.rect[3]) / 2
            d = _pt_distance(lt["cx"], lt["cy"], acx, acy)
            if d < best_dist:
                best_dist = d
                best_annot = a
        if best_annot and best_dist < 100:  # within 100pt
            color = best_annot.stroke_color or best_annot.fill_color
            items.append({
                "label": lt["content"],
                "nearby_color": [round(c, 3) for c in color] if color else [],
                "nearby_color_name": _color_name(tuple(color)) if color else "",
                "nearby_type": best_annot.type,
                "distance_pt": round(best_dist, 1),
            })

    # Determine primary legend region
    regions = [lt["region"] for lt in legend_texts]
    primary = max(set(regions), key=regions.count) if regions else "unknown"

    return {
        "area": f"auto-detected {primary} region",
        "items": items,
    }


# ─── Main extraction pipeline ─────────────────────────────────────────────────

def extract_page(page: "fitz.Page", page_num: int,
                 origin: Optional[tuple] = None) -> dict:
    """Extract and structure all annotations from a single PDF page.

    Args:
        page: PyMuPDF page object
        page_num: 1-based page number
        origin: Optional (x_pt, y_pt) for coordinate origin. If None, uses
                bottom-left of page.

    Returns:
        Structured dict with all annotation data, scale, and converted coords.
    """
    page_width = page.rect.width
    page_height = page.rect.height

    # Extract raw annotations
    raw = _extract_raw_annotations(page)
    if not raw:
        return {
            "page_num": page_num,
            "page_size_pt": [round(page_width, 1), round(page_height, 1)],
            "annotation_count": 0,
            "annotations": {},
        }

    # Count by type
    type_counts = {}
    for a in raw:
        type_counts[a.type] = type_counts.get(a.type, 0) + 1

    # Compute scale factor
    scale_result = _compute_scale(raw, page_height)
    scale_factor = scale_result.meters_per_point if scale_result else None

    # Set origin
    if origin:
        origin_x, origin_y = origin
    else:
        # Default: bottom-left of page = (0, page_height) in PDF coords
        origin_x, origin_y = 0.0, page_height

    # Classify and convert annotations
    measurements = []
    lines = []
    rectangles = []
    polygons = []
    texts = []

    for annot in raw:
        # Measurements
        if ("measurement" in annot.subject.lower()
                or "length" in annot.subject.lower()
                or "dimension" in annot.subject.lower()):
            entry = {
                "content": annot.content.strip(),
                "subject": annot.subject,
            }
            real_m = _parse_measurement_value(annot.content)
            if real_m:
                entry["value_m"] = round(real_m, 4)
            if annot.vertices and len(annot.vertices) >= 2:
                v = annot.vertices
                entry["direction"] = _direction(v[0][0], v[0][1], v[-1][0], v[-1][1])
                entry["pt"] = {
                    "x1": v[0][0], "y1": v[0][1],
                    "x2": v[-1][0], "y2": v[-1][1],
                }
                if scale_factor:
                    entry["meters"] = {
                        "start": _pt_to_meters(v[0][0], v[0][1], scale_factor,
                                               origin_x, origin_y, page_height),
                        "end": _pt_to_meters(v[-1][0], v[-1][1], scale_factor,
                                             origin_x, origin_y, page_height),
                    }
            measurements.append(entry)
            continue

        # Lines
        if annot.type == "Line" or (annot.type == "PolyLine" and len(annot.vertices) == 2):
            color = annot.stroke_color or annot.fill_color or []
            entry = {
                "color_rgb": [round(c, 3) for c in color] if color else [],
                "color_name": _color_name(tuple(color)) if color else "",
                "subject": annot.subject,
                "width": annot.width,
            }
            if annot.vertices and len(annot.vertices) >= 2:
                v = annot.vertices
                entry["pt"] = {
                    "x1": v[0][0], "y1": v[0][1],
                    "x2": v[1][0], "y2": v[1][1],
                }
                entry["direction"] = _direction(v[0][0], v[0][1], v[1][0], v[1][1])
                if scale_factor:
                    entry["meters"] = {
                        "start": _pt_to_meters(v[0][0], v[0][1], scale_factor,
                                               origin_x, origin_y, page_height),
                        "end": _pt_to_meters(v[1][0], v[1][1], scale_factor,
                                             origin_x, origin_y, page_height),
                    }
                    entry["length_m"] = round(
                        _pt_distance(v[0][0], v[0][1], v[1][0], v[1][1]) * scale_factor, 4)
            lines.append(entry)
            continue

        # Rectangles (Square type in PDF annotation spec)
        if annot.type in ("Square", "Rectangle"):
            color = annot.stroke_color or annot.fill_color or []
            r = annot.rect
            cx = (r[0] + r[2]) / 2
            cy = (r[1] + r[3]) / 2
            w = abs(r[2] - r[0])
            h = abs(r[3] - r[1])
            entry = {
                "color_rgb": [round(c, 3) for c in color] if color else [],
                "color_name": _color_name(tuple(color)) if color else "",
                "subject": annot.subject,
                "center_pt": [round(cx, 2), round(cy, 2)],
                "size_pt": [round(w, 2), round(h, 2)],
            }
            if scale_factor:
                entry["center_m"] = _pt_to_meters(cx, cy, scale_factor,
                                                  origin_x, origin_y, page_height)
                entry["size_m"] = [round(w * scale_factor, 4),
                                   round(h * scale_factor, 4)]
            if annot.content:
                entry["content"] = annot.content.strip()
            rectangles.append(entry)
            continue

        # Polygons
        if annot.type in ("Polygon", "PolyLine") and len(annot.vertices or []) > 2:
            color = annot.stroke_color or annot.fill_color or []
            entry = {
                "color_rgb": [round(c, 3) for c in color] if color else [],
                "color_name": _color_name(tuple(color)) if color else "",
                "subject": annot.subject,
                "vertex_count": len(annot.vertices),
                "vertices_pt": annot.vertices,
            }
            if scale_factor:
                entry["vertices_m"] = [
                    _pt_to_meters(v[0], v[1], scale_factor,
                                  origin_x, origin_y, page_height)
                    for v in annot.vertices
                ]
            if annot.content:
                entry["content"] = annot.content.strip()
            polygons.append(entry)
            continue

        # FreeText / Text
        if annot.type in ("FreeText", "Text"):
            entry = {
                "content": annot.content.strip(),
                "rect_pt": annot.rect,
            }
            if scale_factor:
                cx = (annot.rect[0] + annot.rect[2]) / 2
                cy = (annot.rect[1] + annot.rect[3]) / 2
                entry["center_m"] = _pt_to_meters(cx, cy, scale_factor,
                                                  origin_x, origin_y, page_height)
            texts.append(entry)
            continue

    # Legend detection
    legend = _detect_legend(raw, page_width, page_height)

    # Build result
    result = {
        "page_num": page_num,
        "page_size_pt": [round(page_width, 1), round(page_height, 1)],
        "annotation_count": len(raw),
        "type_counts": type_counts,
    }

    if scale_result:
        result["scale"] = {
            "meters_per_point": scale_result.meters_per_point,
            "source_count": scale_result.source_count,
            "variance_pct": scale_result.variance_pct,
        }
        if scale_result.variance_pct > 2.0:
            result["scale"]["warning"] = (
                f"High variance ({scale_result.variance_pct}%) in scale measurements. "
                "Results may be unreliable."
            )

    result["annotations"] = {
        "measurements": measurements,
        "lines": lines,
        "rectangles": rectangles,
        "polygons": polygons,
        "texts": texts,
        "legend": legend,
    }

    return result


def extract_pdf(pdf_path: str, pages: Optional[list[int]] = None,
                origin: Optional[tuple] = None) -> dict:
    """Extract annotations from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        pages: List of 1-based page numbers to extract. None = all pages.
        origin: Optional (x_pt, y_pt) coordinate origin override.

    Returns:
        Structured dict with file metadata and per-page annotation data.
    """
    pdf_path = str(Path(pdf_path).resolve())
    doc = fitz.open(pdf_path)

    result = {
        "file": Path(pdf_path).name,
        "file_path": pdf_path,
        "total_pages": doc.page_count,
        "pages": [],
    }

    target_pages = pages or list(range(1, doc.page_count + 1))

    for pn in target_pages:
        if pn < 1 or pn > doc.page_count:
            print(f"  Warning: Page {pn} out of range (1-{doc.page_count}), skipping.")
            continue

        page = doc[pn - 1]  # 0-based index
        print(f"  Extracting page {pn}/{doc.page_count}...")
        page_data = extract_page(page, pn, origin=origin)
        result["pages"].append(page_data)

    doc.close()

    # Aggregate scale from all pages
    all_scales = []
    for pd in result["pages"]:
        if "scale" in pd:
            all_scales.append(pd["scale"]["meters_per_point"])
    if all_scales:
        avg_scale = sum(all_scales) / len(all_scales)
        result["scale"] = {
            "meters_per_point": round(avg_scale, 6),
            "source_pages": len(all_scales),
        }

    return result


def has_annotations(pdf_path: str) -> bool:
    """Quick check: does the PDF have any Bluebeam annotations?

    Useful for deciding whether to use annotation-based or image-based workflow.
    """
    try:
        doc = fitz.open(str(pdf_path))
        for page in doc:
            annots = list(page.annots())
            if annots:
                doc.close()
                return True
        doc.close()
        return False
    except Exception:
        return False


def summarize(result: dict) -> str:
    """Print a human-readable summary of extraction results."""
    lines = []
    lines.append(f"File: {result['file']}")
    lines.append(f"Total pages: {result['total_pages']}")
    if "scale" in result:
        lines.append(f"Average scale: {result['scale']['meters_per_point']} m/pt "
                      f"(from {result['scale']['source_pages']} page(s))")

    for pd in result["pages"]:
        lines.append(f"\n--- Page {pd['page_num']} ---")
        lines.append(f"  Size: {pd['page_size_pt'][0]} x {pd['page_size_pt'][1]} pt")
        lines.append(f"  Annotations: {pd['annotation_count']}")
        if "type_counts" in pd:
            counts = ", ".join(f"{k}: {v}" for k, v in sorted(pd["type_counts"].items()))
            lines.append(f"  Types: {counts}")
        if "scale" in pd:
            s = pd["scale"]
            lines.append(f"  Scale: {s['meters_per_point']} m/pt "
                         f"(from {s['source_count']} measurements, "
                         f"variance {s['variance_pct']}%)")
        annots = pd.get("annotations", {})
        lines.append(f"  Measurements: {len(annots.get('measurements', []))}")
        lines.append(f"  Lines: {len(annots.get('lines', []))}")
        lines.append(f"  Rectangles: {len(annots.get('rectangles', []))}")
        lines.append(f"  Polygons: {len(annots.get('polygons', []))}")
        lines.append(f"  Texts: {len(annots.get('texts', []))}")
        legend = annots.get("legend", {})
        if legend.get("items"):
            lines.append(f"  Legend items: {len(legend['items'])}")
            for item in legend["items"]:
                lines.append(f"    - {item['label']}: {item.get('nearby_color_name', '?')} "
                             f"({item.get('nearby_type', '?')})")

    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extract Bluebeam annotations from PDF with precise coordinates."
    )
    parser.add_argument("--input", "-i", required=True,
                        help="Path to annotated PDF file")
    parser.add_argument("--pages", "-p", type=str, default=None,
                        help="Comma-separated page numbers (1-based). Default: all pages")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output JSON file path. Default: print to stdout")
    parser.add_argument("--origin", type=str, default=None,
                        help="Coordinate origin as 'x,y' in PDF points (default: bottom-left)")
    parser.add_argument("--check", action="store_true",
                        help="Only check if PDF has annotations (exit code 0=yes, 1=no)")
    parser.add_argument("--summary", action="store_true",
                        help="Print human-readable summary instead of JSON")

    args = parser.parse_args()

    pdf_path = Path(args.input)
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    # Quick check mode
    if args.check:
        if has_annotations(str(pdf_path)):
            print(f"YES: {pdf_path.name} has Bluebeam annotations.")
            sys.exit(0)
        else:
            print(f"NO: {pdf_path.name} has no annotations.")
            sys.exit(1)

    # Parse pages
    pages = None
    if args.pages:
        pages = [int(p.strip()) for p in args.pages.split(",")]

    # Parse origin
    origin = None
    if args.origin:
        parts = args.origin.split(",")
        origin = (float(parts[0].strip()), float(parts[1].strip()))

    # Extract
    print(f"Extracting annotations from: {pdf_path.name}")
    result = extract_pdf(str(pdf_path), pages=pages, origin=origin)

    # Output
    if args.summary:
        print(summarize(result))
    elif args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Output written to: {out_path}")
        print(f"\nSummary:")
        print(summarize(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
