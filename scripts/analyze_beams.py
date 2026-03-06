"""
Pixel-based coordinate analysis for Y21 structural layout drawings.
Measures secondary beam positions by mapping pixel coordinates to real-world coordinates.
"""

from PIL import Image
import numpy as np

# Grid system (known)
# X: Grid 1=0, Grid 2=8.85, Grid 3=17.35, Grid 4=24.45
# Y: Grid A=0, Grid B=9.95, Grid C=18.40, Grid D=30.10

GRID_X = {1: 0.0, 2: 8.85, 3: 17.35, 4: 24.45}
GRID_Y = {'A': 0.0, 'B': 9.95, 'C': 18.40, 'D': 30.10}

base_path = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\Y21\2026-0305 SKILL TEST.VER\結構配置圖\pages"

def analyze_image(img_path, label):
    """Load image and print dimensions"""
    img = Image.open(img_path)
    arr = np.array(img)
    print(f"\n{'='*60}")
    print(f"Analyzing: {label}")
    print(f"Image size: {img.size[0]} x {img.size[1]} pixels")
    return arr

def find_color_lines(arr, color_rgb, tolerance=40, min_length=30):
    """
    Find horizontal and vertical lines of a specific color.
    Returns lists of horizontal lines (y, x_start, x_end) and vertical lines (x, y_start, y_end).
    """
    h, w = arr.shape[:2]

    # Create mask for the target color
    diff = np.abs(arr[:,:,:3].astype(int) - np.array(color_rgb).astype(int))
    mask = np.all(diff < tolerance, axis=2)

    # Find horizontal lines
    h_lines = []
    for y in range(0, h, 1):
        row = mask[y, :]
        if np.sum(row) < min_length:
            continue
        # Find contiguous segments
        segments = []
        in_seg = False
        start = 0
        for x in range(w):
            if row[x] and not in_seg:
                in_seg = True
                start = x
            elif not row[x] and in_seg:
                in_seg = False
                if x - start >= min_length:
                    segments.append((start, x))
        if in_seg and w - start >= min_length:
            segments.append((start, w))
        for seg in segments:
            h_lines.append((y, seg[0], seg[1]))

    # Merge nearby horizontal lines (within 3px y)
    merged_h = []
    if h_lines:
        h_lines.sort()
        current = list(h_lines[0])
        for line in h_lines[1:]:
            if line[0] - current[0] <= 3 and abs(line[1] - current[1]) < 20 and abs(line[2] - current[2]) < 20:
                current[0] = (current[0] + line[0]) // 2
                current[1] = min(current[1], line[1])
                current[2] = max(current[2], line[2])
            else:
                merged_h.append(tuple(current))
                current = list(line)
        merged_h.append(tuple(current))

    # Find vertical lines
    v_lines = []
    for x in range(0, w, 1):
        col = mask[:, x]
        if np.sum(col) < min_length:
            continue
        segments = []
        in_seg = False
        start = 0
        for y in range(h):
            if col[y] and not in_seg:
                in_seg = True
                start = y
            elif not col[y] and in_seg:
                in_seg = False
                if y - start >= min_length:
                    segments.append((start, y))
        if in_seg and h - start >= min_length:
            segments.append((start, h))
        for seg in segments:
            v_lines.append((x, seg[0], seg[1]))

    # Merge nearby vertical lines (within 3px x)
    merged_v = []
    if v_lines:
        v_lines.sort()
        current = list(v_lines[0])
        for line in v_lines[1:]:
            if line[0] - current[0] <= 3 and abs(line[1] - current[1]) < 20 and abs(line[2] - current[2]) < 20:
                current[0] = (current[0] + line[0]) // 2
                current[1] = min(current[1], line[1])
                current[2] = max(current[2], line[2])
            else:
                merged_v.append(tuple(current))
                current = list(line)
        merged_v.append(tuple(current))

    return merged_h, merged_v

