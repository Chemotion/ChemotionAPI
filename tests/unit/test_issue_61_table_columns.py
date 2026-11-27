"""Issue #61: table columns of the types ELN 4.0.2's template designer offers.

The designer (chem-generic-ui bundled with ELN 4.0.2) offers eight column types: drag_molecule,
drag_sample, formula-field, number, select, select-multi, system-defined, text. Its formula editor
saves ``{formula: str, decimal: int >= 0 (default 5), refs: [{id, abbr}]}``, leaving out refs with
an empty ``abbr``. ``FORMULA`` below is the column of the template ``ttes`` on the test ELN.
"""
import copy
import json
import os

import pytest
from jsonschema import ValidationError

from chemotion_api.labImotion import GenericElementKlass
from chemotion_api.labImotion.items.fields import table_sub_fields as T
from chemotion_api.labImotion.items.options import FieldType, SubTableFieldType

FIXTURE = os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'GenericElement.json')
LAYER = 'aaa'

FORMULA = {"id": "2ea56479-5b80-4683-aa1a-7849c735292e", "refs": [], "type": "formula-field", "value": "",
           "decimal": 5, "formula": "", "col_name": "formula-field"}
NUMBER = {"id": "n1", "type": "number", "value": "", "col_name": "mass"}
SELECT_MULTI = {"id": "m1", "type": "select-multi", "value": "", "option_layers": "", "col_name": "tags"}
TEXT = {"id": "t1", "type": "text", "value": "", "col_name": "note"}


def _klass(*columns):
    with open(FIXTURE) as f:
        data = json.load(f)
    for where in ('properties_template', 'properties_release'):
        data[where]['layers'][LAYER]['fields'].append({
            'type': 'table', 'field': 'tbl', 'label': 'tbl', 'default': '', 'position': 99, 'required': False,
            'sub_fields': [copy.deepcopy(c) for c in columns], 'text_sub_fields': []})
    return GenericElementKlass(data, None)


def _table(klass):
    layer = next(lay for lay in klass.properties.layers if lay.key == LAYER)
    return next(f for f in layer.fields if f.field == 'tbl')


def _saved_columns(klass):
    fields = klass.to_dict()['properties_template']['layers'][LAYER]['fields']
    return next(f for f in fields if f['field'] == 'tbl')['sub_fields']


def _new_table():
    with open(FIXTURE) as f:
        klass = GenericElementKlass(json.load(f), None)
    return klass.properties.add_new_layer('Extra').add_field(FieldType.TABLE, 'Results')


# --- loading and round trip ---------------------------------------------------------------------

def test_the_formula_column_of_ttes_loads_and_round_trips():
    klass = _klass(FORMULA)
    (col,) = _table(klass).sub_fields
    assert isinstance(col, T.TSFormula)
    assert (col.formula, col.refs, col.decimal) == ('', [], 5)
    assert _saved_columns(klass) == [FORMULA]


def test_a_formula_column_with_refs_round_trips():
    formula = {**FORMULA, 'id': 'f1', 'formula': 'a*2+b', 'decimal': 2,
               'refs': [{'id': 'n1', 'abbr': 'a'}, {'id': 't1', 'abbr': 'b'}]}
    klass = _klass(NUMBER, TEXT, formula)
    assert _saved_columns(klass) == [NUMBER, TEXT, formula]


def test_number_and_select_multi_columns_are_typed():
    klass = _klass(TEXT, NUMBER, SELECT_MULTI)
    assert [type(c) for c in _table(klass).sub_fields] == [T.TSText, T.TSNumber, T.TSSelectMulti]
    assert _saved_columns(klass) == [TEXT, NUMBER, SELECT_MULTI]


def test_an_unknown_column_type_is_kept_and_the_other_columns_stay_typed():
    future = {"id": "x1", "type": "future-column", "value": "", "col_name": "x", "widget": {"a": 1}}
    klass = _klass(TEXT, future)
    text, opaque = _table(klass).sub_fields
    assert isinstance(text, T.TSText)
    assert isinstance(opaque, T.TSOpaque)
    assert _saved_columns(klass) == [TEXT, future]


