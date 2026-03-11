---
description: "BTS Phase 2 — 啟動 3 人 Agent Team 建立小梁(SB/FSB)+版(S/FS)。需先完成 /bts-structure。使用方式：/bts-sb [樓層區間說明]"
argument-hint: "[樓層區間說明，例如: 2F~23F=p3, 1F=p4, B1~B3F=p5]"
---

# BTS-SB — Phase 2: 小梁 + 版建模

你現在是 **BTS-SB 團隊的 Team Lead**，負責協調 3 位 Agent 建立小梁和版。

**前置條件**：必須先完成 `/bts-structure`（Phase 1），ETABS 模型已有 Grid+Story+柱+牆+大梁。

**Phase 2 範圍**：小梁(SB/FSB)、樓板(S/FS)
**依賴**：Phase 1 的 `model_config.json`（大梁座標用於版切割）

---

## 鐵則（ABSOLUTE RULES）

1. **小梁位置禁止猜測！** 必須從 annotation.json 讀取並驗證座標。
2. **小梁等分座標必須退回重做。**
3. **每條小梁都是版的切割線** —— 版不可跨過任何梁（含小梁）。
4. **每案獨立**——禁止從記憶推斷。
5. **Phase 4 (run_all.py) 必須在 Phase 6 報告前執行完畢。** 禁止在 run_all.py 執行完畢前向用戶回報「Phase 2 建模完成」。CONFIG-BUILDER 完成 ≠ Phase 2 完成。

---

## 團隊編制

| Agent | 代號 | Agent 定義檔 | 職責 |
|-------|------|-------------|------|
| Agent 1 | **SB-READER-A** | `.claude/agents/phase2-sb-reader.md` | 讀取分配的樓層區間 SB 座標 |
| Agent 2 | **SB-READER-B** | `.claude/agents/phase2-sb-reader.md` | 讀取分配的樓層區間 SB 座標 |
| Agent 3 | **CONFIG-BUILDER** | `.claude/agents/phase2-config-builder.md` | 從 SB-BEAM/ 讀取 + 切版 → sb_slabs_patch.json |

---

## 執行流程

### Phase 0: 確認前置條件

1. **確認 Phase 1 已完成**：
   - `model_config.json` 存在於 case folder
   - ETABS 模型已開啟且有 Grid+柱+牆+梁
2. **確認用戶提供的樓層區間分類**：
   - 用戶需告知哪些 PDF 頁面對應哪些樓層區間
   - 例如：「2F~23F 在 page 3-4, 1F 在 page 4, B1F~B3F 在 page 5」
   - **以樓層區間分類，不以 PDF 頁碼分類**
3. **確認板厚**：
   - 如果 Phase 1 已記錄，直接使用
   - 否則詢問用戶

### Phase 0.5: 提取標註（如需要）

如果 annotations.json 尚未包含小梁相關頁面的標註：

```bash
python -m golden_scripts.tools.pdf_annot_extractor \
  --input "{Case Folder}/結構配置圖/結構尺寸配置.pdf" \
  --pages {SB_PAGES} \
  --output "{Case Folder}/結構配置圖/annotations.json" \
  --crop --crop-dir "{Case Folder}/結構配置圖/"
```

### Phase 0.7: 提取上下文 & 建立資料夾 & 分配工作

1. **讀取 annotations.json，提取 SB 圖例色彩對應**：
   - 讀取 `{Case Folder}/結構配置圖/annotations.json`
   - 從 `annotations.legend.items` 中找出 label 含「小梁」「SB」「次梁」的項目
   - 記錄色彩對應，格式如：`SB30X50 → #FF0000, SB25X50 → #00FF00`
   - 儲存為 `SB_LEGEND_MAPPING` 變數，後續傳給 SB-READER
2. **讀取結構配置圖 PNG，辨識各頁面的樓層範圍標註**：
   - 讀取 `*_full.png` 圖檔
   - 找出圖面上標註的樓層範圍文字（如「2F~12F 小梁配置」「1F 小梁配置」）
   - 記錄每個頁面的樓層範圍標註
   - 儲存為 `PAGE_FLOOR_LABELS` 變數，後續傳給 SB-READER
