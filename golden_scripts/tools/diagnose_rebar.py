"""
Diagnostic tool: test SetRebarColumn / SetRebarBeam API calls.

Connects to a running ETABS instance, reads current rebar state for sample
column and beam sections, attempts to set rebar, then reads back to verify.

Outputs a JSON report with full before/after comparison.

Key insight: comtypes returns (ref_param_1, ..., ref_param_n, return_code)
for methods with ref parameters. The return code is the LAST element.
For methods without ref parameters (Set*), the return is the plain int.

Usage:
    python -m golden_scripts.tools.diagnose_rebar --output diagnose_rebar_report.json
"""
import json
import sys
import os
import argparse
import traceback

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_dir, ".."))  # golden_scripts/
from constants import (
    COL_COVER, COL_CORNER_BARS, COL_TIE_SPACING,
    COL_REBAR_SIZE, COL_TIE_SIZE, COL_NUM_2DIR_TIE, COL_NUM_3DIR_TIE,
    BEAM_COVER_TOP, BEAM_COVER_BOT, FB_COVER_TOP, FB_COVER_BOT,
    parse_frame_section, get_frame_dimensions, calc_column_bar_distribution,
    is_foundation_beam,
)


def _connect():
    """Connect to running ETABS. Returns (SapModel, connection_method)."""
    method = "unknown"
    try:
        from find_etabs import find_etabs
        etabs, filename = find_etabs(run=False, backup=False)
        SapModel = etabs.SapModel
        method = "find_etabs (etabs_api)"
    except (ImportError, ModuleNotFoundError, Exception):
        import comtypes.client
        etabs = comtypes.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        SapModel = etabs.SapModel
        method = "comtypes.client.GetActiveObject"
    SapModel.SetPresentUnits(12)  # TON/M
    return SapModel, method


def _safe_str(val):
    """Convert COM return values to JSON-safe strings."""
    if isinstance(val, (list, tuple)):
        return [_safe_str(v) for v in val]
    return val


def get_rebar_sizes(SapModel):
    """Get all available rebar size names from PropRebar.GetNameList."""
    try:
        ret = SapModel.PropRebar.GetNameList(0, [])
        # comtypes return: (NumberNames, names_tuple, retcode)
        # retcode is LAST element
        ret_list = list(ret) if isinstance(ret, (list, tuple)) else [ret]
        retcode = ret_list[-1] if len(ret_list) > 1 else ret_list[0]
        names = []
        for item in ret_list:
            if isinstance(item, (list, tuple)):
                for s in item:
                    if isinstance(s, str):
                        names.append(s)
        return {"retcode": retcode, "ret_raw": str(ret), "names": names}
    except Exception as e:
        return {"retcode": -1, "error": str(e), "names": []}


def get_frame_sections(SapModel):
    """Get all frame section names from PropFrame.GetNameList."""
    try:
        ret = SapModel.PropFrame.GetNameList(0, [])
        names = []
        for item in ret:
            if isinstance(item, (list, tuple)):
                for s in item:
                    if isinstance(s, str):
                        names.append(s)
            elif isinstance(item, str):
                names.append(item)
        return names
    except Exception as e:
        print(f"  ERROR getting frame sections: {e}")
        return []


def get_materials(SapModel):
    """Get all material names."""
    try:
        ret = SapModel.PropMaterial.GetNameList(0, [])
        names = []
        for item in ret:
            if isinstance(item, (list, tuple)):
                for s in item:
                    if isinstance(s, str):
                        names.add(s) if hasattr(names, 'add') else names.append(s)
            elif isinstance(item, str):
                names.append(item)
        return sorted(set(names))
    except Exception as e:
        print(f"  ERROR getting materials: {e}")
        return []


