---
name: etabs-modeler
description: "ETABS 手動建模與 API 腳本參考。用於 ad-hoc Python 腳本修改模型、查詢分析結果、調整構件屬性等非完整建模任務。觸發條件：用戶需要寫 ETABS Python 腳本、修改模型中的 modifier/rebar/載重、查詢層間位移或構件內力、手動調整 ETABS 模型、使用 COM API 操作 ETABS。注意：完整建模請使用 /bts-gs（Golden Scripts 流程），本技能僅用於局部修改和 API 查詢。"
---

# ETABS Modeler — API Reference for Ad-hoc Scripting

## Overview

本技能用於 **ad-hoc ETABS 腳本** — 局部修改模型、查詢分析結果、調整屬性。

**不適用於完整建模**（完整建模使用 `/bts-gs` + Golden Scripts）。

### 使用時機

| 適用 | 不適用 |
|------|--------|
| 修改所有柱的 modifier | 從零建立完整模型 |
| 查詢某層層間位移 | 定義所有樓層和 Grid |
| 批次調整 rebar cover | 建立所有構件 |
| 讀取分析結果 | 完整載重設定 |
| 導出 Database Table 資料 | 端到端建模流程 |

---

## Connection

```python
from find_etabs import find_etabs
etabs, filename = find_etabs(run=False, backup=False)
SapModel = etabs.SapModel
SapModel.SetPresentUnits(12)  # TON/M
```

完整連線規則見 `CLAUDE.md`。

---

## Common Operations Catalog

### 構件查詢

| 任務 | API 方法 | 範例 |
|------|---------|------|
| 取得所有 frame 名稱 | `SapModel.FrameObj.GetNameList()` | `ret = SapModel.FrameObj.GetNameList(0, [])` |
| 取得 frame 斷面 | `SapModel.FrameObj.GetSection(name)` | `ret[1]` = section name |
| 取得 frame 座標 | `SapModel.FrameObj.GetPoints(name)` | 返回端點名稱 |
| 取得 area 名稱 | `SapModel.AreaObj.GetNameList()` | 同上 |
| 取得 point 座標 | `SapModel.PointObj.GetCoordCartesian(name)` | `(x, y, z)` |

### 屬性修改

| 任務 | API 方法 | 範例 |
|------|---------|------|
| 修改 frame modifier | `SapModel.FrameObj.SetModifiers(name, vals)` | `vals` = 8-element list |
| 修改 area modifier | `SapModel.AreaObj.SetModifiers(name, vals)` | `vals` = 10-element list |
| 設定 frame 斷面 | `SapModel.FrameObj.SetSection(name, sec)` | 變更斷面 |
| 設定 end release | `SapModel.FrameObj.SetReleases(name, II, JJ, S, E)` | M2+M3 release |
| 設定 rigid zone | `SapModel.FrameObj.SetEndLengthOffset(name, True, 0, 0, 0.75)` | RZ=0.75 |
| 設定 rebar (column) | `SapModel.PropFrame.SetRebarColumn(...)` | cover=0.07m |
| 設定 rebar (beam) | `SapModel.PropFrame.SetRebarBeam(...)` | cover=0.09m |

### 載重操作

| 任務 | API 方法 | 範例 |
|------|---------|------|
| 新增 load pattern | `SapModel.LoadPatterns.Add(name, type, sw)` | Dead=1, Live=3, Quake=5 |
| 面載重 | `SapModel.AreaObj.SetLoadUniform(name, pat, val, dir)` | dir=6 (Global-Z) |
| 線載重 | `SapModel.FrameObj.SetLoadDistributed(...)` | dir=11 (Gravity) |
| 點彈簧 | `SapModel.PointObj.SetSpring(name, [0,0,Kv,0,0,0])` | 垂直彈簧 |

### 分析與結果

| 任務 | API 方法 | 範例 |
|------|---------|------|
| 執行分析 | `SapModel.Analyze.RunAnalysis()` | 先 Save |
| 層間位移 | `SapModel.Results.StoryDrifts(...)` | 需先 SetCaseSelectedForOutput |
| 構件內力 | `SapModel.Results.FrameForce(name, 0)` | ObjectElm=0 |
| 模態週期 | `SapModel.Results.ModalPeriod(0, [], [], [], [], [], [])` | |
| Database Table | `SapModel.DatabaseTables.GetTableForDisplayArray(key, ...)` | 見下方 |

