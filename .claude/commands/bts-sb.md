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
| Agent 3 | **CONFIG-BUILDER** | `.claude/agents/phase2-config-builder.md` | 執行 GS steps 2,7,8 + 錯誤修正（sb_patch+merge+snap+slab 已由腳本完成） |

---

## 執行流程

### Phase 0: 確認前置條件

1. **確認 Phase 1 已完成**：
   - `model_config.json` 存在於 case folder
   - `elements.json` 存在於 case folder（需含 `page_num`，用於 affine 校正）
   - ETABS 模型已開啟且有 Grid+柱+牆+梁
2. **樓層區間自動掃描**（取代手動分類）：
   - 使用 `--scan-floors` 自動從 PPT 掃描樓層標註，不需用戶手動指定
   - 掃描結果含信心度評分，高信心度直接使用，低信心度才請用戶確認
   ```bash
   python -m golden_scripts.tools.pptx_to_elements \
     --input "{Case Folder}/結構配置圖/xxx.pptx" \
     --scan-floors
   ```
3. **板厚**：
   - **先嘗試從 PPT 標註讀取**（掃描 PPT 中的板厚標註，如 "S=15cm", "FS=100cm"）
   - 如 PPT 無標註，再用 AskUserQuestion 詢問用戶

### Step 0: 提取小梁座標（PPT，自動樓層偵測）

掃描 `結構配置圖/` 內的 `.pptx` 檔案：

**方式 A：自動樓層（推薦，Phase 0 掃描結果信心度高時）**
```bash
python -m golden_scripts.tools.pptx_to_elements \
  --input "{Case Folder}/結構配置圖/xxx.pptx" \
  --output "{Case Folder}/sb_elements.json" \
  --auto-floors \
  --phase phase2
```

**方式 B：確認後指定（掃描信心度低時）**
```bash
python -m golden_scripts.tools.pptx_to_elements \
  --input "{Case Folder}/結構配置圖/xxx.pptx" \
  --output "{Case Folder}/sb_elements.json" \
  --confirm-floors \
  --phase phase2
```

**驗證**：檢查輸出 summary 的小梁數量是否合理。

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

#### Step B: 等待所有 SB-Reader 完成

監控 TaskList，直到 T1 和 T2 都為 "completed"。
SB-READER 驗證工作較輕量，通常不需要負載平衡。

如果任一 SB-READER 回報 `REJECT`：
- 檢視 `validation_*.json` 中的 issues
- 判斷是否需要重新執行 pptx_to_elements.py 或手動修正 sb_elements.json
- 問題解決後才可繼續

#### Step C: 發送 RUN_SB_PIPELINE（腳本執行 sb_patch + merge + snap + slab_generator）

所有 SB-READER 驗證完成後，SendMessage 給**先完成的 SB-READER**：

```
SendMessage(
  recipient="SB-READER-A",  // 或 SB-READER-B（先完成者）
  message="RUN_SB_PIPELINE — 所有驗證完成，請執行 SB Pipeline。
CASE_FOLDER={Case Folder}
SLAB_THICKNESS={SLAB_THICKNESS_CM}
RAFT_THICKNESS={RAFT_THICKNESS_CM}"
)
```

SB-READER 會依序執行 4 步腳本（見 phase2-sb-reader.md「SB Pipeline Step」）：
1. `sb_patch_build.py` → sb_patch.json
2. `config_merge` → merged_config.json
3. `config_snap` → snapped_config.json
4. `slab_generator` → final_config.json

#### Step D: 等待 Pipeline 完成

監控 SB-READER 的 SendMessage 回報。成功時會收到「SB pipeline 完成，final_config.json 已生成」。
失敗時會收到具體錯誤，Team Lead 需判斷修正方式。

#### Step E: 啟動 CONFIG-BUILDER（只執行 GS）

Pipeline 成功後，啟動 CONFIG-BUILDER：

```
Agent(
  subagent_type="phase2-config-builder",
  team_name="bts-sb-team",
  name="CONFIG-BUILDER",
  description="執行 GS steps 2,7,8",
  prompt="你被指派為 BTS-SB Team 的 CONFIG-BUILDER。

⭐ final_config.json 已由 sb_patch_build + config_merge + config_snap + slab_generator 腳本生成。
你只需要執行 Golden Scripts 並處理錯誤。

final_config.json 路徑：{Case Folder}/final_config.json

執行：
cd golden_scripts && python run_all.py --config \"{Case Folder}/final_config.json\" --steps 2,7,8

請按照 .claude/agents/phase2-config-builder.md 的指示執行。

完成後：
1. SendMessage 告知 Team Lead：GS 執行結果（成功/失敗 + 構件數量）
2. TaskUpdate 標記完成",
  run_in_background=true
)
```

#### Step F: 等待 CONFIG-BUILDER 完成

監控 T3 狀態為 "completed"。CONFIG-BUILDER 只負責 GS 執行 + 錯誤修正。

#### 邊界情況處理

| Case | Handling |
|------|----------|
| 兩個 SB-Reader 同時完成 | 直接發送 RUN_SB_PIPELINE 給 SB-READER-A |
| SB-READER 回報 REJECT | 檢視 issues，修正 sb_elements.json + 重跑 affine 後重新驗證 |
| SB-READER 回報 WARN | 記錄警告，繼續 |
| Pipeline 腳本失敗 | 檢視錯誤，修正 sb_elements_aligned.json 或 model_config.json 後重發 RUN_SB_PIPELINE |

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

Step 3: SB-READER 執行 SB Pipeline（4 步腳本，秒級完成）：
        sb_patch_build → config_merge → config_snap → slab_generator
        → final_config.json（含板）

Step 4: CONFIG-BUILDER 執行 GS steps 2,7,8 → ETABS model
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
