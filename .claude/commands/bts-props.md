---
description: "BTS Phase 3 — 執行 Properties + Loads + Diaphragms（gs_09~gs_11）。需先完成 /bts-structure + /bts-sb。使用方式：/bts-props"
argument-hint: "[config 路徑，預設使用 merged_config.json]"
---

# BTS-PROPS — Phase 3: Properties + Loads + Diaphragms

你現在是 **BTS-PROPS 的 Team Lead**，直接執行 gs_09~gs_11（無 Agent Team）。

**前置條件**：必須先完成 `/bts-structure`（Phase 1）+ `/bts-sb`（Phase 2），ETABS 模型已有完整結構構件。

**Phase 3 範圍**：
- **gs_09**: Frame modifiers, rigid zones (0.75), end releases
- **gs_10**: Load patterns (DL/LL/EQ), slab loads, exterior wall loads, seismic, spectrum, foundation springs (Kv/Kw)
- **gs_11**: Diaphragm assignment at slab corner points

**無需 Agent Team** — 這三步全為確定性操作，所有參數來自 config 或 constants.py 預設值。

---

## 鐵則（ABSOLUTE RULES）

1. **不建立 SDL**——所有附加靜載使用 DL。
2. **Kw 自動偵測**——所有 FWB 斷面的梁自動設定 Kw line spring。
3. **Diaphragm 只指定在版角點**——不指定到所有樓層 joint。
4. **restraint_floor 自動偵測**——從 stories 偵測第一個 B*F，不再手動詢問。

---

## 執行流程

### Step 1: 確認前置條件 + 收集參數

1. **找到 config 檔**（按優先順序）：
   - 用戶指定的路徑：`$ARGUMENTS`
   - `final_config.json`（Phase 2 slab_generator 輸出）
   - `merged_config.json`（Phase 2 輸出）
   - `model_config.json`（如果 Phase 2 直接修改了 model_config）
2. **確認 ETABS 模型已開啟** — 有 Grid、Story、柱、牆、梁、小梁、版
3. **自動偵測 restraint_floor**：
   - 從 config `stories` 偵測第一個 B*F（不含 BASE）
   - 顯示結果供用戶確認：`Auto-detected restraint_floor: B3F`
4. **收集基礎參數**（用 AskUserQuestion 一次詢問）：

   | # | 參數 | 說明 | 必要性 |
   |---|------|------|--------|
   | 1 | 基礎 Kv | 垂直彈簧係數 (ton/m³) | **必問** |
   | 2 | 邊梁 Kw | 側邊彈簧係數 (ton/m³) | **必問** |
   | 3 | 反應譜檔案 | SPECTRUM.TXT 路徑 | 可選（無則跳過） |

5. **外牆線載（自動）**：
   - 直接從 config 的 `building_outline` 讀取 outline
   - 使用 constants.py 預設值（t=0.15m, γ=2.4, opening=0.6）
   - 若 `building_outline` 不存在，gs_10 會自動跳過並顯示警告

6. **將參數寫入 config**：
   ```python
   config.setdefault("loads", {})
   config["loads"].setdefault("zone_defaults", DEFAULT_LOADS)
   config["loads"]["spectrum_file"] = SPECTRUM_PATH  # if provided
   config.setdefault("foundation", {})
   config["foundation"]["kv"] = KV_VALUE
   config["foundation"]["kw"] = KW_VALUE
   config["foundation"]["restraint_floor"] = auto_detected_floor
   ```

### Step 2: 顯示載重預設值 + 確認

顯示 `constants.py` 的 `DEFAULT_LOADS` 預設值表：

```
載重預設值（ton/m²）：
┌──────────────────┬──────┬──────┐
│ Zone             │  DL  │  LL  │
├──────────────────┼──────┼──────┤
│ superstructure   │ 0.45 │ 0.20 │
│ rooftop          │ 0.45 │ 0.30 │
│ substructure     │ 0.15 │ 0.50 │
│ 1F_indoor        │ 0.30 │ 0.50 │
│ 1F_outdoor       │ 0.60 │ 1.00 │
│ FS               │ 0.63 │ 0.00 │
└──────────────────┴──────┴──────┘
```

用 AskUserQuestion 確認：
- 是否使用預設值？
- 如需自訂，詢問哪些 zone 的 DL/LL 要修改

如果用戶要自訂，更新 config 的 `loads.zone_defaults` 後再繼續。

### Step 3: 確認基礎參數

從 config 中讀取並顯示 Step 1 寫入的參數：
- `foundation.kv` = {KV_VALUE}
- `foundation.kw` = {KW_VALUE}
- `foundation.restraint_floor` = {auto-detected}
- `loads.spectrum_file` = {SPECTRUM_PATH}（如有）
- `exterior_wall`: auto（從 `building_outline` 讀取，t=0.15, γ=2.4, opening=0.6）

確認無誤後繼續。

### Step 4: 執行 Golden Scripts

```bash
cd golden_scripts
python run_all.py --config "{CONFIG_PATH}" --steps 9,10,11
```

執行內容：
| Step | 功能 | Config 依賴 |
|------|------|------------|
| 09 | Frame modifiers + rigid zone (0.75) + end releases | 無（全 hardcoded） |
| 10 | Load patterns + slab loads + exterior wall loads + seismic + spectrum + Kv/Kw | loads, foundation |
| 11 | Diaphragm（每層一組 D_{story}，指定到版角點） | 無（自動偵測版） |

### Step 5: 驗證

在 ETABS 中確認：
1. **Frame Modifiers**：
   - Beams: `[1, 1, 1, 0.0001, 0.7, 0.7, 0.8, 0.8]`
   - Columns: `[1, 1, 1, 0.0001, 0.7, 0.7, 0.95, 0.95]`
2. **Rigid Zones**: factor=0.75 on all frames
3. **End Releases**: M2+M3 at discontinuous beam ends
4. **Load Patterns**: DL(SW=1), LL, EQXP/EQXN/EQYP/EQYN（係數由用戶在 ETABS 手動設定）
5. **Slab Loads**: DL/LL assigned per zone
6. **Exterior Wall Loads**: DL line loads on edge beams（自動從 `building_outline` 判定）
7. **Foundation**:
   - UX/UY restraints at `restraint_floor` (auto-detected)
   - Kv springs on foundation points
   - Kw springs on all FWB beams
8. **Diaphragms**: D_{story} per story, assigned to slab/FS corner points

可選：執行 `pytest -v` 跑完整驗證。

### Step 6: 報告結果

向用戶報告：
- Phase 3 完成
- Modifiers / Rigid Zone / End Releases 數量
- Load patterns 定義
- Slab load 分配數量
- Exterior wall load 分配數量（如啟用）
- Foundation spring 數量
- Diaphragm 數量
- **提醒**：Phase 1+2+3 建模完成，可進入分析設計（`run_all.py --steps 12`）

---

## Golden Scripts 執行步驟（Phase 3 only）

| Step | 腳本 | 功能 | Config 欄位 |
|------|------|------|------------|
| 09 | gs_09_properties.py | Modifiers + RZ + Releases | 無 |
| 10 | gs_10_loads.py | DL/LL/EQ + Spectrum + Ext Wall + Kv/Kw | loads.*, foundation.* |
| 11 | gs_11_diaphragms.py | Diaphragm per story | 無 |

---

用戶的附加指示：$ARGUMENTS
