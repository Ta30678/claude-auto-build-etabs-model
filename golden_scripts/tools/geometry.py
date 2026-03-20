"""Shared geometry utilities for outline-aware operations.

Extracted from config_build.py to allow reuse across calibration,
validation, and slab generation tools.
"""

import math


def point_in_polygon(x, y, polygon):
    """Ray-casting algorithm for point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def point_to_segment_distance(px, py, x1, y1, x2, y2):
    """Minimum distance from point to line segment."""
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-12:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def point_in_or_near_polygon(x, y, polygon, tolerance=0.01):
    """Check if point is inside polygon or within tolerance of boundary."""
    if point_in_polygon(x, y, polygon):
        return True
    for i in range(len(polygon)):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % len(polygon)]
        if point_to_segment_distance(x, y, x1, y1, x2, y2) <= tolerance:
            return True
    return False


def polygon_area(polygon):
    """Shoelace formula for polygon area."""
    n = len(polygon)
    area = 0.0
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def is_non_rectangular(polygon):
    """Check if polygon is non-rectangular (L-shaped, etc.)."""
    if not polygon or len(polygon) < 3:
        return False
    if len(polygon) != 4:
        return True
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    bbox_area = (max(xs) - min(xs)) * (max(ys) - min(ys))
    poly_area = polygon_area(polygon)
    return abs(bbox_area - poly_area) > 0.01
