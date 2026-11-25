"""Values of generic (LabIMotion) elements and segments, as ELN 4.0.2 (LabIMotion 2.3.4, chem-generic-ui 2.3.2)
stores them.

* select-multi and datetime-range fields keep their value in ``sub_fields``; both read as None and a
  changed value was dropped (or written into ``value``, which the web form ignores).
* of two fields with the same label, a first one reading as None was overwritten by the second.
* ``element_klass: null`` (an element shared below detail level 10) crashed ``label`` and friends, and
  ``klass_version`` gave the template's current version, not the release the element was saved with.
* the ELN drops ``select_options`` from a saved element's ``properties``; they are in ``properties_release``.
* a field or layer label of None crashed the reader, and reading reordered the raw fields.
* a table row without a cell for a column raised KeyError.
"""
import copy
import json
from types import SimpleNamespace

import pytest

from chemotion_api.elements.abstract_element import AbstractElement
from chemotion_api.elements.generic_element import GenericElement
from chemotion_api.utils import add_to_dict, clean_generic_object_json, parse_generic_layer, \
    parse_generic_object_json, parse_generic_object_layer_json

OPTIONS = {'colours': {'options': [{'key': 'red', 'label': 'Red'}, {'key': 'blue', 'label': 'Blue'},
                                   {'key': 'green', 'label': 'Green'}]}}


def _range_parts(start='01/02/2025 10:00:00', stop='02/02/2025 10:00:00', duration='1', unit='d'):
    # as the web form creates them (chem-generic-ui 2.3.2)
    return [{'id': 'p1', 'type': 'text', 'value': start, 'col_name': 'timeStart'},
            {'id': 'p2', 'type': 'text', 'value': stop, 'col_name': 'timeStop'},
            {'id': 'p3', 'type': 'text', 'value': '', 'col_name': 'durationCalc'},
            {'id': 'p4', 'type': 'text', 'value': duration, 'col_name': 'duration', 'option_layers': 'duration',
             'value_system': unit}]


def _record(multi=None, parts=None, select_options_in_properties=True) -> dict:
    fields = [
        {'type': 'select-multi', 'field': 'multi', 'label': 'Multi', 'position': 1, 'option_layers': 'colours',
         'sub_fields': [{'value': k} for k in (multi or [])]},
        {'type': 'datetime-range', 'field': 'range', 'label': 'Range', 'position': 2, 'sub_fields': parts or []},
        {'type': 'select', 'field': 'colour', 'label': 'Colour', 'position': 3, 'option_layers': 'colours',
         'value': 'red'},
    ]
    properties = {'layers': {'l': {'key': 'l', 'label': 'L', 'position': 1, 'fields': fields}}}
    if select_options_in_properties:
        properties['select_options'] = copy.deepcopy(OPTIONS)
    return {'id': 1, 'properties': properties,
            'properties_release': {'version': '1.0', 'select_options': copy.deepcopy(OPTIONS), 'layers': {}}}


def _round_trip(record: dict, change=None) -> dict:
    parsed = parse_generic_object_json(record)
    if change is not None:
        change(parsed['values'])
    clean_generic_object_json(record, parsed['values'], parsed['obj_mapping'])
    return record


def _fields(record: dict) -> dict:
    return {f['field']: f for f in record['properties']['layers']['l']['fields']}


# --- select-multi and datetime-range: read ---------------------------------------------------------

def test_select_multi_reads_the_option_keys():
    values = parse_generic_object_json(_record(multi=['red', 'blue']))['values']
    assert values['L']['Multi'] == ['red', 'blue']
    assert parse_generic_object_json(_record())['values']['L']['Multi'] == []


def test_datetime_range_reads_start_stop_and_duration():
    values = parse_generic_object_json(_record(parts=_range_parts(duration='3', unit='h')))['values']
    assert values['L']['Range'] == {'timeStart': '01/02/2025 10:00:00', 'timeStop': '02/02/2025 10:00:00',
                                    'duration': {'value': '3', 'unit': 'h'}}


def test_datetime_range_without_parts_reads_as_the_empty_form():
    values = parse_generic_object_json(_record())['values']
    assert values['L']['Range'] == {'timeStart': '', 'timeStop': '', 'duration': {'value': '', 'unit': 'd'}}


# --- select-multi and datetime-range: write --------------------------------------------------------

@pytest.mark.parametrize('record', [
    _record(multi=['red', 'blue'], parts=_range_parts()),
    _record(),
    _record(multi=['red'], parts=_range_parts(), select_options_in_properties=False),
], ids=['filled', 'empty', 'saved-record'])
def test_unchanged_save_leaves_the_raw_json_as_it_was(record):
    before = json.dumps(record, sort_keys=True)
    assert json.dumps(_round_trip(record), sort_keys=True) == before


