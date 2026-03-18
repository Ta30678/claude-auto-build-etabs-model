"""
Diagnostic tool: compare ETABS story elevations vs config elev_map.

Helps diagnose floor-mismapping issues where elements end up on wrong stories.

Usage:
    python -m golden_scripts.tools.diagnose_elev --config model_config.json
"""
import json
import sys
import os
import argparse

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_dir, ".."))  # golden_scripts/
from constants import normalize_stories_order, is_substructure_story


def _connect():
    """Connect to running ETABS, return SapModel."""
    try:
        from find_etabs import find_etabs
        etabs, filename = find_etabs(run=False, backup=False)
        SapModel = etabs.SapModel
    except (ImportError, ModuleNotFoundError):
        import comtypes.client
        etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        SapModel = etabs.SapModel
    SapModel.SetPresentUnits(12)  # TON/M
    return SapModel


def read_etabs_elevations(SapModel):
    """Read story elevations from ETABS. Returns {name: elevation}."""
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Story Definitions", [], "All", 0, [], 0, [])
    if ret[0] != 0:
        print("ERROR: Cannot read Story Definitions from ETABS")
        return {}

    fields = list(ret[4])
    n_fields = len(fields)
    n_records = ret[5]
    data = list(ret[6])

    elev_map = {}
    for i in range(n_records):
        row = dict(zip(fields, data[i * n_fields:(i + 1) * n_fields]))
        name = row.get("Name", "")
        try:
            elev = float(row.get("Elevation", 0))
        except (ValueError, TypeError):
            elev = 0.0
        elev_map[name] = elev

    # Rename "Base" -> "BASE"
    if "Base" in elev_map:
        elev_map["BASE"] = elev_map.pop("Base")

    return elev_map


def compute_elev_map(config, use_reversed=False):
    """Compute elev_map from config.

    If use_reversed=True, uses the old (buggy) reversed() logic.
    If use_reversed=False, uses normalize_stories_order().
    """
    stories = config.get("stories", [])
    base_elev = config.get("base_elevation", 0)

    if not stories:
        return {}

    if use_reversed:
        ordered = list(reversed(stories))
    else:
        ordered = normalize_stories_order(stories)

    elev_map = {"BASE": base_elev}
    current = base_elev
    for s in ordered:
        current += s["height"]
        elev_map[s["name"]] = current
    return elev_map


def diagnose(config_path):
    """Run full diagnosis."""
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    print("=" * 80)
    print("  ELEVATION DIAGNOSTIC")
    print(f"  Config: {config_path}")
    print("=" * 80)

    # 1. Config story order detection
    stories = config.get("stories", [])
    if not stories:
        print("ERROR: No stories in config")
        return

    first_name = stories[0]["name"]
    last_name = stories[-1]["name"]
    first_is_sub = is_substructure_story(first_name)
    last_is_sub = is_substructure_story(last_name)

    print(f"\n  Config stories: {len(stories)} stories")
    print(f"  First: {first_name} (substructure={first_is_sub})")
    print(f"  Last:  {last_name} (substructure={last_is_sub})")

    if first_is_sub and not last_is_sub:
        print("  --> Config order: BOTTOM-TO-TOP (B3F...PRF)")
        print("  --> reversed() would INVERT this (WRONG)")
        print("  --> normalize_stories_order() keeps as-is (CORRECT)")
    elif last_is_sub and not first_is_sub:
        print("  --> Config order: TOP-TO-BOTTOM (PRF...B3F)")
        print("  --> reversed() would fix this (CORRECT)")
        print("  --> normalize_stories_order() reverses (CORRECT)")
    else:
        print("  --> Config order: AMBIGUOUS")

    # 2. Compute both elev_maps
    elev_normalized = compute_elev_map(config, use_reversed=False)
    elev_reversed = compute_elev_map(config, use_reversed=True)

    # 3. Read ETABS
    print("\n  Connecting to ETABS...")
    SapModel = _connect()
    print(f"  Model: {SapModel.GetModelFilename()}")
    etabs_elev = read_etabs_elevations(SapModel)

    if not etabs_elev:
        print("  WARNING: No stories found in ETABS. Showing config-only comparison.\n")
        print(f"  {'Story':<10} {'Normalized':>12} {'Reversed':>12}")
        print(f"  {'-'*10} {'-'*12} {'-'*12}")
        for name in [s["name"] for s in normalize_stories_order(stories)]:
            n = elev_normalized.get(name, 0)
            r = elev_reversed.get(name, 0)
            diff_marker = " <-- DIFF" if abs(n - r) > 0.01 else ""
            print(f"  {name:<10} {n:>12.2f} {r:>12.2f}{diff_marker}")
        return

    # 4. Compare
    all_names = ["BASE"] + [s["name"] for s in normalize_stories_order(stories)]

    print(f"\n  {'Story':<10} {'ETABS':>10} {'Normalized':>12} {'Reversed':>12} {'Match?':>10}")
    print(f"  {'-'*10} {'-'*10} {'-'*12} {'-'*12} {'-'*10}")

    norm_match = 0
    rev_match = 0
    total = 0

    for name in all_names:
        e = etabs_elev.get(name)
        n = elev_normalized.get(name)
        r = elev_reversed.get(name)

        if e is None:
            print(f"  {name:<10} {'N/A':>10} {n or 0:>12.2f} {r or 0:>12.2f} {'MISSING':>10}")
            continue

        total += 1
        n_ok = n is not None and abs(n - e) <= 0.01
        r_ok = r is not None and abs(r - e) <= 0.01

        if n_ok:
            norm_match += 1
        if r_ok:
            rev_match += 1

        if n_ok and r_ok:
            match = "BOTH"
        elif n_ok:
            match = "NORM"
        elif r_ok:
            match = "REV"
        else:
            match = "NONE"

        print(f"  {name:<10} {e:>10.2f} {n or 0:>12.2f} {r or 0:>12.2f} {match:>10}")

    # Summary
    print(f"\n  {'='*60}")
    print(f"  Normalized match: {norm_match}/{total}")
    print(f"  Reversed match:   {rev_match}/{total}")

    if norm_match > rev_match:
        print("  --> normalize_stories_order() is CORRECT")
        if rev_match == total:
            print("  --> (Both match — stories were already top-to-bottom)")
    elif rev_match > norm_match:
        print("  --> reversed() was CORRECT (config is top-to-bottom)")
        print("  --> normalize_stories_order() should also handle this!")
    elif norm_match == rev_match == total:
        print("  --> Both methods match ETABS (stories order doesn't matter here)")
    else:
        print("  --> NEITHER method fully matches ETABS!")
        print("  --> Check if stories were manually edited in ETABS")
    print(f"  {'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose story elevation mismatch between config and ETABS")
    parser.add_argument("--config", required=True, help="Path to model_config.json")
    args = parser.parse_args()
    diagnose(args.config)


if __name__ == "__main__":
    main()
