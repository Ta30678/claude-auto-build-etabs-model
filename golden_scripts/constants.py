"""
Shared constants for Golden Scripts.
All deterministic values that were previously re-derived by AI each session.

Story classification functions (see skills/structural-glossary/SKILL.md):
  is_substructure_story(name)   — B*F, 1F, BASE
  is_superstructure_story(name) — 1MF, 2F~RF (excludes rooftop)
  is_rooftop_story(name)        — R*F, PRF
"""
import re

# ── Unit System ──────────────────────────────────────────────
UNITS_TON_M = 12  # eUnits code for TON/M

# ── Material Types (eMatType) ────────────────────────────────
MATTYPE_STEEL = 1
MATTYPE_CONCRETE = 2
MATTYPE_REBAR = 6       # NOT 5 (5 = ColdFormed)

# ── Concrete Material Properties (in TON/M units) ───────────
CONCRETE_GRADES = [280, 315, 350, 420, 490]

CONCRETE_PROPS = {
    280: {"E": 2.50e6, "nu": 0.2, "thermal": 1e-5, "wt": 2.4, "fc_tonm2": 2800},
    315: {"E": 2.65e6, "nu": 0.2, "thermal": 1e-5, "wt": 2.4, "fc_tonm2": 3150},
    350: {"E": 2.80e6, "nu": 0.2, "thermal": 1e-5, "wt": 2.4, "fc_tonm2": 3500},
    420: {"E": 3.06e6, "nu": 0.2, "thermal": 1e-5, "wt": 2.4, "fc_tonm2": 4200},
    490: {"E": 3.31e6, "nu": 0.2, "thermal": 1e-5, "wt": 2.4, "fc_tonm2": 4900},
}

REBAR_PROPS = {
    "SD420": {"E": 2.04e7, "nu": 0.3, "Fy": 42000, "Fu": 63000},
    "SD490": {"E": 2.04e7, "nu": 0.3, "Fy": 49000, "Fu": 73500},
}

# ── Section Expansion ───────────────────────────────────────
EXPAND_RANGE = 20   # cm
EXPAND_STEP = 5     # cm
MIN_BEAM_W = 25     # cm
MIN_BEAM_D = 40     # cm
MIN_COL_DIM = 30    # cm

# ── Stiffness Modifiers ─────────────────────────────────────
# Frame: [Area, As2, As3, Torsion, I22, I33, Mass, Weight]
BEAM_MODIFIERS = [1, 1, 1, 0.0001, 0.7, 0.7, 0.8, 0.8]
COL_MODIFIERS  = [1, 1, 1, 0.0001, 0.7, 0.7, 0.95, 0.95]

# Area: [f11, f22, f12, m11, m22, m12, v13, v23, Mass, Weight]
SLAB_WALL_MODIFIERS = [0.4, 0.4, 0.4, 1, 1, 1, 1, 1, 1, 1]
RAFT_MODIFIERS      = [0.4, 0.4, 0.4, 0.7, 0.7, 0.7, 1, 1, 1, 1]

# ── Shell Types ──────────────────────────────────────────────
SHELL_MEMBRANE = 2    # Slab, Wall
SHELL_THICK = 1       # Raft (FS)

# ── Rebar Constants ──────────────────────────────────────────
BEAM_COVER_TOP = 0.09       # 9 cm
BEAM_COVER_BOT = 0.09       # 9 cm
FB_COVER_TOP = 0.11          # 11 cm (foundation beam)
FB_COVER_BOT = 0.15          # 15 cm (foundation beam)
COL_COVER = 0.07             # 7 cm
COL_CORNER_BARS = 4
COL_TIE_SPACING = 0.15       # 15 cm
COL_REBAR_SIZE = "#8"
COL_TIE_SIZE = "#4"
COL_NUM_2DIR_TIE = 2
COL_NUM_3DIR_TIE = 2

# ── Rigid Zone ───────────────────────────────────────────────
RIGID_ZONE_FACTOR = 0.75

# ── End Release Arrays ───────────────────────────────────────
# [P, V2, V3, T, M2, M3]
RELEASE_M2M3 = [False, False, False, False, True, True]
NO_RELEASE   = [False, False, False, False, False, False]
ZERO_SPRINGS = [0.0] * 6

# ── Foundation ───────────────────────────────────────────────
BASE_RESTRAINT = [True, True, False, False, False, False]  # UX, UY only

# ── Iteration Thresholds ──────────────────────────────────
COL_REBAR_DOWNSIZE = 0.01    # = 1% (ETABS code minimum) -> downsize
COL_REBAR_MAX = 0.04         # > 4% -> upsize
COL_RESIZE_STEP = 10         # cm (both W and D)

BEAM_REBAR_MIN = 0.01        # < 1% -> downsize
BEAM_REBAR_MAX = 0.02        # > 2% -> upsize
BEAM_RESIZE_STEP = 5         # cm
BEAM_MAX_WIDTH_RATIO = 1.2   # W <= 1.2*D, then switch to D increase

