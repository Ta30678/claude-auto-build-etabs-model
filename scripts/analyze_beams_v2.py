"""
Refined pixel-based analysis for Y21 structural layout.
Uses column positions as grid anchors, then analyzes beam colors more carefully.
"""

from PIL import Image
import numpy as np
from scipy import ndimage

base_path = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\Y21\2026-0305 SKILL TEST.VER\結構配置圖\pages"

# Grid system
GRID_X = {1: 0.0, 2: 8.85, 3: 17.35, 4: 24.45}
GRID_Y = {'A': 0.0, 'B': 9.95, 'C': 18.40, 'D': 30.10}

# ============================================================
# From page_08.png (4F~9F), we identified main column pixel positions:
# Grid X pixels: 1=780, 2=1156, 3=1518, 4=1819
# Grid Y pixels: D=557, C=1056, B=1414, A=1838
# (Y is inverted: top of image = Grid D = Y=30.10m)
# ============================================================

# Reference grid pixel positions for 4F~9F (page_08.png)
PX_4F = {
    'x': [(780, 0.0), (1156, 8.85), (1518, 17.35), (1819, 24.45)],
    'y': [(557, 30.10), (1056, 18.40), (1414, 9.95), (1838, 0.0)]
}

def px_to_m(px_x, px_y, ref=PX_4F):
    """Convert pixel to real coordinates using linear interpolation."""
    x_px = [p[0] for p in ref['x']]
    x_m = [p[1] for p in ref['x']]
    y_px = [p[0] for p in ref['y']]
    y_m = [p[1] for p in ref['y']]
    real_x = np.interp(px_x, x_px, x_m)
    real_y = np.interp(px_y, y_px, y_m)
    return real_x, real_y


def find_beams_by_color(arr, color_rgb, tolerance=35, min_pixels=50, ref=PX_4F):
    """
    Find beam lines by color, using a stricter approach.
    Returns horizontal and vertical beam segments with real coordinates.
    """
    h, w = arr.shape[:2]

    # Tighter color matching
    r_diff = np.abs(arr[:,:,0].astype(int) - color_rgb[0])
    g_diff = np.abs(arr[:,:,1].astype(int) - color_rgb[1])
    b_diff = np.abs(arr[:,:,2].astype(int) - color_rgb[2])
    mask = (r_diff < tolerance) & (g_diff < tolerance) & (b_diff < tolerance)

    # Only look within the plan area (between grid lines)
    x_min = int(min(p[0] for p in ref['x'])) - 20
    x_max = int(max(p[0] for p in ref['x'])) + 20
    y_min = int(min(p[0] for p in ref['y'])) - 20
    y_max = int(max(p[0] for p in ref['y'])) + 20

    # Zero out areas outside the plan
    plan_mask = np.zeros_like(mask)
    plan_mask[max(0,y_min):min(h,y_max), max(0,x_min):min(w,x_max)] = True
    mask = mask & plan_mask

    total_pixels = np.sum(mask)
    print(f"    Total matching pixels in plan area: {total_pixels}")

    if total_pixels < min_pixels:
        return [], []

    # Label connected components
    labeled, num_features = ndimage.label(mask)

    h_beams = []  # (y_m, x_start_m, x_end_m)
    v_beams = []  # (x_m, y_start_m, y_end_m)

    for i in range(1, num_features + 1):
        ys, xs = np.where(labeled == i)
        area = len(ys)
        if area < min_pixels:
            continue

        # Determine if horizontal or vertical
        y_range = ys.max() - ys.min()
        x_range = xs.max() - xs.min()

        if x_range > y_range * 2:  # Horizontal beam (X-direction)
            cy = np.mean(ys)
            x1 = xs.min()
            x2 = xs.max()
            rx1, ry = px_to_m(x1, cy, ref)
            rx2, _ = px_to_m(x2, cy, ref)
            if abs(rx2 - rx1) > 0.5:  # Minimum 0.5m length
                h_beams.append((round(ry, 2), round(min(rx1,rx2), 2), round(max(rx1,rx2), 2), area))
        elif y_range > x_range * 2:  # Vertical beam (Y-direction)
            cx = np.mean(xs)
            y1 = ys.min()
            y2 = ys.max()
            rx, ry1 = px_to_m(cx, y1, ref)
            _, ry2 = px_to_m(cx, y2, ref)
            if abs(ry2 - ry1) > 0.5:  # Minimum 0.5m length
                v_beams.append((round(rx, 2), round(min(ry1,ry2), 2), round(max(ry1,ry2), 2), area))
        else:
            # Could be a short beam or artifact - skip if too small
            if area > min_pixels * 3:
                cy = np.mean(ys)
                cx = np.mean(xs)
                rx, ry = px_to_m(cx, cy, ref)
                print(f"    Ambiguous shape at ({rx:.2f}m, {ry:.2f}m), area={area}, x_range={x_range}, y_range={y_range}")

    return h_beams, v_beams


