---
name: section-name
description: "斷面命名與解析規則。涵蓋柱/梁/牆/板的命名慣例、D/B Swap、Parsing 演算法、強度分配、柱筋分配。觸發條件：需要解讀斷面名稱（如 B55X80、C90X90、SB35X65）、D/B swap 規則、T3/T2 對應、斷面命名格式、parse_frame_section、parse_area_section、強度分配表、柱筋 NumR2/NumR3 計算。"
---

# 斷面命名與解析規則

本技能涵蓋所有結構斷面的命名慣例、API 參數對應、解析演算法、強度分配、柱筋計算。

---

## 一、命名慣例 (Naming Convention)

### 1.1 Frame Sections (柱/梁)

| Element Type | Format | Example | T3 (Depth) | T2 (Width) |
|---|---|---|---|---|
| Beam | `B{W}X{D}[C{fc}]` | B55X80C350 | 0.80 | 0.55 |
| Small Beam | `SB{W}X{D}[C{fc}]` | SB35X65C280 | 0.65 | 0.35 |
| Wall Beam | `WB{W}X{D}[C{fc}]` | WB50X70C350 | 0.70 | 0.50 |
| Foundation Beam | `FB{W}X{D}[C{fc}]` | FB90X230C420 | 2.30 | 0.90 |
| Foundation Small Beam | `FSB{W}X{D}[C{fc}]` | FSB40X80C280 | 0.80 | 0.40 |
| Foundation Wall Beam | `FWB{W}X{D}[C{fc}]` | FWB40X80C350 | 0.80 | 0.40 |
| Column | `C{Xwidth}X{Ydepth}[C{fc}]` | C150X130C420 | 1.30 | 1.50 |

### 1.2 Area Sections (牆/板)

| Element Type | Format | Example | Shell Type |
|---|---|---|---|
| Slab | `S{T}[C{fc}]` | S15C280 | Membrane (2) |
| Wall | `W{T}[C{fc}]` | W20C350 | Membrane (2) |
| Foundation Slab | `FS{T}[C{fc}]` | FS100C350 | ShellThick (1) |

### 1.3 Column Naming Detail

```
C{Xwidth}X{Ydepth}
├── Xwidth = Global X 方向（水平）長度 (cm)
└── Ydepth = Global Y 方向（垂直）長度 (cm)

範例：C120X180 = X向 120cm, Y向 180cm
      → 水平方向較短，垂直方向較長
```

---

## 二、D/B Swap 規則 (CRITICAL)

命名格式與 API 參數順序不同，必須交換：

```
Name:  {PREFIX}{WIDTH}X{DEPTH}
API:   SetRectangle(Name, Material, T3=Depth, T2=Width)
                                    ^^^^^^^^  ^^^^^^^^
                                    先深度     再寬度
```

### 範例

```
B55X80C350 → W=55, D=80 → SetRectangle("B55X80C350", "C350", 0.80, 0.55)
C90X90C420 → W=90, D=90 → SetRectangle("C90X90C420", "C420", 0.90, 0.90)
SB35X65C280 → W=35, D=65 → SetRectangle("SB35X65C280", "C280", 0.65, 0.35)
```

---

## 三、Parsing 演算法

標準函式位於 `golden_scripts/constants.py`。

### 3.1 Frame Section

```python
import re

def parse_frame_section(name):
    """Parse frame section name -> (prefix, width_cm, depth_cm, fc_or_None).

    B55X80 -> ('B', 55, 80, None)
    B55X80C350 -> ('B', 55, 80, 350)
    C90X90C420 -> ('C', 90, 90, 420)
    """
    m = re.match(r'^(B|SB|WB|FB|FSB|FWB|C)(\d+)X(\d+)(?:C(\d+))?$', name)
    if m:
        fc = int(m.group(4)) if m.group(4) else None
        return m.group(1), int(m.group(2)), int(m.group(3)), fc
    return None, None, None, None
```

### 3.2 Area Section

```python
def parse_area_section(name):
    """Parse area section name -> (prefix, thickness_cm, fc_or_None).

    S15 -> ('S', 15, None)
    S15C280 -> ('S', 15, 280)
    FS100C350 -> ('FS', 100, 350)
    """
    m = re.match(r'^(S|W|FS)(\d+)(?:C(\d+))?$', name)
    if m:
        fc = int(m.group(3)) if m.group(3) else None
        return m.group(1), int(m.group(2)), fc
    return None, None, None
```

---

## 四、強度分配 (Strength Assignment)

### 4.1 strength_map 格式

config 中的 `strength_map` 以樓層範圍為 key：

```json
{
  "B3F~1F": {"column": 490, "beam": 420, "wall": 420, "slab": 280},
  "2F~7F":  {"column": 420, "beam": 350, "wall": 350, "slab": 280},
  "8F~RF":  {"column": 350, "beam": 280, "wall": 280, "slab": 280}
}
```

### 4.2 命名組合

最終斷面名稱 = base section + C{fc}：

```
Plan-reader output:  "B55X80"  at floor "5F"
Strength table:      5F beam → C350
→ Section name:      "B55X80C350"
```

### 4.3 Expansion 規則

每個 base section 只跨 concrete grade 建立（不再有 ±20cm size expansion）。
例：B55X80 + [C280, C350, C420] → B55X80C280, B55X80C350, B55X80C420

---

## 五、柱筋分配 (Column Bar Distribution)

標準函式：`constants.calc_column_bar_distribution(width_cm, depth_cm)`

### 5.1 計算規則

NumR2（沿寬度）和 NumR3（沿深度）按 W:D 比例計算：

```python
def calc_column_bar_distribution(width_cm, depth_cm):
    ratio = width_cm / depth_cm
    if abs(ratio - 1.0) < 0.1:
        return 3, 3  # square
    if ratio > 1:
        num_r3 = 2
        num_r2 = max(2, min(6, round(2 * ratio)))
    else:
        num_r2 = 2
        num_r3 = max(2, min(6, round(2 / ratio)))
    return num_r2, num_r3
```

### 5.2 範例表格

| Column | W:D Ratio | NumR2 | NumR3 |
|--------|-----------|-------|-------|
| C90X90 | 1:1 | 3 | 3 |
| C60X90 | 2:3 | 2 | 3 |
| C150X130 | ~1.15:1 | 3 | 3 |
| C60X120 | 1:2 | 2 | 4 |
| C120X60 | 2:1 | 4 | 2 |

### 5.3 其他柱筋常數

| 常數 | 值 | 說明 |
|------|-----|------|
| Cover | 7 cm | 柱保護層 |
| Corner Bars | 4 | 角隅鋼筋數 |
| Tie Spacing | 15 cm | 繫筋間距 |
| Rebar Size | #8 | 主筋號數 |
| Tie Size | #4 | 繫筋號數 |

---

## Self-Learning Protocol

### 執行前：讀取經驗

載入本 skill 時，讀取 `learned/` 目錄中所有檔案作為補充知識。

### 執行後：紀錄新發現

任務完成後，檢查是否有以下新發現需要紀錄：

1. **patterns.md** — 新的命名模式、未見過的斷面格式
2. **mistakes.md** — 命名或 D/B swap 相關錯誤及修正
3. **edge-cases.md** — 特殊斷面命名或解析邊界情況

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
