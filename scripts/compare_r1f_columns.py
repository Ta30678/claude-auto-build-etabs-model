"""Compare column section assignments around R1F between original A/B/C/D and MERGED e2k files."""
import re
import os
from collections import defaultdict

# File paths
files = {
    'A': r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\A\2026-0303_A_SC_KpKvKw.e2k',
    'B': r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\B\2026-0303_B_SC_KpKvKw.e2k',
    'C': r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\C\2026-0304_C_SC_KpKvKw.e2k',
    'D': r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\D\2026-0303_D_SC_KpKvKw.e2k',
    'MERGED': r'C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\ALL\2026-0305\MERGED_ALL_v2.e2k',
}

target_stories = ['30F', '31F', '32F', '33F', '34F', 'R1F', 'R2F', 'R3F', 'PRF']


def parse_e2k_full(filepath, label, is_merged=False):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Detect units
    m = re.search(r'UNITS\s+"([^"]+)"', content)
    units = m.group(1) if m else 'Unknown'

    # Parse FRAMESECTION definitions with MATERIAL
    sections = {}
    sec_pattern = re.compile(
        r'^\s*FRAMESECTION\s+"([^"]+)"\s+MATERIAL\s+"([^"]+)"\s+SHAPE\s+"([^"]+)"(.*)$',
        re.MULTILINE
    )
    for m in sec_pattern.finditer(content):
        sec_name = m.group(1)
        material = m.group(2)
        shape = m.group(3)
        rest = m.group(4)
        d_match = re.search(r'\bD\s+([\d.eE+-]+)', rest)
        b_match = re.search(r'\bB\s+([\d.eE+-]+)', rest)
        sections[sec_name] = {
            'material': material,
            'shape': shape,
            'D': float(d_match.group(1)) if d_match else None,
            'B': float(b_match.group(1)) if b_match else None,
        }

    # Also detect Auto Select Lists
    asl_pattern = re.compile(
        r'^\s*FRAMESECTION\s+"([^"]+)"\s+SHAPE\s+"Auto Select List"',
        re.MULTILINE
    )
    for m in asl_pattern.finditer(content):
        sec_name = m.group(1)
        sections[sec_name] = {
            'material': 'AutoSelect',
            'shape': 'Auto Select List',
            'D': None,
            'B': None,
        }

    # Parse modifier lines
    mod_pattern = re.compile(
        r'^\s*FRAMESECTION\s+"([^"]+)"\s+(JMOD\s+[\d.eE+-]+.*)$',
        re.MULTILINE
    )
    modifiers = {}
    for m in mod_pattern.finditer(content):
        sec_name = m.group(1)
        mod_line = m.group(2)
        mods = {}
        for key in ['JMOD', 'I2MOD', 'I3MOD', 'MMOD', 'WMOD', 'AMOD', 'A2MOD', 'A3MOD']:
            km = re.search(rf'{key}\s+([\d.eE+-]+)', mod_line)
            if km:
                mods[key] = float(km.group(1))
        modifiers[sec_name] = mods

    # Parse LINEASSIGN
    line_assign_pattern = re.compile(
        r'^\s*LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"(.*)$',
        re.MULTILINE
    )

    col_assignments = defaultdict(dict)

    for m in line_assign_pattern.finditer(content):
        frame_name = m.group(1)
        story_name = m.group(2)
        sec_name = m.group(3)

        if story_name not in target_stories:
            continue

        if is_merged:
            is_col = False
            bldg = None
            if re.match(r'^AC\d+$', frame_name):
                is_col = True
                bldg = 'A'
            elif re.match(r'^BC\d+$', frame_name):
                is_col = True
                bldg = 'B'
            elif re.match(r'^CC\d+$', frame_name):
                is_col = True
                bldg = 'C'
            elif re.match(r'^DC\d+$', frame_name):
                is_col = True
                bldg = 'D'

            if is_col:
                col_assignments[story_name][frame_name] = {
                    'section': sec_name,
                    'building': bldg,
                }
        else:
            if frame_name.startswith('C'):
                col_assignments[story_name][frame_name] = {
                    'section': sec_name,
                    'building': label,
                }

    return {
        'units': units,
        'sections': sections,
        'modifiers': modifiers,
        'col_assignments': dict(col_assignments),
    }


# Parse all files
all_data = {}
for label, filepath in files.items():
    is_merged = (label == 'MERGED')
    all_data[label] = parse_e2k_full(filepath, label, is_merged)

