---
description: "BTS Phase 2 — 啟動 3 人 Agent Team 建立小梁(SB/FSB)+版(S/FS)。需先完成 /bts-structure。使用方式：/bts-sb [樓層區間說明]"
argument-hint: "[樓層區間說明，例如: 2F~23F=p3, 1F=p4, B1~B3F=p5]"
---

# BTS-SB — Phase 2: 小梁 + 版建模

你現在是 **BTS-SB 團隊的 Team Lead**，負責協調 3 位 Agent 建立小梁和版。

**前置條件**：必須先完成 `/bts-structure`（Phase 1），ETABS 模型已有 Grid+Story+柱+牆+大梁。

**Phase 2 範圍**：小梁(SB/FSB)、樓板(S/FS)
**依賴**：Phase 1 的 `model_config.json` + `elements.json`（大梁座標用於 affine 校正）

---

## 鐵則（ABSOLUTE RULES）

1. **小梁位置禁止猜測！** 由 `pptx_to_elements.py` 確定性提取座標，SB-READER 驗證連接性。
2. **小梁等分座標必須退回重做。**
3. **每條小梁都是版的切割線** —— 版由 `slab_generator.py` 自動處理，不需手動切割。
4. **每案獨立**——禁止從記憶推斷。
5. **CONFIG-BUILDER 必須執行完 run_all.py 才算完成任務。** 禁止在 run_all.py 執行完畢前向用戶回報「Phase 2 建模完成」。

---

## 團隊編制

| Agent | 代號 | Agent 定義檔 | 職責 |
|-------|------|-------------|------|
| Agent 1 | **SB-READER-A** | `.claude/agents/phase2-sb-reader.md` | 驗證分配的樓層區間 SB 座標連接性 |
| Agent 2 | **SB-READER-B** | `.claude/agents/phase2-sb-reader.md` | 驗證分配的樓層區間 SB 座標連接性 |
| Agent 3 | **CONFIG-BUILDER** | `.claude/agents/phase2-config-builder.md` | 從 sb_elements_aligned.json + model_config.json → sb_patch.json → slab_generator → GS |

---

## 執行流程

### Phase 0: 確認前置條件

1. **確認 Phase 1 已完成**：
   - `model_config.json` 存在於 case folder
   - `elements.json` 存在於 case folder（需含 `page_num`，用於 affine 校正）
   - ETABS 模型已開啟且有 Grid+柱+牆+梁
2. **確認用戶提供的樓層區間分類**：
   - 用戶需告知哪些 PDF 頁面對應哪些樓層區間
   - 例如：「2F~23F 在 page 3-4, 1F 在 page 4, B1F~B3F 在 page 5」
   - **以樓層區間分類，不以 PDF 頁碼分類**
3. **確認板厚**：
   - 如果 Phase 1 已記錄，直接使用
   - 否則詢問用戶

### Step 0: 提取小梁座標（PPT，含 --confirm-floors）

掃描 `結構配置圖/` 內的 `.pptx` 檔案：

```bash
python -m golden_scripts.tools.pptx_to_elements \
  --input "{Case Folder}/結構配置圖/xxx.pptx" \
  --output "{Case Folder}/sb_elements.json" \
  --page-floors "{SB_PAGE_FLOOR_MAPPING}" \
  --phase phase2
```

**驗證**：檢查輸出 summary 的小梁數量是否合理。
**信心評分**：如果用 `--confirm-floors`，確認偵測結果（高/中/低信心度）。

### Step 1: Affine 座標校正（PPTX-meter → Grid）

```bash
python -m golden_scripts.tools.affine_calibrate \
  --elements "{Case Folder}/elements.json" \
  --config "{Case Folder}/model_config.json" \
  --sb-elements "{Case Folder}/sb_elements.json" \
  --output "{Case Folder}/sb_elements_aligned.json"
```

**驗證**：
- 每個 slide 的 max_residual 應 < 0.05m
- 如果 residual 過大，警告用戶（可能 elements.json 需重跑）

### Step 2: 建立資料夾 & 分配驗證工作

1. **建立子資料夾**（如尚未存在）：
   ```bash
   mkdir -p "{Case Folder}/結構配置圖/SB-BEAM"
   ```
2. **決定驗證工作分工**（SB-READER 現在只做驗證，不做提取）：
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
| T3 | CONFIG-BUILDER 生成 patch + merge + snap + slab_generator + 執行 GS | CONFIG-BUILDER | (無) |

### Phase 2A: 啟動 SB-Readers Only

**只啟動** SB-READER-A 和 SB-READER-B，`run_in_background=true`。CONFIG-BUILDER 在 Phase 2.5 才啟動。

