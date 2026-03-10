"""
Pytest configuration for ETABS model verification.

Provides SapModel fixture that connects to a running ETABS instance.
Tests verify the model state against expected values from config.
"""
import pytest
import json
import os
import sys


def pytest_addoption(parser):
    parser.addoption(
        "--config", action="store", default=None,
        help="Path to model_config.json for verification"
    )


@pytest.fixture(scope="session")
def SapModel():
    """Connect to running ETABS instance."""
    try:
        from find_etabs import find_etabs
        etabs, filename = find_etabs(run=False, backup=False)
        SapModel = etabs.SapModel
        SapModel.SetPresentUnits(12)  # TON/M
        print(f"\nConnected to ETABS: {filename}")
        return SapModel
    except Exception:
        pass
    try:
        import comtypes.client
        etabs = comtypes.client.GetActiveObject('CSI.ETABS.API.ETABSObject')
        SapModel = etabs.SapModel
        SapModel.SetPresentUnits(12)  # TON/M
        print(f"\nConnected to ETABS via comtypes: {SapModel.GetModelFilename()}")
        return SapModel
    except Exception as e:
        pytest.skip(f"Cannot connect to ETABS: {e}")


@pytest.fixture(scope="session")
def config(request):
    """Load model config for comparison."""
    config_path = request.config.getoption("--config")
    if config_path and os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return None


@pytest.fixture(scope="session")
def all_frames(SapModel):
    """Get all frame data once for the session."""
    ret = SapModel.FrameObj.GetAllFrames(
        0, [], [], [], [], [], [], [], [], [], [], [],
        [], [], [], [], [], [], [], [])
    if isinstance(ret[0], int) and ret[0] > 0:
        return {
            "count": ret[0],
            "names": ret[1],
            "props": ret[2],
            "stories": ret[3],
        }
    return {"count": 0, "names": [], "props": [], "stories": []}