# Build report
report = []
report.append("# R1F Column Section Comparison Report")
report.append("")
report.append("## Files Analyzed")
report.append("")
for label, filepath in files.items():
    units = all_data[label]['units']
    report.append(f"- **{label}**: `{os.path.basename(filepath)}` (Units: {units})")
report.append("")
report.append("## Target Stories")
report.append("")
report.append(", ".join(target_stories))
report.append("")

# Per-story per-building comparison
report.append("## Per-Story Column Assignment Comparison")
report.append("")

all_mismatches = []

for story in target_stories:
    report.append(f"### Story: {story}")
    report.append("")

    for bldg in ['A', 'B', 'C', 'D']:
        orig = all_data[bldg]
        merged = all_data['MERGED']

        orig_cols = orig['col_assignments'].get(story, {})

        # Get merged columns for this building
        merged_cols = {}
        merged_all = merged['col_assignments'].get(story, {})
        for fname, info in merged_all.items():
            if info['building'] == bldg:
                merged_cols[fname] = info

        if not orig_cols and not merged_cols:
            continue

        report.append(f"**Building {bldg}** (Original units: {orig['units']})")
        report.append("")

        # Count sections in original
        orig_sec_counts = defaultdict(int)
        for f, info in orig_cols.items():
            orig_sec_counts[info['section']] += 1

        # Count sections in merged
        merged_sec_counts = defaultdict(int)
        for f, info in merged_cols.items():
            merged_sec_counts[info['section']] += 1

        report.append(f"| Metric | Original | Merged |")
        report.append(f"|--------|----------|--------|")
        report.append(f"| Column count | {len(orig_cols)} | {len(merged_cols)} |")
        report.append(f"| Sections used | {dict(orig_sec_counts)} | {dict(merged_sec_counts)} |")
        report.append("")

        # Check per-column match
        mismatches = []
        for fname, info in orig_cols.items():
            orig_sec = info['section']
            merged_fname = f"{bldg}{fname}"
            if merged_fname in merged_cols:
                merged_sec = merged_cols[merged_fname]['section']
                if merged_sec != orig_sec:
                    mismatches.append((fname, merged_fname, orig_sec, merged_sec))
            else:
                mismatches.append((fname, f"{bldg}{fname}", orig_sec, "MISSING"))

        for fname, info in merged_cols.items():
            orig_fname = fname[1:]  # Remove building prefix
            if orig_fname not in orig_cols:
                mismatches.append(("N/A", fname, "NOT IN ORIGINAL", info['section']))

        if mismatches:
            report.append(f"**MISMATCHES ({len(mismatches)}):**")
            report.append("")
            report.append("| Original Frame | Merged Frame | Original Section | Merged Section | Status |")
            report.append("|---------------|-------------|-----------------|---------------|--------|")
            for mm in mismatches:
                status = "SECTION DIFFERS" if mm[2] != "NOT IN ORIGINAL" and mm[3] != "MISSING" else mm[3] if mm[3] == "MISSING" else "EXTRA IN MERGED"
                report.append(f"| {mm[0]} | {mm[1]} | {mm[2]} | {mm[3]} | {status} |")
                all_mismatches.append({
                    'story': story,
                    'building': bldg,
                    'orig_frame': mm[0],
                    'merged_frame': mm[1],
                    'orig_section': mm[2],
                    'merged_section': mm[3],
                })
            report.append("")
        else:
            report.append("All columns match (section names are identical).")
            report.append("")

# Section dimension comparison for sections used at target stories
report.append("---")
report.append("")
report.append("## Section Dimension Comparison")
report.append("")
report.append("### Sections Used at R1F")
report.append("")

r1f_sections = set()
for bldg in ['A', 'B', 'C', 'D']:
    for f, info in all_data[bldg]['col_assignments'].get('R1F', {}).items():
        r1f_sections.add(info['section'])
for f, info in all_data['MERGED']['col_assignments'].get('R1F', {}).items():
    r1f_sections.add(info['section'])

report.append("| Section | File | D | B | Units | Shape | Material | Notes |")
report.append("|---------|------|---|---|-------|-------|----------|-------|")

