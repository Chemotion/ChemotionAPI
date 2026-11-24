import copy
import os
import re
import sys
import uuid
from abc import ABC
from collections.abc import Mapping, MutableMapping, MutableSequence
from collections import OrderedDict
from typing import Any, Optional

from chemotion_api.utils.segment_fields import SegmentField, format_datetime, to_decimal


class PropertyDict(MutableMapping):

    def __init__(self, on_change, kwargs):
        self.data = kwargs
        self._on_change = on_change

    @property
    def on_change(self):
        return self._on_change

    @on_change.setter
    def on_change(self, value):
        self._on_change = value

    def __getitem__(self, name):
        ret_val = self.data.__getitem__(name)
        # Dict subclasses with their own methods (e.g. Temperature) are returned as they are
        if type(ret_val) is dict:
            ret_val = PropertyDict(None, ret_val)
        if isinstance(ret_val, PropertyDict):
            def inner_on_change(inner_dict_obj, inner_name, inner_value):
                return self._on_change([self.to_dict(), *inner_dict_obj], [name, *inner_name], [ret_val.to_dict(), *inner_value])
            ret_val.on_change = inner_on_change
        return ret_val

    def __setitem__(self, name, value):
        if self._on_change is not None and self._on_change([self.data], [name], [value]):
            self.data.__setitem__(name, value)

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def __delitem__(self, k):
        raise NotImplementedError

    def __contains__(self, k):
        return k in self.data

    @property
    def __dict__(self):
        return self.to_dict()

    def to_dict(self):
        """:return: The underlying plain ``dict`` backing this mapping."""
        return self.data

    def _attr_error(self, name):
        import difflib
        keys = [k for k in self.data.keys() if isinstance(k, str)]
        hint = difflib.get_close_matches(name, keys, n=3)
        suffix = f" Did you mean: {', '.join(hint)}?" if hint else (
            f" Available keys: {', '.join(sorted(keys))}" if keys else "")
        return AttributeError(f"'PropertyDict' object has no property '{name}'.{suffix}")

    def __getattr__(self, name):
        if name.startswith('_') or name in ('data', 'on_change', 'to_dict'):
            raise AttributeError(f"'PropertyDict' object has no attribute '{name}'")
        try:
            return self[name]
        except KeyError:
            raise self._attr_error(name) from None

    def __setattr__(self, name, value):
        if name.startswith('_') or name in ('data', 'on_change'):
            super().__setattr__(name, value)
        elif hasattr(self.__class__, name) and isinstance(getattr(self.__class__, name), property):
            super().__setattr__(name, value)
        else:
            try:
                self[name] = value
            except KeyError:
                raise AttributeError(f"'PropertyDict' object has no attribute '{name}'") from None


def resource_path(file_path):
    """Get the absolute path to the resource, works for development and PyInstaller build."""
    return os.path.dirname(file_path)


def fixeddict_serializer(obj):
    if isinstance(obj, PropertyDict):
        return obj.to_dict()  # Return the underlying dictionary
    return obj

class FixedDict(PropertyDict):

    def __init__(self, data):
        super().__init__(None, data)

    def __setitem__(self, k, v):
        if k not in self.data:
            raise KeyError(k)

        super().__setitem__(k,v)

    def __delitem__(self, k):
        raise NotImplementedError

    def __getitem__(self, k):
        return super().__getitem__(k)


class UnitDict(FixedDict):
    def __init__(self, unit: str, value: float | None):
        super().__init__({'unit': unit, 'value': value})

    def set_value_unit(self, value: float):
        self.__setitem__('value', value)

    def set_value(self, value: float):
        self.__setitem__('value', value)

    def set_unit(self, unit: str):
        self.__setitem__('unit', unit)


class AttrAccessMixin:
    """
    Makes the keys of a dict readable and writable as attributes: ``obj.name`` is ``obj['name']``.
    Real attributes take precedence over keys.
    """

    def __getattr__(self, name: str) -> Any:
        if not name.startswith('_'):
            try:
                return self[name]
            except KeyError:
                pass
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any):
        if not name.startswith('_') and name in self and name not in self.__dict__ and \
                not hasattr(type(self), name):
            self[name] = value
        else:
            super().__setattr__(name, value)


def add_to_dict(obj: dict, key: str, val: any) -> str:
    origen_key = key
    idx = 1
    while key in obj and obj[key] is not None:
        key = f"{origen_key}.{idx}"
        idx += 1

    obj[key] = val
    return key