def analyze_floor(img_path, label, ref=PX_4F):
    """Analyze a floor plan image."""
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")

    arr = np.array(Image.open(img_path))

    # Define beam colors more precisely based on the legend
    # SB45X60 = bright green: approximately (0, 176, 80) or (0, 200, 0)
    # SB30X60 = yellow: approximately (255, 255, 0)
    # SB25X50 = cyan: approximately (0, 255, 255)
    # B (main beam) = blue: approximately (0, 112, 192) or similar
    # WB (wall beam) = purple

    beam_colors = {
        'SB45X60 (green)': [(34, 177, 76), (0, 176, 80), (0, 200, 0), (0, 160, 0)],
        'SB30X60 (yellow)': [(255, 242, 0), (255, 255, 0), (255, 230, 0)],
        'SB25X50 (cyan)': [(0, 255, 255), (0, 230, 230), (0, 200, 255)],
    }

    for beam_name, color_variants in beam_colors.items():
        print(f"\n  --- {beam_name} ---")

        all_h = []
        all_v = []

        for color in color_variants:
            h_beams, v_beams = find_beams_by_color(arr, color, tolerance=40, min_pixels=80, ref=ref)
            all_h.extend(h_beams)
            all_v.extend(v_beams)

        # Deduplicate beams that are very close
        def dedup(beams, tol=0.3):
            if not beams:
                return []
            unique = [beams[0]]
            for b in beams[1:]:
                is_dup = False
                for u in unique:
                    if abs(b[0]-u[0]) < tol and abs(b[1]-u[1]) < tol and abs(b[2]-u[2]) < tol:
                        is_dup = True
                        break
                if not is_dup:
                    unique.append(b)
            return unique

        all_h = dedup(sorted(all_h))
        all_v = dedup(sorted(all_v))

        if all_h:
            print(f"    X-direction beams (horizontal, constant Y):")
            for y, x1, x2, area in all_h:
                # Determine which bay
                bay = "?"
                for ga, gb, na, nb in [('A','B',0,9.95), ('B','C',9.95,18.40), ('C','D',18.40,30.10)]:
                    if na - 0.5 <= y <= nb + 0.5:
                        bay = f"{ga}-{gb}"
                print(f"      Y={y:.2f}m ({bay}): X={x1:.2f}m ~ {x2:.2f}m  (L={x2-x1:.2f}m, px={area})")

        if all_v:
            print(f"    Y-direction beams (vertical, constant X):")
            for x, y1, y2, area in all_v:
                bay = "?"
                for g1, g2, n1, n2 in [(1,2,0,8.85), (2,3,8.85,17.35), (3,4,17.35,24.45)]:
                    if n1 - 0.5 <= x <= n2 + 0.5:
                        bay = f"{g1}-{g2}"
                print(f"      X={x:.2f}m ({bay}): Y={y1:.2f}m ~ {y2:.2f}m  (L={y2-y1:.2f}m, px={area})")

        if not all_h and not all_v:
            print(f"    No beams detected.")

    return arr


