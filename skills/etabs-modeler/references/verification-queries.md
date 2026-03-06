# Verification Queries

Python code snippets for verifying ETABS model correctness. Run via `mcp__etabs__run_python` or Bash.

## 1. Check Units

```python
units = SapModel.GetPresentUnits()
assert units == 12, f"Units={units}, expected 12 (TON/M)"
print(f"Units OK: {units} (TON/M)")
```

## 2. Element Count per Story

```python
# Frame count
ret = SapModel.FrameObj.GetAllFrames(
    0, [], [], [], [], [], [], [], [], [], [], [],
    [], [], [], [], [], [], [], [])
num_frames = ret[0]
stories = ret[3]
from collections import Counter
frame_counts = Counter(stories)
print(f"Total frames: {num_frames}")
for story, count in sorted(frame_counts.items()):
    print(f"  {story}: {count}")

# Area count via database tables
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Area Assignments - Summary", [], "All", 0, [], 0, [])
print(f"Total areas: {ret[5]}")
```

## 3. Section D/B Verification

```python
import re
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Frame Section Properties", [], "All", 0, [], 0, [])
fields = list(ret[4])
data = list(ret[6])
nf = len(fields)
nr = ret[5]
name_i = fields.index("Name")
t3_i = fields.index("t3")
t2_i = fields.index("t2")

errors = []
for i in range(nr):
    row = data[i*nf:(i+1)*nf]
    name = row[name_i]
    t3 = float(row[t3_i]) if row[t3_i] else 0
    t2 = float(row[t2_i]) if row[t2_i] else 0
    m = re.match(r'^(B|SB|WB|FB|FSB|FWB|C)(\d+)X(\d+)C?\d*$', name)
    if m:
        exp_w = int(m.group(2)) / 100.0
        exp_d = int(m.group(3)) / 100.0
        if abs(t3 - exp_d) > 0.001 or abs(t2 - exp_w) > 0.001:
            errors.append(f"{name}: T3={t3} T2={t2} expected T3={exp_d} T2={exp_w}")

if errors:
    print(f"D/B ERRORS ({len(errors)}):")
    for e in errors:
        print(f"  {e}")
else:
    print(f"All {nr} sections D/B correct")
```

## 4. Modifier Verification

### Frame Modifiers
```python
# Check beam modifiers (sample)
ret = SapModel.FrameObj.GetAllFrames(0,[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[])
names, props = ret[1], ret[2]
beam_ok, beam_fail = 0, 0
col_ok, col_fail = 0, 0
for i in range(min(100, len(names))):
    mod_ret = SapModel.FrameObj.GetModifiers(names[i], [])
    mods = list(mod_ret[1])
    is_col = props[i].startswith('C') and 'X' in props[i]
    expected_torsion = 0.0001
    expected_mass = 0.95 if is_col else 0.8
    if abs(mods[3] - expected_torsion) < 0.001 and abs(mods[6] - expected_mass) < 0.01:
        if is_col: col_ok += 1
        else: beam_ok += 1
    else:
        if is_col: col_fail += 1
        else: beam_fail += 1

print(f"Beams: {beam_ok} OK, {beam_fail} FAIL")
print(f"Columns: {col_ok} OK, {col_fail} FAIL")
```

### Area Modifiers
```python
# Check via section property modifiers
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Area Section Properties", [], "All", 0, [], 0, [])
fields = list(ret[4])
data = list(ret[6])
nf = len(fields)
nr = ret[5]
name_i = fields.index("Name")
for i in range(nr):
    row = data[i*nf:(i+1)*nf]
    sec_name = row[name_i]
    mod_ret = SapModel.PropArea.GetModifiers(sec_name, [])
    if mod_ret[0] == 0:
        mods = list(mod_ret[1])
        is_raft = sec_name.startswith("FS")
        if is_raft:
            ok = abs(mods[0]-0.4)<0.01 and abs(mods[3]-0.7)<0.01
        else:
            ok = abs(mods[0]-0.4)<0.01 and abs(mods[3]-1.0)<0.01
        status = "OK" if ok else "FAIL"
        print(f"  {sec_name}: f11={mods[0]}, m11={mods[3]} [{status}]")
```

## 5. Rebar Verification

### Column Rebar
```python
import re
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Frame Section Properties", [], "All", 0, [], 0, [])
fields = list(ret[4])
data = list(ret[6])
nf = len(fields)
nr = ret[5]
name_i = fields.index("Name")

for i in range(nr):
    row = data[i*nf:(i+1)*nf]
    sec = row[name_i]
    if not (sec.startswith('C') and 'X' in sec):
        continue
    try:
        rb = SapModel.PropFrame.GetRebarColumn(sec,'','',0,0,0,0,0,0,'','',0,0,0,False)
        cover = rb[5]
        ok = abs(cover - 0.07) < 0.001
        print(f"  {sec}: cover={cover}m, ToBeDesigned={rb[13]} [{'OK' if ok else 'FAIL'}]")
    except:
        print(f"  {sec}: no rebar configured")
```

