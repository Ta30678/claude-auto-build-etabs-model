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
3. **Grid 名稱/方向/順序從 ETABS 預建模型讀取（grid_data.json），PPT 用於驗證。**
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

**「先掃描，再確認」**——所有能從 PPT 自動取得的資訊先掃描一輪，再向用戶確認。

**參數清單**：

| # | 參數 | 說明 | 取得方式 |
|---|------|------|----------|
| 1 | 結構配置圖 | `{Case Folder}/結構配置圖/` | **自動掃描目錄** |
| 2 | 樓層高度表 | 各樓層高度 (m)，含基礎層 | **PPT 掃描**（PNG/文字）→ 用戶確認 |
| 3 | 強度分配表 | 混凝土等級 by 樓層區段 | **PPT 掃描**（PNG/文字）→ 用戶確認 |
| 4 | 基礎樓層 | BASE 上一層 | **自動偵測**（最低樓層，如 14F/B5F → B5F） |
| 5 | ETABS 預建 Grid | ETABS 中是否已開啟預建 Grid 的模型？ | **必問**（確認 ETABS 已開啟） |
| 6 | EDB 存檔路徑 | 模型檔路徑 | **必問** |

> **已移至 Phase 3 `/bts-props`**：Kv、Kw、反應譜檔案、Base Shear C、EQV Scale Factor
> **已移至 Phase 2 `/bts-sb`**：板厚

#### 樓層高度掃描流程

1. **掃描 PPT**：在 PPT 中尋找樓層高度表（可能是 PNG 圖片、表格、或文字框）
2. **顯示掃描結果**：列出各樓層名稱 + 高度 (m)
3. **用戶確認**：用 AskUserQuestion 請用戶確認或修正
4. **⚠️ 樓高轉換規則**：建築圖上標示的「N 層樓高」= ETABS 中「N+1 層的 story height」
   - 原因：與柱/牆 +1 rule 一致——柱站在 NF，向上延伸到 (N+1)F
   - 例如：建築圖「1F 樓高 4.2m」→ ETABS「2F story height = 4.2m」
   - 例如：建築圖「B1F 樓高 3.5m」→ ETABS「1F story height = 3.5m」
5. **產生 STORY_TABLE**：用戶確認後，將樓高轉換為 ETABS 格式 JSON，供 READER 直接引用：
   ```json
   {
     "stories": [
       {"name": "B3F", "height": 2.30},
       {"name": "B2F", "height": 4.50},
       {"name": "1F", "height": 4.20}
     ],
     "base_elevation": -12.40
   }
   ```
   格式與 `grid_info.json` 的 `stories` / `base_elevation` 欄位一致。READER 直接複製到 grid_info.json，不需重新掃描。

#### 強度分配掃描流程

1. **掃描 PPT**：在 PPT 中尋找強度分配表或標註（fc' by 樓層區段）
2. **顯示掃描結果**：列出各樓層區段 + 對應混凝土強度 (kgf/cm²)
3. **用戶確認**：用 AskUserQuestion 請用戶確認或修正
4. **產生 STRENGTH_TABLE**：用戶確認後，將強度分配轉換為 JSON，供 READER 直接引用：
   ```json
   {
     "B3F~1F": {"column": 490, "beam": 420, "slab": 280, "wall": 280},
     "2F~14F": {"column": 350, "beam": 280, "slab": 280, "wall": 280}
   }
   ```
   格式與 `grid_info.json` 的 `strength_map` 欄位一致。READER 直接複製到 grid_info.json，不需重新掃描。

#### 屋突樓層自動偵測

如果 PPT 掃描（--scan-floors）未偵測到屋突頁面（無 R1F/R2F/R3F/PRF 標註）：
- 在樓層高度確認時一併提示：「PPT 未偵測到屋突頁面，將使用預設屋突（R1F~R3F+PRF，各 3m）。如需調整屋突層數或高度請修改。」
- 將預設屋突樓層加入 STORY_TABLE 傳給 CONFIG-BUILDER

