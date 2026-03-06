"""
Final comprehensive analysis with calibrated colors.
"""

from PIL import Image
import numpy as np
from scipy import ndimage

base_path = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\Y21\2026-0305 SKILL TEST.VER\結構配置圖\pages"

GRID_X = {1: 0.0, 2: 8.85, 3: 17.35, 4: 24.45}
GRID_Y = {'A': 0.0, 'B': 9.95, 'C': 18.40, 'D': 30.10}

# Calibrated colors from sampling:
# Main beam (blue): RGB(76,166,255) +/- 30
# SB45X60 (green): RGB(76,255,76) +/- 40
# SB30X60 (yellow): RGB(255,255,76) +/- 30
# SB25X50 (cyan): need to find...
# WB (purple/magenta): need to verify
# Diaphragm wall (red): RGB(226,126,126) approximately

# Grid pixel positions (consistent across all basement+tower plans)
GRID_PX = {
    'x': [(780, 0.0), (1156, 8.85), (1518, 17.35), (1819, 24.45)],
    'y': [(557, 30.10), (1056, 18.40), (1414, 9.95), (1838, 0.0)]
}

def px_to_m(px_x, px_y, ref=GRID_PX):
    x_px = [p[0] for p in ref['x']]
    x_m = [p[1] for p in ref['x']]
    y_px = [p[0] for p in ref['y']]
    y_m = [p[1] for p in ref['y']]
    real_x = np.interp(px_x, x_px, x_m)
    real_y = np.interp(px_y, y_px, y_m)
    return real_x, real_y


def find_beams(arr, color_rgb, tolerance=30, min_area=200, ref=GRID_PX):
    """Find beam segments by color."""
    r_diff = np.abs(arr[:,:,0].astype(int) - color_rgb[0])
    g_diff = np.abs(arr[:,:,1].astype(int) - color_rgb[1])
    b_diff = np.abs(arr[:,:,2].astype(int) - color_rgb[2])
    mask = (r_diff < tolerance) & (g_diff < tolerance) & (b_diff < tolerance)

    # Clip to plan area
    x_min = int(min(p[0] for p in ref['x'])) - 30
    x_max = int(max(p[0] for p in ref['x'])) + 30
    y_min = int(min(p[0] for p in ref['y'])) - 30
    y_max = int(max(p[0] for p in ref['y'])) + 30

    plan_mask = np.zeros_like(mask)
    h, w = arr.shape[:2]
    plan_mask[max(0,y_min):min(h,y_max), max(0,x_min):min(w,x_max)] = True
    mask = mask & plan_mask

    labeled, num_features = ndimage.label(mask)

    h_beams = []
    v_beams = []

    for i in range(1, num_features + 1):
        ys, xs = np.where(labeled == i)
        area = len(ys)
        if area < min_area:
            continue

        y_range = ys.max() - ys.min()
        x_range = xs.max() - xs.min()

        if x_range > y_range * 1.5:  # Horizontal (X-direction)
            cy = np.median(ys)
            x1 = xs.min()
            x2 = xs.max()
            rx1, ry = px_to_m(x1, cy, ref)
            rx2, _ = px_to_m(x2, cy, ref)
            length = abs(rx2 - rx1)
            if length > 1.0:
                h_beams.append({
                    'y': round(ry, 2),
                    'x1': round(min(rx1,rx2), 2),
                    'x2': round(max(rx1,rx2), 2),
                    'length': round(length, 2),
                    'area': area,
                    'px_y': int(cy),
                    'px_x1': int(x1),
                    'px_x2': int(x2)
                })
        elif y_range > x_range * 1.5:  # Vertical (Y-direction)
            cx = np.median(xs)
            y1 = ys.min()
            y2 = ys.max()
            rx, ry1 = px_to_m(cx, y1, ref)
            _, ry2 = px_to_m(cx, y2, ref)
            length = abs(ry2 - ry1)
            if length > 1.0:
                v_beams.append({
                    'x': round(rx, 2),
                    'y1': round(min(ry1,ry2), 2),
                    'y2': round(max(ry1,ry2), 2),
                    'length': round(length, 2),
                    'area': area,
                    'px_x': int(cx),
                    'px_y1': int(y1),
                    'px_y2': int(y2)
                })

    return h_beams, v_beams


def get_bay(val, grid_vals, grid_names):
    """Identify which bay a coordinate falls in."""
    for i in range(len(grid_vals)-1):
        if grid_vals[i] - 0.5 <= val <= grid_vals[i+1] + 0.5:
            return f"{grid_names[i]}-{grid_names[i+1]}"
    return "?"


