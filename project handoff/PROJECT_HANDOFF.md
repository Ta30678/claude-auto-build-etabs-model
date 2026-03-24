# 專案接手操作手冊

> **專案名稱**: V22 AGENTIC MODEL — AI 驅動 ETABS 結構建模系統
> **最後更新**: 2026-03-24
> **核心功能**: 透過 Claude Code (CLI) 的 AI Agent Team，從結構配置圖 (PPT) 自動建立 ETABS 22 結構模型

---

## 目錄

1. [環境需求與設定](#1-環境需求與設定)
2. [專案目錄結構](#2-專案目錄結構)
3. [核心概念：四種建模工作流](#3-核心概念四種建模工作流)
4. [Slash Commands（指令）](#4-slash-commands指令)
5. [Agents（AI 代理人）](#5-agentsai-代理人)
6. [Skills（技能模組）](#6-skills技能模組)
7. [Golden Scripts（建模腳本）](#7-golden-scripts建模腳本)
8. [Tools（CLI 工具集）](#8-toolscli-工具集)
9. [重要檔案用途說明](#9-重要檔案用途說明)
10. [中間產物檔案結構](#10-中間產物檔案結構)
11. [測試](#11-測試)
12. [MCP Server](#12-mcp-server)
13. [完整操作範例：三階段建模](#13-完整操作範例三階段建模)
14. [重要工程規則](#14-重要工程規則)
15. [常見問題與除錯](#15-常見問題與除錯)

---

## 1. 環境需求與設定

| 項目        | 需求                                                                                        |
| ----------- | ------------------------------------------------------------------------------------------- |
| ETABS       | 22 版，安裝於 `C:/Program Files/Computers and Structures/ETABS 22/ETABS.exe`                |
| Python      | 3.11.7                                                                                      |
| Python 套件 | `comtypes` 1.4.16, `numpy`, `pandas`, `etabs_api` (1.2), `python-pptx`, `Pillow`, `shapely` |
| Claude Code | Anthropic CLI，模型需支援 Agent/Skill/SendMessage                                           |
| OS          | Windows 10/11                                                                               |

### ETABS 連線方式

**所有腳本**都必須透過 `find_etabs` 模組連線。此模組隨 `etabs_api` 套件安裝（`pip install etabs_api`），**不在本專案目錄內**：

```python
from find_etabs import find_etabs
etabs, filename = find_etabs(run=False, backup=False)
SapModel = etabs.SapModel
```

**禁止**直接使用 `comtypes.client.GetActiveObject()`。`etabs_api` 會處理 COM 型別轉換問題。
對於 `etabs_api` 未封裝的操作，可直接存取底層 API：`etabs.SapModel.*`。

### 預設單位

- Golden Scripts 使用 **Ton-m** (code 12)
- 部分 legacy 腳本使用 kgf-cm (code 14)

---

## 2. 專案目錄結構

```
V22 AGENTIC MODEL/
├── .claude/
│   ├── commands/           # Slash command 定義（/bts-structure, /bts-sb, 等）
│   ├── agents/             # Agent 定義（phase1-reader, phase2-sb-reader, 等）
│   └── settings.local.json # Claude Code 本地設定
├── .mcp.json               # MCP Server 設定（ETABS MCP）
├── CLAUDE.md               # ★ 核心指引文件 — Claude Code 的所有規則都在此
├── etabs_current_state.md  # ★ ETABS 模型快照（某時點的 Database Table dump）
├── ERROR 紀錄.txt          # 開發過程中的問題紀錄與決策記錄
│
├── golden_scripts/         # ★ 核心建模引擎
│   ├── run_all.py          # 主 orchestrator（--config, --steps, --dry-run）
│   ├── constants.py        # 所有工程規則硬編碼（modifiers, rebar, 樓層分類）
│   ├── config_schema.json  # model_config.json 的 JSON Schema
│   ├── example_config.json # A21 案例參考 config
│   ├── modeling/           # gs_01~gs_11（11 個建模步驟）
│   ├── design/             # gs_12（分析設計迭代）
│   ├── tools/              # CLI 工具集（pptx_to_elements, affine_calibrate, 等）
│   └── qc/                 # QC 驗證腳本
│
├── skills/                 # Skill 定義（結構術語、斷面命名、API 查詢、等）
├── tests/                  # pytest 測試套件
├── api_docs/               # ETABS API 原始 HTML 文件（1693 個 .htm）
├── api_docs_index/         # 預建 API 索引（task_index.md, categories.json）
├── scripts/                # MCP Server 實驗版本
├── ETABS REF/              # 參考案例（A21 NEW, 產後護理）— 含完整中間檔案
├── rc_iterations/          # RC 迭代分析設計結果
├── docs/                   # superpowers 文件
├── models/                 # ETABS 輸出模型檔（.EDB）
└── CSI API ETABS v1.chm   # ETABS API CHM 離線文件
```

---

## 3. 核心概念：四種建模工作流

| #   | 工作流         | 指令                                        | 說明                                  | 推薦度   |
| --- | -------------- | ------------------------------------------- | ------------------------------------- | -------- |
| 1   | **三階段建模** | `/bts-structure` → `/bts-sb` → `/bts-props` | 分三階段減少 token 消耗，提高 AI 品質 | ★★★ 首選 |
| 2   | 單次建模       | `/bts-gs`                                   | 一次完成全部，token 消耗大            | ★★ 備用  |
| 3   | Ad-hoc 腳本    | 直接對話                                    | Claude 寫一次性 Python 腳本           | 視需求   |

### 三階段建模流程圖

```
使用者準備 PPT 結構配置圖 + ETABS Grid System
                    │
                    ▼
    ┌──── Phase 1: /bts-structure ────┐
    │  read_grid → pptx_to_elements  │
    │  → affine_calibrate            │
    │  → beam_validate               │
    │  → config_build                │
    │  → run_all --steps 1,2,3,4,5,6 │
    │  輸出: model_config.json       │
    │  ETABS: Grid+Story+柱+牆+大梁  │
    └────────────────────────────────┘
                    │
                    ▼
    ┌──── Phase 2: /bts-sb ──────────┐
    │  pptx_to_elements --phase2     │
    │  → affine_calibrate            │
    │  → sb_validate                 │
    │  → sb_patch_build + merge      │
    │  → slab_generator              │
    │  → run_all --steps 2,7,8       │
    │  輸出: final_config.json       │
    │  ETABS: +小梁+版               │
    └────────────────────────────────┘
                    │
                    ▼
    ┌──── Phase 3: /bts-props ───────┐
    │  run_all --steps 9,10,11       │
    │  Modifiers + 載重 + Diaphragms │
    │  ETABS: 完成建模               │
    └────────────────────────────────┘
                    │
                    ▼
        (可選) /rc-iteration ( rc-sub/rc-super 上下構分開設計的指令) → RC 設計迭代
```

---

## 4. Slash Commands（指令）

在 Claude Code 中輸入 `/指令名稱` 觸發。定義在 `.claude/commands/` 目錄。

### 建模指令（BTS 系列）

| 指令             | 檔案                        | 說明                                                                                                                                |
| ---------------- | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `/bts-structure` | `commands/bts-structure.md` | **Phase 1**: 啟動 2 READER + 1 CONFIG-BUILDER Agent Team，建立 Grid+Story+柱+牆+大梁。需要使用者提供 PPT 路徑和 page-floors 對應。  |
| `/bts-sb`        | `commands/bts-sb.md`        | **Phase 2**: 啟動 2 SB-READER + 1 CONFIG-BUILDER Agent Team，建立小梁+版。需要先完成 Phase 1。                                      |
| `/bts-sb-eq`     | `commands/bts-sb-eq.md`     | **Phase 2 (等分小梁)**: 使用 `eq_sb_generator.py` 數學計算等分小梁座標（非 AI 猜測），適用於工程師刻意設計等分小梁的情境。          |
| `/bts-props`     | `commands/bts-props.md`     | **Phase 3**: 無 Agent Team，Team Lead 收集參數（C 係數、Kv/Kw 彈簧、反應譜路徑、外牆線載重），再執行 `run_all.py --steps 9,10,11`。 |
| `/bts-qc1`       | `commands/bts-qc1.md`       | **Phase 1 QC**: 比對 ETABS 模型 vs `model_config.json`，執行 8 項檢查。                                                             |
| `/bts-gs`        | `commands/OLD/bts-gs.md`    | **(舊版)** 3-agent 單次建模。Token 消耗大，已移至 OLD。                                                                             |

### E2K 工具指令

| 指令     | 檔案                | 說明                                              |
| -------- | ------------------- | ------------------------------------------------- |
| `/split` | `commands/split.md` | 將多棟合併的 e2k 拆分成單棟模型（保留共構下構）。 |
| `/merge` | `commands/merge.md` | 將多個單棟 e2k 合併回一個分析模型。               |

### RC 設計指令

| 指令            | 檔案                       | 說明                                 |
| --------------- | -------------------------- | ------------------------------------ |
| `/rc-iteration` | `commands/rc-iteration.md` | RC 分析設計迭代（上構+下構兩階段）。 |
| `/rc-super`     | `commands/rc-super.md`     | 僅上構 RC 迭代（USS 設計組合）。     |
| `/rc-sub`       | `commands/rc-sub.md`       | 僅下構 RC 檢核（BUSS 設計組合）。    |

---

## 5. Agents（AI 代理人）

定義在 `.claude/agents/` 目錄。每個 Agent 有特定角色、可用工具、輸入輸出。

### Phase 1 Agents（`/bts-structure` 使用）

| Agent                   | 檔案                              | 角色                                                                                                                    | 可用工具                                   |
| ----------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `phase1-reader`         | `agents/phase1-reader.md`         | 結構配置圖判讀專家。讀取 PPT 中的 Grid 名稱/座標、建物外框、柱/梁/牆位置。                                              | Bash, Read, Glob, Grep, Write, SendMessage |
| `phase1-config-builder` | `agents/phase1-config-builder.md` | GS 執行專家。驗證 `model_config.json`（schema + floors +1 rule），執行 Golden Scripts steps 1-6。**禁止修改構件陣列**。 | All tools                                  |

**Phase 1 流程**: Team Lead 啟動 2 個 `phase1-reader`（分別讀上構/下構），完成後用 `elements_merge` + `config_build` 生成 config，再由 `phase1-config-builder` 執行建模。

### Phase 2 Agents（`/bts-sb` 使用）

| Agent                   | 檔案                              | 角色                                                                                            | 可用工具                                   |
| ----------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `phase2-sb-reader`      | `agents/phase2-sb-reader.md`      | 小梁驗證專家。Per-slide 校正+驗證小梁座標連接性。                                               | Bash, Read, Glob, Grep, Write, SendMessage |
| `phase2-config-builder` | `agents/phase2-config-builder.md` | GS 執行專家。執行 Golden Scripts steps 2,7,8。構件陣列受 SHA-256 完整性檢查保護，**禁止修改**。 | All tools                                  |
| `phase2-eq-reader`      | `agents/phase2-eq-reader.md`      | 等分小梁識別專家（用於 `/bts-sb-eq`）。讀圖+識別哪些跨距需等分小梁。                            | Read, Glob, Grep, Write, SendMessage       |

### E2K Agents

| Agent          | 檔案                     | 角色                |
| -------------- | ------------------------ | ------------------- |
| `e2k-merger`   | `agents/e2k-merger.md`   | 合併多棟 e2k 檔案。 |
| `e2k-splitter` | `agents/e2k-splitter.md` | 拆分多棟 e2k 模型。 |

### Legacy Agents（`OLD/` 目錄，已停用）

| Agent            | 檔案                           | 說明                                                                            |
| ---------------- | ------------------------------ | ------------------------------------------------------------------------------- |
| `reader`         | `agents/OLD/reader.md`         | 舊版結構圖判讀（AI 視覺識別，非 pptx_to_elements）。                            |
| `sb-reader`      | `agents/OLD/sb-reader.md`      | 舊版小梁讀取（從 Bluebeam annotation.json，非 PPT 提取）。                      |
| `config-builder` | `agents/OLD/config-builder.md` | 舊版 config 生成（手動整合 READER/SB-READER 輸出，禁止執行 Python/ETABS API）。 |

---

## 6. Skills（技能模組）

定義在 `skills/` 目錄。Claude Code 根據觸發條件自動載入。

### 結構工程 Skills（本專案核心）

| Skill                    | 路徑                                   | 用途                                                                                                    |
| ------------------------ | -------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **structural-glossary**  | `skills/structural-glossary/SKILL.md`  | 結構術語標準定義（上構/下構/屋突/共構/分棟），樓層分類邏輯，構件前綴對照表。所有 Agent/Skill 共同參考。 |
| **plan-reader**          | `skills/plan-reader/SKILL.md`          | 結構配置圖核心解讀器。協調 `plan-reader-elements` 和 `plan-reader-floors`，確保完整解讀流程。           |
| **plan-reader-elements** | `skills/plan-reader-elements/SKILL.md` | 構件辨識規則：圖例讀取、Grid 座標系統、特殊柱位（退縮/斜撐）、共構邊界判斷。                            |
| **plan-reader-floors**   | `skills/plan-reader-floors/SKILL.md`   | 樓層對應規則：+1 floor rule（柱/牆的 ETABS 樓層 = 平面圖樓層 +1）、屋突層定義、樓板判斷。               |
| **section-name**         | `skills/section-name/SKILL.md`         | 斷面命名與解析：B55X80 → T3=0.80, T2=0.55 的 D/B Swap、強度分配、柱筋計算。                             |
| **etabs-modeler**        | `skills/etabs-modeler/SKILL.md`        | Ad-hoc ETABS API 腳本參考（局部修改模型用，非完整建模）。                                               |
| **etabs-api-lookup**     | `skills/etabs-api-lookup.md`           | ETABS COM API 查詢流程：如何從 `api_docs/` 找到正確的方法簽名。                                         |
| **rc-design**            | `skills/rc-design/SKILL.md`            | RC 分析設計：ACI 318-19 sway types、配筋比計算、斷面迭代、設計組合。                                    |
| **e2k-split**            | `skills/e2k-split/SKILL.md`            | E2K 分棟拆分操作指引。                                                                                  |
| **e2k-merge**            | `skills/e2k-merge/SKILL.md`            | E2K 合棟合併操作指引。                                                                                  |

### 通用 Skills（Superpowers 插件提供）

| Skill               | 用途                           |
| ------------------- | ------------------------------ |
| **doc-coauthoring** | 文件共同撰寫。                 |
| **docx**            | Word .docx 操作（OOXML）。     |
| **pptx**            | PowerPoint .pptx 操作。        |
| **pdf**             | PDF 操作（表單填寫、轉圖片）。 |
| **xlsx**            | Excel .xlsx 操作。             |
| **mcp-builder**     | MCP Server 開發指引。          |
| **skill-creator**   | 新 Skill 的建立與迭代測試。    |

---

## 7. Golden Scripts（建模腳本）

位於 `golden_scripts/` 目錄。全部是**確定性腳本**（Deterministic）— 不含 AI 推理，純粹讀取 `model_config.json` 並執行 ETABS API。

### 主要 Orchestrator

```bash
# 完整建模
python run_all.py --config model_config.json

# 指定步驟（如只跑 columns + walls）
python run_all.py --config model_config.json --steps 4,5

# 預覽不執行
python run_all.py --config model_config.json --dry-run
```

### 建模步驟（gs_01 ~ gs_11）

| Step | 腳本                             | 功能                                       | 備註                        |
| ---- | -------------------------------- | ------------------------------------------ | --------------------------- |
| 01   | `modeling/gs_01_init.py`         | 建立新模型 + 材料 (C280~C490, SD420/SD490) | `new_model=true` 會重置所有 |
| 02   | `modeling/gs_02_sections.py`     | 批次建立斷面 + D/B swap + 配筋 + modifiers |                             |
| 03   | `modeling/gs_03_grid_stories.py` | Grid 系統（跳過若已預建） + Story 定義     |                             |
| 04   | `modeling/gs_04_columns.py`      | 柱（內建 +1 floor rule）                   |                             |
| 05   | `modeling/gs_05_walls.py`        | 牆（+1 floor rule，連續壁 → C280）         |                             |
| 06   | `modeling/gs_06_beams.py`        | 大梁 (B, WB, FB)                           |                             |
| 07   | `modeling/gs_07_small_beams.py`  | 小梁 (SB)                                  | Phase 2 使用                |
| 08   | `modeling/gs_08_slabs.py`        | 版 (S=Membrane, FS=ShellThick)             | Phase 2 使用                |
| 09   | `modeling/gs_09_properties.py`   | Modifiers + 剛域 (0.75) + 端釋放           | Phase 3                     |
| 10   | `modeling/gs_10_loads.py`        | DL/LL/EQ + 反應譜 + 基礎彈簧               | Phase 3                     |
| 11   | `modeling/gs_11_diaphragms.py`   | Diaphragm 指定                             | Phase 3                     |

### 設計步驟（gs_12）

| Step | 腳本                      | 功能                                   |
| ---- | ------------------------- | -------------------------------------- |
| 12   | `design/gs_12_iterate.py` | ACI 318-19 配筋比優化迭代（最多 5 輪） |

### 常數定義 (`constants.py`)

所有工程規則集中在此檔案，包括：

```
Frame modifiers (beam):   [1, 1, 1, 0.0001, 0.7, 0.7, 0.8, 0.8]
Frame modifiers (column): [1, 1, 1, 0.0001, 0.7, 0.7, 0.95, 0.95]
Area modifiers (slab):    [0.4, 0.4, 0.4, 1, 1, 1, 1, 1, 1, 1]
Area modifiers (raft):    [0.4, 0.4, 0.4, 0.7, 0.7, 0.7, 1, 1, 1, 1]
Rigid zone factor: 0.75
Beam cover: 9cm (一般), 11cm top / 15cm bot (基礎)
Column cover: 7cm
```

---

## 8. Tools（CLI 工具集）

位於 `golden_scripts/tools/`。可獨立執行，也被 Agent 呼叫。

### 核心 Pipeline 工具

| 工具                 | 指令                                              | 功能                                                                          |
| -------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------- |
| **pptx_to_elements** | `python -m golden_scripts.tools.pptx_to_elements` | 從 PPT 確定性提取構件座標（Phase 1: 柱/梁/牆, Phase 2: 小梁）。核心提取引擎。 |
| **affine_calibrate** | `python -m golden_scripts.tools.affine_calibrate` | Grid 模式仿射校正：PPT 座標 → ETABS 座標（基於 grid anchors）。               |
| **beam_validate**    | `python -m golden_scripts.tools.beam_validate`    | Phase 1 梁驗證：角度校正 + ray snap + 群集 + 分割。                           |
| **sb_validate**      | `python -m golden_scripts.tools.sb_validate`      | Phase 2 小梁驗證：角度校正 + snap + cluster + split。                         |
| **elements_merge**   | `python -m golden_scripts.tools.elements_merge`   | 合併多個 per-slide JSON 為單一 elements.json。                                |
| **config_build**     | `python -m golden_scripts.tools.config_build`     | 將 elements.json + grid_info.json 合併為 model_config.json。                  |
| **sb_patch_build**   | `python -m golden_scripts.tools.sb_patch_build`   | 從 sb_elements_validated.json 提取小梁 → sb_patch.json。                      |
| **config_merge**     | `python -m golden_scripts.tools.config_merge`     | 合併 Phase 1 base config + Phase 2 SB patch。                                 |
| **slab_generator**   | `python -m golden_scripts.tools.slab_generator`   | 圖論演算法自動生成板多邊形（從梁佈局切割）。                                  |
| **plot_elements**    | `python -m golden_scripts.tools.plot_elements`    | 視覺化 elements JSON（含 Grid overlay）。                                     |

### 輔助工具

| 工具                       | 功能                                                                 |
| -------------------------- | -------------------------------------------------------------------- |
| **read_grid**              | 從 ETABS 讀取預建 Grid System → `grid_data.json`。Phase 1 前置步驟。 |
| **config_snap**            | Snap SB 座標到最近結構元素。                                         |
| **config_integrity**       | 檢查 config 完整性。                                                 |
| **diagnose_elev**          | 比對 config elev_map vs ETABS 實際高程。                             |
| **diagnose_rebar**         | 檢查配筋設定。                                                       |
| **discover_seismic_table** | 自動偵測地震力表格。                                                 |
| **eq_sb_generator**        | 等分小梁座標數學計算（`/bts-sb-eq` 使用）。                          |
| **geometry**               | 幾何運算工具函式。                                                   |

### E2K 工具

| 工具               | 功能             |
| ------------------ | ---------------- |
| **gs_split**       | 分棟拆分 e2k。   |
| **gs_merge**       | 合棟合併 e2k。   |
| **e2k_parser**     | E2K 檔案解析器。 |
| **e2k_writer**     | E2K 檔案寫入器。 |
| **unit_converter** | 單位轉換。       |

---

## 9. 重要檔案用途說明

### 核心設定檔

| 檔案                                 | 用途                                                                                                                                           |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `CLAUDE.md`                          | **最重要的檔案**。Claude Code 的所有工作規則、API 參考、工程規則、指令用法都在此。任何修改行為都以此為準。                                     |
| `.mcp.json`                          | MCP Server 設定。目前連接 `scripts/structural-mcp-servers/servers/etabs_mcp/current_working/server.py`，提供 ETABS 連線/資訊查詢的 MCP tools。 |
| `.claude/settings.local.json`        | Claude Code 本地權限設定（哪些命令允許自動執行）。                                                                                             |
| `golden_scripts/config_schema.json`  | `model_config.json` 的 JSON Schema。所有 config 都必須符合此 schema。                                                                          |
| `golden_scripts/example_config.json` | A21 案例的完整 config 範例，可作為新案的參考模板。                                                                                             |
| `golden_scripts/constants.py`        | **所有工程規則硬編碼在此**：frame/area modifiers、配筋規則、樓層分類邏輯、斷面解析。修改工程規則只需改此檔。                                   |

### 狀態與紀錄檔

| 檔案                     | 用途                                                                                                                                                                                                                                                                             |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `etabs_current_state.md` | ETABS 模型的 Database Table 完整 dump（某時點快照）。包含：Unit 設定、Grid Lines、Story Definitions、Material Properties、Frame/Area Section Properties、Frame/Area Assignments、Load Patterns 等。用於離線分析模型狀態，不需 ETABS 執行。**注意**：此為靜態快照，不會自動更新。 |
| `ERROR 紀錄.txt`         | 開發過程中的問題紀錄與設計決策。記錄了：Grid Line 不能由 Agent 設定的問題、PPT 視覺遮擋問題、屋突層處理方式、token 浪費問題、構件遺漏問題等。**新開發者應先讀此檔**了解歷史踩坑紀錄。                                                                                            |

### API 文件

| 路徑                                 | 用途                                                   |
| ------------------------------------ | ------------------------------------------------------ |
| `api_docs/CSI API ETABS v1.hhc`      | ETABS API 主目錄（可搜尋方法名稱）。                   |
| `api_docs/html/`                     | 1693 個 .htm 方法文件。                                |
| `api_docs_index/task_index.md`       | 任務導向查詢（"How do I add a beam?"）。               |
| `api_docs_index/group_a_analysis.md` | Analysis, Results, Load Cases, Design Codes 詳細文件。 |
| `api_docs_index/group_b_analysis.md` | Modeling, Properties, DB Tables 詳細文件。             |
| `api_docs_index/categories.json`     | Interface 分類對照。                                   |
| `CSI API ETABS v1.chm`               | ETABS API 離線 CHM 文件（原始檔）。                    |

### 參考案例

| 路徑                  | 用途                                                                                                                                                                       |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ETABS REF/A21 NEW/`  | A21 案例的完整建模中間產物（Phase 1 + Phase 2），包含所有 per-slide JSON、grid_anchors、calibrated、screenshots、最終 config。**最佳參考案例**，包含 SB Phase 2 完整流程。 |
| `ETABS REF/產後護理/` | 產後護理案例的建模中間產物（較舊格式，Phase 1 only）。                                                                                                                     |
| `rc_iterations/`      | RC 設計迭代結果（5 輪迭代 + final_summary.json）。                                                                                                                         |

### 其他

| 路徑                              | 用途                                                    |
| --------------------------------- | ------------------------------------------------------- |
| `scripts/structural-mcp-servers/` | ETABS MCP Server 開發版本歷史（v0.1~v0.7+），實驗性質。 |
| `docs/superpowers/`               | Superpowers 插件文件。                                  |
| `temp_import/`                    | 臨時匯入區。                                            |
| `雜項/`                           | 雜項工具/測試。                                         |

---

## 10. 中間產物檔案結構

每個建模案例會在 Case Folder 產生以下中間檔案：

```
{Case Folder}/
├── 結構配置圖/
│   ├── plan.pptx                          # 使用者的結構配置圖
│   │
│   ├── SLIDES INFO/                        # ═══ Phase 1 專用 ═══
│   │   └── {floor_label}/                  # 例: 1F, B3F, 3F~14F
│   │       ├── pptx_to_elements/
│   │       │   ├── {floor_label}.json      # 原始提取的構件 (PPT-meter 座標)
│   │       │   └── {floor_label}.png       # 提取結果繪圖
│   │       ├── calibrated/
│   │       │   ├── calibrated.json         # 校正+驗證後的構件 (ETABS 座標)
│   │       │   └── calibrated.png          # 校正結果繪圖
│   │       ├── grid_anchors_{fl}.json      # Grid 錨點 (Phase 2 複用)
│   │       ├── beam_report_{fl}.json       # beam_validate 報告
│   │       └── screenshots/                # PPT 截圖
│   │
│   ├── SB SLIDES INFO/                     # ═══ Phase 2 專用 ═══
│   │   └── {floor_label}/
│   │       ├── pptx_to_elements/
│   │       │   ├── sb_{floor_label}.json   # 原始 SB 提取
│   │       │   └── sb_{floor_label}.png    # 提取結果繪圖
│   │       ├── calibrated/
│   │       │   ├── calibrated.json         # 校正+驗證後的 SB
│   │       │   └── calibrated.png          # 校正結果繪圖
│   │       ├── sb_report_{fl}.json         # sb_validate 報告
│   │       └── sb_validation_{fl}.json     # AI 驗證結果 (OK/WARN/REJECT)
│   │
│   └── grid_info.json                      # Phase 1 READER 輸出 (outline/stories)
│
├── grid_data.json                          # Phase 0 從 ETABS 讀取的 Grid (ground truth)
├── elements.json                           # Phase 1 合併結果
├── model_config.json                       # Phase 1 輸出 config (無 SB/slabs)
├── sb_elements_validated.json              # Phase 2 合併驗證後 SB
├── sb_patch.json                           # Phase 2 SB patch
├── merged_config.json                      # Phase 2 base + SB patch
└── final_config.json                       # Phase 2 最終 config (含自動生成的板)
```

---

## 11. 測試

### Mock 測試（不需 ETABS）

```bash
# 執行所有 mock 測試
pytest tests/test_pptx_color_matching.py tests/test_beam_validate.py \
       tests/test_sb_validate.py tests/test_slab_generator.py \
       tests/test_affine_calibrate.py tests/test_config_build.py \
       tests/test_elements_merge.py tests/test_sb_patch_build.py \
       tests/test_plot_elements.py -v

# 單一檔案
pytest tests/test_beam_validate.py -v

# 單一測試
pytest tests/test_beam_validate.py::TestRaySnap::test_snap_to_nearest -v
```

### ETABS 驗證測試（需 ETABS 執行中）

```bash
# 全部測試（ETABS 不在時自動 skip）
pytest tests/ -v

# 搭配 config 比對
pytest tests/ -v --config path/to/model_config.json
```

### 測試檔案對照

| 測試檔案                      | 測試對象                         |
| ----------------------------- | -------------------------------- |
| `test_pptx_color_matching.py` | PPT 顏色匹配邏輯                 |
| `test_pptx_to_elements.py`    | PPT 構件提取                     |
| `test_affine_calibrate.py`    | 仿射校正                         |
| `test_beam_validate.py`       | 梁驗證 (角度校正/ray snap/split) |
| `test_sb_validate.py`         | 小梁驗證                         |
| `test_slab_generator.py`      | 板多邊形生成                     |
| `test_config_build.py`        | Config 構建                      |
| `test_sb_patch_build.py`      | SB patch 提取                    |
| `test_elements_merge.py`      | Elements 合併                    |
| `test_plot_elements.py`       | 繪圖工具                         |
| `test_config_integrity.py`    | Config 完整性                    |
| `test_grid_calibrate.py`      | Grid 校正                        |
| `test_wall_split.py`          | 牆分割                           |
| `test_slab_zones.py`          | 板厚分區                         |
| `test_sections.py`            | 斷面定義                         |
| `test_iteration.py`           | RC 迭代                          |
| `test_diaphragms.py`          | Diaphragm (ETABS)                |
| `test_element_counts.py`      | 構件數量 (ETABS)                 |
| `test_loads.py`               | 載重 (ETABS)                     |
| `test_modifiers.py`           | Modifiers (ETABS)                |
| `test_rebar.py`               | 配筋 (ETABS)                     |
| `test_rigid_zones.py`         | 剛域 (ETABS)                     |
| `test_units.py`               | 單位 (ETABS)                     |

---

## 12. MCP Server

設定於 `.mcp.json`，提供 ETABS 連線的 MCP tools：

```json
{
  "mcpServers": {
    "etabs": {
      "command": "python",
      "args": [
        "scripts/structural-mcp-servers/servers/etabs_mcp/current_working/server.py"
      ]
    }
  }
}
```

提供的 MCP Tools:

- `connect_etabs` — 連線 ETABS
- `get_etabs_model_info` — 讀取模型資訊
- `test_connection` — 測試連線

MCP Server 開發歷史在 `scripts/structural-mcp-servers/servers/etabs_mcp/` 下有 v0.1~v0.7 的版本記錄。

---

## 13. 完整操作範例：三階段建模

### 前置準備

1. **準備結構配置圖 PPT** — 放在 Case Folder 的 `結構配置圖/` 目錄
2. **在 ETABS 中預建 Grid System** — Phase 1 讀取此 Grid 作為 ground truth
3. **開啟 ETABS** — 確保程式執行中
4. **在 Claude Code 中 `cd` 到 Case Folder**

### Phase 1: 建立主結構

```
/bts-structure

# Claude 會詢問：
# 1. PPT 路徑
# 2. page-floors 對應（如 "1=B3F, 3=1F~2F, 4=3F~14F"）
#
# 流程：
# - read_grid → grid_data.json
# - pptx_to_elements --scan-floors（自動偵測 page-floor 對應）
# - 啟動 2 READER Agents（平行讀取不同樓層範圍）
# - 每個 READER: pptx_to_elements → affine_calibrate → beam_validate → plot_elements
# - Team Lead: elements_merge → config_build → model_config.json
# - CONFIG-BUILDER: run_all.py --steps 1,2,3,4,5,6
```

### Phase 1 QC（可選）

```
/bts-qc1 model_config.json
```

### Phase 2: 建立小梁+版

```
/bts-sb

# 流程：
# - pptx_to_elements --phase phase2（提取小梁）
# - 啟動 2 SB-READER Agents（平行校正+驗證不同樓層）
# - 每個 SB-READER: affine_calibrate（複用 Phase 1 grid_anchors）→ sb_validate → plot_elements
# - Team Lead: elements_merge → sb_patch_build → config_merge → slab_generator → final_config.json
# - CONFIG-BUILDER: run_all.py --steps 2,7,8
```

### Phase 3: 設定屬性

```
/bts-props

# 直接執行 run_all.py --steps 9,10,11
# 設定 modifiers, rigid zones, end releases, 載重, diaphragms
```

### 後續（可選）: RC 設計迭代

```
/rc-iteration
```

---

## 14. 重要工程規則

### +1 Floor Rule（最常出錯的規則）

```
柱/牆: ETABS 樓層 = 平面圖樓層 + 1
梁/版: ETABS 樓層 = 平面圖樓層（不加 1）

範例：平面圖 5F 的柱 → ETABS 6F 的柱
範例：平面圖 5F 的梁 → ETABS 5F 的梁
```

### 斷面命名 D/B Swap

```
梁: B{Width}X{Depth} → T3=Depth, T2=Width
    B55X80 → SetRectangle(Name, Mat, T3=0.80, T2=0.55)

柱: C{Xwidth}X{Ydepth} → T3=Ydepth, T2=Xwidth
    C100X120 → SetRectangle(Name, Mat, T3=1.20, T2=1.00)
```

### 基礎層規則

- 基礎層 = BASE 上一層（如 B3F）
- BASE 沒有任何物件
- 基礎層的版用 ShellThick (FS)，modifiers 用 RAFT_MODIFIERS
- 基礎層有 UX/UY restraints + Kv 彈簧
- FWB（基礎壁梁）自動加 Kw 側向彈簧
- **永遠不建 SDL load pattern**

### Grid 規則

- Grid 名稱、方向、順序從 ETABS 預建模型讀取（`grid_data.json`）
- PPT 只用於驗證，不假設 X=數字、Y=字母
- Grid 座標精度要求 1cm (0.01m)

---

## 15. 常見問題與除錯

### ETABS 連線失敗

```python
# 確認 ETABS 執行中，且有打開模型
from find_etabs import find_etabs
etabs, filename = find_etabs(run=False, backup=False)
# 如果失敗，檢查 etabs_api 版本: pip show etabs_api
```

### COM RPC 中斷

批次建立大量 frame sections 時可能崩潰。解法：分批執行或增加延遲。

### 構件遺漏

- 檢查 PPT 顏色匹配：`pptx_to_elements` 使用 ±15 RGB tolerance
- 確認圖例表格格式正確（2-column table）
- 查看 `beam_report_*.json` 中的 unmatched shapes 數量

### 高程不匹配

```bash
python -m golden_scripts.tools.diagnose_elev --config model_config.json
```

### 查看 API 方法

```
1. 搜尋 api_docs/CSI API ETABS v1.hhc
2. 讀取對應 .htm 檔
3. 或查 api_docs_index/task_index.md（任務導向查詢）
```

---

## 附錄 A：架構演進（Legacy → Phased）

| 面向        | Legacy `/bts` / `/bts-gs`         | Phased `/bts-structure` + `/bts-sb` + `/bts-props` |
| ----------- | --------------------------------- | -------------------------------------------------- |
| 構件提取    | AI 視覺識別 / Bluebeam annotation | **確定性** `pptx_to_elements.py` 提取              |
| 座標校正    | AI 手動對應                       | `affine_calibrate` + `beam_validate` 自動化        |
| Config 生成 | CONFIG-BUILDER Agent 手動整合     | `config_build.py` 確定性合併                       |
| Token 消耗  | ~130K+ (一次完成)                 | ~40-50K per phase (分三次)                         |
| 板生成      | AI 手動切割                       | `slab_generator` 圖論演算法自動生成                |
| 錯誤率      | 較高（AI 猜測）                   | 趨近零（確定性工具 + AI 驗證）                     |
| 可追溯性    | 低（對話中生成）                  | 高（每步有中間 JSON + 報告）                       |

**重點**: 新版將 AI 的角色從「生成座標」轉為「驗證座標」，所有座標提取都由確定性工具完成。

---

## 附錄 B：結構術語對照

| 術語     | English                    | 說明                         |
| -------- | -------------------------- | ---------------------------- |
| 上構     | Superstructure             | 地上結構 (2F~RF)             |
| 下構     | Substructure               | 地下結構 (B\*F, 1F)          |
| 屋突     | Rooftop                    | R1F~PRF                      |
| 共構     | Shared Substructure        | 多棟共用地下室               |
| 分棟     | Building Split             | 靠 Diaphragm Name 辨識       |
| 連續壁   | Diaphragm Wall             | 是牆不是梁，用現有 Grid 座標 |
| 小梁     | Small Beam (SB)            | 次梁                         |
| 壁梁     | Wall Beam (WB)             | 沿牆的梁                     |
| 基礎梁   | Foundation Beam (FB)       | 基礎層的大梁                 |
| 基礎壁梁 | Foundation Wall Beam (FWB) | 基礎層壁梁，自動加 Kw        |
