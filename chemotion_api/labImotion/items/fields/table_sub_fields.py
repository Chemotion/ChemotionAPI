import re

from chemotion_api.labImotion.items.fields.abstract_fields import SystemDefined, Select, Numeric
from chemotion_api.labImotion.items.fields.sub_fields import SubBaseField
from chemotion_api.labImotion.items.options import SubTableFieldType
from chemotion_api.labImotion.structure import StructureRegistry

class TableSubBaseField(SubBaseField):
    """A column of a table field: :attr:`id`, :attr:`col_name` (the heading) and the type settings of its
    subclass. Columns are added with
    :meth:`chemotion_api.labImotion.items.fields.fields.TableField.add_subfield`."""
    _default_required_fields = ["id", "col_name", "field_type", "value"]
    required_fields = []

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._col_name = json_data.get("col_name", "")

    @property
    def col_name(self) -> str:
        """The column heading. Rows of an element address their cells by it."""
        return self._col_name
    
    @col_name.setter
    def col_name(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"col_name {type(value)} not supported")
        self._col_name = value


class _TSDrag(TableSubBaseField):
    """A drag column; ``value`` lists the extra columns shown for the dropped item, ';'-separated."""

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        if 'value' in json_data:
            # Normalised only when set from user code: a loaded template is saved as it was.
            self._value = json_data['value']


class TSDragMolecule(_TSDrag):
    """A molecule column. :attr:`value` lists the extra columns shown for the dropped molecule
    (``'inchikey;smiles;iupac;molecular_weight;'``); set it with :meth:`set_sample_display`."""
    field_type = SubTableFieldType.DRAG_MOLECULE

    @property
    def value(self) -> str:
        """The extra columns, e.g. ``'inchikey;iupac;'``. When set, unknown names are dropped."""
        return self._value

    @value.setter
    def value(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"value {type(value)} not supported")
        text_display = []
        value_split = value.split(';')
        if 'inchikey' in value_split:
            text_display.append("inchikey;")
        if 'smiles' in value_split:
            text_display.append("smiles;")
        if 'iupac' in value_split:
            text_display.append("iupac;")
        if 'molecular_weight' in value_split:
            text_display.append("molecular_weight;")
        self._value = ''.join(text_display)

    def set_sample_display(self, inchikey: bool, smiles: bool, iupac: bool, molecular_weight: bool):
        """Chooses the extra columns shown for the dropped molecule."""
        text_display = []
        if inchikey:
            text_display.append("inchikey;")
        if smiles:
            text_display.append("smiles;")
        if iupac:
            text_display.append("iupac;")
        if molecular_weight:
            text_display.append("molecular_weight;")
        self.value = ''.join(text_display)


class TSDragSample(_TSDrag):
    """A sample column. :attr:`value` lists the extra columns shown for the dropped sample
    (``'name;external_label;molecular_weight;'``); set it with :meth:`set_sample_display`."""
    field_type = SubTableFieldType.DRAG_SAMPLE

    @property
    def value(self) -> str:
        """The extra columns, e.g. ``'name;molecular_weight;'``. When set, unknown names are dropped."""
        return self._value

    @value.setter
    def value(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"value {type(value)} not supported")
        text_display = []
        value_split = value.split(';')
        if 'name' in value_split:
            text_display.append("name;")
        if 'external_label' in value_split:
            text_display.append("external_label;")
        if 'molecular_weight' in value_split:
            text_display.append("molecular_weight;")
        # Built the filtered token list and then threw it away: ''.join(value) just rebuilds the
        # raw input string, so unrecognised tokens survived and terminators were never normalised.
        self._value = ''.join(text_display)

    def set_sample_display(self, name: bool, external_label: bool, molecular_weight: bool):
        """Chooses the extra columns shown for the dropped sample."""
        text_display = []
        if name:
            text_display.append("name;")
        if external_label:
            text_display.append("external_label;")
        if molecular_weight:
            text_display.append("molecular_weight;")
        self.value = ''.join(text_display)