3. **建立子資料夾**（如尚未存在）：
   ```bash
   mkdir -p "{Case Folder}/結構配置圖/SB-BEAM"
   ```
4. **決定樓層區間分工**：
   - 根據用戶標註的樓層區間分配給兩個 SB-READER
   - 原則：工作量大致相等
   - 例如：SB-READER-A 負責 2F~23F, SB-READER-B 負責 1F + B1F~B3F
5. **記錄各 SB-READER 的預期輸出檔案**：
   ```
   SB_READER_A_EXPECTED = [{floor_range}.md for each page in SB_GROUP_1]
   SB_READER_B_EXPECTED = [{floor_range}.md for each page in SB_GROUP_2]
   ```
   用於 Phase 2.5 的 file-based detection。

### Phase 1: 建立 Team + 創建任務

```
TeamCreate(team_name="bts-sb-team", description="BTS Phase 2 小梁+版建模")
```

| Task | 主題 | Owner | blockedBy |
|------|------|-------|-----------|
| T1 | SB-READER-A 讀取小梁 | SB-READER-A | (無) |
| T2 | SB-READER-B 讀取小梁 | SB-READER-B | (無) |
| T3 | CONFIG-BUILDER 生成 patch | CONFIG-BUILDER | (無) |
| T4 | Merge + 執行 Golden Scripts | (Team Lead) | T3 |

### Phase 2A: 啟動 SB-Readers Only

**只啟動** SB-READER-A 和 SB-READER-B，`run_in_background=true`。CONFIG-BUILDER 在 Phase 2.5 才啟動。

```
Agent(
  subagent_type="phase2-sb-reader",
  team_name="bts-sb-team",
  name="SB-READER-A",
  description="讀取小梁座標（樓層區間 1）",
  prompt="你被指派為 BTS-SB Team 的 SB-READER-A。

結構配置圖路徑：{Case Folder}/結構配置圖/
你負責的樓層區間：{SB_GROUP_1_FLOORS}
對應的 PDF 頁面/裁切圖：{SB_GROUP_1_PAGES}
標註 JSON：{Case Folder}/結構配置圖/annotations.json

圖例色彩對應（小梁相關）：{SB_LEGEND_MAPPING}
各頁面的樓層範圍標註：{PAGE_FLOOR_LABELS}
規則：以圖面標註的樓層範圍為小梁分段依據，禁止用斷面變化分層。

請按照 .claude/agents/phase2-sb-reader.md 的指示執行。
先讀取 skills/plan-reader/SKILL.md 了解完整流程。

驗證小梁連接性時，可參照：
- 結構配置圖/BEAM/*.md 中的大梁座標
- 或 model_config.json 中的 beams 欄位

輸出檔案至：
- 結構配置圖/SB-BEAM/{floor_range}.md

完成後：
1. SendMessage 通知 Team Lead
2. TaskUpdate 標記完成
3. 進入等待模式（監聽 RESUME 指令和 CONFIG-BUILDER 問題）",
  run_in_background=true
)

Agent(
  subagent_type="phase2-sb-reader",
  team_name="bts-sb-team",
  name="SB-READER-B",
  description="讀取小梁座標（樓層區間 2）",
  prompt="你被指派為 BTS-SB Team 的 SB-READER-B。

結構配置圖路徑：{Case Folder}/結構配置圖/
你負責的樓層區間：{SB_GROUP_2_FLOORS}
對應的 PDF 頁面/裁切圖：{SB_GROUP_2_PAGES}
標註 JSON：{Case Folder}/結構配置圖/annotations.json

圖例色彩對應（小梁相關）：{SB_LEGEND_MAPPING}
各頁面的樓層範圍標註：{PAGE_FLOOR_LABELS}
規則：以圖面標註的樓層範圍為小梁分段依據，禁止用斷面變化分層。

請按照 .claude/agents/phase2-sb-reader.md 的指示執行。
先讀取 skills/plan-reader/SKILL.md 了解完整流程。

驗證小梁連接性時，可參照：
- 結構配置圖/BEAM/*.md 中的大梁座標
- 或 model_config.json 中的 beams 欄位

輸出檔案至：
- 結構配置圖/SB-BEAM/{floor_range}.md

完成後：
1. SendMessage 通知 Team Lead
2. TaskUpdate 標記完成
3. 進入等待模式（監聽 RESUME 指令和 CONFIG-BUILDER 問題）",
  run_in_background=true
)
```

