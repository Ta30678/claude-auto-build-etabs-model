---
name: plan-reader
description: "結構配置圖核心解讀器。從結構平面圖讀取柱、梁、牆、板等構件配置，輸出結構化摘要供 ETABS 建模使用。觸發條件：用戶上傳結構配置圖、提到「結構配置」「讀懂配置」「解讀平面」「構件識別」「梁柱配置」、上傳建築平面 PDF/PPT/截圖、提到 annotation.json、需要從圖面提取結構資訊。此 Skill 協調 plan-reader-elements（構件辨識）和 plan-reader-floors（樓層規則）兩個子技能，確保完整解讀流程。"
---

# 結構配置圖核心解讀器

## 決策流程圖

```
輸入：結構配置圖（PDF/PPT/截圖）
           │
           ▼
  annotation.json 存在？
     ├── Yes → 第二節 Bluebeam 標註流程（精確座標）
     └── No  → plan-reader-floors 第二節（像素量測備案）
           │
           ▼
  辨識構件 → 參考 plan-reader-elements
  樓層對應 → 參考 plan-reader-floors
           │
           ▼
  輸出結構化摘要（第五節格式）
```

**核心原則：從圖面讀取資訊，不做假設。**

---

## 一、工作目錄與檔案管理

結構配置圖相關檔案統一存放在 Case Folder 的 **「結構配置圖」** 子資料夾：

```
{Case Folder}/
├── 結構配置圖/          # 所有結構配置圖相關檔案
│   ├── 1F.png           # 各樓層結構配置圖截圖
│   ├── 2F.png
│   ├── RF.png
│   └── ...
├── SPECTRUM.TXT         # 反應譜檔案
├── EQ_PARAMS.txt        # 地震力參數
└── ...
```

---

## 二、Bluebeam 標註工作流（主要方法）

### 2.1 概述

使用 `pdf_annot_extractor` 從 Bluebeam PDF 自動提取標註精確座標，取代目視判讀和像素量測。

**優勢**：構件座標精確到 mm、比例尺自動計算、圖例自動生成、小梁位置直接可用。

### 2.2 使用條件

- PDF 含有 Bluebeam 標註（Lines, Rectangles, Polygons, FreeText）
- 至少 2 條 Length Measurement 標註（計算比例尺）
- 建議比例尺 variance < 2%

### 2.3 提取指令

```bash
python -m golden_scripts.tools.pdf_annot_extractor --input "結構配置.pdf" --check          # 檢查標註
python -m golden_scripts.tools.pdf_annot_extractor --input "結構配置.pdf" --pages 5 --output annotations.json  # 提取
python -m golden_scripts.tools.pdf_annot_extractor --input "結構配置.pdf" --pages 5 --summary                  # 摘要
```

### 2.4 標註 JSON 結構

JSON 包含 `file`, `scale` (meters_per_point), `pages[]` 每頁含 `annotations`：
- `measurements`: 長度標註（自動計算比例尺）
- `lines`: 線段（含 color_name, direction, meters）
- `rectangles`: 矩形（含 color_name, center_m, size_m）
- `polygons`: 多邊形（含 content, vertices_m）
- `texts`: 文字標註
- `legend.items[]`: 圖例項目（label + nearby_color_name）

### 2.5 標註類型 → 構件映射

| 標註類型 | 構件類型 | 辨識方式 |
|----------|----------|----------|
| `rectangles` (orange/red) | 柱 (Column) | legend 中 label 含「柱」的顏色 |
| `lines` (blue/cyan) | 大梁 (Main Beam) | legend 中 label 含「大梁」「RC大梁」 |
| `lines` (green/pink) | 小梁 (Secondary Beam) | legend 中 label 含「小梁」「SB」 |
| `lines` (brown/dark) | 壁梁 (Wall Beam) | legend 中 label 含「壁梁」「WB」 |
| `polygons` | 剪力牆/板厚 | content 或 legend 文字描述 |
| `measurements` | 比例尺/間距 | 自動計算 meters_per_point |

### 2.6 標註 JSON 與圖面影像分工

| 資訊 | 標註 JSON | 仍需圖面讀取 |
|------|-----------|-------------|
| 構件座標 | 精確 meters | — |
| 比例尺 | 自動計算 | — |
| 圖例對照 | 自動偵測 | 需人工驗證 |
| Grid 名稱/間距 | — | 從圖面讀取 |
| 樓層資訊 | — | 從標題/用戶說明 |
| 建物邊界 | — | 需交叉比對 |

---

## 三、輸入來源與格式

| 來源 | 格式 | 說明 |
|------|------|------|
| Bluebeam Revu | PDF / 截圖 PNG | 建築平面 PDF 上疊加色彩標註 |
| PowerPoint | PPTX / 截圖 PNG | PPT 繪圖工具標註 |
| 手動截圖 | PNG / JPG | 已完成標註的螢幕截圖 |