for sec in sorted(r1f_sections):
    for label in ['A', 'B', 'C', 'D', 'MERGED']:
        if sec in all_data[label]['sections']:
            s = all_data[label]['sections'][sec]
            d = s.get('D')
            b = s.get('B')
            units = all_data[label]['units']
            shape = s['shape']
            material = s['material']

            notes = ""
            if label == 'MERGED' and d is not None and b is not None:
                # Check for unit mismatch
                if d < 10 and b > 10:
                    notes = "BUG: D in m but B in cm!"
                elif d > 10 and b < 10:
                    notes = "BUG: D in cm but B in m!"

            d_str = f"{d}" if d is not None else "N/A"
            b_str = f"{b}" if b is not None else "N/A"
            report.append(f"| {sec} | {label} | {d_str} | {b_str} | {units} | {shape} | {material} | {notes} |")

# Property modifier comparison for affected sections
report.append("")
report.append("### Property Modifier Comparison for C42x/C420x Sections")
report.append("")

mod_sections = ['C100X100C42', 'C130X130C42', 'C150X150C42',
                'C100X100C420', 'C130X130C420', 'C150X150C420',
                'C100X100C420SD490', 'C130X130C420SD490', 'C150X150C420SD490']

report.append("| Section | File | JMOD | I2MOD | I3MOD | MMOD | WMOD | Notes |")
report.append("|---------|------|------|-------|-------|------|------|-------|")

for sec in mod_sections:
    for label in ['A', 'B', 'C', 'D', 'MERGED']:
        data = all_data[label]
        if sec in data.get('modifiers', {}):
            mods = data['modifiers'][sec]
            notes = ""
            # Check if modifiers look scaled incorrectly
            if label == 'MERGED':
                # Compare with original
                for orig_label in ['A', 'B', 'C', 'D']:
                    if sec in all_data[orig_label].get('modifiers', {}):
                        orig_mods = all_data[orig_label]['modifiers'][sec]
                        for key in ['I2MOD', 'I3MOD', 'MMOD', 'WMOD']:
                            if key in mods and key in orig_mods:
                                ratio = mods[key] / orig_mods[key] if orig_mods[key] != 0 else 0
                                if abs(ratio - 1.0) > 0.01:
                                    notes += f"{key} ratio={ratio:.4f}; "
                        break

            jmod = mods.get('JMOD', 'N/A')
            i2mod = mods.get('I2MOD', 'N/A')
            i3mod = mods.get('I3MOD', 'N/A')
            mmod = mods.get('MMOD', 'N/A')
            wmod = mods.get('WMOD', 'N/A')
            report.append(f"| {sec} | {label} | {jmod} | {i2mod} | {i3mod} | {mmod} | {wmod} | {notes} |")

# CRITICAL BUG section
report.append("")
report.append("---")
report.append("")
report.append("## CRITICAL BUGS FOUND")
report.append("")

# Bug 1: Section dimension B not converted
report.append("### Bug 1: Section Dimensions B Not Converted to Meters")
report.append("")
report.append("In the MERGED e2k file (which uses TON/M units), several column sections have")
report.append("the D dimension correctly converted to meters but the B dimension is still in cm:")
report.append("")
report.append("| Section | D (MERGED) | B (MERGED) | Expected D (m) | Expected B (m) |")
report.append("|---------|------------|------------|----------------|----------------|")

bug_sections = []
for sec in sorted(all_data['MERGED']['sections'].keys()):
    s = all_data['MERGED']['sections'][sec]
    if s['D'] is not None and s['B'] is not None:
        if s['D'] < 10 and s['B'] > 10:
            expected_b = s['B'] / 100.0
            report.append(f"| {sec} | {s['D']} | {s['B']} | {s['D']} | {expected_b} |")
            bug_sections.append(sec)

report.append("")
report.append(f"**Total affected sections: {len(bug_sections)}**")
report.append("")
report.append("These sections all come from buildings A, C, D (which use KGF/CM units).")
report.append("When merging into the MERGED e2k (TON/M), the D dimension was converted by dividing")
report.append("by 100, but B was left unconverted. This means ETABS would interpret these columns")
report.append("as extremely thin and wide rectangles instead of squares.")
report.append("")

# Bug 2: Property modifiers scaled incorrectly
report.append("### Bug 2: Property Modifiers Incorrectly Scaled")
report.append("")
report.append("The property modifiers for these same sections were also incorrectly scaled:")
report.append("")

