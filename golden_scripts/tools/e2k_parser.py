"""
General-purpose e2k parser for ETABS model files.
Refactored from scripts/e2k_parser.py — project-agnostic, no hardcoded paths.

Usage:
    from golden_scripts.tools.e2k_parser import E2KModel
    model = E2KModel.from_file("path/to/model.e2k")
    print(model.units)          # ('TON', 'M')
    print(model.stories)        # [{'name': 'PRF', 'height': 3.5}, ...]
    print(len(model.points))    # number of points
"""
import re
from collections import OrderedDict

from golden_scripts.tools.unit_converter import detect_units


# Canonical section order in e2k files
SECTION_ORDER = [
    'PROGRAM INFORMATION', 'CONTROLS', 'STORIES - IN SEQUENCE FROM TOP',
    'DIAPHRAGM NAMES', 'GRIDS', 'MATERIAL PROPERTIES', 'FRAME SECTIONS',
    'AUTO SELECT SECTION LISTS', 'REBAR DEFINITIONS', 'CONCRETE SECTIONS',
    'WALL/SLAB/DECK PROPERTIES', 'LINK PROPERTIES', 'PIER/SPANDREL NAMES',
    'POINT COORDINATES', 'LINE CONNECTIVITIES', 'AREA CONNECTIVITIES',
    'POINT ASSIGNS', 'LINE ASSIGNS', 'AREA ASSIGNS',
    'STATIC LOADS', 'AREA OBJECT LOADS',
    'ANALYSIS OPTIONS', 'FUNCTIONS', 'RESPONSE SPECTRUM CASES',
    'LOAD COMBINATIONS', 'STEEL DESIGN PREFERENCES',
    'CONCRETE DESIGN PREFERENCES', 'CONCRETE DESIGN OVERWRITES',
    'COMPOSITE DESIGN PREFERENCES', 'WALL DESIGN PREFERENCES',
    'SPECIAL SEISMIC DATA', 'DIMENSION LINES', 'DEVELOPED ELEVATIONS', 'LOG',
    'END OF MODEL FILE',
]


