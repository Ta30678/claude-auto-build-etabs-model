---
name: plan-reader
description: "結構配置圖核心解讀器。從結構平面圖讀取柱、梁、牆、板等構件配置，輸出結構化摘要供 ETABS 建模使用。觸發條件：用戶上傳結構配置圖、提到「結構配置」「讀懂配置」「解讀平面」「構件識別」「梁柱配置」、上傳建築平面 PDF/PPT/截圖、提到 annotation.json、需要從圖面提取結構資訊。此 Skill 協調 plan-reader-elements（構件辨識）和 plan-reader-floors（樓層規則）兩個子技能，確保完整解讀流程。"
---

# 結構配置圖核心解讀器

## 決策流程圖

```
輸入：結構配置圖（PPT/截圖）
           │
           ▼
  pptx_to_elements.py 提取精確座標
           │
           ▼
  辨識構件 → 參考 plan-reader-elements
  樓層對應 → 參考 plan-reader-floors
  斷面命名 → 參考 section-name
           │
           ▼
  輸出結構化摘要（第四節格式）
```

**核心原則：從圖面讀取資訊，不做假設。**

---

## 一、工作目錄與檔案管理

結構配置圖相關檔案統一存放在 Case Folder，Phase 1/2 中間檔案結構如下：

```
{Case Folder}/
├── 結構配置圖/
│   ├── SLIDES INFO/             # Phase 1: per-slide extraction output
│   │   └── {floor_label}/       # Per-floor subdirectory
│   │       ├── {floor_label}.json       # Per-slide JSON (PPT-米座標)
│   │       ├── grid_anchors_{fl}.json   # READER Grid anchor positions
│   │       └── screenshots/             # Cropped PNGs for this floor
│   ├── grid_info.json           # Phase 1 READER output (outline/stories — AI)
│   └── SB-BEAM/                 # Phase 2: SB-READER validation results
├── calibrated/                  # Phase 1: Grid-calibrated per-slide JSONs
│   └── {floor_label}/
│       └── elements.json
├── elements.json                # Phase 1 merged (elements_merge.py --inputs-dir calibrated/)
├── elements_validated.json      # Phase 1 beam-snapped elements (beam_validate.py)
├── beam_validation_report.json  # Phase 1 beam endpoint correction report
├── grid_data.json               # Phase 0.3 ETABS Grid read (ground truth)
├── sb_elements.json             # Phase 2 script output (small beams — PPTX-meter)
├── sb_elements_aligned.json     # Phase 2 affine-calibrated (grid-aligned)
├── model_config.json            # Phase 1 output (no SB/slabs)
├── sb_patch.json                # Phase 2 output (SB only, no slabs)
├── merged_config.json           # Merged (base + SB patch)
├── snapped_config.json          # Snap-corrected config
└── final_config.json            # Final config with auto-generated slabs
```

---

## 二、輸入來源與格式

| 來源          | 格式            | 說明                        |
| ------------- | --------------- | --------------------------- |
| Bluebeam Revu | PDF / 截圖 PNG  | 建築平面 PDF 上疊加色彩標註 |
| PowerPoint    | PPTX / 截圖 PNG | PPT 繪圖工具標註            |
| 手動截圖      | PNG / JPG       | 已完成標註的螢幕截圖        |

完整結構配置圖包含：底圖（建築平面）、疊加標註（顏色/線型）、圖例 (Legend)、Grid Line 圈號。

---

## 三、完整解讀流程

Phase 1 READER 的實際工作流：

```
Step 0  Prerequisites
        ├── read_grid.py → grid_data.json（從 ETABS 讀取 Grid 為 ground truth）
        └── pptx_to_elements.py --scan-floors → PAGE_FLOOR_MAPPING（樓層標籤偵測）

Step 1  Per-slide extraction
        └── pptx_to_elements.py --slides-info-dir "SLIDES INFO" --page-floors "{floors}"
            → SLIDES INFO/{floor_label}/{floor_label}.json (PPT-米座標, per-slide)

Step 2  圖例讀取（自動）
        └── pptx_to_elements.py 自動從 PPT 2-column 表格提取
        → 詳見 plan-reader-elements 第一節

Step 3  Grid anchor identification
        └── READER 識別 PPT 中的 Grid 標記位置
        → SLIDES INFO/{fl}/grid_anchors_{fl}.json

Step 4  Affine calibration
        └── affine_calibrate.py --mode grid
        → calibrated/{fl}/elements.json (Grid 座標)

Step 5  Merge + Validate
        ├── elements_merge.py --inputs-dir calibrated/ → elements.json (auto-globs */elements.json)
        └── beam_validate.py (per-slide, in Step E3.5)

Step 6  Grid 驗證 + building_outline + core_grid_area
        └── READER 驗證 Grid 對齊、定義建物外框與屋突核心區

Step 7  config_build
        └── config_build.py → model_config.json

Step 8  輸出 grid_info.json
        └── READER 輸出 Grid 驗證結果、outline、core_area
```

---

## 四、輸出格式

解讀完成後，以下列格式整理結果（設計為 ETABS 建模的直接輸入）：