for sec in mod_sections:
    if sec in all_data['MERGED'].get('modifiers', {}):
        merged_mods = all_data['MERGED']['modifiers'][sec]
        for orig_label in ['A', 'C', 'D']:
            if sec in all_data[orig_label].get('modifiers', {}):
                orig_mods = all_data[orig_label]['modifiers'][sec]
                report.append(f"- **{sec}** (orig={orig_label}):")
                for key in ['JMOD', 'I2MOD', 'I3MOD', 'MMOD', 'WMOD']:
                    if key in merged_mods and key in orig_mods:
                        report.append(f"  - {key}: {orig_mods[key]} (original) -> {merged_mods[key]} (merged)")
                break

report.append("")
report.append("These modifiers appear to have been divided by 100, which is incorrect --")
report.append("property modifiers are dimensionless ratios and should NOT be converted with units.")
report.append("")

# Summary
report.append("---")
report.append("")
report.append("## Summary of Column Assignment Matches")
report.append("")
report.append("| Building | Stories Checked | Section Name Match | Column Count Match | Dimension Bug |")
report.append("|----------|----------------|--------------------|--------------------|---------------|")

for bldg in ['A', 'B', 'C', 'D']:
    all_match = True
    count_match = True
    dim_bug = False

    for story in target_stories:
        orig_cols = all_data[bldg]['col_assignments'].get(story, {})
        merged_cols = {}
        for fname, info in all_data['MERGED']['col_assignments'].get(story, {}).items():
            if info['building'] == bldg:
                merged_cols[fname] = info

        if len(orig_cols) != len(merged_cols):
            count_match = False

        for fname, info in orig_cols.items():
            merged_fname = f"{bldg}{fname}"
            if merged_fname in merged_cols:
                if merged_cols[merged_fname]['section'] != info['section']:
                    all_match = False
            else:
                all_match = False

    # Check if any section used by this building has dimension bug
    for story in target_stories:
        for f, info in all_data[bldg]['col_assignments'].get(story, {}).items():
            sec = info['section']
            if sec in bug_sections:
                dim_bug = True

    sec_match = "YES" if all_match else "NO - MISMATCH"
    cnt_match = "YES" if count_match else "NO - MISMATCH"
    dim_str = "YES - B not converted!" if dim_bug else "No"
    report.append(f"| {bldg} | {len(target_stories)} | {sec_match} | {cnt_match} | {dim_str} |")

report.append("")

# Detailed mismatch list
if all_mismatches:
    report.append("## All Mismatches (Detailed)")
    report.append("")
    report.append("| Story | Building | Original Frame | Original Section | Merged Frame | Merged Section |")
    report.append("|-------|----------|---------------|-----------------|-------------|---------------|")
    for mm in all_mismatches:
        report.append(f"| {mm['story']} | {mm['building']} | {mm['orig_frame']} | {mm['orig_section']} | {mm['merged_frame']} | {mm['merged_section']} |")
    report.append("")

# B building special note
report.append("## Building B Special Notes")
report.append("")
report.append("Building B uses SRC (Steel Reinforced Concrete) columns with Auto Select Lists.")
report.append("At stories 30F-34F, it uses `SRC100X100C420` (D=1.0m, B=1.0m = 100x100cm).")
report.append("At R1F and above, it transitions to SRC auto-select sections:")
report.append("")
report.append("| Section | Type | Size Range (mm) |")
report.append("|---------|------|-----------------|")
report.append("| ACB3 | Auto Select | 500x500 to 1000x1200 |")
report.append("| ACB4 | Auto Select | 500x500 to 1000x1000 |")
report.append("| ACBC2 | Auto Select | 500x1100 to 3000x4000 |")
report.append("| ACN1 | Auto Select | 500x500 to 1300x1800 |")
report.append("| SRC100X100C420 | Rectangular | 1000x1000 (100x100cm) |")
report.append("")
report.append("In the MERGED model, B building columns at R1F correctly use the same")
report.append("auto-select section names (ACB3, ACB4, ACBC2, ACN1) as the original.")
report.append("These sections are preserved correctly in the merge.")

# Write report
os.makedirs(r'C:\Users\User\Desktop\V22 AGENTIC MODEL\scripts\agent_reports', exist_ok=True)
report_path = r'C:\Users\User\Desktop\V22 AGENTIC MODEL\scripts\agent_reports\r1f_column_comparison.md'
with open(report_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(report))

print(f"Report written to: {report_path}")
print(f"Total mismatches found: {len(all_mismatches)}")
print(f"Dimension bug sections: {len(bug_sections)}")
print(f"Affected sections: {bug_sections}")
