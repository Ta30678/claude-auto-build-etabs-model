"""
Golden Scripts - Master Orchestrator

Runs all golden scripts in sequence to build an ETABS model from config.

Usage:
    python run_all.py --config model_config.json
    python run_all.py --config model_config.json --steps 1,2,3
    python run_all.py --config model_config.json --dry-run
"""
import json
import sys
import os
import time
import argparse

# Add golden_scripts to path
sys.path.insert(0, os.path.dirname(__file__))

from constants import build_strength_lookup, normalize_stories_order
from modeling import gs_01_init
from modeling import gs_02_sections
from modeling import gs_03_grid_stories
from modeling import gs_04_columns
from modeling import gs_05_walls
from modeling import gs_06_beams
from modeling import gs_07_small_beams
from modeling import gs_08_slabs
from modeling import gs_09_properties
from modeling import gs_10_loads
from modeling import gs_11_diaphragms
from design import gs_12_iterate


MODELING_STEPS = {
    1:  ("Init + Materials",     gs_01_init),
    2:  ("Sections",             gs_02_sections),
    3:  ("Grids + Stories",      gs_03_grid_stories),
    4:  ("Columns",              gs_04_columns),
    5:  ("Walls",                gs_05_walls),
    6:  ("Beams",                gs_06_beams),
    7:  ("Small Beams",          gs_07_small_beams),
    8:  ("Slabs",                gs_08_slabs),
    9:  ("Properties",           gs_09_properties),
    10: ("Loads",                gs_10_loads),
    11: ("Diaphragms",           gs_11_diaphragms),
}
DESIGN_STEPS = {
    12: ("Iterate",              gs_12_iterate),
}
STEPS = {**MODELING_STEPS, **DESIGN_STEPS}


def _read_etabs_elevations(SapModel):
    """Read actual story elevations from ETABS. Returns {name: top_elev} or None."""
    try:
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            "Story Definitions", [], "All", 0, [], 0, [])
        if ret[5] != 0:
            return None
        fields = list(ret[2])
        n_fields = len(fields)
        n_records = ret[3]
        data = list(ret[4])
        elev_map = {}
        for i in range(n_records):
            row = dict(zip(fields, data[i * n_fields:(i + 1) * n_fields]))
            name = row.get("Name", "")
            try:
                elev = float(row.get("Elevation", 0))
            except (ValueError, TypeError):
                continue
            elev_map[name] = elev
        # Rename "Base" -> "BASE" for consistency
        if "Base" in elev_map:
            elev_map["BASE"] = elev_map.pop("Base")
        return elev_map if elev_map else None
    except Exception:
        return None


