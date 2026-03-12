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
6. **下構樓層（B*F + 1F）共用同一個 building_outline（基地範圍）。** 1F 的建物外框 = B*F 的建物外框。

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

### Phase 0.5: 標註提取（PPT）

掃描 `結構配置圖/` 內的 `.pptx` 檔案：

1. **自動偵測樓層標籤**：
   ```bash
   python -m golden_scripts.tools.pptx_to_elements \
     --input "{Case Folder}/結構配置圖/xxx.pptx" \
     --scan-floors
   ```
   此命令會掃描所有 slide 的文字（包括 TEXT_BOX、AUTO_SHAPE、GROUP 內部），
   自動偵測樓層範圍標註（如 "B3F", "1F~2F", "3F~14F"），並輸出建議的 `--page-floors` 字串。

   - **驗證偵測結果**：確認 slide 與樓層對應正確
   - 如偵測正確，可直接使用 `--auto-floors` 跳過手動指定
   - 如偵測有誤，手動修正為 `PAGE_FLOOR_MAPPING` 變數
   - 儲存 slide 上的樓層文字為 `PAGE_FLOOR_LABELS` 變數

2. **執行 PPT 構件提取**（二擇一）：

   **方式 A：自動樓層（推薦）**
   ```bash
   python -m golden_scripts.tools.pptx_to_elements \
     --input "{Case Folder}/結構配置圖/xxx.pptx" \
     --output "{Case Folder}/elements.json" \
     --auto-floors \
     --phase phase1 \
     --crop --crop-dir "{Case Folder}/結構配置圖/"
   ```

   **方式 B：手動指定樓層**
   ```bash
   python -m golden_scripts.tools.pptx_to_elements \
     --input "{Case Folder}/結構配置圖/xxx.pptx" \
     --output "{Case Folder}/elements.json" \
     --page-floors "{PAGE_FLOOR_MAPPING}" \
     --phase phase1 \
     --crop --crop-dir "{Case Folder}/結構配置圖/"
   ```
   此命令同時完成構件提取 + PNG 提取。

   **驗證**：
   - 檢查輸出 summary 的構件數量是否合理。如果某頁 0 個構件，檢查 legend 是否正確。
   - 檢查 **Legend Validation** 報告：確認所有 legend 項目都有匹配的 shapes，留意 orphan shapes 警告。
   - 如有 WARNING 關於 fallback scale，確認無測量標註的 slide 是否需要補上 "X.X m" 標註。
   - 檢查 wall snap 訊息：確認牆座標是否正確對齊到梁軸線。

### Phase 0.7: 建立子資料夾 & 分配讀圖工作

1. **建立子資料夾**（如尚未存在）：
   ```bash
   mkdir -p "{Case Folder}/結構配置圖/BEAM"
   mkdir -p "{Case Folder}/結構配置圖/COLUMN"
   mkdir -p "{Case Folder}/結構配置圖/WALL"
   ```
2. **決定樓層分工**（READER 現在只讀 Grid/outline/stories）：
   - 根據 annotations 中各頁的樓層標註，將頁面分為兩組
   - 原則：工作量大致相等
   - 例如：READER-A 負責上構典型樓層，READER-B 負責下構+屋突

### Phase 1: 建立 Team + 創建任務

```
TeamCreate(team_name="bts-structure-team", description="BTS Phase 1 主結構建模")
```

| Task | 主題 | Owner | blockedBy |
|------|------|-------|-----------|
| T1 | READER-A 讀圖 | READER-A | (無) |
| T2 | READER-B 讀圖 | READER-B | (無) |
| T3 | CONFIG-BUILDER 生成 config + 執行 GS | CONFIG-BUILDER | (無) |

### Phase 2A: 啟動 Readers Only

**只啟動** READER-A 和 READER-B，`run_in_background=true`。CONFIG-BUILDER 在 Phase 2.5 才啟動。

