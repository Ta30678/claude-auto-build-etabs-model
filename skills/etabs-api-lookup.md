# Skill: ETABS API Lookup

## Purpose
This skill describes how to efficiently look up ETABS v22 COM API method details from the local documentation. Use this whenever you need to verify a method signature, parameter types, return values, or find which interface contains a specific method.

## When to Use This Skill
- Before writing any API call you are not 100% certain about
- When you encounter an unknown method name or parameter
- When a script fails with a COM error (wrong parameters, wrong types)
- When a user asks about a specific API capability
- When you need to find the correct interface for a task

## Documentation Layout

```
V22 AGENTIC MODEL/
├── api_docs/
│   ├── CSI API ETABS v1.hhc     # Master TOC - maps method names to HTML files
│   └── html/                     # ~1693 individual .htm files (one per method/type)
├── api_docs_index/
│   ├── categories.json           # Interface-to-category mapping (JSON)
│   ├── full_toc.json             # Complete TOC extracted from .hhc (JSON)
│   ├── group_a_analysis.md       # Detailed docs: Analysis, Results, Load Cases, Design Codes
│   ├── group_b_analysis.md       # Detailed docs: Modeling, Properties, DB Tables, Structures
│   └── task_index.md             # Task-oriented "How do I...?" guide
└── CLAUDE.md                     # Project instructions with inline API reference
```

## Lookup Process

### Step 1: Identify What You Need

Determine the category of the operation:
- **Modeling** (create objects, set properties) -> group_b_analysis.md
- **Analysis** (run analysis, get results) -> group_a_analysis.md
- **Design** (concrete/steel design) -> group_a_analysis.md (design codes section)
- **Database Tables** (bulk data) -> group_b_analysis.md (section 8)
- **Task-based** ("how do I add a beam?") -> task_index.md

### Step 2: Search the Pre-Built Index Files

**For a quick task lookup:**
```
Read api_docs_index/task_index.md
```
This maps common tasks (e.g., "add a beam", "run analysis", "get story drifts") to exact API calls with Python examples.

**For interface-level details:**
```
Read api_docs_index/group_a_analysis.md   # Analysis/Results/LoadCases/Design
Read api_docs_index/group_b_analysis.md   # Modeling/Properties/Stories/DBTables
```
These contain method signatures, parameter descriptions, and Python usage notes.

**For finding which interface a method belongs to:**
```
Read api_docs_index/categories.json
```
This maps category names to interface names.

### Step 3: Search the Raw Documentation (When Index Files Are Not Enough)

If the pre-built index files do not have enough detail (e.g., you need exact parameter meanings for an obscure method), search the raw HTML docs:

**Search the Table of Contents (.hhc file):**
```
Grep for "MethodName" in api_docs/CSI API ETABS v1.hhc
```
The .hhc file contains entries like:
```html
<LI> <OBJECT type="text/sitemap">
  <param name="Name" value="MethodName Method">
  <param name="Local" value="html/GUID-HERE.htm">
</OBJECT>
```
Extract the `Local` value to find the HTML file path.

**Read the HTML method documentation:**
```
Read api_docs/html/GUID-HERE.htm
```
The HTML files contain the definitive method documentation with:
- Full C# signature (with `<span>` tags for syntax highlighting)
- Parameter descriptions with types
- Return value description
- Remarks and notes
- Cross-references to related methods

**Search across all HTML files for a keyword:**
```
Grep for "keyword" in api_docs/html/*.htm
```

### Step 4: Parse the HTML File

The HTML files use C# syntax with HTML markup. Key patterns:

**Method signature** (look for the method name in `<span>` tags):
```html
<span class="keyword">public</span> <span class="identifier">int</span>
<span class="identifier">MethodName</span>(
  <span class="keyword">ref</span> <span class="identifier">string</span> Name,
  ...
)
```

**Parameter table** (look for `<dt>` or `<td>` tags):
```html
<dt>Name</dt>
<dd>Description of the Name parameter</dd>
```