def get_rebar_column(SapModel, name):
    """Call GetRebarColumn and return parsed result dict.

    comtypes returns: (MatPropLong, MatPropConfine, Pattern, ConfineType,
    Cover, NumberCBars, NumberR3Bars, NumberR2Bars, RebarSize, TieSize,
    TieSpacingLongit, Number2DirTieBars, Number3DirTieBars, ToBeDesigned,
    retcode)  -- retcode is LAST.
    """
    try:
        ret = SapModel.PropFrame.GetRebarColumn(
            name, "", "", 0, 0, 0.0, 0, 0, 0, "", "", 0.0, 0, 0, False
        )
        ret_list = list(ret) if isinstance(ret, (list, tuple)) else [ret]
        if len(ret_list) >= 15:
            # retcode is last element
            return {
                "retcode": ret_list[-1],
                "MatPropLong": ret_list[0],
                "MatPropConfine": ret_list[1],
                "Pattern": ret_list[2],
                "ConfineType": ret_list[3],
                "Cover": ret_list[4],
                "NumberCBars": ret_list[5],
                "NumberR3Bars": ret_list[6],
                "NumberR2Bars": ret_list[7],
                "RebarSize": ret_list[8],
                "TieSize": ret_list[9],
                "TieSpacingLongit": ret_list[10],
                "Number2DirTieBars": ret_list[11],
                "Number3DirTieBars": ret_list[12],
                "ToBeDesigned": ret_list[13],
                "ret_raw": str(ret),
            }
        return {"retcode": ret_list[-1] if ret_list else -1,
                "ret_raw": str(ret),
                "error": f"Unexpected return length: {len(ret_list)}"}
    except Exception as e:
        return {"retcode": -1, "error": str(e), "traceback": traceback.format_exc()}


def set_rebar_column(SapModel, name, num_r3, num_r2):
    """Call SetRebarColumn with standard constants. Return raw result."""
    try:
        ret = SapModel.PropFrame.SetRebarColumn(
            name,
            "SD420",           # MatPropLong
            "SD420",           # MatPropConfine
            1,                 # Pattern: Rectangular
            1,                 # ConfineType: Ties
            COL_COVER,         # Cover (0.07 m)
            COL_CORNER_BARS,   # NumberCBars (4)
            num_r3,            # NumberR3Bars
            num_r2,            # NumberR2Bars
            COL_REBAR_SIZE,    # RebarSize ("#8")
            COL_TIE_SIZE,      # TieSize ("#4")
            COL_TIE_SPACING,   # TieSpacingLongit (0.15 m)
            COL_NUM_2DIR_TIE,  # Number2DirTieBars (2)
            COL_NUM_3DIR_TIE,  # Number3DirTieBars (2)
            True               # ToBeDesigned
        )
        retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
        return {"retcode": retcode, "ret_raw": str(ret)}
    except Exception as e:
        return {"retcode": -1, "error": str(e), "traceback": traceback.format_exc()}


def get_rebar_beam(SapModel, name):
    """Call GetRebarBeam and return parsed result dict.

    comtypes returns: (MatPropLong, MatPropConfine, CoverTop, CoverBot,
    TopLeftArea, TopRightArea, BotLeftArea, BotRightArea, retcode)
    -- retcode is LAST.
    """
    try:
        ret = SapModel.PropFrame.GetRebarBeam(
            name, "", "", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        )
        ret_list = list(ret) if isinstance(ret, (list, tuple)) else [ret]
        if len(ret_list) >= 9:
            return {
                "retcode": ret_list[-1],
                "MatPropLong": ret_list[0],
                "MatPropConfine": ret_list[1],
                "CoverTop": ret_list[2],
                "CoverBot": ret_list[3],
                "TopLeftArea": ret_list[4],
                "TopRightArea": ret_list[5],
                "BotLeftArea": ret_list[6],
                "BotRightArea": ret_list[7],
                "ret_raw": str(ret),
            }
        return {"retcode": ret_list[-1] if ret_list else -1,
                "ret_raw": str(ret),
                "error": f"Unexpected return length: {len(ret_list)}"}
    except Exception as e:
        return {"retcode": -1, "error": str(e), "traceback": traceback.format_exc()}


