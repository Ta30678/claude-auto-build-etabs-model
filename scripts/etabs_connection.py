"""
ETABS API Connection Module
============================
Provides functions to connect to a running ETABS instance or start a new one.
Uses COM automation via comtypes (Windows).

Usage:
    from etabs_connection import connect_to_etabs, start_new_etabs, get_model

ETABS 22 Installation Path:
    C:/Program Files/Computers and Structures/ETABS 22/ETABS.exe
"""

import os
import sys
import comtypes.client

# ETABS 22 installation path
ETABS_EXE_PATH = r"C:\Program Files\Computers and Structures\ETABS 22\ETABS.exe"
ETABS_API_DLL = r"C:\Program Files\Computers and Structures\ETABS 22\ETABSv1.dll"


def _ensure_api_registered():
    """Ensure the ETABS API type library is accessible."""
    if not os.path.exists(ETABS_API_DLL):
        raise FileNotFoundError(f"ETABS API DLL not found: {ETABS_API_DLL}")


def connect_to_etabs():
    """
    Connect to an already-running ETABS instance.

    Returns:
        tuple: (EtabsObject, SapModel)
            - EtabsObject: The ETABS application COM object
            - SapModel: The SapModel object for API operations

    Raises:
        Exception: If no running ETABS instance is found.
    """
    _ensure_api_registered()
    helper = comtypes.client.CreateObject("CSI.ETABS.API.ETABSObject")
    EtabsObject = helper.QueryInterface(
        comtypes.client.gen_dir and
        comtypes.gen.ETABSv1.cOAPI or
        helper
    )
    # Alternative approach: get running instance
    try:
        EtabsObject = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
    except OSError:
        raise Exception(
            "No running ETABS instance found. "
            "Please open ETABS first, or use start_new_etabs()."
        )
    SapModel = EtabsObject.SapModel
    return EtabsObject, SapModel


def start_new_etabs(visible=True):
    """
    Start a new ETABS instance.

    Args:
        visible (bool): Whether the ETABS window should be visible.

    Returns:
        tuple: (EtabsObject, SapModel)
    """
    _ensure_api_registered()
    helper = comtypes.client.CreateObject("CSI.ETABS.API.ETABSObject")
    EtabsObject = helper
    EtabsObject.ApplicationStart()
    SapModel = EtabsObject.SapModel
    return EtabsObject, SapModel


def attach_to_etabs():
    """
    Attach to ETABS using the helper object approach.
    This is the most reliable method for ETABS 22.

    Returns:
        tuple: (EtabsObject, SapModel)
    """
    _ensure_api_registered()
    # Create helper
    helper = comtypes.client.CreateObject("CSI.ETABS.API.ETABSObject")

    # Try to get active instance first
    try:
        EtabsObject = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
    except OSError:
        # No running instance; start new
        EtabsObject = helper
        EtabsObject.ApplicationStart()

    SapModel = EtabsObject.SapModel
    return EtabsObject, SapModel


def get_model(SapModel):
    """
    Get basic information about the current model.

    Args:
        SapModel: The SapModel object.

    Returns:
        dict: Model information including filename, units, etc.
    """
    info = {}
    info["filename"] = SapModel.GetModelFilename()
    info["is_locked"] = SapModel.GetModelIsLocked()

    # Get present units
    # 1=lb_in, 2=lb_ft, 3=kip_in, 4=kip_ft, 5=kN_mm, 6=kN_m,
    # 7=kgf_mm, 8=kgf_m, 9=N_mm, 10=N_m, 11=Ton_mm, 12=Ton_m,
    # 13=kN_cm, 14=kgf_cm, 15=N_cm, 16=Ton_cm
    units_map = {
        1: "lb_in", 2: "lb_ft", 3: "kip_in", 4: "kip_ft",
        5: "kN_mm", 6: "kN_m", 7: "kgf_mm", 8: "kgf_m",
        9: "N_mm", 10: "N_m", 11: "Ton_mm", 12: "Ton_m",
        13: "kN_cm", 14: "kgf_cm", 15: "N_cm", 16: "Ton_cm"
    }
    unit_code = SapModel.GetPresentUnits()
    info["units"] = units_map.get(unit_code, f"Unknown({unit_code})")

    return info


# Unit constants for SetPresentUnits
class Units:
    lb_in = 1
    lb_ft = 2
    kip_in = 3
    kip_ft = 4
    kN_mm = 5
    kN_m = 6
    kgf_mm = 7
    kgf_m = 8
    N_mm = 9
    N_m = 10
    Ton_mm = 11
    Ton_m = 12
    kN_cm = 13
    kgf_cm = 14
    N_cm = 15
    Ton_cm = 16


if __name__ == "__main__":
    print("Attempting to connect to running ETABS...")
    try:
        EtabsObject, SapModel = attach_to_etabs()
        info = get_model(SapModel)
        print(f"Connected successfully!")
        print(f"  Filename: {info['filename']}")
        print(f"  Units: {info['units']}")
        print(f"  Model locked: {info['is_locked']}")
    except Exception as e:
        print(f"Error: {e}")