def analyze_floor(img_path, label, ref=GRID_PX):
    """Complete analysis of a floor plan."""
    print(f"\n{'#'*70}")
    print(f"# {label}")
    print(f"{'#'*70}")

    arr = np.array(Image.open(img_path))

    # Detect beams
    beam_types = {
        'Main Beam (blue)': (76, 166, 255),
        'SB45X60 (green)': (76, 255, 76),
        'SB30X60 (yellow)': (255, 255, 76),
        'SB25X50 (cyan)': (76, 255, 255),
    }

    for name, color in beam_types.items():
        tol = 35 if 'green' in name else 30
        h_beams, v_beams = find_beams(arr, color, tolerance=tol, min_area=150, ref=ref)

        if not h_beams and not v_beams:
            # Try with looser tolerance
            h_beams, v_beams = find_beams(arr, color, tolerance=50, min_area=150, ref=ref)

        if h_beams or v_beams:
            print(f"\n  {name}:")

            if h_beams:
                h_beams.sort(key=lambda b: (-b['y'], b['x1']))
                print(f"    X-direction (horizontal, fixed Y):")
                for b in h_beams:
                    bay_y = get_bay(b['y'], [0, 9.95, 18.40, 30.10], ['A', 'B', 'C', 'D'])
                    bay_x1 = get_bay(b['x1'], [0, 8.85, 17.35, 24.45], ['1', '2', '3', '4'])
                    bay_x2 = get_bay(b['x2'], [0, 8.85, 17.35, 24.45], ['1', '2', '3', '4'])
                    print(f"      Y={b['y']:.2f}m (bay {bay_y}): "
                          f"X={b['x1']:.2f}~{b['x2']:.2f}m (L={b['length']:.2f}m) "
                          f"[px: y={b['px_y']}, x={b['px_x1']}~{b['px_x2']}]")

            if v_beams:
                v_beams.sort(key=lambda b: (b['x'], -b['y2']))
                print(f"    Y-direction (vertical, fixed X):")
                for b in v_beams:
                    bay_x = get_bay(b['x'], [0, 8.85, 17.35, 24.45], ['1', '2', '3', '4'])
                    print(f"      X={b['x']:.2f}m (bay {bay_x}): "
                          f"Y={b['y1']:.2f}~{b['y2']:.2f}m (L={b['length']:.2f}m) "
                          f"[px: x={b['px_x']}, y={b['px_y1']}~{b['px_y2']}]")
        else:
            print(f"\n  {name}: none detected")


# ============================================================
# First, let's find cyan color by sampling page_08.png more
# ============================================================
arr = np.array(Image.open(f"{base_path}/page_08.png"))

# Scan for cyan-ish pixels in the plan area
print("Scanning for cyan pixels in 4F~9F plan area...")
cyan_count = 0
r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
# Cyan = low red, high green, high blue
cyan_mask = (r < 130) & (g > 200) & (b > 200) & (g > r + 50) & (b > r + 50)
# Clip to plan
plan = np.zeros_like(cyan_mask)
plan[530:1860, 750:1850] = True
cyan_mask = cyan_mask & plan
cyan_pixels = np.sum(cyan_mask)
print(f"  Cyan pixels found: {cyan_pixels}")

if cyan_pixels > 0:
    cy_ys, cy_xs = np.where(cyan_mask)
    for i in range(0, min(len(cy_ys), 50), 5):
        y, x = cy_ys[i], cy_xs[i]
        rx, ry = px_to_m(x, y)
        print(f"  Cyan at px({x},{y}) = ({rx:.2f}m, {ry:.2f}m), RGB={arr[y,x,:3]}")

# Also scan for light blue that might be SB25X50
# From the image, SB25X50 appears as a lighter cyan/turquoise
light_cyan_mask = (r < 160) & (g > 220) & (b > 220) & (b > r + 80)
light_cyan_mask = light_cyan_mask & plan
lc_pixels = np.sum(light_cyan_mask)
print(f"\n  Light cyan pixels: {lc_pixels}")

# Let's also check what colors are actually in the main beam corridors
# The SB25X50 beams should be visible as short segments
# Sample some likely locations based on visual inspection
print("\n\nChecking SB25X50 locations from visual inspection:")
# From page_08: cyan beams appear near the stairwell/elevator area
for y in [1180, 1190, 1200, 1210, 1220]:
    for x in [1590, 1600, 1610, 1620, 1630, 1700, 1710, 1720]:
        if 0 <= y < arr.shape[0] and 0 <= x < arr.shape[1]:
            pix = arr[y, x, :3]
            if not (pix[0] > 220 and pix[1] > 220 and pix[2] > 220):
                rx, ry = px_to_m(x, y)
                print(f"  px({x},{y}) = ({rx:.2f}, {ry:.2f}): RGB({pix[0]},{pix[1]},{pix[2]})")


