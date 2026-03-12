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

1. **小梁位置禁止猜測！** 由 `annot_to_elements.py` 確定性提取座標，SB-READER 驗證連接性。
2. **小梁等分座標必須退回重做。**
3. **每條小梁都是版的切割線** —— 版不可跨過任何梁（含小梁）。
4. **每案獨立**——禁止從記憶推斷。
5. **CONFIG-BUILDER 必須執行完 run_all.py 才算完成任務。** 禁止在 run_all.py 執行完畢前向用戶回報「Phase 2 建模完成」。

---

## 團隊編制

| Agent | 代號 | Agent 定義檔 | 職責 |
|-------|------|-------------|------|
| Agent 1 | **SB-READER-A** | `.claude/agents/phase2-sb-reader.md` | 驗證分配的樓層區間 SB 座標連接性 |
| Agent 2 | **SB-READER-B** | `.claude/agents/phase2-sb-reader.md` | 驗證分配的樓層區間 SB 座標連接性 |
| Agent 3 | **CONFIG-BUILDER** | `.claude/agents/phase2-config-builder.md` | 從 sb_elements.json + model_config.json 切版 → sb_slabs_patch.json |

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

### Phase 0.5: 提取標註（PDF 或 PPT）

判斷 `結構配置圖/` 內的輸入檔案類型：

#### 路徑 A：PPT 檔案（.pptx）

PPT 路徑直接提取小梁座標，跳過 annotations.json，也**跳過 Phase 0.7 的 annot_to_elements 步驟**。

```bash
python -m golden_scripts.tools.pptx_to_elements \
  --input "{Case Folder}/結構配置圖/xxx.pptx" \
  --output "{Case Folder}/sb_elements.json" \
  --page-floors "{SB_PAGE_FLOOR_MAPPING}" \
  --phase phase2
```

**驗證**：檢查輸出 summary 的小梁數量是否合理。完成後**跳至 Phase 0.7 步驟 3**（建立資料夾 + 分工）。

#### 路徑 B：PDF 檔案（.pdf）— 現有流程不變

如果 annotations.json 尚未包含小梁相關頁面的標註：

```bash
python -m golden_scripts.tools.pdf_annot_extractor \
  --input "{Case Folder}/結構配置圖/結構尺寸配置.pdf" \
  --pages {SB_PAGES} \
  --output "{Case Folder}/結構配置圖/annotations.json" \
  --crop --crop-dir "{Case Folder}/結構配置圖/"
```

### Phase 0.7: 執行確定性腳本 & 建立資料夾 & 分配驗證工作

> **注意**：如已使用 PPT 路徑（Phase 0.5 路徑 A），步驟 1~2 已完成，直接跳至步驟 3。

1. **讀取結構配置圖 PNG，辨識各頁面的樓層範圍標註**：
   - 讀取 `*_full.png` 圖檔
   - 找出圖面上標註的樓層範圍文字（如「2F~12F 小梁配置」「1F 小梁配置」）
   - 記錄每個頁面的樓層範圍標註
   - 儲存為 `PAGE_FLOOR_LABELS` 變數
2. **執行確定性小梁提取腳本**（⭐ 新增步驟）：
   ```bash
   python -m golden_scripts.tools.annot_to_elements \
     --input "{Case Folder}/結構配置圖/annotations.json" \
     --output "{Case Folder}/sb_elements.json" \
     --page-floors "{PAGE_FLOOR_MAPPING}" \
     --phase phase2
   ```
   其中 `PAGE_FLOOR_MAPPING` 格式如 `"3=1F~2F, 4=3F~14F"`，
   根據步驟 1 辨識的各頁面樓層範圍組成。

   **驗證**：檢查輸出 summary 的小梁數量是否合理。
3. **建立子資料夾**（如尚未存在）：
   ```bash
   mkdir -p "{Case Folder}/結構配置圖/SB-BEAM"
   ```
4. **決定驗證工作分工**（SB-READER 現在只做驗證，不做提取）：
   - 根據用戶標註的樓層區間分配給兩個 SB-READER
   - 原則：工作量大致相等
   - 例如：SB-READER-A 驗證 2F~23F, SB-READER-B 驗證 1F + B1F~B3F

### Phase 1: 建立 Team + 創建任務

```
TeamCreate(team_name="bts-sb-team", description="BTS Phase 2 小梁+版建模")
```

