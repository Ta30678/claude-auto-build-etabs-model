"""Test: Units should be TON/M (12)."""


def test_units_are_ton_m(SapModel):
    units = SapModel.GetPresentUnits()
    assert units == 12, f"Units={units}, expected 12 (TON/M)"
