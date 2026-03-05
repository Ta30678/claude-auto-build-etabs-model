"""
Comprehensive check of MERGED_ALL.e2k for missing definitions.
"""
import re
from collections import defaultdict

filepath = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_ALL_copy.e2k'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.read().split('\n')

print(f"Total lines: {len(lines)}")

# Find all section headers
sections = {}
current_section = None
section_start = 0
for i, line in enumerate(lines):
    if line.startswith('$ '):
        if current_section:
            sections[current_section] = (section_start, i-1)
        current_section = line[2:].strip()
        section_start = i
if current_section:
    sections[current_section] = (section_start, len(lines)-1)

print("\n=== SECTIONS FOUND ===")
for name, (start, end) in sorted(sections.items(), key=lambda x: x[1][0]):
    print(f"  Line {start+1}-{end+1}: {name} ({end-start} lines)")

# Check key definitions
print("\n=== DEFINITION CHECKS ===")

# 1. Materials defined
materials = set()
for line in lines:
    m = re.match(r'\s+MATERIAL\s+"([^"]+)"', line)
    if m:
        materials.add(m.group(1))
print(f"Materials defined: {len(materials)}")
for mat in sorted(materials):
    print(f"  {mat}")

# 2. Frame sections defined
frame_sections = set()
for line in lines:
    m = re.match(r'\s+FRAMESECTION\s+"([^"]+)"', line)
    if m:
        frame_sections.add(m.group(1))
print(f"\nFrame sections defined: {len(frame_sections)}")

# 3. Concrete sections defined
concrete_sections = set()
for line in lines:
    m = re.match(r'\s+CONCRETESECTION\s+"([^"]+)"', line)
    if m:
        concrete_sections.add(m.group(1))
print(f"Concrete sections defined: {len(concrete_sections)}")

all_defined_sections = frame_sections | concrete_sections

# 4. Wall/Slab/Deck sections
wall_sections = set()
slab_sections = set()
deck_sections = set()
for line in lines:
    m = re.match(r'\s+WALLPROP\s+"([^"]+)"', line)
    if m: wall_sections.add(m.group(1))
    m = re.match(r'\s+SLABPROP\s+"([^"]+)"', line)
    if m: slab_sections.add(m.group(1))
    m = re.match(r'\s+DECKPROP\s+"([^"]+)"', line)
    if m: deck_sections.add(m.group(1))
area_sections = wall_sections | slab_sections | deck_sections
print(f"Wall/Slab/Deck sections: {len(area_sections)}")

# 5. Load patterns defined
load_patterns = set()
for line in lines:
    m = re.match(r'\s+LOADPATTERN\s+"([^"]+)"', line)
    if m:
        load_patterns.add(m.group(1))
print(f"Load patterns defined: {len(load_patterns)}")

# 6. Stories defined
stories_defined = set()
for line in lines:
    m = re.match(r'\s+STORY\s+"([^"]+)"', line)
    if m:
        stories_defined.add(m.group(1))
print(f"Stories defined: {len(stories_defined)}")

# 7. Diaphragms defined
diaphragms_defined = set()
for line in lines:
    m = re.match(r'\s+DIAPHRAGM\s+"([^"]+)"', line)
    if m:
        diaphragms_defined.add(m.group(1))
print(f"Diaphragms defined: {sorted(diaphragms_defined)}")

# 8. Points defined
point_defs = set()
for line in lines:
    m = re.match(r'\s+POINT\s+"([^"]+)"', line)
    if m:
        point_defs.add(m.group(1))
print(f"Points defined: {len(point_defs)}")

# 9. Line definitions (connectivities)
line_defs = set()
line_section_refs = set()
line_point_refs = set()
for line in lines:
    m = re.match(r'\s+LINE\s+"([^"]+)"\s+(BEAM|COLUMN|BRACE)\s+"([^"]+)"\s+"([^"]+)"\s+(\d+)\s+"([^"]+)"', line)
    if m:
        label = m.group(1)
        elem_type = m.group(2)
        pt_i = m.group(3)
        pt_j = m.group(4)
        num_stories = m.group(5)
        section = m.group(6)
        line_defs.add(label)
        line_section_refs.add(section)
        line_point_refs.add(pt_i)
        line_point_refs.add(pt_j)
print(f"\nLine connectivities: {len(line_defs)}")

