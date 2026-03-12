---
description: "BTS Phase 2 (等分小梁) — 啟動 EQ-READER Agent + eq_sb_generator.py 建立等分小梁座標，再接 Phase 2 CONFIG-BUILDER 建版。需先完成 /bts-structure。使用方式：/bts-sb-eq [樓層說明]"
argument-hint: "[樓層說明，例如: 2F~23F, 板厚15cm]"
---

# BTS-SB-EQ — 等分小梁建模流程

你現在是 **BTS-SB-EQ 的 Team Lead**，負責協調等分小梁的建模流程。

**前置條件**：必須先完成 `/bts-structure`（Phase 1），`model_config.json` 已存在。

**適用情境**：
1. 工程師明確知道設計就是等分（精確宣告）
2. 初期概估快速建模（無 Bluebeam annotation 情況）

**注意**：等分座標由 `eq_sb_generator.py` 數學計算，是工程師宣告等分設計意圖，不違反 Rule #4。

---

## 鐵則（ABSOLUTE RULES）

1. **等分設計必須工程師明確宣告。** 不可由 AI 主動猜測「這個跨距應該是等分」。
2. **`divisions` 預設 2（中點一根）**，除非用戶明確指定其他分數。
3. **EQ-READER 不量測圖片座標**。跨距端點座標一律從 `model_config.json` 大梁取得。
4. **每條等分小梁都是版的切割線**——版不可跨過任何梁（含等分小梁）。
5. **CONFIG-BUILDER 必須執行完 run_all.py 才算完成任務。**

---

## 執行流程

### Phase 0: 確認前置條件

1. **確認 Phase 1 已完成**：
   - `model_config.json` 存在於 case folder
   - ETABS 模型已開啟且有 Grid+柱+牆+大梁
2. **確認板厚**（詢問用戶或從 Phase 1 記錄取得）
3. **告知用戶**：EQ-READER 將讀取結構配置圖，識別哪些跨距要放等分小梁。

### Phase 1: 啟動 EQ-READER

```
TeamCreate(team_name="bts-sb-eq-team", description="BTS 等分小梁建模")
```

啟動 EQ-READER（前景，需等待結果）：

```
Agent(
  subagent_type="phase2-eq-reader",
  team_name="bts-sb-eq-team",
  name="EQ-READER",
  description="識別等分小梁跨距，輸出 eq_sb_rules.json",
  prompt="你被指派為 BTS-SB-EQ Team 的 EQ-READER。

Case Folder 絕對路徑：{Case Folder}
model_config.json 路徑：{Case Folder}/model_config.json
結構配置圖路徑：{Case Folder}/結構配置圖/
用戶指定樓層說明：{ARGUMENTS}

請按照 .claude/agents/phase2-eq-reader.md 的指示執行。

工作：
1. 讀取 model_config.json，取得大梁座標和 Grid 系統
2. 讀取結構配置圖圖片（*_full.png），識別哪些跨距有等分小梁
3. 確認 section 名稱和 floors 範圍
4. 輸出 {Case Folder}/eq_sb_rules.json

完成後 SendMessage 通知 Team Lead：eq_sb_rules.json 已生成，規則數量。",
  run_in_background=false
)
```

### Phase 2: 執行確定性計算

EQ-READER 完成後，執行 eq_sb_generator.py：

```bash
python -m golden_scripts.tools.eq_sb_generator \
  --rules "{Case Folder}/eq_sb_rules.json" \
  --output "{Case Folder}/sb_elements.json"
```

驗證輸出：
- 確認 `sb_elements.json` 已生成
- 檢查小梁數量是否合理
- 確認座標格式正確（數值，非字串）

### Phase 3: 啟動 CONFIG-BUILDER

**注意：不啟動 phase2-sb-reader**（等分座標是刻意設計，不需要等分警告驗證）。

```
Agent(
  subagent_type="phase2-config-builder",
  team_name="bts-sb-eq-team",
  name="CONFIG-BUILDER",
  description="生成 patch → merge → snap → 執行 GS steps 2,7,8",
  prompt="你被指派為 BTS-SB-EQ Team 的 CONFIG-BUILDER。

Case Folder 絕對路徑：{Case Folder}

⭐ 小梁座標已由 eq_sb_generator.py 等分計算輸出至 sb_elements.json。
   等分座標是工程師刻意宣告的設計，不是 AI 猜測。
   驗證 checklist 的「小梁座標不是機械性等分」項目對本次不適用，跳過此項。

步驟：
1. 立即預讀 golden_scripts/config_schema.json
2. 讀取 {Case Folder}/sb_elements.json（等分小梁座標）
3. 讀取 {Case Folder}/model_config.json（大梁座標、Grid 系統、building_outline）
4. 合併小梁 + 大梁座標 → 執行板切割 → {Case Folder}/sb_slabs_patch.json
5. 執行驗證 Checklist（跳過等分檢查項目）
6. python -m golden_scripts.tools.config_merge --base \"{Case Folder}/model_config.json\" --patch \"{Case Folder}/sb_slabs_patch.json\" --output \"{Case Folder}/merged_config.json\" --validate
7. python -m golden_scripts.tools.config_snap --input \"{Case Folder}/merged_config.json\" --output \"{Case Folder}/snapped_config.json\"
8. cd golden_scripts && python run_all.py --config \"{Case Folder}/snapped_config.json\" --steps 2,7,8

板厚資訊：
- 上構板厚：{SLAB_THICKNESS_SUPER}
- 基礎板厚：{SLAB_THICKNESS_FS}（如有）

請按照 .claude/agents/phase2-config-builder.md 的指示執行。

完成後：
1. SendMessage 告知 Team Lead：snapped_config.json 路徑 + GS 執行結果
2. TaskUpdate 標記完成",
  run_in_background=false
)
```

### Phase 4: 驗證結果

CONFIG-BUILDER 完成後確認：
- config_merge 驗證通過
- config_snap 無嚴重 WARNING
- GS steps 2,7,8 全部成功
- ETABS 中小梁位置精確落在等分點

### Phase 5: 報告結果

向用戶報告：
- 等分小梁建模完成
- 構件數量（小梁/版）
- 提醒：下一步執行 Phase 3（`/bts-props`）
- **snapped_config.json 為最終完整配置檔**

### Phase 6: Shutdown

```
SendMessage(type="shutdown_request", recipient="EQ-READER")
SendMessage(type="shutdown_request", recipient="CONFIG-BUILDER")
```

---

## 中間檔案結構

```
{Case Folder}/
├── model_config.json          # Phase 1 輸出（前置條件）
├── eq_sb_rules.json           # EQ-READER 輸出（等分規則）
├── sb_elements.json           # eq_sb_generator.py 輸出（等分座標）
├── sb_slabs_patch.json        # CONFIG-BUILDER 輸出
├── merged_config.json         # config_merge 輸出
└── snapped_config.json        # 最終完整配置檔
```

---

用戶的附加指示：$ARGUMENTS