完整結構配置圖包含：底圖（建築平面）、疊加標註（顏色/線型）、圖例 (Legend)、Grid Line 圈號。

---

## 四、完整解讀流程

依照以下步驟系統性解讀結構配置圖：

```
Step 1  辨識圖面基本資訊
        ├── 樓層（從標題或用戶說明）
        ├── Grid Line 編號（X向數字、Y向字母）
        ├── Grid Line 間距
        └── 累積座標計算
        → 詳見 plan-reader-elements 第三節

Step 2  讀取圖例 (Legend)
        ├── 找到圖例位置
        ├── 逐項記錄「視覺特徵 → 構件名稱」
        └── 建立本圖專用對照表
        → 詳見 plan-reader-elements 第二節

Step 3  辨識所有柱位
        ├── Grid 位置 + 柱尺寸 (C{X向寬}X{Y向深})
        ├── 退縮柱位/斜柱 → 詢問使用者
        └── ETABS 樓層 = 平面圖樓層 + 1
        → 詳見 plan-reader-elements 第一、四節
        → 樓層規則見 plan-reader-floors 第一節

Step 4  辨識所有大梁
        ├── 方向（X/Y）、起終點 Grid Line
        └── 尺寸（從圖例對照）

Step 5  讀取小梁座標
        ├── 主要：從 annotation.json 讀取精確座標
        ├── SB-READER 驗證連接性和合理性
        └── 備案：從圖面像素量測
        → 備案流程見 plan-reader-floors 第二節

Step 6  辨識剪力牆、連續壁和壁梁
        ├── 連續壁材質 = C280（預設）
        └── 剪力牆/連續壁 ETABS 樓層 = 平面圖 + 1

Step 7  判斷樓板區域
        → 詳見 plan-reader-floors 第三節

Step 8  輸出結構化摘要（第五節格式）
```

---

## 五、輸出格式

解讀完成後，以下列格式整理結果（設計為 ETABS 建模的直接輸入）：

```markdown
## {樓層}F 結構配置摘要

### Grid 系統
- X方向：Grid 1 ~ 5
  - 間距 (cm)：860, 860, 860, 860
  - 累積座標 (cm)：0, 860, 1720, 2580, 3440
- Y方向：Grid A ~ D
  - 間距 (cm)：700, 700, 700
  - 累積座標 (cm)：0, 700, 1400, 2100

### 柱配置 (平面圖 {N}F → ETABS {N+1}F)
| Grid 位置 | 柱尺寸 | X座標(cm) | Y座標(cm) | 備註 |
|-----------|--------|-----------|-----------|------|

### 斜撐/斜柱 (如有)
| 起點Grid | 終點Grid | 尺寸 | 起點座標(cm) | 終點座標(cm) | 備註 |
|----------|----------|------|-------------|-------------|------|

### 大梁配置 (ETABS {N}F)
| 方向 | Grid Line | 跨度 | 尺寸 | 起點座標(cm) | 終點座標(cm) |
|------|-----------|------|------|-------------|-------------|

### 小梁配置 (ETABS {N}F)
| 編號 | 方向 | 起點座標(cm) | 終點座標(cm) | 固定軸座標(cm) | 所在區間 | 尺寸 | 連接狀態 |
|------|------|-------------|-------------|---------------|----------|------|---------|

### 剪力牆配置 (平面圖 {N}F → ETABS {N+1}F)
| Grid 位置 | 厚度 | 起點座標(cm) | 終點座標(cm) | 材質 |
|-----------|------|-------------|-------------|------|

### 連續壁配置 (平面圖 {N}F → ETABS {N+1}F)
| Grid 位置 | 厚度 | 起點座標(cm) | 終點座標(cm) | 材質 |
|-----------|------|-------------|-------------|------|

### 壁梁配置 (ETABS {N}F)
| 位置 | 尺寸 | 起點座標(cm) | 終點座標(cm) |
|------|------|-------------|-------------|

### 樓板區域判斷
| Grid 區域 | 打叉 | 四面梁 | 結論 |
|-----------|------|--------|------|

### 屋突核心區 (僅 R2F 以上)
- X/Y 範圍 + Grid + 座標

### 需確認事項
- [ ] 退縮柱位 / 小梁位置不確定 / ...
```

---

## 六、絕對規則與檢核表

### 鐵則（違反即失敗）

**小梁位置絕對禁止用 1/2、1/3 grid 間距猜測或假設等間距配置。**
小梁位置必須從 annotation.json 讀取精確座標（主要），或從圖面像素量測計算（備案）。
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
[ ] 小梁位置精確座標（annotation.json 或像素量測）？
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
