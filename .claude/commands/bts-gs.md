---
description: "BTS Golden Scripts - 啟動 3 人 Agent Team + Golden Scripts 建模流程。比舊 /BTS 快 70%、錯誤率趨近零。使用方式：/bts-gs [樓層/圖片說明]"
argument-hint: "[樓層說明或附加指示]"
---

# BTS-GS - Build Team Structure with Golden Scripts

你現在是 **BTS-GS 團隊的 Team Lead**，負責協調 3 位 Agent + Golden Scripts 自動建模。

**與舊版 /BTS 的差異**：
- 3 個 Agent（少了 MODELER-A/B）→ 改用 CONFIG-BUILDER + Golden Scripts
- 確定性建模規則（D/B、modifier、rebar）已「編譯」進 Python，不需 AI 推理
- 自動化驗證（pytest）取代人工檢查
- Token 消耗 ~130K（舊版 ~500K），速度快 3 倍

---

## 鐵則（ABSOLUTE RULES）

1. **小梁位置禁止猜測！** SB-READER 必須從 annotation.json 讀取並驗證座標。
2. **結構配置從圖面讀取，禁止從舊模型複製。**
3. **建物範圍需交叉比對結構配置圖和建築平面圖。**
4. **小梁等分座標必須退回重做。**

---

## 團隊編制

| Agent | 代號 | Agent 定義檔 | 職責 |
|-------|------|-------------|------|
| Agent 1 | **READER** | `.claude/agents/reader.md` | 解讀結構配置圖：柱、大梁、壁梁、剪力牆、Grid |
| Agent 2 | **SB-READER** | `.claude/agents/sb-reader.md` | 小梁座標驗證與格式化輸出 |
| Agent 3 | **CONFIG-BUILDER** | `.claude/agents/config-builder.md` | 將 READER/SB-READER 輸出 → model_config.json |

**不再需要**：MODELER-A、MODELER-B（由 Golden Scripts 取代）

---

## 執行流程

### Phase 0: 確認輸入（與舊版相同）

**必要參數清單（MUST ASK）**：

| # | 參數 | 說明 | 預設值 |
|---|------|------|--------|
| 1 | 結構配置圖 | 路徑 `{Case Folder}/結構配置圖/` | 自動掃描 |
| 2 | 樓層高度表 | 各樓層高度 (m)，含基礎層 | **無，必問** |
| 3 | 強度分配表 | 混凝土等級 by 樓層區段 | **無，必問** |
| 4 | 基礎 Kv | 彈簧係數 | 可選 |
| 5 | 邊梁 Kw | 側邊彈簧 | 可選 |
| 6 | 反應譜檔案 | SPECTRUM.TXT | 可選 |
| 7 | Base Shear C | 地震力係數 | 可選 |
| 8 | EQV Scale Factor | 放大係數 | 可選 |
| 9 | 板厚 | 各區 (cm) | **無，必問** |
| 10 | 基礎樓層 | BASE 上一層 | **無，必問** |
| 11 | EDB 存檔路徑 | 模型檔路徑 | **無，必問** |

> **LL values are zone-based defaults (see CLAUDE.md). No user input needed.**

### Phase 0.5: Bluebeam 標註提取（必要步驟）

在啟動 Agent 前，Team Lead 提取 Bluebeam 標註：

```python
# 掃描 Case Folder 中的 PDF 檔案
from golden_scripts.tools.pdf_annot_extractor import has_annotations, extract_pdf

# 1. 找到結構配置 PDF
pdf_files = glob("{Case Folder}/結構配置圖/*.pdf") + glob("{Case Folder}/*.pdf")

# 2. 檢查是否有 Bluebeam 標註
for pdf in pdf_files:
    if has_annotations(pdf):
        # 3. 提取標註 → JSON
        result = extract_pdf(pdf, pages=[目標頁碼])
        # 4. 存為 JSON 供 READER/SB-READER 使用
        with open("{Case Folder}/結構配置圖/annotations.json", "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        break
```

或使用 CLI：
```bash
python -m golden_scripts.tools.pdf_annot_extractor \
  --input "{Case Folder}/結構配置圖/結構尺寸配置.pdf" \
  --pages 5 \
  --output "{Case Folder}/結構配置圖/annotations.json"
```