def test_a_decimal_stored_as_text_is_read_as_a_number():
    klass = _klass({**FORMULA, 'decimal': '3'})
    assert _table(klass).sub_fields[0].decimal == 3


def test_a_known_column_type_still_may_not_carry_unknown_keys():
    with pytest.raises(ValidationError, match='bogus'):
        _klass({**TEXT, 'bogus': 1})


# --- authoring ------------------------------------------------------------------------------------

def test_a_formula_column_can_be_authored():
    table = _new_table()
    mass = table.add_subfield(SubTableFieldType.NUMBER, 'mass')
    count = table.add_subfield(SubTableFieldType.NUMBER, 'count')
    calc = table.add_subfield(SubTableFieldType.FORMULA_FIELD, 'per item')
    calc.add_ref(mass, 'm').add_ref(count.id, 'n')
    calc.formula = 'm/n'
    calc.decimal = 2
    assert calc.to_dict() == {'id': calc.id, 'col_name': 'per item', 'type': 'formula-field', 'value': '',
                              'formula': 'm/n', 'refs': [{'id': mass.id, 'abbr': 'm'}, {'id': count.id, 'abbr': 'n'}],
                              'decimal': 2}


def test_a_new_formula_column_starts_as_the_designer_starts_it():
    calc = _new_table().add_subfield(SubTableFieldType.FORMULA_FIELD, 'calc')
    assert (calc.formula, calc.refs, calc.decimal) == ('', [], 5)


@pytest.mark.parametrize('decimal, error', [(-1, ValueError), (1.5, TypeError), (True, TypeError), ('x', ValueError)])
def test_decimal_takes_a_whole_number_of_zero_or_more(decimal, error):
    calc = _new_table().add_subfield(SubTableFieldType.FORMULA_FIELD, 'calc')
    with pytest.raises(error):
        calc.decimal = decimal


@pytest.mark.parametrize('refs, error', [
    ('a', TypeError), ([{'id': 'n1'}], ValueError), ([{'id': 'n1', 'abbr': ''}], ValueError),
    ([{'id': 1, 'abbr': 'a'}], TypeError), ([{'id': 'n1', 'abbr': 'a', 'x': 1}], ValueError)])
def test_refs_are_id_and_abbr_pairs(refs, error):
    calc = _new_table().add_subfield(SubTableFieldType.FORMULA_FIELD, 'calc')
    with pytest.raises(error):
        calc.refs = refs


def test_a_number_column_takes_numbers():
    col = _new_table().add_subfield(SubTableFieldType.NUMBER, 'mass')
    col.value = 2.5
    assert col.value == '2.5'
    with pytest.raises(ValueError):
        col.value = 'abc'


#: A number column of ``ttes``: the designer stores the column's number settings like a number field's.
NUMBER_WITH_SETTINGS = {"id": "4d3d18cc-5ed4-482b-bfca-e7ee969ed1ae", "type": "number", "value": "",
                        "numeric": {"max": "", "min": "", "decimals": 0}, "col_name": "number"}


def test_a_number_column_with_numeric_settings_loads_and_round_trips():
    klass = _klass(NUMBER_WITH_SETTINGS)
    (col,) = _table(klass).sub_fields
    assert col.numeric == {"max": "", "min": "", "decimals": 0}
    assert _saved_columns(klass) == [NUMBER_WITH_SETTINGS]


def test_numeric_settings_of_a_number_column_can_be_set():
    col = _new_table().add_subfield(SubTableFieldType.NUMBER, 'mass')
    assert 'numeric' not in col.to_dict()
    col.numeric = {'decimals': 2, 'min': 0}
    assert col.to_dict()['numeric'] == {'decimals': 2, 'min': 0}
    for bad, error in [({'decimals': -1}, ValueError), ({'step': 1}, ValueError), ({'min': True}, TypeError)]:
        with pytest.raises(error):
            col.numeric = bad


