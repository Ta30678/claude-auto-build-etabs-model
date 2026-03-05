"""
ETABS MCP Server
================
Exposes ETABS COM API operations as MCP tools for Claude Code.
Run with: python etabs_mcp_server.py
"""

import json
import sys
import traceback
from contextlib import contextmanager
from mcp.server.fastmcp import FastMCP

# ── MCP Server ──────────────────────────────────────────────────────────────
mcp = FastMCP("etabs", log_level="WARNING")

# ── ETABS Connection (lazy singleton) ──────────────────────────────────────
_etabs_obj = None
_sap_model = None


def _connect():
    """Connect to running ETABS instance (cached)."""
    global _etabs_obj, _sap_model
    if _sap_model is not None:
        try:
            _sap_model.GetPresentUnits()  # health check
            return _sap_model
        except Exception:
            _etabs_obj = None
            _sap_model = None

    import comtypes.client
    try:
        _etabs_obj = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
    except OSError:
        raise RuntimeError("No running ETABS instance found. Please open ETABS first.")
    _sap_model = _etabs_obj.SapModel
    return _sap_model


UNITS_MAP = {
    1: "lb_in", 2: "lb_ft", 3: "kip_in", 4: "kip_ft",
    5: "kN_mm", 6: "kN_m", 7: "kgf_mm", 8: "kgf_m",
    9: "N_mm", 10: "N_m", 11: "Ton_mm", 12: "Ton_m",
    13: "kN_cm", 14: "kgf_cm", 15: "N_cm", 16: "Ton_cm",
}

UNIT_CODES = {v: k for k, v in UNITS_MAP.items()}


# ── Helper ──────────────────────────────────────────────────────────────────

def _table_to_records(fields, num_records, table_data):
    """Convert flat ETABS table data to list of dicts."""
    nf = len(fields)
    rows = []
    for i in range(num_records):
        row = {}
        for j in range(nf):
            row[fields[j]] = table_data[i * nf + j]
        rows.append(row)
    return rows


