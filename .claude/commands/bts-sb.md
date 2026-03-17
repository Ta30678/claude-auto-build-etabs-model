---
description: "BTS Phase 2 — 啟動 3 人 Agent Team 建立小梁(SB/FSB)+版(S/FS)。需先完成 /bts-structure。使用方式：/bts-sb [樓層區間說明]"
argument-hint: "[樓層區間說明，例如: 2F~23F=p3, 1F=p4, B1~B3F=p5]"
---

# BTS-SB — Phase 2: 小梁 + 版建模

你現在是 **BTS-SB 團隊的 Team Lead**，負責協調 3 位 Agent 建立小梁和版。

**前置條件**：必須先完成 `/bts-structure`（Phase 1），ETABS 模型已有 Grid+Story+柱+牆+大梁。

**Phase 2 範圍**：小梁(SB/FSB)、樓板(S/FS)
**依賴**：Phase 1 的 `model_config.json`、`grid_data.json`、`SLIDES INFO/`（grid_anchors + screenshots）

---

## 鐵則（ABSOLUTE RULES）

1. **小梁位置禁止猜測！** 由 `pptx_to_elements.py` 確定性提取座標，SB-READER 校正+驗證連接性。
2. **小梁等分座標必須退回重做。**
3. **每條小梁都是版的切割線** —— 版由 `slab_generator.py` 自動處理，不需手動切割。
4. **每案獨立**——禁止從記憶推斷。
5. **CONFIG-BUILDER 必須執行完 run_all.py 才算完成任務。** 禁止在 run_all.py 執行完畢前向用戶回報「Phase 2 建模完成」。

---

## 團隊編制

| Agent | 代號 | Agent 定義檔 | 職責 |
|-------|------|-------------|------|
| Agent 1 | **SB-READER-A** | `.claude/agents/phase2-sb-reader.md` | Per-slide affine 校正 + sb_validate + AI 驗證（分配的樓層） |
| Agent 2 | **SB-READER-B** | `.claude/agents/phase2-sb-reader.md` | Per-slide affine 校正 + sb_validate + AI 驗證（分配的樓層） |
| Agent 3 | **CONFIG-BUILDER** | `.claude/agents/phase2-config-builder.md` | 執行 GS steps 2,7,8 + 錯誤修正 |

---

## 執行流程

### Phase 0: 確認前置條件（Pre-flight）

1. **驗證 Phase 1 產出存在**：
   - `model_config.json` 存在於 case folder
   - `grid_data.json` 存在於 case folder
   - `SLIDES INFO/` 結構存在（Phase 1 READER 輸出）

2. **驗證每個相關 floor 有必要的 Phase 1 檔案**：
   ```
   SLIDES INFO/{fl}/grid_anchors_{fl}.json  — affine 校正用
   SLIDES INFO/{fl}/screenshots/            — 視覺驗證用
   ```
   如缺少 grid_anchors，警告用戶（Phase 2 affine 校正需要 Phase 1 的 grid anchors）。

3. **建立 Phase 2 專用目錄**：
   ```bash
   mkdir -p "{Case Folder}/結構配置圖/SB SLIDES INFO"
   mkdir -p "{Case Folder}/sb_calibrated"
   ```

4. **樓層區間自動掃描**：
   ```bash
   python -m golden_scripts.tools.pptx_to_elements \
     --input "{Case Folder}/結構配置圖/xxx.pptx" \
     --scan-floors
   ```

5. **確認參數**（必問）：
   - `slab_thickness`（一般樓板厚度 cm，例如 15）
   - `raft_thickness`（基礎版厚度 cm，例如 100）

### Phase 0.5: Per-slide SB 提取（Team Lead 一次呼叫）

Team Lead 直接執行 `pptx_to_elements.py`，不委派給 SB-READER：

```bash
python -m golden_scripts.tools.pptx_to_elements \
  --input "{PPT_PATH}" \
  --page-floors "{PAGE_FLOOR_MAPPING}" \
  --phase phase2 \
  --slides-info-dir "{Case Folder}/結構配置圖/SB SLIDES INFO"
```

**輸出**：每個 floor 在 `SB SLIDES INFO/{fl}/sb_{fl}.json` 生成 per-slide SB JSON（PPT-meter 座標）。

**驗證**：
- 檢查每個 floor 的 SB 數量是否合理
- 如果某 floor SB 數量為 0，警告用戶

### Phase 0.7: 分工

根據樓層分配給兩個 SB-READER：
- **SB-READER-A**：上構 floors（e.g., 1F~14F）
- **SB-READER-B**：下構+屋突 floors（e.g., B3F, R1F~R3F）
- 原則：工作量大致相等

