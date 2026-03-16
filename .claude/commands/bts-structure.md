---
description: "BTS Phase 1 — 啟動 3 人 Agent Team 建立主結構（Grid+Story+柱+牆+大梁）。使用方式：/bts-structure [樓層/圖片說明]"
argument-hint: "[樓層說明或附加指示]"
---

# BTS-STRUCTURE — Phase 1: 主結構建模

你現在是 **BTS-STRUCTURE 團隊的 Team Lead**，負責協調 3 位 Agent 建立主結構模型。

**Phase 1 範圍**：Grid、Story、柱(C)、牆(W)、大梁(B/WB/FB/FWB)
**不包含**：小梁(SB/FSB)、樓板(S/FS)——由 Phase 2 `/bts-sb` 處理

> 鐵則詳見各 agent 定義檔 + CLAUDE.md「BTS Agent Team Rules」。

---

## 團隊編制

| Agent   | 代號               | Agent 定義檔                              | 職責                                |
| ------- | ------------------ | ----------------------------------------- | ----------------------------------- |
| Agent 1 | **READER-A**       | `.claude/agents/phase1-reader.md`         | 讀取分配的樓層範圍（Grid+柱+梁+牆） |
| Agent 2 | **READER-B**       | `.claude/agents/phase1-reader.md`         | 讀取分配的樓層範圍（Grid+柱+梁+牆） |
| Agent 3 | **CONFIG-BUILDER** | `.claude/agents/phase1-config-builder.md` | 從 folders 讀取 → model_config.json |

---

## 執行流程

### Phase 0: 確認輸入

**「先掃描，再確認」**——所有能從 PPT 自動取得的資訊先掃描一輪，再向用戶確認。

**參數清單**：

| #   | 參數            | 說明                                 | 取得方式                                   |
| --- | --------------- | ------------------------------------ | ------------------------------------------ |
| 1   | 結構配置圖      | `{Case Folder}/結構配置圖/`          | **自動掃描目錄**                           |
| 2   | 樓層高度表      | 各樓層高度 (m)，含基礎層             | **PPT 掃描**（PNG/文字）→ 用戶確認         |
| 3   | 強度分配表      | 混凝土等級 by 樓層區段               | **PPT 掃描**（PNG/文字）→ 用戶確認         |
| 4   | 基礎樓層        | BASE 上一層                          | **自動偵測**（最低樓層，如 14F/B5F → B5F） |
| 5   | ETABS 預建 Grid | ETABS 中是否已開啟預建 Grid 的模型？ | **必問**（確認 ETABS 已開啟）              |
| 6   | EDB 存檔路徑    | 模型檔路徑                           | **必問**                                   |

#### 樓層高度掃描流程

1. **掃描 PPT** 中的樓層高度表（PNG/表格/文字框）
2. **顯示掃描結果** → 用 AskUserQuestion 請用戶確認或修正
3. **⚠️ 樓高轉換規則**：建築圖「N 層樓高」= ETABS「N+1 層 story height」（與柱/牆 +1 rule 一致）
4. **產生 STORY_TABLE**：格式與 `grid_info.json` 的 `stories`/`base_elevation` 欄位一致
5. 未偵測到屋突頁面時，提示使用預設屋突（R1F~R3F+PRF，各 3m）

#### 強度分配掃描流程

1. **掃描 PPT** 中的強度分配表/標註（fc' by 樓層區段）
2. **顯示掃描結果** → 用 AskUserQuestion 請用戶確認或修正
3. **產生 STRENGTH_TABLE**：格式與 `grid_info.json` 的 `strength_map` 欄位一致

#### 基礎樓層自動偵測

從樓層高度表自動識別最低樓層作為基礎樓層（BASE 上一層），不另外詢問。

### Phase 0.3: Read Grid from ETABS

```bash
python -m golden_scripts.tools.read_grid --output "{Case Folder}/grid_data.json"
```

讀取 `grid_data.json`，確認 Grid 名稱/座標/數量正確。存為 `GRID_DATA` 變數。

### Phase 0.5: 樓層標籤掃描（PPT）

