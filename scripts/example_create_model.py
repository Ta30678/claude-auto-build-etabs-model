"""
Example: Create a simple RC building model from scratch.
Demonstrates the full workflow of model creation via ETABS API.

This creates a 5-story RC building with:
- 3x3 bays, 8m x 8m each
- Story height: 3.4m (typical), 4.2m (1F)
- Concrete: fc'=280 kgf/cm2
- Columns: 80x80 cm
- Beams: 40x70 cm
- Slab: 15 cm thick
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etabs_connection import attach_to_etabs, Units
from etabs_utils import (
    new_model, save_model,
    add_concrete_material, add_rebar_material,
    add_rectangular_column, add_rectangular_beam, add_slab,
    add_load_pattern, run_analysis
)


def main():
    print("Connecting to ETABS...")
    EtabsObject, SapModel = attach_to_etabs()

    # Initialize new model in kgf-cm
    print("Creating new blank model...")
    new_model(SapModel, units=Units.kgf_cm)

    # ---- Define Materials ----
    print("Defining materials...")
    SapModel.PropMaterial.SetMaterial("C280", 2)  # 2=Concrete
    SapModel.PropMaterial.SetMPIsotropic("C280", 252671, 0.2, 0.0000099)

    SapModel.PropMaterial.SetMaterial("SD420", 6)  # 6=Rebar
    SapModel.PropMaterial.SetMPIsotropic("SD420", 2040000, 0.3, 0.0000117)

    # ---- Define Sections ----
    print("Defining sections...")
    SapModel.PropFrame.SetRectangle("C80x80", "C280", 80, 80)
    SapModel.PropFrame.SetRectangle("B40x70", "C280", 70, 40)
    SapModel.PropArea.SetSlab("S15", 0, 2, "C280", 15)

    # ---- Define Stories ----
    print("Defining stories...")
    story_names = ["Base", "1F", "2F", "3F", "4F", "5F"]
    story_heights = [0, 420, 340, 340, 340, 340]
    n = len(story_names)
    SapModel.Story.SetStories_2(
        0,  # base elevation
        n,
        story_names,
        story_heights,
        [True, True, True, True, True, True],  # is_master
        ["", "", "", "", "", ""],  # similar_to
        [False] * n,  # splice_above
        [0.0] * n,  # splice_height
        [0] * n  # color
    )

    # ---- Define Grid / Geometry ----
    print("Creating structural elements...")

    # Grid coordinates (cm)
    x_grids = [0, 800, 1600, 2400]  # 3 bays @ 8m
    y_grids = [0, 800, 1600, 2400]  # 3 bays @ 8m

    # Story elevations (cumulative, cm)
    elevations = [0, 420, 760, 1100, 1440, 1780]

    # Add columns at every grid intersection, every story
    for floor_idx in range(len(elevations) - 1):
        z_bot = elevations[floor_idx]
        z_top = elevations[floor_idx + 1]
        for x in x_grids:
            for y in y_grids:
                name = [""]
                SapModel.FrameObj.AddByCoord(
                    x, y, z_bot,
                    x, y, z_top,
                    name, "C80x80"
                )

    # Add beams along X direction at each floor (excluding base)
    for floor_idx in range(1, len(elevations)):
        z = elevations[floor_idx]
        for y in y_grids:
            for i in range(len(x_grids) - 1):
                name = [""]
                SapModel.FrameObj.AddByCoord(
                    x_grids[i], y, z,
                    x_grids[i + 1], y, z,
                    name, "B40x70"
                )

    # Add beams along Y direction at each floor
    for floor_idx in range(1, len(elevations)):
        z = elevations[floor_idx]
        for x in x_grids:
            for i in range(len(y_grids) - 1):
                name = [""]
                SapModel.FrameObj.AddByCoord(
                    x, y_grids[i], z,
                    x, y_grids[i + 1], z,
                    name, "B40x70"
                )

    # Add floor slabs at each level
    for floor_idx in range(1, len(elevations)):
        z = elevations[floor_idx]
        for i in range(len(x_grids) - 1):
            for j in range(len(y_grids) - 1):
                x = [x_grids[i], x_grids[i + 1], x_grids[i + 1], x_grids[i]]
                y = [y_grids[j], y_grids[j], y_grids[j + 1], y_grids[j + 1]]
                z_list = [z, z, z, z]
                name = [""]
                SapModel.AreaObj.AddByCoord(4, x, y, z_list, name, "S15")

    # ---- Load Patterns ----
    print("Defining load patterns...")
    SapModel.LoadPatterns.Add("Dead", 1, 1.0, True)  # self weight multiplier = 1
    SapModel.LoadPatterns.Add("SDL", 2, 0, True)      # super dead
    SapModel.LoadPatterns.Add("Live", 3, 0, True)     # live

    # ---- Refresh View ----
    SapModel.View.RefreshView(0, False)

    # ---- Save ----
    save_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "models", "example_5story.EDB"
    )
    save_path = os.path.normpath(save_path)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    print(f"Saving model to: {save_path}")
    SapModel.File.Save(save_path)

    print("\nModel created successfully!")
    print(f"  Stories: {len(elevations) - 1}")
    print(f"  Columns: {(len(elevations) - 1) * len(x_grids) * len(y_grids)}")
    print(f"  Beams (X): {(len(elevations) - 1) * len(y_grids) * (len(x_grids) - 1)}")
    print(f"  Beams (Y): {(len(elevations) - 1) * len(x_grids) * (len(y_grids) - 1)}")
    print(f"  Slabs: {(len(elevations) - 1) * (len(x_grids) - 1) * (len(y_grids) - 1)}")


if __name__ == "__main__":
    main()