# --- review fixes -----------------------------------------------------------------------------------

@pytest.mark.parametrize('future', [
    {"id": "x1", "type": "future-column", "value": [], "col_name": "x"},
    {"id": "x1", "type": "future-column", "col_name": "x", "numeric": {"step": 1}, "refs": "all"},
])
def test_an_unknown_column_type_is_kept_whatever_its_values(future):
    klass = _klass(TEXT, future)
    assert _saved_columns(klass) == [TEXT, future]


@pytest.mark.parametrize('column', [
    {**NUMBER, 'numeric': {'decimals': '2', 'min': None, 'max': ''}},
    {**FORMULA, 'refs': [{'id': 'n1', 'abbr': 'a', 'label': 'mass'}]},
])
def test_settings_the_setters_refuse_are_kept_as_stored(column):
    assert _saved_columns(_klass(column)) == [column]


def test_refs_take_valid_unique_abbrs_and_not_the_column_itself():
    calc = _new_table().add_subfield(SubTableFieldType.FORMULA_FIELD, 'calc')
    for refs in ([{'id': 'n1', 'abbr': '1x'}], [{'id': 'n1', 'abbr': 'a b'}],
                 [{'id': 'n1', 'abbr': 'a'}, {'id': 'n2', 'abbr': 'a'}]):
        with pytest.raises(ValueError):
            calc.refs = refs
    with pytest.raises(ValueError):
        calc.add_ref(calc, 'c')
    with pytest.raises(ValueError):
        calc.decimal = '²'


def test_numeric_bounds_are_numbers_and_min_is_not_above_max():
    col = _new_table().add_subfield(SubTableFieldType.NUMBER, 'mass')
    for bad in ({'min': 'abc'}, {'min': 5, 'max': '1'}):
        with pytest.raises(ValueError):
            col.numeric = bad
    col.numeric = {'min': '', 'max': '2,5'}


def test_to_dict_does_not_share_the_columns_settings():
    table = _new_table()
    num = table.add_subfield(SubTableFieldType.NUMBER, 'mass')
    num.numeric = {'decimals': 1}
    num.to_dict()['numeric']['decimals'] = 9
    calc = table.add_subfield(SubTableFieldType.FORMULA_FIELD, 'calc').add_ref(num, 'm')
    calc.to_dict()['refs'][0]['abbr'] = 'x'
    assert (num.numeric, calc.refs) == ({'decimals': 1}, [{'id': num.id, 'abbr': 'm'}])


@pytest.mark.parametrize('bad', [{'min': None}, {'max': None}, {'decimals': None}])
def test_numeric_settings_are_never_written_as_null(bad):
    col = _new_table().add_subfield(SubTableFieldType.NUMBER, 'mass')
    with pytest.raises(TypeError):
        col.numeric = bad


def test_an_unknown_column_without_col_name_round_trips_exactly():
    future = {"id": "x1", "type": "future-column"}
    assert _saved_columns(_klass(future)) == [future]


def test_the_numeric_settings_of_an_input_group_number_are_kept():
    with open(FIXTURE) as f:
        data = json.load(f)
    group = {'type': 'input-group', 'field': 'grp', 'label': 'grp', 'default': '', 'position': 98,
             'required': False, 'text_sub_fields': [],
             'sub_fields': [{'id': 's1', 'type': 'number', 'value': '1',
                             'numeric': {'decimals': 2, 'min': '', 'max': ''}}]}
    for where in ('properties_template', 'properties_release'):
        data[where]['layers'][LAYER]['fields'].append(copy.deepcopy(group))
    fields = GenericElementKlass(data, None).to_dict()['properties_template']['layers'][LAYER]['fields']
    assert next(f for f in fields if f['field'] == 'grp')['sub_fields'] == group['sub_fields']