### Database Table 批次讀寫

```python
# 讀取
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Story Drifts", [], "All", 0, [], 0, [])
# ret = (retcode, ..., FieldsKeysIncluded, NumberRecords, TableData)

# 使用 etabs_api 高階封裝
df = etabs.database.read("Story Drifts", to_dataframe=True)
```

常用 Table Key：`"Story Definitions"`, `"Frame Section Properties"`, `"Area Section Properties"`,
`"Story Drifts"`, `"Modal Periods And Frequencies"`, `"Concrete Column Summary"`, `"Concrete Beam Summary"`

### Diaphragm

| 任務 | API 方法 |
|------|---------|
| 建立 Diaphragm | `SapModel.Diaphragm.SetDiaphragm(name, False)` |
| 指定到 point | `SapModel.PointObj.SetDiaphragm(pt, 3, name)` |

### 其他

| 任務 | API 方法 |
|------|---------|
| 設定單位 | `SapModel.SetPresentUnits(12)` — 12=Ton_m |
| 解鎖模型 | `SapModel.SetModelIsLocked(False)` |
| 儲存 | `SapModel.File.Save(path)` |
| 重新整理 | `SapModel.View.RefreshView(0, False)` |
| 設定約束 | `SapModel.PointObj.SetRestraint(pt, [T,T,F,F,F,F])` |

---

## Key Constants Reference

```
Frame modifiers (beam):   [1, 1, 1, 0.0001, 0.7, 0.7, 0.8, 0.8]
Frame modifiers (column): [1, 1, 1, 0.0001, 0.7, 0.7, 0.95, 0.95]
Area modifiers (slab/wall): [0.4, 0.4, 0.4, 1, 1, 1, 1, 1, 1, 1]
Area modifiers (raft):      [0.4, 0.4, 0.4, 0.7, 0.7, 0.7, 1, 1, 1, 1]
Rigid zone factor: 0.75
Beam cover: 9cm (regular), 11cm top / 15cm bot (foundation)
Column cover: 7cm
Section: T3=Depth, T2=Width (SetRectangle)
```

---

## Cross-References

| 資源 | 路徑 | 用途 |
|------|------|------|
| Modifier/Rebar 詳細規則 | `references/modifier-rebar-rules.md` | 所有修改器和鋼筋值 |
| Section 解析規則 | `references/section-parsing-rules.md` | 斷面命名解析邏輯 |
| 驗證查詢腳本 | `references/verification-queries.md` | 模型驗證程式碼片段 |
| 驗證腳本 | `scripts/verify_model.py` | 完整模型驗證報告 |
| API 查找方法 | `skills/etabs-api-lookup.md` | 如何查 ETABS API |
| Task Index | `api_docs_index/task_index.md` | 「如何...？」指南 |
| 建模 API | `api_docs_index/group_b_analysis.md` | 建模相關 interface |
| 分析 API | `api_docs_index/group_a_analysis.md` | 分析相關 interface |
| 完整規則 | `CLAUDE.md` | 所有建模規則和常數 |
| Golden Scripts | `golden_scripts/` | 完整自動建模流程 |

---

## Self-Learning Protocol

### 執行前：讀取經驗
載入本 skill 時，讀取 `learned/` 目錄中所有檔案作為補充知識。

### 執行後：紀錄新發現
任務完成後，檢查是否有以下新發現需要紀錄：

1. **patterns.md** — 新發現的 API 用法、未見過的參數組合
2. **mistakes.md** — 本次犯的錯誤及修正方法（含根因分析）
3. **edge-cases.md** — API 文件未涵蓋的特殊情況及處理方式

### 紀錄格式
每條紀錄包含：
- **日期**: YYYY-MM-DD
- **案名**: 專案識別
- **發現**: 具體描述
- **處理**: 採取的做法
- **是否應更新 SKILL.md**: Yes/No（如 Yes，標記待更新的 section）

### 紀錄原則
- 不重複紀錄已有的內容
- 先檢查 learned/ 現有內容再寫入
- 每個檔案保持 <100 行，超過時歸納合併舊條目
- 確認為通用規律後（>=2 次出現），才建議更新 SKILL.md 本體
