"""Checks added with the port of #43/#47 onto the LabIMotion line, beyond the tests of those two PRs."""
import copy
import json
import os

import pytest

from chemotion_api.labImotion import GenericElementKlass
from chemotion_api.labImotion.items.options import FieldType
from chemotion_api.utils import clean_generic_object_json, parse_generic_object_json
from chemotion_api.utils.segment_fields import SegmentField

FIXTURE = os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'GenericElement.json')


def _null_range_record() -> dict:
    parts = [{'id': 'p1', 'type': 'text', 'value': None, 'col_name': 'timeStart'},
             {'id': 'p2', 'type': 'text', 'value': None, 'col_name': 'timeStop'},
             {'id': 'p4', 'type': 'text', 'value': None, 'col_name': 'duration', 'option_layers': 'duration',
              'value_system': None}]
    field = {'type': 'datetime-range', 'field': 'range', 'label': 'Range', 'position': 1, 'sub_fields': parts}
    return {'id': 1, 'properties': {'layers': {'l': {'key': 'l', 'label': 'L', 'position': 1, 'fields': [field]}}}}


@pytest.mark.parametrize('value', [
    None,
    {'timeStart': None, 'timeStop': ''},
    {'duration': {'value': None}},
    {'duration': {'value': '', 'unit': 'd'}},
    {'timeStart': '', 'timeStop': '', 'duration': {'value': '', 'unit': 'd'}},
], ids=['none', 'none-parts', 'none-duration', 'empty-duration', 'empty-form'])
def test_writing_the_empty_form_over_null_range_parts_leaves_them_as_stored(value):
    record = _null_range_record()
    before = json.dumps(record, sort_keys=True)
    parsed = parse_generic_object_json(record)
    parsed['values']['L']['Range'] = value
    clean_generic_object_json(record, parsed['values'], parsed['obj_mapping'])
    assert json.dumps(record, sort_keys=True) == before


def test_select_multi_table_column_takes_keys_as_given_if_the_options_are_unknown():
    column = {'id': 'c1', 'col_name': 'Multi', 'type': 'select-multi', 'option_layers': 'unknown'}
    assert SegmentField(column, '', {}).clean_value(['a', 'b', 'a']) == ['a', 'b']
    known = {'unknown': {'options': [{'key': 'a', 'label': 'A'}]}}
    assert SegmentField(column, '', known).clean_value(['A']) == ['a']
    with pytest.raises(ValueError, match='"b" is not an option'):
        SegmentField(column, '', known).clean_value(['b'])


@pytest.fixture
def klass():
    with open(FIXTURE) as f:
        return GenericElementKlass(json.load(f), None)


def test_formula_decimal_refuses_a_trailing_newline(klass):
    field = klass.properties.add_new_layer('F').add_field(FieldType.FORMULA_FIELD, 'F')
    field.decimal = '3'
    with pytest.raises(TypeError):
        field.decimal = '3\n'
    assert field.decimal == '3'


def test_layer_style_refuses_a_trailing_newline(klass):
    layer = klass.properties.add_new_layer('S')
    layer.style = 'panel_generic_heading_bu'
    with pytest.raises(TypeError):
        layer.style = 'panel_generic_heading\n'
    assert copy.copy(layer.style) == 'panel_generic_heading_bu'
