---
description: "Build Team Structure - 啟動 4 人資深結構工程師 Agent Team，解讀結構配置圖並建立 ETABS 模型。使用方式：/BTS [樓層/圖片說明]"
argument-hint: "[樓層說明或附加指示]"
---

# BTS - Build Team Structure (Agent Team 版 — 協力模式)

你現在是 **BTS 團隊的 Team Lead**，負責建立並協調 4 位資深結構工程師 Agent Team。

---

## 團隊編制

| Agent | 代號 | Agent 定義檔 | 職責 |
|-------|------|-------------|------|
| Agent 1 | **READER** | `.claude/agents/reader.md` | 解讀結構配置圖：柱、大梁、壁梁、剪力牆、Grid |
| Agent 2 | **SB-READER** | `.claude/agents/sb-reader.md` | 小梁像素量測與精確座標計算 |
| Agent 3 | **MODELER-A** | `.claude/agents/modeler-a.md` | 材料/斷面/Grid/樓層/柱/牆 |
| Agent 4 | **MODELER-B** | `.claude/agents/modeler-b.md` | 梁/板/載重/釋放/勁度折減/隔膜 |

---

## 執行流程

### Phase 0: 確認輸入（強制參數檢查）

**必要參數清單（MUST ASK）** — 以下任何一項缺失，必須立即詢問用戶，禁止跳過或使用預設值：

| # | 參數 | 說明 | 預設值 |
|---|------|------|--------|
| 1 | 結構配置圖 | 固定路徑 `{Case Folder}/結構配置圖/` | 自動掃描 |
| 2 | 樓層高度表 | 各樓層高度 (m)，含基礎層 | **無，必問** |
| 3 | 強度分配表 | 混凝土等級 by 樓層區段 | **無，必問** |
| 4 | LL 值 | ton/m2（活載重） | 0.3 ton/m2 |
| 5 | 基礎 Kv | 基礎版彈簧係數 | 可選 |
| 6 | 邊梁 Kw | 連續壁側邊彈簧係數 | 可選 |
| 7 | 反應譜檔案 | 路徑或函數定義 | 可選 |
| 8 | Base Shear Coefficient C | 地震力係數 | 可選 |
| 9 | EQV Scale Factor | 等值靜力放大係數 | 可選 |
| 10 | 板厚 | 各區板厚度 (cm) | **無，必問** |
| 11 | 基礎樓層 | 基礎樓層名稱（BASE 上一層，例如 B3F）— FS/鎖點/Kv/Kw 皆設於此層 | **無，必問** |

**規則：標記「無，必問」的參數禁止跳過。有預設值的參數僅在用戶未提供時使用預設值。**
用戶可透過 $ARGUMENTS 覆蓋任何預設值。

### Phase 1: 建立 Team + 創建任務

**Step 1**: 建立團隊

```
TeamCreate(team_name="bts-team", description="BTS 結構建模團隊")
```

**Step 2**: 創建任務（含依賴關係）

用 TaskCreate 建立以下任務，然後用 TaskUpdate 設定 blockedBy 依賴：

| Task | 主題 | Owner | blockedBy |
|------|------|-------|-----------|
| T1 | READER 讀圖：辨識柱/梁/牆/Grid | READER | (無) |
| T2 | SB-READER 小梁定位：像素量測+座標計算 | SB-READER | (無) |
| T3 | MODELER-A 基礎建設：材料/斷面/Grid/樓層/柱/牆 | MODELER-A | T1 |
| T4 | MODELER-B 上層建設：梁/板/載重/釋放/隔膜 | MODELER-B | T1, T2, T3 |
| T5 | 驗證與整合：檢查模型完整性 | (Team Lead) | T3, T4 |

### Phase 2: 一次啟動所有 Agent（協力模式）

**同時**啟動 4 個 Agent，全部 `run_in_background=true`。
**不等待任何 Agent 完成**，立即進入 Phase 3 監控模式。

Agent 之間的依賴透過 SendMessage 自行管理：
- READER / SB-READER：立即開始工作，完成後主動 SendMessage 給 MODELER
- MODELER-A / MODELER-B：先預讀文件，收到資料後自動開始建模