def cluster_lines(lines, axis_idx=0, gap=15):
    """Cluster lines that are close together on the specified axis."""
    if not lines:
        return []
    sorted_lines = sorted(lines, key=lambda l: l[axis_idx])
    clusters = [[sorted_lines[0]]]
    for line in sorted_lines[1:]:
        if line[axis_idx] - clusters[-1][-1][axis_idx] <= gap:
            clusters[-1].append(line)
        else:
            clusters.append([line])

    result = []
    for cluster in clusters:
        avg_pos = int(np.mean([l[axis_idx] for l in cluster]))
        min_start = min(l[1] for l in cluster) if axis_idx == 0 else min(l[1] for l in cluster)
        max_end = max(l[2] for l in cluster) if axis_idx == 0 else max(l[2] for l in cluster)
        result.append((avg_pos, min_start, max_end, len(cluster)))
    return result


def find_grid_pixel_positions(arr):
    """
    Try to find the grid line pixel positions by looking for the column positions (orange squares).
    Orange columns are at grid intersections.
    """
    h, w = arr.shape[:2]

    # Orange color for columns: roughly RGB(255, 165, 0) or similar
    # From the images, columns appear as orange/golden squares
    # Let's look for orange-ish pixels
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]

    # Orange mask: high red, medium green, low blue
    orange_mask = (r > 180) & (g > 100) & (g < 200) & (b < 80)

    # Find clusters of orange pixels (columns)
    from scipy import ndimage
    labeled, num_features = ndimage.label(orange_mask)

    col_positions = []
    for i in range(1, num_features + 1):
        ys, xs = np.where(labeled == i)
        area = len(ys)
        if area > 100:  # Minimum size for a column marker
            cx = np.mean(xs)
            cy = np.mean(ys)
            col_positions.append((cx, cy, area))

    return col_positions


def map_pixel_to_real(px, py, grid_px, grid_real_x, grid_real_y):
    """
    Map pixel coordinates to real coordinates using known grid positions.
    grid_px: dict with 'x' list of (px_x, real_x) and 'y' list of (px_y, real_y)
    """
    # Interpolate X
    x_pairs = sorted(grid_real_x, key=lambda p: p[0])
    real_x = np.interp(px, [p[0] for p in x_pairs], [p[1] for p in x_pairs])

    # Interpolate Y (note: pixel Y increases downward, real Y increases upward typically)
    y_pairs = sorted(grid_real_y, key=lambda p: p[0])
    real_y = np.interp(py, [p[0] for p in y_pairs], [p[1] for p in y_pairs])

    return real_x, real_y


# ============================================================
# Analyze page_08.png (4F~9F typical floor)
# ============================================================
print("="*80)
print("ANALYZING 4F~9F TYPICAL FLOOR (page_08.png)")
print("="*80)

arr = analyze_image(f"{base_path}/page_08.png", "4F~9F")

# Find column positions (orange squares)
col_positions = find_grid_pixel_positions(arr)
print(f"\nFound {len(col_positions)} orange column markers:")
for i, (cx, cy, area) in enumerate(sorted(col_positions, key=lambda p: (p[1], p[0]))):
    print(f"  Col {i+1}: px({cx:.0f}, {cy:.0f}), area={area}")

# Also look for small red squares (C40x40)
r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
red_mask = (r > 200) & (g < 80) & (b < 80)
from scipy import ndimage
labeled_red, num_red = ndimage.label(red_mask)
red_positions = []
for i in range(1, num_red + 1):
    ys, xs = np.where(labeled_red == i)
    area = len(ys)
    if 20 < area < 500:  # Small red squares
        cx = np.mean(xs)
        cy = np.mean(ys)
        red_positions.append((cx, cy, area))

print(f"\nFound {len(red_positions)} red C40x40 markers:")
for i, (cx, cy, area) in enumerate(sorted(red_positions, key=lambda p: (p[1], p[0]))):
    print(f"  C40x40 {i+1}: px({cx:.0f}, {cy:.0f}), area={area}")

# Now identify grid lines from column positions
# Sort columns by position to identify grid intersections
# The 4F~9F plan should have 12 main columns (C120x120) at 4x3 grid = max 12
# Plus some C40x40

# Group columns by approximate X position
col_x_groups = {}
for cx, cy, area in col_positions:
    found = False
    for key in col_x_groups:
        if abs(cx - key) < 40:
            col_x_groups[key].append((cx, cy, area))
            found = True
            break
    if not found:
        col_x_groups[cx] = [(cx, cy, area)]

