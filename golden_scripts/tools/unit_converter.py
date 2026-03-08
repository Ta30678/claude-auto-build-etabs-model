"""
Unit detection and conversion for e2k files.
Supports KGF-CM, KGF-M, TON-M, KN-M and cross-conversions.
"""
import re


# ── Unit scale factors (to base: TON and M) ──────────────────
FORCE_TO_TON = {
    "KGF": 0.001,
    "TON": 1.0,
    "KN":  0.101972,   # 1 kN = 0.101972 ton
    "KIP": 0.453592,
}

LENGTH_TO_M = {
    "CM":  0.01,
    "MM":  0.001,
    "M":   1.0,
    "IN":  0.0254,
    "FT":  0.3048,
}

# Derived dimension exponents: (force_exp, length_exp)
DIMENSION_EXPONENTS = {
    "length":            (0, 1),
    "area":              (0, 2),
    "inertia":           (0, 4),
    "force":             (1, 0),
    "stress":            (1, -2),   # force/area
    "line_load":         (1, -1),   # force/length
    "area_load":         (1, -2),   # force/area (same as stress)
    "spring_stiffness":  (1, -1),   # force/length
    "rotational_spring": (1, 1),    # force*length/radian
    "moment":            (1, 1),    # force*length
}


def detect_units(content):
    """Detect force and length units from e2k CONTROLS section.

    Args:
        content: raw e2k file text

    Returns:
        (force_unit, length_unit) e.g. ("TON", "M") or ("KGF", "CM")
    """
    m = re.search(r'UNITS\s+"(\w+)"\s+"(\w+)"', content)
    if m:
        return m.group(1).upper(), m.group(2).upper()
    return "TON", "M"


def scale_factor(from_force, from_length, to_force, to_length, dimension):
    """Compute multiplicative scale factor for a given dimension.

    Args:
        from_force, from_length: source units (e.g. "KGF", "CM")
        to_force, to_length: target units (e.g. "TON", "M")
        dimension: one of DIMENSION_EXPONENTS keys

    Returns:
        float multiplier such that value_target = value_source * multiplier
    """
    f_exp, l_exp = DIMENSION_EXPONENTS[dimension]

    f_scale = FORCE_TO_TON[from_force] / FORCE_TO_TON[to_force]
    l_scale = LENGTH_TO_M[from_length] / LENGTH_TO_M[to_length]

    return (f_scale ** f_exp) * (l_scale ** l_exp)


def convert(value, from_force, from_length, to_force, to_length, dimension):
    """Convert a numeric value between unit systems.

    Args:
        value: numeric value to convert
        from_force, from_length: source units
        to_force, to_length: target units
        dimension: dimension key (see DIMENSION_EXPONENTS)

    Returns:
        converted float value
    """
    return value * scale_factor(from_force, from_length,
                                to_force, to_length, dimension)


def units_label(force, length):
    """Return human-readable unit label like 'TON-M' or 'KGF-CM'."""
    return f"{force}-{length}"