```
Agent(
  subagent_type="reader",
  team_name="bts-team",
  name="READER",
  description="讀取結構配置圖",
  prompt="你被指派為 BTS Team 的 READER。請按照你的 agent 定義執行工作。

結構配置圖路徑：{Case Folder}/結構配置圖/
用戶說明：$ARGUMENTS
樓層資訊：[樓層高度表]

請先讀取 skills/plan-reader/SKILL.md 了解完整流程，然後開始讀圖。
**你必須為每個區段（每張結構配置圖）分別產出結構摘要。不同區段可能有不同的柱/梁配置，不可假設相同。**

完成後：
1. 用 SendMessage 將結構化摘要**直接發給 MODELER-A 和 MODELER-B**（不經過 Team Lead）
2. 用 TaskUpdate 標記 T1 完成
3. 進入等待模式，持續監聽來自 MODELER-A/MODELER-B 的後續問題",
  run_in_background=true
)

Agent(
  subagent_type="sb-reader",
  team_name="bts-team",
  name="SB-READER",
  description="小梁精確定位",
  prompt="你被指派為 BTS Team 的 SB-READER。請按照你的 agent 定義執行工作。

結構配置圖路徑：{Case Folder}/結構配置圖/
用戶說明：$ARGUMENTS

請先讀取 skills/plan-reader/SKILL.md 第六節了解小梁定位方法，然後開始工作。
**你必須為每個區段（每張結構配置圖）分別產出小梁座標表。不同區段的小梁配置可能不同，必須逐一讀取，不可假設相同。**

完成後：
1. 用 SendMessage 將小梁座標表**直接發給 MODELER-B**（不經過 Team Lead）
2. 用 TaskUpdate 標記 T2 完成
3. 進入等待模式——MODELER-B 會逐區段向你確認小梁配置，你必須留在線上回應",
  run_in_background=true
)

Agent(
  subagent_type="modeler-a",
  team_name="bts-team",
  name="MODELER-A",
  description="ETABS 基礎建設",
  prompt="你被指派為 BTS Team 的 MODELER-A。請按照你的 agent 定義執行工作。

【自驅動模式】你已與 READER 同時啟動。請按以下順序行動：
1. 立即開始預讀 skills/etabs-modeler/SKILL.md 和 CLAUDE.md（不需等任何人）
2. 等待 READER 透過 SendMessage 發送結構化摘要
3. 收到摘要後立即開始建模

強度分配表：[強度分配]
樓層高度：[樓層高度表]
基礎層位置：[FS 所在樓層]

**注意基礎層規則：FS 基礎版所在樓層（BASE 上一層）不建立柱。**

Grid 和 Stories 完成後：
→ 立即用 SendMessage 通知 MODELER-B：「Grid 和樓層已定義完成」
→ 繼續建立柱和牆（不需等 MODELER-B 回應）

全部完成後用 SendMessage 告知 Team Lead。",
  run_in_background=true
)

Agent(
  subagent_type="modeler-b",
  team_name="bts-team",
  name="MODELER-B",
  description="ETABS 上層建設",
  prompt="你被指派為 BTS Team 的 MODELER-B。請按照你的 agent 定義執行工作。

【自驅動模式】你已與所有 Agent 同時啟動。請按以下順序行動：
1. 立即開始預讀 skills/etabs-modeler/SKILL.md 和 CLAUDE.md（不需等任何人）
2. 等待以下 3 個前置條件（全部透過 SendMessage 接收，不經過 Team Lead）：
   a. READER 的結構化摘要
   b. SB-READER 的小梁座標表
   c. MODELER-A 的 Grid/Stories 完成通知
3. 全部收到後開始建模

強度分配表：[強度分配]
Live 載重：[LIVE_VALUE] ton/m2
樓層高度：[樓層高度表]
基礎層位置：[FS 所在樓層]

**小梁建模必須逐區段與 SB-READER 討論確認：**
每個區段 → SendMessage 問 SB-READER 確認 → 驗證座標 → 建立。
詳細流程見你的 agent 定義。

全部完成後用 SendMessage 告知 Team Lead。",
  run_in_background=true
)
```

### Phase 3: 監控與支援

所有 Agent 啟動後，Team Lead 進入監控模式：

1. 定期用 `TaskList` 檢查任務進度
2. 處理 Agent 的 escalation（缺少參數 → 詢問用戶）
3. 等待所有 Task 標記完成
4. 如果超過合理時間沒有進展，用 `SendMessage` 詢問 Agent 狀態

### Phase 4: 驗證與整合

所有 MODELER 完成後：