# 10. Area definitions
area_defs = set()
area_section_refs = set()
area_point_refs = set()
for line in lines:
    m = re.match(r'\s+AREA\s+"([^"]+)"\s+(\d+)\s+"([^"]+)"', line)
    if m:
        label = m.group(1)
        num_pts = int(m.group(2))
        section = m.group(3)
        area_defs.add(label)
        area_section_refs.add(section)
        # Extract point refs from AREA line
    # Also get points from AREA lines
    m2 = re.match(r'\s+AREA\s+"[^"]+"\s+\d+\s+"[^"]+"\s+(.*)', line)
    if m2:
        rest = m2.group(1)
        pts = re.findall(r'"([^"]+)"', rest)
        for p in pts:
            area_point_refs.add(p)
print(f"Area connectivities: {len(area_defs)}")

# === CROSS-REFERENCE CHECKS ===
print("\n=== CROSS-REFERENCE CHECKS ===")

# Check 1: Line sections vs defined sections
missing_line_sections = line_section_refs - all_defined_sections
print(f"\nLine section refs: {len(line_section_refs)}")
if missing_line_sections:
    print(f"  *** MISSING LINE SECTIONS ({len(missing_line_sections)}): {sorted(missing_line_sections)}")
else:
    print(f"  OK - all line sections defined")

# Check 2: Area sections vs defined area sections
missing_area_sections = area_section_refs - area_sections
print(f"\nArea section refs: {len(area_section_refs)}")
if missing_area_sections:
    print(f"  *** MISSING AREA SECTIONS ({len(missing_area_sections)}): {sorted(missing_area_sections)}")
else:
    print(f"  OK - all area sections defined")

# Check 3: Points in lines vs defined points
missing_points_lines = line_point_refs - point_defs
print(f"\nPoints ref'd by lines: {len(line_point_refs)}")
if missing_points_lines:
    print(f"  *** MISSING POINTS ({len(missing_points_lines)}): {sorted(list(missing_points_lines))[:30]}")
else:
    print(f"  OK - all line points defined")

# Check 4: Points in areas vs defined points
missing_points_areas = area_point_refs - point_defs
print(f"\nPoints ref'd by areas: {len(area_point_refs)}")
if missing_points_areas:
    print(f"  *** MISSING POINTS ({len(missing_points_areas)}): {sorted(list(missing_points_areas))[:30]}")
else:
    print(f"  OK - all area points defined")

# Check 5: Lines in assigns vs defined lines
line_assign_refs = set()
area_assign_refs = set()
in_section = None
for line in lines:
    if line.startswith('$ '):
        in_section = line[2:].strip()
    if 'LINEASSIGN' in line:
        m = re.match(r'\s+LINEASSIGN\s+"([^"]+)"', line)
        if m:
            line_assign_refs.add(m.group(1))
    if 'AREAASSIGN' in line:
        m = re.match(r'\s+AREAASSIGN\s+"([^"]+)"', line)
        if m:
            area_assign_refs.add(m.group(1))

missing_line_assigns = line_assign_refs - line_defs
print(f"\nLine assigns: {len(line_assign_refs)}")
if missing_line_assigns:
    print(f"  *** MISSING LINE DEFS ({len(missing_line_assigns)}): {sorted(list(missing_line_assigns))[:20]}")
else:
    print(f"  OK - all line assigns reference defined lines")

missing_area_assigns = area_assign_refs - area_defs
print(f"Area assigns: {len(area_assign_refs)}")
if missing_area_assigns:
    print(f"  *** MISSING AREA DEFS ({len(missing_area_assigns)}): {sorted(list(missing_area_assigns))[:20]}")
else:
    print(f"  OK - all area assigns reference defined areas")

# Check 6: Story references in assigns
story_refs_in_assigns = set()
for line in lines:
    m = re.search(r'STORY\s+"([^"]+)"', line)
    if m:
        s = m.group(1)
        if s not in stories_defined and not line.strip().startswith('STORY '):
            story_refs_in_assigns.add(s)

# Filter to those actually missing
actually_missing_stories = story_refs_in_assigns - stories_defined
if actually_missing_stories:
    print(f"\n*** MISSING STORY DEFS (referenced in assigns): {sorted(actually_missing_stories)}")

# Check 7: Diaphragm references
diaphragm_refs = set()
for line in lines:
    m = re.search(r'DIAPH\s+"([^"]+)"', line)
    if m:
        diaphragm_refs.add(m.group(1))