class TSSelect(TableSubBaseField, Select):
    """A select column; ``option_layers`` names the option set."""
    field_type = SubTableFieldType.SELECT
    required_fields = ['option_layers']

    def __init__(self, sr: StructureRegistry,  layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        Select.__init__(self, sr, json_data)


class TSSystemDefined(TableSubBaseField, SystemDefined):
    """A number-with-unit column: ``option_layers`` is the unit type, ``value_system`` the default
    unit."""
    field_type = SubTableFieldType.SYSTEM_DEFINED
    required_fields = ['option_layers', 'value_system']

    def __init__(self, sr: StructureRegistry,  layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        SystemDefined.__init__(self, json_data)


class TSText(TableSubBaseField):
    """A text column."""
    field_type = SubTableFieldType.TEXT


class TSNumber(TableSubBaseField, Numeric):
    """A number column. New columns get ``numeric = {decimals: 0, min: '', max: ''}`` like in the designer;
    see :meth:`Numeric.set_numeric`."""
    field_type = SubTableFieldType.NUMBER
    required_fields = ['numeric']

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        Numeric.__init__(self, json_data)
        if self._numeric is None:
            self._numeric = {'decimals': 0, 'min': '', 'max': ''}


class TSSelectMulti(TableSubBaseField, Select):
    """A multiple-choice column; ``option_layers`` names the option set."""
    field_type = SubTableFieldType.SELECT_MULTI
    required_fields = ['option_layers']

    def __init__(self, sr: StructureRegistry,  layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        Select.__init__(self, sr, json_data)


class TSFormulaField(TableSubBaseField):
    """A column computed from number and system-defined columns of the same row.

    The formula uses abbreviations that :meth:`add_ref` binds to columns, e.g.::

        mass = table.add_subfield(SubTableFieldType.NUMBER, 'Mass')
        total = table.add_subfield(SubTableFieldType.FORMULA_FIELD, 'Double mass')
        total.add_ref(mass, 'm')
        total.formula = 'm*2'
    """
    field_type = SubTableFieldType.FORMULA_FIELD
    required_fields = ['formula', 'decimal', 'refs']
    #: The column types a formula can use (the designer's ``rl``).
    ref_types = (SubTableFieldType.NUMBER, SubTableFieldType.SYSTEM_DEFINED)

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._formula = json_data.get('formula', '')
        self._decimal = json_data.get('decimal', 5)
        self._refs = json_data.get('refs', [])

    @property
    def formula(self) -> str:
        """The expression, in the abbreviations of :attr:`refs` (``**`` or ``^`` for powers)."""
        return self._formula

    @formula.setter
    def formula(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"formula {type(value)} not supported")
        self._formula = value

    @property
    def decimal(self) -> int:
        """The number of decimal places of the result (default 5)."""
        return self._decimal

    @decimal.setter
    def decimal(self, value: int):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"decimal must be an integer >= 0, not {value!r}")
        self._decimal = value

    @property
    def refs(self) -> list[dict]:
        """The columns the formula uses: ``[{id: <column id>, abbr: <name in the formula>}]``."""
        return self._refs

    @refs.setter
    def refs(self, value: list[dict]):
        if not isinstance(value, list) or not all(isinstance(r, dict) and 'id' in r and 'abbr' in r for r in value):
            raise TypeError("refs must be a list of {'id': ..., 'abbr': ...} dicts")
        self._refs = value

    def add_ref(self, column: TableSubBaseField, abbr: str) -> dict:
        """
        Lets the formula use ``column`` under the name ``abbr``.

        :param column: a number or system-defined column of the same table
        :param abbr: the name used in the formula (letters, digits, '_'; not starting with a digit)
        :return: the new reference

        :raises ValueError: if the column type cannot be used or the name is invalid or taken
        """
        if column.field_type not in self.ref_types:
            raise ValueError(f"Only {', '.join(t.value for t in self.ref_types)} columns can be used in a formula")
        if not isinstance(abbr, str) or re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', abbr) is None:
            raise ValueError(f"abbr must be a name of letters, digits and '_', not {abbr!r}")
        if any(r['abbr'] == abbr for r in self._refs):
            raise ValueError(f"abbr {abbr!r} is already used")
        ref = {'id': column.id, 'abbr': abbr}
        self._refs = [r for r in self._refs if r['id'] != column.id] + [ref]
        return ref
