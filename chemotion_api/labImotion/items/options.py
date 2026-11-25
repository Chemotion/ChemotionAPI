from enum import Enum

class ListableEnum(Enum):
    """An enum with :meth:`list`."""
    @classmethod
    def list(cls):
        """The values of all members."""
        return list(map(lambda c: c.value, cls))

class SaveActionType(Enum):
    """What ``klass.save()`` does with the template: ``DRAFT`` stores it, ``MINOR`` releases it as the
    next minor version (e.g. 1.0 -> 1.1), ``MAJOR`` as the next major version (e.g. 0.1 -> 1.0). New
    elements always use the latest release."""
    DRAFT = "draft"
    MINOR = "minor"
    MAJOR = "major"

class ElementType(ListableEnum):
    """The three kinds of LabIMotion klass: element, segment and dataset."""
    SEGMENT = 'SegmentKlass'
    ELEMENT = 'ElementKlass'
    DATASET = 'DatasetKlass'

class SubFieldType(ListableEnum):
    """The part types of an input-group field (``InputGroupField.add_subfield``)."""
    NUMBER = 'number'
    LABEL = 'label'
    TEXT = 'text'
    SYSTEM_DEFINED = 'system-defined'


class SubTableFieldType(ListableEnum):
    """The column types of a table field, as the template designer offers them
    (chem-generic-ui 2.3.2: ``i42`` plus ``drag_sample``)."""
    DRAG_MOLECULE = "drag_molecule"
    DRAG_SAMPLE = "drag_sample"
    FORMULA_FIELD = "formula-field"
    NUMBER = "number"
    SELECT = "select"
    SELECT_MULTI = "select-multi"
    SYSTEM_DEFINED = 'system-defined'
    TEXT = 'text'


class FieldType(ListableEnum):
    """The field types of a template layer, as stored in a field's ``type``.

    :meth:`~chemotion_api.labImotion.items.layer.Layer.add_field` creates every member. ``DATE``,
    ``WF_NEXT``, ``SYS_REACTION``, ``DRAG`` and ``DRAG_REACTION`` get a field without type-specific
    settings (:class:`~chemotion_api.labImotion.items.fields.fields.OpaqueField`); loaded fields of these
    types keep all their keys. ``INTEGER`` creates a ``number`` field (see ``add_field``).
    """
    DUMMY = 'dummy'
    CHECKBOX = "checkbox"
    DATETIME = "datetime"
    DATETIME_RANGE = "datetime-range"
    DRAG_ELEMENT = "drag_element"
    DRAG_MOLECULE = "drag_molecule"
    DRAG_SAMPLE = "drag_sample"
    FORMULA_FIELD = "formula-field"
    INPUT_GROUP = "input-group"
    #: Deprecated by the template designer ("Integer (deprecated, use Number)"), which turns every
    #: ``integer`` field into ``number`` when it saves a template. Kept so such templates load.
    INTEGER = "integer"
    #: The designer's numeric field; its rounding and range are in ``numeric``.
    NUMBER = "number"
    #: A select whose options are the children of an ontology term (``ontology_term``).
    ONTOLOGY_SELECT = "ontology-select"
    SELECT = "select"
    #: Emitted by the server but deliberately NOT declared in the gem's field_type.rb
    #: ("`select-multi` deliberately has no Labimotion::FieldType constant" —
    #: labimotion/libs/element_variation_column_set.rb). Do not delete when re-syncing
    #: from the gem: regenerating from field_type.rb alone would drop it again.
    SELECT_MULTI = "select-multi"
    #: Declared by the gem's field_type.rb but previously missing here.
    DATE = "date"
    WF_NEXT = "wf-next"
    SYS_REACTION = "sys-reaction"
    DRAG = "drag"
    DRAG_REACTION = "drag_reaction"
    SYSTEM_DEFINED = "system-defined"
    TABLE = "table"
    TEXT_FORMULA = 'text-formula'
    TEXT = 'text'
    TEXTAREA = 'textarea'
    UPLOAD = 'upload'


class ConditionOperator(ListableEnum):
    """How the restrictions of a field or layer are combined: shown if all (``MATCH_ALL``), at least one
    (``MATCH_ONE``, the default) or none (``MATCH_NONE``) of them match."""
    MATCH_ALL = 9
    MATCH_ONE = 1
    MATCH_NONE = 0