class E2KModel:
    """Parsed representation of an e2k file.

    Attributes:
        raw_sections: OrderedDict {section_name: raw_text}
        units: (force_unit, length_unit) e.g. ('TON', 'M')
        filepath: source file path (or None)
    """

    def __init__(self):
        self.raw_sections = OrderedDict()
        self.units = ('TON', 'M')
        self.filepath = None
        # Cached parsed data (lazy)
        self._stories = None
        self._story_elevations = None
        self._points = None
        self._lines = None
        self._areas = None
        self._diaphragms = None

    @classmethod
    def from_file(cls, filepath):
        """Parse an e2k file into an E2KModel."""
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        model = cls.from_text(content)
        model.filepath = filepath
        return model

    @classmethod
    def from_text(cls, content):
        """Parse e2k text content into an E2KModel."""
        model = cls()
        model.raw_sections = _split_sections(content)
        model.units = detect_units(content)
        return model

    def invalidate_cache(self):
        """Clear cached parsed data (call after modifying raw_sections)."""
        self._stories = None
        self._story_elevations = None
        self._points = None
        self._lines = None
        self._areas = None
        self._diaphragms = None

    # ── Stories ──────────────────────────────────────────────

    @property
    def stories(self):
        """List of story dicts (top to bottom order as in e2k)."""
        if self._stories is None:
            self._stories = _parse_stories(
                self.raw_sections.get('STORIES - IN SEQUENCE FROM TOP', ''))
        return self._stories

    @property
    def story_names(self):
        """List of story names (top to bottom)."""
        return [s['name'] for s in self.stories]

    @property
    def story_elevations(self):
        """Dict {story_name: absolute_elevation}."""
        if self._story_elevations is None:
            self._story_elevations = _calc_story_elevations(self.stories)
        return self._story_elevations

    # ── Points ──────────────────────────────────────────────

    @property
    def points(self):
        """Dict {label: (x, y)} in file units."""
        if self._points is None:
            self._points = _parse_points(
                self.raw_sections.get('POINT COORDINATES', ''))
        return self._points

    # ── Lines (Frames) ──────────────────────────────────────

    @property
    def lines(self):
        """List of line connectivity dicts."""
        if self._lines is None:
            self._lines = _parse_lines(
                self.raw_sections.get('LINE CONNECTIVITIES', ''))
        return self._lines

    # ── Areas ───────────────────────────────────────────────

    @property
    def areas(self):
        """List of area connectivity dicts."""
        if self._areas is None:
            self._areas = _parse_areas(
                self.raw_sections.get('AREA CONNECTIVITIES', ''))
        return self._areas

    # ── Diaphragm Names ─────────────────────────────────────

    @property
    def diaphragm_names(self):
        """List of diaphragm name strings defined in the model."""
        if self._diaphragms is None:
            self._diaphragms = _parse_diaphragm_names(
                self.raw_sections.get('DIAPHRAGM NAMES', ''))
        return self._diaphragms

    # ── Assign Queries ──────────────────────────────────────

    def get_assigns(self, section_name, keyword=None):
        """Get all assignment lines from a section.

        Args:
            section_name: e.g. 'LINE ASSIGNS', 'AREA ASSIGNS', 'POINT ASSIGNS'
            keyword: optional filter (e.g. 'LINEASSIGN', 'AREAASSIGN')

        Returns: list of raw line strings
        """
        text = self.raw_sections.get(section_name, '')
        result = []
        for line in text.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue
            if keyword and not stripped.startswith(keyword):
                continue
            result.append(stripped)
        return result

    def get_element_labels_by_story(self, section_name, target_stories, keyword):
        """Get set of element labels assigned to target stories.

        Args:
            section_name: e.g. 'LINE ASSIGNS'
            target_stories: set of story names
            keyword: e.g. 'LINEASSIGN'

        Returns: set of element label strings
        """
        text = self.raw_sections.get(section_name, '')
        labels = set()
        for line in text.split('\n'):
            stripped = line.strip()
            m = re.match(rf'{keyword}\s+"([^"]+)"\s+"([^"]+)"', stripped)
            if m and m.group(2) in target_stories:
                labels.add(m.group(1))
        return labels

    def get_diaphragm_assignments(self):
        """Get diaphragm assignments from AREA ASSIGNS.

        Returns: dict {(element_label, story): diaphragm_name}
        """
        text = self.raw_sections.get('AREA ASSIGNS', '')
        assignments = {}
        for line in text.split('\n'):
            stripped = line.strip()
            m = re.match(
                r'AREAASSIGN\s+"([^"]+)"\s+"([^"]+)".*?DIAPHRAGM\s+"([^"]+)"',
                stripped)
            if m:
                assignments[(m.group(1), m.group(2))] = m.group(3)
        return assignments

    def get_section_names_used(self):
        """Get set of all section names referenced in LINE/AREA ASSIGNS."""
        sections = set()
        for sec_key in ['LINE ASSIGNS', 'AREA ASSIGNS']:
            text = self.raw_sections.get(sec_key, '')
            for m in re.finditer(r'SECTION\s+"([^"]+)"', text):
                sections.add(m.group(1))
        return sections

    def get_material_names_used(self):
        """Get set of all material names referenced in FRAME/AREA SECTIONS."""
        materials = set()
        for sec_key in ['FRAME SECTIONS', 'WALL/SLAB/DECK PROPERTIES']:
            text = self.raw_sections.get(sec_key, '')
            for m in re.finditer(r'MATERIAL\s+"([^"]+)"', text):
                materials.add(m.group(1))
        return materials

    def get_frame_section_names_defined(self):
        """Get set of frame section names defined in FRAME SECTIONS."""
        text = self.raw_sections.get('FRAME SECTIONS', '')
        return set(re.findall(r'FRAMESECTION\s+"([^"]+)"', text))

    def get_area_section_names_defined(self):
        """Get set of area section names defined in WALL/SLAB/DECK PROPERTIES."""
        text = self.raw_sections.get('WALL/SLAB/DECK PROPERTIES', '')
        names = set()
        for m in re.finditer(r'(?:SHELLPROP|WALLPROP|DECKPROP)\s+"([^"]+)"', text):
            names.add(m.group(1))
        return names

    def get_material_names_defined(self):
        """Get set of material names defined in MATERIAL PROPERTIES."""
        text = self.raw_sections.get('MATERIAL PROPERTIES', '')
        return set(re.findall(r'MATERIAL\s+"([^"]+)"', text))


# ── Internal parsing functions ──────────────────────────────


def _split_sections(content):
    """Split e2k text into OrderedDict of {section_name: raw_text}."""
    sections = OrderedDict()
    pattern = re.compile(r'^\$\s+(.+)$', re.MULTILINE)
    matches = list(pattern.finditer(content))

    # Capture header before first $
    if matches:
        header = content[:matches[0].start()].strip()
        if header:
            sections['__HEADER__'] = header

    for i, match in enumerate(matches):
        section_name = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sections[section_name] = content[start:end].rstrip()

    return sections


def _parse_stories(text):
    """Parse STORIES section into list of dicts."""
    stories = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('$'):
            continue
        m = re.match(r'STORY\s+"([^"]+)"\s+(.*)', line)
        if m:
            story = {'name': m.group(1)}
            rest = m.group(2)
            hm = re.search(r'HEIGHT\s+([\d.E+-]+)', rest)
            if hm:
                story['height'] = float(hm.group(1))
            em = re.search(r'ELEV\s+([-\d.E+]+)', rest)
            if em:
                story['elev'] = float(em.group(1))
            sm = re.search(r'SIMILARTO\s+"([^"]+)"', rest)
            if sm:
                story['similar_to'] = sm.group(1)
            mm = re.search(r'MASTERSTORY\s+"([^"]+)"', rest)
            if mm:
                story['master'] = mm.group(1)
            stories.append(story)
    return stories