### Beam Rebar
```python
for i in range(nr):
    row = data[i*nf:(i+1)*nf]
    sec = row[name_i]
    m = re.match(r'^(B|SB|WB|FB|FSB|FWB)', sec)
    if not m:
        continue
    prefix = m.group(1)
    is_fb = prefix in ('FB','FSB','FWB')
    try:
        rb = SapModel.PropFrame.GetRebarBeam(sec,'','',0,0,0,0,0,0,False)
        ct, cb = rb[3], rb[4]
        if is_fb:
            ok = abs(ct-0.11)<0.01 and abs(cb-0.15)<0.01
        else:
            ok = abs(ct-0.09)<0.01 and abs(cb-0.09)<0.01
        print(f"  {sec}: top={ct}m, bot={cb}m [{'OK' if ok else 'FAIL'}]")
    except:
        pass
```

## 6. Rigid Zone Verification

```python
ret = SapModel.FrameObj.GetAllFrames(0,[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[])
names = ret[1]
ok, fail = 0, 0
for name in names[:50]:
    rz = SapModel.FrameObj.GetEndLengthOffset(name, False, 0, 0, 0)
    rz_factor = rz[4]
    if abs(rz_factor - 0.75) < 0.01:
        ok += 1
    else:
        fail += 1
print(f"Rigid zone: {ok} OK, {fail} FAIL (checked {ok+fail})")
```

## 7. End Release Verification

```python
ret = SapModel.FrameObj.GetAllFrames(0,[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[])
names, props = ret[1], ret[2]
released = 0
for name in names:
    prop = props[names.index(name)] if name in names else ""
    if prop.startswith('C'):
        continue  # skip columns
    try:
        rel = SapModel.FrameObj.GetReleases(name, [False]*6, [False]*6, [0]*6, [0]*6)
        ii = list(rel[1])
        jj = list(rel[2])
        if any(ii[4:6]) or any(jj[4:6]):
            released += 1
    except:
        pass
print(f"Beams with releases: {released}")
```

## 8. Diaphragm Verification

```python
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Diaphragm Definitions", [], "All", 0, [], 0, [])
if ret[0] == 0:
    fields = list(ret[4])
    data = list(ret[6])
    nf = len(fields)
    for i in range(ret[5]):
        row = data[i*nf:(i+1)*nf]
        print(f"  Diaphragm: {row}")
```

## 9. Spring Verification

```python
# Point springs
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Joint Assignments - Springs", [], "All", 0, [], 0, [])
if ret[0] == 0:
    print(f"Point springs: {ret[5]} assignments")

# Line springs
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Frame Assignments - Line Springs", [], "All", 0, [], 0, [])
if ret[0] == 0:
    print(f"Line springs: {ret[5]} assignments")
```

## 10. Load Verification

```python
# Load patterns
ret = SapModel.DatabaseTables.GetTableForDisplayArray(
    "Load Pattern Definitions", [], "All", 0, [], 0, [])
fields = list(ret[4])
data = list(ret[6])
nf = len(fields)
print("Load Patterns:")
for i in range(ret[5]):
    row = data[i*nf:(i+1)*nf]
    print(f"  {row}")

# Check if loads are assigned (DL and LL)
for lp in ["DL", "LL"]:
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        "Area Loads - Uniform", [], "All", 0, [], 0, [])
    if ret[0] == 0:
        print(f"Area uniform loads: {ret[5]} assignments")
    break
```

## Full Verification Checklist

Run all checks above and compare against:

```
[ ] Units = TON/M (12)
[ ] All sections D/B correct (T3=depth, T2=width)
[ ] Batch sections cover +-20cm/5cm/all grades
[ ] Column/wall floors = plan +1
[ ] Every floor has slabs (no missing)
[ ] 樓板按大小梁切割（非直接 Grid 交點建板）
[ ] FS 基礎版額外 2x2 切割
[ ] 小梁兩端都有接合其他梁/柱
[ ] Slab/wall ShellType = Membrane (2)
[ ] Raft ShellType = ShellThick (1)
[ ] Slab/wall modifier: f11=f22=f12=0.4
[ ] Raft modifier: f=0.4, m=0.7
[ ] Beam modifier: T=0.0001, I22/I33=0.7, Mass/Wt=0.8
[ ] Column modifier: T=0.0001, I22/I33=0.7, Mass/Wt=0.95
[ ] Regular beam cover: 9cm top/bottom
[ ] Foundation beam cover: 11cm top, 15cm bottom
[ ] Column cover: 7cm
[ ] Column bar distribution matches W:D ratio
[ ] Column ToBeDesigned = True
[ ] Rigid zone = 0.75 for all frames (SetEndLengthOffset)
[ ] Discontinuous beam ends have M2+M3 release
[ ] Base restraints = UX,UY at FS slab level (NOT at BASE)
[ ] Raft points have Kv springs
[ ] FS 基礎版有設 Diaphragm
[ ] FS 基礎版有 DL=0.63 載重
[ ] Edge beams have Kw line springs
[ ] DL and LL loads assigned to slabs (by zone defaults)
[ ] 外牆線載重方向為 GRAVITY（正值，非負值）
[ ] Exterior wall loads only where beam exists above
[ ] 載重工況無 SDL（除非使用者要求）
[ ] Load patterns: DL/LL/EQXP/EQXN/EQYP/EQYN
[ ] EQ params: ECC=0.05, K=1, C=user value, Top=PRF, Bot=1F
[ ] Response spectrum FROM FILE (SPECTRUM.TXT) imported
[ ] 0SPECX/0SPECXY modified (NOT new RSX/RSY created)
[ ] Load combo EQV scale factor set
[ ] Diaphragm walls use C280
[ ] Diaphragm only at slab corner points
[ ] Model saved successfully
```
