import re

from chemotion_api.labImotion.items.fields.abstract_fields import SystemDefined, Select, \
    _report_unknown_unit as _report_unknown_value
from chemotion_api.labImotion.items.fields.sub_fields import SubBaseField, NUMBER_PATTERN
from chemotion_api.labImotion.items.options import SubTableFieldType
from chemotion_api.labImotion.structure import StructureRegistry

class TableSubBaseField(SubBaseField):
    _default_required_fields = ["id", "col_name", "field_type", "value"]
    required_fields = []

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._col_name = json_data.get("col_name", "")

    @property
    def col_name(self) -> str:
        return self._col_name
    
    @col_name.setter
    def col_name(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"col_name {type(value)} not supported")
        self._col_name = value

    def _set_lenient(self, name: str, value) -> None:
        """Assign a value read from the server through its setter; keep it as stored if the setter
        refuses it. As for layer fields (``BaseField._parse_json``): a column this client would
        not accept from user code must not make the whole template unreadable."""
        try:
            setattr(self, name, value)
        except (ValueError, TypeError) as e:
            object.__setattr__(self, f'_{name}', value)
            _report_unknown_value(f"{type(self).__name__}.{name} rejected the server's value {value!r} "
                                  f"({type(e).__name__}: {e})")


class TSDragMolecule(TableSubBaseField):
    field_type = SubTableFieldType.DRAG_MOLECULE

    @property
    def value(self) -> str:
        if self._value is None or self._value == '':
            self._value = ';'
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


class TSDragSample(TableSubBaseField):
    field_type = SubTableFieldType.DRAG_SAMPLE

    @property
    def value(self) -> str:
        if self._value is None or self._value == '':
            self._value = ';'
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
        text_display = []
        if name:
            text_display.append("name;")
        if external_label:
            text_display.append("external_label;")
        if molecular_weight:
            text_display.append("molecular_weight;")
        self.value = ''.join(text_display)



class TSSelect(TableSubBaseField, Select):
    field_type = SubTableFieldType.SELECT
    required_fields = ['option_layers']

    def __init__(self, sr: StructureRegistry,  layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        Select.__init__(self, sr, json_data)


class TSSystemDefined(TableSubBaseField, SystemDefined):
    field_type = SubTableFieldType.SYSTEM_DEFINED
    required_fields = ['option_layers', 'value_system']

    def __init__(self, sr: StructureRegistry,  layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        SystemDefined.__init__(self, json_data)


class TSText(TableSubBaseField):
    field_type = SubTableFieldType.TEXT


class TSNumber(TableSubBaseField):
    """A ``number`` column. Values are stored as text, like the designer's number input: ``''`` or a
    number with sign, decimals and exponent.

    ``numeric`` holds the column's optional number settings,
    ``{'decimals': int >= 0, 'min': number | str, 'max': number | str}``, as the designer stores them.
    """
    field_type = SubTableFieldType.NUMBER
    _NUMERIC_KEYS = ('decimals', 'min', 'max')

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, {**json_data, 'value': ''})
        self._numeric: dict | None = None
        self._set_lenient('value', json_data.get('value', ''))
        if 'numeric' in json_data:
            self._set_lenient('numeric', json_data['numeric'])

    def to_dict(self):
        json_dict = super().to_dict()
        if self._numeric is not None:
            json_dict['numeric'] = dict(self._numeric)
        return json_dict

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
        # A key that is given may not be None: write '' for an unset bound, or leave the key out.
        # (The schema reads a stored null leniently; this client does not write one.)
        if 'decimals' in value:
            decimals = value['decimals']
            if isinstance(decimals, bool) or not isinstance(decimals, int):
                raise TypeError(f"numeric decimals {type(decimals)} not supported, use an int")
            if decimals < 0:
                raise ValueError("numeric decimals must be 0 or more")
        bounds = {}
        for key in ('min', 'max'):
            if key not in value:
                continue
            bound = value[key]
            if isinstance(bound, bool) or not isinstance(bound, int | float | str):
                raise TypeError(f"numeric {key} {type(bound)} not supported, use a number or str")
            if isinstance(bound, str):
                if bound.strip() == '':
                    continue  # '' is how the designer stores an unset bound
                # the designer reads a single ',' as the decimal point
                if NUMBER_PATTERN.fullmatch(bound.strip().replace(',', '.')) is None:
                    raise ValueError(f"numeric {key} must be a number or '': {bound!r}")
                bound = float(bound.strip().replace(',', '.'))
            bounds[key] = bound
        if 'min' in bounds and 'max' in bounds and bounds['min'] > bounds['max']:
            raise ValueError(f"numeric min {value['min']!r} is greater than max {value['max']!r}")
        self._numeric = dict(value)

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str | float | int):
        if isinstance(value, bool):
            raise TypeError(f"value {type(value)} not supported")
        if isinstance(value, float | int):
            value = str(value)
        if not isinstance(value, str):
            raise TypeError(f"value {type(value)} not supported")
        if value != '' and NUMBER_PATTERN.fullmatch(value) is None:
            raise ValueError(f"value must be a number: {value}")
        self._value = value


