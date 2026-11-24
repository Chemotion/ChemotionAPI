import re
import uuid

from chemotion_api.labImotion.items.fields import BaseField
from chemotion_api.labImotion.items.fields.abstract_fields import SystemDefined, Select, Numeric
from chemotion_api.labImotion.items.fields.sub_fields import SubBaseField, NumberField as SubNumberField, \
    TextField as SubTextField, SystemDefinedField as SubSystemDefinedField, LabelField, OpaqueSubField
from chemotion_api.labImotion.items.fields.table_sub_fields import TableSubBaseField, TSDragMolecule, TSDragSample, \
    TSSelect, TSSystemDefined, TSText, TSNumber, TSSelectMulti, TSFormulaField
from chemotion_api.labImotion.items.options import FieldType, FieldUnit, get_unit, SubFieldType, SubTableFieldType
from chemotion_api.labImotion.ontology import get_term
from chemotion_api.labImotion.structure import StructureRegistry

#: Separates a table field and its column in a text-formula reference (chem-generic-ui ``SEPARATOR_TAG``).
TABLE_COLUMN_SEPARATOR = '[@@]'


class Placeholder:
    """The placeholder of an input ("Placeholder" in the designer: text, integer and number fields)."""
    _placeholder: str | None = None

    @property
    def placeholder(self) -> str | None:
        """The placeholder shown in the empty input, or None."""
        return self._placeholder

    @placeholder.setter
    def placeholder(self, value: str | None):
        if value is not None and not isinstance(value, str):
            raise TypeError(f"placeholder {type(value)} not supported")
        self._placeholder = value


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
    """A date and time. :attr:`readonly` is saved with the template."""
    field_type = FieldType.DATETIME

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()


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
    #: The field types a formula can use (chem-generic-ui ``WZ``).
    operand_types = (FieldType.INTEGER, FieldType.NUMBER, FieldType.SYSTEM_DEFINED)

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
                if structure.get(variable) not in self.operand_types:
                    raise ValueError(f"Only numbers (integer or floating '12.3'), field names of "
                                     f"{', '.join(t.value for t in self.operand_types)} fields in the same layer "
                                     f"or operations like addition (+), subtraction (-), multiplication (*), and "
                                     f"division (/)")

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
            elif isinstance(entry, dict):
                new_val.append(OpaqueSubField(self._sr, self._layer_key, entry))
            else:
                raise TypeError("Value entries must be of type SubBaseField or dict")

        self._sub_fields = new_val



    def add_subfield(self, sf_type: SubFieldType) -> SubNumberField | SubTextField | SubSystemDefinedField | LabelField:
        self.sub_fields.append(self._factory_subfield(sf_type))
        return self.sub_fields[-1]

    def _factory_subfield(self, sf_type: SubFieldType,
                          data=None) -> SubNumberField | SubTextField | SubSystemDefinedField | LabelField:
        if data is None:
            data = {}
        if sf_type == SubFieldType.TEXT:
            return SubTextField(self._sr, self._layer_key, data)
        elif sf_type == SubFieldType.LABEL:
            return LabelField(self._sr, self._layer_key, data)
        elif sf_type == SubFieldType.NUMBER:
            return SubNumberField(self._sr, self._layer_key, data)
        elif sf_type == SubFieldType.SYSTEM_DEFINED:
            return SubSystemDefinedField(self._sr, self._layer_key, data)


class IntegerField(BaseField, Numeric, Placeholder):
    """The deprecated integer field. Templates with it still load and save as they are; new number fields
    are :class:`NumberField` (see :meth:`chemotion_api.labImotion.items.layer.Layer.add_field`)."""
    field_type = FieldType.INTEGER
    optional_fields = ['numeric', 'placeholder']

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        Numeric.__init__(self, json_data)
        self._parse_json()


class NumberField(BaseField, Numeric, Placeholder):
    """A number ("Number" in the designer). ``numeric`` holds its rounding and range; a new field gets
    ``{decimals: 0, min: '', max: ''}`` as in the designer. See :meth:`Numeric.set_numeric`."""
    field_type = FieldType.NUMBER
    required_fields = ['numeric']
    optional_fields = ['placeholder']

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        Numeric.__init__(self, json_data)
        if self._numeric is None:
            self._numeric = {'decimals': 0, 'min': '', 'max': ''}
        self._parse_json()


