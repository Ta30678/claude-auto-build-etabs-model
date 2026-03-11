# Common Mistakes
| 日期 | 案名 | 錯誤 | 根因 | 修正 | 更新SKILL? |
|------|------|------|------|------|-----------|
| 2026-03-10 | A21 | 所有柱 floors 包含 R1F，+1 rule 導致柱多建到 R2F | READER 不清楚 floors=「站立起始層」而非「頂端層」，將柱的頂端層也寫進 floors | 柱 floors 最後一層應為 14F（+1 自動到 R1F），不可寫 R1F | Yes — agent definitions |
| 2026-03-11 | General | 1F 梁位與 B1F 以下不同，下構平面範圍不一致 | READER 讀 1F 頁面時獨立判定建物範圍，未遵循基地範圍 | 下構所有樓層（B*F + 1F）強制共用同一 building_outline | Yes — phase1-reader, bts-structure |
