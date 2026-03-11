# Common Mistakes
| 日期 | 案名 | 錯誤 | 根因 | 修正 | 更新SKILL? |
|------|------|------|------|------|-----------|
| 2026-03-10 | A21 | model_config.json 柱 floors 含 R1F，柱多建一層到 R2F | AI 混淆 floors=頂端層 vs 站立起始層 | floors 最後一層 = 構件站立起始層，Golden Scripts +1 rule 自動延伸 | Yes |