```
Agent(
  subagent_type="phase1-reader",
  team_name="bts-structure-team",
  name="READER-A",
  description="讀取 Grid/建物外框/板區域（樓層組 1）",
  prompt="你被指派為 BTS-STRUCTURE Team 的 READER-A。

【重要】構件(柱/梁/牆)的座標已由 pptx_to_elements.py 自動提取到 elements.json。
你不需要分類或計數構件。你只負責讀取 AI 視覺才能取得的資訊。

結構配置圖路徑：{Case Folder}/結構配置圖/
你負責的樓層範圍：{GROUP_1_FLOORS}
對應的 PDF 頁面/裁切圖：{GROUP_1_PAGES}
elements.json 路徑：{Case Folder}/elements.json（供交叉比對）

你的職責（Reduced）：
1. Grid 名稱、間距、累積座標、方向、Bubble 位置
2. 建物外框 (building_outline) polygon
3. 板區域判斷 (slab_region_matrix)
4. 強度分配 (strength_map) — 如圖面有標註

各頁面的樓層範圍標註：{PAGE_FLOOR_LABELS}
規則：下構樓層（B*F + 1F）的 building_outline 必須一致，1F 建物外框 = 基地範圍。

請按照 .claude/agents/phase1-reader.md 的指示執行。
先讀取 skills/plan-reader/SKILL.md 了解完整流程。

輸出 JSON 至：
- 結構配置圖/grid_info.json

完成後：
1. SendMessage 通知 Team Lead
2. TaskUpdate 標記完成
3. 進入等待模式（監聽 CONFIG-BUILDER 問題）",
  run_in_background=true
)

Agent(
  subagent_type="phase1-reader",
  team_name="bts-structure-team",
  name="READER-B",
  description="讀取 Grid/建物外框/板區域（樓層組 2）",
  prompt="你被指派為 BTS-STRUCTURE Team 的 READER-B。

【重要】構件(柱/梁/牆)的座標已由 pptx_to_elements.py 自動提取到 elements.json。
你不需要分類或計數構件。你只負責讀取 AI 視覺才能取得的資訊。

結構配置圖路徑：{Case Folder}/結構配置圖/
你負責的樓層範圍：{GROUP_2_FLOORS}
對應的 PDF 頁面/裁切圖：{GROUP_2_PAGES}
elements.json 路徑：{Case Folder}/elements.json（供交叉比對）

你的職責（Reduced）：
1. Grid 名稱、間距、累積座標、方向、Bubble 位置（如 READER-A 未涵蓋）
2. 建物外框 (building_outline) polygon（如與 READER-A 不同範圍）
3. 板區域判斷 (slab_region_matrix) — 你的樓層範圍
4. 強度分配 (strength_map) — 如圖面有標註
5. 屋突核心區 (core_grid_area) — 如你負責屋突樓層

各頁面的樓層範圍標註：{PAGE_FLOOR_LABELS}
規則：下構樓層（B*F + 1F）的 building_outline 必須一致，1F 建物外框 = 基地範圍。

請按照 .claude/agents/phase1-reader.md 的指示執行。
先讀取 skills/plan-reader/SKILL.md 了解完整流程。

輸出 JSON 至：
- 結構配置圖/grid_info.json（合併或補充 READER-A 的資料）

完成後：
1. SendMessage 通知 Team Lead
2. TaskUpdate 標記完成
3. 進入等待模式（監聯 CONFIG-BUILDER 問題）",
  run_in_background=true
)
```

### Phase 2.5: 主動監控 + 動態調度

啟動 Readers 後，Team Lead 使用 TaskList 監控 T1/T2 狀態。

#### Step A: 等待第一個 Reader 完成

反覆執行 TaskList，直到 T1 或 T2 狀態為 "completed"。

#### Step B: 啟動 CONFIG-BUILDER（延遲啟動）

第一個 Reader 完成後，**立即啟動** CONFIG-BUILDER：