missing_diaphs = diaphragm_refs - diaphragms_defined
if missing_diaphs:
    print(f"\n*** MISSING DIAPHRAGMS: {sorted(missing_diaphs)}")

# Check 8: Material references in sections
mat_refs = set()
for line in lines:
    # FRAMESECTION or CONCRETESECTION with MATERIAL
    m = re.search(r'MATERIAL\s+"([^"]+)"', line)
    if m:
        mat_refs.add(m.group(1))
    # WALLPROP/SLABPROP with MATERIAL
    m = re.search(r'MAT\s+"([^"]+)"', line)
    if m:
        mat_refs.add(m.group(1))
missing_mats = mat_refs - materials
if missing_mats:
    print(f"\n*** MISSING MATERIALS: {sorted(missing_mats)}")

# Check 9: Load pattern references
load_refs = set()
for line in lines:
    m = re.search(r'LOADTYPE\s+"([^"]+)"', line)
    if m:
        load_refs.add(m.group(1))
    m = re.search(r'LOAD\s+"([^"]+)"\s+TYPE', line)
    if m:
        load_refs.add(m.group(1))
missing_loads = load_refs - load_patterns
if missing_loads:
    print(f"\n*** MISSING LOAD PATTERNS: {sorted(missing_loads)}")

# Check 10: Point assigns vs defined points
point_assign_refs = set()
for line in lines:
    m = re.match(r'\s+POINTASSIGN\s+"([^"]+)"', line)
    if m:
        point_assign_refs.add(m.group(1))
missing_point_assigns = point_assign_refs - point_defs
if missing_point_assigns:
    print(f"\n*** MISSING POINT DEFS (referenced in assigns): {len(missing_point_assigns)}")
    print(f"  {sorted(list(missing_point_assigns))[:20]}")

# Check 11: Look for common ETABS e2k issues
print("\n=== POTENTIAL ISSUES ===")

# Check if VERSION is compatible with ETABS 22
for line in lines:
    if 'PROGRAM' in line and 'VERSION' in line:
        print(f"Program version: {line.strip()}")
        break

# Check for UNITS consistency
for line in lines:
    if 'UNITS' in line and not line.strip().startswith('$'):
        print(f"Units: {line.strip()}")
        break

# Check format: ETABS 22 uses different e2k format than v9.7.3
print("\nIMPORTANT: File says VERSION 9.7.3 but importing into ETABS 22!")
print("ETABS 22 might need different syntax or section format.")

# Sample some section definitions to check format
print("\n=== SAMPLE FRAME SECTION DEFINITIONS ===")
count = 0
for i, line in enumerate(lines):
    if 'FRAMESECTION' in line and count < 5:
        print(f"  Line {i+1}: {line.strip()[:120]}")
        count += 1

print("\n=== SAMPLE CONCRETE SECTION DEFINITIONS ===")
count = 0
for i, line in enumerate(lines):
    if 'CONCRETESECTION' in line and count < 5:
        print(f"  Line {i+1}: {line.strip()[:120]}")
        count += 1

print("\n=== SAMPLE LINE CONNECTIVITIES ===")
count = 0
for i, line in enumerate(lines):
    if re.match(r'\s+LINE\s+".*"\s+(BEAM|COLUMN)', line) and count < 5:
        print(f"  Line {i+1}: {line.strip()[:120]}")
        count += 1

print("\n=== SAMPLE AREA CONNECTIVITIES ===")
count = 0
for i, line in enumerate(lines):
    if re.match(r'\s+AREA\s+".*"\s+\d+\s+"', line) and count < 5:
        print(f"  Line {i+1}: {line.strip()[:120]}")
        count += 1

print("\n=== SAMPLE POINT ASSIGNS ===")
count = 0
for i, line in enumerate(lines):
    if 'POINTASSIGN' in line and count < 5:
        print(f"  Line {i+1}: {line.strip()[:120]}")
        count += 1

print("\n=== SAMPLE LINE ASSIGNS ===")
count = 0
for i, line in enumerate(lines):
    if 'LINEASSIGN' in line and count < 5:
        print(f"  Line {i+1}: {line.strip()[:120]}")
        count += 1

print("\n=== SAMPLE AREA ASSIGNS ===")
count = 0
for i, line in enumerate(lines):
    if 'AREAASSIGN' in line and count < 5:
        print(f"  Line {i+1}: {line.strip()[:120]}")
        count += 1