class FieldUnit(ListableEnum):
    """The unit types of system-defined fields, sub-fields and columns (their ``option_layers``). The
    units of each type are in :data:`UNITS`; the first one is the default."""
    ACCELERATION = "acceleration"
    AGITATION = "agitation"
    AMOUNT_ENZYME = "amount_enzyme"
    AMOUNT_SUBSTANCE = "amount_substance"
    AREAL_DENSITY = "areal_density"
    MOLARITY = "molarity"
    CHEM_DISTANCES = "chem_distances"
    CONCENTRATION = "concentration"
    CONDUCTIVITY = "conductivity"
    CURRENCY = "currency"
    CURRENT = "current"
    C_RATE = "c_rate"
    DEGREE = "degree"
    DENSITY = "density"
    DIMENSIONLESS_CONCENTRATION = "dimensionless_concentration"
    DURATION = "duration"
    ELASTIC_MODULUS = "elastic_modulus"
    ELECTRIC_CHARGE_C = "electric_charge_c"
    ELECTRIC_CHARGE_MOL = "electric_charge_mol"
    ELECTRIC_FIELD = "electric_field"
    ELECTRICAL_CAPACITY = "electrical_capacity"
    ELECTRICAL_POTENTIAL = "electrical_potential"
    ENERGY = "energy"
    FREE_ENERGY = "free_energy"
    ENZYME_ACTIVITY = "enzyme_activity"
    FARADAY = "faraday"
    FLOW_RATE = "flow_rate"
    FREQUENCY = "frequency"
    HEATING_RATE = "heating_rate"
    LENGTH = "length"
    MAGNETIC_FLUX_DENSITY = "magnetic_flux_density"
    MASS = "mass"
    MASS_FLOW = "mass_flow"
    MASS_FRACTION = "mass_fraction"
    MASS_LOADING = "mass_loading"
    MASS_MOLECULE = "mass_molecule"
    MOLAR_CONDUCTIVITY = "molar_conductivity"
    MOLAR_ENTROPY = "molar_entropy"
    MOLECULAR_WEIGHT = "molecular_weight"
    PERCENTAGE = "percentage"
    POWER = "power"
    PRESSURE = "pressure"
    PROCESS_RATE = "process_rate"
    RATE_CONSTANT = "rate_constant"
    REACTION_RATE = "reaction_rate"
    RESOLUTION = "resolution"
    SCAN_RATE = "scan_rate"
    SPACE_TIME_YIELD = "space_time_yield"
    SPECIFIC_CURRENT = "specific_current"
    SPECIFIC_ELECTRICAL_CAPACITY = "specific_electrical_capacity"
    SPECIFIC_SURFACE_AREA = "specific_surface_area"
    SPECIFIC_VOLUME = "specific_volume"
    SPEED = "speed"
    SUBATOMIC_LENGTH = "subatomic_length"
    SURFACE = "surface"
    TEMPERATURE = "temperature"
    TENSILE_FORCE = "tensile_force"
    TENSILE_STRESS = "tensile_stress"
    TURNOVER_NUMBER = "turnover_number"
    VISCOSITY = "viscosity"
    KINEMATIC_VISCOSITY = "kinematic_viscosity"
    VOLTAGE = "voltage"
    VOLUMES = "volumes"
    VOLUME_FRACTION = "volume_fraction"
    VOLUMES_METRIC = "volumes_metric"


class LayerColor(ListableEnum):
    """The heading colors of a layer, named after the designer's color: ``BLUE`` is stored as
    ``'primary'``, ``GREEN`` as ``'success'`` and so on."""
    NONE = "none"
    BLUE = "primary"
    BLUE_LIGHT = "info"
    GREEN = "success"
    GREY = "default"
    RED = "danger"
    ORANGE = "warning"