#### 基礎樓層自動偵測

從樓層高度表中自動識別最低樓層作為基礎樓層（BASE 上一層），不另外詢問。
- 例如：樓層有 B5F~R3F → 基礎樓層 = B5F
- 例如：樓層有 1F~15F → 基礎樓層 = 1F

### Phase 0.3: Read Grid from ETABS

用戶已在 ETABS 中預建 Grid System。從 ETABS 讀取 Grid 資訊作為 ground truth。

1. **確認 ETABS 已開啟**：用戶確認 ETABS 中已開啟預建 Grid 的模型
2. **執行讀取**：
   ```bash
   python -m golden_scripts.tools.read_grid --output "{Case Folder}/grid_data.json"
   ```
3. **驗證結果**：讀取 `grid_data.json`，確認 Grid 名稱、座標、數量正確
4. **儲存變數**：將 `grid_data.json` 的內容存為 `GRID_DATA` 變數，後續傳給 Agent

### Phase 0.5: 樓層標籤掃描（PPT）

掃描 `結構配置圖/` 內的 `.pptx` 檔案，取得 slide → 樓層對應：

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
- 儲存 PPT 路徑為 `PPT_PATH` 變數

> **注意**：構件提取已下放給兩個 READER 平行執行。
> Team Lead 只需在此步驟取得 `PAGE_FLOOR_MAPPING` 和 `PPT_PATH`，並分配頁面子集。

### Phase 0.7: 建立子資料夾 & 分配平行提取工作

1. **建立子資料夾**（如尚未存在）：
   ```bash
   mkdir -p "{Case Folder}/結構配置圖/BEAM"
   mkdir -p "{Case Folder}/結構配置圖/COLUMN"
   mkdir -p "{Case Folder}/結構配置圖/WALL"
   ```
2. **決定樓層分工**（兩個 READER 各自提取 + 視覺任務）：
   - 根據 annotations 中各頁的樓層標註，將頁面分為兩組
   - **READER-A**: 上構頁面 → `elements_A.json`
   - **READER-B**: 下構+屋突頁面 → `elements_B.json`
   - 每個 READER 提取自己負責的頁面子集（各自的 `--page-floors`）
   - 各自產出 `--crop` PNG 到共用的 `結構配置圖/` 目錄

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

【重要】你需要先執行構件提取（你負責的頁面子集），再做視覺任務。

PPT_PATH={PPT_PATH}
PAGE_FLOOR_MAPPING={READER_A_PAGE_FLOORS}
OUTPUT_FILE={Case Folder}/elements_A.json
CASE_FOLDER={Case Folder}

Grid 系統資料（來自 ETABS 模型，ground truth）：{GRID_DATA}
Grid 名稱和座標以此為準，不需要獨立從 PPT 推斷 Grid 系統。
你仍需看 PPT 上的 Grid 線位置，用於驗證和定位元素。

STORY_TABLE（已由 Team Lead 掃描+用戶確認，直接複製到 grid_info.json）：
{STORY_TABLE}

STRENGTH_TABLE（已由 Team Lead 掃描+用戶確認，直接複製到 grid_info.json）：
{STRENGTH_TABLE}

結構配置圖路徑：{Case Folder}/結構配置圖/
你負責的樓層範圍：{GROUP_1_FLOORS}
對應的 PDF 頁面/裁切圖：{GROUP_1_PAGES}

你的工作流：
Step 1: 執行 pptx_to_elements.py --phase phase1 --crop --output elements_A.json（見 Element Extraction Step）
        注意：--page-floors 只包含你負責的頁面子集
Step 2: 驗證 elements_A.json 的 legend/counts/wall snap → SendMessage 回報
Step 3: 視覺任務：
  - Grid 驗證：比對 ETABS Grid 資料與 PPT 圖面上的 Grid 線位置
  - 建物外框 (building_outline) polygon
  - 屋突核心區 (core_grid_area) — 如 READER-B 未涵蓋，從標準層圖面辨識
