"""
ETABS Connection Template (comtypes)
Usage: from connect_etabs import get_etabs
       SapModel = get_etabs()
Always sets TON/M units and unlocks model.
"""
import sys
import comtypes.client


def get_etabs():
    """Attach to running ETABS instance, set TON/M units, unlock model."""
    try:
        helper = comtypes.client.CreateObject("ETABSv1.Helper")
        helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)
        EtabsObject = helper.GetObject("CSI.ETABS.API.ETABSObject")
        SapModel = EtabsObject.SapModel
    except Exception as e:
        print(f"ERROR: Cannot connect to ETABS. Is it running?\n{e}")
        sys.exit(1)

    # Set TON/M units (eUnits=12)
    SapModel.SetPresentUnits(12)

    # Unlock model for editing
    SapModel.SetModelIsLocked(False)

    print(f"Connected to ETABS. File: {SapModel.GetModelFilename()}")
    return SapModel


if __name__ == "__main__":
    SapModel = get_etabs()
    print("Connection OK.")