print("\nColumn X-groups:")
x_keys = sorted(col_x_groups.keys())
for k in x_keys:
    cols = col_x_groups[k]
    avg_x = np.mean([c[0] for c in cols])
    y_vals = sorted([c[1] for c in cols])
    print(f"  X~{avg_x:.0f}px: {len(cols)} columns, Y positions: {[f'{y:.0f}' for y in y_vals]}")

# Group columns by approximate Y position
col_y_groups = {}
for cx, cy, area in col_positions:
    found = False
    for key in col_y_groups:
        if abs(cy - key) < 40:
            col_y_groups[key].append((cx, cy, area))
            found = True
            break
    if not found:
        col_y_groups[cy] = [(cx, cy, area)]

print("\nColumn Y-groups:")
y_keys = sorted(col_y_groups.keys())
for k in y_keys:
    cols = col_y_groups[k]
    avg_y = np.mean([c[1] for c in cols])
    x_vals = sorted([c[0] for c in cols])
    print(f"  Y~{avg_y:.0f}px: {len(cols)} columns, X positions: {[f'{x:.0f}' for x in x_vals]}")

# Determine pixel-to-real mapping from the 4 corner columns
# Grid intersections with columns:
# From the image, the grid goes: X: 1,2,3,4 and Y: A(bottom), B, C, D(top)
# In pixel coordinates, Y is inverted (top=small Y, bottom=large Y)
# So Grid D (top in real) = smallest pixel Y, Grid A (bottom in real) = largest pixel Y

print("\n" + "="*80)
print("MAPPING GRID PIXEL POSITIONS")
print("="*80)

# Identify the 4 grid X positions and 4 grid Y positions from column clusters
if len(x_keys) >= 4:
    # Take the 4 most distinct X positions
    grid_px_x = sorted(x_keys)[:4] if len(x_keys) == 4 else sorted(x_keys)
    print(f"\nGrid X pixel positions: {[f'{x:.0f}' for x in grid_px_x]}")

    # Map to real coordinates
    x_mapping = list(zip(grid_px_x[:4], [GRID_X[1], GRID_X[2], GRID_X[3], GRID_X[4]]))
    print(f"X mapping: {[(f'{px:.0f}px -> {real:.2f}m') for px, real in x_mapping]}")

if len(y_keys) >= 4:
    grid_px_y = sorted(y_keys)[:4] if len(y_keys) == 4 else sorted(y_keys)
    print(f"\nGrid Y pixel positions (top to bottom): {[f'{y:.0f}' for y in grid_px_y]}")

    # In image: top = Grid D (30.10m), bottom = Grid A (0m)
    # So smallest pixel Y = largest real Y
    y_mapping = list(zip(grid_px_y[:4], [GRID_Y['D'], GRID_Y['C'], GRID_Y['B'], GRID_Y['A']]))
    print(f"Y mapping: {[(f'{px:.0f}px -> {real:.2f}m') for px, real in y_mapping]}")


# ============================================================
# Find secondary beams by color
# ============================================================
print("\n" + "="*80)
print("FINDING SECONDARY BEAMS BY COLOR (4F~9F)")
print("="*80)

# Color definitions from legend:
# SB45X60 = Green (approximately RGB 0,180,0 or similar bright green)
# SB30X60 = Yellow (approximately RGB 255,255,0)
# SB25X50 = Cyan (approximately RGB 0,255,255)

colors = {
    'SB45X60_green': (0, 180, 0),
    'SB30X60_yellow': (255, 255, 0),
    'SB25X50_cyan': (0, 255, 255),
}

for name, color in colors.items():
    print(f"\n--- {name} (target RGB={color}) ---")
    h_lines, v_lines = find_color_lines(arr, color, tolerance=50, min_length=40)

    # Cluster horizontal lines
    h_clustered = cluster_lines(h_lines, axis_idx=0, gap=8)
    print(f"  Horizontal lines (Y-direction beams): {len(h_clustered)} clusters")
    for pos, start, end, count in h_clustered:
        print(f"    Y={pos}px, X: {start}-{end}px (width={end-start}px, {count} raw lines)")

    # Cluster vertical lines
    v_clustered = cluster_lines(v_lines, axis_idx=0, gap=8)
    print(f"  Vertical lines (X-direction beams): {len(v_clustered)} clusters")
    for pos, start, end, count in v_clustered:
        print(f"    X={pos}px, Y: {start}-{end}px (height={end-start}px, {count} raw lines)")