# ============================================================
# 4F~9F Analysis
# ============================================================
print("\n" + "="*80)
print("4F~9F TYPICAL FLOOR (page_08.png)")
print("="*80)

arr = np.array(Image.open(f"{base_path}/page_08.png"))

# Let's sample specific colors at known beam locations to calibrate
# From visual inspection of page_08.png:
# Green beams are visible in the D-C bay and C-B bay areas
# Yellow beams are in the A-B bay area
# Cyan beams appear along edges

# Sample actual pixel colors at locations where beams are visible
sample_points = [
    # (description, x, y) - approximate locations of beams from visual inspection
    ("green beam D-C left", 900, 700),
    ("green beam D-C mid", 1300, 700),
    ("green beam C-B area", 1300, 1200),
    ("yellow beam B-A area", 1300, 1600),
    ("cyan beam edge", 1100, 1500),
    ("blue main beam X-dir D", 1000, 557),
    ("blue main beam Y-dir 1", 780, 800),
]

print("\nColor sampling at known beam locations:")
for desc, x, y in sample_points:
    if 0 <= y < arr.shape[0] and 0 <= x < arr.shape[1]:
        r, g, b = arr[y, x, 0], arr[y, x, 1], arr[y, x, 2]
        print(f"  {desc}: px({x},{y}) -> RGB({r},{g},{b})")

# Let's sample more systematically along horizontal scanlines
print("\nSampling along Y=700px (between D and C grids):")
for x in range(780, 1820, 20):
    r, g, b = arr[700, x, 0], arr[700, x, 1], arr[700, x, 2]
    if not (r > 240 and g > 240 and b > 240):  # Skip white
        rx, ry = px_to_m(x, 700)
        print(f"  X={rx:.2f}m: RGB({r},{g},{b})")

print("\nSampling along Y=800px:")
for x in range(780, 1820, 10):
    r, g, b = arr[800, x, 0], arr[800, x, 1], arr[800, x, 2]
    if not (r > 240 and g > 240 and b > 240):  # Skip white
        rx, ry = px_to_m(x, 800)
        print(f"  X={rx:.2f}m: RGB({r},{g},{b})")

print("\nSampling along Y=900px (closer to C grid):")
for x in range(780, 1820, 10):
    r, g, b = arr[900, x, 0], arr[900, x, 1], arr[900, x, 2]
    if not (r > 240 and g > 240 and b > 240):
        rx, ry = px_to_m(x, 900)
        print(f"  X={rx:.2f}m: RGB({r},{g},{b})")

# Sample vertical direction
print("\nSampling along X=900px (between grid 1 and 2, Y direction):")
for y in range(557, 1838, 10):
    r, g, b = arr[y, 900, 0], arr[y, 900, 1], arr[y, 900, 2]
    if not (r > 240 and g > 240 and b > 240):
        rx, ry = px_to_m(900, y)
        print(f"  Y={ry:.2f}m: RGB({r},{g},{b})")

print("\nSampling along X=1300px (between grid 2 and 3, Y direction):")
for y in range(557, 1838, 10):
    r, g, b = arr[y, 1300, 0], arr[y, 1300, 1], arr[y, 1300, 2]
    if not (r > 240 and g > 240 and b > 240):
        rx, ry = px_to_m(1300, y)
        print(f"  Y={ry:.2f}m: RGB({r},{g},{b})")

print("\nSampling along X=1650px (between grid 3 and 4, Y direction):")
for y in range(557, 1838, 10):
    r, g, b = arr[y, 1650, 0], arr[y, 1650, 1], arr[y, 1650, 2]
    if not (r > 240 and g > 240 and b > 240):
        rx, ry = px_to_m(1650, y)
        print(f"  Y={ry:.2f}m: RGB({r},{g},{b})")

print("\n\nDone.")