**Key translation rules for Python COM:**
- `ref string Name` -> pass `Name = ''` (empty string, filled by method)
- `ref int Value` -> pass `Value = 0` (integer, filled by method)
- `ref double[] Array` -> pass `Array = []` (empty list, filled by method)
- `ref bool[] Flags` -> pass `Flags = []` (empty list, filled by method)
- `string Name = "Default"` -> optional parameter with default "Default"
- `eItemType ItemType = eItemType.Objects` -> optional, default 0 (Objects)

**Return values:**
- Almost all methods return `int` (0 = success, nonzero = failure)
- A few return `string`, `bool`, `double`, or enum values (check signature)

## Quick Decision Tree

```
Need to do something with ETABS API?
  |
  +-- Know exactly what task?
  |     -> Read task_index.md
  |
  +-- Know the interface but not the method?
  |     -> Read group_a_analysis.md or group_b_analysis.md
  |
  +-- Know the method name but not the parameters?
  |     -> Grep for method in .hhc file -> read the HTML
  |
  +-- Not sure which interface?
  |     -> Check categories.json or CLAUDE.md access path table
  |
  +-- Need design code item numbers?
        -> Grep for the code name in group_a_analysis.md
        -> Or read the specific HTML file for item descriptions
```

## ETABS 操作方式（必須遵守）

### 連線方式：使用 etabs_api 套件（已安裝）
```python
from find_etabs import find_etabs
etabs, filename = find_etabs(run=False, backup=False)
```

### 禁止直接使用 comtypes
不要用 `comtypes.client.GetActiveObject()` 直接操作 SapModel。
一律透過 `etabs_api` 封裝操作，它已處理好型別轉換問題。

### 常用操作對照
```python
# 讀取資料表（回傳 DataFrame，無型別問題）
df = etabs.database.read("表名", to_dataframe=True)

# 寫入資料表
etabs.database.write(table_key="表名", data=df)

# 地震力載重
ex, exn, exp, ey, eyn, eyp = etabs.load_patterns.get_seismic_load_patterns()

# 構件操作
etabs.frame_obj.方法名()
etabs.area.方法名()

# 樓層操作
etabs.story.方法名()

# 載重組合
etabs.load_combinations.方法名()

# 設計
etabs.design.方法名()

# 結果
etabs.results.方法名()

# 模型管理
etabs.lock_and_unlock_model()

# 刷新畫面
etabs.SapModel.View.RefreshView(0, False)
```

### 如果 etabs_api 沒有對應函數
可以透過 `etabs.SapModel` 存取底層 API：
```python
etabs.SapModel.Analyze.RunAnalysis()
etabs.SapModel.Results.StoryDrifts()
```
但 ByRef 參數不要手動傳值，讓 comtypes 自動處理。

---

## Important Reminders

1. **NEVER guess parameter order or types.** Always verify against documentation.
2. **優先使用 etabs_api 封裝。** 只有在 etabs_api 沒有對應函數時，才透過 `etabs.SapModel` 存取底層 API。
3. **C# `ref` parameters become output parameters in Python COM.** Initialize them before calling.
4. **Array parameters**: In C#, arrays are `ref string[]` or `ref double[]`. In Python, pass empty lists `[]`.
5. **Enumeration values**: Use integer codes, not enum names. Check the mapping in CLAUDE.md or the HTML docs.
6. **Versioned methods**: Many methods have `_1`, `_2` suffixes (newer versions). Prefer the latest version (e.g., `GetStories_2` over `GetStories`).
7. **Deprecated methods**: Some methods are marked DEPRECATED in the docs. Use the recommended replacement.
8. **The HTML files are the ultimate source of truth.** When in doubt, read the HTML.

## Cross-References
- Project instructions and inline API reference: `CLAUDE.md`
- Task-oriented lookup guide: `api_docs_index/task_index.md`
- Detailed interface docs: `api_docs_index/group_a_analysis.md`, `api_docs_index/group_b_analysis.md`