# ============================================================
# Now map beam pixel positions to real coordinates
# ============================================================
print("\n" + "="*80)
print("SECONDARY BEAM REAL COORDINATES (4F~9F)")
print("="*80)

if len(x_keys) >= 4 and len(y_keys) >= 4:
    x_map = list(zip(grid_px_x[:4], [0.0, 8.85, 17.35, 24.45]))
    # Y: top pixel = D(30.10), bottom pixel = A(0.0)
    y_map = list(zip(grid_px_y[:4], [30.10, 18.40, 9.95, 0.0]))

    def px_to_m(px_x, px_y):
        real_x = np.interp(px_x, [p[0] for p in x_map], [p[1] for p in x_map])
        real_y = np.interp(px_y, [p[0] for p in y_map], [p[1] for p in y_map])
        return real_x, real_y

    for name, color in colors.items():
        print(f"\n--- {name} ---")
        h_lines, v_lines = find_color_lines(arr, color, tolerance=50, min_length=40)
        h_clustered = cluster_lines(h_lines, axis_idx=0, gap=8)
        v_clustered = cluster_lines(v_lines, axis_idx=0, gap=8)

        print(f"  X-direction beams (horizontal in plan, constant Y):")
        for pos, start, end, count in h_clustered:
            x1, y1 = px_to_m(start, pos)
            x2, y2 = px_to_m(end, pos)
            y_avg = (y1 + y2) / 2
            print(f"    Y={y_avg:.2f}m: X from {x1:.2f}m to {x2:.2f}m (length={x2-x1:.2f}m)")

        print(f"  Y-direction beams (vertical in plan, constant X):")
        for pos, start, end, count in v_clustered:
            x1, y1 = px_to_m(pos, start)
            x2, y2 = px_to_m(pos, end)
            x_avg = (x1 + x2) / 2
            print(f"    X={x_avg:.2f}m: Y from {min(y1,y2):.2f}m to {max(y1,y2):.2f}m (length={abs(y2-y1):.2f}m)")


# ============================================================
# Analyze B1F (page_04.png)
# ============================================================
print("\n\n" + "="*80)
print("ANALYZING B1F (page_04.png)")
print("="*80)

arr_b1 = analyze_image(f"{base_path}/page_04.png", "B1F")
col_pos_b1 = find_grid_pixel_positions(arr_b1)
print(f"\nFound {len(col_pos_b1)} orange column markers (C120x180):")
for i, (cx, cy, area) in enumerate(sorted(col_pos_b1, key=lambda p: (p[1], p[0]))):
    print(f"  Col {i+1}: px({cx:.0f}, {cy:.0f}), area={area}")

# Find pink C50x50 markers
r, g, b = arr_b1[:,:,0], arr_b1[:,:,1], arr_b1[:,:,2]
pink_mask = (r > 200) & (g > 150) & (g < 220) & (b > 150) & (b < 220) & (r > g) & (r > b)
labeled_pink, num_pink = ndimage.label(pink_mask)
pink_positions = []
for i in range(1, num_pink + 1):
    ys, xs = np.where(labeled_pink == i)
    area = len(ys)
    if 20 < area < 500:
        cx = np.mean(xs)
        cy = np.mean(ys)
        pink_positions.append((cx, cy, area))

print(f"\nFound {len(pink_positions)} pink C50x50 markers:")
for i, (cx, cy, area) in enumerate(sorted(pink_positions, key=lambda p: (p[1], p[0]))):
    print(f"  C50x50 {i+1}: px({cx:.0f}, {cy:.0f}), area={area}")

