"""
Helpers for the fields of generic (LabIMotion) segments.

Segment values are plain dicts. A :class:`SegmentField` looks up what the segment template says about
one field - its type, select options and units - checks values before they are saved, and converts
between the two formats Chemotion stores:

* in a segment, a select field holds the option **key** and a system-defined field holds
  ``value`` and ``value_system``
* in a reaction variation (Chemotion >= 3.1), each field is an entry
  ``{'type', 'label', 'options', 'value', 'unit', 'quantity'}`` stored under
  ``'layer<layer key>field<field key>'``, and a select field holds the option **label**
"""
import datetime
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation
from typing import Any

# Field types the variations grid of the Chemotion frontend shows as columns.
VARIATION_FIELD_TYPES = ('integer', 'system-defined', 'select', 'text')

_EMPTY = (None, '')

#: ``option_layers`` of a select field whose options are the ELN's users ("System user list"); its value is a
#: user id.
USER_LIST = '-su03-'

#: How the ELN web form writes a date and time: ``new Date(x).toLocaleString('en-GB')`` without the comma.
DATETIME_FORMAT = '%d/%m/%Y %H:%M:%S'


def format_datetime(value: Any) -> Any:
    """
    Returns a :class:`datetime.datetime` or :class:`datetime.date` as the ELN web form stores it
    (``DD/MM/YYYY HH:mm:ss``). Any other value is returned as it is.
    """
    if isinstance(value, datetime.datetime):
        return value.strftime(DATETIME_FORMAT)
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time()).strftime(DATETIME_FORMAT)
    return value


