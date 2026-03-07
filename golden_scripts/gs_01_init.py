"""
Golden Script 01: Model Initialization + Materials

- Connects to ETABS (or creates new model)
- Sets units to TON/M
- Defines all concrete materials (C280~C490) and rebar (SD420, SD490)
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from constants import (
    UNITS_TON_M, CONCRETE_GRADES, CONCRETE_PROPS, REBAR_PROPS,
)


def connect_etabs(config):
    """Connect to ETABS using find_etabs (etabs_api package)."""
    from find_etabs import find_etabs
    etabs, filename = find_etabs(run=False, backup=False)
    SapModel = etabs.SapModel
    print(f"Connected to ETABS. File: {filename}")
    return SapModel


def init_model(SapModel, config):
    """Initialize model: set units, optionally create new blank model."""
    project = config.get("project", {})

    if project.get("new_model", False):
        SapModel.InitializeNewModel(UNITS_TON_M)
        SapModel.File.NewBlank()
        print("Created new blank model")

    SapModel.SetPresentUnits(UNITS_TON_M)
    SapModel.SetModelIsLocked(False)
    print(f"Units set to TON/M ({UNITS_TON_M})")


def define_materials(SapModel, config=None):
    """Define all concrete grades and rebar materials."""
    count = 0

    for fc in CONCRETE_GRADES:
        props = CONCRETE_PROPS[fc]
        mat_name = f"C{fc}"
        try:
            SapModel.PropMaterial.AddMaterial(mat_name, 2, "", "", "")
        except:
            pass  # may already exist

        SapModel.PropMaterial.SetMPIsotropic(mat_name, props["E"], props["nu"], props["thermal"])
        SapModel.PropMaterial.SetWeightAndMass(mat_name, 1, props["wt"])
        SapModel.PropMaterial.SetOConcrete_1(
            mat_name, props["fc_tonm2"], False, 1, 2, 1, 0.002, 0.005, -0.1, 0, 0)
        count += 1
        print(f"  Material: {mat_name} (fc={fc} kgf/cm2, E={props['E']:.2e})")

    for rb_name, rb_props in REBAR_PROPS.items():
        try:
            SapModel.PropMaterial.AddMaterial(rb_name, 5, "", "", "")
        except:
            pass

        SapModel.PropMaterial.SetMPIsotropic(rb_name, rb_props["E"], rb_props["nu"], rb_props["Fy"] * 0.00001)
        SapModel.PropMaterial.SetORebar_1(
            rb_name, rb_props["Fy"], rb_props["Fu"],
            rb_props["Fy"], rb_props["Fu"],
            1, 1, 0.01, 0.09, False)
        count += 1
        print(f"  Material: {rb_name} (Fy={rb_props['Fy']} ton/m2)")

    print(f"Total materials defined: {count}")
    return count


def run(SapModel, config):
    """Execute step 01: init + materials."""
    print("=" * 60)
    print("STEP 01: Model Initialization + Materials")
    print("=" * 60)

    init_model(SapModel, config)
    define_materials(SapModel, config)
    SapModel.View.RefreshView(0, False)
    print("Step 01 complete.\n")


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "model_config.json"
    with open(config_path) as f:
        config = json.load(f)
    SapModel = connect_etabs(config)
    run(SapModel, config)