| Task | 主題 | Owner | blockedBy |
|------|------|-------|-----------|
| T1 | SB-READER-A 驗證小梁座標 | SB-READER-A | (無) |
| T2 | SB-READER-B 驗證小梁座標 | SB-READER-B | (無) |
| T3 | CONFIG-BUILDER 生成 patch + merge + snap + 執行 GS | CONFIG-BUILDER | (無) |

### Phase 2A: 啟動 SB-Readers Only

**只啟動** SB-READER-A 和 SB-READER-B，`run_in_background=true`。CONFIG-BUILDER 在 Phase 2.5 才啟動。

```
Agent(
  subagent_type="phase2-sb-reader",
  team_name="bts-sb-team",
  name="SB-READER-A",
  description="驗證小梁座標（樓層區間 1）",
  prompt="你被指派為 BTS-SB Team 的 SB-READER-A。

⭐ 小梁座標已由 annot_to_elements.py 腳本確定性提取完成。
你的職責是**驗證**座標的連接性和合理性，不需要從 annotation.json 提取。

sb_elements.json 路徑：{Case Folder}/sb_elements.json
model_config.json 路徑：{Case Folder}/model_config.json
結構配置圖路徑：{Case Folder}/結構配置圖/
你負責驗證的樓層區間：{SB_GROUP_1_FLOORS}
對應的裁切圖（供視覺交叉比對）：{SB_GROUP_1_PAGES}

請按照 .claude/agents/phase2-sb-reader.md 的指示執行。

驗證項目：
1. 連接性：每根小梁兩端是否接觸大梁/牆/柱/其他小梁（容差 0.3m）
2. 等分模式：是否有小梁恰好落在 1/2、1/3 等分點（標記 WARNING）
3. Grid 邊界：所有小梁座標是否在 Grid 系統範圍內
4. 視覺交叉比對：抽查對照圖面 PNG

驗證資料來源：
- sb_elements.json 的 small_beams 陣列
- model_config.json 的 beams/walls/columns 欄位

輸出驗證結果至：
- 結構配置圖/SB-BEAM/validation_{floor_range}.json

完成後：
1. SendMessage 通知 Team Lead：驗證結果 OK/WARN/REJECT
2. TaskUpdate 標記完成
3. 進入等待模式（監聽 CONFIG-BUILDER 確認要求和 shutdown_request）",
  run_in_background=true
)

Agent(
  subagent_type="phase2-sb-reader",
  team_name="bts-sb-team",
  name="SB-READER-B",
  description="驗證小梁座標（樓層區間 2）",
  prompt="你被指派為 BTS-SB Team 的 SB-READER-B。

⭐ 小梁座標已由 annot_to_elements.py 腳本確定性提取完成。
你的職責是**驗證**座標的連接性和合理性，不需要從 annotation.json 提取。

sb_elements.json 路徑：{Case Folder}/sb_elements.json
model_config.json 路徑：{Case Folder}/model_config.json
結構配置圖路徑：{Case Folder}/結構配置圖/
你負責驗證的樓層區間：{SB_GROUP_2_FLOORS}
對應的裁切圖（供視覺交叉比對）：{SB_GROUP_2_PAGES}

請按照 .claude/agents/phase2-sb-reader.md 的指示執行。

驗證項目：
1. 連接性：每根小梁兩端是否接觸大梁/牆/柱/其他小梁（容差 0.3m）
2. 等分模式：是否有小梁恰好落在 1/2、1/3 等分點（標記 WARNING）
3. Grid 邊界：所有小梁座標是否在 Grid 系統範圍內
4. 視覺交叉比對：抽查對照圖面 PNG

驗證資料來源：
- sb_elements.json 的 small_beams 陣列
- model_config.json 的 beams/walls/columns 欄位

輸出驗證結果至：
- 結構配置圖/SB-BEAM/validation_{floor_range}.json

完成後：
1. SendMessage 通知 Team Lead：驗證結果 OK/WARN/REJECT
2. TaskUpdate 標記完成
3. 進入等待模式（監聽 CONFIG-BUILDER 確認要求和 shutdown_request）",
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
  description="生成 patch → merge → snap → 執行 GS steps 2,7,8",
  prompt="你被指派為 BTS-SB Team 的 CONFIG-BUILDER。
你被延遲啟動。至少一個 SB-READER 已完成驗證。

Case Folder 絕對路徑：{Case Folder}

⭐ 小梁座標已由 annot_to_elements.py 腳本確定性提取至 sb_elements.json。
你直接從 sb_elements.json 讀取小梁座標（不從 SB-BEAM/*.md 讀取）。

步驟（Phase 1 — 生成 patch）：
1. 立即預讀 golden_scripts/config_schema.json
2. 讀取 {Case Folder}/sb_elements.json（小梁座標 — 確定性資料）
3. 讀取 {Case Folder}/model_config.json（大梁座標、Grid 系統、building_outline）
4. 讀取 SB-READER 驗證結果 結構配置圖/SB-BEAM/validation_*.json（如有問題需處理）
5. 等待 Team Lead 的 'ALL_DATA_READY' SendMessage（確認所有驗證完成）
6. 合併小梁 + 大梁座標 → 執行板切割 → sb_slabs_patch.json

步驟（Phase 2 — 合併 + 校正 + 執行 GS）：
7. 生成 sb_slabs_patch.json 後，立即執行：
   python -m golden_scripts.tools.config_merge --base \"{Case Folder}/model_config.json\" --patch \"{Case Folder}/sb_slabs_patch.json\" --output \"{Case Folder}/merged_config.json\" --validate
8. python -m golden_scripts.tools.config_snap --input \"{Case Folder}/merged_config.json\" --output \"{Case Folder}/snapped_config.json\"
9. cd golden_scripts && python run_all.py --config \"{Case Folder}/snapped_config.json\" --steps 2,7,8
10. 如有 ERROR，檢查 config 並修正後重跑失敗的 step（最多重試 2 次）

請按照 .claude/agents/phase2-config-builder.md 的指示執行。

資料來源：
- sb_elements.json 的 small_beams 陣列（小梁座標+斷面+樓層）
- model_config.json 的 beams（大梁座標）、grids、building_outline、slab_region_matrix

整合為 sb_slabs_patch.json：
1. 從 sb_elements.json 取得小梁座標（去重、合併 floors）
2. 以所有梁（大梁+小梁）的座標執行板切割
3. 輸出 small_beams + slabs + sections

板厚資訊：
- 上構板厚：{SLAB_THICKNESS_SUPER}
- 基礎板厚：{SLAB_THICKNESS_FS}（如有）

完成後：
1. 將 sb_slabs_patch.json 寫入 {Case Folder}/
2. 執行 config_merge → config_snap → run_all.py --steps 2,7,8
3. SendMessage 告知 Team Lead：snapped_config.json 路徑 + GS 執行結果（成功/失敗 + 構件數量）
4. TaskUpdate 標記完成",
  run_in_background=true
)
```