def to_decimal(value: Any) -> Decimal | None:
    """
    Reads a number as the ELN web form does: numbers and numeric strings, with a single ``,`` as the decimal
    separator. Returns None for anything else (also for booleans and for ``inf``/``nan``).
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value.count(',') > 1 or value.count('.') > 1 or (',' in value and '.' in value):
            return None
        value = value.replace(',', '.')
    try:
        number = Decimal(str(value)) if isinstance(value, float) else Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number.is_finite() else None


class SegmentField:
    """
    One field of a segment template.

    :param field: field dict from the template's ``layers[...]['fields']``
    :param layer_key: key of the layer containing the field
    :param select_options: ``select_options`` of the template
    """

    def __init__(self, field: dict, layer_key: str, select_options: dict | None = None):
        self._field = field
        self.layer_key = layer_key
        self._select_options = select_options or {}

    @property
    def key(self) -> str:
        return str(self._field.get('field') or self._field.get('id', ''))

    @property
    def label(self) -> str:
        """The label of the field, or the column name of a table column."""
        return self._field.get('label') or self._field.get('col_name') or self.key

    @property
    def type(self) -> str:
        return self._field['type']

    @property
    def ontology(self) -> dict | None:
        """The ontology term linked to the field in the template, or None."""
        return self._field.get('ontology') or None

    @property
    def quantity(self) -> str | None:
        """Unit quantity of a system-defined field (e.g. 'current'), or the option set of a select field."""
        return self._field.get('option_layers') or None

    @property
    def default_unit(self) -> str | None:
        return self._field.get('value_system') or None

    @property
    def variation_key(self) -> str:
        return f'layer<{self.layer_key}>field<{self.key}>'

    @property
    def numeric(self) -> dict:
        """
        The ``numeric`` settings of a number field: ``{'decimals', 'min', 'max'}``. A number field without
        them takes integers only, as in the ELN web form.
        """
        return self._field.get('numeric') or {}

    def options(self) -> list[dict[str, str]]:
        """
        :return: options of a select or select-multi field as ``[{'key': ..., 'label': ...}]``. Empty for a
            field that lists the ELN's users (``option_layers`` ``'-su03-'``)
        """
        if self.type not in ('select', 'select-multi'):
            raise TypeError(f'Field "{self.label}" is a {self.type} field, not a select field.')
        options = self._select_options.get(self.quantity, {}).get('options', [])
        return [{'key': o.get('key'), 'label': o.get('label', o.get('key'))} for o in options]

    def units(self) -> list[str]:
        """
        :return: units of a system-defined field, or an empty list if its quantity is unknown
        """
        if self.type != 'system-defined':
            raise TypeError(f'Field "{self.label}" is a {self.type} field, not a system-defined field.')
        from chemotion_api.labImotion.items.options import FieldUnit, UNITS
        try:
            return list(UNITS[FieldUnit(self.quantity)])
        except ValueError:
            return []

    def option_key(self, value: str) -> str:
        """Returns the key of the select option given by its key or label."""
        return self._find_option(value)['key']

    def option_label(self, value: str) -> str:
        """Returns the label of the select option given by its key or label."""
        return self._find_option(value)['label']

    def _find_option(self, value: str) -> dict[str, str]:
        options = self.options()
        option = next((o for o in options if o['key'] == value), None)
        option = option or next((o for o in options if o['label'] == value), None)
        if option is None:
            labels = ', '.join(f'"{o["label"]}"' for o in options)
            raise ValueError(f'"{value}" is not an option of "{self.label}". Options: {labels}')
        return option

    def clean_value(self, value: Any) -> Any:
        """
        Checks a value for this field and returns it in segment format, as the ELN web form stores it:

        * select: the option **key** (an option may be given by key or label). A field listing the ELN's
          users takes a user id, stored as a string.
        * select-multi: a list of option keys, without duplicates. If the field's options are unknown (the
          template has no option list for it), the keys are taken as given.
        * system-defined: ``{'value': ..., 'unit': ...}``. A bare number gets the field's default unit.
        * number: a number, rounded to no more than ``numeric['decimals']`` places and within
          ``numeric['min']``/``['max']``; ``''`` for no value
        * integer: an integral number (stored as given)
        * checkbox: ``True`` or ``False``
        * datetime: a ``DD/MM/YYYY HH:mm:ss`` string; a :class:`datetime.datetime` is converted to it
        * ontology-select: the label of the chosen ontology term (a string)

        Other types are returned as they are.

        :raises ValueError: if the value does not fit the field
        """
        if self.type == 'select':
            if value in _EMPTY:
                return value
            return str(value) if self.quantity == USER_LIST else self.option_key(value)
        if self.type == 'select-multi':
            return self._clean_select_multi(value)
        if self.type == 'system-defined':
            return self._clean_system_defined(value)
        if self.type == 'number':
            return self._clean_number(value)
        if self.type == 'integer' and value not in _EMPTY:
            try:
                is_integer = float(value) == int(float(value))
            except (TypeError, ValueError):
                is_integer = False
            if not is_integer:
                raise ValueError(f'"{self.label}" needs an integer, got {value!r}.')
        if self.type == 'checkbox' and not isinstance(value, bool):
            raise ValueError(f'"{self.label}" needs True or False, got {value!r}.')
        if self.type == 'datetime':
            return format_datetime(value)
        if self.type == 'ontology-select' and value is not None and not isinstance(value, str):
            raise ValueError(f'"{self.label}" needs the label of an ontology term (a string), got {value!r}.')
        return value

    def _clean_select_multi(self, value: Any) -> list[str]:
        if value in _EMPTY:
            return []
        if isinstance(value, (str, int)):
            value = [value]
        if not isinstance(value, (list, tuple, set)):
            raise ValueError(f'"{self.label}" needs a list of options, got {value!r}.')
        # If the field's options are unknown (no option list for its option_layers), keys are taken as given
        options_known = self.quantity != USER_LIST and bool(self.options())
        keys: list[str] = []
        for item in value:
            if item in _EMPTY:
                continue
            if self.quantity == USER_LIST:
                key = str(item)
            else:
                key = self.option_key(item) if options_known else item
            if key not in keys:
                keys.append(key)
        return keys

    def _clean_number(self, value: Any) -> Any:
        if value in _EMPTY:
            return ''
        number = to_decimal(value)
        if number is None:
            raise ValueError(f'"{self.label}" needs a number, got {value!r}.')
        numeric = self.numeric
        try:
            decimals = max(int(numeric.get('decimals') or 0), 0)
        except (TypeError, ValueError):
            decimals = 0
        exponent = number.normalize().as_tuple().exponent
        if isinstance(exponent, int) and -exponent > decimals:
            raise ValueError(f'"{self.label}" takes at most {decimals} decimal place(s), got {value!r}.')
        lowest, highest = to_decimal(numeric.get('min')), to_decimal(numeric.get('max'))
        if lowest is not None and number < lowest:
            raise ValueError(f'"{self.label}" must be at least {numeric.get("min")}, got {value!r}.')
        if highest is not None and number > highest:
            raise ValueError(f'"{self.label}" must be at most {numeric.get("max")}, got {value!r}.')
        return int(number) if number == number.to_integral_value() else float(number)

    def _clean_system_defined(self, value: Any) -> dict:
        if isinstance(value, dict):
            unit = value.get('unit') or self.default_unit
            value = value.get('value')
        else:
            unit = self.default_unit
        if value not in _EMPTY:
            try:
                float(value)
            except (TypeError, ValueError):
                raise ValueError(f'"{self.label}" needs a number, got {value!r}.') from None
        units = self.units()
        if unit is not None and units and unit not in units:
            raise ValueError(f'"{unit}" is not a unit of "{self.label}". Units: {", ".join(units)}')
        return {'value': value, 'unit': unit}

    def default_variation_value(self) -> Any:
        """The value a new variation starts with, as the Chemotion frontend sets it."""
        if self.type == 'select':
            options = self.options()
            return options[0]['label'] if options else None
        if self.type == 'system-defined':
            return {'value': None, 'unit': self.default_unit}
        return None

    def from_variation_entry(self, entry: dict) -> Any:
        """Reads the value of a variation entry."""
        if self.type == 'system-defined':
            return {'value': entry.get('value'), 'unit': entry.get('unit') or self.default_unit}
        return entry.get('value')

    def to_variation_entry(self, value: Any) -> dict:
        """
        Builds the variation entry for a value. Select values are stored as option labels.

        :raises ValueError: if the value does not fit the field, or if a system-defined field without a
            default unit gets a value - the frontend cannot show such a value in the variations grid.
        """
        entry = {
            'type': self.type,
            'label': self.label,
            'value': value,
            'unit': self.default_unit,
            'quantity': self.quantity,
        }
        if self.type == 'select':
            entry['options'] = [o['label'] for o in self.options()]
            entry['value'] = None if value in _EMPTY else self.option_label(value)
        elif self.type == 'system-defined':
            cleaned = self._clean_system_defined(value)
            if cleaned['value'] not in _EMPTY:
                if self.default_unit is None:
                    raise ValueError(
                        f'"{self.label}" has no default unit in the segment template, so the variations grid '
                        f'cannot show it. Set a default unit for it in LabIMotion first.')
                cleaned['value'] = float(cleaned['value'])
            entry['value'] = cleaned['value']
            entry['unit'] = cleaned['unit']
        else:
            entry['value'] = self.clean_value(value)
        return entry


def iter_fields(properties: dict) -> Iterator[tuple[str, str, SegmentField]]:
    """
    Iterates over the fields of a segment template or segment.

    The layer and field names are the ones ``element.segments`` uses: the label, or the key if there is
    no label, with ``.1``, ``.2``, ... appended to duplicates.

    :param properties: ``properties`` or ``properties_release`` of a segment
    :return: ``(layer name, field name, field)`` tuples
    """
    select_options = properties.get('select_options', {})
    layer_names: set[str] = set()
    layers = sorted(properties.get('layers', {}).items(), key=lambda x: x[1].get('position'))
    for layer_key, layer in layers:
        layer_name = _unique_name(layer.get('label') or layer.get('key'), layer_names)
        field_names: set[str] = set()
        for field in sorted(layer.get('fields', []), key=lambda x: x.get('position')):
            if field.get('type') == 'wf-next':
                continue
            field_name = _unique_name(field.get('label') or field.get('field'), field_names)
            yield layer_name, field_name, SegmentField(field, layer_key, select_options)


def _unique_name(name: str, used: set[str]) -> str:
    unique_name, idx = name, 1
    while unique_name in used:
        unique_name = f'{name}.{idx}'
        idx += 1
    used.add(unique_name)
    return unique_name
