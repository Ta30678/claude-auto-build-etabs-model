---
description: "BTS Phase 1 — 啟動 3 人 Agent Team 建立主結構（Grid+Story+柱+牆+大梁）。使用方式：/bts-structure [樓層/圖片說明]"
argument-hint: "[樓層說明或附加指示]"
---

# BTS-STRUCTURE — Phase 1: 主結構建模

你現在是 **BTS-STRUCTURE 團隊的 Team Lead**，負責協調 3 位 Agent 建立主結構模型。

**Phase 1 範圍**：Grid、Story、柱(C)、牆(W)、大梁(B/WB/FB/FWB)
**不包含**：小梁(SB/FSB)、樓板(S/FS)——由 Phase 2 `/bts-sb` 處理

---

## 鐵則（ABSOLUTE RULES）

1. **結構配置從圖面讀取，禁止從舊模型複製。**
2. **建物範圍需交叉比對結構配置圖和建築平面圖。**
3. **Grid 名稱/方向/順序必須從圖面讀取，禁止假設。**
4. **連續壁是牆，不是梁。使用現有 Grid 座標。**
5. **每案獨立**——禁止從記憶推斷。

---

## 團隊編制

| Agent | 代號 | Agent 定義檔 | 職責 |
|-------|------|-------------|------|
| Agent 1 | **READER-A** | `.claude/agents/phase1-reader.md` | 讀取分配的樓層範圍（Grid+柱+梁+牆） |
| Agent 2 | **READER-B** | `.claude/agents/phase1-reader.md` | 讀取分配的樓層範圍（Grid+柱+梁+牆） |
| Agent 3 | **CONFIG-BUILDER** | `.claude/agents/phase1-config-builder.md` | 從 folders 讀取 → model_config.json |

---

## 執行流程

### Phase 0: 確認輸入

**必要參數清單（MUST ASK）**：

| # | 參數 | 說明 | 預設值 |
|---|------|------|--------|
| 1 | 結構配置圖 | 路徑 `{Case Folder}/結構配置圖/` | 自動掃描 |
| 2 | 樓層高度表 | 各樓層高度 (m)，含基礎層 | **無，必問** |
| 3 | 強度分配表 | 混凝土等級 by 樓層區段 | **無，必問** |
| 4 | 基礎 Kv | 彈簧係數 | 可選 |
| 5 | 邊梁 Kw | 側邊彈簧 | 可選 |
| 6 | 反應譜檔案 | SPECTRUM.TXT | 可選 |
| 7 | Base Shear C | 地震力係數 | 可選 |
| 8 | EQV Scale Factor | 放大係數 | 可選 |
| 9 | 板厚 | 各區 (cm)，Phase 1 記錄但不建板 | **無，必問** |
| 10 | 基礎樓層 | BASE 上一層 | **無，必問** |
| 11 | EDB 存檔路徑 | 模型檔路徑 | **無，必問** |

### Phase 0.5: Bluebeam 標註提取

```bash
python -m golden_scripts.tools.pdf_annot_extractor \
  --input "{Case Folder}/結構配置圖/結構尺寸配置.pdf" \
  --pages {頁碼} \
  --output "{Case Folder}/結構配置圖/annotations.json" \
  --crop --crop-dir "{Case Folder}/結構配置圖/"
```

### Phase 0.7: 分析樓層分佈 & 建立資料夾

1. **讀取 annotations.json**，分析各頁的樓層標註
2. **建立子資料夾**（如尚未存在）：
   ```bash
   mkdir -p "{Case Folder}/結構配置圖/BEAM"
   mkdir -p "{Case Folder}/結構配置圖/COLUMN"
   mkdir -p "{Case Folder}/結構配置圖/WALL"
   ```
3. **決定樓層分工**：
   - 根據 annotations 中各頁的樓層標註，將頁面分為兩組
   - 原則：工作量大致相等
   - 例如：READER-A 負責 2F~23F（典型樓層），READER-B 負責 B3F~1F + RF~PRF

### Phase 1: 建立 Team + 創建任務

```
TeamCreate(team_name="bts-structure-team", description="BTS Phase 1 主結構建模")
```

| Task | 主題 | Owner | blockedBy |
|------|------|-------|-----------|
| T1 | READER-A 讀圖 | READER-A | (無) |
| T2 | READER-B 讀圖 | READER-B | (無) |
| T3 | CONFIG-BUILDER 生成 config | CONFIG-BUILDER | T1, T2 |
| T4 | 執行 Golden Scripts | (Team Lead) | T3 |

### Phase 2: 啟動 3 個 Agent

**同時**啟動 READER-A、READER-B、CONFIG-BUILDER，全部 `run_in_background=true`。