def set_rebar_beam(SapModel, name, cover_top, cover_bot):
    """Call SetRebarBeam with standard constants. Return raw result."""
    try:
        ret = SapModel.PropFrame.SetRebarBeam(
            name,
            "SD420",       # MatPropLong
            "SD420",       # MatPropConfine
            cover_top,     # CoverTop
            cover_bot,     # CoverBot
            0.0,           # TopLeftArea (0 = design mode)
            0.0,           # TopRightArea
            0.0,           # BotLeftArea
            0.0            # BotRightArea
        )
        retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
        return {"retcode": retcode, "ret_raw": str(ret)}
    except Exception as e:
        return {"retcode": -1, "error": str(e), "traceback": traceback.format_exc()}


def try_set_rebar_column_with_ctypes(SapModel, name, num_r3, num_r2):
    """Try SetRebarColumn with explicit ctypes type casting."""
    import ctypes
    try:
        ret = SapModel.PropFrame.SetRebarColumn(
            str(name),
            str("SD420"),
            str("SD420"),
            ctypes.c_int(1),
            ctypes.c_int(1),
            ctypes.c_double(COL_COVER),
            ctypes.c_int(COL_CORNER_BARS),
            ctypes.c_int(num_r3),
            ctypes.c_int(num_r2),
            str(COL_REBAR_SIZE),
            str(COL_TIE_SIZE),
            ctypes.c_double(COL_TIE_SPACING),
            ctypes.c_int(COL_NUM_2DIR_TIE),
            ctypes.c_int(COL_NUM_3DIR_TIE),
            ctypes.c_bool(True)
        )
        retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
        return {"retcode": retcode, "ret_raw": str(ret), "method": "ctypes"}
    except Exception as e:
        return {"retcode": -1, "error": str(e), "method": "ctypes"}


def try_set_rebar_beam_with_ctypes(SapModel, name, cover_top, cover_bot):
    """Try SetRebarBeam with explicit ctypes type casting."""
    import ctypes
    try:
        ret = SapModel.PropFrame.SetRebarBeam(
            str(name),
            str("SD420"),
            str("SD420"),
            ctypes.c_double(cover_top),
            ctypes.c_double(cover_bot),
            ctypes.c_double(0.0),
            ctypes.c_double(0.0),
            ctypes.c_double(0.0),
            ctypes.c_double(0.0)
        )
        retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
        return {"retcode": retcode, "ret_raw": str(ret), "method": "ctypes"}
    except Exception as e:
        return {"retcode": -1, "error": str(e), "method": "ctypes"}


def try_unlock_and_set(SapModel, col_section, beam_section, num_r3, num_r2,
                       cover_top, cover_bot):
    """Unlock model and retry Set calls."""
    results = {}
    try:
        was_locked = SapModel.GetModelIsLocked()
        results["was_locked"] = was_locked
        if was_locked:
            SapModel.SetModelIsLocked(False)
            results["unlocked"] = True

        if col_section:
            ret = SapModel.PropFrame.SetRebarColumn(
                col_section, "SD420", "SD420", 1, 1, COL_COVER,
                COL_CORNER_BARS, num_r3, num_r2,
                COL_REBAR_SIZE, COL_TIE_SIZE, COL_TIE_SPACING,
                COL_NUM_2DIR_TIE, COL_NUM_3DIR_TIE, True
            )
            retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
            results["col_retcode_after_unlock"] = retcode

        if beam_section:
            ret = SapModel.PropFrame.SetRebarBeam(
                beam_section, "SD420", "SD420",
                cover_top, cover_bot, 0.0, 0.0, 0.0, 0.0
            )
            retcode = ret[0] if isinstance(ret, (list, tuple)) else ret
            results["beam_retcode_after_unlock"] = retcode

    except Exception as e:
        results["error"] = str(e)
    return results