### Phase 2.5: 主動監控 + 動態調度

啟動 SB-Readers 後，Team Lead 使用 TaskList 監控 T1/T2 狀態。

#### Step A: 等待第一個 SB-Reader 完成

反覆執行 TaskList，直到 T1 或 T2 狀態為 "completed"。

#### Step B: 啟動 CONFIG-BUILDER（延遲啟動）

第一個 SB-Reader 完成後，**立即啟動** CONFIG-BUILDER：

```
Agent(
  subagent_type="phase2-config-builder",
  team_name="bts-sb-team",
  name="CONFIG-BUILDER",
  description="生成 sb_slabs_patch.json",
  prompt="你被指派為 BTS-SB Team 的 CONFIG-BUILDER。
你被延遲啟動。至少一個 SB-READER 已完成輸出。

1. 立即預讀 golden_scripts/config_schema.json + model_config.json
2. 用 Glob 掃描 SB-BEAM 資料夾，讀取所有已存在的 .md 檔案
3. 開始建構初步 small_beams 清單
4. 等待 Team Lead 的 'ALL_DATA_READY' SendMessage
5. 收到後，再次 Glob 掃描，讀取新增的 .md 檔案
6. 合併為完整 sb_slabs_patch.json

先讀取以下檔案：
1. golden_scripts/config_schema.json（了解格式）
2. {Case Folder}/model_config.json（取得大梁座標、Grid 系統、building_outline）
3. 結構配置圖/BEAM/*.md 中的 Slab Region Matrix（樓板區域判斷）

資料夾路徑：
- 結構配置圖/SB-BEAM/*.md

整合為 sb_slabs_patch.json：
1. 合併所有小梁座標（去重、合併 floors）
2. 以所有梁（大梁+小梁）的座標執行板切割
3. 輸出 small_beams + slabs + sections

板厚資訊：
- 上構板厚：{SLAB_THICKNESS_SUPER}
- 基礎板厚：{SLAB_THICKNESS_FS}（如有）

完成後：
1. 將 sb_slabs_patch.json 寫入 {Case Folder}/
2. SendMessage 告知 Team Lead patch 路徑
3. TaskUpdate 標記完成",
  run_in_background=true
)
```

#### Step C: 負載平衡（File-Based Detection）

1. 用 Glob 掃描 `結構配置圖/SB-BEAM/` 資料夾中已產生的 .md 檔案
2. 比對 SB_READER_B_EXPECTED（或 SB_READER_A_EXPECTED，視誰較慢）
3. 計算慢速 SB-Reader 尚未產出的檔案數量

**如果剩餘 ≥ 2 頁**：
  - 從慢速 SB-Reader 分配清單的「尾端」取出未處理的頁面
  - SendMessage 給已完成的 SB-Reader：
    "RESUME: 請額外處理以下頁面：{pages_list}
     樓層範圍：{floor_ranges}
     輸出至相同的 SB-BEAM 資料夾。
     完成後 SendMessage 通知 Team Lead。"

**如果剩餘 < 2 頁**：
  - 不重新分配，讓慢速 SB-Reader 自然完成

#### Step D: 等待所有讀圖完成

監控 TaskList，直到所有讀圖工作完成：
- T1 和 T2 都為 "completed"
- 已分配給快速 SB-Reader 的額外工作也已完成（收到 SendMessage 確認）