MAX_ITERATIONS = 5
DESIGN_CODE = "ACI 318-19"
ITER_SKIP_PREFIXES = ["FB", "FSB", "FWB"]  # foundation beams excluded

# ── Sway Frame Types (ACI318_19.SetOverwrite Item=1) ─────
SWAY_SPECIAL = 1   # Value 1 = Sway Special
SWAY_ORDINARY = 3  # Value 3 = Sway Ordinary

# ── Design Load Combinations (fixed) ─────────────────────
SUPER_COMBOS = ["USS01", "USS02"] + [f"USS{i}S" for i in range(68, 84)]  # 18 combos
SUB_COMBOS = [f"BUSS{i:02d}" for i in range(1, 68)]  # 67 combos

# ── Default Loads (ton/m2) ───────────────────────────────────
# FS DL = 2.4(gamma_c) * 0.2(BS slab 20cm, not modeled) + 0.15(substructure DL) = 0.63
# BS slab sits above FS at foundation level; only its weight is considered, not strength.
# SDL is NEVER created. All additional dead loads use DL pattern.
DEFAULT_LOADS = {
    "superstructure": {"DL": 0.45, "LL": 0.2},    # 2F~RF
    "rooftop":        {"DL": 0.45, "LL": 0.3},    # R1F~PRF
    "substructure":   {"DL": 0.15, "LL": 0.5},    # B_F~1F
    "1F_indoor":      {"DL": 0.3,  "LL": 0.5},
    "1F_outdoor":     {"DL": 0.6,  "LL": 1.0},
    "FS":             {"DL": 0.63, "LL": 0},
}

# ── Load Patterns ────────────────────────────────────────────
STANDARD_LOAD_PATTERNS = [
    ("DL",   1, 1),    # Dead with self-weight=1
    ("LL",   3, 0),    # Live
    ("EQXP", 5, 0),    # Seismic +X
    ("EQXN", 5, 0),    # Seismic -X
    ("EQYP", 5, 0),    # Seismic +Y
    ("EQYN", 5, 0),    # Seismic -Y
]

# ── Exterior Wall Defaults ───────────────────────────────────
EXT_WALL_THICKNESS = 0.15     # m
EXT_WALL_UNIT_WEIGHT = 2.4    # ton/m3
EXT_WALL_OPENING_FACTOR = 0.6


# ── Parsing Utilities ────────────────────────────────────────

def parse_frame_section(name):
    """Parse frame section name -> (prefix, num1, num2, fc_or_None).

    Naming:
      Beams:   {PREFIX}{WIDTH}X{DEPTH}[C{fc}]  → num1=width, num2=depth
      Columns: C{DEPTH}X{WIDTH}[C{fc}]         → num1=depth, num2=width

    Use get_frame_dimensions(prefix, num1, num2) to get (width_cm, depth_cm).

    B55X80 -> ('B', 55, 80, None)     → width=55, depth=80
    B55X80C350 -> ('B', 55, 80, 350)  → width=55, depth=80
    C100X120C420 -> ('C', 100, 120, 420) → depth=100, width=120
    """
    m = re.match(r'^(B|SB|WB|FB|FSB|FWB|C)(\d+)X(\d+)(?:C(\d+))?$', name)
    if m:
        fc = int(m.group(4)) if m.group(4) else None
        return m.group(1), int(m.group(2)), int(m.group(3)), fc
    return None, None, None, None


def parse_area_section(name):
    """Parse area section name -> (prefix, thickness_cm, fc_or_None).

    S15 -> ('S', 15, None)
    S15C280 -> ('S', 15, 280)
    FS100C350 -> ('FS', 100, 350)
    """
    m = re.match(r'^(S|W|FS)(\d+)(?:C(\d+))?$', name)
    if m:
        fc = int(m.group(3)) if m.group(3) else None
        return m.group(1), int(m.group(2)), fc
    return None, None, None


def is_foundation_beam(prefix):
    """Check if a beam prefix indicates a foundation beam."""
    return prefix in ("FB", "FSB", "FWB")


def get_frame_dimensions(prefix, num1, num2):
    """Convert parsed section numbers to (width_cm, depth_cm).

    Beams:   {PREFIX}{WIDTH}X{DEPTH}  → num1=width,  num2=depth
    Columns: C{DEPTH}X{WIDTH}        → num1=depth,  num2=width

    Returns (width_cm, depth_cm) for SetRectangle(T3=depth, T2=width).
    """
    if prefix == "C":
        return num2, num1   # swap: width=second, depth=first
    return num1, num2       # beams: width=first, depth=second


def calc_column_bar_distribution(width_cm, depth_cm):
    """Calculate NumR3, NumR2 for column rebar.

    NumberR3Bars = width_cm // 10  (bars on face parallel to 3-axis, scaled by T2)
    NumberR2Bars = depth_cm // 10  (bars on face parallel to 2-axis, scaled by T3)

    Returns (num_r3, num_r2).
    """
    return width_cm // 10, depth_cm // 10