def test_select_multi_is_written_into_sub_fields():
    def change(values):
        values['L']['Multi'] = ['green', 'red']
    field = _fields(_round_trip(_record(multi=['red']), change))['multi']
    assert field['sub_fields'] == [{'value': 'green'}, {'value': 'red'}]
    assert 'value' not in field
    assert parse_generic_object_json({'properties': {'layers': {'l': {'label': 'L', 'fields': [field]}}}}) \
        ['values']['L']['Multi'] == ['green', 'red']


def test_select_multi_refuses_unknown_keys_if_the_options_are_known():
    def change(values):
        values['L']['Multi'] = ['red', 'purple']
    with pytest.raises(ValueError, match="'purple'"):
        _round_trip(_record(), change)


def test_select_multi_takes_keys_as_given_if_the_options_are_unknown():
    record = _record()
    del record['properties']['select_options']
    del record['properties_release']['select_options']

    def change(values):
        values['L']['Multi'] = ['purple']
    assert _fields(_round_trip(record, change))['multi']['sub_fields'] == [{'value': 'purple'}]


def test_datetime_range_is_written_into_its_sub_fields():
    def change(values):
        values['L']['Range'] = {'timeStart': '03/02/2025 08:00:00', 'timeStop': '02/02/2025 10:00:00',
                                'duration': {'value': '2', 'unit': 'h'}}
    field = _fields(_round_trip(_record(parts=_range_parts()), change))['range']
    assert 'value' not in field
    parts = {p['col_name']: p for p in field['sub_fields']}
    assert [p['id'] for p in field['sub_fields']] == ['p1', 'p2', 'p3', 'p4']
    assert parts['timeStart']['value'] == '03/02/2025 08:00:00'
    assert parts['timeStop']['value'] == '02/02/2025 10:00:00'
    assert (parts['duration']['value'], parts['duration']['value_system']) == ('2', 'h')


def test_datetime_range_creates_the_parts_as_the_web_form_does():
    def change(values):
        values['L']['Range'] = {'timeStart': '03/02/2025 08:00:00', 'duration': 5}
    field = _fields(_round_trip(_record(), change))['range']
    assert [p['col_name'] for p in field['sub_fields']] == ['timeStart', 'timeStop', 'durationCalc', 'duration']
    assert all(p['type'] == 'text' and p['id'] for p in field['sub_fields'])
    duration = field['sub_fields'][3]
    assert (duration['value'], duration['value_system'], duration['option_layers']) == (5, 'd', 'duration')
    assert parse_generic_object_json(_record(parts=field['sub_fields']))['values']['L']['Range'] == \
        {'timeStart': '03/02/2025 08:00:00', 'timeStop': '', 'duration': {'value': 5, 'unit': 'd'}}


def test_datetime_range_refuses_unknown_parts():
    def change(values):
        values['L']['Range'] = {'durationCalc': '1'}
    with pytest.raises(ValueError, match='durationCalc'):
        _round_trip(_record(parts=_range_parts()), change)


# --- fields with the same label ---------------------------------------------------------------------

def test_add_to_dict_does_not_overwrite_a_none_value():
    values = {'Name': None}
    assert add_to_dict(values, 'Name', 'x') == 'Name.1'
    assert values == {'Name': None, 'Name.1': 'x'}


def test_a_field_reading_none_is_not_overwritten_by_a_field_with_the_same_label():
    layer = {'fields': [{'type': 'text', 'field': 'a', 'label': 'Same', 'position': 1},
                        {'type': 'text', 'field': 'b', 'label': 'Same', 'position': 2, 'value': 'x'}]}
    parsed = parse_generic_layer('l', layer)
    assert parsed['values'] == {'Same': None, 'Same.1': 'x'}
    assert parsed['obj_mapping'] == {'__key': 'l', 'Same': 'a', 'Same.1': 'b'}


# --- GenericElement ---------------------------------------------------------------------------------

def _element(json_data: dict) -> GenericElement:
    element = GenericElement(SimpleNamespace(), SimpleNamespace(), id=1, element_type='plan', avoid_load=True)
    element.json_data = json_data
    return element


def test_klass_properties_of_an_element_with_a_withheld_klass():
    element = _element({'element_klass': None, 'properties_release': {}})
    assert (element.label, element.klass_name, element.klass_version, element.klass_prefix) == \
           (None, None, None, None)


def test_klass_version_is_the_release_the_element_was_saved_with():
    klass = {'label': 'Plan', 'name': 'plan', 'version': '2.0', 'klass_prefix': 'PLN'}
    assert _element({'element_klass': klass, 'properties_release': {'version': '1.0'}}).klass_version == '1.0'
    assert _element({'element_klass': klass, 'properties_release': {}}).klass_version == '2.0'