**裁切頁面為多張 PNG**（全圖 + 局部放大，方便 Agent 讀取細節）：

```python
# 5. 裁切頁面為多張 PNG（全圖 + 局部放大）
from golden_scripts.tools.pdf_annot_extractor import crop_page_images

image_paths = crop_page_images(
    pdf_path=str(pdf_path),
    page_num=目標頁碼,
    output_dir=f"{Case Folder}/結構配置圖/",
    annotations_json=result,  # 用標註密度智能分區
    dpi=200
)
```

或使用 CLI：
```bash
python -m golden_scripts.tools.pdf_annot_extractor \
  --input "{Case Folder}/結構配置圖/結構尺寸配置.pdf" \
  --pages 5 \
  --output "{Case Folder}/結構配置圖/annotations.json" \
  --crop --crop-dir "{Case Folder}/結構配置圖/"
```

**標註 JSON 已提取**：啟動 Agent 時在 prompt 中附帶 JSON 路徑，Agent 使用精確座標進行讀圖和驗證。

### Phase 1: 建立 Team + 創建任務

```
TeamCreate(team_name="bts-gs-team", description="BTS-GS 結構建模團隊")
```

| Task | 主題 | Owner | blockedBy |
|------|------|-------|-----------|
| T1 | READER 讀圖 | READER | (無) |
| T2 | SB-READER 小梁定位 | SB-READER | (無) |
| T3 | CONFIG-BUILDER 生成 config | CONFIG-BUILDER | T1, T2 |
| T4 | 執行 Golden Scripts | (Team Lead) | T3 |
| T5 | 執行 pytest 驗證 | (Team Lead) | T4 |

### Phase 2: 啟動 3 個 Agent

**同時**啟動 READER、SB-READER、CONFIG-BUILDER，全部 `run_in_background=true`。

```
Agent(
  subagent_type="reader",
  team_name="bts-gs-team",
  name="READER",
  description="讀取結構配置圖",
  prompt="你被指派為 BTS-GS Team 的 READER。請按照你的 agent 定義執行工作。

結構配置圖路徑：{Case Folder}/結構配置圖/
用戶說明：$ARGUMENTS
樓層資訊：[樓層高度表]
標註 JSON：[ANNOTATION_JSON_PATH 或 '無']

請先讀取 skills/plan-reader/SKILL.md 了解完整流程。
如果有標註 JSON，優先使用標註資料的精確座標（見 agent 定義中的「標註優先工作流」）。
為每個區段分別產出結構摘要。
如有 R2F 以上屋突樓層，請辨識核心區 Grid 範圍，輸出 core_grid_area。

完成後：
1. 用 SendMessage 將摘要**直接發給 CONFIG-BUILDER**
2. 用 TaskUpdate 標記 T1 完成
3. 進入等待模式，回應 CONFIG-BUILDER 的後續問題",
  run_in_background=true
)

Agent(
  subagent_type="sb-reader",
  team_name="bts-gs-team",
  name="SB-READER",
  description="小梁座標驗證",
  prompt="你被指派為 BTS-GS Team 的 SB-READER。請按照你的 agent 定義執行工作。

結構配置圖路徑：{Case Folder}/結構配置圖/
用戶說明：$ARGUMENTS
標註 JSON：{Case Folder}/結構配置圖/annotations.json

讀取 annotation.json，驗證小梁座標的連接性和合理性。
為每個區段分別驗證小梁座標。

完成後：
1. 用 SendMessage 將小梁座標表**直接發給 CONFIG-BUILDER**
2. 用 TaskUpdate 標記 T2 完成
3. 進入等待模式",
  run_in_background=true
)

Agent(
  subagent_type="config-builder",
  team_name="bts-gs-team",
  name="CONFIG-BUILDER",
  description="生成 model_config.json",
  prompt="你被指派為 BTS-GS Team 的 CONFIG-BUILDER。請按照你的 agent 定義執行工作。

先讀取 golden_scripts/config_schema.json 了解輸出格式。

等待 READER 和 SB-READER 的 SendMessage，然後整合為 model_config.json。
屋突複製：如有 R2F 以上樓層，根據 READER 的 core_grid_area 將 R1F 核心區構件複製到更高樓層。

用戶提供的參數：
- 樓層高度表：[樓層高度表]
- 強度分配表：[強度分配]
- 板厚：[板厚]
- 基礎樓層：[基礎樓層]
- 基礎 Kv：[KV_VALUE]
- 邊梁 Kw：[KW_VALUE]
- EDB 存檔路徑：[SAVE_PATH]
- Base Shear C：[C_VALUE]
- 反應譜檔案：[SPECTRUM_PATH]

完成後：
1. 將 model_config.json 寫入 {Case Folder}/
2. 用 SendMessage 告知 Team Lead config 路徑
3. 用 TaskUpdate 標記 T3 完成",
  run_in_background=true
)
```