class TSSelectMulti(TableSubBaseField, Select):
    """A ``select-multi`` column, linked to an option list of the template like a ``select`` column."""
    field_type = SubTableFieldType.SELECT_MULTI
    required_fields = ['option_layers']

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        Select.__init__(self, sr, json_data)


class TSFormula(TableSubBaseField):
    """A ``formula-field`` column: its cells are computed by the ELN from other columns of the row.

    ``formula`` uses variable names, ``refs`` maps each name to a column
    (``[{'id': <column id>, 'abbr': <name>}]``, see :meth:`add_ref`) and ``decimal`` is the number of
    decimal places (default 5, as in the designer). Referenced columns are used in their default unit.
    """
    field_type = SubTableFieldType.FORMULA_FIELD
    required_fields = ['formula', 'refs', 'decimal']
    _REF_KEYS = {'id', 'abbr'}
    #: A variable name as the designer's formula editor accepts it.
    _ABBR_PATTERN = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        self._formula = ''
        self._refs: list[dict[str, str]] = []
        self._decimal = 5
        for name in ('formula', 'refs', 'decimal'):
            if name in json_data:
                self._set_lenient(name, json_data[name])

    def to_dict(self):
        json_dict = super().to_dict()
        if isinstance(json_dict.get('refs'), list):
            json_dict['refs'] = [dict(r) if isinstance(r, dict) else r for r in json_dict['refs']]
        return json_dict

    @property
    def formula(self) -> str:
        return self._formula

    @formula.setter
    def formula(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"formula {type(value)} not supported")
        self._formula = value

    @property
    def refs(self) -> list[dict[str, str]]:
        return self._refs

    @refs.setter
    def refs(self, value: list[dict[str, str]]):
        if not isinstance(value, list):
            raise TypeError(f"refs {type(value)} not supported, use a list of {{'id', 'abbr'}}")
        refs = []
        seen_abbrs = set()
        for ref in value:
            if not isinstance(ref, dict):
                raise TypeError(f"ref {type(ref)} not supported, use {{'id', 'abbr'}}")
            if set(ref) != self._REF_KEYS:
                raise ValueError(f"a ref has exactly the keys 'id' and 'abbr', not {sorted(ref)}")
            if not isinstance(ref['id'], str) or not isinstance(ref['abbr'], str):
                raise TypeError("a ref's 'id' and 'abbr' are strings")
            abbr = ref['abbr'].strip()
            if abbr == '':
                raise ValueError("a ref needs a non-empty 'abbr' (the designer drops refs without one)")
            if self._ABBR_PATTERN.fullmatch(abbr) is None:
                raise ValueError(f"abbr {abbr!r} is invalid: use letters, digits and underscore, "
                                 f"not starting with a digit")
            if abbr in seen_abbrs:
                raise ValueError(f"abbr {abbr!r} is used more than once")
            seen_abbrs.add(abbr)
            refs.append({'id': ref['id'], 'abbr': abbr})
        self._refs = refs

    def add_ref(self, column: TableSubBaseField | str, abbr: str) -> TSFormula:
        """Make ``abbr`` a variable of the formula that stands for ``column`` (a column of the same
        table, or its id).

        :return: this column, so calls can be chained
        """
        column_id = column if isinstance(column, str) else column.id
        if column_id == self.id:
            raise ValueError("a formula column cannot reference itself")
        self.refs = self.refs + [{'id': column_id, 'abbr': abbr}]
        return self

    @property
    def decimal(self) -> int:
        return self._decimal

    @decimal.setter
    def decimal(self, value: int | str):
        if isinstance(value, bool) or not isinstance(value, int | str):
            raise TypeError(f"decimal {type(value)} not supported, use an int")
        if isinstance(value, str):
            if not (value.strip().isascii() and value.strip().isdigit()):
                raise ValueError(f"decimal must be a whole number of 0 or more: {value!r}")
            value = int(value)
        if value < 0:
            raise ValueError("decimal must be 0 or more")
        self._decimal = value


class TSOpaque(TableSubBaseField):
    """A column of a type this client has no class for. It keeps every key the server sent, so the
    template round-trips, and the table's other columns stay typed."""

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        self.field_type = json_data.get('type')
        self._json_data = dict(json_data)
        super().__init__(sr, layer_key, {**json_data, 'value': ''})
        self._value = json_data.get('value', '')

    def to_dict(self):
        json_dict = dict(self._json_data) | super().to_dict()
        for key in ('col_name', 'value'):
            if key not in self._json_data and json_dict.get(key) == '':
                del json_dict[key]  # keep the column as the server sent it
        return json_dict
