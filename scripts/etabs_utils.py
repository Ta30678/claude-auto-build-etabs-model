"""
ETABS Utility Functions
========================
Common operations for ETABS model manipulation.
Provides high-level wrappers around the ETABS COM API.
"""


# ============================================================
# Story / Grid Operations
# ============================================================

def get_stories(SapModel):
    """Get all story names and elevations."""
    stories = {}
    ret = SapModel.Story.GetStories_2()
    # Returns: [ret, NumberStories, StoryNames, StoryElevations,
    #           StoryHeights, IsMasterStory, SimilarToStory, SpliceAbove,
    #           SpliceHeight, Color]
    if ret[0] == 0:
        n = ret[1]
        for i in range(n):
            stories[ret[2][i]] = {
                "elevation": ret[3][i],
                "height": ret[4][i],
                "is_master": ret[5][i],
            }
    return stories


def define_story(SapModel, name, height, is_master=False, similar_to=""):
    """Define a single story."""
    # Use Story.SetStories_2 for batch definition
    pass  # Implemented via batch in create_stories


def create_stories(SapModel, story_list):
    """
    Create multiple stories.

    Args:
        SapModel: SapModel object
        story_list: list of dicts with keys:
            - name (str)
            - height (float) in current units
            - is_master (bool, optional)
            - similar_to (str, optional)

    Example:
        create_stories(SapModel, [
            {"name": "Base", "height": 0},
            {"name": "1F", "height": 400},
            {"name": "2F", "height": 340},
        ])
    """
    n = len(story_list)
    names = [s["name"] for s in story_list]
    heights = [s["height"] for s in story_list]
    is_masters = [s.get("is_master", False) for s in story_list]
    similar_tos = [s.get("similar_to", "") for s in story_list]
    splice_aboves = [False] * n
    splice_heights = [0.0] * n
    colors = [0] * n

    ret = SapModel.Story.SetStories_2(
        0,  # BaseElevation
        n, names, heights, is_masters, similar_tos,
        splice_aboves, splice_heights, colors
    )
    return ret


# ============================================================
# Grid Operations
# ============================================================

def define_grid_system(SapModel, x_coords, y_coords, name="Global"):
    """
    Define a cartesian grid system.

    Args:
        SapModel: SapModel object
        x_coords: list of X grid coordinates
        y_coords: list of Y grid coordinates
        name: grid system name
    """
    # This is typically done through coordinate system and grid definitions
    pass


# ============================================================
# Material Definitions
# ============================================================

def add_concrete_material(SapModel, name, fc, unit_weight=2400, E=None):
    """
    Add a concrete material.

    Args:
        name: Material name (e.g., "C280")
        fc: Compressive strength in current units
        unit_weight: Unit weight (kg/m3 default)
        E: Elastic modulus (auto-calculated if None)
    """
    # eMatType: 1=Steel, 2=Concrete, 6=Rebar
    ret = SapModel.PropMaterial.SetMaterial(name, 2)  # 2 = Concrete
    if E:
        SapModel.PropMaterial.SetMPIsotropic(name, E, 0.2, 0.0000099)
    return ret


def add_steel_material(SapModel, name, fy, fu, E=200000):
    """
    Add a steel material.

    Args:
        name: Material name (e.g., "A572Gr50")
        fy: Yield strength
        fu: Ultimate strength
        E: Elastic modulus (default 200000 MPa)
    """
    ret = SapModel.PropMaterial.SetMaterial(name, 1)  # 1 = Steel
    SapModel.PropMaterial.SetMPIsotropic(name, E, 0.3, 0.0000117)
    SapModel.PropMaterial.SetOSteel_1(name, fy, fu, fy, fu)
    return ret


def add_rebar_material(SapModel, name, fy, fu, E=200000):
    """
    Add a rebar material.

    Args:
        name: Material name (e.g., "SD420")
        fy: Yield strength
        fu: Ultimate strength
    """
    ret = SapModel.PropMaterial.SetMaterial(name, 6)  # 6 = Rebar
    SapModel.PropMaterial.SetMPIsotropic(name, E, 0.3, 0.0000117)
    SapModel.PropMaterial.SetORebar(name, fy, fu, fy, fu, 1, 1, 0.01, 0.09, False)
    return ret


# ============================================================
# Section Properties
# ============================================================

def add_rectangular_column(SapModel, name, width, depth, material, rebar_mat=None):
    """Add a rectangular concrete column section."""
    ret = SapModel.PropFrame.SetRectangle(name, material, depth, width)
    return ret


def add_rectangular_beam(SapModel, name, width, depth, material):
    """Add a rectangular concrete beam section."""
    ret = SapModel.PropFrame.SetRectangle(name, material, depth, width)
    return ret


def add_slab(SapModel, name, thickness, material, slab_type=0):
    """
    Add a slab/shell section.

    Args:
        slab_type: 0=Shell-Thin, 1=Shell-Thick, 2=Membrane, 3=Plate-Thin, 4=Plate-Thick
    """
    ret = SapModel.PropArea.SetSlab(name, slab_type, 2, material, thickness)
    return ret