```bash
python -m golden_scripts.tools.pptx_to_elements \
  --input "{Case Folder}/結構配置圖/xxx.pptx" \
  --scan-floors
```

- 驗證 slide ↔ 樓層對應。偵測正確可用 `--auto-floors`，否則手動修正為 `PAGE_FLOOR_MAPPING`
- 儲存 `PAGE_FLOOR_LABELS`、`PPT_PATH` 變數

> 構件提取已下放給兩個 READER 平行執行。Team Lead 只需取得 `PAGE_FLOOR_MAPPING` 和 `PPT_PATH`，並分配頁面子集。

### Phase 0.7: 分配平行提取工作

1. 根據 annotations 中各頁的樓層標註，將頁面分為兩組：
   - **READER-A**: 上構頁面 → `SLIDES INFO/{floor_label}/` per-slide JSONs + `calibrated/{floor_label}/`
   - **READER-B**: 下構+屋突頁面 → `SLIDES INFO/{floor_label}/` per-slide JSONs + `calibrated/{floor_label}/`
2. 設定 `SLIDES_INFO_DIR` = `{Case Folder}/結構配置圖/SLIDES INFO`

### Phase 1: 建立 Team + 創建任務

```
TeamCreate(team_name="bts-structure-team", description="BTS Phase 1 主結構建模")
```

| Task | 主題                                 | Owner          | blockedBy |
| ---- | ------------------------------------ | -------------- | --------- |
| T1   | READER-A 讀圖                        | READER-A       | (無)      |
| T2   | READER-B 讀圖                        | READER-B       | (無)      |
| T3   | CONFIG-BUILDER 生成 config + 執行 GS | CONFIG-BUILDER | (無)      |

### Phase 2A: 啟動 Readers Only

**只啟動** READER-A 和 READER-B，`run_in_background=true`。CONFIG-BUILDER 在 Phase 2.5 才啟動。

```
Agent(
  subagent_type="phase1-reader",
  team_name="bts-structure-team",
  name="READER-A",
  description="讀取 Grid/建物外框/板區域（樓層組 1）",
  prompt="你被指派為 BTS-STRUCTURE Team 的 READER-A。

PPT_PATH={PPT_PATH}
PAGE_FLOOR_MAPPING={READER_A_PAGE_FLOORS}
SLIDES_INFO_DIR={SLIDES_INFO_DIR}
CASE_FOLDER={Case Folder}
GRID_DATA={GRID_DATA}
STORY_TABLE={STORY_TABLE}
STRENGTH_TABLE={STRENGTH_TABLE}
GROUP_FLOORS={GROUP_1_FLOORS}
GROUP_PAGES={GROUP_1_PAGES}
PAGE_FLOOR_LABELS={PAGE_FLOOR_LABELS}

請按照 .claude/agents/phase1-reader.md 的指示執行。
先讀取 skills/plan-reader/SKILL.md 了解完整流程。",
  run_in_background=true
)

Agent(
  subagent_type="phase1-reader",
  team_name="bts-structure-team",
  name="READER-B",
  description="讀取 Grid/建物外框/板區域（樓層組 2）",
  prompt="你被指派為 BTS-STRUCTURE Team 的 READER-B。

PPT_PATH={PPT_PATH}
PAGE_FLOOR_MAPPING={READER_B_PAGE_FLOORS}
SLIDES_INFO_DIR={SLIDES_INFO_DIR}
CASE_FOLDER={Case Folder}
GRID_DATA={GRID_DATA}
STORY_TABLE={STORY_TABLE}
STRENGTH_TABLE={STRENGTH_TABLE}
GROUP_FLOORS={GROUP_2_FLOORS}
GROUP_PAGES={GROUP_2_PAGES}
PAGE_FLOOR_LABELS={PAGE_FLOOR_LABELS}
ROLE_NOTE=合併或補充 READER-A 的 grid_info.json。core_grid_area 必須由你或 READER-A 提供。

請按照 .claude/agents/phase1-reader.md 的指示執行。
先讀取 skills/plan-reader/SKILL.md 了解完整流程。",
  run_in_background=true
)
```

### Phase 2.5: 主動監控 + 合併 + 驗證 + 啟動 GS