### Phase 1: 啟動 SB-READERs（並行，background）

建立 Team + 啟動兩個 SB-READER：

```
TeamCreate(team_name="bts-sb-team", description="BTS Phase 2 小梁+版建模")
```

| Task | 主題 | Owner | blockedBy |
|------|------|-------|-----------|
| T1 | SB-READER-A 校正+驗證小梁座標 | SB-READER-A | (無) |
| T2 | SB-READER-B 校正+驗證小梁座標 | SB-READER-B | (無) |
| T3 | CONFIG-BUILDER 執行 GS | CONFIG-BUILDER | (無) |

**同時啟動**兩個 SB-READER（background）：

```
Agent(
  subagent_type="phase2-sb-reader",
  team_name="bts-sb-team",
  name="SB-READER-A",
  description="校正+驗證小梁（上構）",
  prompt="你被指派為 BTS-SB Team 的 SB-READER-A。

CASE_FOLDER={Case Folder}
GRID_DATA={Case Folder}/grid_data.json
SLIDES_INFO_DIR={Case Folder}/結構配置圖/SLIDES INFO
SB_SLIDES_INFO_DIR={Case Folder}/結構配置圖/SB SLIDES INFO
SB_CALIBRATED_DIR={Case Folder}/sb_calibrated
MODEL_CONFIG={Case Folder}/model_config.json
GROUP_FLOORS={GROUP_1_FLOORS}
GROUP_PAGES={GROUP_1_PAGES}

⭐ SB 座標已由 Team Lead 執行 pptx_to_elements.py --phase phase2 提取到 SB SLIDES INFO/ 目錄。
你的職責是：per-slide affine 校正 + sb_validate + AI 視覺驗證。

Grid anchors 和截圖在 Phase 1 的 SLIDES INFO/ 目錄中，請跨目錄讀取。

請按照 .claude/agents/phase2-sb-reader.md 的指示執行。",
  run_in_background=true
)

Agent(
  subagent_type="phase2-sb-reader",
  team_name="bts-sb-team",
  name="SB-READER-B",
  description="校正+驗證小梁（下構+屋突）",
  prompt="你被指派為 BTS-SB Team 的 SB-READER-B。

CASE_FOLDER={Case Folder}
GRID_DATA={Case Folder}/grid_data.json
SLIDES_INFO_DIR={Case Folder}/結構配置圖/SLIDES INFO
SB_SLIDES_INFO_DIR={Case Folder}/結構配置圖/SB SLIDES INFO
SB_CALIBRATED_DIR={Case Folder}/sb_calibrated
MODEL_CONFIG={Case Folder}/model_config.json
GROUP_FLOORS={GROUP_2_FLOORS}
GROUP_PAGES={GROUP_2_PAGES}

⭐ SB 座標已由 Team Lead 執行 pptx_to_elements.py --phase phase2 提取到 SB SLIDES INFO/ 目錄。
你的職責是：per-slide affine 校正 + sb_validate + AI 視覺驗證。

Grid anchors 和截圖在 Phase 1 的 SLIDES INFO/ 目錄中，請跨目錄讀取。

請按照 .claude/agents/phase2-sb-reader.md 的指示執行。",
  run_in_background=true
)
```

### Phase 2.5: 等待 + Merge + Pipeline（Team Lead）

#### Step A: 等待兩個 SB-READER 完成

監聽 SB-READER 的 SendMessage，等待兩個都回報 `VALIDATION_COMPLETE`。

如果任一 SB-READER 回報 `VALIDATION_FAILED`：
- 檢視錯誤訊息
- 修正後重新啟動失敗的 SB-READER

如果任一 SB-READER 回報含 `REJECT`：
- 檢視 `sb_validation_{fl}.json` 中的 issues
- 判斷是否需要重新執行 pptx_to_elements.py 或手動修正
- 問題解決後才可繼續

#### Step B: 合併 Per-slide SBs

```bash
python -m golden_scripts.tools.elements_merge \
  --inputs-dir "{Case Folder}/sb_calibrated" \
  --phase phase2 \
  --output "{Case Folder}/sb_elements_validated.json"
```

#### Step C: SB Patch

```bash
python -m golden_scripts.tools.sb_patch_build \
  --sb-elements "{Case Folder}/sb_elements_validated.json" \
  --config "{Case Folder}/model_config.json" \
  --output "{Case Folder}/sb_patch.json"
```

#### Step D: Merge Config

```bash
python -m golden_scripts.tools.config_merge \
  --base "{Case Folder}/model_config.json" \
  --patch "{Case Folder}/sb_patch.json" \
  --output "{Case Folder}/merged_config.json" --validate
```