Step 4: 寫 grid_info.json（stories/strength_map 直接使用上方 STORY_TABLE/STRENGTH_TABLE）
Step 5: 審閱 beam_validation_report.json（如 Team Lead 提供路徑）

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

【重要】你需要先執行構件提取（你負責的頁面子集），再做視覺任務。

PPT_PATH={PPT_PATH}
PAGE_FLOOR_MAPPING={READER_B_PAGE_FLOORS}
OUTPUT_FILE={Case Folder}/elements_B.json
CASE_FOLDER={Case Folder}

Grid 系統資料（來自 ETABS 模型，ground truth）：{GRID_DATA}
Grid 名稱和座標以此為準，不需要獨立從 PPT 推斷 Grid 系統。
你仍需看 PPT 上的 Grid 線位置，用於驗證和定位元素。

STORY_TABLE（已由 Team Lead 掃描+用戶確認，直接複製到 grid_info.json）：
{STORY_TABLE}

STRENGTH_TABLE（已由 Team Lead 掃描+用戶確認，直接複製到 grid_info.json）：
{STRENGTH_TABLE}

結構配置圖路徑：{Case Folder}/結構配置圖/
你負責的樓層範圍：{GROUP_2_FLOORS}
對應的 PDF 頁面/裁切圖：{GROUP_2_PAGES}

你的工作流：
Step 1: 執行 pptx_to_elements.py --phase phase1 --crop --output elements_B.json
        注意：--page-floors 只包含你負責的頁面子集
Step 2: 驗證 elements_B.json 的 legend/counts/wall snap → SendMessage 回報
Step 3: 視覺任務：
  - Grid 驗證：比對 ETABS Grid 資料與 PPT 圖面上的 Grid 線位置，確認一致性
  - 建物外框 (building_outline) polygon（下構範圍 = substructure_outline）
  - 屋突核心區 (core_grid_area) — 從標準層圖面辨識電梯井和樓梯間的 Grid 範圍（必要）
Step 4: 寫 grid_info.json（合併或補充 READER-A 的資料）
        stories → 直接使用上方 STORY_TABLE
        strength_map → 直接使用上方 STRENGTH_TABLE
Step 5: 審閱 beam_validation_report.json（如 Team Lead 提供路徑）

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

### Phase 2.5: 主動監控 + 合併 + 驗證 + 啟動 GS

啟動 Readers 後，Team Lead 使用 TaskList 監控 T1/T2 狀態。

#### Step A: 等待第一個 Reader 完成

反覆執行 TaskList，直到 T1 或 T2 狀態為 "completed"。

#### Step B: 負載平衡（File-Based Detection）

1. 用 Glob 掃描 `結構配置圖/` 中已產生的 crop PNG 數量
2. 比較兩個 READER 的進度

**如果剩餘 ≥ 2 頁**：
  - 從慢速 Reader 分配清單的「尾端」取出未處理的頁面
  - SendMessage 給已完成的 Reader：
    "RESUME: 請額外處理以下頁面：{pages_list}
     樓層範圍：{floor_ranges}
     完成後 SendMessage 通知 Team Lead。"

**如果剩餘 < 2 頁**：
  - 不重新分配，讓慢速 Reader 自然完成

#### Step C: 等待所有讀圖完成

監控 TaskList，直到所有讀圖工作完成：
- T1 和 T2 都為 "completed"
- 已分配給快速 Reader 的額外工作也已完成（收到 SendMessage 確認）

#### Step D: 合併 elements（Team Lead 執行）

兩個 READER 都完成後，Team Lead 直接執行：

```bash
python -m golden_scripts.tools.elements_merge \
    --inputs "{Case Folder}/elements_A.json" "{Case Folder}/elements_B.json" \
    --output "{Case Folder}/elements.json"
```

檢查：
- exit code 0 → 繼續
- exit code 1（空斷面 > 30%）→ 檢查 Legend 色碼匹配問題，可能需調整 `--color-tolerance`