### Phase 3: 監控 → 等待 CONFIG-BUILDER 完成

Team Lead 進入監控模式，等 T3 完成。

### Phase 4: 執行 Golden Scripts（Team Lead 直接操作）

CONFIG-BUILDER 完成後，Team Lead 自行執行：

```bash
cd golden_scripts
python run_all.py --config "{Case Folder}/model_config.json" --steps modeling
```

檢查輸出：
- 每個 step 應該印出 "complete"
- 如有 ERROR，修正 model_config.json 後重跑失敗的 step：
  `python run_all.py --config "..." --steps 5`

### Phase 5: 執行 pytest 驗證

```bash
cd tests
pytest -v --config "{Case Folder}/model_config.json"
```

預期結果：
```
test_units.py::test_units_are_ton_m PASSED
test_sections.py::test_section_db_correct PASSED
test_modifiers.py::test_frame_modifiers PASSED
test_modifiers.py::test_area_modifiers PASSED
test_rebar.py::test_column_rebar PASSED
test_rebar.py::test_beam_rebar PASSED
test_rigid_zones.py::test_rigid_zone_factor PASSED
test_diaphragms.py::test_diaphragms_exist PASSED
test_loads.py::test_load_patterns_exist PASSED
test_element_counts.py::test_frames_exist PASSED
...
```

如有 FAIL：
1. 讀取 pytest 報告找出具體錯誤
2. 修正 config 或重跑指定 step
3. 再跑 pytest 直到全 PASS

### Phase 6: 報告結果

向用戶報告：
- 建模完成時間
- pytest 結果摘要（PASS/FAIL）
- 構件數量（柱/梁/牆/板）
- 如有任何需要手動調整的項目

### Phase 7: Shutdown

```
SendMessage(type="shutdown_request", recipient="READER")
SendMessage(type="shutdown_request", recipient="SB-READER")
SendMessage(type="shutdown_request", recipient="CONFIG-BUILDER")
```

---

## Golden Scripts 執行什麼

| Step | 腳本 | 功能 | 典型錯誤消除 |
|------|------|------|-------------|
| 01 | modeling/gs_01_init.py | 材料 C280~C490 + SD420/SD490 | - |
| 02 | modeling/gs_02_sections.py | 斷面展開 + D/B + rebar + area modifier | D/B swap |
| 03 | modeling/gs_03_grid_stories.py | Grid + Stories | - |
| 04 | modeling/gs_04_columns.py | 柱 (+1 rule 內建) | +1 遺忘 |
| 05 | modeling/gs_05_walls.py | 牆 (+1 rule + diaphragm=C280) | - |
| 06 | modeling/gs_06_beams.py | 大梁/壁梁/基礎梁 | - |
| 07 | modeling/gs_07_small_beams.py | 小梁 | - |
| 08 | modeling/gs_08_slabs.py | 板（含 FS ShellThick） | Shell Type 錯 |
| 09 | modeling/gs_09_properties.py | Modifier + RZ=0.75 + 釋放 | Modifier 值錯 |
| 10 | modeling/gs_10_loads.py | DL/LL/EQ + 反應譜 + 基礎 | 載重方向 |
| 11 | modeling/gs_11_diaphragms.py | Diaphragm (slab corner only) | 漏 FS diaphragm |

---

## 重要規則

所有舊版 /BTS 的規則仍然有效，特別是：
1. 小梁座標禁猜測
2. D/B 不可搞反（Golden Scripts 已處理，但 config 中的 section 命名必須正確）
3. 基礎樓層要建柱（+1 rule 建在基礎樓層→上一層之間）
4. 連續壁用 C280
5. 不使用 SDL
6. 每案獨立，禁從記憶推斷

---

用戶的附加指示：$ARGUMENTS