啟動 Readers 後，Team Lead 使用 TaskList 監控 T1/T2 狀態。

#### Step A: 等待第一個 Reader 完成

反覆執行 TaskList，直到 T1 或 T2 狀態為 "completed"。

#### Step B: 負載平衡

用 Glob 掃描 `結構配置圖/` 已產生的 crop PNG 數量，比較進度。剩餘 ≥ 2 頁 → 從慢速 Reader 尾端取出未處理頁面，SendMessage "RESUME" 給已完成的 Reader。剩餘 < 2 頁 → 不重新分配。

#### Step C: 等待所有讀圖完成

T1 和 T2 都為 "completed"，且額外分配工作也已完成。

#### Step D: 合併 elements（Team Lead 執行）

```bash
python -m golden_scripts.tools.elements_merge \
    --inputs-dir "{Case Folder}/calibrated" \
    --output "{Case Folder}/elements.json"
```

exit code 1（空斷面 > 30%）→ 檢查 Legend 色碼，可試 `--color-tolerance 25` 重新提取。

#### Step E: config_build（Team Lead 執行）

> beam_validate 已由 READER 在 per-slide 階段（Step E3.5）完成，Team Lead 不再需要執行。

```bash
python -m golden_scripts.tools.config_build \
    --elements "{Case Folder}/elements.json" \
    --grid-info "{Case Folder}/結構配置圖/grid_info.json" \
    --output "{Case Folder}/model_config.json" \
    --save-path "{SAVE_PATH}" \
    --project-name "{PROJECT_NAME}"
```

#### Step G: 啟動 CONFIG-BUILDER（GS 執行）

```
Agent(
  subagent_type="phase1-config-builder",
  team_name="bts-structure-team",
  name="CONFIG-BUILDER",
  description="執行 GS steps 1-6",
  prompt="你被指派為 BTS-STRUCTURE Team 的 CONFIG-BUILDER。
model_config.json 已由 config_build.py 腳本生成。

Case Folder: {Case Folder}
Config: {Case Folder}/model_config.json

請按照 .claude/agents/phase1-config-builder.md 的指示執行。",
  run_in_background=true
)
```

#### Step H: 等待 CONFIG-BUILDER 完成

監控 T3 狀態為 "completed"。

#### 邊界情況

- 兩個 Reader 同時完成 → 跳過重分配，直接 Step D
- READER-B 先完成 → 對稱處理
- elements_merge 失敗 → 檢查 Legend 色碼，可試 `--color-tolerance 25`
- config_build 失敗 → 修正 grid_info.json 後重新執行
- READER EXTRACTION_FAILED → 檢視錯誤，修正後 SendMessage 給 READER 重新提取
- READER beam_validate WARNING → READER 自行審閱 per-slide report 並回報

### Phase 5: 驗證 CONFIG-BUILDER 結果

確認 GS steps 1-6 成功、構件數量合理。失敗時協助 CB 修正。

在 ETABS 中確認：Grid 維持預建、Story 正確、柱/牆/大梁已建立、無小梁和版。

### Phase 6: 報告結果

向用戶報告 Phase 1 完成 + 構件數量 + 提醒下一步 `/bts-sb`。

### Phase 7: Shutdown

```
SendMessage(type="shutdown_request", recipient="READER-A")
SendMessage(type="shutdown_request", recipient="READER-B")
SendMessage(type="shutdown_request", recipient="CONFIG-BUILDER")
```

---

## Golden Scripts 執行步驟（Phase 1 only）

| Step | 腳本                  | 功能                               |
| ---- | --------------------- | ---------------------------------- |
| 01   | gs_01_init.py         | 材料 C280~C490 + SD420/SD490       |
| 02   | gs_02_sections.py     | 斷面展開 + D/B + rebar + modifiers |
| 03   | gs_03_grid_stories.py | Grid（如已存在則跳過）+ Stories    |
| 04   | gs_04_columns.py      | 柱 (+1 rule)                       |
| 05   | gs_05_walls.py        | 牆 (+1 rule + diaphragm=C280)      |
| 06   | gs_06_beams.py        | 大梁/壁梁/基礎梁                   |

---

用戶的附加指示：$ARGUMENTS