def next_story(floor_label, all_stories=None):
    """Get the story name above a given floor.
    B3F->B2F, B1F->1F, 1F->2F, RF->PRF

    If all_stories is provided (ordered bottom-to-top), use positional lookup.
    Otherwise fall back to pattern-based logic.
    """
    # If story list provided, use positional lookup
    if all_stories:
        try:
            idx = all_stories.index(floor_label)
            if idx + 1 < len(all_stories):
                return all_stories[idx + 1]
        except ValueError:
            pass  # fall through to pattern matching

    # Legacy pattern-based fallback
    m = re.match(r'^B(\d+)F$', floor_label)
    if m:
        n = int(m.group(1))
        return "1F" if n == 1 else f"B{n-1}F"

    m = re.match(r'^(\d+)F$', floor_label)
    if m:
        return f"{int(m.group(1))+1}F"

    if floor_label == "RF":
        return "PRF"

    return floor_label


def parse_story_range(range_str, all_stories):
    """Parse story range like 'B3F~1F' into list of story names.

    Args:
        range_str: e.g. 'B3F~1F' or '2F~7F' or 'RF'
        all_stories: ordered list of all story names (bottom to top)

    Returns: list of story names in range
    """
    if "~" not in range_str:
        return [range_str] if range_str in all_stories else []

    start, end = range_str.split("~", 1)
    if start not in all_stories or end not in all_stories:
        return []

    i_start = all_stories.index(start)
    i_end = all_stories.index(end)
    if i_start > i_end:
        i_start, i_end = i_end, i_start
    return all_stories[i_start:i_end + 1]


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
    range_str = range_str.replace("\uff5e", "~").replace("-", "~")  # normalize separators
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
    ms_n = re.match(r"^(\d+)F$", start)
    me_r = re.match(r"^R(\d*)F$", end)
    if ms_n and me_r:
        s = int(ms_n.group(1))
        r_num = me_r.group(1)
        result = [f"{i}F" for i in range(s, s + 1)]  # start only
        result.append(end)
        print(f"  WARNING: Cannot fully enumerate '{range_str}'; returning [{start}, {end}]")
        return result

    # Fallback
    print(f"  WARNING: Cannot expand floor range '{range_str}'; returning as-is")
    return [start, end]


def build_strength_lookup(strength_map_config, all_stories):
    """Convert config strength_map to (story, element_type) -> fc lookup.

    Args:
        strength_map_config: dict from config, e.g.
            {"B3F~1F": {"column": 490, "beam": 420, ...}, "2F~7F": {...}}
        all_stories: ordered list of all story names

    Returns: dict mapping (story_name, element_type) -> fc_grade
    """
    lookup = {}
    for range_str, grades in strength_map_config.items():
        stories = parse_story_range(range_str, all_stories)
        for story in stories:
            for elem_type, fc in grades.items():
                lookup[(story, elem_type)] = fc
    return lookup


# ── Story Classification (see skills/structural-glossary/SKILL.md) ──

SUBSTRUCTURE_PATTERNS = [
    re.compile(r'^B\d+F$'),     # B1F, B2F, ...
    re.compile(r'^1F$'),        # 1F
    re.compile(r'^BASE$'),      # BASE
]

ROOFTOP_PATTERNS = [
    re.compile(r'^R\d*F$'),     # RF, R1F, R2F, R3F, ...
    re.compile(r'^PRF$'),       # PRF
]


def is_substructure_story(name):
    """Check if story belongs to substructure (下構): B*F, 1F, BASE."""
    return any(p.match(name) for p in SUBSTRUCTURE_PATTERNS)


def is_rooftop_story(name):
    """Check if story belongs to rooftop (屋突): R*F, PRF."""
    return any(p.match(name) for p in ROOFTOP_PATTERNS)


def is_superstructure_story(name):
    """Check if story belongs to superstructure (上構): 1MF, 2F~RF (excludes rooftop)."""
    return not is_substructure_story(name) and not is_rooftop_story(name)


def classify_story(name):
    """Classify a story name. Returns 'substructure', 'superstructure', or 'rooftop'."""
    if is_substructure_story(name):
        return "substructure"
    if is_rooftop_story(name):
        return "rooftop"
    return "superstructure"


def get_above_ground_stories(story_names):
    """Filter story names to only above-ground (superstructure + rooftop).
    Used for split/merge: these are the stories that belong to individual buildings.
    """
    return [s for s in story_names if not is_substructure_story(s)]


def normalize_stories_order(stories):
    """Ensure stories are in bottom-to-top order.

    Detects whether stories are top-to-bottom or bottom-to-top
    by checking if substructure stories come first (bottom-to-top)
    or last (top-to-bottom).

    Returns stories in bottom-to-top order (B3F, B2F, ..., PRF).
    """
    if not stories or len(stories) <= 1:
        return list(stories)
    first = stories[0]["name"]
    last = stories[-1]["name"]
    # If first story is a substructure story, already bottom-to-top
    if is_substructure_story(first) and not is_substructure_story(last):
        return list(stories)
    # If last story is a substructure story, reverse to bottom-to-top
    if is_substructure_story(last) and not is_substructure_story(first):
        return list(reversed(stories))
    # Ambiguous: return as-is (assume bottom-to-top)
    return list(stories)