```
Agent(
  subagent_type="phase1-config-builder",
  team_name="bts-structure-team",
  name="CONFIG-BUILDER",
  description="合併 → model_config.json → 執行 GS steps 1-6",
  prompt="你被指派為 BTS-STRUCTURE Team 的 CONFIG-BUILDER。
你被延遲啟動。elements.json 已生成，至少一個 READER 已完成 grid_info.json。

Case Folder 絕對路徑：{Case Folder}

你的輸入來源：
1. {Case Folder}/elements.json — 構件座標（腳本確定性輸出，直接使用）
2. {Case Folder}/結構配置圖/grid_info.json — Grid/outline/stories（READER AI 輸出）
3. Team Lead 提供的工程參數

步驟（Phase 1 — 生成 config）：
1. 預讀 golden_scripts/config_schema.json + example_config.json
2. 讀取 elements.json（columns, beams, walls, sections）
3. 讀取 grid_info.json（grids, stories, building_outline, slab_region_matrix, strength_map）
4. 等待 Team Lead 的 'ALL_DATA_READY' SendMessage（如 READER 尚未全部完成）
5. 合併為完整 model_config.json（small_beams 和 slabs 留空）

步驟（Phase 2 — 執行 Golden Scripts）：
6. 生成 model_config.json 後，立即執行：
   cd golden_scripts
   python run_all.py --config \"{Case Folder}/model_config.json\" --steps 1,2,3,4,5,6
7. 每個 step 應印出 complete；如有 ERROR，檢查 config 並修正後重跑失敗的 step
8. 最多重試 2 次，仍失敗則 SendMessage 告知 Team Lead 錯誤詳情

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
2. 執行 run_all.py --steps 1,2,3,4,5,6
3. SendMessage 告知 Team Lead：config 路徑 + GS 執行結果（成功/失敗 + 構件數量）
4. TaskUpdate 標記完成",
  run_in_background=true
)
```

#### Step C: 負載平衡（File-Based Detection）

1. 用 Glob 掃描 BEAM/COLUMN/WALL 資料夾中已產生的 .md 檔案
2. 比對 READER_B_EXPECTED（或 READER_A_EXPECTED，視誰較慢）
3. 計算慢速 Reader 尚未產出的檔案數量

**如果剩餘 ≥ 2 頁**：
  - 從慢速 Reader 分配清單的「尾端」取出未處理的頁面
  - SendMessage 給已完成的 Reader：
    "RESUME: 請額外處理以下頁面：{pages_list}
     樓層範圍：{floor_ranges}
     輸出至相同的 BEAM/COLUMN/WALL 資料夾。
     完成後 SendMessage 通知 Team Lead。"

**如果剩餘 < 2 頁**：
  - 不重新分配，讓慢速 Reader 自然完成

#### Step D: 等待所有讀圖完成

監控 TaskList，直到所有讀圖工作完成：
- T1 和 T2 都為 "completed"
- 已分配給快速 Reader 的額外工作也已完成（收到 SendMessage 確認）

#### Step E: 通知 CONFIG-BUILDER

SendMessage 給 CONFIG-BUILDER：
"ALL_DATA_READY — BEAM/COLUMN/WALL 所有 .md 檔案已完成。請處理全部資料。"

#### Step F: 等待 CONFIG-BUILDER 完成

監控 T3 狀態為 "completed"。

#### 邊界情況處理

| Case | Handling |
|------|----------|
| 兩個 Reader 同時完成 | 跳過重分配，啟動 CB + 直接發送 ALL_DATA_READY |
| 剩餘頁面 < 2 | 不重新分配，不值得額外開銷 |
| READER-B 先完成 | 對稱處理 — 將 READER-A 尾端工作分給 READER-B |

### Phase 5: 驗證 CONFIG-BUILDER 結果

CONFIG-BUILDER 完成後會 SendMessage 回報 GS 執行結果。Team Lead 確認：
- GS steps 1-6 全部成功
- 構件數量合理（柱/梁/牆）

如 CB 回報 GS 執行失敗：
- 檢視錯誤訊息
- 協助 CB 修正 config 或排除環境問題
- 必要時手動重跑失敗的 step

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
