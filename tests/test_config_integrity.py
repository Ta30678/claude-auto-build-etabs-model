"""Tests for config integrity verification."""
import copy
import json
import pytest

from golden_scripts.tools.config_integrity import (
    ELEMENT_KEYS,
    compute_integrity,
    stamp_config,
    verify_integrity,
)


def _make_config():
    """Return a minimal config with some elements."""
    return {
        "columns": [
            {"name": "C1", "section": "C80X80", "x": 0, "y": 0, "floors": ["1F"]},
            {"name": "C2", "section": "C80X80", "x": 6, "y": 0, "floors": ["1F"]},
        ],
        "beams": [
            {"name": "B1", "section": "B40X70", "x1": 0, "y1": 0,
             "x2": 6, "y2": 0, "floors": ["2F"]},
        ],
        "walls": [
            {"name": "W1", "section": "W25", "x1": 0, "y1": 0,
             "x2": 0, "y2": 4, "floors": ["1F"]},
        ],
        "small_beams": [],
        "slabs": [],
    }


class TestComputeIntegrity:
    def test_compute_basic(self):
        """Counts and hash structure are correct."""
        config = _make_config()
        result = compute_integrity(config)

        assert "element_counts" in result
        assert "element_hash" in result
        assert result["element_counts"]["columns"] == 2
        assert result["element_counts"]["beams"] == 1
        assert result["element_counts"]["walls"] == 1
        assert result["element_counts"]["small_beams"] == 0
        assert result["element_counts"]["slabs"] == 0
        assert len(result["element_hash"]) == 64  # SHA-256 hex

    def test_hash_deterministic(self):
        """Same input always produces same hash."""
        config = _make_config()
        h1 = compute_integrity(config)["element_hash"]
        h2 = compute_integrity(config)["element_hash"]
        assert h1 == h2


class TestStampAndVerify:
    def test_stamp_and_verify_pass(self):
        """Round-trip stamp → verify passes."""
        config = _make_config()
        stamp_config(config)
        assert "_integrity" in config
        ok, msg = verify_integrity(config)
        assert ok is True
        assert msg == "OK"

    def test_stamp_idempotent(self):
        """Stamping twice produces the same result."""
        config = _make_config()
        stamp_config(config)
        first = copy.deepcopy(config["_integrity"])
        stamp_config(config)
        second = config["_integrity"]
        assert first == second

    def test_empty_arrays(self):
        """Config with all empty arrays still works."""
        config = {k: [] for k in ELEMENT_KEYS}
        stamp_config(config)
        ok, msg = verify_integrity(config)
        assert ok is True


class TestVerifyFailures:
    def test_missing_integrity_fails(self):
        """No _integrity field → fail."""
        config = _make_config()
        ok, msg = verify_integrity(config)
        assert ok is False
        assert "Missing _integrity" in msg

    def test_deleted_column_fails(self):
        """Remove 1 column → count mismatch detected."""
        config = _make_config()
        stamp_config(config)
        config["columns"].pop()
        ok, msg = verify_integrity(config)
        assert ok is False
        assert "columns" in msg
        assert "DELETED" in msg

    def test_deleted_beam_fails(self):
        """Remove 1 beam → count mismatch detected."""
        config = _make_config()
        stamp_config(config)
        config["beams"].pop()
        ok, msg = verify_integrity(config)
        assert ok is False
        assert "beams" in msg
        assert "DELETED" in msg

    def test_modified_coordinate_fails(self):
        """Change a coordinate → hash mismatch (counts unchanged)."""
        config = _make_config()
        stamp_config(config)
        config["columns"][0]["x"] = 999
        ok, msg = verify_integrity(config)
        assert ok is False
        assert "hash mismatch" in msg

    def test_added_element_fails(self):
        """Add an element → count mismatch detected."""
        config = _make_config()
        stamp_config(config)
        config["small_beams"].append(
            {"name": "SB1", "section": "SB20X40",
             "x1": 1, "y1": 1, "x2": 5, "y2": 1, "floors": ["2F"]}
        )
        ok, msg = verify_integrity(config)
        assert ok is False
        assert "small_beams" in msg
        assert "ADDED" in msg