#: Allowed unit keys per unit type. Mirrors ``lib/labimotion/utils/units.rb`` from the
#: LabIMotion gem (2.3.2, the version ELN v4.0.0 pins) — verified with
#: `scripts/sync_labimotion_units.py 2.3.2 --check`. Note the test stack's RC image still
#: runs 2.3.0.rc6, which lacks mass_flow and space_time_yield, so those two cannot be
#: exercised there. Regenerate from the gem when the ELN bumps LabIMotion; see
#: ``docs/`` and the note on :func:`get_unit`.
UNITS: dict[FieldUnit, list[str]] = {
    FieldUnit.ACCELERATION: ["mm_s2"],
    FieldUnit.AGITATION: ["rpm"],
    FieldUnit.AMOUNT_ENZYME: ["u", "mu", "kat", "mkat", "µkat", "nkat"],
    FieldUnit.AMOUNT_SUBSTANCE: ["mol", "mmol", "umol", "nmol", "pmol"],
    FieldUnit.AREAL_DENSITY: ["kg_m2", "t_m2", "kg_cm2", "g_m2"],
    FieldUnit.MOLARITY: ["mol_l", "mmol_l", "umol_l", "nmol_l", "pmol_l"],
    FieldUnit.CHEM_DISTANCES: ["angstrom"],
    FieldUnit.CONCENTRATION: ["ng_l", "mg_l", "g_l"],
    FieldUnit.CONDUCTIVITY: ["s_m", "ms_cm"],
    FieldUnit.CURRENCY: ["eur", "chf", "gbp", "usd", "jpy"],
    FieldUnit.CURRENT: ["A", "mA", "uA", "nA"],
    FieldUnit.C_RATE: ["c_h"],
    FieldUnit.DEGREE: ["degree"],
    FieldUnit.DENSITY: ["g_cm3", "kg_l"],
    FieldUnit.DIMENSIONLESS_CONCENTRATION: ["ppm", "ppb"],
    FieldUnit.DURATION: ["d", "h", "min", "s", "y"],
    FieldUnit.ELASTIC_MODULUS: ["m_pa", "k_pa", "pa"],
    FieldUnit.ELECTRIC_CHARGE_C: ["ec_c"],
    FieldUnit.ELECTRIC_CHARGE_MOL: ["ec_mol"],
    FieldUnit.ELECTRIC_FIELD: ["v_m"],
    FieldUnit.ELECTRICAL_CAPACITY: ["mah", "ah", "as", "c"],
    FieldUnit.ELECTRICAL_POTENTIAL: ["v_re", "mv_re", "mv_ce", "v_ce"],
    FieldUnit.ENERGY: ["eV", "keV", "j", "k_j", "kWh"],
    FieldUnit.FREE_ENERGY: ["kj_mol"],
    FieldUnit.ENZYME_ACTIVITY: ["u_l", "u_ml", "u_g", "u_mg"],
    FieldUnit.FARADAY: ["faraday"],
    FieldUnit.FLOW_RATE: ["l_m", "ml_min", "ul_min", "ml_h"],
    FieldUnit.FREQUENCY: ["hz", "khz", "mhz"],
    FieldUnit.HEATING_RATE: ["k_min", "k_s", "k_h", "degc_min", "degc_s", "degc_h"],
    FieldUnit.LENGTH: ["mm", "cm", "m"],
    FieldUnit.MAGNETIC_FLUX_DENSITY: ["T"],
    FieldUnit.MASS: ["g", "mg", "ug", "kg"],
    FieldUnit.MASS_FLOW: ["g_min", "kg_h", "kg_s", "g_s", "mg_s"],
    FieldUnit.MASS_FRACTION: ["wt_p"],
    FieldUnit.MASS_LOADING: ["g_cm2", "mg_cm2"],
    FieldUnit.MASS_MOLECULE: ["dalton", "kilo_dalton"],
    FieldUnit.MOLAR_CONDUCTIVITY: ["s_cm2_mol"],
    FieldUnit.MOLAR_ENTROPY: ["j_mol_k"],
    FieldUnit.MOLECULAR_WEIGHT: ["g_mol"],
    FieldUnit.PERCENTAGE: ["p"],
    FieldUnit.POWER: ["watt"],
    FieldUnit.PRESSURE: ["atm", "pa", "kpa", "mpa", "hpa", "torr", "bar", "mbar"],
    FieldUnit.PROCESS_RATE: ["1_s", "1_min", "1_h"],
    FieldUnit.RATE_CONSTANT: ["1_m_s"],
    FieldUnit.REACTION_RATE: ["mol_lmin", "mol_lsec"],
    FieldUnit.RESOLUTION: ["px", "mp"],
    FieldUnit.SCAN_RATE: ["mv_s", "v_s"],
    FieldUnit.SPACE_TIME_YIELD: ["kg_m3_d", "kg_m3_h", "g_l_h", "mg_ml_h", "g_l_min", "g_m3_s"],
    FieldUnit.SPECIFIC_CURRENT: ["ma_g", "a_g", "ma_cm2", "a_cm2", "a_mm2"],
    FieldUnit.SPECIFIC_ELECTRICAL_CAPACITY: ["mah_g", "ah_g"],
    FieldUnit.SPECIFIC_SURFACE_AREA: ["m2_g"],
    FieldUnit.SPECIFIC_VOLUME: ["cm3_g"],
    FieldUnit.SPEED: ["cm_s", "mm_s", "um_m", "nm_m", "cm_h", "mm_h"],
    FieldUnit.SUBATOMIC_LENGTH: ["um", "nm", "pm"],
    FieldUnit.SURFACE: ["a_2", "um_2", "mm_2", "cm_2"],
    FieldUnit.TEMPERATURE: ["C", "F", "K"],
    FieldUnit.TENSILE_FORCE: ["n", "kn", "mn"],
    FieldUnit.TENSILE_STRESS: ["n_cm2", "n_mm2"],
    FieldUnit.TURNOVER_NUMBER: ["1_s", "1_m"],
    FieldUnit.VISCOSITY: ["pas", "mpas"],
    FieldUnit.KINEMATIC_VISCOSITY: ["m2_s"],
    FieldUnit.VOLTAGE: ["mv", "v", "kv"],
    FieldUnit.VOLUMES: ["l", "ml", "ul", "nl"],
    FieldUnit.VOLUME_FRACTION: ["vol_p"],
    FieldUnit.VOLUMES_METRIC: ["cm3", "mm3", "m3"],
}

def get_unit(field_unit: FieldUnit) -> list[str]:
    return UNITS.get(field_unit, [])