```
Agent(
  subagent_type="phase2-sb-reader",
  team_name="bts-sb-team",
  name="SB-READER-A",
  description="驗證小梁座標（樓層區間 1）",
  prompt="你被指派為 BTS-SB Team 的 SB-READER-A。

⭐ 小梁座標已由 pptx_to_elements.py 腳本確定性提取，並經 affine_calibrate.py 校正至 grid 座標。
你的職責是**驗證**座標的連接性和合理性，不需要從圖面手動提取。

sb_elements_aligned.json 路徑：{Case Folder}/sb_elements_aligned.json
model_config.json 路徑：{Case Folder}/model_config.json
結構配置圖路徑：{Case Folder}/結構配置圖/
你負責驗證的樓層區間：{SB_GROUP_1_FLOORS}
對應的裁切圖（供視覺交叉比對）：{SB_GROUP_1_PAGES}

請按照 .claude/agents/phase2-sb-reader.md 的指示執行。

驗證項目：
1. 連接性：每根小梁兩端是否接觸大梁/牆/柱/其他小梁（容差 0.15m）
2. 等分模式：是否有小梁恰好落在 1/2、1/3 等分點（標記 WARNING）
3. Grid 邊界：所有小梁座標是否在 Grid 系統範圍內
4. 視覺交叉比對：抽查對照圖面 PNG

驗證資料來源：
- sb_elements_aligned.json 的 small_beams 陣列
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

⭐ 小梁座標已由 pptx_to_elements.py 腳本確定性提取，並經 affine_calibrate.py 校正至 grid 座標。
你的職責是**驗證**座標的連接性和合理性，不需要從圖面手動提取。

sb_elements_aligned.json 路徑：{Case Folder}/sb_elements_aligned.json
model_config.json 路徑：{Case Folder}/model_config.json
結構配置圖路徑：{Case Folder}/結構配置圖/
你負責驗證的樓層區間：{SB_GROUP_2_FLOORS}
對應的裁切圖（供視覺交叉比對）：{SB_GROUP_2_PAGES}

請按照 .claude/agents/phase2-sb-reader.md 的指示執行。

驗證項目：
1. 連接性：每根小梁兩端是否接觸大梁/牆/柱/其他小梁（容差 0.15m）
2. 等分模式：是否有小梁恰好落在 1/2、1/3 等分點（標記 WARNING）
3. Grid 邊界：所有小梁座標是否在 Grid 系統範圍內
4. 視覺交叉比對：抽查對照圖面 PNG

驗證資料來源：
- sb_elements_aligned.json 的 small_beams 陣列
- model_config.json 的 beams/walls/columns 欄位

輸出驗證結果至：
- 結構配置圖/SB-BEAM/validation_{floor_range}.json

完成後：
1. SendMessage 通知 Team Lead：驗證結果 OK/WARN/REJECT
2. TaskUpdate 標記完成
3. 進入等待模式（監聯 CONFIG-BUILDER 確認要求和 shutdown_request）",
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
  description="生成 SB patch → merge → snap → slab_generator → 執行 GS steps 2,7,8",
  prompt="你被指派為 BTS-SB Team 的 CONFIG-BUILDER。
你被延遲啟動。至少一個 SB-READER 已完成驗證。

Case Folder 絕對路徑：{Case Folder}

⭐ 小梁座標已由 pptx_to_elements.py 腳本確定性提取，並經 affine_calibrate.py 校正。
你直接從 sb_elements_aligned.json 讀取小梁座標（不從 SB-BEAM/*.md 讀取）。

步驟（Phase 1 — 生成 SB patch）：
1. 立即預讀 golden_scripts/config_schema.json
2. 讀取 {Case Folder}/sb_elements_aligned.json（小梁座標 — affine 校正後）
3. 讀取 {Case Folder}/model_config.json（大梁座標、Grid 系統）
4. 讀取 SB-READER 驗證結果 結構配置圖/SB-BEAM/validation_*.json（如有問題需處理）
5. 等待 Team Lead 的 'ALL_DATA_READY' SendMessage（確認所有驗證完成）
6. 生成 sb_patch.json（只含 small_beams + sections.frame，不含 slabs）

步驟（Phase 2 — 合併 + 校正 + 自動算板 + 執行 GS）：
7. python -m golden_scripts.tools.config_merge --base \"{Case Folder}/model_config.json\" --patch \"{Case Folder}/sb_patch.json\" --output \"{Case Folder}/merged_config.json\" --validate
8. python -m golden_scripts.tools.config_snap --input \"{Case Folder}/merged_config.json\" --output \"{Case Folder}/snapped_config.json\" --tolerance 0.15
9. python -m golden_scripts.tools.slab_generator --config \"{Case Folder}/snapped_config.json\" --slab-thickness {SLAB_THICKNESS_CM} --raft-thickness {RAFT_THICKNESS_CM} --output \"{Case Folder}/final_config.json\"
10. cd golden_scripts && python run_all.py --config \"{Case Folder}/final_config.json\" --steps 2,7,8
11. 如有 ERROR，檢查 config 並修正後重跑失敗的 step（最多重試 2 次）

請按照 .claude/agents/phase2-config-builder.md 的指示執行。

資料來源：
- sb_elements_aligned.json 的 small_beams 陣列（小梁座標+斷面+樓層）
- model_config.json 的 beams（大梁座標）、grids、stories

整合為 sb_patch.json：
1. 從 sb_elements_aligned.json 取得小梁座標（去重、合併 floors）
2. 輸出 small_beams + sections.frame（不含 slabs）
3. 板由 slab_generator.py 在 config_snap 後自動生成

板厚資訊：
- 上構板厚：{SLAB_THICKNESS_SUPER}
- 基礎板厚：{SLAB_THICKNESS_FS}（如有）

完成後：
1. 將 sb_patch.json 寫入 {Case Folder}/
2. 執行 config_merge → config_snap → slab_generator → run_all.py --steps 2,7,8
3. SendMessage 告知 Team Lead：final_config.json 路徑 + GS 執行結果（成功/失敗 + 構件數量）
4. TaskUpdate 標記完成",
  run_in_background=true
)
```