#### Step E: 通知 CONFIG-BUILDER

SendMessage 給 CONFIG-BUILDER：
"ALL_DATA_READY — SB-BEAM 所有 .md 檔案已完成。請處理全部資料。"

#### Step F: 等待 CONFIG-BUILDER 完成

監控 T3 狀態為 "completed"。

> ⚠️ **T3 完成後不可停止！** 必須立即繼續執行 Phase 3.5 + Phase 4（merge + run_all.py），否則小梁和版不會寫入 ETABS 模型。

#### 邊界情況處理

| Case | Handling |
|------|----------|
| 兩個 SB-Reader 同時完成 | 跳過重分配，啟動 CB + 直接發送 ALL_DATA_READY |
| 剩餘頁面 < 2 | 不重新分配，不值得額外開銷 |
| SB-READER-B 先完成 | 對稱處理 — 將 SB-READER-A 尾端工作分給 SB-READER-B |

### Phase 3.5: Pre-flight Validation

CONFIG-BUILDER 完成後，先合併並驗證配置檔：

```bash
python -m golden_scripts.tools.config_merge \
  --base "{Case Folder}/model_config.json" \
  --patch "{Case Folder}/sb_slabs_patch.json" \
  --output "{Case Folder}/merged_config.json" \
  --validate
```

如果驗證失敗（exit code ≠ 0）：
1. 檢視錯誤訊息，辨識問題類型（座標字串、無效樓層名、格式錯誤等）
2. 修正 `sb_slabs_patch.json` 中的錯誤（或請 CONFIG-BUILDER 重新生成）
3. 重新執行合併+驗證
4. **驗證通過後才可繼續 Phase 4**

### Phase 3.7: Snap SB Coordinates

Phase 3.5 驗證通過後，執行座標校正：

```bash
python -m golden_scripts.tools.config_snap \
  --input "{Case Folder}/merged_config.json" \
  --output "{Case Folder}/snapped_config.json"
```

此步驟自動將 SB 端點吸附到最近的柱/梁/牆，修正 SB-READER 的座標誤差（容差 30cm）。
同時更新 slab 角點座標以保持拓撲一致。

如果有 WARNING（端點超過容差），檢查是否為 SB-READER 的明顯錯誤，必要時手動修正。

### ⚠️ Phase 4: 執行 Golden Scripts【ETABS 寫入關鍵步驟】

Phase 3.7 完成後，Team Lead **必須立即**執行：

**Step 1: 執行 Golden Scripts**
```bash
cd golden_scripts
python run_all.py --config "{Case Folder}/snapped_config.json" --steps 2,7,8
```

- Step 2: 建立新的 SB/S/FS 斷面（已存在的不受影響）
- Step 7: 放置小梁
- Step 8: 放置版（含 FS 2x2 細分）

### Phase 5: 驗證

在 ETABS 中確認：
- 小梁數量合理
- 版數量 > 0，每個梁圍區域都有版
- 沒有版跨過梁（含小梁）
- FS 版已正確細分

### Phase 6: 報告結果

向用戶報告：
- Phase 2 建模完成
- 構件數量（小梁/版）
- 提醒：下一步執行 Phase 3（properties/loads/diaphragms）
- **snapped_config.json 為最終完整配置檔**（已校正 SB 座標）

### Phase 7: Shutdown

```
SendMessage(type="shutdown_request", recipient="SB-READER-A")
SendMessage(type="shutdown_request", recipient="SB-READER-B")
SendMessage(type="shutdown_request", recipient="CONFIG-BUILDER")
```

---

## Golden Scripts 執行步驟（Phase 2 only）

| Step | 腳本 | 功能 |
|------|------|------|
| 02 | gs_02_sections.py | 新增 SB/S/FS 斷面（idempotent） |
| 07 | gs_07_small_beams.py | 小梁放置 |
| 08 | gs_08_slabs.py | 版放置（含 FS 2x2 細分） |

---

用戶的附加指示：$ARGUMENTS
