"""
Comprehensive e2k parser for ETABS model files.
Parses sections into structured dictionaries, handles unit conversions.
"""
import re, json, os

class E2KParser:
    """Parse an e2k file into structured sections."""

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
        'END OF MODEL FILE'
    ]

    def __init__(self, filepath):
        self.filepath = filepath
        self.sections = {}
        self.raw_sections = {}
        self.units = None  # (force_unit, length_unit)
        self.length_scale = 1.0  # multiplier to convert to meters
        self.force_scale = 1.0   # multiplier to convert to ton
        self._parse()

    def _parse(self):
        """Parse the file into raw section text blocks."""
        with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # Split by section headers
        section_pattern = re.compile(r'^\$ (.+)$', re.MULTILINE)
        matches = list(section_pattern.finditer(content))

        for i, match in enumerate(matches):
            section_name = match.group(1).strip()
            start = match.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(content)
            section_text = content[start:end].strip()
            self.raw_sections[section_name] = section_text

        # Parse CONTROLS for units
        if 'CONTROLS' in self.raw_sections:
            ctrl = self.raw_sections['CONTROLS']
            m = re.search(r'UNITS\s+"(\w+)"\s+"(\w+)"', ctrl)
            if m:
                self.units = (m.group(1), m.group(2))
                if self.units[1] == 'CM':
                    self.length_scale = 0.01  # cm -> m
                elif self.units[1] == 'MM':
                    self.length_scale = 0.001
                else:
                    self.length_scale = 1.0  # already m

                if self.units[0] == 'KGF':
                    self.force_scale = 0.001  # kgf -> ton
                elif self.units[0] == 'KN':
                    self.force_scale = 0.101972  # kN -> ton
                else:
                    self.force_scale = 1.0  # already ton

    def get_stories(self):
        """Parse story definitions. Returns list of dicts."""
        text = self.raw_sections.get('STORIES - IN SEQUENCE FROM TOP', '')
        stories = []
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('$'):
                continue
            m = re.match(r'STORY\s+"([^"]+)"\s+(.*)', line)
            if m:
                name = m.group(1)
                rest = m.group(2)
                story = {'name': name}
                # Parse HEIGHT or ELEV
                hm = re.search(r'HEIGHT\s+([\d.E+-]+)', rest)
                if hm:
                    story['height'] = float(hm.group(1)) * self.length_scale
                em = re.search(r'ELEV\s+([-\d.E+]+)', rest)
                if em:
                    story['elev'] = float(em.group(1)) * self.length_scale
                sm = re.search(r'SIMILARTO\s+"([^"]+)"', rest)
                if sm:
                    story['similar_to'] = sm.group(1)
                mm = re.search(r'MASTERSTORY\s+"([^"]+)"', rest)
                if mm:
                    story['master'] = mm.group(1)
                stories.append(story)
        return stories

    def get_story_elevations(self):
        """Calculate absolute elevations for each story. Returns dict {name: elev}."""
        stories = self.get_stories()
        # Find BASE story with ELEV
        base_elev = None
        base_idx = None
        for i, s in enumerate(stories):
            if 'elev' in s:
                base_elev = s['elev']
                base_idx = i
                break

        if base_elev is None:
            return {}

        # Stories are listed top to bottom; BASE is at the bottom
        # Work upward from BASE
        elevs = {stories[base_idx]['name']: base_elev}
        current_elev = base_elev
        for i in range(base_idx - 1, -1, -1):
            s = stories[i]
            if 'height' in s:
                current_elev += s['height']
            elevs[s['name']] = round(current_elev, 6)

        return elevs

    def get_grids(self):
        """Parse grid definitions. Returns dict {label: (dir, coord_in_m)}."""
        text = self.raw_sections.get('GRIDS', '')
        grids = {}
        for line in text.split('\n'):
            line = line.strip()
            m = re.search(r'LABEL\s+"([^"]+)"\s+DIR\s+"([^"]+)"\s+COORD\s+([-\d.E+]+)', line)
            if m:
                label = m.group(1)
                direction = m.group(2)
                coord = float(m.group(3)) * self.length_scale
                grids[label] = (direction, round(coord, 6))
        return grids

    def get_points(self):
        """Parse point coordinates. Returns dict {label: (x, y, z)} in meters."""
        text = self.raw_sections.get('POINT COORDINATES', '')
        points = {}
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            # POINT "label" X coord Y coord Z coord
            m = re.match(r'POINT\s+"([^"]+)"\s+(.*)', line)
            if m:
                label = m.group(1)
                rest = m.group(2)
                coords = {}
                for axis in ['X', 'Y', 'Z']:
                    am = re.search(rf'{axis}\s+([-\d.E+]+)', rest)
                    if am:
                        coords[axis] = float(am.group(1)) * self.length_scale
                if len(coords) == 3:
                    points[label] = (coords['X'], coords['Y'], coords['Z'])
        return points

    def get_lines(self):
        """Parse line connectivities. Returns list of dicts."""
        text = self.raw_sections.get('LINE CONNECTIVITIES', '')
        lines = []
        current_line = None
        for raw_line in text.split('\n'):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            # LINE "label" ...
            m = re.match(r'LINE\s+"([^"]+)"\s+(.*)', raw_line)
            if m:
                if current_line:
                    lines.append(current_line)
                label = m.group(1)
                rest = m.group(2)
                current_line = {'label': label, 'raw': raw_line}
                # Parse STORY
                sm = re.search(r'STORY\s+"([^"]+)"', rest)
                if sm:
                    current_line['story'] = sm.group(1)
                # Parse SECTION
                sm = re.search(r'SECTION\s+"([^"]+)"', rest)
                if sm:
                    current_line['section'] = sm.group(1)
                # Parse POINTI, POINTJ
                pm = re.search(r'POINTI\s+"([^"]+)"', rest)
                if pm:
                    current_line['point_i'] = pm.group(1)
                pm = re.search(r'POINTJ\s+"([^"]+)"', rest)
                if pm:
                    current_line['point_j'] = pm.group(1)
            elif current_line and raw_line.startswith('LINE'):
                # Continuation line for same element
                current_line['raw'] += '\n  ' + raw_line

        if current_line:
            lines.append(current_line)
        return lines

    def get_areas(self):
        """Parse area connectivities. Returns list of dicts."""
        text = self.raw_sections.get('AREA CONNECTIVITIES', '')
        areas = []
        current_area = None
        for raw_line in text.split('\n'):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            m = re.match(r'AREA\s+"([^"]+)"\s+(.*)', raw_line)
            if m:
                if current_area:
                    areas.append(current_area)
                label = m.group(1)
                rest = m.group(2)
                current_area = {'label': label, 'raw': raw_line}
                sm = re.search(r'STORY\s+"([^"]+)"', rest)
                if sm:
                    current_area['story'] = sm.group(1)
                sm = re.search(r'SECTION\s+"([^"]+)"', rest)
                if sm:
                    current_area['section'] = sm.group(1)
            elif current_area and raw_line.startswith('AREA'):
                current_area['raw'] += '\n  ' + raw_line

        if current_area:
            areas.append(current_area)
        return areas

    def get_section_by_story(self, section_name, story_list):
        """Get raw lines from a section that reference specific stories."""
        text = self.raw_sections.get(section_name, '')
        story_set = set(story_list)
        matching = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Check if this line references any of the target stories
            sm = re.search(r'STORY\s+"([^"]+)"', line)
            if sm and sm.group(1) in story_set:
                matching.append(line)
            elif not sm:
                # Lines without STORY might be global or continuation
                matching.append(line)
        return matching

    def get_raw_lines_for_stories(self, section_name, target_stories):
        """Extract raw lines from multi-line records that belong to target stories."""
        text = self.raw_sections.get(section_name, '')
        if not text:
            return []

        story_set = set(target_stories)
        records = []
        current_record = []
        current_story = None

        for line in text.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue

            # Check if this starts a new record (typically starts with a keyword like LINE, AREA, POINT)
            sm = re.search(r'STORY\s+"([^"]+)"', stripped)
            if sm:
                current_story = sm.group(1)

            # Check for element name patterns
            elem_match = re.match(r'(LINE|AREA|POINT|LINELOAD|AREALOAD)\s+"([^"]+)"', stripped)
            if elem_match:
                if current_record and current_story in story_set:
                    records.extend(current_record)
                current_record = [stripped]
                if sm:
                    current_story = sm.group(1)
            else:
                current_record.append(stripped)

        if current_record and current_story in story_set:
            records.extend(current_record)

        return records

    def get_all_raw_sections(self):
        """Return all raw sections."""
        return self.raw_sections


