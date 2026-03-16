---
name: structural-glossary
description: "結構工程術語表。提供上構/下構/屋突/共構/分棟等結構術語的標準定義、樓層分類邏輯、構件前綴對照表。觸發條件：需要查詢結構術語（上構、下構、屋突、共構、分棟、合棟）、確認樓層分類邏輯、查詢構件前綴意義（B/SB/WB/FB/C/W/S/FS）、需要結構工程中英文對照。所有 agent 和 skill 都應參考此術語表以確保用詞一致。"
---

# Structural Glossary (結構術語表)

Canonical definitions for structural terminology used across all agents, skills, and commands.
All classification logic is implemented in `golden_scripts/constants.py`.

---

## Story Classification

| 術語 | English | 樓層範圍 | 判斷邏輯 (regex) | 代碼常數 |
|------|---------|---------|-----------------|---------|
| 下構 | substructure | B*F, 1F | `^B\d+F$` 或 `1F` 或 `BASE` | `is_substructure_story()` |
| 上構 | superstructure | 1MF, 2F ~ RF | 非下構、非屋突 | `is_superstructure_story()` |
| 屋突 | rooftop | R1F ~ PRF | `^R\d*F$` 或 `PRF` | `is_rooftop_story()` |
| 基礎 | foundation | FS | 斷面前綴 `FS`，位於下構最底層上方 | `is_foundation_beam()` |

### Story Ordering (top to bottom in e2k)

```
PRF          ─┐
R3F           │ rooftop (屋突)
R2F           │
R1F / RF     ─┘
NF           ─┐
...           │ superstructure (上構)
2F            │
1MF          ─┘
1F           ─┐
B1F           │ substructure (下構)
B2F           │
...           │
BnF          ─┘
BASE          ← no objects, elevation reference only
```

### Python API (`from golden_scripts.constants import ...`)

```python
is_substructure_story("B2F")   # True
is_substructure_story("1F")    # True
is_substructure_story("2F")    # False

is_superstructure_story("2F")  # True
is_superstructure_story("1MF") # True
is_superstructure_story("B1F") # False
is_superstructure_story("PRF") # False (rooftop)

is_rooftop_story("R1F")       # True
is_rooftop_story("PRF")       # True
is_rooftop_story("RF")        # True
is_rooftop_story("5F")        # False
```

---

## Multi-Building Terminology

| 術語 | English | 定義 |
|------|---------|------|
| 共構 | shared substructure | 多棟共用的下構部分。分棟操作時下構全部保留。 |
| 分棟 | building split | 將全棟模型拆為單棟模型，保留共構下構。靠上構 Diaphragm Name 辨識棟別。 |
| 合棟 | building merge | 各棟上構 + 共構下構 → 合併為全棟模型。 |

### Building Identification

- 上構樓層的 **Diaphragm Name** 即為棟別標識
- 例：`DA` = A棟, `DB` = B棟, `DC` = C棟, `DD` = D棟
- 下構樓層的 Diaphragm 不用於分棟判斷（共用）
- 同一 Diaphragm 下的所有 frame/area objects 屬於該棟

### Split/Merge Flow

```
全棟模型 (.e2k)
    │
    ├── /split ──→ 單棟 A.e2k (上構A + 全部下構)
    ├── /split ──→ 單棟 B.e2k (上構B + 全部下構)
    └── ...

各單棟 .e2k (修改後)
    │
    └── /merge ──→ 合併後全棟模型 (.e2k)
```

---

## Section Prefix Reference

| Prefix | Type | 中文 | Shell Type | 相關技能 |
|--------|------|------|-----------|---------|
| `B` | Beam | 大梁 | — | section-name |
| `SB` | Small Beam | 小梁 | — | section-name |
| `WB` | Wall Beam | 壁梁 | — | section-name |
| `FB` | Foundation Beam | 基礎梁 | — | section-name |
| `FSB` | Foundation Small Beam | 基礎小梁 | — | section-name |
| `FWB` | Foundation Wall Beam | 基礎壁梁 | — | section-name |
| `C` | Column | 柱 | — | section-name |
| `W` | Wall | 牆 | Membrane | — |
| `S` | Slab | 樓板 | Membrane | — |
| `FS` | Foundation Slab | 基礎版 | ShellThick | — |

### Section Naming Format

```
{PREFIX}{WIDTH}X{DEPTH}C{fc}
範例：B55X80C350 = 寬55cm, 深80cm, fc'=350
      C90X90C420 = X向90cm, Y向90cm, fc'=420
```

詳細命名規則見 `section-name` skill。

---

## Floor Classification Rules

| 區分 | ETABS 樓層範圍 | 說明 |
|------|---------------|------|
| 上構 (Superstructure) | 2F 以上（不含 1F） | 地表以上結構物 |
| 下構 (Substructure) | 1F 以下（含 1F） | 地表以下結構物，含 1F |
| 屋突 (Rooftop) | R1F ~ PRF | 頂樓以上樓層 |
| 基礎層 | BASE 上一層 | BASE 本身無物件 |

詳細樓層對應規則見 `plan-reader-floors` 第一節。

---

## Usage

All agents and skills should:
1. Import classification functions from `golden_scripts.constants`
2. Never hardcode story lists (use the regex-based functions)
3. Reference this glossary for terminology consistency

### Cross-References

| 技能 | 用途 |
|------|------|
| `plan-reader` | 結構配置圖核心解讀 |
| `plan-reader-elements` | 構件辨識規則 |
| `plan-reader-floors` | 樓層對應與樓板判斷 |
| `section-name` | 斷面命名與解析規則 |
| `etabs-modeler` | ETABS API 參考（ad-hoc 腳本） |
| `e2k-split` / `e2k-merge` | 分棟/合棟工具 |

---

## Self-Learning Protocol

### 執行前：讀取經驗
載入本 skill 時，讀取 `learned/` 目錄中所有檔案作為補充知識。

### 執行後：紀錄新發現
任務完成後，檢查是否有以下新發現需要紀錄：

1. **patterns.md** — 新的結構術語、未見過的樓層命名慣例
2. **mistakes.md** — 術語誤用及修正
3. **edge-cases.md** — 術語定義不明確的特殊情況

### 紀錄格式
每條紀錄包含：
- **日期**: YYYY-MM-DD
- **案名**: 專案識別
- **發現**: 具體描述
- **處理**: 採取的做法
- **是否應更新 SKILL.md**: Yes/No（如 Yes，標記待更新的 section）

### 紀錄原則
- 不重複紀錄已有的內容
- 先檢查 learned/ 現有內容再寫入
- 每個檔案保持 <100 行，超過時歸納合併舊條目
- 確認為通用規律後（>=2 次出現），才建議更新 SKILL.md 本體