class TableRow(dict):
    """
    One row of a generic table field: ``{column name: cell value}``.

    :attr:`row_id` is the id the ELN stores for the row. A row read from the server keeps it, so removing,
    reordering or editing rows keeps the ids of the other rows. Rows added as plain dicts are new rows and get a
    new id when they are saved.
    """

    def __init__(self, *args, row_id: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.row_id = row_id


#: Column names of the four sub-fields of a datetime-range field, in the order the ELN web form creates them.
#: ``durationCalc`` is never filled by the form (it shows the computed difference without storing it).
DATETIME_RANGE_PARTS = ('timeStart', 'timeStop', 'durationCalc', 'duration')
_DATETIME_RANGE_VALUES = ('timeStart', 'timeStop', 'duration')
_DURATION_DEFAULT_UNIT = 'd'


def _plain(value: Any) -> Any:
    """Unwraps :class:`PropertyDict` objects (also nested ones) into the dicts they hold."""
    if isinstance(value, PropertyDict):
        value = value.to_dict()
    if type(value) is dict:
        return {k: _plain(v) for k, v in value.items()}
    if type(value) is list:
        return [_plain(v) for v in value]
    return value


def _cell_value(cell: Any) -> Any:
    """The value of a table cell stored as ``{'value': ...}``; legacy plain cells are returned as they are."""
    if isinstance(cell, dict) and 'value' in cell:
        return cell['value']
    return cell


def _read_table_cell(column: dict, cell: Any) -> Any:
    """
    Reads a table cell in the shape of the matching field type: text as a string, number, select key, list of
    keys (select-multi), ``{'value', 'unit'}`` (system-defined), formula result, or the dropped molecule or
    sample (``{'el_id', 'el_type', ...}``). Cells of unknown column types are returned as stored.
    """
    col_type = column.get('type')
    if col_type == 'text':
        return _cell_value(cell)
    if col_type == 'select-multi':
        keys = _cell_value(cell)
        return list(keys) if isinstance(keys, list) else []
    if col_type == 'system-defined':
        stored = cell if isinstance(cell, dict) else {'value': cell}
        return {'value': stored.get('value'), 'unit': stored.get('value_system') or column.get('value_system')}
    if col_type in ('number', 'select', 'formula-field', 'drag_molecule', 'drag_sample'):
        return _cell_value(cell)
    return cell


def _read_datetime_range(field: dict) -> dict:
    """
    Reads a datetime-range field as ``{'timeStart', 'timeStop', 'duration': {'value', 'unit'}}``. Without
    stored sub-fields it reads as the empty form: ``''`` and unit ``'d'``.
    """
    parts = {x.get('col_name'): x for x in field.get('sub_fields') or [] if isinstance(x, dict)}
    duration = parts.get('duration', {})
    return {'timeStart': parts.get('timeStart', {}).get('value', ''),
            'timeStop': parts.get('timeStop', {}).get('value', ''),
            'duration': {'value': duration.get('value', ''),
                         'unit': duration.get('value_system', _DURATION_DEFAULT_UNIT)}}


def parse_generic_field(field: dict) -> dict[str, any]:
    """
    Reads the value of one field of a generic element, segment or dataset.

    The value has the shape the field type stores, see :func:`clean_generic_field`. Input groups read as a list
    of their sub-field values, tables as a list of :class:`TableRow`.

    :param field: the field dict of the layer
    :return: ``{'values': value, 'obj_mapping': field key}``; for tables the mapping is
        ``{'__field': field key, column name: column id}``
    """
    field_type = field.get('type')
    field_key = field.get('id', field.get('field'))
    sub_fields = [x for x in field.get('sub_fields') or [] if isinstance(x, dict)]
    if field_type == 'input-group':
        return {'values': [parse_generic_field(x).get('values') for x in sub_fields],
                'obj_mapping': {'__field': field.get('field')}}
    if field_type == 'table':
        field_mapping = {'__field': field.get('field')}
        names = [add_to_dict(field_mapping, x.get('col_name') or x.get('id'), x.get('id')) for x in sub_fields]
        rows = []
        for stored in field.get('sub_values') or []:
            if not isinstance(stored, dict):
                continue
            rows.append(TableRow({name: _read_table_cell(column, stored.get(column.get('id')))
                                  for name, column in zip(names, sub_fields)}, row_id=stored.get('id')))
        return {'values': rows, 'obj_mapping': field_mapping}
    if field_type == 'select-multi':
        return {'values': [x.get('value') for x in sub_fields if x.get('value') not in (None, '')],
                'obj_mapping': field_key}
    if field_type == 'datetime-range':
        return {'values': _read_datetime_range(field), 'obj_mapping': field_key}
    if field_type == 'system-defined':
        return {'values': {'value': field.get('value'), 'unit': field.get('value_system')},
                'obj_mapping': field_key}
    if field_type == 'drag_element':
        return {'values': {'value': field.get('value')}, 'obj_mapping': field_key}
    return {'values': field.get('value'), 'obj_mapping': field_key}


def parse_generic_layer(key: str, layer: dict) -> dict[str, dict]:
    temp_layer = {}
    temp_id_layer = {'__key': key}
    fields = layer.get('fields', [])
    fields.sort(key=lambda x: x.get('position'))
    for field in fields:
        if field.get('type') != 'wf-next':
            temp_field = parse_generic_field(field)
            field_name = field.get('label') or field.get('field')
            key = add_to_dict(temp_layer, field_name, temp_field.get('values'))
            temp_id_layer[key] = temp_field.get('obj_mapping')

    return {'values': temp_layer, 'obj_mapping': temp_id_layer}


def parse_generic_object_json(segment_json_data: dict) -> dict:
    temp_segment = {}
    temp_id_segment = {'__id': segment_json_data.get('id')}
    layers = OrderedDict(
        sorted(segment_json_data.get('properties', {}).get('layers', {}).items(),
               key=lambda x: (x[1].get('position'), x[1].get('wf_position') or 0)))
    for key, layer in layers.items():
        parse_generic_object_layer_json(key, layer, temp_segment, temp_id_segment)
    return {'values': temp_segment, 'obj_mapping': temp_id_segment}


def parse_generic_object_layer_json(key, layer, values, obj_mapping) -> str:
    """
    Adds a layer to the values as ``values[name] = {field: value}`` and returns the name. The name is the layer
    label; a duplicated layer (key ``three.1``) gets the suffix of its key (``Nr 3.1``), so the name does not
    depend on the order the layers are read in.
    """
    temp_layer = parse_generic_layer(key, layer)
    layer_name = layer.get('label') or layer.get('key')
    suffix = re.fullmatch(r'.+\.(\d+)', key or '')
    if suffix is not None and not layer_name.endswith(f".{suffix.group(1)}") and \
            f"{layer_name}.{suffix.group(1)}" not in values:
        layer_name = f"{layer_name}.{suffix.group(1)}"
    key = add_to_dict(values, layer_name, temp_layer.get('values'))
    obj_mapping[key] = temp_layer.get('obj_mapping')
    return key


def clean_generic_field(field_obj: dict, values: Any, field_mapping: dict | str | None = None,
                        select_options: dict | None = None) -> dict[str, Any]:
    """
    Writes a value into a field of a generic element, segment or dataset, in the shape the ELN web form
    (chem-generic-ui) stores it. A value equal to the one read from the field is kept as stored, so data
    loaded from the server can always be saved again. Changed values are checked (see
    :meth:`SegmentField.clean_value`) and converted:

    * select-multi: a list of option keys or labels -> ``sub_fields = [{'value': key}, ...]``
    * datetime-range: a dict with any of ``timeStart``, ``timeStop`` (strings ``DD/MM/YYYY HH:mm:ss`` or
      :class:`datetime.datetime`) and ``duration`` (``{'value', 'unit'}`` or a bare number in the current unit)
      -> its four sub-fields. The duration is not derived from start and stop: the web form fills it only
      when the user clicks its copy button.
    * datetime: ``None`` removes the value, as clearing the date picker does. A field without a stored
      value (dummy, text-formula) does not get one.
    * input-group: a list of sub-field values in sub-field order
    * table: a list of row dicts ``{column name: cell}``; the table ends up with exactly these rows, see
      :func:`_clean_table`
    * system-defined: ``{'value', 'unit'}`` or a bare number -> ``value`` and ``value_system``

    :param field_obj: the field dict of the layer; changed in place
    :param values: the new value
    :param field_mapping: the field's entry of the mapping from :func:`parse_generic_field`
    :param select_options: ``select_options`` of the template
    :return: ``field_obj``
    :raises ValueError: if the value does not fit the field
    """
    values = _plain(values)
    field_type = field_obj.get('type')
    if field_type == 'input-group':
        _clean_input_group(field_obj, values)
    elif field_type == 'table':
        _clean_table(field_obj, values, field_mapping if isinstance(field_mapping, dict) else {}, select_options)
    elif field_type == 'select-multi':
        _clean_select_multi(field_obj, values, select_options)
    elif field_type == 'datetime-range':
        _clean_datetime_range(field_obj, values)
    else:
        values = _check_generic_field_value(field_obj, values, select_options)
        if field_type == 'system-defined':
            field_obj['value'] = values['value']
            field_obj['value_system'] = values['unit']
        elif field_type == 'drag_element':
            field_obj['value'] = values['value']
        elif values is None and (field_type == 'datetime' or 'value' not in field_obj):
            # a cleared date picker deletes the value; fields without one (dummy, text-formula) get none
            field_obj.pop('value', None)
        else:
            field_obj['value'] = values
    return field_obj


def _clean_input_group(field_obj: dict, values: Any):
    """
    Writes the list of sub-field values of an input group. ``number`` sub-fields must hold a number (any
    number: the web form uses a plain number input); system-defined sub-fields are checked like
    system-defined fields.
    """
    sub_fields = field_obj.get('sub_fields') or []
    if not isinstance(values, (list, tuple)):
        raise ValueError(f'Input group "{field_obj.get("label")}" needs a list of {len(sub_fields)} values, '
                         f'got {values!r}.')
    if len(values) > len(sub_fields):
        raise ValueError(f'Input group "{field_obj.get("label")}" has {len(sub_fields)} parts, '
                         f'got {len(values)} values.')
    for sub_field, value in zip(sub_fields, values):
        current = parse_generic_field(sub_field).get('values')
        if value == current:
            continue
        if sub_field.get('type') == 'system-defined':
            clean_generic_field(sub_field, value)
            continue
        if sub_field.get('type') == 'number' and value not in (None, '') and to_decimal(value) is None:
            raise ValueError(f'Input group "{field_obj.get("label")}" needs a number in part '
                             f'{sub_fields.index(sub_field) + 1}, got {value!r}.')
        sub_field['value'] = value


def _clean_select_multi(field_obj: dict, values: Any, select_options: dict | None):
    """Stores the selected options of a select-multi field in ``sub_fields`` as ``[{'value': key}]``."""
    if values == parse_generic_field(field_obj).get('values'):
        return
    field = SegmentField(field_obj, '', select_options)
    try:
        keys = field.clean_value(values)
    except ValueError as e:
        raise ValueError(f'Invalid value for field "{field.label}": {e}') from None
    field_obj['sub_fields'] = [{'value': key} for key in keys]


def _clean_datetime_range(field_obj: dict, values: Any):
    """Writes the parts of a datetime-range field into its four sub-fields, creating them as the web form does."""
    label = field_obj.get('label') or field_obj.get('field')
    current = _read_datetime_range(field_obj)
    if values is None:
        values = {'timeStart': '', 'timeStop': '', 'duration': {'value': '', 'unit': current['duration']['unit']}}
    if not isinstance(values, dict):
        raise ValueError(f'Datetime range "{label}" needs a dict with {", ".join(_DATETIME_RANGE_VALUES)}, '
                         f'got {values!r}.')
    unknown = [k for k in values if k not in _DATETIME_RANGE_VALUES]
    if unknown:
        raise ValueError(f'Datetime range "{label}" has no part {", ".join(map(str, unknown))}. '
                         f'Parts: {", ".join(_DATETIME_RANGE_VALUES)}')
    changed = {k: v for k, v in values.items() if v != current[k]}
    if not changed:
        return
    duration = None
    if 'duration' in changed:
        duration = changed['duration'] if isinstance(changed['duration'], dict) else \
            {'value': changed['duration'], 'unit': current['duration']['unit']}
        unit = duration.get('unit') or current['duration']['unit']
        from chemotion_api.labImotion.items.options import FieldUnit, UNITS
        if unit not in UNITS[FieldUnit.DURATION]:
            raise ValueError(f'"{unit}" is not a unit of the duration of "{label}". '
                             f'Units: {", ".join(UNITS[FieldUnit.DURATION])}')
        if duration.get('value') not in (None, '') and to_decimal(duration.get('value')) is None:
            raise ValueError(f'The duration of "{label}" needs a number, got {duration.get("value")!r}.')
        duration = {'value': '' if duration.get('value') is None else duration.get('value'), 'unit': unit}

    sub_fields = field_obj.get('sub_fields') or []
    for name in DATETIME_RANGE_PARTS:
        if not any(isinstance(x, dict) and x.get('col_name') == name for x in sub_fields):
            new_part: dict[str, Any] = {'type': 'text', 'value': '', 'col_name': name}
            if name == 'duration':
                new_part |= {'option_layers': 'duration', 'value_system': _DURATION_DEFAULT_UNIT}
            sub_fields.append(new_part | {'id': str(uuid.uuid4())})
    field_obj['sub_fields'] = sub_fields
    parts = {x.get('col_name'): x for x in sub_fields if isinstance(x, dict)}
    for name in ('timeStart', 'timeStop'):
        if name in changed:
            value = format_datetime(changed[name])
            parts[name]['value'] = '' if value is None else value
    if duration is not None:
        parts['duration']['value'] = duration['value']
        parts['duration']['value_system'] = duration['unit']


def _new_table_cell(column: dict) -> Any:
    """The cell a new row starts with, as the web form's ``addRow`` creates it."""
    col_type = column.get('type')
    if col_type == 'text':
        return ''
    if col_type == 'select-multi':
        return {'value': []}
    if col_type in ('number', 'formula-field'):
        return {'value': ''}
    if col_type == 'system-defined':
        return {'value': '', 'value_system': column.get('value_system') or _first_unit(column.get('option_layers'))}
    cell: dict[str, Any] = {'value': ''}
    if column.get('value_system') is not None:
        cell['value_system'] = column['value_system']
    return cell


def _first_unit(quantity: str | None) -> str:
    from chemotion_api.labImotion.items.options import FieldUnit, UNITS
    try:
        return UNITS[FieldUnit(quantity)][0]
    except (ValueError, KeyError, IndexError):
        return ''


def _clean_table_cell(column: dict, value: Any, select_options: dict | None) -> Any:
    """
    Converts the value of a table cell into the stored cell: text -> string; number, select, formula-field,
    drag_molecule, drag_sample -> ``{'value': ...}``; select-multi -> ``{'value': [keys]}``; system-defined ->
    ``{'value', 'value_system'}``. Cells given in the stored shape are accepted too. Formula cells are not
    recomputed.
    """
    col_type = column.get('type')
    field = SegmentField(column, '', select_options)
    if col_type == 'system-defined':
        if isinstance(value, dict) and 'value_system' in value and 'unit' not in value:
            value = {'value': value.get('value'), 'unit': value.get('value_system')}
        if not isinstance(value, dict):
            value = {'value': value, 'unit': column.get('value_system') or _first_unit(column.get('option_layers'))}
        cleaned = field.clean_value(value)
        return {'value': '' if cleaned['value'] is None else cleaned['value'], 'value_system': cleaned['unit']}
    if col_type == 'text':
        value = _cell_value(value)
        return '' if value is None else value if isinstance(value, str) else str(value)
    if col_type in ('number', 'select', 'select-multi', 'formula-field'):
        if isinstance(value, dict) and set(value) == {'value'}:
            value = value['value']
        if col_type == 'formula-field':
            if value not in (None, '') and to_decimal(value) is None:
                raise ValueError(f'"{field.label}" needs a number, got {value!r}.')
            return {'value': '' if value is None else value}
        cleaned = field.clean_value(value)
        return {'value': '' if cleaned is None else cleaned}
    if col_type in ('drag_molecule', 'drag_sample'):
        if isinstance(value, dict) and set(value) == {'value'}:
            value = value['value']
        if value not in (None, '') and not isinstance(value, dict):
            raise ValueError(f'"{field.label}" needs the dropped {col_type[5:]} as a dict of its el_* keys, '
                             f'got {value!r}.')
        return {'value': '' if value is None else value}
    return value


def _clean_table(field_obj: dict, rows: Any, field_mapping: dict, select_options: dict | None):
    """
    Writes the rows of a table field. The table ends up with exactly the given rows, in the given order. A
    :class:`TableRow` read from this table keeps its id and its stored cells, and only changed cells are
    rewritten; any other row is a new row with a new id, starting from the web form's empty cells.

    :raises ValueError: for an unknown column name or a cell that does not fit its column
    """
    label = field_obj.get('label') or field_obj.get('field')
    if rows is None:
        rows = []
    if not isinstance(rows, (list, tuple)):
        raise ValueError(f'Table "{label}" needs a list of rows, got {rows!r}.')
    columns = {x.get('id'): x for x in field_obj.get('sub_fields') or [] if isinstance(x, dict)}
    names = {k: v for k, v in field_mapping.items() if not k.startswith('__')}
    stored_rows = {x.get('id'): x for x in field_obj.get('sub_values') or [] if isinstance(x, dict)}
    new_rows = []
    used_ids = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError(f'Table "{label}" needs each row as a dict {{column name: value}}, got {row!r}.')
        row_id = getattr(row, 'row_id', None)
        stored = stored_rows.get(row_id) if row_id not in used_ids else None
        if stored is None:
            stored = {'id': str(uuid.uuid4())}
            stored |= {col_id: _new_table_cell(column) for col_id, column in columns.items()}
        else:
            stored = copy.deepcopy(stored)
        used_ids.add(stored['id'])
        for name, value in row.items():
            col_id = names.get(name)
            if col_id is None or col_id not in columns:
                raise ValueError(f'Table "{label}" has no column "{name}". Columns: {", ".join(names)}')
            column = columns[col_id]
            value = _plain(value)
            if value == _read_table_cell(column, stored.get(col_id)):
                continue
            try:
                stored[col_id] = _clean_table_cell(column, value, select_options)
            except ValueError as e:
                raise ValueError(f'Invalid value in table "{label}", column "{name}": {e}') from None
        new_rows.append(stored)
    field_obj['sub_values'] = new_rows


def select_options_of(json_data: dict) -> dict:
    """
    The select options of a generic element, segment or dataset. The ELN does not keep ``select_options`` in
    a saved record's ``properties``, so they are taken from its template release (``properties_release``)
    when ``properties`` has none.
    """
    return (json_data.get('properties') or {}).get('select_options') or \
        (json_data.get('properties_release') or {}).get('select_options') or {}


def clean_generic_object_json(segment_json_data: dict, values: dict, mapping: dict):
    """
    Writes the values of a generic element, segment or dataset (``{layer: {field: value}}`` as read by
    :func:`parse_generic_object_json`) back into its JSON data, see :func:`clean_generic_field`.

    :raises ValueError: for an unknown layer or field name or a value that does not fit its field
    """
    properties: dict = segment_json_data['properties']
    select_options = select_options_of(segment_json_data)
    for (k, v) in values.items():
        layer_mapping = mapping.get(k, {})
        layer_key = layer_mapping.get('__key')
        layer = properties.get('layers').get(layer_key)
        if layer is None:
            available = [name for name in mapping if not name.startswith('__')]
            raise ValueError(f'Unknown layer "{k}". Available: {", ".join(available)}')
        fields = layer.get('fields')
        for (value_name, value_ob) in v.items():
            field_mapping = layer_mapping.get(value_name)
            field_key = ''
            if type(field_mapping) is str:
                field_key = field_mapping
            elif type(field_mapping) is dict:
                field_key = field_mapping.get('__field')
            field_obj = next((x for x in fields if x.get('field') == field_key), None)
            if field_obj is None:
                available = [name for name in layer_mapping if not name.startswith('__')]
                raise ValueError(f'Unknown field "{value_name}" in layer "{k}". Fields are named as in the template '
                                 f'version the element uses. Available: {", ".join(available)}')
            clean_generic_field(field_obj, value_ob, field_mapping, select_options)


def _check_generic_field_value(field_obj: dict, values: Any, select_options: dict | None) -> Any:
    """
    Checks a changed value of a field with a single value (select, system-defined, number, integer, checkbox,
    datetime, ontology-select, ...) against the template and returns it in the stored format, see
    :meth:`SegmentField.clean_value`. Unchanged values are returned as they are, so data loaded from the server
    can always be saved again.
    """
    current: Any
    if field_obj.get('type') == 'system-defined':
        current = {'value': field_obj.get('value'), 'unit': field_obj.get('value_system')}
    else:
        current = field_obj.get('value')
    if values == current:
        return values
    field = SegmentField(field_obj, '', select_options)
    try:
        return field.clean_value(values)
    except ValueError as e:
        raise ValueError(f'Invalid value for field "{field.label}": {e}') from None


def merge_dicts(*args) -> dict:
    dicts = list(args)
    if len(dicts) == 0:
        return {}
    res = dicts.pop(0)
    for d in dicts:
        _merge_dicts(res, d)
    return res


def _merge_dicts(a: dict | list, b: dict | list, path: list = None):
    if path is None:
        path = []

    if isinstance(b, dict):
        iterator = b.items()
    elif isinstance(b, list):
        iterator = enumerate(b)
    else:
        return

    def get_values(elem: list | dict, idx: str | int) -> any:
        if isinstance(elem, dict):
            return elem.get(idx)
        elif isinstance(elem, list):
            try:
                return elem[idx]
            except:
                pass
        return None

    def set_values(elem: list | dict, idx: str | int, value: any):
        if isinstance(elem, dict):
            elem[idx] = value
            return
        elif isinstance(elem, list):
            try:
                elem[idx] = value
            except:
                elem.append(value)

    for key, b_val in iterator:
        a_val = get_values(a, key)
        if isinstance(a_val, dict) and isinstance(b_val, dict):
            _merge_dicts(a_val, b_val, path + [str(key)])
        elif isinstance(a_val, list) and isinstance(b_val, list):
            _merge_dicts(a_val, b_val, path + [str(key)])
        else:
            set_values(a, key, b_val)
    return a


def snake_to_camel_case(snake_str):
    return "".join(x.capitalize() for x in snake_str.lower().split("_"))


class TypedList(list):
    def __init__(self, element_type, *args):
        self.element_type = element_type
        super().__init__(*args)
        self._check_elements()

    def _prepare_element(self, element):
        return element

    def after_append(self, element):
        pass

    def _check_elements(self):
        for element in self:
            self._check_element(element)

    def _check_element(self, element):
        if not isinstance(element, self.element_type):
            raise TypeError(f"All elements must be of type {self.element_type.__name__}")

    def append(self, element):
        self._check_element(element)
        prepared_element = self._prepare_element(element)
        super().append(prepared_element)
        self.after_append(prepared_element)
        return prepared_element

    def extend(self, iterable):
        for element in iterable:
            self.append(element)

    def insert(self, index, element):
        self._check_element(element)
        prepared_element = self._prepare_element(element)
        super().insert(index, prepared_element)
        self.after_append(prepared_element)

    def __setitem__(self, index, element):
        if isinstance(index, slice):
            for i in element:
                self._check_element(element)
        else:
            self._check_element(element)
        super().__setitem__(index, self._prepare_element(element))

    def __add__(self, other):
        x = copy.copy(self)
        x.extend(other)
        return x

    def __iadd__(self, other):
        self.extend(other)
        return self


def quill_hedging(input: str | dict, name: str) -> dict[str:list]:
    if isinstance(input, str):
        return {
            'ops': [
                {'insert': input}
            ]
        }
    if not isinstance(input, (dict, PropertyDict)) or 'ops' not in input or not isinstance(input['ops'], list):
        raise ValueError(f'{name} must be in the Quill.js format. (https://quilljs.com/docs/delta)')
    return input


def text_to_quill(text: str) -> dict:
    """Turn plain text into a Quill delta, the ELN's rich-text format — the counterpart of
    :func:`quill_to_text`.

    The result is a single insert ending in a newline, the shape the ELN's own editor creates
    (Quill 2 / quill-delta 5; the format is documented at https://quilljs.com/docs/delta). Use it
    to write a rich-text property::

        reaction.properties['observation'] = text_to_quill('turned yellow after 5 min')

    :raises TypeError: if ``text`` is not a string.
    """
    if not isinstance(text, str):
        raise TypeError(f'text_to_quill() takes a string, not {type(text).__name__}')
    return {'ops': [{'insert': text if text.endswith('\n') else text + '\n'}]}


def is_quill_document(value) -> bool:
    """Whether ``value`` is a well-formed Quill *document* delta: ``{"ops": [...]}`` whose ops are
    all inserts (text or an embed mapping), each with optional ``attributes``."""
    from collections.abc import Mapping
    if not isinstance(value, (Mapping, PropertyDict)) or not isinstance(value.get('ops'), list):
        return False
    for op in value['ops']:
        if not isinstance(op, Mapping) or set(op) - {'insert', 'attributes'} or 'insert' not in op:
            return False
        if not isinstance(op['insert'], (str, Mapping)):
            return False
        if 'attributes' in op and not isinstance(op['attributes'], Mapping):
            return False
    return True


def quill_to_text(value) -> str:
    """Flatten a Chemotion rich-text value to plain text.

    Chemotion stores descriptions and observations as Quill deltas
    (``{"ops": [{"insert": "..."}]}``), not strings. Anything that only accepts ``str`` therefore
    silently drops exactly the fields whose narrative matters.

    :param value: a delta mapping, a plain string, or ``None``.
    :return: the text, or ``""`` when there is none.
    """
    from collections.abc import Iterable, Mapping

    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping) and "ops" in value:
        ops = value["ops"]
        if isinstance(ops, Iterable):
            return "".join(op.get("insert", "") for op in ops
                           if isinstance(op, Mapping)).strip()
    return ""


