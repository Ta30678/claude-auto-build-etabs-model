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

| Prefix | Type | 中文 | Shell Type |
|--------|------|------|-----------|
| `B` | Beam | 大梁 | — |
| `SB` | Small Beam | 小梁 | — |
| `WB` | Wall Beam | 壁梁 | — |
| `FB` | Foundation Beam | 基礎梁 | — |
| `FSB` | Foundation Small Beam | 基礎小梁 | — |
| `FWB` | Foundation Wall Beam | 基礎壁梁 | — |
| `C` | Column | 柱 | — |
| `W` | Wall | 牆 | Membrane |
| `S` | Slab | 樓板 | Membrane |
| `FS` | Foundation Slab | 基礎版 | ShellThick |

---

## Usage

All agents and skills should:
1. Import classification functions from `golden_scripts.constants`
2. Never hardcode story lists (use the regex-based functions)
3. Reference this glossary for terminology consistency
