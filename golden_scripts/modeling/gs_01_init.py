"""
Golden Script 01: Model Initialization + Materials

- Connects to ETABS (or creates new model)
- Sets units to TON/M
- Defines all concrete materials (C280~C490) and rebar (SD420, SD490)
"""
import json
import sys
import os

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)                      # modeling/ (sibling imports)
sys.path.insert(0, os.path.dirname(_dir))      # golden_scripts/ (constants)
from constants import (
    UNITS_TON_M, CONCRETE_GRADES, CONCRETE_PROPS, REBAR_PROPS,
)


def connect_etabs(config):
    """Connect to ETABS via COM."""
    try:
        from find_etabs import find_etabs
        etabs, filename = find_etabs(run=False, backup=False)
        SapModel = etabs.SapModel
    except (ImportError, ModuleNotFoundError):
        import comtypes.client
        etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        SapModel = etabs.SapModel
        filename = SapModel.GetModelFilename()
    print(f"Connected to ETABS. File: {filename}")
    return SapModel


def _reacquire_SapModel():
    """Re-acquire SapModel from COM after InitializeNewModel."""
    import comtypes.client
    etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
    return etabs.SapModel


def init_model(SapModel, config):
    """Initialize model: set units, optionally create new blank model.
    Returns (possibly new) SapModel reference.
    """
    project = config.get("project", {})

    if project.get("new_model", False):
        # If no model is open, open backup or any EDB first
        # (ETABS COM requires an open model for File operations)
        current = SapModel.GetModelFilename()
        if not current or current == "None":
            # Look for backup in same MODEL directory
            save_path = project.get("save_path", "")
            if save_path:
                import glob as glob_mod
                model_dir = os.path.dirname(save_path.replace("/", os.sep))
                edbs = glob_mod.glob(os.path.join(model_dir, "*.EDB"))
                if edbs:
                    SapModel.File.OpenFile(edbs[0])
                    print(f"  Opened existing model for init: {edbs[0]}")

        SapModel.InitializeNewModel(UNITS_TON_M)
        # COM reference becomes stale after InitializeNewModel; re-acquire
        SapModel = _reacquire_SapModel()
        SapModel.File.NewBlank()
        print("Created new blank model")

    SapModel.SetPresentUnits(UNITS_TON_M)
    SapModel.SetModelIsLocked(False)
    print(f"Units set to TON/M ({UNITS_TON_M})")
    return SapModel


def define_materials(SapModel, config=None):
    """Define all concrete grades and rebar materials."""
    count = 0

    for fc in CONCRETE_GRADES:
        props = CONCRETE_PROPS[fc]
        mat_name = f"C{fc}"
        try:
            ret = SapModel.PropMaterial.AddMaterial(mat_name, 2, "", "", "")
            # ETABS may auto-rename; use ChangeName to set desired name
            actual = ret[0] if isinstance(ret, (list, tuple)) else mat_name
            if actual != mat_name:
                SapModel.PropMaterial.ChangeName(actual, mat_name)
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
            ret = SapModel.PropMaterial.AddMaterial(rb_name, 5, "", "", "")
            actual = ret[0] if isinstance(ret, (list, tuple)) else rb_name
            if actual != rb_name:
                SapModel.PropMaterial.ChangeName(actual, rb_name)
        except:
            pass

        SapModel.PropMaterial.SetMPIsotropic(rb_name, rb_props["E"], rb_props["nu"], rb_props["Fy"] * 0.00001)
        SapModel.PropMaterial.SetORebar_1(
            rb_name, rb_props["Fy"], rb_props["Fu"],
            rb_props["Fy"], rb_props["Fu"],
            1, 1, 0.01, 0.09, False, False)
        count += 1
        print(f"  Material: {rb_name} (Fy={rb_props['Fy']} ton/m2)")

    print(f"Total materials defined: {count}")
    return count


def run(SapModel, config):
    """Execute step 01: init + materials."""
    print("=" * 60)
    print("STEP 01: Model Initialization + Materials")
    print("=" * 60)

    SapModel = init_model(SapModel, config)
    define_materials(SapModel, config)
    SapModel.View.RefreshView(0, False)
    print("Step 01 complete.\n")
    return SapModel


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "model_config.json"
    with open(config_path) as f:
        config = json.load(f)
    SapModel = connect_etabs(config)
    run(SapModel, config)
