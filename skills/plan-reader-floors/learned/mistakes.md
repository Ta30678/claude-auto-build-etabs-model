# Common Mistakes
| 日期 | 案名 | 錯誤 | 根因 | 修正 | 更新SKILL? |
|------|------|------|------|------|-----------|
| 2026-03-10 | A21 | 所有柱 floors 包含 R1F，+1 rule 導致柱多建到 R2F | AI 混淆 floors=「站立起始層」vs「頂端層」，將 +1 後的頂端層寫進 floors | 柱 floors 最後一層 = 構件站立起始層（如 14F），Golden Scripts +1 rule 自動延伸到 R1F | Yes — agent definitions + SKILL.md |