def normalise_range_value(value: str) -> str | None:
    """Turn Chemotion's Ruby range strings into something a reader can use.

    Melting and boiling points arrive as serialised Ruby ranges. The ELN sets both to an infinite
    range on create (``sample.rb``: ``before_create :set_boiling_melting_points``), which
    serialises as ``"(,)"`` — so *every* sample carries two of them, meaning "unset". A degenerate
    range (``"-114...-114"``) is just a single value written twice.

    :param value: the raw range string.
    :return: a usable value, or ``None`` when the range carries no information.
    """
    text = value.strip()
    if not text or text in ("(,)", "(...)", "..."):
        return None
    for separator in ("...", ".."):
        if separator in text:
            low, _, high = text.partition(separator)
            low, high = low.strip("( )"), high.strip("( )")
            if not low and not high:
                return None
            if low == high:
                return low or None
            return f"{low}-{high}" if low and high else (low or high)
    return text


def break_parent_cycles(parent_of: dict) -> set:
    """Find nodes whose parent chain loops, so a caller can treat them as roots instead.

    A collection tree is built by pointing each node at its parent. If those links form a cycle —
    A's parent is B and B's parent is A, or a node is its own parent — then *every* node has a
    parent, no node qualifies as a root, and a tree builder that collects roots ends up with an
    empty list. The observed consequence was an export that silently produced an archive
    containing nothing at all, and exited successfully.

    Returning the offenders rather than raising lets the caller keep the salvageable data: promote
    them to roots and say so, instead of discarding the whole dump over one bad link.

    :param parent_of: node key -> parent key (or ``None`` for a root).
    :return: the keys that sit on a cycle; empty when the links form a proper forest.
    """
    cyclic: set = set()
    settled: set = set()          # known to terminate at a root
    for start in parent_of:
        if start in settled or start in cyclic:
            continue
        chain: list = []
        seen: set = set()
        node = start
        while node is not None and node in parent_of and node not in seen:
            seen.add(node)
            chain.append(node)
            node = parent_of.get(node)
        if node is not None and node in seen:
            # The walk re-entered itself at `node`. Only the suffix from there is the cycle;
            # the nodes before it merely *lead into* one and keep a perfectly good parent, so
            # promoting them to roots would flatten a subtree that was not itself broken.
            cyclic.update(chain[chain.index(node):])
        else:
            settled.update(chain)
    return cyclic