```
Task(
  subagent_type="phase1-reader",
  team_name="bts-structure-team",
  name="READER-A",
  description="讀取結構配置圖（樓層組 1）",
  prompt="你被指派為 BTS-STRUCTURE Team 的 READER-A。

結構配置圖路徑：{Case Folder}/結構配置圖/
你負責的樓層範圍：{GROUP_1_FLOORS}
對應的 PDF 頁面/裁切圖：{GROUP_1_PAGES}
標註 JSON：{Case Folder}/結構配置圖/annotations.json

請按照 .claude/agents/phase1-reader.md 的指示執行。
先讀取 skills/plan-reader/SKILL.md 了解完整流程。
優先使用 annotation.json 的精確座標。

輸出檔案至：
- 結構配置圖/BEAM/{floor_range}.md
- 結構配置圖/COLUMN/{floor_range}.md
- 結構配置圖/WALL/{floor_range}.md

完成後：
1. SendMessage 通知 CONFIG-BUILDER
2. TaskUpdate 標記完成
3. 進入等待模式",
  run_in_background=true
)

Task(
  subagent_type="phase1-reader",
  team_name="bts-structure-team",
  name="READER-B",
  description="讀取結構配置圖（樓層組 2）",
  prompt="你被指派為 BTS-STRUCTURE Team 的 READER-B。

結構配置圖路徑：{Case Folder}/結構配置圖/
你負責的樓層範圍：{GROUP_2_FLOORS}
對應的 PDF 頁面/裁切圖：{GROUP_2_PAGES}
標註 JSON：{Case Folder}/結構配置圖/annotations.json

請按照 .claude/agents/phase1-reader.md 的指示執行。
先讀取 skills/plan-reader/SKILL.md 了解完整流程。
優先使用 annotation.json 的精確座標。

輸出檔案至：
- 結構配置圖/BEAM/{floor_range}.md
- 結構配置圖/COLUMN/{floor_range}.md
- 結構配置圖/WALL/{floor_range}.md

完成後：
1. SendMessage 通知 CONFIG-BUILDER
2. TaskUpdate 標記完成
3. 進入等待模式",
  run_in_background=true
)

Task(
  subagent_type="phase1-config-builder",
  team_name="bts-structure-team",
  name="CONFIG-BUILDER",
  description="生成 model_config.json",
  prompt="你被指派為 BTS-STRUCTURE Team 的 CONFIG-BUILDER。

先讀取 golden_scripts/config_schema.json 了解輸出格式。
等待 READER-A 和 READER-B 的 SendMessage 通知，然後從資料夾讀取資料：
- 結構配置圖/BEAM/*.md
- 結構配置圖/COLUMN/*.md
- 結構配置圖/WALL/*.md

整合為 model_config.json（small_beams 和 slabs 留空）。

用戶提供的參數：
- 樓層高度表：{STORY_TABLE}
- 強度分配表：{STRENGTH_MAP}
- 板厚：{SLAB_THICKNESS}（記錄但 sections.slab 留空）
- 基礎樓層：{FOUNDATION_FLOOR}
- 基礎 Kv：{KV_VALUE}
- 邊梁 Kw：{KW_VALUE}
- EDB 存檔路徑：{SAVE_PATH}
- Base Shear C：{C_VALUE}
- 反應譜檔案：{SPECTRUM_PATH}

完成後：
1. 將 model_config.json 寫入 {Case Folder}/
2. SendMessage 告知 Team Lead config 路徑
3. TaskUpdate 標記完成",
  run_in_background=true
)
```

### Phase 3: 監控 → 等待 CONFIG-BUILDER 完成

Team Lead 進入監控模式，等 T3 完成。

### Phase 4: 執行 Golden Scripts（Team Lead 直接操作）

CONFIG-BUILDER 完成後，Team Lead 執行：

```bash
cd golden_scripts
python run_all.py --config "{Case Folder}/model_config.json" --steps 1,2,3,4,5,6
```

**注意**：只執行 steps 1-6（不含 7=小梁, 8=版, 9-11=properties/loads/diaphragms）

檢查輸出：
- 每個 step 應印出 "complete"
- 如有 ERROR，修正 model_config.json 後重跑失敗的 step

### Phase 5: 基本驗證

在 ETABS 中確認：
- Grid 系統正確
- Story 數量和高度正確
- 柱數量合理
- 牆（含連續壁）已建立
- 大梁已建立
- **無**小梁和版（Phase 2 處理）

### Phase 6: 報告結果

向用戶報告：
- Phase 1 建模完成
- 構件數量（柱/梁/牆）
- 提醒：下一步執行 `/bts-sb` 建立小梁和版

### Phase 7: Shutdown

```
SendMessage(type="shutdown_request", recipient="READER-A")
SendMessage(type="shutdown_request", recipient="READER-B")
SendMessage(type="shutdown_request", recipient="CONFIG-BUILDER")
```

---

## Golden Scripts 執行步驟（Phase 1 only）

| Step | 腳本 | 功能 |
|------|------|------|
| 01 | gs_01_init.py | 材料 C280~C490 + SD420/SD490 |
| 02 | gs_02_sections.py | 斷面展開 + D/B + rebar + modifiers |
| 03 | gs_03_grid_stories.py | Grid + Stories |
| 04 | gs_04_columns.py | 柱 (+1 rule) |
| 05 | gs_05_walls.py | 牆 (+1 rule + diaphragm=C280) |
| 06 | gs_06_beams.py | 大梁/壁梁/基礎梁 |

---

用戶的附加指示：$ARGUMENTS
