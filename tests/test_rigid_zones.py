"""Test: Rigid zone factor should be 0.75 for all frames."""
import pytest


def test_rigid_zone_factor(SapModel, all_frames):
    """All frame objects should have rigid zone factor = 0.75."""
    if all_frames["count"] == 0:
        pytest.skip("No frames in model")

    names = all_frames["names"]
    errors = []
    checked = 0

    for name in names[:100]:  # spot check first 100
        rz = SapModel.FrameObj.GetEndLengthOffset(name, False, 0, 0, 0)
        rz_factor = rz[4]

        if abs(rz_factor - 0.75) > 0.01:
            errors.append(f"{name}: RZ={rz_factor}, expected 0.75")
        checked += 1

    assert len(errors) == 0, (
        f"Rigid zone errors ({len(errors)}/{checked}):\n"
        + "\n".join(errors[:20])
    )
