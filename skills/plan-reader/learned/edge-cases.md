# Edge Cases
| 日期 | 案名 | 情境 | 處理決策 | 更新SKILL? |
|------|------|------|----------|-----------|
| 2026-03-10 | A21 | 14F/B3F 建築無 RF story（14F 直接到 R1F），柱到 R1F 標高 | 柱 floors 最後寫 14F（next_story=R1F），不寫 R1F | Yes |
| 2026-03-11 | General | 下構樓層（B*F + 1F）的 building_outline 必須一致（基地範圍），1F 不可用上構範圍作為 building_outline | 新增鐵則到 phase1-reader, bts-structure | Yes |
