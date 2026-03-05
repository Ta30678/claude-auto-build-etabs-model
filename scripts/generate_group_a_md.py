import json, re, os

base = r"C:\Users\User\Desktop\V22 AGENTIC MODEL"

with open(os.path.join(base, 'api_docs_index', 'group_a_extracted.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

with open(os.path.join(base, 'api_docs_index', 'group_a.json'), 'r', encoding='utf-8') as f:
    index = json.load(f)

def clean_param_desc(desc):
    desc = re.sub(r'AddLanguageSpecificTextSet\([^)]+\);', '', desc)
    desc = re.sub(r'^Type:\s*(System|ETABSv1)?(String|Int32|Double|Boolean|eItemTypeElm|eItemType)?\s*', '', desc)
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc

def format_sig(sig):
    if not sig:
        return ''
    sig = sig.replace('ref ', '')
    sig = re.sub(r'\s+', ' ', sig).strip()
    return sig

def get_ptype(sig, pname):
    pattern = rf'(\w+(?:\[\])?)\s+{re.escape(pname)}'
    m = re.search(pattern, sig or '')
    return m.group(1) if m else ''

lines = []

# HEADER
lines.append('# ETABS API Reference - Group A (Analysis, Results, Load Cases, Design Codes)')
lines.append('')
lines.append('> Auto-generated from ETABS v22 COM API documentation.')
lines.append('> Access path notation: `SapModel.X.Method()` where X is the sub-object.')
lines.append('')
lines.append('---')
lines.append('')

# TABLE OF CONTENTS
lines.append('## Table of Contents')
lines.append('')
lines.append('### Core Analysis Interfaces')
lines.append('1. [cAnalysisResults](#1-canalysisresults) - SapModel.Results')
lines.append('2. [cAnalysisResultsSetup](#2-canalysisresultssetup) - SapModel.Results.Setup')
lines.append('3. [cAnalyze](#3-canalyze) - SapModel.Analyze')
lines.append('4. [cAreaElm](#4-careaelm) - SapModel.AreaElm')
lines.append('5. [cAreaObj](#5-careaobj) - SapModel.AreaObj')
lines.append('6. [cAutoSeismic](#6-cautoseismic) - SapModel.AutoSeismic')
lines.append('7. [cCombo](#7-ccombo) - SapModel.RespCombo')
lines.append('8. [cConstraint](#8-cconstraint) - SapModel.ConstraintDef')
lines.append('')
lines.append('### Load Case Interfaces')
lines.append('9. [cCaseModalEigen](#9-ccasemodalEigen) - SapModel.LoadCases.ModalEigen')
lines.append('10. [cCaseModalRitz](#10-ccasemodalritz) - SapModel.LoadCases.ModalRitz')
lines.append('11. [cCaseStaticLinear](#11-ccasestaticlinear) - SapModel.LoadCases.StaticLinear')
lines.append('12. [cCaseStaticNonlinear](#12-ccasestaticnonlinear) - SapModel.LoadCases.StaticNonlinear')
lines.append('13. [cCaseStaticNonlinearStaged](#13-ccasestaticnonlinearstaged)')
lines.append('14. [cCaseResponseSpectrum](#14-ccaseresponsespectrum)')
lines.append('15. [Other Load Case Interfaces](#15-other-load-case-interfaces)')
lines.append('')
lines.append('### Design Code Interfaces')
lines.append('16. [Concrete Design Codes (cDCo*)](#16-concrete-design-codes)')
lines.append('17. [Composite Column Design (cDCompCol*)](#17-composite-column-design-codes)')
lines.append('18. [Concrete Slab Design (cDConcSlab*)](#18-concrete-slab-design-codes)')
lines.append('19. [Steel Design Codes (cDSt*)](#19-steel-design-codes)')
lines.append('')
lines.append('---')
lines.append('')


def write_interface(iface_name, num, access, description, detail_level='full'):
    lines.append('## %s. %s' % (num, iface_name))
    lines.append('**Access**: `%s`' % access)
    lines.append('')
    lines.append('**Description**: %s' % description)
    lines.append('')

    iface = data.get(iface_name, {})
    props = iface.get('properties', [])
    if props:
        lines.append('### Properties')
        for p in props:
            lines.append('- **%s**: %s' % (p['name'], p.get('description', '')))
        lines.append('')

    methods = iface.get('methods', [])
    if not methods:
        return

    lines.append('### Methods')
    lines.append('')

    for m in methods:
        desc = m.get('description', 'No description')
        sig = m.get('signature', '')
        ret = m.get('return', '')
        remarks = m.get('remarks', '')

        lines.append('#### %s' % m['name'])
        lines.append('- **Purpose**: %s' % desc)
        lines.append('- **Signature**: `%s`' % format_sig(sig))

        params = m.get('params', [])
        if detail_level == 'full' and params:
            if len(params) <= 10:
                lines.append('- **Parameters**:')
                for pname, pdesc in params:
                    pt = get_ptype(sig, pname)
                    cl = clean_param_desc(pdesc)
                    if len(cl) > 200:
                        cl = cl[:200] + '...'
                    lines.append('  - `%s` (%s): %s' % (pname, pt, cl))
            else:
                lines.append('- **Parameters**: %d params (see HTML for full details)' % len(params))
                for pname, pdesc in params[:4]:
                    pt = get_ptype(sig, pname)
                    cl = clean_param_desc(pdesc)
                    if len(cl) > 150:
                        cl = cl[:150] + '...'
                    lines.append('  - `%s` (%s): %s' % (pname, pt, cl))
                lines.append('  - ... and %d more output arrays' % (len(params) - 4))
        elif detail_level == 'compact' and params:
            lines.append('- **Parameters**: %d params' % len(params))

        if ret:
            lines.append('- **Returns**: %s' % ret)
        if remarks and len(remarks) > 15:
            lines.append('- **Remarks**: %s' % remarks[:300])
        lines.append('- **HTML**: `%s`' % m['html'])
        lines.append('')

    lines.append('---')
    lines.append('')


# Write all core interfaces
write_interface('cAnalysisResults', '1', 'SapModel.Results',
    'Primary interface for extracting analysis results. Provides methods to retrieve forces, displacements, reactions, modal data, story drifts, and more. All result methods follow a common pattern: pass Name + ItemTypeElm, get back arrays of results.')

write_interface('cAnalysisResultsSetup', '2', 'SapModel.Results.Setup',
    'Configures which load cases/combos are selected for output, and sets result output options (envelopes, step-by-step, etc.). Must be configured before calling result extraction methods.')

write_interface('cAnalyze', '3', 'SapModel.Analyze',
    'Controls analysis execution, active DOF, solver options, and run case flags. Core workflow: set DOF -> set run flags -> save file -> run analysis.')

write_interface('cAreaElm', '4', 'SapModel.AreaElm',
    'Read-only access to area element (analysis model) data. Area elements are created from area objects during analysis. Use for element-level queries after analysis.')

write_interface('cAreaObj', '5', 'SapModel.AreaObj',
    'Primary interface for creating and manipulating area objects (slabs, walls, decks, openings). 64 methods covering geometry creation, property assignment, load application, pier/spandrel labels, diaphragm assignment, and queries.',
    detail_level='compact')

write_interface('cAutoSeismic', '6', 'SapModel.AutoSeismic',
    'Get and set automatic seismic load code parameters. Supports ASCE 7-16 and IBC 2006 seismic codes.')

write_interface('cCombo', '7', 'SapModel.RespCombo',
    'Create and manage load combinations. Add combos, add cases/combos to combos, get case lists, manage combo types, add design defaults.')

write_interface('cConstraint', '8', 'SapModel.ConstraintDef',
    'Joint constraints interface, primarily for diaphragm constraints in ETABS.')

# Load Case interfaces
write_interface('cCaseModalEigen', '9', 'SapModel.LoadCases.ModalEigen',
    'Eigen modal analysis case. Configure number of modes, frequency shift, convergence tolerance, mass source, and initial stiffness from another case.')

write_interface('cCaseModalRitz', '10', 'SapModel.LoadCases.ModalRitz',
    'Ritz modal analysis case. Configure starting load vectors, number of modes, and initial stiffness case.')

write_interface('cCaseStaticLinear', '11', 'SapModel.LoadCases.StaticLinear',
    'Linear static load case. Configure load patterns with scale factors and initial conditions.')

write_interface('cCaseStaticNonlinear', '12', 'SapModel.LoadCases.StaticNonlinear',
    'Nonlinear static (pushover) analysis. Configure geometric nonlinearity, hinge unloading, load application (force/displacement control), solution control parameters, target force parameters, mass source, and modal case for P-Delta.')

write_interface('cCaseStaticNonlinearStaged', '13', 'SapModel.LoadCases.StaticNonlinearStaged',
    'Staged construction nonlinear static case. Configure stages (add/remove objects, load application), geometric nonlinearity, material nonlinearity, hinge unloading, solution control, and time-dependent properties.')

write_interface('cCaseResponseSpectrum', '14', 'SapModel.LoadCases.ResponseSpectrum',
    'Response spectrum analysis case. Configure damping type/values, directional combination rule, eccentricity override, modal combination method (CQC/SRSS/etc.), applied spectrum functions with direction and scale factors.')

# Other load cases
lines.append('## 15. Other Load Case Interfaces')
lines.append('')
lines.append('These interfaces follow similar patterns to the main load case interfaces.')
lines.append('')

other_cases = [
    ('cCaseDirectHistoryLinear', 'SapModel.LoadCases.DirHistLinear', 'Direct integration linear time history'),
    ('cCaseDirectHistoryNonlinear', 'SapModel.LoadCases.DirHistNonlinear', 'Direct integration nonlinear time history'),
    ('cCaseModalHistoryLinear', 'SapModel.LoadCases.ModHistLinear', 'Modal linear time history'),
    ('cCaseModalHistoryNonlinear', 'SapModel.LoadCases.ModHistNonlinear', 'Modal nonlinear time history'),
    ('cCaseHyperStatic', 'SapModel.LoadCases.HyperStatic', 'Hyperstatic (secondary) load case'),
]

for iname, access, desc in other_cases:
    iface = data.get(iname, {})
    mnames = [m['name'] for m in iface.get('methods', [])]
    lines.append('### %s' % iname)
    lines.append('- **Access**: `%s`' % access)
    lines.append('- **Description**: %s' % desc)
    lines.append('- **Methods** (%d): %s' % (len(mnames), ', '.join(mnames)))
    lines.append('')

lines.append('---')
lines.append('')

# DESIGN CODES - Section 16
lines.append('## 16. Concrete Design Codes (cDCo*)')
lines.append('')
lines.append('**Access**: `SapModel.DesignConcrete.{CodeName}`')
lines.append('')
lines.append('### Common Pattern')
lines.append('All concrete design code interfaces expose 4 methods:')
lines.append('')
lines.append('| Method | Signature | Purpose |')
lines.append('|--------|-----------|---------|')
lines.append('| GetOverwrite | `int GetOverwrite(string Name, int Item, ref double Value)` | Get design overwrite for a frame object |')
lines.append('| SetOverwrite | `int SetOverwrite(string Name, int Item, double Value)` | Set design overwrite for a frame object |')
lines.append('| GetPreference | `int GetPreference(int Item, ref double Value)` | Get design preference value |')
lines.append('| SetPreference | `int SetPreference(int Item, double Value)` | Set design preference value |')
lines.append('')
lines.append('**Notes**:')
lines.append('- `Item` is an integer index specific to each code. Consult the HTML docs for item meanings.')
lines.append('- `Value=0` for overwrites typically means "use program-determined value".')
lines.append('- `Name` refers to a frame object name (for overwrites).')
lines.append('')

# Example from ACI318_19
if 'cDCoACI318_19' in data:
    lines.append('### Example: cDCoACI318_19')
    lines.append('')
    iface = data['cDCoACI318_19']
    for m in iface['methods']:
        desc = m.get('description', '')
        sig = m.get('signature', '')
        ret = m.get('return', '')
        remarks = m.get('remarks', '')
        params = m.get('params', [])

        lines.append('#### %s' % m['name'])
        lines.append('- **Purpose**: %s' % desc)
        lines.append('- **Signature**: `%s`' % format_sig(sig))
        if params:
            lines.append('- **Parameters**:')
            for pname, pdesc in params:
                pt = get_ptype(sig, pname)
                cl = clean_param_desc(pdesc)
                if len(cl) > 300:
                    cl = cl[:300] + '...'
                lines.append('  - `%s` (%s): %s' % (pname, pt, cl))
        if ret:
            lines.append('- **Returns**: %s' % ret)
        if remarks and len(remarks) > 15:
            lines.append('- **Remarks**: %s' % remarks[:400])
        lines.append('')

lines.append('### All Available Concrete Design Codes')
lines.append('')
concrete_codes = sorted([k for k in index.keys() if k.startswith('cDCo')])
for code in concrete_codes:
    methods = [m['name'] for m in index[code]['methods']]
    if methods:
        lines.append('- **%s**: %d methods (%s)' % (code, len(methods), ', '.join(methods)))
    else:
        lines.append('- **%s**: no methods' % code)
lines.append('')
lines.append('---')
lines.append('')

# Section 17 - Composite Column
lines.append('## 17. Composite Column Design Codes (cDCompCol*)')
lines.append('')
lines.append('**Access**: `SapModel.DesignCompositeColumn.{CodeName}`')
lines.append('')
lines.append('Same 4-method pattern as concrete codes.')
lines.append('')
comp_codes = sorted([k for k in index.keys() if k.startswith('cDCompCol')])
for code in comp_codes:
    methods = [m['name'] for m in index[code]['methods']]
    lines.append('- **%s**: %s' % (code, ', '.join(methods)))
lines.append('')
lines.append('---')
lines.append('')

# Section 18 - Slab
lines.append('## 18. Concrete Slab Design Codes (cDConcSlab*)')
lines.append('')
lines.append('**Access**: `SapModel.DesignConcreteSlab.{CodeName}`')
lines.append('')
lines.append('Slab design interfaces typically only expose GetPreference (no overwrite methods).')
lines.append('')
slab_codes = sorted([k for k in index.keys() if k.startswith('cDConcSlab')])
for code in slab_codes:
    methods = [m['name'] for m in index[code]['methods']]
    if methods:
        lines.append('- **%s**: %s' % (code, ', '.join(methods)))
    else:
        lines.append('- **%s**: no methods' % code)
lines.append('')

shell_codes = sorted([k for k in index.keys() if 'ConcShell' in k or 'ConcreteShell' in k])
if shell_codes:
    lines.append('### Related: Concrete Shell Design')
    for code in shell_codes:
        methods = [m['name'] for m in index[code]['methods']]
        if methods:
            lines.append('- **%s**: %s' % (code, ', '.join(methods)))
        else:
            lines.append('- **%s**: no methods exposed' % code)
    lines.append('')

lines.append('---')
lines.append('')

# Section 19 - Steel
lines.append('## 19. Steel Design Codes (cDSt*)')
lines.append('')
lines.append('**Access**: `SapModel.DesignSteel.{CodeName}`')
lines.append('')
lines.append('Same 4-method pattern: GetOverwrite, SetOverwrite, GetPreference, SetPreference.')
lines.append('')
lines.append('### Available Codes')
lines.append('')
steel_codes = sorted([k for k in index.keys() if k.startswith('cDSt')])
for code in steel_codes:
    methods = [m['name'] for m in index[code]['methods']]
    lines.append('- **%s**: %s' % (code, ', '.join(methods)))
lines.append('')
lines.append('---')
lines.append('')

# QUICK REFERENCE
lines.append('## Quick Reference: Common Workflows')
lines.append('')
lines.append('### Running Analysis and Getting Results')
lines.append('```python')
lines.append('# 1. Save model first (required before analysis)')
lines.append('ret = SapModel.File.Save(filepath)')
lines.append('')
lines.append('# 2. Set active DOF if needed')
lines.append('ret = SapModel.Analyze.SetActiveDOF(DOF)  # bool array [UX,UY,UZ,RX,RY,RZ]')
lines.append('')
lines.append('# 3. Set which cases to run')
lines.append('ret = SapModel.Analyze.SetRunCaseFlag("", True, True)  # run all cases')
lines.append('')
lines.append('# 4. Run analysis')
lines.append('ret = SapModel.Analyze.RunAnalysis()')
lines.append('')
lines.append('# 5. Configure output')
lines.append('ret = SapModel.Results.Setup.DeselectAllCasesAndCombosForOutput()')
lines.append('ret = SapModel.Results.Setup.SetCaseSelectedForOutput("DEAD")')
lines.append('')
lines.append('# 6. Get results')
lines.append('ret = SapModel.Results.FrameForce(name, eItemTypeElm.ObjectElm,')
lines.append('    NumberResults, Obj, ObjSta, Elm, ElmSta, LoadCase, StepType, StepNum,')
lines.append('    P, V2, V3, T, M2, M3)')
lines.append('```')
lines.append('')
lines.append('### Creating and Modifying Area Objects')
lines.append('```python')
lines.append('# Add by coordinates')
lines.append('ret = SapModel.AreaObj.AddByCoord(NumPoints, x, y, z, Name, PropName)')
lines.append('')
lines.append('# Add by point names')
lines.append('ret = SapModel.AreaObj.AddByPoint(NumPoints, PointNames, Name, PropName)')
lines.append('')
lines.append('# Assign loads')
lines.append('ret = SapModel.AreaObj.SetLoadUniform(Name, LoadPat, Value, Dir)')
lines.append('')
lines.append('# Assign diaphragm')
lines.append('ret = SapModel.AreaObj.SetDiaphragm(Name, DiaphragmName)')
lines.append('')
lines.append('# Set pier/spandrel labels')
lines.append('ret = SapModel.AreaObj.SetPier(Name, PierName)')
lines.append('ret = SapModel.AreaObj.SetSpandrel(Name, SpandrelName)')
lines.append('```')
lines.append('')
lines.append('### Response Spectrum Case Setup')
lines.append('```python')
lines.append('ret = SapModel.LoadCases.ResponseSpectrum.SetCase("RSX")')
lines.append('ret = SapModel.LoadCases.ResponseSpectrum.SetLoads("RSX", ...)')
lines.append('ret = SapModel.LoadCases.ResponseSpectrum.SetModalCase("RSX", "Modal")')
lines.append('ret = SapModel.LoadCases.ResponseSpectrum.SetEccentricity("RSX", 0.05)')
lines.append('```')
lines.append('')
lines.append('### Load Combinations')
lines.append('```python')
lines.append('ret = SapModel.RespCombo.Add("COMB1", ComboType)')
lines.append('ret = SapModel.RespCombo.SetCaseList("COMB1", CaseType, CaseName, SF)')
lines.append('ret = SapModel.RespCombo.AddDesignDefaultCombos(DesignAct)')
lines.append('```')
lines.append('')

# ENUMERATIONS
lines.append('---')
lines.append('')
lines.append('## Appendix: Key Enumerations')
lines.append('')
lines.append('### eItemTypeElm (result methods)')
lines.append('| Value | Name | Description |')
lines.append('|-------|------|-------------|')
lines.append('| 0 | ObjectElm | Results for elements from the named object |')
lines.append('| 1 | Element | Results for the specific named element |')
lines.append('| 2 | GroupElm | Results for all elements in the named group |')
lines.append('| 3 | SelectionElm | Results for all selected elements (Name ignored) |')
lines.append('')
lines.append('### eItemType (object assignment methods)')
lines.append('| Value | Name | Description |')
lines.append('|-------|------|-------------|')
lines.append('| 0 | Objects | Apply to the named object |')
lines.append('| 1 | Group | Apply to all objects in the named group |')
lines.append('| 2 | SelectedObjects | Apply to all selected objects (Name ignored) |')
lines.append('')

# INTERFACE SUMMARY TABLE
lines.append('---')
lines.append('')
lines.append('## Appendix: Complete Interface Summary')
lines.append('')
lines.append('| Interface | Access Path | Methods | Description |')
lines.append('|-----------|-------------|---------|-------------|')

summary_data = [
    ('cAnalysisResults', 'SapModel.Results', 37, 'Analysis results extraction'),
    ('cAnalysisResultsSetup', 'SapModel.Results.Setup', 21, 'Result output configuration'),
    ('cAnalyze', 'SapModel.Analyze', 21, 'Analysis execution and settings'),
    ('cAreaElm', 'SapModel.AreaElm', 13, 'Area element queries (read-only)'),
    ('cAreaObj', 'SapModel.AreaObj', 64, 'Area object manipulation'),
    ('cAutoSeismic', 'SapModel.AutoSeismic', 6, 'Seismic code parameters'),
    ('cCaseDirectHistoryLinear', 'SapModel.LoadCases.DirHistLinear', 1, 'Direct linear time history'),
    ('cCaseDirectHistoryNonlinear', 'SapModel.LoadCases.DirHistNonlinear', 1, 'Direct NL time history'),
    ('cCaseHyperStatic', 'SapModel.LoadCases.HyperStatic', 3, 'Hyperstatic load case'),
    ('cCaseModalEigen', 'SapModel.LoadCases.ModalEigen', 9, 'Eigen modal analysis'),
    ('cCaseModalHistoryLinear', 'SapModel.LoadCases.ModHistLinear', 3, 'Modal linear time history'),
    ('cCaseModalHistoryNonlinear', 'SapModel.LoadCases.ModHistNonlinear', 1, 'Modal NL time history'),
    ('cCaseModalRitz', 'SapModel.LoadCases.ModalRitz', 7, 'Ritz modal analysis'),
    ('cCaseResponseSpectrum', 'SapModel.LoadCases.ResponseSpectrum', 16, 'Response spectrum'),
    ('cCaseStaticLinear', 'SapModel.LoadCases.StaticLinear', 5, 'Linear static case'),
    ('cCaseStaticNonlinear', 'SapModel.LoadCases.StaticNonlinear', 21, 'Pushover analysis'),
    ('cCaseStaticNonlinearStaged', 'SapModel.LoadCases.StaticNonlinearStaged', 29, 'Staged construction'),
    ('cCombo', 'SapModel.RespCombo', 11, 'Load combinations'),
    ('cConstraint', 'SapModel.ConstraintDef', 4, 'Joint constraints'),
]

for name, access, count, desc in summary_data:
    lines.append('| %s | `%s` | %d | %s |' % (name, access, count, desc))

lines.append('')
lines.append('### Design Code Interfaces (all follow Get/SetOverwrite + Get/SetPreference pattern)')
lines.append('')

all_design = sorted([k for k in index.keys() if k.startswith('cDCo') or k.startswith('cDCompCol') or k.startswith('cDConcSlab') or k.startswith('cDConcShell') or k.startswith('cDConcreteShell') or k.startswith('cDSt')])
lines.append('Total design code interfaces: %d' % len(all_design))
lines.append('')
lines.append('| Category | Count | Interfaces |')
lines.append('|----------|-------|------------|')

conc = [k for k in all_design if k.startswith('cDCo')]
comp = [k for k in all_design if k.startswith('cDCompCol')]
slab = [k for k in all_design if k.startswith('cDConcSlab')]
shell = [k for k in all_design if 'ConcShell' in k or 'ConcreteShell' in k]
steel = [k for k in all_design if k.startswith('cDSt')]

lines.append('| Concrete (cDCo*) | %d | %s |' % (len(conc), ', '.join(conc)))
lines.append('| Composite Column (cDCompCol*) | %d | %s |' % (len(comp), ', '.join(comp)))
lines.append('| Concrete Slab (cDConcSlab*) | %d | %s |' % (len(slab), ', '.join(slab)))
lines.append('| Concrete Shell | %d | %s |' % (len(shell), ', '.join(shell)))
lines.append('| Steel (cDSt*) | %d | %s |' % (len(steel), ', '.join(steel)))
lines.append('')

outpath = os.path.join(base, 'api_docs_index', 'group_a_analysis.md')
with open(outpath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print('SUCCESS: Written %d lines to group_a_analysis.md' % len(lines))
