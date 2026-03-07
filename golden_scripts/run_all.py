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

from constants import build_strength_lookup
import gs_01_init
import gs_02_sections
import gs_03_grid_stories
import gs_04_columns
import gs_05_walls
import gs_06_beams
import gs_07_small_beams
import gs_08_slabs
import gs_09_properties
import gs_10_loads
import gs_11_diaphragms


STEPS = {
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


def run_all(config, steps_to_run=None, dry_run=False):
    """Run all golden scripts in sequence."""
    start_time = time.time()

    print("=" * 70)
    print("  GOLDEN SCRIPTS - ETABS Model Builder")
    print(f"  Project: {config.get('project', {}).get('name', 'Unknown')}")
    print(f"  Steps: {steps_to_run if steps_to_run else 'ALL'}")
    print("=" * 70)

    if dry_run:
        print("\n[DRY RUN] Would execute the following steps:")
        for num, (name, _) in sorted(STEPS.items()):
            if steps_to_run is None or num in steps_to_run:
                print(f"  Step {num:02d}: {name}")
        return

    # Connect to ETABS
    SapModel = gs_01_init.connect_etabs(config)

    # Prepare shared data
    all_stories = [s["name"] for s in config.get("stories", [])]
    strength_lookup = build_strength_lookup(
        config.get("strength_map", {}), all_stories)

    elev_map = None
    results = {}

    for num in sorted(STEPS.keys()):
        if steps_to_run is not None and num not in steps_to_run:
            continue

        name, module = STEPS[num]
        step_start = time.time()

        try:
            if num == 1:
                module.run(SapModel, config)
            elif num == 2:
                module.run(SapModel, config)
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

            elapsed = time.time() - step_start
            print(f"  [{elapsed:.1f}s]\n")

        except Exception as e:
            print(f"\n  ERROR in step {num} ({name}): {e}")
            import traceback
            traceback.print_exc()
            print(f"\n  Stopping at step {num}. Fix the issue and rerun with --steps {num}")
            break

    # Save model
    save_path = config.get("project", {}).get("save_path")
    if save_path:
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
    parser.add_argument("--config", required=True, help="Path to model_config.json")
    parser.add_argument("--steps", type=str, default=None,
                        help="Comma-separated step numbers to run (e.g. '1,2,3')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without executing")
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    steps = None
    if args.steps:
        steps = set(int(s.strip()) for s in args.steps.split(","))

    run_all(config, steps, args.dry_run)


if __name__ == "__main__":
    main()