def test_field_options_of_a_saved_element_come_from_its_release():
    record = _record(select_options_in_properties=False)
    element = _element(record)
    element._properties_mapping = parse_generic_object_json(record)['obj_mapping']
    assert [o['key'] for o in element.field('L', 'Colour').options()] == ['red', 'blue', 'green']


def test_a_select_value_can_be_written_to_a_saved_element():
    def change(values):
        values['L']['Colour'] = 'Blue'
    assert _fields(_round_trip(_record(select_options_in_properties=False), change))['colour']['value'] == 'blue'


def test_segment_field_options_of_a_saved_segment_come_from_its_release():
    segment = _record(select_options_in_properties=False)
    element = AbstractElement(SimpleNamespace(), SimpleNamespace(), id=1, element_type='sample', avoid_load=True)
    element.json_data = {'segments': [segment]}
    element._segments_mapping = {'Seg': parse_generic_object_json(segment)['obj_mapping']}
    assert [o['key'] for o in element._segment_field('Seg', 'L', 'Colour').options()] == ['red', 'blue', 'green']


# --- labels and field order -------------------------------------------------------------------------

def test_a_field_without_label_is_named_by_its_key():
    layer = {'fields': [{'type': 'text', 'field': 'f1', 'label': None, 'position': 1, 'value': 'x'}]}
    assert parse_generic_layer('l', layer)['values'] == {'f1': 'x'}


def test_a_layer_without_label_is_named_by_its_key():
    values: dict = {}
    assert parse_generic_object_layer_json('k', {'key': 'k', 'label': None, 'fields': []}, values, {}) == 'k'
    assert values == {'k': {}}


def test_reading_does_not_reorder_the_raw_fields():
    layer = {'fields': [{'type': 'text', 'field': 'b', 'label': 'B', 'position': 2},
                        {'type': 'text', 'field': 'a', 'label': 'A', 'position': 1}]}
    assert list(parse_generic_layer('l', layer)['values']) == ['A', 'B']
    assert [f['field'] for f in layer['fields']] == ['b', 'a']


# --- table rows -------------------------------------------------------------------------------------

def _table_record() -> dict:
    table = {'type': 'table', 'field': 'tbl', 'label': 'Table', 'position': 1,
             'sub_fields': [{'id': 'c1', 'col_name': 'A', 'type': 'text'},
                            {'id': 'c2', 'col_name': 'B', 'type': 'text'}],  # B added after the row
             'sub_values': [{'id': 'r1', 'c1': 'x'}]}
    return {'id': 1, 'properties': {'layers': {'l': {'key': 'l', 'label': 'L', 'position': 1, 'fields': [table]}}}}


def test_a_table_row_without_a_cell_reads_it_as_none():
    assert parse_generic_object_json(_table_record())['values']['L']['Table'] == [{'A': 'x', 'B': None}]


def test_a_table_row_without_a_cell_saves():
    record = _table_record()
    before = json.dumps(record, sort_keys=True)
    assert json.dumps(_round_trip(record), sort_keys=True) == before

    def change(values):
        values['L']['Table'][0]['B'] = 'y'
    assert _round_trip(record, change)['properties']['layers']['l']['fields'][0]['sub_values'] == \
        [{'id': 'r1', 'c1': 'x', 'c2': 'y'}]


# --- review fixes -----------------------------------------------------------------------------------

def test_an_untouched_datetime_range_with_null_parts_is_left_as_stored():
    parts = _range_parts()
    for part in parts:
        part['value'] = None
    parts[3]['value_system'] = None
    parts = parts[:2] + parts[3:]  # no durationCalc: a save must not add it either
    record = _record(parts=copy.deepcopy(parts))
    values = parse_generic_object_json(record)['values']
    assert values['L']['Range'] == {'timeStart': '', 'timeStop': '', 'duration': {'value': '', 'unit': 'd'}}
    assert _fields(_round_trip(record))['range']['sub_fields'] == parts


def test_a_generic_segment_labelled_properties_keeps_the_builtin_names():
    """`add_to_dict` no longer overwrites None, and every segment not added yet is a None placeholder."""
    from chemotion_api.elements.sample import Sample
    from test_sample_properties import SESSION, _sample_json

    segments = SimpleNamespace(all_classes=[
        {'id': 9, 'label': label, 'element_klass': {'name': 'sample'}} for label in ('Properties', 'Analyses')])
    sample = Sample(segments, SESSION, json_data=_sample_json(1))
    keys = dict.keys(sample._segments)
    assert 'Properties.1' not in keys and 'Analyses.1' not in keys
    assert dict.__getitem__(sample._segments, 'Analyses') is sample._analyses