# ═══════════════════════════════════════════════════════════════════════════
#  TOOLS
# ═══════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_model_info() -> str:
    """Get basic info about the currently open ETABS model: filename, units, lock state, story count, frame/area/point counts."""
    sm = _connect()
    filename = sm.GetModelFilename()
    unit_code = sm.GetPresentUnits()
    locked = sm.GetModelIsLocked()

    # counts
    ret = sm.FrameObj.GetAllFrames(
        0, [], [], [], [], [], [], [], [], [], [], [],
        [], [], [], [], [], [], [], []
    )
    n_frames = ret[0] if ret[0] else 0

    ret2 = sm.PointObj.GetNameList(0, [])
    n_points = ret2[0] if ret2[0] else 0

    ret3 = sm.AreaObj.GetNameList(0, [])
    n_areas = ret3[0] if ret3[0] else 0

    return json.dumps({
        "filename": filename,
        "units": UNITS_MAP.get(unit_code, str(unit_code)),
        "unit_code": unit_code,
        "locked": locked,
        "num_frames": n_frames,
        "num_points": n_points,
        "num_areas": n_areas,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def get_stories() -> str:
    """Get all story definitions: names, elevations, heights."""
    sm = _connect()
    ret = sm.Story.GetStories_2(0, 0, [], [], [], [], [], [], [], [])
    # ret: (BaseElev, NumStories, Names, Elevs, Heights, IsMaster, Similar, Splice, SpliceH, Color)
    base_elev = ret[0]
    n = ret[1]
    names = list(ret[2]) if ret[2] else []
    elevs = list(ret[3]) if ret[3] else []
    heights = list(ret[4]) if ret[4] else []
    stories = []
    for i in range(n):
        stories.append({
            "name": names[i],
            "elevation": elevs[i],
            "height": heights[i],
        })
    return json.dumps({"base_elevation": base_elev, "num_stories": n, "stories": stories},
                       ensure_ascii=False, indent=2)


@mcp.tool()
def read_table(table_key: str, max_rows: int = 500) -> str:
    """Read an ETABS database table by key. Returns records as JSON.

    Common table keys:
    - "Story Definitions", "Frame Section Properties", "Area Section Properties"
    - "Material Properties", "Load Pattern Definitions", "Load Case Definitions"
    - "Load Combination Definitions", "Frame Assignments - Summary"
    - "Story Drifts", "Story Forces", "Joint Displacements", "Joint Reactions"
    - "Element Forces - Frames", "Modal Periods And Frequencies"
    - "Modal Participating Mass Ratios"
    - "Concrete Column Summary", "Concrete Beam Summary", "Steel Frame Design Summary"

    Use list_tables() to discover all available table names.
    """
    sm = _connect()
    ret = sm.DatabaseTables.GetTableForDisplayArray(
        table_key, [], "All", 0, [], 0, []
    )
    # ret: (FieldKeyList, GroupName, TableVersion, FieldsKeysIncluded, NumberRecords, TableData, retval)
    fields = list(ret[3]) if ret[3] else []
    num_records = ret[4]
    table_data = list(ret[5]) if ret[5] else []
    retval = ret[6]

    if retval != 0:
        return json.dumps({"error": f"GetTableForDisplayArray returned {retval}", "table_key": table_key})

    if num_records > max_rows:
        table_data = table_data[:max_rows * len(fields)]
        num_records = max_rows
        truncated = True
    else:
        truncated = False

    records = _table_to_records(fields, num_records, table_data)
    return json.dumps({
        "table_key": table_key,
        "fields": fields,
        "num_records": num_records,
        "truncated": truncated,
        "records": records,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def list_tables() -> str:
    """List all available ETABS database table names."""
    sm = _connect()
    ret = sm.DatabaseTables.GetAllTables(0, [], 0, [])
    # ret: (NumberTables, TableKey, TableImportable, retval)
    # Actually the signature may vary. Let's handle it:
    table_keys = list(ret[1]) if ret[1] else []
    return json.dumps({"num_tables": len(table_keys), "tables": table_keys},
                       ensure_ascii=False, indent=2)


@mcp.tool()
def set_units(unit: str) -> str:
    """Set the present display units.

    Valid values: lb_in, lb_ft, kip_in, kip_ft, kN_mm, kN_m, kgf_mm, kgf_m,
                  N_mm, N_m, Ton_mm, Ton_m, kN_cm, kgf_cm, N_cm, Ton_cm
    """
    sm = _connect()
    code = UNIT_CODES.get(unit)
    if code is None:
        return json.dumps({"error": f"Unknown unit '{unit}'. Valid: {list(UNIT_CODES.keys())}"})
    ret = sm.SetPresentUnits(code)
    return json.dumps({"success": ret == 0, "unit": unit, "code": code})


@mcp.tool()
def run_analysis() -> str:
    """Save the model and run analysis. Returns success/failure."""
    sm = _connect()
    filename = sm.GetModelFilename()
    if not filename:
        return json.dumps({"error": "Model has no filename. Save first."})
    ret_save = sm.File.Save(filename)
    ret_run = sm.Analyze.RunAnalysis()
    return json.dumps({
        "save_result": ret_save,
        "analysis_result": ret_run,
        "success": ret_run == 0,
    })


@mcp.tool()
def get_modal_results() -> str:
    """Get modal periods, frequencies, and participating mass ratios."""
    sm = _connect()
    # Periods
    ret = sm.Results.ModalPeriod(0, [], [], [], [], [], [], [])
    n = ret[0]
    periods = list(ret[4]) if ret[4] else []
    frequencies = list(ret[5]) if ret[5] else []

    # Mass ratios
    ret2 = sm.Results.ModalParticipatingMassRatios(
        0, [], [], [], [], [], [], [], [], [], [], [], [], [], []
    )
    n2 = ret2[0]
    modes = []
    for i in range(min(n, n2)):
        m = {"mode": i + 1, "period": periods[i], "frequency": frequencies[i]}
        if ret2[4]:
            m["UX"] = ret2[5][i] if ret2[5] else None
            m["UY"] = ret2[6][i] if ret2[6] else None
            m["UZ"] = ret2[7][i] if ret2[7] else None
            m["SumUX"] = ret2[8][i] if ret2[8] else None
            m["SumUY"] = ret2[9][i] if ret2[9] else None
            m["SumUZ"] = ret2[10][i] if ret2[10] else None
        modes.append(m)
    return json.dumps({"num_modes": n, "modes": modes}, ensure_ascii=False, indent=2)


@mcp.tool()
def get_story_drifts(load_case: str = "") -> str:
    """Get story drift results. Optionally filter by load case name."""
    sm = _connect()
    # Select output
    sm.Results.Setup.DeselectAllCasesAndCombosForOutput()
    if load_case:
        sm.Results.Setup.SetCaseSelectedForOutput(load_case)
    else:
        sm.Results.Setup.SetOptionModalHist(2)  # all

    ret = sm.Results.StoryDrifts(
        0, [], [], [], [], [], [], [], [], [], []
    )
    n = ret[0]
    stories = list(ret[1]) if ret[1] else []
    cases = list(ret[2]) if ret[2] else []
    directions = list(ret[5]) if ret[5] else []
    drifts = list(ret[6]) if ret[6] else []
    labels = list(ret[7]) if ret[7] else []

    records = []
    for i in range(n):
        records.append({
            "story": stories[i],
            "load_case": cases[i],
            "direction": directions[i],
            "drift": drifts[i],
            "label": labels[i],
        })
    return json.dumps({"num_results": n, "records": records}, ensure_ascii=False, indent=2)


@mcp.tool()
def get_base_reactions(load_case: str = "", combo: str = "") -> str:
    """Get base reactions. Specify either load_case or combo name."""
    sm = _connect()
    sm.Results.Setup.DeselectAllCasesAndCombosForOutput()
    if load_case:
        sm.Results.Setup.SetCaseSelectedForOutput(load_case)
    if combo:
        sm.Results.Setup.SetComboSelectedForOutput(combo)

    ret = sm.Results.BaseReact(
        0, [], [], [], [], [], [], [], [], [], 0, 0, 0
    )
    n = ret[0]
    cases = list(ret[1]) if ret[1] else []
    fx = list(ret[4]) if ret[4] else []
    fy = list(ret[5]) if ret[5] else []
    fz = list(ret[6]) if ret[6] else []
    mx = list(ret[7]) if ret[7] else []
    my = list(ret[8]) if ret[8] else []
    mz = list(ret[9]) if ret[9] else []

    records = []
    for i in range(n):
        records.append({
            "load_case": cases[i],
            "FX": fx[i], "FY": fy[i], "FZ": fz[i],
            "MX": mx[i], "MY": my[i], "MZ": mz[i],
        })
    return json.dumps({"num_results": n, "records": records}, ensure_ascii=False, indent=2)


@mcp.tool()
def unlock_model() -> str:
    """Unlock the model for editing."""
    sm = _connect()
    ret = sm.SetModelIsLocked(False)
    return json.dumps({"success": ret == 0})


@mcp.tool()
def refresh_view() -> str:
    """Refresh the ETABS view."""
    sm = _connect()
    ret = sm.View.RefreshView(0, False)
    return json.dumps({"success": ret == 0})


@mcp.tool()
def run_python(code: str) -> str:
    """Execute arbitrary Python code against the ETABS COM API.

    The code has access to `sm` (SapModel) pre-connected.
    Use `result = ...` to set the return value, or use print().

    Example:
        code: |
          sm.SetPresentUnits(12)
          names = sm.FrameObj.GetNameList(0, [])[1]
          result = {"count": len(names), "first_5": list(names[:5])}
    """
    sm = _connect()
    local_vars = {"sm": sm, "result": None}
    import io
    stdout_capture = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = stdout_capture
        exec(code, {"__builtins__": __builtins__}, local_vars)
    except Exception:
        sys.stdout = old_stdout
        return json.dumps({
            "error": traceback.format_exc(),
            "stdout": stdout_capture.getvalue(),
        })
    finally:
        sys.stdout = old_stdout

    output = stdout_capture.getvalue()
    result = local_vars.get("result")

    if result is not None:
        try:
            return json.dumps({"result": result, "stdout": output}, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return json.dumps({"result": str(result), "stdout": output})
    elif output:
        return output
    else:
        return json.dumps({"result": "OK (no output)"})


@mcp.tool()
def select_objects(
    object_type: str = "frame",
    names: list[str] | None = None,
    story: str = "",
    property_name: str = "",
) -> str:
    """Select objects in the ETABS model by name list, story, or property.

    object_type: "frame", "area", or "point"
    names: list of object names to select
    story: select all objects on this story
    property_name: select all objects with this section property
    """
    sm = _connect()
    sm.SelectObj.ClearSelection()

    if names:
        for name in names:
            if object_type == "frame":
                sm.FrameObj.SetSelected(name, True)
            elif object_type == "area":
                sm.AreaObj.SetSelected(name, True)
            elif object_type == "point":
                sm.PointObj.SetSelected(name, True)
        return json.dumps({"selected": len(names), "type": object_type})

    if story:
        sm.SelectObj.Story(story)
        return json.dumps({"selected_story": story})

    if property_name:
        sm.SelectObj.PropertyFrame(property_name)
        return json.dumps({"selected_property": property_name})

    return json.dumps({"error": "Provide names, story, or property_name"})


@mcp.tool()
def get_design_results(design_type: str = "concrete", element: str = "column") -> str:
    """Get design results summary.

    design_type: "concrete" or "steel"
    element: "column" or "beam" (for concrete only)
    """
    sm = _connect()
    table_map = {
        ("concrete", "column"): "Concrete Column Summary",
        ("concrete", "beam"): "Concrete Beam Summary",
        ("steel", "frame"): "Steel Frame Design Summary",
        ("steel", "beam"): "Steel Frame Design Summary",
        ("steel", "column"): "Steel Frame Design Summary",
    }
    table_key = table_map.get((design_type, element))
    if not table_key:
        return json.dumps({"error": f"Unknown design_type/element: {design_type}/{element}"})

    ret = sm.DatabaseTables.GetTableForDisplayArray(
        table_key, [], "All", 0, [], 0, []
    )
    fields = list(ret[3]) if ret[3] else []
    num_records = ret[4]
    table_data = list(ret[5]) if ret[5] else []
    retval = ret[6]

    if retval != 0:
        return json.dumps({"error": f"Table read failed (ret={retval}). Run design first?"})

    records = _table_to_records(fields, min(num_records, 200), table_data[:200 * len(fields)])
    return json.dumps({
        "table_key": table_key,
        "num_records": num_records,
        "truncated": num_records > 200,
        "records": records,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def get_load_patterns() -> str:
    """Get all load pattern definitions."""
    sm = _connect()
    ret = sm.LoadPatterns.GetNameList(0, [])
    n = ret[0]
    names = list(ret[1]) if ret[1] else []
    patterns = []
    for name in names:
        lp_type = sm.LoadPatterns.GetLoadType(name)
        sw = sm.LoadPatterns.GetSelfWTMultiplier(name)
        patterns.append({"name": name, "type": lp_type[0] if isinstance(lp_type, tuple) else lp_type,
                          "self_weight_multiplier": sw[0] if isinstance(sw, tuple) else sw})
    return json.dumps({"num_patterns": n, "patterns": patterns}, ensure_ascii=False, indent=2)


@mcp.tool()
def get_load_combinations() -> str:
    """Get all load combination definitions."""
    sm = _connect()
    ret = sm.RespCombo.GetNameList(0, [])
    n = ret[0]
    names = list(ret[1]) if ret[1] else []
    combos = []
    for name in names:
        case_ret = sm.RespCombo.GetCaseList(name, 0, [], [], [])
        num_cases = case_ret[0] if case_ret[0] else 0
        case_types = list(case_ret[1]) if case_ret[1] else []
        case_names = list(case_ret[2]) if case_ret[2] else []
        scale_factors = list(case_ret[3]) if case_ret[3] else []
        cases = []
        for j in range(num_cases):
            cases.append({
                "type": case_types[j],
                "name": case_names[j],
                "scale_factor": scale_factors[j],
            })
        combos.append({"name": name, "cases": cases})
    return json.dumps({"num_combos": n, "combos": combos}, ensure_ascii=False, indent=2)


@mcp.tool()
def get_frame_sections() -> str:
    """Get all frame section properties (name, material, shape, dimensions)."""
    sm = _connect()
    return read_table("Frame Section Properties", max_rows=500)


@mcp.tool()
def get_area_sections() -> str:
    """Get all area section properties."""
    sm = _connect()
    return read_table("Area Section Properties", max_rows=500)


@mcp.tool()
def get_materials() -> str:
    """Get all material property definitions."""
    sm = _connect()
    return read_table("Material Properties", max_rows=200)


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mcp.run(transport="stdio")
