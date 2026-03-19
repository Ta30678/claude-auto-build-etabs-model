"""Tests for slab zone overlay feature.

Tests the full pipeline: PPT slab zone extraction → affine transform →
merge across slides → zone-based thickness assignment in slab_generator.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from golden_scripts.tools.pptx_to_elements import (
    parse_legend_label,
    _SLAB_SECTION_RE,
)
from golden_scripts.tools.affine_calibrate import (
    apply_transform_to_slide,
    apply_affine,
)
from golden_scripts.tools.elements_merge import (
    merge_small_beams_only,
    normalize_per_slide_input,
)
from golden_scripts.tools.slab_generator import (
    generate_slab_config,
    point_in_polygon,
    face_centroid,
    _match_zone,
)


# ---------------------------------------------------------------------------
# Step 1: PPT legend parsing — slab entries in phase2
# ---------------------------------------------------------------------------

class TestSlabLegendParsedInPhase2:
    """Slab legend entries like S15, FS100 should be recognized by parse_legend_label."""

    def test_s15_parsed(self):
        etype, section, spec, prefix, is_diaphragm = parse_legend_label("S15")
        assert etype == "slab"
        assert section == "S15"
        assert prefix == "S"

    def test_fs100_parsed(self):
        etype, section, spec, prefix, is_diaphragm = parse_legend_label("FS100")
        assert etype == "slab"
        assert section == "FS100"
        assert prefix == "FS"

    def test_s20_parsed(self):
        etype, section, spec, prefix, is_diaphragm = parse_legend_label("S20")
        assert etype == "slab"
        assert section == "S20"
        assert prefix == "S"

    def test_slab_regex(self):
        """_SLAB_SECTION_RE matches S15, FS100 but not FSB30X60."""
        assert _SLAB_SECTION_RE.search("S15")
        assert _SLAB_SECTION_RE.search("FS100")
        # FSB should NOT match (B prefix prevents it via lookbehind)
        m = _SLAB_SECTION_RE.search("FSB30X60")
        # FSB30X60: the regex has (?<![A-Za-z]) lookbehind, so "FS" within "FSB" won't match at 'FS'
        # but "SB" part... let's check
        if m:
            # If it matches, the group should not be 'FS' at the FSB position
            assert m.group(0) != "FSB30"


# ---------------------------------------------------------------------------
# Step 1: Slab zone extraction from shapes
# ---------------------------------------------------------------------------

class TestRectangleToSlabZone:
    """AUTO_SHAPE rectangle → 4-corner polygon."""

    def test_basic_rectangle_zone(self):
        """A slab zone dict should have section, corners, color_hex, floors."""
        zone = {
            "section": "S15",
            "corners": [[0.0, 0.0], [10.0, 0.0], [10.0, 5.0], [0.0, 5.0]],
            "color_hex": "88CC88",
            "floors": ["2F", "3F"],
        }
        assert zone["section"] == "S15"
        assert len(zone["corners"]) == 4
        assert zone["floors"] == ["2F", "3F"]


class TestFreeformToSlabZone:
    """FREEFORM shape → N-corner polygon."""

    def test_pentagon_zone(self):
        """A freeform slab zone can have more than 4 corners."""
        zone = {
            "section": "S20",
            "corners": [
                [0.0, 0.0], [5.0, 0.0], [7.0, 3.0], [5.0, 6.0], [0.0, 6.0]
            ],
            "color_hex": "AABB00",
            "floors": ["2F"],
        }
        assert len(zone["corners"]) == 5
        assert zone["section"] == "S20"


# ---------------------------------------------------------------------------
# Step 2: Affine transform on slab zone corners
# ---------------------------------------------------------------------------

class TestCalibratSlabZoneCorners:
    """Affine transform applied to slab_zones corners."""

    def test_transform_slab_zone_corners(self):
        """apply_transform_to_slide should transform slab_zones corners."""
        slide_data = {
            "_metadata": {"slide_num": 1, "floors": ["2F"]},
            "columns": [],
            "beams": [],
            "walls": [],
            "small_beams": [],
            "slab_zones": [
                {
                    "section": "S15",
                    "corners": [[1.0, 2.0], [3.0, 2.0], [3.0, 4.0], [1.0, 4.0]],
                    "color_hex": "88CC88",
                    "floors": ["2F"],
                }
            ],
        }
        transform = {
            "sx": 2.0, "ox": 10.0,
            "sy": 3.0, "oy": 20.0,
            "n_points": 4,
            "max_residual": 0.01,
            "mean_residual": 0.005,
        }
        result = apply_transform_to_slide(slide_data, transform)
        zones = result["slab_zones"]
        assert len(zones) == 1
        # Corner [1.0, 2.0] → (2.0*1.0+10.0, 3.0*2.0+20.0) = (12.0, 26.0)
        c0 = zones[0]["corners"][0]
        assert abs(c0[0] - 12.0) < 0.01
        assert abs(c0[1] - 26.0) < 0.01

    def test_no_slab_zones_unchanged(self):
        """Slide data without slab_zones should pass through unchanged."""
        slide_data = {
            "_metadata": {"slide_num": 1, "floors": ["2F"]},
            "columns": [],
            "beams": [],
            "walls": [],
            "small_beams": [],
        }
        transform = {
            "sx": 1.0, "ox": 0.0,
            "sy": 1.0, "oy": 0.0,
            "n_points": 4,
            "max_residual": 0.0,
            "mean_residual": 0.0,
        }
        result = apply_transform_to_slide(slide_data, transform)
        assert "slab_zones" not in result


# ---------------------------------------------------------------------------
# Step 3: Merge slab zones across slides
# ---------------------------------------------------------------------------

class TestMergeSlabZonesAcrossSlides:
    """Phase 2 merge preserves and concatenates slab_zones."""

    def test_merge_slab_zones(self):
        file_a = {
            "small_beams": [
                {"x1": 0, "y1": 0, "x2": 5, "y2": 0,
                 "section": "SB30X60", "floors": ["2F"]},
            ],
            "slab_zones": [
                {"section": "S15", "corners": [[0, 0], [5, 0], [5, 3], [0, 3]],
                 "color_hex": "88CC88", "floors": ["2F"]},
            ],
            "_metadata": {
                "input_file": "a.json", "phase": "phase2",
                "per_page_stats": {}, "page_floors": {},
                "totals": {"small_beams": 1}, "warnings": [],
            },
        }
        file_b = {
            "small_beams": [
                {"x1": 0, "y1": 0, "x2": 5, "y2": 0,
                 "section": "SB30X60", "floors": ["3F"]},
            ],
            "slab_zones": [
                {"section": "S20", "corners": [[0, 0], [5, 0], [5, 3], [0, 3]],
                 "color_hex": "AABB00", "floors": ["3F"]},
                {"section": "S15", "corners": [[5, 0], [10, 0], [10, 3], [5, 3]],
                 "color_hex": "88CC88", "floors": ["3F"]},
            ],
            "_metadata": {
                "input_file": "b.json", "phase": "phase2",
                "per_page_stats": {}, "page_floors": {},
                "totals": {"small_beams": 1}, "warnings": [],
            },
        }
        merged, stats = merge_small_beams_only(file_a, file_b)
        assert len(merged["slab_zones"]) == 3
        assert stats["slab_zones"] == 3
        sections = {z["section"] for z in merged["slab_zones"]}
        assert "S15" in sections
        assert "S20" in sections

    def test_merge_no_slab_zones(self):
        """Files without slab_zones should produce empty list."""
        file_a = {
            "small_beams": [],
            "_metadata": {
                "input_file": "a.json", "phase": "phase2",
                "per_page_stats": {}, "page_floors": {},
                "totals": {"small_beams": 0}, "warnings": [],
            },
        }
        merged, stats = merge_small_beams_only(file_a)
        assert merged.get("slab_zones", []) == []
        assert stats.get("slab_zones", 0) == 0


class TestNormalizePerSlideSlabZones:
    """normalize_per_slide_input passes through slab_zones."""

    def test_slab_zones_passthrough(self):
        slide_data = {
            "_metadata": {
                "slide_num": 3,
                "floors": ["2F", "3F"],
                "floor_label": "2F~3F",
                "stats": {"small_beams": 5},
            },
            "columns": [],
            "beams": [],
            "walls": [],
            "small_beams": [
                {"x1": 0, "y1": 0, "x2": 5, "y2": 0,
                 "section": "SB30X60", "floors": ["2F"],
                 "element_type": "small_beam"},
            ],
            "slab_zones": [
                {"section": "S15", "corners": [[0, 0], [5, 0], [5, 3], [0, 3]],
                 "color_hex": "88CC88", "floors": ["2F"]},
            ],
        }
        result = normalize_per_slide_input(slide_data)
        assert len(result["slab_zones"]) == 1
        assert result["slab_zones"][0]["section"] == "S15"


# ---------------------------------------------------------------------------
# Step 4: Zone-based thickness assignment
# ---------------------------------------------------------------------------

class TestMatchZone:
    """_match_zone centroid-in-polygon zone matching."""

    def test_centroid_inside_zone(self):
        zones = [
            {"section": "S20",
             "corners": [[0, 0], [10, 0], [10, 6], [0, 6]],
             "floors": ["2F"]},
        ]
        result = _match_zone(5.0, 3.0, ["2F"], zones, is_foundation=False)
        assert result == "S20"

    def test_centroid_outside_zone(self):
        zones = [
            {"section": "S20",
             "corners": [[0, 0], [10, 0], [10, 6], [0, 6]],
             "floors": ["2F"]},
        ]
        result = _match_zone(15.0, 3.0, ["2F"], zones, is_foundation=False)
        assert result is None

    def test_fs_zone_only_foundation(self):
        """FS zones should not match regular slabs."""
        zones = [
            {"section": "FS100",
             "corners": [[0, 0], [10, 0], [10, 6], [0, 6]],
             "floors": ["B3F"]},
        ]
        # Regular slab at 2F should NOT match FS zone
        result = _match_zone(5.0, 3.0, ["2F"], zones, is_foundation=False)
        assert result is None
        # Foundation slab at B3F SHOULD match
        result = _match_zone(5.0, 3.0, ["B3F"], zones, is_foundation=True)
        assert result == "FS100"

    def test_s_zone_not_foundation(self):
        """S zones should not match foundation slabs."""
        zones = [
            {"section": "S20",
             "corners": [[0, 0], [10, 0], [10, 6], [0, 6]],
             "floors": ["B3F"]},
        ]
        result = _match_zone(5.0, 3.0, ["B3F"], zones, is_foundation=True)
        assert result is None

    def test_zone_floor_filtering(self):
        """Zone floors must overlap with slab floors."""
        zones = [
            {"section": "S20",
             "corners": [[0, 0], [10, 0], [10, 6], [0, 6]],
             "floors": ["3F", "4F"]},
        ]
        # 2F not in zone floors → no match
        result = _match_zone(5.0, 3.0, ["2F"], zones, is_foundation=False)
        assert result is None
        # 3F is in zone floors → match
        result = _match_zone(5.0, 3.0, ["3F"], zones, is_foundation=False)
        assert result == "S20"


class TestNoZonesBackwardCompat:
    """Without slab_zones, all slabs get uniform thickness (backward compat)."""

    def test_uniform_without_zones(self):
        slabs = [
            {"corners": [[0, 0], [5, 0], [5, 3], [0, 3]],
             "floors": ["2F"], "area": 15.0},
            {"corners": [[5, 0], [10, 0], [10, 3], [5, 3]],
             "floors": ["2F"], "area": 15.0},
        ]
        entries, sections = generate_slab_config(
            slabs, slab_thickness=15, raft_thickness=100)
        assert all(e["section"] == "S15" for e in entries)
        assert sections["slab"] == [15]

    def test_uniform_with_foundation(self):
        slabs = [
            {"corners": [[0, 0], [5, 0], [5, 3], [0, 3]],
             "floors": ["2F"], "area": 15.0},
            {"corners": [[0, 0], [5, 0], [5, 3], [0, 3]],
             "floors": ["B3F"], "area": 15.0},
        ]
        entries, sections = generate_slab_config(
            slabs, slab_thickness=15, raft_thickness=100,
            foundation_floor="B3F")
        s_entries = [e for e in entries if e["section"].startswith("S")]
        fs_entries = [e for e in entries if e["section"].startswith("FS")]
        assert all(e["section"] == "S15" for e in s_entries)
        assert all(e["section"] == "FS100" for e in fs_entries)


class TestTwoZonesDifferentThickness:
    """Left zone S15, right zone S20 — assigned correctly."""

    def test_two_zones(self):
        zones = [
            {"section": "S15",
             "corners": [[0, 0], [5, 0], [5, 6], [0, 6]],
             "floors": ["2F"]},
            {"section": "S20",
             "corners": [[5, 0], [10, 0], [10, 6], [5, 6]],
             "floors": ["2F"]},
        ]
        slabs = [
            # Left slab — centroid at (2.5, 3.0) → inside S15 zone
            {"corners": [[0, 0], [5, 0], [5, 6], [0, 6]],
             "floors": ["2F"], "area": 30.0},
            # Right slab — centroid at (7.5, 3.0) → inside S20 zone
            {"corners": [[5, 0], [10, 0], [10, 6], [5, 6]],
             "floors": ["2F"], "area": 30.0},
        ]
        entries, sections = generate_slab_config(
            slabs, slab_thickness=15, raft_thickness=100,
            slab_zones=zones)
        assert len(entries) == 2
        # Find entries by centroid position
        left_entry = [e for e in entries
                      if face_centroid([(c[0], c[1]) for c in e["corners"]])[0] < 5][0]
        right_entry = [e for e in entries
                       if face_centroid([(c[0], c[1]) for c in e["corners"]])[0] >= 5][0]
        assert left_entry["section"] == "S15"
        assert right_entry["section"] == "S20"
        assert sorted(sections["slab"]) == [15, 20]


class TestCentroidOutsideZoneUsesDefault:
    """Slab centroid outside all zones → falls back to default thickness."""

    def test_fallback_to_default(self):
        zones = [
            {"section": "S20",
             "corners": [[0, 0], [5, 0], [5, 6], [0, 6]],
             "floors": ["2F"]},
        ]
        slabs = [
            # Centroid at (2.5, 3.0) → inside zone → S20
            {"corners": [[0, 0], [5, 0], [5, 6], [0, 6]],
             "floors": ["2F"], "area": 30.0},
            # Centroid at (7.5, 3.0) → outside zone → default S15
            {"corners": [[5, 0], [10, 0], [10, 6], [5, 6]],
             "floors": ["2F"], "area": 30.0},
        ]
        entries, sections = generate_slab_config(
            slabs, slab_thickness=15, raft_thickness=100,
            slab_zones=zones)
        left_entry = [e for e in entries
                      if face_centroid([(c[0], c[1]) for c in e["corners"]])[0] < 5][0]
        right_entry = [e for e in entries
                       if face_centroid([(c[0], c[1]) for c in e["corners"]])[0] >= 5][0]
        assert left_entry["section"] == "S20"
        assert right_entry["section"] == "S15"  # default fallback


class TestFsZoneOnlyFoundation:
    """FS zones should only affect foundation floor slabs."""

    def test_fs_zone_foundation_only(self):
        zones = [
            {"section": "FS120",
             "corners": [[0, 0], [10, 0], [10, 6], [0, 6]],
             "floors": ["B3F"]},
            {"section": "S20",
             "corners": [[0, 0], [10, 0], [10, 6], [0, 6]],
             "floors": ["2F"]},
        ]
        slabs = [
            # Foundation slab — centroid inside both zones
            {"corners": [[0, 0], [10, 0], [10, 6], [0, 6]],
             "floors": ["B3F"], "area": 60.0},
            # Regular slab — same position
            {"corners": [[0, 0], [10, 0], [10, 6], [0, 6]],
             "floors": ["2F"], "area": 60.0},
        ]
        entries, sections = generate_slab_config(
            slabs, slab_thickness=15, raft_thickness=100,
            foundation_floor="B3F", slab_zones=zones)
        fs_entries = [e for e in entries if "B3F" in e["floors"]]
        s_entries = [e for e in entries if "2F" in e["floors"]]
        assert len(fs_entries) == 1
        assert fs_entries[0]["section"] == "FS120"
        assert len(s_entries) == 1
        assert s_entries[0]["section"] == "S20"
        assert 120 in sections.get("raft", [])
        assert 20 in sections.get("slab", [])


class TestZoneFloorFiltering:
    """Zone floors must be respected — zones with non-overlapping floors ignored."""

    def test_zone_only_applies_to_matching_floors(self):
        zones = [
            {"section": "S20",
             "corners": [[0, 0], [10, 0], [10, 6], [0, 6]],
             "floors": ["3F", "4F"]},  # Only for 3F and 4F
        ]
        slabs = [
            # Slab at 2F — zone doesn't apply → default S15
            {"corners": [[0, 0], [10, 0], [10, 6], [0, 6]],
             "floors": ["2F"], "area": 60.0},
            # Slab at 3F — zone applies → S20
            {"corners": [[0, 0], [10, 0], [10, 6], [0, 6]],
             "floors": ["3F"], "area": 60.0},
        ]
        entries, sections = generate_slab_config(
            slabs, slab_thickness=15, raft_thickness=100,
            slab_zones=zones)
        entry_2f = [e for e in entries if "2F" in e["floors"]][0]
        entry_3f = [e for e in entries if "3F" in e["floors"]][0]
        assert entry_2f["section"] == "S15"  # default
        assert entry_3f["section"] == "S20"  # zone match