#### Step E: 大梁端點校正（Team Lead 執行）

```bash
python -m golden_scripts.tools.beam_validate \
    --elements "{Case Folder}/elements.json" \
    --grid-data "{Case Folder}/grid_data.json" \
    --output "{Case Folder}/elements_validated.json" \
    --tolerance 1.5 \
    --report "{Case Folder}/beam_validation_report.json"
```

檢查：
- 校正摘要（數量、最大距離）
- WARNING 項目 → 可 SendMessage 給 READER 審閱 `beam_validation_report.json`
- 如有明顯問題 → 協助修正（可能需手動調整 elements.json）

#### Step F: config_build（Team Lead 執行）

```bash
python -m golden_scripts.tools.config_build \
    --elements "{Case Folder}/elements_validated.json" \
    --grid-info "{Case Folder}/結構配置圖/grid_info.json" \
    --output "{Case Folder}/model_config.json" \
    --save-path "{SAVE_PATH}" \
    --project-name "{PROJECT_NAME}"
```

#### Step G: 啟動 CONFIG-BUILDER（GS 執行）

config_build 成功後，啟動 CONFIG-BUILDER 執行 Golden Scripts：

```
Agent(
  subagent_type="phase1-config-builder",
  team_name="bts-structure-team",
  name="CONFIG-BUILDER",
  description="執行 GS steps 1-6",
  prompt="你被指派為 BTS-STRUCTURE Team 的 CONFIG-BUILDER。
model_config.json 已由 config_build.py 腳本生成。

Case Folder 絕對路徑：{Case Folder}
Config 路徑：{Case Folder}/model_config.json

你的任務：
1. 快速掃描 model_config.json（確認結構合理）
2. 執行：cd golden_scripts && python run_all.py --config \"{Case Folder}/model_config.json\" --steps 1,2,3,4,5,6
3. 如有 ERROR，修正 config 後重跑失敗的 step（最多 2 次）
4. SendMessage 告知 Team Lead：GS 執行結果
5. TaskUpdate 標記完成",
  run_in_background=true
)
```

#### Step H: 等待 CONFIG-BUILDER 完成

監控 T3 狀態為 "completed"。

#### 邊界情況處理

| Case | Handling |
|------|----------|
| 兩個 Reader 同時完成 | 跳過重分配，直接執行 Step D（合併） |
| 剩餘頁面 < 2 | 不重新分配，不值得額外開銷 |
| READER-B 先完成 | 對稱處理 — 將 READER-A 尾端工作分給 READER-B |
| elements_merge 失敗（>30% 空斷面）| 檢查 Legend 色碼匹配，可試 `--color-tolerance 25` 重新提取 |
| beam_validate WARNING | SendMessage 給 READER 審閱報告，確認浮動大梁是否為真 |
| config_build.py 失敗 | 檢視錯誤，修正 grid_info.json 後重新執行 |
| READER EXTRACTION_FAILED | 檢視錯誤訊息（legend 問題？PPT 格式？），修正後 SendMessage 給 READER 重新執行提取 |

### Phase 5: 驗證 CONFIG-BUILDER 結果

CONFIG-BUILDER 完成後會 SendMessage 回報 GS 執行結果。Team Lead 確認：
- GS steps 1-6 全部成功
- 構件數量合理（柱/梁/牆）

如 CB 回報 GS 執行失敗：
- 檢視錯誤訊息
- 協助 CB 修正 config 或排除環境問題
- 必要時手動重跑失敗的 step

在 ETABS 中確認：
- Grid 系統維持預建狀態（未被覆寫）
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
| 03 | gs_03_grid_stories.py | Grid（如已存在則跳過）+ Stories |
| 04 | gs_04_columns.py | 柱 (+1 rule) |
| 05 | gs_05_walls.py | 牆 (+1 rule + diaphragm=C280) |
| 06 | gs_06_beams.py | 大梁/壁梁/基礎梁 |

---

用戶的附加指示：$ARGUMENTS
