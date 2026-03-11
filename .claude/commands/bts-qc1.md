---
description: "BTS QC Phase 1 — 檢核 /bts-structure 完成後的 ETABS 模型。使用方式：/bts-qc1 <config路徑>"
argument-hint: "<model_config.json 路徑>"
---

# BTS-QC1 — Phase 1 品質檢核

執行 `golden_scripts/qc/qc_phase1.py`，比對 ETABS 模型現況與 `model_config.json`。

## 前提
- ETABS 已開啟且模型已載入
- Phase 1 (`/bts-structure`) 已完成（steps 1-6）

## 執行

```bash
cd golden_scripts
python -m golden_scripts.qc.qc_phase1 --config "$ARGUMENTS"
```

## 檢查項目

| # | 項目 | 說明 |
|---|------|------|
| 1 | Units | TON/M (12) |
| 2 | Stories | 數量、名稱、高度逐層比對 |
| 3 | Grids | X/Y 軸數量、標籤、座標比對 |
| 4 | Columns | config 展開 floors 後總數 vs ETABS |
| 5 | Walls | config 展開 floors 後總數 vs ETABS |
| 6 | Beams | B/WB/FB/FWB 總數比對（不含 SB） |
| 7 | Sections | config 所列斷面皆已在 ETABS 定義 |
| 8 | No SB/Slabs | Phase 1 後不應有小梁或版 |

## 結果判讀

- **全 PASS**：Phase 1 模型正確，可進入 `/bts-sb`
- **有 FAIL**：檢視差異，修正 config 或重跑對應 step