class OntologySelectField(BaseField):
    """A select whose options are the sub-terms of an ontology term (``ontology_term``), looked up in the
    TIB Terminology Service by the element form."""
    field_type = FieldType.ONTOLOGY_SELECT
    optional_fields = ['ontology_term']

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._ontology_term: dict | None = None
        self._parse_json()

    @property
    def ontology_term(self) -> dict | None:
        """
        The root term of the options, stored as the designer's term picker stores it:
        ``{'value': <term id of the terminology service, e.g. 'chmo:class:http://purl...CHMO_0000228'>,
        'label': <term label>}``. It can be set to such a dict, to a term dict of
        :func:`chemotion_api.labImotion.ontology.search_terms`, to a term ID ('CHMO:0000228'), which is looked
        up, or to None.
        """
        return self._ontology_term

    @ontology_term.setter
    def ontology_term(self, value: dict | str | None):
        if isinstance(value, str):
            value = get_term(value)
        if value is None:
            self._ontology_term = None
        elif isinstance(value, dict) and 'value' in value:
            self._ontology_term = value
        elif isinstance(value, dict) and value.get('id'):
            self._ontology_term = {'value': value['id'], 'label': value.get('label') or value['id']}
        else:
            raise TypeError("ontology_term must be a term dict (with 'id'), {'value', 'label'}, a term ID or None")


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
    ``sys-reaction``, ``drag``, ``drag_reaction``, ``date``) and for anything LabIMotion adds later.
    Its type-specific keys survive a save because :meth:`BaseField.to_dict` writes over the loaded
    payload.
    """

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

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        SystemDefined.__init__(self, json_data)
        self._parse_json()


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
            if isinstance(entry, (TableSubBaseField, OpaqueSubField)):
                new_val.append(entry)
            elif isinstance(entry, dict) and entry.get('type') in SubTableFieldType.list():
                sf_type = SubTableFieldType(entry['type'])
                new_val.append(self._factory_subfield(sf_type, entry))
            elif isinstance(entry, dict):
                # A column type this client does not model (e.g. LabIMotion 2.4's drag_element): kept as is.
                new_val.append(OpaqueSubField(self._sr, self._layer_key, entry))
            else:
                raise TypeError("Value entries must be of type SubBaseField or dict")

        self._sub_fields = new_val



    def add_subfield(self, sf_type: SubTableFieldType, col_name: str) -> TableSubBaseField:
        """
        Adds a column, set up as the designer sets up a new column of that type.

        :param sf_type: the column type
        :param col_name: the column heading
        :return: the new column
        """
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
            return TSFormulaField(self._sr, self._layer_key, data)
        raise ValueError(f"unknown column type {sf_type}")


class TextFormulaField(BaseField):
    """Shows the values of text fields joined together. The joined fields are :attr:`text_sub_fields`
    (``[{id, layer, field, separator}]``); add them with :meth:`add_text_sub_field`."""
    field_type = FieldType.TEXT_FORMULA

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._parse_json()

    def add_text_sub_field(self, field: BaseField | str, layer: str | None = None, separator: str = '.') -> dict:
        """
        Appends a text field to the joined fields.

        >>> joined.add_text_sub_field(first_name, separator=' ')
        >>> joined.add_text_sub_field('strain', layer='cultivation')

        :param field: the text field, or its key (field name). A table column is given as
            ``'<table field>[@@]<column id>'``
        :param layer: the key of the field's layer (default: the field's own layer, or this field's layer for a key)
        :param separator: the text put after the value (the designer's default is '.')
        :return: the new entry

        :raises ValueError: if the field is not a text field of the template
        """
        if isinstance(field, BaseField):
            layer = layer or field.layer_key
            field = field.field
        layer = layer or self._layer_key
        if not isinstance(field, str) or not isinstance(layer, str) or not isinstance(separator, str):
            raise TypeError("field, layer and separator must be strings")
        if TABLE_COLUMN_SEPARATOR not in field:
            field_type = self._sr.get_structure().get(layer, {}).get(field)
            if field_type != FieldType.TEXT:
                raise ValueError(f'"{field}" in layer "{layer}" is not a text field (found {field_type})')
        entry = {'id': str(uuid.uuid4()), 'layer': layer, 'field': field, 'separator': separator}
        self.text_sub_fields = self.text_sub_fields + [entry]
        return entry


class TextField(BaseField, Placeholder):
    """A one-line text. Besides the common attributes it has a :attr:`placeholder`; with
    :attr:`readonly` the form shows the placeholder as plain text."""
    field_type = FieldType.TEXT
    optional_fields = ['placeholder']

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