1. 匯總兩邊的報告
2. 執行驗證檢查（參考 skills/etabs-modeler/SKILL.md Section 8 的 Verification Checklist）
3. 向用戶報告建模結果摘要

### Phase 5: Shutdown Team

所有 Agent 統一結束：

```
SendMessage(type="shutdown_request", recipient="READER")
SendMessage(type="shutdown_request", recipient="SB-READER")
SendMessage(type="shutdown_request", recipient="MODELER-A")
SendMessage(type="shutdown_request", recipient="MODELER-B")
```

---

## Agent 互動模式（協力模式）

本 Team 的核心優勢是 Agent 之間**直接溝通**，不經過 Team Lead 轉發。

### 協力時間線：
```
|--READER---------|  (完成讀圖後進入等待模式，回應問題)
|--SB-READER------|  (完成定位後進入等待模式，回應問題)
   |---MODELER-A (預讀docs)---|---建模---|
      |---MODELER-B (預讀docs)---|--等Grid--|---建梁板---|
0     t1                       t2        t3          t4
```

### Agent 間 SendMessage 路徑：
```
READER ──SendMessage──→ MODELER-A  （結構摘要）
READER ──SendMessage──→ MODELER-B  （結構摘要）
SB-READER ──SendMessage──→ MODELER-B  （小梁座標表）
MODELER-A ──SendMessage──→ MODELER-B  （Grid/Stories 完成通知）
MODELER-B ──SendMessage──→ SB-READER  （逐區段確認小梁）
SB-READER ──SendMessage──→ MODELER-B  （確認後回覆座標表）
MODELER-B ──SendMessage──→ READER     （如需確認梁尺寸）
READER ──SendMessage──→ MODELER-B     （回覆確認）
```

Team Lead（你）的角色：
- 建立團隊和任務
- 提供初始 context（用戶參數）
- 監控進度（透過 TaskList）
- 處理 escalation（Agent 遇到無法解決的問題時）
- 最終驗證和報告

---

## 重要規則

1. **謹慎原則**：四位 Agent 都是資深工程師，遇到不確定的事項一律詢問，不猜測
2. **分工明確**：READER 負責柱/大梁/壁梁/牆，SB-READER 專責小梁定位；MODELER-A 和 MODELER-B 的工作項目不重疊
3. **直接溝通**：Agent 之間透過 SendMessage 直接交流，不需經過 Team Lead
4. **D/B 不可搞反**：SetRectangle(Name, Material, T3=深度, T2=寬度)
5. **小梁座標來源**：MODELER-B 建立小梁時，必須使用 SB-READER 提供的精確座標，且必須逐區段確認
6. **強度分配必查**：建立任何構件前，必須根據強度分配表確定該樓層的混凝土等級
7. **禁止使用預設值**：所有建模參數因案例而異，缺失參數必須回報 Team Lead 詢問用戶
8. **基礎樓層規則**：基礎樓層 = BASE 上一層。BASE 層無任何物件。基礎樓層設置 FS 基礎版/鎖點/Kv/Kw，但不建柱往 BASE（柱從基礎樓層上方 story 開始）
9. **逐區段確認小梁**：MODELER-B 必須對每個樓層區段分別與 SB-READER 確認小梁配置，禁止只讀最低樓層套用全部
10. **不使用 SDL 載重**：模型只有 DL 和 LL 載重工況，不建立 SDL
11. **樓層配置必須從 case folder 確認**：每案樓層配置不同（如 "24F/B6" = 上構24F+屋突層+下構到B6F），禁止從記憶或過去案子推斷，必須從該 case 的樓層高度表或結構配置圖取得
12. **R1F 屋突層規則**：R1F 梁/板同頂樓；ETABS R1F 柱 = 頂樓柱、R2F 柱 = R1F 柱（柱往下長）；R2F 以上通常無圖，用 R1F 的 2x2 Grid 核心區間延伸到 PRF
13. **共構下構範圍 3 種情況**：(1) 上構柱區已是最外邊→直接延續；(2) 最外邊不在 Grid Line→按比例外推，不建柱；(3) 最外邊在 Grid Line→往外一跨，不建柱。同一案不同立面可能對應不同情況，需逐面判斷

---

## 開始執行

收到用戶指令後，立即進入 Phase 0 確認輸入，然後依序執行 Phase 1 -> Phase 2（一次啟動全部 Agent）-> Phase 3（監控）-> Phase 4 -> Phase 5。

用戶的附加指示：$ARGUMENTS
