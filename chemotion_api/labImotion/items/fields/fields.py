import re

from chemotion_api.labImotion.items.fields import BaseField
from chemotion_api.labImotion.items.fields.abstract_fields import SystemDefined, Select
from chemotion_api.labImotion.items.fields.sub_fields import SubBaseField, NumberField, TextField as SubTextField, \
    SystemDefinedField as SubSystemDefinedField, LabelField
from chemotion_api.labImotion.items.fields.table_sub_fields import TableSubBaseField, TSDragMolecule, TSDragSample, \
    TSSelect, TSSystemDefined, TSText, TSNumber, TSSelectMulti, TSFormula, TSOpaque
from chemotion_api.labImotion.items.options import FieldType, FieldUnit, get_unit, SubFieldType, SubTableFieldType
from chemotion_api.labImotion.ontology import get_term
from chemotion_api.labImotion.structure import StructureRegistry


class DummyField(BaseField):
    field_type = FieldType.DUMMY

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()


class CheckboxField(BaseField):
    field_type = FieldType.CHECKBOX

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()


class DatetimeField(BaseField):
    field_type = FieldType.DATETIME

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._readonly = False
        self._parse_json()

    @property
    def readonly(self) -> bool:
        return self._readonly

    @readonly.setter
    def readonly(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError(f"readonly {type(value)} not supported")
        self._readonly = value


class DatetimeRangeField(BaseField):
    field_type = FieldType.DATETIME_RANGE

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()


class DragElementField(BaseField):
    field_type = FieldType.DRAG_ELEMENT

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()


class DragMoleculeField(BaseField):
    field_type = FieldType.DRAG_MOLECULE

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()


class DragSampleField(BaseField):
    field_type = FieldType.DRAG_SAMPLE

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()


class FormulaFieldField(BaseField):
    field_type = FieldType.FORMULA_FIELD
    required_fields = ["formula", "decimal", "canAdjust"]

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._formula = ""
        self._decimal = 2
        self._can_adjust = True
        self._parse_json()

    @property
    def canAdjust(self) -> bool:
        return self._can_adjust

    @canAdjust.setter
    def canAdjust(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError(f"canAdjust {type(value)} not supported")
        self._can_adjust = value

    @property
    def decimal(self) -> str:
        return str(self._decimal)

    @decimal.setter
    def decimal(self, value: str | int):
        if isinstance(value, int):
            value = str(value)
        if re.match(r"^[0-9]+$", value) is None:
            raise TypeError(f"decimal {type(value)} not supported. Must be a positive integer as string.")
        self._decimal = value

    @property
    def formula(self) -> str:
        return self._formula

    @formula.setter
    def formula(self, value: str):
        structure = self._sr.get_structure()[self._layer_key]
        if not isinstance(value, str):
            raise TypeError(f"formula {type(value)} not supported")
        for variable in re.split(r'[+\-*/]', value):
            variable = variable.strip('() ')
            try:
                float(variable)
            except ValueError:
                if structure.get(variable) not in [FieldType.INTEGER, FieldType.SYSTEM_DEFINED]:
                    raise ValueError(f"Only numbers (integer or floating '12.3'), field names of {FieldType.INTEGER} or {FieldType.SYSTEM_DEFINED} in the same layer or operations like addition (+), subtraction (-), multiplication (*), and division (/)")

        self._formula = value


class InputGroupField(BaseField):
    field_type = FieldType.INPUT_GROUP

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._sub_fields = []
        self._parse_json()

    @property
    def sub_fields(self) -> list:
        return self._sub_fields

    @sub_fields.setter
    def sub_fields(self, value: list):
        new_val = []
        for entry in value:
            if isinstance(entry, SubBaseField):
                new_val.append(entry)
            elif isinstance(entry, dict) and entry.get('type') in SubFieldType.list():
                sf_type = SubFieldType(entry['type'])
                new_val.append(self._factory_subfield(sf_type, entry))
            else:
                raise TypeError("Value entries must be of type SubBaseField or dict")

        self._sub_fields = new_val



    def add_subfield(self, sf_type: SubFieldType) -> NumberField | SubTextField | SubSystemDefinedField | LabelField:
        self.sub_fields.append(self._factory_subfield(sf_type))
        return self.sub_fields[-1]

    def _factory_subfield(self, sf_type: SubFieldType,
                          data=None) -> NumberField | SubTextField | SubSystemDefinedField | LabelField:
        if data is None:
            data = {}
        if sf_type == SubFieldType.TEXT:
            return SubTextField(self._sr, self._layer_key, data)
        elif sf_type == SubFieldType.LABEL:
            return LabelField(self._sr, self._layer_key, data)
        elif sf_type == SubFieldType.NUMBER:
            return NumberField(self._sr, self._layer_key, data)
        elif sf_type == SubFieldType.SYSTEM_DEFINED:
            return SubSystemDefinedField(self._sr, self._layer_key, data)


class IntegerField(BaseField):
    field_type = FieldType.INTEGER

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()


class SelectField(BaseField, Select):
    field_type = FieldType.SELECT
    required_fields = ['option_layers']

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        Select.__init__(self, sr, json_data)
        self._parse_json()


class SelectMultiField(BaseField, Select):
    """A multi-select field.

    ``select-multi`` behaves like ``select`` on the wire (it carries ``option_layers``), but the
    LabIMotion gem deliberately does not declare it in ``field_type.rb`` — see the note on
    :attr:`~chemotion_api.labImotion.items.options.FieldType.SELECT_MULTI`. The server emits it
    regardless, so it needs a real class here rather than a passthrough.
    """
    field_type = FieldType.SELECT_MULTI
    required_fields = ['option_layers']

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        Select.__init__(self, sr, json_data)
        self._parse_json()


class OpaqueField(BaseField):
    """Fallback for a field type this client has no dedicated class for.

    Keeps the payload intact so the klass loads AND round-trips, instead of making the whole
    element unreadable. Used for gem-declared types we do not model (``wf-next``,
    ``sys-reaction``, ``drag``, ``drag_reaction``) and for anything LabIMotion adds later.

    Round-tripping is the point, and it is not free: :meth:`BaseField.to_dict` rebuilds a field
    from its declared required/optional keys only, and this class declares none — so without the
    override below, loading a klass with an unmodelled field and calling ``save()`` would POST it
    back **stripped of every type-specific key**, silently destroying that data on the server.
    Before this class existed such a klass raised on load, which at least could not delete
    anything.
    """

    def to_dict(self) -> dict:
        """The rebuilt field merged *over* the original payload, so unknown keys survive a save.

        :return: the field as a ``dict``, retaining every key the server sent.
        """
        return dict(self._json_data) | super().to_dict()

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        # field_type is per-instance here: one class stands in for several wire types, and for
        # types with no enum member at all — in which case the raw string is kept, so to_dict()
        # still round-trips what the server sent.
        raw_type = json_data.get('type')
        try:
            self.field_type = FieldType(raw_type)
        except ValueError:
            self.field_type = raw_type
        super().__init__(sr, layer_key, json_data)
        self._parse_json()


class SystemDefinedField(BaseField, SystemDefined):
    field_type = FieldType.SYSTEM_DEFINED
    required_fields = ['option_layers', 'value_system']
    optional_fields = ['value_system_base']

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        SystemDefined.__init__(self, json_data)
        self._value_system_base: str | None = None
        self._parse_json()

    @property
    def value_system_base(self) -> str | None:
        """The base unit of the field, a unit key of ``option_layers``, or None.

        The ELN's template designer fills it in for system-defined fields that have none
        (chem-generic-ui backfills it from ``value_system``); this client keeps what is stored and
        never invents it.
        """
        return self._value_system_base

    @value_system_base.setter
    def value_system_base(self, value: str | None):
        if value is None:
            self._value_system_base = None
            return
        if not isinstance(value, str):
            raise TypeError(f"value_system_base {type(value)} not supported")
        available_units = get_unit(self.option_layers)
        if value not in available_units:
            raise ValueError(f"value_system_base {value} must be in {available_units}")
        self._value_system_base = value


class NumericField(BaseField):
    """The ``number`` field type: a number with optional ``numeric`` settings.

    ``numeric`` is ``{'decimals': int >= 0, 'min': number | str, 'max': number | str}``, every key
    optional, as the ELN's template designer stores it.
    """
    field_type = FieldType.NUMBER
    optional_fields = ['numeric']
    _NUMERIC_KEYS = ('decimals', 'min', 'max')

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._numeric: dict | None = None
        self._parse_json()

    @property
    def numeric(self) -> dict | None:
        return self._numeric

    @numeric.setter
    def numeric(self, value: dict | None):
        if value is None:
            self._numeric = None
            return
        if not isinstance(value, dict):
            raise TypeError(f"numeric {type(value)} not supported")
        unknown = set(value) - set(self._NUMERIC_KEYS)
        if unknown:
            raise ValueError(f"numeric takes only {list(self._NUMERIC_KEYS)}, not {sorted(unknown)}")
        decimals = value.get('decimals')
        if decimals is not None:
            if isinstance(decimals, bool) or not isinstance(decimals, int):
                raise TypeError(f"numeric decimals {type(decimals)} not supported, use an int")
            if decimals < 0:
                raise ValueError("numeric decimals must be 0 or more")
        for key in ('min', 'max'):
            bound = value.get(key)
            if bound is not None and (isinstance(bound, bool) or not isinstance(bound, int | float | str)):
                raise TypeError(f"numeric {key} {type(bound)} not supported, use a number or str")
        self._numeric = dict(value)


class OntologySelectField(BaseField):
    """The ``ontology-select`` field type: a choice among the terms below ``ontology_term``.

    The ELN's template designer stores the root term as ``{'value': <TIB term id>, 'label': <label>}``,
    e.g. ``{'value': 'obi:class:http://purl.obolibrary.org/obo/OBI_0000070', 'label': 'assay'}``.
    """
    field_type = FieldType.ONTOLOGY_SELECT
    optional_fields = ['ontology_term']

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        # Kept as stored, not through the setter: a string would be looked up online while
        # loading, and the designer also reads the older string forms ('<onto>|<iri>', an IRI).
        self._ontology_term: dict | str | None = json_data.get('ontology_term') or None
        self._json_data = {k: v for k, v in json_data.items() if k != 'ontology_term'}
        self._parse_json()
        self._json_data = json_data

    @property
    def ontology_term(self) -> dict | str | None:
        """The root term, or None. It can be set to a term ID ('OBI:0000070', a short form or the
        IRI, looked up in the TIB Terminology Service like :attr:`ontology`), to a term dict (e.g.
        from :meth:`GenericManager.search_ontology_terms`), to ``{'value', 'label'}`` as stored, or
        to None to remove it. A plain string read from the server is kept as it is."""
        return self._ontology_term

    @ontology_term.setter
    def ontology_term(self, value: dict | str | None):
        if value is None or value == {}:
            self._ontology_term = None
        elif isinstance(value, str):
            term = get_term(value)
            if term is None:
                raise ValueError(f"unknown ontology term {value!r}")
            self._ontology_term = {'value': term['id'], 'label': term.get('label') or term['id']}
        elif isinstance(value, dict):
            if 'id' in value:       # a TIB term
                self._ontology_term = {'value': value['id'], 'label': value.get('label') or value['id']}
            elif 'value' in value:  # as the designer stores it
                self._ontology_term = {'value': value['value'], 'label': value.get('label') or value['value']}
            else:
                raise ValueError("ontology_term needs an 'id' (a term) or a 'value' (as stored)")
        else:
            raise TypeError(f"ontology_term {type(value)} not supported")


class TableField(BaseField):
    field_type = FieldType.TABLE

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._sub_fields = []
        self._parse_json()

    @property
    def sub_fields(self) -> list:
        return self._sub_fields

    @sub_fields.setter
    def sub_fields(self, value: list):
        new_val = []
        for entry in value:
            if isinstance(entry, TableSubBaseField):
                new_val.append(entry)
            elif isinstance(entry, dict) and entry.get('type') in SubTableFieldType.list():
                sf_type = SubTableFieldType(entry['type'])
                new_val.append(self._factory_subfield(sf_type, entry))
            elif isinstance(entry, dict) and isinstance(entry.get('type'), str):
                # A column type this client does not know (issue #61): keep that column as it is,
                # rather than leaving the whole table untyped.
                new_val.append(TSOpaque(self._sr, self._layer_key, entry))
            else:
                raise TypeError("Value entries must be of type SubBaseField or dict")

        self._sub_fields = new_val



    def add_subfield(self, sf_type: SubTableFieldType, col_name: str) -> TableSubBaseField:
        self.sub_fields.append(self._factory_subfield(sf_type, {'col_name': col_name}))
        return self.sub_fields[-1]

    def _factory_subfield(self, sf_type: SubTableFieldType,
                          data=None) -> TableSubBaseField:
        if data is None:
            data = {}
        if sf_type == SubTableFieldType.DRAG_MOLECULE:
            return TSDragMolecule(self._sr, self._layer_key, data)
        elif sf_type == SubTableFieldType.DRAG_SAMPLE:
            return TSDragSample(self._sr, self._layer_key, data)
        elif sf_type == SubTableFieldType.SELECT:
            return TSSelect(self._sr, self._layer_key, data)
        elif sf_type == SubTableFieldType.SYSTEM_DEFINED:
            return TSSystemDefined(self._sr, self._layer_key, data)
        elif sf_type == SubTableFieldType.TEXT:
            return TSText(self._sr, self._layer_key, data)
        elif sf_type == SubTableFieldType.NUMBER:
            return TSNumber(self._sr, self._layer_key, data)
        elif sf_type == SubTableFieldType.SELECT_MULTI:
            return TSSelectMulti(self._sr, self._layer_key, data)
        elif sf_type == SubTableFieldType.FORMULA_FIELD:
            return TSFormula(self._sr, self._layer_key, data)


class TextFormulaField(BaseField):
    field_type = FieldType.TEXT_FORMULA

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()


class TextField(BaseField):
    field_type = FieldType.TEXT

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()


class TextareaField(BaseField):
    field_type = FieldType.TEXTAREA

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()


class UploadField(BaseField):
    field_type = FieldType.UPLOAD

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()
