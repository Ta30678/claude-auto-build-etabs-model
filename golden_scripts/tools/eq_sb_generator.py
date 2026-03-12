"""
eq_sb_generator.py — 等分小梁座標計算工具

從 eq_sb_rules.json 讀取等分規則，計算精確的等分點座標，
輸出與 annot_to_elements.py phase2 格式完全相同的 sb_elements.json。

用法：
    python -m golden_scripts.tools.eq_sb_generator \
        --rules eq_sb_rules.json \
        --output sb_elements.json \
        [--dry-run]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def generate_equal_sb(rules: list[dict]) -> list[dict]:
    """
    計算等分小梁座標。

    規則：
    - span_axis: "Y" → SB 平行 X 軸（固定 Y 座標），等分 Y 方向跨距
    - span_axis: "X" → SB 平行 Y 軸（固定 X 座標），等分 X 方向跨距
    - divisions: n → 放 n-1 根 SB（在 1/n, 2/n, ..., (n-1)/n 處）
    """
    output_sbs = []

    for rule_idx, rule in enumerate(rules):
        axis = rule["span_axis"]
        start = float(rule["span_start"])
        end = float(rule["span_end"])
        n = int(rule.get("divisions", 2))
        section = rule["section"]
        floors = rule["floors"]

        if n < 2:
            print(
                f"WARNING: rule {rule_idx} has divisions={n} < 2, skipping.",
                file=sys.stderr,
            )
            continue

        if start >= end:
            print(
                f"WARNING: rule {rule_idx} has span_start={start} >= span_end={end}, skipping.",
                file=sys.stderr,
            )
            continue

        # 計算等分點（不含端點）：i = 1, 2, ..., n-1
        for i in range(1, n):
            fixed = start + i * (end - start) / n
            # 四捨五入到 4 位小數（避免浮點誤差累積）
            fixed = round(fixed, 4)

            if axis == "Y":
                # SB 平行 X 軸：固定 Y，延伸 X
                x1 = float(rule["x_from"])
                y1 = fixed
                x2 = float(rule["x_to"])
                y2 = fixed
            elif axis == "X":
                # SB 平行 Y 軸：固定 X，延伸 Y
                x1 = fixed
                y1 = float(rule["y_from"])
                x2 = fixed
                y2 = float(rule["y_to"])
            else:
                print(
                    f"WARNING: rule {rule_idx} has unknown span_axis='{axis}', skipping.",
                    file=sys.stderr,
                )
                continue

            output_sbs.append(
                {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "section": section,
                    "floors": floors,
                }
            )

    return output_sbs


def main():
    parser = argparse.ArgumentParser(
        description="Generate equal-spaced small beam coordinates from eq_sb_rules.json"
    )
    parser.add_argument(
        "--rules", required=True, help="Path to eq_sb_rules.json (EQ-READER output)"
    )
    parser.add_argument(
        "--output", required=True, help="Path to write sb_elements.json"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview output without writing to disk",
    )
    args = parser.parse_args()

    rules_path = Path(args.rules)
    if not rules_path.exists():
        print(f"ERROR: Rules file not found: {rules_path}", file=sys.stderr)
        sys.exit(1)

    with open(rules_path, encoding="utf-8") as f:
        rules_data = json.load(f)

    equal_sb_rules = rules_data.get("equal_sb_rules", [])
    if not equal_sb_rules:
        print("WARNING: No equal_sb_rules found in input file.", file=sys.stderr)

    small_beams = generate_equal_sb(equal_sb_rules)

    # 統計
    total_rules = len(equal_sb_rules)
    total_sbs = len(small_beams)
    sections_used = sorted({sb["section"] for sb in small_beams})

    # 輸出格式與 annot_to_elements.py phase2 完全一致
    output = {
        "small_beams": small_beams,
        "_metadata": {
            "source": "eq_sb_generator",
            "generated_at": datetime.now().isoformat(),
            "rules_file": str(rules_path),
            "total_rules": total_rules,
            "total_sbs": total_sbs,
            "sections": sections_used,
            "note": "Equal-spaced coordinates calculated from model_config.json beam positions. "
            "This is intentional equal-division design, not AI guessing.",
        },
    }

    # 列印摘要
    print(f"Equal SB Generator Summary")
    print(f"  Rules file  : {rules_path}")
    print(f"  Total rules : {total_rules}")
    print(f"  Total SBs   : {total_sbs}")
    print(f"  Sections    : {', '.join(sections_used) if sections_used else '(none)'}")
    print()

    if args.dry_run:
        print("=== DRY RUN — output NOT written ===")
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Output written to: {output_path}")

    # 列印每根 SB 的座標（方便確認）
    print()
    print("Generated SBs:")
    for i, sb in enumerate(small_beams):
        print(
            f"  [{i:3d}] ({sb['x1']:.4f},{sb['y1']:.4f}) → ({sb['x2']:.4f},{sb['y2']:.4f})"
            f"  {sb['section']}  floors={sb['floors']}"
        )


if __name__ == "__main__":
    main()