```markdown
## {樓層}F 結構配置摘要

### Grid 系統

- X方向：Grid [從圖面讀取的名稱和順序]
  - 名稱：[實際圈號，按圖面順序]
  - 間距 (cm)：[依序]
  - 累積座標 (cm)：0, ...
  - 方向說明：[例如「由左至右遞增」或「由右至左遞增」]
- Y方向：Grid [從圖面讀取的名稱和順序]
  - 名稱：[實際圈號，按圖面順序]
  - 間距 (cm)：[依序]
  - 累積座標 (cm)：0, ...
  - 方向說明：[例如「由下至上遞增」或「由上至下遞增」]

### 柱配置 (平面圖 {N}F → ETABS {N+1}F)

| Grid 位置 | 柱尺寸 | X座標(cm) | Y座標(cm) | 備註 |
| --------- | ------ | --------- | --------- | ---- |

### 斜撐/斜柱 (如有)

| 起點Grid | 終點Grid | 尺寸 | 起點座標(cm) | 終點座標(cm) | 備註 |
| -------- | -------- | ---- | ------------ | ------------ | ---- |

### 大梁配置 (ETABS {N}F)

| 方向 | Grid Line | 跨度 | 尺寸 | 起點座標(cm) | 終點座標(cm) |
| ---- | --------- | ---- | ---- | ------------ | ------------ |

### 小梁配置 (ETABS {N}F)

| 編號 | 方向 | 起點座標(cm) | 終點座標(cm) | 固定軸座標(cm) | 所在區間 | 尺寸 | 連接狀態 |
| ---- | ---- | ------------ | ------------ | -------------- | -------- | ---- | -------- |

### 剪力牆配置 (平面圖 {N}F → ETABS {N+1}F)

| Grid 位置 | 厚度 | 起點座標(cm) | 終點座標(cm) | 材質 |
| --------- | ---- | ------------ | ------------ | ---- |

### 連續壁配置 (平面圖 {N}F → ETABS {N+1}F)

| Grid 位置 | 厚度 | 起點座標(cm) | 終點座標(cm) | 材質 |
| --------- | ---- | ------------ | ------------ | ---- |

### 壁梁配置 (ETABS {N}F)

| 位置 | 尺寸 | 起點座標(cm) | 終點座標(cm) |
| ---- | ---- | ------------ | ------------ |

### 樓板區域判斷

| Grid 區域 | 打叉 | 四面梁 | 結論 |
| --------- | ---- | ------ | ---- |

### 建築外框 (Building Outline)

- 形狀：[矩形/L型/T型/U型/不規則]
- 外框座標 (m)：[[x1,y1], [x2,y2], [x3,y3], ...]（順時針或逆時針）
- 凹口區域：Grid [X範圍] / [Y範圍]（無結構，不建柱/梁/板）

### 屋突核心區 (僅 R2F 以上)

- X/Y 範圍 + Grid + 座標

### 需確認事項

- [ ] 退縮柱位 / 小梁位置不確定 / ...
```

---

## 五、絕對規則與檢核表

### 鐵則（違反即失敗）

**小梁位置絕對禁止用 1/2、1/3 grid 間距猜測或假設等間距配置。**
小梁位置必須從 pptx_to_elements.py 提取精確座標（主要），或從圖面像素量測計算（備案）。
小梁位置由結構工程師根據住宅單元隔間決定，每根位置都不同。用等分假設建模等同於造假數據。

### 應該做的

- 從圖例讀取顏色與構件對應關係，每張圖獨立建立對照表
- 明確區分平面圖樓層與 ETABS 樓層（柱/牆 +1 規則）
- 利用 Grid 間距等比例計算小梁位置（精確到 cm）
- 柱尺寸注意 X/Y 方向對應（C{X向寬}X{Y向深}）
- 連續壁預設材質 C280
- 退縮柱位主動詢問使用者；斜柱標記為 BRACE
- 遇到無法辨識的項目主動詢問用戶

### 不應該做的

- 假設「紅色一定是柱」或「藍色一定是大梁」
- 跨樓層推斷構件尺寸（每層獨立讀取）
- 僅描述小梁大概位置而不計算精確座標
- 從舊模型複製或按比例縮放小梁位置
- 將退縮柱位自行處理而不詢問使用者

### 快速檢核清單

```
[ ] 讀取圖例中所有構件類型？
[ ] 所有柱位記錄？（含 X/Y 向尺寸確認）
[ ] 所有大梁記錄（含方向和跨度）？
[ ] 小梁位置精確座標（pptx_to_elements.py 或像素量測）？
[ ] 小梁兩端接觸其他構件？（懸空=可疑）
[ ] 剪力牆和壁梁辨識？
[ ] 連續壁標記材質 C280？
[ ] 樓層對應正確？（柱/牆 → ETABS +1）
[ ] Grid 間距和累積座標記錄？
[ ] 退縮柱位標記並詢問使用者？
[ ] 斜柱標記為 BRACE？
[ ] 柱連續性檢查？
[ ] 輸出包含精確座標？
[ ] 打叉叉區域辨識？每區域建板/不建板判斷？
[ ] R2F 以上屋突核心區辨識？
[ ] 不規則平面缺角標記為不建板？
```

---

## Self-Learning Protocol

### 執行前：讀取經驗

載入本 skill 時，讀取 `learned/` 目錄中所有檔案作為補充知識。

### 執行後：紀錄新發現

任務完成後，檢查是否有以下新發現需要紀錄：

1. **patterns.md** — 新的命名模式、未見過的圖例符號、新的構件配置方式
2. **mistakes.md** — 本次犯的錯誤及修正方法（含根因分析）
3. **edge-cases.md** — 規則未覆蓋的特殊情況及處理決策

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