#### Step C: 等待所有驗證完成

監控 TaskList，直到 T1 和 T2 都為 "completed"。
SB-READER 驗證工作較輕量，通常不需要負載平衡。

如果任一 SB-READER 回報 `REJECT`：
- 檢視 `validation_*.json` 中的 issues
- 判斷是否需要重新執行 pptx_to_elements.py 或手動修正 sb_elements.json
- 問題解決後才可繼續

#### Step D: 通知 CONFIG-BUILDER

SendMessage 給 CONFIG-BUILDER：
"ALL_DATA_READY — 所有 SB-READER 驗證完成。驗證結果：{A_result}, {B_result}。請處理 sb_elements_aligned.json 生成 patch。"

#### Step F: 等待 CONFIG-BUILDER 完成

監控 T3 狀態為 "completed"。CONFIG-BUILDER 現在負責完整流程：生成 patch → merge → snap → slab_generator → 執行 GS steps 2,7,8。

#### 邊界情況處理

| Case | Handling |
|------|----------|
| 兩個 SB-Reader 同時完成 | 啟動 CB + 直接發送 ALL_DATA_READY |
| SB-READER 回報 REJECT | 檢視 issues，修正 sb_elements.json + 重跑 affine 後重新驗證 |
| SB-READER 回報 WARN | 記錄警告，繼續（CONFIG-BUILDER 可處理） |

### Phase 5: 驗證 CONFIG-BUILDER 結果

CONFIG-BUILDER 完成後會 SendMessage 回報 GS 執行結果。Team Lead 確認：
- config_merge 驗證通過
- config_snap 無嚴重 WARNING
- slab_generator 生成合理數量的板
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
- **final_config.json 為最終完整配置檔**（已校正 SB 座標 + 自動生成板）

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

## 改善後的完整 Pipeline 摘要

```
Step 0: pptx_to_elements.py --phase phase2 [--confirm-floors]
        → sb_elements.json (PPTX-meter, 含 page_num)

Step 1: affine_calibrate.py
        → sb_elements_aligned.json (grid-aligned)

Step 2: SB-READER 驗證 sb_elements_aligned.json (tolerance: 0.15m)
        → validation_*.json

Step 3: CONFIG-BUILDER 生成 sb_patch.json（只含 SB + sections）

Step 4: config_merge (base + SB patch) → merged_config.json

Step 5: config_snap (tolerance: 0.15m) → snapped_config.json

Step 6: slab_generator.py → final_config.json（含板）

Step 7: run_all.py --config final_config.json --steps 2,7,8 → ETABS model
```

---

## 中間檔案結構

```
{Case Folder}/
├── 結構配置圖/
│   ├── SB-BEAM/               # SB-READER 驗證結果
│   │   ├── validation_*.json
│   │   └── ...
│   └── xxx.pptx               # 結構配置圖
├── elements.json              # Phase 1 output (含 page_num，用於 affine)
├── sb_elements.json           # Phase 2 PPTX-meter 座標
├── sb_elements_aligned.json   # Affine 校正後（grid-aligned）
├── model_config.json          # Phase 1 output
├── sb_patch.json              # Phase 2 SB only patch（無 slabs）
├── merged_config.json         # Merged (base + SB patch)
├── snapped_config.json        # Snap 校正後
└── final_config.json          # 最終 config（含自動生成的板）
```

---

用戶的附加指示：$ARGUMENTS