def try_database_tables(SapModel, section_name):
    """Try reading rebar data via DatabaseTables as alternative verification."""
    results = {}
    try:
        # Try "Frame Section Property Definitions - Concrete Rectangular"
        table_key = "Frame Section Property Definitions - Concrete Rectangular"
        ret = SapModel.DatabaseTables.GetTableForDisplayArray(
            table_key, [], "All", 0, [], 0, [])
        retcode = ret[0]
        results["table_retcode"] = retcode
        if retcode == 0:
            fields = list(ret[4])
            n_fields = len(fields)
            n_records = ret[5]
            data = list(ret[6])
            results["fields"] = fields
            results["n_records"] = n_records
            # Find matching section
            for i in range(n_records):
                row = dict(zip(fields, data[i * n_fields:(i + 1) * n_fields]))
                if row.get("Name") == section_name:
                    results["section_row"] = row
                    break
        else:
            results["table_error"] = f"GetTableForDisplayArray returned {retcode}"
    except Exception as e:
        results["error"] = str(e)
    return results


def find_sample_sections(frame_sections):
    """Find one column and one beam section from the list."""
    col_section = None
    beam_section = None
    for name in frame_sections:
        prefix, w, d, fc = parse_frame_section(name)
        if not prefix:
            continue
        if prefix == "C" and col_section is None:
            col_section = name
        elif prefix != "C" and beam_section is None:
            beam_section = name
        if col_section and beam_section:
            break
    return col_section, beam_section