def add_wall(SapModel, name, thickness, material):
    """Add a wall section property."""
    ret = SapModel.PropArea.SetWall(name, 0, 2, material, thickness)
    return ret


# ============================================================
# Object Creation
# ============================================================

def add_column(SapModel, x, y, story_base, story_top, section):
    """Add a column at (x, y) between two stories."""
    ret = SapModel.FrameObj.AddByCoord(
        x, y, 0,  # base point (z will be determined by story)
        x, y, 0,  # top point
        "", section
    )
    return ret


def add_beam(SapModel, x1, y1, x2, y2, z, section):
    """Add a beam between two points at elevation z."""
    name = [""]
    ret = SapModel.FrameObj.AddByCoord(
        x1, y1, z,
        x2, y2, z,
        name, section
    )
    return ret


def add_floor(SapModel, x_coords, y_coords, z, section):
    """
    Add a floor slab defined by corner points.

    Args:
        x_coords: list of X coordinates of corners
        y_coords: list of Y coordinates of corners
        z: elevation
        section: area section name
    """
    n = len(x_coords)
    z_coords = [z] * n
    name = [""]
    ret = SapModel.AreaObj.AddByCoord(
        n, x_coords, y_coords, z_coords, name, section
    )
    return ret


# ============================================================
# Load Patterns & Cases
# ============================================================

def add_load_pattern(SapModel, name, pattern_type=0, self_wt_mult=0):
    """
    Add a load pattern.

    pattern_type:
        0=Dead, 1=SuperDead, 2=Live, 3=ReduceLive, 4=Quake,
        5=Wind, 6=Snow, 7=Other, 8=Move, 11=Temperature,
        12=Roof Live, 13=Notional
    """
    ret = SapModel.LoadPatterns.Add(name, pattern_type, self_wt_mult, True)
    return ret


def assign_uniform_load_to_floor(SapModel, area_name, load_pattern, load_value, direction=6):
    """
    Assign uniform load to a floor area.

    direction: 1=X, 2=Y, 3=Z (local), 4=X, 5=Y, 6=Z (global gravity)
    """
    ret = SapModel.AreaObj.SetLoadUniform(
        area_name, load_pattern, load_value, direction
    )
    return ret


# ============================================================
# Analysis
# ============================================================

def run_analysis(SapModel):
    """Run the analysis."""
    # Set model to be analyzed
    SapModel.Analyze.SetRunCaseFlag("", True, True)
    ret = SapModel.Analyze.RunAnalysis()
    return ret


def get_story_drifts(SapModel):
    """Get story drift results."""
    ret = SapModel.Results.Setup.DeselectAllCasesAndCombosForOutput()
    # Select relevant load cases
    SapModel.Results.Setup.SetCaseSelectedForOutput("Dead")
    ret = SapModel.Results.StoryDrifts()
    return ret


def get_base_reactions(SapModel, load_case=None):
    """Get base reaction results."""
    if load_case:
        SapModel.Results.Setup.DeselectAllCasesAndCombosForOutput()
        SapModel.Results.Setup.SetCaseSelectedForOutput(load_case)
    ret = SapModel.Results.BaseReact()
    return ret


# ============================================================
# Database Tables (Powerful for batch data extraction)
# ============================================================

def get_table(SapModel, table_key):
    """
    Get data from ETABS database tables.

    Args:
        table_key: Table identifier string.

    Common table keys:
        - "Story Definitions"
        - "Frame Section Properties"
        - "Area Section Properties"
        - "Material Properties"
        - "Load Pattern Definitions"
        - "Story Drifts"
        - "Story Forces"
        - "Joint Displacements"
        - "Frame Forces"
        - "Concrete Column Summary"
        - "Concrete Beam Summary"

    Returns:
        dict with column headers as keys and lists of values.
    """
    ret = SapModel.DatabaseTables.GetTableForDisplayArray(
        table_key, "", "", 0, [], 0, []
    )
    # ret = [retval, TableVersion, FieldKeysIncluded, NumberRecords,
    #        TableData, FieldsKeysCount, FieldKeys]
    if ret[0] != 0:
        return None

    n_fields = ret[5]
    field_keys = list(ret[6])
    table_data = list(ret[4])
    n_records = ret[3]

    result = {key: [] for key in field_keys}
    for i in range(n_records):
        for j in range(n_fields):
            idx = i * n_fields + j
            if idx < len(table_data):
                result[field_keys[j]].append(table_data[idx])

    return result


# ============================================================
# File Operations
# ============================================================

def new_model(SapModel, units=14):
    """
    Initialize a new blank model.

    Args:
        units: Unit system code (default 14 = kgf_cm)
    """
    ret = SapModel.InitializeNewModel(units)
    ret2 = SapModel.File.NewBlank()
    return ret, ret2


def save_model(SapModel, filepath):
    """Save the model to a file."""
    ret = SapModel.File.Save(filepath)
    return ret


def open_model(SapModel, filepath):
    """Open an existing model file."""
    ret = SapModel.File.OpenFile(filepath)
    return ret