# B1F secondary beams
print("\n--- B1F Secondary Beams ---")
for name, color in colors.items():
    h_lines, v_lines = find_color_lines(arr_b1, color, tolerance=50, min_length=40)
    h_clustered = cluster_lines(h_lines, axis_idx=0, gap=8)
    v_clustered = cluster_lines(v_lines, axis_idx=0, gap=8)
    if h_clustered or v_clustered:
        print(f"\n  {name}:")
        print(f"    Horizontal: {len(h_clustered)} lines")
        for pos, start, end, count in h_clustered:
            print(f"      Y={pos}px, X: {start}-{end}px")
        print(f"    Vertical: {len(v_clustered)} lines")
        for pos, start, end, count in v_clustered:
            print(f"      X={pos}px, Y: {start}-{end}px")


# ============================================================
# Analyze 2F (page_06.png)
# ============================================================
print("\n\n" + "="*80)
print("ANALYZING 2F (page_06.png)")
print("="*80)

arr_2f = analyze_image(f"{base_path}/page_06.png", "2F")
col_pos_2f = find_grid_pixel_positions(arr_2f)
print(f"\nFound {len(col_pos_2f)} orange column markers (C120x150):")
for i, (cx, cy, area) in enumerate(sorted(col_pos_2f, key=lambda p: (p[1], p[0]))):
    print(f"  Col {i+1}: px({cx:.0f}, {cy:.0f}), area={area}")

# Find red C40x40 markers
r, g, b = arr_2f[:,:,0], arr_2f[:,:,1], arr_2f[:,:,2]
red_mask = (r > 200) & (g < 80) & (b < 80)
labeled_red, num_red = ndimage.label(red_mask)
red_pos_2f = []
for i in range(1, num_red + 1):
    ys, xs = np.where(labeled_red == i)
    area = len(ys)
    if 20 < area < 500:
        cx = np.mean(xs)
        cy = np.mean(ys)
        red_pos_2f.append((cx, cy, area))

print(f"\nFound {len(red_pos_2f)} red C40x40 markers:")
for i, (cx, cy, area) in enumerate(sorted(red_pos_2f, key=lambda p: (p[1], p[0]))):
    print(f"  C40x40 {i+1}: px({cx:.0f}, {cy:.0f}), area={area}")


# ============================================================
# Analyze 14F~R1F (page_10.png) for setback
# ============================================================
print("\n\n" + "="*80)
print("ANALYZING 14F~R1F (page_10.png)")
print("="*80)

arr_14 = analyze_image(f"{base_path}/page_10.png", "14F~R1F")
col_pos_14 = find_grid_pixel_positions(arr_14)
print(f"\nFound {len(col_pos_14)} orange column markers:")
for i, (cx, cy, area) in enumerate(sorted(col_pos_14, key=lambda p: (p[1], p[0]))):
    print(f"  Col {i+1}: px({cx:.0f}, {cy:.0f}), area={area}")

# Find red C40x40 markers
r, g, b = arr_14[:,:,0], arr_14[:,:,1], arr_14[:,:,2]
red_mask = (r > 200) & (g < 80) & (b < 80)
labeled_red, num_red = ndimage.label(red_mask)
red_pos_14 = []
for i in range(1, num_red + 1):
    ys, xs = np.where(labeled_red == i)
    area = len(ys)
    if 20 < area < 500:
        cx = np.mean(xs)
        cy = np.mean(ys)
        red_pos_14.append((cx, cy, area))

print(f"\nFound {len(red_pos_14)} red C40x40 markers:")
for i, (cx, cy, area) in enumerate(sorted(red_pos_14, key=lambda p: (p[1], p[0]))):
    print(f"  C40x40 {i+1}: px({cx:.0f}, {cy:.0f}), area={area}")


# ============================================================
# Analyze B4F (page_01.png) - Foundation level
# ============================================================
print("\n\n" + "="*80)
print("ANALYZING B4F (page_01.png)")
print("="*80)

arr_b4 = analyze_image(f"{base_path}/page_01.png", "B4F")
col_pos_b4 = find_grid_pixel_positions(arr_b4)
print(f"\nFound {len(col_pos_b4)} orange column markers (C120x180):")
for i, (cx, cy, area) in enumerate(sorted(col_pos_b4, key=lambda p: (p[1], p[0]))):
    print(f"  Col {i+1}: px({cx:.0f}, {cy:.0f}), area={area}")


print("\n\nDONE - Analysis complete.")