# ============================================================
# Full analysis of all key floors
# ============================================================

# 4F~9F
analyze_floor(f"{base_path}/page_08.png", "4F~9F TYPICAL FLOOR")

# B4F
analyze_floor(f"{base_path}/page_01.png", "B4F (Foundation)")

# B1F
analyze_floor(f"{base_path}/page_04.png", "B1F")

# 1F
analyze_floor(f"{base_path}/page_05.png", "1F")

# 2F
analyze_floor(f"{base_path}/page_06.png", "2F")

# 3F
analyze_floor(f"{base_path}/page_07.png", "3F")

# 10~13F
analyze_floor(f"{base_path}/page_09.png", "10F~13F")

# 14F~R1F (different grid spacing!)
# X: 6.75, 8.50, 5.60 -> Grids at 0, 6.75, 15.25, 20.85
# But the columns are at different pixel positions
# From the analysis: cols at px x=869, 1156, 1518, 1756
# These map to the SETBACK grid: 0, 6.75, 15.25, 20.85
# However Y grids remain the same

PX_14F = {
    'x': [(869, 0.0), (1156, 6.75), (1518, 15.25), (1756, 20.85)],
    'y': [(557, 30.10), (1056, 18.40), (1414, 9.95), (1838, 0.0)]
}
# Actually wait - the 14F grid is a setback of the SAME building
# The grids 2 and 3 remain at the same positions (8.85m apart = 8.50m center-to-center)
# Grid 1 and 4 move INWARD
# Let me re-check: page_10 says 6.75 + 8.50 + 5.60 = 20.85m total
# The setback is symmetric around the middle
# Grid 2 (original 8.85m) -> now at (24.45-20.85)/2 + 6.75 = 1.80 + 6.75 = 8.55m from original grid 1
# Actually no, the setback columns are at NEW positions relative to the original grid
# The middle span (8.50m) matches the original middle span (8.50m)
# So grid 2 and 3 positions are UNCHANGED
# Grid 1' = Grid 2 - 6.75 = 8.85 - 6.75 = 2.10m (from original Grid 1)
# Grid 4' = Grid 3 + 5.60 = 17.35 + 5.60 = 22.95m (from original Grid 1)
# Wait - that gives 22.95 - 2.10 = 20.85m total, which matches!

# So the 14F grid in ORIGINAL coordinates:
# Grid 1' = 2.10m, Grid 2 = 8.85m, Grid 3 = 17.35m, Grid 4' = 22.95m

PX_14F = {
    'x': [(869, 2.10), (1156, 8.85), (1518, 17.35), (1756, 22.95)],
    'y': [(557, 30.10), (1056, 18.40), (1414, 9.95), (1838, 0.0)]
}

analyze_floor(f"{base_path}/page_10.png", "14F~R1F (Setback)", ref=PX_14F)


# ============================================================
# Also check for the wall beams on B1F and 1F
# ============================================================
print("\n\n" + "#"*70)
print("# WALL BEAM (WB) AND DIAPHRAGM WALL ANALYSIS")
print("#"*70)

# WB (purple/magenta): need to identify color
arr_b1 = np.array(Image.open(f"{base_path}/page_04.png"))

# The WB (wall beam) appears purple in the legend
# Purple ~ RGB(128, 0, 128) or similar
# Let's scan for purple pixels
print("\nScanning for purple (WB) pixels in B1F...")
r, g, b = arr_b1[:,:,0], arr_b1[:,:,1], arr_b1[:,:,2]
purple_mask = (r > 100) & (r < 200) & (g < 80) & (b > 100) & (b < 200)
plan = np.zeros_like(purple_mask)
plan[530:1860, 750:1850] = True
purple_mask = purple_mask & plan
pp = np.sum(purple_mask)
print(f"  Purple pixels: {pp}")

if pp > 0:
    py_ys, py_xs = np.where(purple_mask)
    for i in range(0, min(len(py_ys), 20)):
        y, x = py_ys[i], py_xs[i]
        rx, ry = px_to_m(x, y)
        print(f"  Purple at px({x},{y}) = ({rx:.2f}m, {ry:.2f}m), RGB={arr_b1[y,x,:3]}")


# Diaphragm wall (red/pink border)
print("\nScanning for diaphragm wall (red border) in B1F...")
# The diaphragm wall appears as thick red lines around the perimeter
# Red ~ RGB(226, 126, 126) from earlier sampling, or darker red
wall_mask = (r > 180) & (g < 140) & (b < 140) & (r > g + 40)
wall_mask = wall_mask & plan
wp = np.sum(wall_mask)
print(f"  Red/wall pixels in plan area: {wp}")


print("\n\nANALYSIS COMPLETE.")