def _calc_story_elevations(stories):
    """Calculate absolute elevations from parsed stories list."""
    base_elev = None
    base_idx = None
    for i, s in enumerate(stories):
        if 'elev' in s:
            base_elev = s['elev']
            base_idx = i
            break

    if base_elev is None:
        return {}

    elevs = {stories[base_idx]['name']: base_elev}
    current_elev = base_elev
    for i in range(base_idx - 1, -1, -1):
        s = stories[i]
        if 'height' in s:
            current_elev += s['height']
        elevs[s['name']] = round(current_elev, 6)

    return elevs


def _parse_points(text):
    """Parse POINT COORDINATES. Returns dict {label: (x, y)}."""
    points = {}
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'POINT\s+"([^"]+)"\s+([-\d.E+]+)\s+([-\d.E+]+)', line)
        if m:
            points[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return points


def _parse_lines(text):
    """Parse LINE CONNECTIVITIES. Returns list of dicts."""
    lines = []
    for raw_line in text.split('\n'):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        m = re.match(r'LINE\s+"([^"]+)"\s+(\w+)\s+"([^"]+)"\s+"([^"]+)"\s+(\d+)', raw_line)
        if m:
            lines.append({
                'label': m.group(1),
                'type': m.group(2),   # BEAM, COLUMN, BRACE, etc.
                'point_i': m.group(3),
                'point_j': m.group(4),
                'num_stations': int(m.group(5)),
                'raw': raw_line,
            })
    return lines


def _parse_areas(text):
    """Parse AREA CONNECTIVITIES. Returns list of dicts."""
    areas = []
    for raw_line in text.split('\n'):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        m = re.match(r'AREA\s+"([^"]+)"\s+(\w+)\s+(\d+)\s+(.*)', raw_line)
        if m:
            label = m.group(1)
            area_type = m.group(2)
            num_pts = int(m.group(3))
            rest = m.group(4)
            # Extract point labels
            point_labels = re.findall(r'"([^"]+)"', rest)
            areas.append({
                'label': label,
                'type': area_type,
                'num_points': num_pts,
                'point_labels': point_labels[:num_pts],
                'raw': raw_line,
            })
    return areas


def _parse_diaphragm_names(text):
    """Parse DIAPHRAGM NAMES section. Returns list of name strings."""
    names = []
    for line in text.split('\n'):
        line = line.strip()
        m = re.match(r'DIAPHRAGM\s+"([^"]+)"', line)
        if m:
            names.append(m.group(1))
    return names


# ── Utility: filter raw lines ───────────────────────────────


def filter_raw_lines(text, target_labels, keyword):
    """Filter raw e2k text lines by element label.

    Args:
        text: raw section text
        target_labels: set of labels to keep
        keyword: line prefix (e.g. 'LINE', 'AREA', 'LINEASSIGN')

    Returns: list of matching raw line strings
    """
    result = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(rf'{keyword}\s+"([^"]+)"', stripped)
        if m and m.group(1) in target_labels:
            result.append(stripped)
        elif not m and not stripped.startswith(keyword):
            # Non-element lines (e.g., LOADCASE definitions) — keep
            result.append(stripped)
    return result


def filter_raw_lines_by_story(text, target_stories, keyword):
    """Filter raw lines by story name.

    Args:
        text: raw section text
        target_stories: set of story names to keep
        keyword: line prefix (e.g. 'LINEASSIGN', 'AREAASSIGN')

    Returns: list of matching raw line strings
    """
    result = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(rf'{keyword}\s+"[^"]+"\s+"([^"]+)"', stripped)
        if m and m.group(1) in target_stories:
            result.append(stripped)
    return result


def get_point_labels_from_connectivities(line_records, area_records):
    """Extract all point labels referenced by line and area connectivity records.

    Args:
        line_records: list of raw LINE connectivity strings
        area_records: list of raw AREA connectivity strings

    Returns: set of point label strings
    """
    points = set()
    for line in line_records:
        # LINE "label" TYPE "pi" "pj" N
        for m in re.finditer(r'"([^"]+)"', line):
            pass  # grab all quoted strings
        # More precise: extract POINTI and POINTJ
        parts = re.findall(r'"([^"]+)"', line)
        if len(parts) >= 3:
            points.add(parts[1])  # point_i
            points.add(parts[2])  # point_j

    for area_line in area_records:
        parts = re.findall(r'"([^"]+)"', area_line)
        if len(parts) >= 2:
            # First is area label, rest before trailing numbers are point labels
            m = re.match(r'AREA\s+"[^"]+"\s+\w+\s+(\d+)\s+(.*)', area_line)
            if m:
                num_pts = int(m.group(1))
                pt_labels = re.findall(r'"([^"]+)"', m.group(2))
                for pl in pt_labels[:num_pts]:
                    points.add(pl)

    return points