def run_all(config, steps_to_run=None, dry_run=False, skip_integrity=False):
    """Run all golden scripts in sequence."""
    start_time = time.time()

    project_name = config.get('project', {}).get('name', 'Unknown') if config else '(auto)'

    print("=" * 70)
    print("  GOLDEN SCRIPTS - ETABS Model Builder")
    print(f"  Project: {project_name}")
    steps_label = steps_to_run if steps_to_run else 'MODELING (1-11)'
    print(f"  Steps: {steps_label}")
    print("=" * 70)

    # Integrity verification — prevents element array tampering
    if config and not skip_integrity:
        from tools.config_integrity import verify_integrity
        ok, message = verify_integrity(config)
        if not ok:
            print(f"\n{'='*70}")
            print(f"  INTEGRITY CHECK FAILED")
            print(f"{'='*70}")
            print(f"  {message}")
            print(f"\n  Element arrays (columns/beams/walls/small_beams/slabs)")
            print(f"  must not be modified after config generation.")
            print(f"  Re-run the generating tool to produce a fresh config.")
            print(f"{'='*70}")
            return
    if config:
        config.pop("_integrity", None)

    if dry_run:
        dry_steps = steps_to_run if steps_to_run is not None else set(MODELING_STEPS.keys())
        print("\n[DRY RUN] Would execute the following steps:")
        for num, (name, _) in sorted(STEPS.items()):
            if num in dry_steps:
                print(f"  Step {num:02d}: {name}")
        return

    # Pre-flight validation for steps that use AI-generated JSON (small_beams, slabs)
    if config and steps_to_run:
        from tools.config_merge import validate_config
        errors, warnings = validate_config(config)
        if warnings:
            for w in warnings:
                print(f"  WARNING: {w}")
        if errors:
            print(f"\nPRE-FLIGHT VALIDATION FAILED ({len(errors)} errors):")
            for e in errors:
                print(f"  - {e}")
            print("\nFix the config and rerun. Aborting.")
            return

    # Connect to ETABS
    SapModel = gs_01_init.connect_etabs(config)

    # Always unlock model so element additions work (even when skipping step 1)
    SapModel.SetModelIsLocked(False)

    # Prepare shared data (skip if config=None, step 12 handles it internally)
    # Normalize stories to bottom-to-top order required by next_story()
    # and build_strength_lookup(). Config may store stories in either order.
    if config is not None:
        all_stories = [s["name"] for s in normalize_stories_order(config.get("stories", []))]
        strength_lookup = build_strength_lookup(
            config.get("strength_map", {}), all_stories)
    else:
        all_stories = []
        strength_lookup = {}

    # Pre-build elev_map from config (no ETABS side effects).
    # This allows steps 7,8 to work without step 3 running first.
    # Each story name maps to its TOP elevation (= floor slab elevation).
    # Normalize stories to bottom-to-top before accumulating heights.
    elev_map = None
    if config is not None:
        stories = config.get("stories", [])
        base_elev = config.get("base_elevation", 0)
        if stories:
            stories_ordered = normalize_stories_order(stories)
            elev_map = {}
            elev_map["BASE"] = base_elev
            current_elev = base_elev
            for s in stories_ordered:
                current_elev += s["height"]
                elev_map[s["name"]] = current_elev

    # Phase 2 safety: cross-verify elev_map against ETABS when step 3 is not
    # being run (i.e. stories already exist in ETABS from Phase 1).
    default_steps = steps_to_run if steps_to_run is not None else set(MODELING_STEPS.keys())
    if 3 not in default_steps and elev_map:
        etabs_elev = _read_etabs_elevations(SapModel)
        if etabs_elev:
            mismatches = {k: (elev_map[k], etabs_elev[k])
                          for k in elev_map if k in etabs_elev
                          and abs(elev_map[k] - etabs_elev[k]) > 0.01}
            if mismatches:
                print("\n  WARNING: Config elev_map differs from ETABS:")
                for k, (cfg, etb) in sorted(mismatches.items(),
                                             key=lambda x: x[1][1]):
                    print(f"    {k}: config={cfg:.2f}, ETABS={etb:.2f}")
                print("  Using ETABS elevations instead.\n")
                elev_map = etabs_elev

    results = {}
    for num in sorted(STEPS.keys()):
        if num not in default_steps:
            continue

        name, module = STEPS[num]
        step_start = time.time()

        try:
            if num == 1:
                ret = module.run(SapModel, config)
                if ret is not None:
                    SapModel = ret  # init_model may return fresh COM reference
            elif num == 2:
                module.run(SapModel, config)
                # Re-acquire COM reference after heavy section creation.
                # Step 02 makes thousands of COM calls (SetRectangle + SetRebar)
                # which can corrupt the COM proxy state in comtypes, causing
                # subsequent AddByCoord calls to succeed but report failure.
                SapModel = gs_01_init._reacquire_SapModel()
                SapModel.SetPresentUnits(12)  # Ton_m
                SapModel.SetModelIsLocked(False)
            elif num == 3:
                elev_map = module.run(SapModel, config)
            elif num in (4, 5):
                created = module.run(SapModel, config, elev_map, strength_lookup)
                results[name] = len(created) if created else 0
            elif num in (6, 7, 8):
                created = module.run(SapModel, config, elev_map, strength_lookup)
                results[name] = len(created) if created else 0
            elif num == 9:
                module.run(SapModel, config)
            elif num == 10:
                module.run(SapModel, config, elev_map)
            elif num == 11:
                module.run(SapModel, config)
            elif num == 12:
                module.run(SapModel, config)

            elapsed = time.time() - step_start
            print(f"  [{elapsed:.1f}s]\n")

        except Exception as e:
            print(f"\n  ERROR in step {num} ({name}): {e}")
            import traceback
            traceback.print_exc()
            print(f"\n  Stopping at step {num}. Fix the issue and rerun with --steps {num}")
            break

    # Save model
    save_path = config.get("project", {}).get("save_path") if config else None
    if save_path:
        save_path = os.path.normpath(save_path)
        ret = SapModel.File.Save(save_path)
        if ret == 0:
            print(f"\nModel saved to: {save_path}")
        else:
            print(f"\nWARNING: Save returned {ret}")

    total_time = time.time() - start_time

    # Summary
    print("\n" + "=" * 70)
    print("  BUILD SUMMARY")
    print("=" * 70)
    for name, count in results.items():
        print(f"  {name}: {count} elements")
    print(f"\n  Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Golden Scripts - ETABS Model Builder")
    parser.add_argument("--config", required=False, default=None,
                        help="Path to model_config.json (optional for step 12 only)")
    parser.add_argument("--steps", type=str, default=None,
                        help="Step numbers (e.g. '1,2,3') or alias ('modeling', 'design')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without executing")
    parser.add_argument("--skip-integrity", action="store_true",
                        help="Skip integrity check (for manually edited configs)")
    args = parser.parse_args()

    steps = None
    if args.steps:
        if args.steps.lower() == "modeling":
            steps = set(MODELING_STEPS.keys())
        elif args.steps.lower() == "design":
            steps = set(DESIGN_STEPS.keys())
        else:
            steps = set(int(s.strip()) for s in args.steps.split(","))

    if args.config:
        with open(args.config, encoding="utf-8") as f:
            config = json.load(f)
    else:
        # Config only optional when running step 12 alone
        if steps and steps == {12}:
            config = None
        else:
            parser.error("--config is required (unless running only --steps 12)")

    run_all(config, steps, args.dry_run, args.skip_integrity)


if __name__ == "__main__":
    main()