def safe_join(base, name: str):
    """Join ``name`` under ``base``, refusing anything that would escape it.

    Filenames that arrive in data — a crate's ``File.name``, a server's ``Content-Disposition``,
    an attachment record — are not trustworthy paths. Two ways they escape:

    * an **absolute** name: ``Path('/safe/out') / '/etc/passwd'`` is ``/etc/passwd``; pathlib
      discards the base entirely;
    * a **relative** traversal: ``../../`` is not normalised away by ``/``, and code that calls
      ``mkdir(parents=True)`` first will helpfully build the path there.

    :param base: the directory the result must stay inside.
    :param name: the untrusted filename.
    :return: the resolved path, guaranteed to be inside ``base``.
    :raises ValueError: if ``name`` escapes ``base``.
    """
    import os
    from pathlib import Path

    root = Path(base).resolve()
    leaf = os.path.basename(str(name or "").strip()) or "unnamed"
    dest = (root / leaf).resolve()
    if not dest.is_relative_to(root):
        raise ValueError(f"refusing to write outside {root}: {name!r}")
    return dest


def guess_mime_type(file_path: str) -> str:
    """The MIME type of the file at ``file_path``, for uploads.

    Uses python-magic (the file's content) when it and the native libmagic are available. It is
    imported here, not at module level, so ``import chemotion_api`` works without libmagic (e.g. on
    Windows, issue #24); without it the type is guessed from the file extension.
    """
    try:
        import magic
        file_magic = magic.Magic(mime=True)
    except (ImportError, OSError):
        import mimetypes
        return mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    return file_magic.from_file(file_path)
