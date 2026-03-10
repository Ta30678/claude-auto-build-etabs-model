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

### Phase 0.7: 建立資料夾 & 分配工作

1. **建立子資料夾**（如尚未存在）：
   ```bash
   mkdir -p "{Case Folder}/結構配置圖/SB-BEAM"
   ```
2. **決定樓層區間分工**：
   - 根據用戶標註的樓層區間分配給兩個 SB-READER
   - 原則：工作量大致相等
   - 例如：SB-READER-A 負責 2F~23F, SB-READER-B 負責 1F + B1F~B3F

### Phase 1: 建立 Team + 創建任務

```
TeamCreate(team_name="bts-sb-team", description="BTS Phase 2 小梁+版建模")
```

| Task | 主題 | Owner | blockedBy |
|------|------|-------|-----------|
| T1 | SB-READER-A 讀取小梁 | SB-READER-A | (無) |
| T2 | SB-READER-B 讀取小梁 | SB-READER-B | (無) |
| T3 | CONFIG-BUILDER 生成 patch | CONFIG-BUILDER | T1, T2 |
| T4 | Merge + 執行 Golden Scripts | (Team Lead) | T3 |

### Phase 2: 啟動 3 個 Agent

**同時**啟動 SB-READER-A、SB-READER-B、CONFIG-BUILDER，全部 `run_in_background=true`。

```
Task(
  subagent_type="phase2-sb-reader",
  team_name="bts-sb-team",
  name="SB-READER-A",
  description="讀取小梁座標（樓層區間 1）",
  prompt="你被指派為 BTS-SB Team 的 SB-READER-A。

結構配置圖路徑：{Case Folder}/結構配置圖/
你負責的樓層區間：{SB_GROUP_1_FLOORS}
對應的 PDF 頁面/裁切圖：{SB_GROUP_1_PAGES}
標註 JSON：{Case Folder}/結構配置圖/annotations.json

請按照 .claude/agents/phase2-sb-reader.md 的指示執行。
先讀取 skills/plan-reader/SKILL.md 了解完整流程。

驗證小梁連接性時，可參照：
- 結構配置圖/BEAM/*.md 中的大梁座標
- 或 model_config.json 中的 beams 欄位

輸出檔案至：
- 結構配置圖/SB-BEAM/{floor_range}.md

完成後：
1. SendMessage 通知 CONFIG-BUILDER
2. TaskUpdate 標記完成
3. 進入等待模式",
  run_in_background=true
)

Task(
  subagent_type="phase2-sb-reader",
  team_name="bts-sb-team",
  name="SB-READER-B",
  description="讀取小梁座標（樓層區間 2）",
  prompt="你被指派為 BTS-SB Team 的 SB-READER-B。

結構配置圖路徑：{Case Folder}/結構配置圖/
你負責的樓層區間：{SB_GROUP_2_FLOORS}
對應的 PDF 頁面/裁切圖：{SB_GROUP_2_PAGES}
標註 JSON：{Case Folder}/結構配置圖/annotations.json

請按照 .claude/agents/phase2-sb-reader.md 的指示執行。
先讀取 skills/plan-reader/SKILL.md 了解完整流程。

驗證小梁連接性時，可參照：
- 結構配置圖/BEAM/*.md 中的大梁座標
- 或 model_config.json 中的 beams 欄位

輸出檔案至：
- 結構配置圖/SB-BEAM/{floor_range}.md

完成後：
1. SendMessage 通知 CONFIG-BUILDER
2. TaskUpdate 標記完成
3. 進入等待模式",
  run_in_background=true
)

Task(
  subagent_type="phase2-config-builder",
  team_name="bts-sb-team",
  name="CONFIG-BUILDER",
  description="生成 sb_slabs_patch.json",
  prompt="你被指派為 BTS-SB Team 的 CONFIG-BUILDER。

先讀取以下檔案：
1. golden_scripts/config_schema.json（了解格式）
2. {Case Folder}/model_config.json（取得大梁座標、Grid 系統、building_outline）
3. 結構配置圖/BEAM/*.md 中的 Slab Region Matrix（樓板區域判斷）

等待 SB-READER-A 和 SB-READER-B 的 SendMessage 通知，然後從資料夾讀取：
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

### Phase 3: 監控 → 等待 CONFIG-BUILDER 完成

Team Lead 進入監控模式，等 T3 完成。

### Phase 4: Merge + 執行 Golden Scripts

CONFIG-BUILDER 完成後，Team Lead 執行：

**Step 1: 合併配置檔**
```bash
python -m golden_scripts.tools.config_merge \
  --base "{Case Folder}/model_config.json" \
  --patch "{Case Folder}/sb_slabs_patch.json" \
  --output "{Case Folder}/merged_config.json"
```

檢查 merge 輸出：
- small_beams 數量 > 0
- slabs 數量 > 0
- frame sections 包含 SB 斷面

**Step 2: 執行 Golden Scripts**
```bash
cd golden_scripts
python run_all.py --config "{Case Folder}/merged_config.json" --steps 2,7,8
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
- **merged_config.json 為最終完整配置檔**

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