def compute_below_1f_stories():
    """Return list of story names at 1F and below."""
    return ['1F', 'B1F', 'B2F', 'B3F', 'B4F', 'B5F', 'B6F', 'BASE']


def compute_above_1mf_stories():
    """Return list of story names at 1MF and above."""
    return ['1MF', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F',
            '11F', '12F', '13F', '14F', '15F', '16F', '17F', '18F', '19F', '20F',
            '21F', '22F', '23F', '24F', '25F', '26F', '27F', '28F', '29F', '30F',
            '31F', '32F', '33F', '34F', 'R1F', 'R2F', 'R3F', 'PRF']


if __name__ == '__main__':
    base = "C:/Users/User/Desktop/V22 AGENTIC MODEL/ETABS REF/大陳"

    # Test with OLD model
    parser = E2KParser(f"{base}/ALL/OLD/2025-1111_ALL_BUT RC_KpKvKw.e2k")
    print(f"Units: {parser.units}")
    print(f"Length scale: {parser.length_scale}")

    stories = parser.get_stories()
    print(f"\nStories ({len(stories)}):")
    for s in stories[:5]:
        print(f"  {s}")

    elevs = parser.get_story_elevations()
    print(f"\nStory elevations:")
    for name, elev in sorted(elevs.items(), key=lambda x: x[1]):
        print(f"  {name:6s}: {elev:8.2f}m")

    points = parser.get_points()
    print(f"\nTotal points: {len(points)}")

    lines = parser.get_lines()
    print(f"Total lines: {len(lines)}")

    areas = parser.get_areas()
    print(f"Total areas: {len(areas)}")

    # Count by story
    below_1f = compute_below_1f_stories()
    above_1mf = compute_above_1mf_stories()

    below_lines = [l for l in lines if l.get('story') in below_1f]
    above_lines = [l for l in lines if l.get('story') in above_1mf]
    print(f"\nLines below 1F: {len(below_lines)}")
    print(f"Lines above 1MF: {len(above_lines)}")

    below_areas = [a for a in areas if a.get('story') in below_1f]
    above_areas = [a for a in areas if a.get('story') in above_1mf]
    print(f"Areas below 1F: {len(below_areas)}")
    print(f"Areas above 1MF: {len(above_areas)}")
