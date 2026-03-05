"""
Grid comparison tool for 大陳 model integration.
Compares grid lines from A/B/C/D models vs ALL/2026-0305 reference.
"""
import re, json

def parse_e2k_section(filepath, section_name):
    """Extract a section from e2k file between $ SECTION_NAME and next $ line."""
    lines = []
    in_section = False
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith(f'$ {section_name}'):
                in_section = True
                continue
            elif in_section and stripped.startswith('$'):
                break
            elif in_section:
                if stripped:
                    lines.append(stripped)
    return lines

def parse_grids(filepath):
    """Parse grid lines and return dict {label: (dir, coord)}"""
    lines = parse_e2k_section(filepath, 'GRIDS')
    grids = {}
    unit_scale = 1.0
    for line in lines:
        if 'COORDSYSTEM' in line:
            m = re.search(r'BUBBLESIZE\s+([\d.]+)', line)
            if m:
                bs = float(m.group(1))
                if bs > 10:  # cm units (bubblesize 125 = cm)
                    unit_scale = 0.01
            continue
        m = re.search(r'LABEL\s+"([^"]+)"\s+DIR\s+"([^"]+)"\s+COORD\s+([-\d.E+]+)', line)
        if m:
            label, direction, coord = m.group(1), m.group(2), float(m.group(3))
            grids[label] = (direction, coord * unit_scale)
    return grids

def compare_grids(ref_grids, model_grids, model_name):
    """Compare model grids vs reference, return changes."""
    changes = []
    for label, (direction, coord) in model_grids.items():
        if label in ref_grids:
            ref_dir, ref_coord = ref_grids[label]
            diff = abs(coord - ref_coord)
            if diff > 0.001:  # more than 1mm difference
                changes.append({
                    'label': label,
                    'dir': direction,
                    'old': ref_coord,
                    'new': coord,
                    'diff_m': round(coord - ref_coord, 4)
                })
        else:
            changes.append({
                'label': label,
                'dir': direction,
                'old': None,
                'new': coord,
                'diff_m': None
            })
    return changes

# File paths
base = "C:/Users/User/Desktop/V22 AGENTIC MODEL/ETABS REF/大陳"
files = {
    'ALL_NEW': f"{base}/ALL/2026-0305/2026-0305_ALL_BUT RC_KpKvKw.e2k",
    'ALL_OLD': f"{base}/ALL/OLD/2025-1111_ALL_BUT RC_KpKvKw.e2k",
    'A': f"{base}/A/2026-0303_A_SC_KpKvKw.e2k",
    'B': f"{base}/B/2026-0303_B_SC_KpKvKw.e2k",
    'C': f"{base}/C/2026-0304_C_SC_KpKvKw.e2k",
    'D': f"{base}/D/2026-0303_D_SC_KpKvKw.e2k",
}

# Parse all grids
all_grids = {}
for name, path in files.items():
    all_grids[name] = parse_grids(path)
    print(f"\n{name}: {len(all_grids[name])} grid lines")

# Compare each model vs ALL_NEW reference
ref = all_grids['ALL_NEW']
print("\n" + "="*80)
print("GRID DIFFERENCES vs ALL/2026-0305 reference")
print("="*80)

for model_name in ['A', 'B', 'C', 'D']:
    changes = compare_grids(ref, all_grids[model_name], model_name)
    if changes:
        print(f"\n--- {model_name} model changes ---")
        for c in changes:
            if c['old'] is not None:
                print(f"  Grid {c['label']} ({c['dir']}): {c['old']:.4f}m -> {c['new']:.4f}m  (delta={c['diff_m']:+.4f}m)")
            else:
                print(f"  Grid {c['label']} ({c['dir']}): NEW at {c['new']:.4f}m")
    else:
        print(f"\n--- {model_name} model: NO CHANGES ---")

# Build unified grid: take changes from each building where applicable
print("\n" + "="*80)
print("PROPOSED UNIFIED GRID (ALL grids, with A/B/C/D changes applied)")
print("="*80)

# The key insight: each building covers specific grid ranges
# A棟 and D棟 are on opposite ends, B棟 and C棟 in the middle
# Changes from each building should be applied to their covered grids

unified = dict(ref)  # start from reference
change_log = []

for model_name in ['A', 'B', 'C', 'D']:
    changes = compare_grids(ref, all_grids[model_name], model_name)
    for c in changes:
        label = c['label']
        if c['old'] is not None:
            old_val = unified[label]
            unified[label] = (c['dir'], c['new'])
            change_log.append(f"  {label}: {old_val[1]:.4f} -> {c['new']:.4f} (from {model_name})")

if change_log:
    print("Changes applied:")
    for log in change_log:
        print(log)

# Print unified grid
print("\nUnified X grids:")
x_grids = [(label, coord) for label, (d, coord) in unified.items() if d == 'X']
x_grids.sort(key=lambda x: x[1])
for label, coord in x_grids:
    ref_coord = ref[label][1] if label in ref else None
    marker = " *CHANGED*" if ref_coord and abs(coord - ref_coord) > 0.001 else ""
    print(f"  {label:4s} = {coord:10.4f}m{marker}")

print("\nUnified Y grids:")
y_grids = [(label, coord) for label, (d, coord) in unified.items() if d == 'Y']
y_grids.sort(key=lambda x: x[1])
for label, coord in y_grids:
    ref_coord = ref[label][1] if label in ref else None
    marker = " *CHANGED*" if ref_coord and abs(coord - ref_coord) > 0.001 else ""
    print(f"  {label:4s} = {coord:10.4f}m{marker}")

# Save unified grid data for later use
output = {
    'unified_grids': {label: {'dir': d, 'coord': c} for label, (d, c) in unified.items()},
    'changes_by_model': {}
}
for model_name in ['A', 'B', 'C', 'D']:
    changes = compare_grids(ref, all_grids[model_name], model_name)
    output['changes_by_model'][model_name] = changes

with open(f"{base}/grid_comparison.json", 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nGrid comparison saved to: {base}/grid_comparison.json")
