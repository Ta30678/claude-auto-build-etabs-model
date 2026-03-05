"""
Parse the ETABS API .hhc TOC file and build a structured interface→method index.
Outputs two JSON files: group_a.json (interfaces 1-59) and group_b.json (interfaces 60-118).
Also outputs a full_toc.json with the complete structure.
"""
import re
import json
import os

HHC_PATH = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\api_docs\CSI API ETABS v1.hhc"
OUTPUT_DIR = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\api_docs_index"
HTML_DIR = r"C:\Users\User\Desktop\V22 AGENTIC MODEL\api_docs\html"

with open(HHC_PATH, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Extract all name→local pairs
pairs = re.findall(
    r'<param name="Name" value="([^"]+)">\s*<param name="Local" value="([^"]+)">',
    content
)

# Build hierarchical structure: Interface → Properties/Methods → individual items
interfaces = {}
current_interface = None
current_section = None  # "Properties" or "Methods"

for name, local in pairs:
    name = name.strip()

    if name.endswith(' Interface'):
        interface_name = name.replace(' Interface', '')
        current_interface = interface_name
        interfaces[interface_name] = {
            'page': local,
            'properties': [],
            'methods': []
        }
        current_section = None
    elif current_interface:
        if 'Properties' in name and not ('Method' in name):
            current_section = 'properties'
        elif 'Methods' in name and not ('Property' in name):
            current_section = 'methods'
        elif name.endswith(' Method ') or name.endswith(' Method'):
            method_name = name.replace(' Method ', '').replace(' Method', '').strip()
            if current_interface in interfaces:
                interfaces[current_interface]['methods'].append({
                    'name': method_name,
                    'page': local
                })
        elif name.endswith(' Property ') or name.endswith(' Property'):
            prop_name = name.replace(' Property ', '').replace(' Property', '').strip()
            if current_interface in interfaces:
                interfaces[current_interface]['properties'].append({
                    'name': prop_name,
                    'page': local
                })

# Sort interfaces alphabetically
sorted_interfaces = sorted(interfaces.items())

# Split into two groups
midpoint = len(sorted_interfaces) // 2
group_a = dict(sorted_interfaces[:midpoint])
group_b = dict(sorted_interfaces[midpoint:])

# Save full TOC
with open(os.path.join(OUTPUT_DIR, 'full_toc.json'), 'w', encoding='utf-8') as f:
    json.dump(interfaces, f, indent=2, ensure_ascii=False)

# Save group A
with open(os.path.join(OUTPUT_DIR, 'group_a.json'), 'w', encoding='utf-8') as f:
    json.dump(group_a, f, indent=2, ensure_ascii=False)

# Save group B
with open(os.path.join(OUTPUT_DIR, 'group_b.json'), 'w', encoding='utf-8') as f:
    json.dump(group_b, f, indent=2, ensure_ascii=False)

# Print summary
print(f"Total interfaces: {len(interfaces)}")
print(f"Group A: {len(group_a)} interfaces ({list(group_a.keys())[0]} ... {list(group_a.keys())[-1]})")
print(f"Group B: {len(group_b)} interfaces ({list(group_b.keys())[0]} ... {list(group_b.keys())[-1]})")
print()

# Print per-group stats
for group_name, group in [("A", group_a), ("B", group_b)]:
    total_methods = sum(len(v['methods']) for v in group.values())
    total_props = sum(len(v['properties']) for v in group.values())
    print(f"Group {group_name}: {total_methods} methods, {total_props} properties")
    for iname, idata in group.items():
        m = len(idata['methods'])
        p = len(idata['properties'])
        if m + p > 0:
            print(f"  {iname}: {m} methods, {p} properties")

# Also create a quick-reference: interface name → description based on common categories
categories = {
    "Analysis & Results": ["cAnalysisResults", "cAnalysisResultsSetup", "cAnalyze"],
    "Load Cases": ["cCaseDirectHistoryLinear", "cCaseDirectHistoryNonlinear", "cCaseHyperStatic",
                   "cCaseModalEigen", "cCaseModalHistoryLinear", "cCaseModalHistoryNonlinear",
                   "cCaseModalRitz", "cCaseResponseSpectrum", "cCaseStaticLinear",
                   "cCaseStaticNonlinear", "cCaseStaticNonlinearStaged"],
    "Load Definitions": ["cLoadCases", "cLoadPatterns", "cCombo"],
    "Design - Concrete": ["cDesignConcrete", "cDesignConcreteSlab", "cDesignShearWall",
                          "cDConcreteShellDesignRequest"],
    "Design - Steel": ["cDesignSteel"],
    "Design - Composite": ["cDesignCompositeBeam", "cDesignCompositeColumn"],
    "Design - Results/Forces": ["cDesignForces", "cDesignResults"],
    "Modeling - Frame": ["cFrameObj", "cEditFrame", "cLineElm"],
    "Modeling - Area": ["cAreaObj", "cAreaElm"],
    "Modeling - Point": ["cPointObj", "cPointElm"],
    "Modeling - Link/Tendon": ["cLinkObj", "cTendonObj"],
    "Properties - Frame": ["cPropFrame", "cPropFrameSDShape"],
    "Properties - Area": ["cPropArea", "cPropAreaSpring"],
    "Properties - Material": ["cPropMaterial", "cPropRebar", "cPropTendon"],
    "Properties - Spring": ["cPropPointSpring", "cPropLineSpring", "cPropAreaSpring"],
    "Properties - Link": ["cPropLink"],
    "Structure Definition": ["cStory", "cTower", "cGridSys", "cDiaphragm",
                            "cPierLabel", "cSpandrelLabel", "cConstraint"],
    "Model Operations": ["cSapModel", "cFile", "cView", "cSelect", "cOptions"],
    "Database Tables": ["cDatabaseTables"],
    "Groups & Selection": ["cGroup", "cSelect"],
    "Functions": ["cFunction", "cFunctionRS"],
    "Seismic": ["cAutoSeismic"],
    "Plugin System": ["cPluginCallback", "cPluginContract"],
    "Utilities": ["cHelper", "cOAPI", "cEditGeneral", "cGenDispl", "cDetailing", "cDesignStrip"],
}

with open(os.path.join(OUTPUT_DIR, 'categories.json'), 'w', encoding='utf-8') as f:
    json.dump(categories, f, indent=2, ensure_ascii=False)

print("\nCategory mapping saved to categories.json")
print("Done!")