#### Step E: Auto-generate Slabs

```bash
python -m golden_scripts.tools.slab_generator \
  --config "{Case Folder}/merged_config.json" \
  --slab-thickness {SLAB_THICKNESS} \
  --raft-thickness {RAFT_THICKNESS} \
  --output "{Case Folder}/final_config.json"
```

### Phase 2.6: 啟動 CONFIG-BUILDER

Pipeline 成功後，啟動 CONFIG-BUILDER：

```
Agent(
  subagent_type="phase2-config-builder",
  team_name="bts-sb-team",
  name="CONFIG-BUILDER",
  description="執行 GS steps 2,7,8",
  prompt="你被指派為 BTS-SB Team 的 CONFIG-BUILDER。

⭐ final_config.json 已由 Team Lead 執行 elements_merge + sb_patch_build + config_merge + slab_generator 生成。
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

### Phase 5: 驗證 CONFIG-BUILDER 結果

CONFIG-BUILDER 完成後會 SendMessage 回報 GS 執行結果。Team Lead 確認：
- GS steps 2,7,8 全部成功
- 構件數量合理（小梁/版）

如 CB 回報 GS 執行失敗：
- 檢視錯誤訊息
- 協助 CB 修正 config 或排除環境問題
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

## 完整 Pipeline 摘要

```
Phase 0:    Pre-flight（驗證 Phase 1 產出 + 建目錄 + 掃描 + 確認參數）

Phase 0.5:  Team Lead 執行 pptx_to_elements.py --phase phase2 --slides-info-dir
            → SB SLIDES INFO/{fl}/sb_{fl}.json（per-slide SB, PPT-meter）

Phase 0.7:  分工（上構 vs 下構+屋突）

Phase 1:    SB-READER-A ∥ SB-READER-B（並行, per-slide）
            affine_calibrate --mode grid → sb_calibrated/{fl}/sb_elements.json
            sb_validate per-slide → overwrite sb_calibrated/{fl}/sb_elements.json
            AI validation → SB SLIDES INFO/{fl}/sb_validation_{fl}.json

Phase 2.5:  Team Lead 執行合併+工具鏈
            elements_merge --phase phase2 → sb_elements_validated.json
            sb_patch_build → sb_patch.json
            config_merge → merged_config.json
            slab_generator → final_config.json

Phase 2.6:  CONFIG-BUILDER 執行 GS steps 2,7,8 → ETABS model

Phase 5:    驗證（ETABS + 構件數量）

Phase 6:    報告 + Shutdown
```

---

## 中間檔案結構

```
{Case Folder}/
├── 結構配置圖/
│   ├── SLIDES INFO/                        # ═══ Phase 1 專用 ═══
│   │   └── {floor_label}/
│   │       ├── {floor_label}.json          # Phase 1: 大梁/柱/牆 (PPT-meter)
│   │       ├── grid_anchors_{fl}.json      # Phase 1: grid anchors (Phase 2 讀取複用)
│   │       ├── beam_report_{fl}.json       # Phase 1: beam validation report
│   │       └── screenshots/                # Phase 1: 截圖 (Phase 2 讀取複用)
│   │
│   ├── SB SLIDES INFO/                     # ═══ Phase 2 專用 ═══
│   │   └── {floor_label}/
│   │       ├── sb_{floor_label}.json       # Phase 2: 小梁 (PPT-meter)
│   │       ├── sb_report_{fl}.json         # Phase 2: sb_validate report
│   │       └── sb_validation_{fl}.json     # Phase 2: AI validation result (OK/WARN/REJECT)
│   │
│   └── xxx.pptx                            # 結構配置圖
│
├── calibrated/                             # ═══ Phase 1 專用 ═══
│   └── {floor_label}/
│       └── elements.json
│
├── sb_calibrated/                          # ═══ Phase 2 專用 ═══
│   └── {floor_label}/
│       └── sb_elements.json                # Calibrated + validated SBs
│
├── grid_data.json                          # Phase 0.3 ETABS Grid
├── model_config.json                       # Phase 1 output
├── sb_elements_validated.json              # Phase 2 merged SBs
├── sb_patch.json                           # Phase 2 SB patch
├── merged_config.json                      # Phase 2 merged
└── final_config.json                       # Phase 2 final (含自動生成的板)
```

**Phase 2 讀取 Phase 1 的檔案**（跨目錄讀取，不寫入）:
- `SLIDES INFO/{fl}/grid_anchors_{fl}.json` — affine 校正用
- `SLIDES INFO/{fl}/screenshots/` — 視覺驗證用

---

用戶的附加指示：$ARGUMENTS