#### Step C: 等待所有驗證完成

監控 TaskList，直到 T1 和 T2 都為 "completed"。
SB-READER 驗證工作較輕量，通常不需要負載平衡。

如果任一 SB-READER 回報 `REJECT`：
- 檢視 `validation_*.json` 中的 issues
- 判斷是否需要重新執行 annot_to_elements.py 或手動修正 sb_elements.json
- 問題解決後才可繼續

#### Step D: 通知 CONFIG-BUILDER

SendMessage 給 CONFIG-BUILDER：
"ALL_DATA_READY — 所有 SB-READER 驗證完成。驗證結果：{A_result}, {B_result}。請處理 sb_elements.json 生成 patch。"

#### Step F: 等待 CONFIG-BUILDER 完成

監控 T3 狀態為 "completed"。CONFIG-BUILDER 現在負責完整流程：生成 patch → merge → snap → 執行 GS steps 2,7,8。

#### 邊界情況處理

| Case | Handling |
|------|----------|
| 兩個 SB-Reader 同時完成 | 啟動 CB + 直接發送 ALL_DATA_READY |
| SB-READER 回報 REJECT | 檢視 issues，修正 sb_elements.json 後重新驗證 |
| SB-READER 回報 WARN | 記錄警告，繼續（CONFIG-BUILDER 可處理） |

### Phase 5: 驗證 CONFIG-BUILDER 結果

CONFIG-BUILDER 完成後會 SendMessage 回報 GS 執行結果。Team Lead 確認：
- config_merge 驗證通過
- config_snap 無嚴重 WARNING
- GS steps 2,7,8 全部成功
- 構件數量合理（小梁/版）

如 CB 回報 GS 執行失敗：
- 檢視錯誤訊息
- 協助 CB 修正 config/patch 或排除環境問題
- 必要時手動重跑失敗的 step

### Phase 5 (continued): ETABS 驗證

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