def diagnose(output_path):
    """Run full rebar diagnostic."""
    report = {
        "environment": {},
        "rebar_sizes": {},
        "column_test": {},
        "beam_test": {},
        "alternative_tests": {},
        "diagnosis": [],
    }

    print("=" * 70)
    print("  REBAR DIAGNOSTIC TOOL")
    print("=" * 70)

    # 1. Connect
    print("\n  Connecting to ETABS...")
    SapModel, conn_method = _connect()
    model_file = SapModel.GetModelFilename()
    print(f"  Model: {model_file}")
    print(f"  Connection: {conn_method}")

    # Check model lock state
    try:
        is_locked = SapModel.GetModelIsLocked()
    except Exception:
        is_locked = "unknown"

    try:
        units = SapModel.GetPresentUnits()
    except Exception:
        units = "unknown"

    report["environment"]["model_file"] = model_file
    report["environment"]["connection_method"] = conn_method
    report["environment"]["units"] = units
    report["environment"]["model_locked"] = is_locked

    print(f"  Units: {units}")
    print(f"  Model locked: {is_locked}")

    if is_locked:
        report["diagnosis"].append(
            "WARNING: Model is LOCKED (post-analysis state). "
            "Will attempt to unlock before Set calls."
        )

    # 2. Materials
    print("\n  Reading materials...")
    materials = get_materials(SapModel)
    report["environment"]["materials"] = materials
    sd420_exists = "SD420" in materials
    report["environment"]["SD420_exists"] = sd420_exists
    print(f"  SD420 in model: {sd420_exists}")
    print(f"  All materials: {materials}")

    if not sd420_exists:
        report["diagnosis"].append(
            "CRITICAL: SD420 rebar material not found in model. "
            "SetRebarColumn/SetRebarBeam will fail. "
            "gs_01_init.py should create SD420 — check if step 1 ran."
        )

    # 2b. Check SD420 material type (must be eMatType.Rebar = 6)
    if sd420_exists:
        try:
            mat_type_ret = SapModel.PropMaterial.GetTypeOAPI("SD420", 0)
            mat_type = mat_type_ret[0] if isinstance(mat_type_ret, (list, tuple)) else mat_type_ret
            report["environment"]["SD420_mattype"] = mat_type
            report["environment"]["SD420_mattype_raw"] = str(mat_type_ret)
            print(f"  SD420 material type: {mat_type} (6=Rebar, 5=ColdFormed)")

            if mat_type != 6:
                report["diagnosis"].append(
                    f"ROOT CAUSE: SD420 material type is {mat_type} "
                    f"(expected 6=Rebar). gs_01_init.py used wrong eMatType. "
                    f"Fix: SetMaterial('SD420', 6) instead of 5."
                )
                print(f"  *** SD420 IS NOT REBAR TYPE! type={mat_type} ***")
                print(f"  This is the root cause of SetRebarColumn/SetRebarBeam failure.")
            else:
                print(f"  SD420 material type OK (Rebar)")
        except Exception as e:
            print(f"  Could not check SD420 type: {e}")

    # 3. Rebar sizes
    print("\n  Reading rebar size names (PropRebar.GetNameList)...")
    rebar_info = get_rebar_sizes(SapModel)
    report["rebar_sizes"] = rebar_info
    rebar_names = rebar_info.get("names", [])
    print(f"  Rebar sizes ({len(rebar_names)}): {rebar_names}")

    has_8 = COL_REBAR_SIZE in rebar_names
    has_4 = COL_TIE_SIZE in rebar_names
    report["environment"]["rebar_size_8_exists"] = has_8
    report["environment"]["rebar_size_4_exists"] = has_4
    print(f"  {COL_REBAR_SIZE} exists: {has_8}")
    print(f"  {COL_TIE_SIZE} exists: {has_4}")

    if not has_8:
        report["diagnosis"].append(
            f"CRITICAL: Rebar size '{COL_REBAR_SIZE}' not found. "
            f"Available: {rebar_names}. SetRebarColumn will fail."
        )
    if not has_4:
        report["diagnosis"].append(
            f"CRITICAL: Tie size '{COL_TIE_SIZE}' not found. "
            f"Available: {rebar_names}. SetRebarColumn will fail."
        )

    # 4. Frame sections
    print("\n  Reading frame sections...")
    frame_sections = get_frame_sections(SapModel)
    report["environment"]["frame_section_count"] = len(frame_sections)
    report["environment"]["frame_sections_sample"] = frame_sections[:20]
    print(f"  Total frame sections: {len(frame_sections)}")

    col_section, beam_section = find_sample_sections(frame_sections)
    print(f"  Sample column: {col_section}")
    print(f"  Sample beam:   {beam_section}")

    # Compute column params
    num_r3, num_r2 = 0, 0
    cover_top, cover_bot = BEAM_COVER_TOP, BEAM_COVER_BOT
    if col_section:
        prefix, w, d, fc = parse_frame_section(col_section)
        width_cm, depth_cm = get_frame_dimensions(prefix, w, d)
        num_r3, num_r2 = calc_column_bar_distribution(width_cm, depth_cm)

    if beam_section:
        prefix, w, d, fc = parse_frame_section(beam_section)
        is_fb = is_foundation_beam(prefix)
        cover_top = FB_COVER_TOP if is_fb else BEAM_COVER_TOP
        cover_bot = FB_COVER_BOT if is_fb else BEAM_COVER_BOT

    # ====================================================
    # 5. Column test
    # ====================================================
    if col_section:
        print(f"\n  --- Column Test: {col_section} ---")
        prefix, w, d, fc = parse_frame_section(col_section)
        width_cm, depth_cm = get_frame_dimensions(prefix, w, d)

        col_test = {
            "section": col_section,
            "parsed": {"prefix": prefix, "w": w, "d": d, "fc": fc},
            "dimensions": {"width_cm": width_cm, "depth_cm": depth_cm},
            "bar_calc": {"num_r3": num_r3, "num_r2": num_r2},
        }

        # Before
        print("    GetRebarColumn (before)...")
        col_test["before"] = get_rebar_column(SapModel, col_section)
        rc = col_test["before"].get("retcode")
        print(f"    retcode={rc}")
        if rc == 0:
            b = col_test["before"]
            print(f"    MatLong={b.get('MatPropLong')}, Cover={b.get('Cover')}, "
                  f"R3={b.get('NumberR3Bars')}, R2={b.get('NumberR2Bars')}, "
                  f"RebarSize={b.get('RebarSize')}, TieSize={b.get('TieSize')}")

        # Set
        print(f"    SetRebarColumn(num_r3={num_r3}, num_r2={num_r2})...")
        col_test["set_result"] = set_rebar_column(SapModel, col_section, num_r3, num_r2)
        set_rc = col_test["set_result"].get("retcode")
        print(f"    retcode={set_rc}")
        if set_rc != 0:
            print(f"    FAIL: ret_raw={col_test['set_result'].get('ret_raw')}")

        # After
        print("    GetRebarColumn (after)...")
        col_test["after"] = get_rebar_column(SapModel, col_section)
        rc = col_test["after"].get("retcode")
        print(f"    retcode={rc}")
        if rc == 0:
            a = col_test["after"]
            print(f"    MatLong={a.get('MatPropLong')}, Cover={a.get('Cover')}, "
                  f"R3={a.get('NumberR3Bars')}, R2={a.get('NumberR2Bars')}, "
                  f"RebarSize={a.get('RebarSize')}, TieSize={a.get('TieSize')}")

        # Verify
        if set_rc == 0 and col_test["after"].get("retcode") == 0:
            after = col_test["after"]
            col_test["verification"] = {
                "cover_ok": abs(after.get("Cover", 0) - COL_COVER) < 0.001,
                "mat_ok": after.get("MatPropLong") == "SD420",
                "r3_ok": after.get("NumberR3Bars") == num_r3,
                "r2_ok": after.get("NumberR2Bars") == num_r2,
                "rebar_size_ok": after.get("RebarSize") == COL_REBAR_SIZE,
                "tie_size_ok": after.get("TieSize") == COL_TIE_SIZE,
            }
            col_test["verification"]["all_ok"] = all(
                v for k, v in col_test["verification"].items() if k != "all_ok")
            if col_test["verification"]["all_ok"]:
                print("    PASS: All column rebar params verified")
            else:
                failed = [k for k, v in col_test["verification"].items()
                          if k != "all_ok" and not v]
                print(f"    PARTIAL FAIL: {failed}")
        elif set_rc != 0:
            report["diagnosis"].append(
                f"SetRebarColumn FAILED for {col_section} (retcode={set_rc})")

        report["column_test"] = col_test
    else:
        report["column_test"] = {"skipped": True, "reason": "No column section in model"}

    # ====================================================
    # 6. Beam test
    # ====================================================
    if beam_section:
        print(f"\n  --- Beam Test: {beam_section} ---")
        prefix, w, d, fc = parse_frame_section(beam_section)
        is_fb = is_foundation_beam(prefix)

        beam_test = {
            "section": beam_section,
            "parsed": {"prefix": prefix, "w": w, "d": d, "fc": fc},
            "is_foundation_beam": is_fb,
        }

        # Before
        print("    GetRebarBeam (before)...")
        beam_test["before"] = get_rebar_beam(SapModel, beam_section)
        rc = beam_test["before"].get("retcode")
        print(f"    retcode={rc}")
        if rc == 0:
            b = beam_test["before"]
            print(f"    MatLong={b.get('MatPropLong')}, "
                  f"CoverTop={b.get('CoverTop')}, CoverBot={b.get('CoverBot')}")

        # Set
        print(f"    SetRebarBeam(cover_top={cover_top}, cover_bot={cover_bot})...")
        beam_test["set_result"] = set_rebar_beam(SapModel, beam_section, cover_top, cover_bot)
        set_rc = beam_test["set_result"].get("retcode")
        print(f"    retcode={set_rc}")
        if set_rc != 0:
            print(f"    FAIL: ret_raw={beam_test['set_result'].get('ret_raw')}")

        # After
        print("    GetRebarBeam (after)...")
        beam_test["after"] = get_rebar_beam(SapModel, beam_section)
        rc = beam_test["after"].get("retcode")
        print(f"    retcode={rc}")
        if rc == 0:
            a = beam_test["after"]
            print(f"    MatLong={a.get('MatPropLong')}, "
                  f"CoverTop={a.get('CoverTop')}, CoverBot={a.get('CoverBot')}")

        # Verify
        if set_rc == 0 and beam_test["after"].get("retcode") == 0:
            after = beam_test["after"]
            beam_test["verification"] = {
                "cover_top_ok": abs(after.get("CoverTop", 0) - cover_top) < 0.001,
                "cover_bot_ok": abs(after.get("CoverBot", 0) - cover_bot) < 0.001,
                "mat_ok": after.get("MatPropLong") == "SD420",
            }
            beam_test["verification"]["all_ok"] = all(
                v for k, v in beam_test["verification"].items() if k != "all_ok")
            if beam_test["verification"]["all_ok"]:
                print("    PASS: All beam rebar params verified")
            else:
                failed = [k for k, v in beam_test["verification"].items()
                          if k != "all_ok" and not v]
                print(f"    PARTIAL FAIL: {failed}")
        elif set_rc != 0:
            report["diagnosis"].append(
                f"SetRebarBeam FAILED for {beam_section} (retcode={set_rc})")

        report["beam_test"] = beam_test
    else:
        report["beam_test"] = {"skipped": True, "reason": "No beam section in model"}

    # ====================================================
    # 7. Alternative approaches (if Set failed)
    # ====================================================
    col_failed = report.get("column_test", {}).get("set_result", {}).get("retcode") != 0
    beam_failed = report.get("beam_test", {}).get("set_result", {}).get("retcode") != 0

    if col_failed or beam_failed:
        print(f"\n  --- Alternative Approaches (Set failed) ---")
        alts = {}

        # 7a. Unlock and retry
        print("    [A] Unlock model and retry...")
        alts["unlock_retry"] = try_unlock_and_set(
            SapModel,
            col_section if col_failed else None,
            beam_section if beam_failed else None,
            num_r3, num_r2, cover_top, cover_bot
        )
        print(f"    Result: {alts['unlock_retry']}")

        if alts["unlock_retry"].get("col_retcode_after_unlock") == 0:
            print("    >>> UNLOCK FIXED column! Root cause: model was locked.")
            report["diagnosis"].append(
                "ROOT CAUSE: Model was locked. SetRebarColumn works after unlock.")

        if alts["unlock_retry"].get("beam_retcode_after_unlock") == 0:
            print("    >>> UNLOCK FIXED beam! Root cause: model was locked.")
            report["diagnosis"].append(
                "ROOT CAUSE: Model was locked. SetRebarBeam works after unlock.")

        # Check if unlock helped
        unlock_fixed_col = alts["unlock_retry"].get("col_retcode_after_unlock") == 0
        unlock_fixed_beam = alts["unlock_retry"].get("beam_retcode_after_unlock") == 0

        # 7b. ctypes explicit typing (only if unlock didn't help)
        if (col_failed and not unlock_fixed_col) or (beam_failed and not unlock_fixed_beam):
            print("    [B] Retry with explicit ctypes types...")
            if col_failed and not unlock_fixed_col and col_section:
                alts["ctypes_col"] = try_set_rebar_column_with_ctypes(
                    SapModel, col_section, num_r3, num_r2)
                print(f"    Column ctypes: retcode={alts['ctypes_col'].get('retcode')}")

                if alts["ctypes_col"].get("retcode") == 0:
                    report["diagnosis"].append(
                        "ROOT CAUSE: COM type mismatch. ctypes explicit casting fixes it.")

            if beam_failed and not unlock_fixed_beam and beam_section:
                alts["ctypes_beam"] = try_set_rebar_beam_with_ctypes(
                    SapModel, beam_section, cover_top, cover_bot)
                print(f"    Beam ctypes: retcode={alts['ctypes_beam'].get('retcode')}")

                if alts["ctypes_beam"].get("retcode") == 0:
                    report["diagnosis"].append(
                        "ROOT CAUSE: COM type mismatch. ctypes explicit casting fixes it.")

        # 7c. Database tables approach (always run for info)
        if col_section:
            print(f"    [C] Reading database tables for {col_section}...")
            alts["db_tables_col"] = try_database_tables(SapModel, col_section)
            if alts["db_tables_col"].get("section_row"):
                print(f"    DB row: {json.dumps(alts['db_tables_col']['section_row'], indent=2)}")
            elif alts["db_tables_col"].get("error"):
                print(f"    DB error: {alts['db_tables_col']['error']}")
            else:
                print(f"    DB: section not found in table (retcode={alts['db_tables_col'].get('table_retcode')})")

        # 7d. Verify GetRebarColumn after alternatives
        if col_section:
            print(f"\n    GetRebarColumn (final check after alternatives)...")
            final_col = get_rebar_column(SapModel, col_section)
            alts["final_col_get"] = final_col
            rc = final_col.get("retcode")
            print(f"    retcode={rc}")
            if rc == 0:
                print(f"    MatLong={final_col.get('MatPropLong')}, "
                      f"Cover={final_col.get('Cover')}, "
                      f"R3={final_col.get('NumberR3Bars')}, R2={final_col.get('NumberR2Bars')}")

        if beam_section:
            print(f"    GetRebarBeam (final check after alternatives)...")
            final_beam = get_rebar_beam(SapModel, beam_section)
            alts["final_beam_get"] = final_beam
            rc = final_beam.get("retcode")
            print(f"    retcode={rc}")
            if rc == 0:
                print(f"    MatLong={final_beam.get('MatPropLong')}, "
                      f"CoverTop={final_beam.get('CoverTop')}, "
                      f"CoverBot={final_beam.get('CoverBot')}")

        report["alternative_tests"] = alts

    # ====================================================
    # 8. Summary
    # ====================================================
    print("\n" + "=" * 70)
    print("  DIAGNOSIS SUMMARY")
    print("=" * 70)

    if not report["diagnosis"]:
        report["diagnosis"].append("All tests passed. Rebar API calls work correctly.")
        print("  All tests PASSED. SetRebarColumn and SetRebarBeam work correctly.")
    else:
        for i, msg in enumerate(report["diagnosis"], 1):
            print(f"  [{i}] {msg}")

    # Constants reference
    report["constants_used"] = {
        "COL_COVER": COL_COVER,
        "COL_CORNER_BARS": COL_CORNER_BARS,
        "COL_TIE_SPACING": COL_TIE_SPACING,
        "COL_REBAR_SIZE": COL_REBAR_SIZE,
        "COL_TIE_SIZE": COL_TIE_SIZE,
        "COL_NUM_2DIR_TIE": COL_NUM_2DIR_TIE,
        "COL_NUM_3DIR_TIE": COL_NUM_3DIR_TIE,
        "BEAM_COVER_TOP": BEAM_COVER_TOP,
        "BEAM_COVER_BOT": BEAM_COVER_BOT,
        "FB_COVER_TOP": FB_COVER_TOP,
        "FB_COVER_BOT": FB_COVER_BOT,
    }

    # Write report
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Report written to: {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose frame section rebar (SetRebarColumn/SetRebarBeam) issues")
    parser.add_argument(
        "--output", default="diagnose_rebar_report.json",
        help="Output JSON report path (default: diagnose_rebar_report.json)")
    args = parser.parse_args()
    diagnose(args.output)


if __name__ == "__main__":
    main()
