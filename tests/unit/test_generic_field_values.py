"""
Values of LabIMotion generic fields (elements, segments, datasets) are read and written in the shape the
ELN web form (chem-generic-ui 2.3.2, LabIMotion 2.3.4) stores them.
"""
import copy
import datetime
import json

import pytest

from chemotion_api.utils import TableRow, clean_generic_object_json, parse_generic_object_json

SELECT_OPTIONS = {
    'colours': {'options': [{'key': 'red', 'label': 'Red colour'},
                            {'key': 'green', 'label': 'Green colour'},
                            {'key': 'blue', 'label': 'Blue colour'}]},
}

COLUMNS = [
    {'id': 'c-text', 'type': 'text', 'value': '', 'col_name': 'Text'},
    {'id': 'c-num', 'type': 'number', 'value': '', 'col_name': 'Num',
     'numeric': {'decimals': 2, 'min': 0, 'max': 100}},
    {'id': 'c-sel', 'type': 'select', 'value': '', 'col_name': 'Sel', 'option_layers': 'colours'},
    {'id': 'c-multi', 'type': 'select-multi', 'value': '', 'col_name': 'Multi', 'option_layers': 'colours'},
    {'id': 'c-sys', 'type': 'system-defined', 'value': '', 'col_name': 'Temp', 'option_layers': 'temperature',
     'value_system': 'C'},
    {'id': 'c-form', 'type': 'formula-field', 'value': '', 'col_name': 'Form', 'formula': 'a*2', 'decimal': 5,
     'refs': [{'id': 'c-num', 'abbr': 'a'}]},
    {'id': 'c-mol', 'type': 'drag_molecule', 'value': 'inchikey', 'col_name': 'Mol'},
    {'id': 'c-sam', 'type': 'drag_sample', 'value': 'name', 'col_name': 'Sam'},
]

MOLECULE_CELL = {'el_id': 7, 'el_type': 'molecule', 'el_label': 'water', 'el_inchikey': 'XLYOFNOQVPJJNP',
                 'el_smiles': 'O', 'el_iupac': 'oxidane', 'el_molecular_weight': 18.0,
                 'el_svg': '/images/molecules/a.svg'}


def _fields():
    return [
        {'type': 'text', 'field': 'text', 'label': 'Text', 'position': 1, 'value': ''},
        {'type': 'number', 'field': 'number', 'label': 'Number', 'position': 2, 'value': '',
         'numeric': {'decimals': 1, 'min': -5, 'max': 50}},
        {'type': 'number', 'field': 'number_plain', 'label': 'Plain number', 'position': 3, 'value': ''},
        {'type': 'checkbox', 'field': 'checkbox', 'label': 'Checkbox', 'position': 4, 'value': False},
        {'type': 'select', 'field': 'select', 'label': 'Select', 'position': 5, 'value': '',
         'option_layers': 'colours'},
        {'type': 'select-multi', 'field': 'multi', 'label': 'Multi', 'position': 6, 'value': '',
         'option_layers': 'colours', 'sub_fields': []},
        {'type': 'system-defined', 'field': 'temp', 'label': 'Temp', 'position': 7, 'value': '',
         'option_layers': 'temperature', 'value_system': 'C'},
        {'type': 'datetime', 'field': 'when', 'label': 'When', 'position': 8},
        {'type': 'datetime-range', 'field': 'range', 'label': 'Range', 'position': 9, 'sub_fields': []},
        {'type': 'ontology-select', 'field': 'onto', 'label': 'Onto', 'position': 10, 'value': '',
         'ontology_term': 'http://purl.obolibrary.org/obo/CHMO_0000575'},
        {'type': 'formula-field', 'field': 'formula', 'label': 'Formula', 'position': 11, 'value': '',
         'formula': 'number*2', 'canAdjust': True},
        {'type': 'text-formula', 'field': 'tformula', 'label': 'Text formula', 'position': 12,
         'text_sub_fields': [{'id': 'x', 'layer': 'one', 'field': 'text', 'separator': '-'}]},
        {'type': 'input-group', 'field': 'group', 'label': 'Group', 'position': 13, 'sub_fields': [
            {'id': 'g-label', 'type': 'label', 'value': 'Fixed'},
            {'id': 'g-num', 'type': 'number', 'value': ''},
            {'id': 'g-text', 'type': 'text', 'value': ''},
            {'id': 'g-sys', 'type': 'system-defined', 'value': '', 'option_layers': 'temperature',
             'value_system': 'K'},
        ]},
        {'type': 'table', 'field': 'table', 'label': 'Table', 'position': 14,
         'sub_fields': copy.deepcopy(COLUMNS), 'sub_values': []},
        {'type': 'drag_element', 'field': 'link', 'label': 'Link', 'position': 15, 'value': ''},
        {'type': 'drag_sample', 'field': 'sample', 'label': 'Sample', 'position': 16, 'value': ''},
        {'type': 'drag_molecule', 'field': 'molecule', 'label': 'Molecule', 'position': 17, 'value': ''},
        {'type': 'upload', 'field': 'upload', 'label': 'Upload', 'position': 18,
         'value': {'files': [{'uid': 'u1', 'filename': 'a.txt', 'aid': 3}]}},
        {'type': 'dummy', 'field': 'dummy', 'label': '', 'position': 19},
        {'type': 'integer', 'field': 'int', 'label': 'Int', 'position': 20, 'value': ''},
    ]


def _element():
    return {'id': 1, 'properties': {
        'select_options': copy.deepcopy(SELECT_OPTIONS),
        'layers': {'one': {'key': 'one', 'label': 'L', 'position': 1, 'fields': _fields()}},
    }}


def _parse(json_data):
    res = parse_generic_object_json(json_data)
    return res['values'], res['obj_mapping']


def _save(json_data, values, mapping):
    """Writes the values, sends them through JSON like a save and parses them again."""
    clean_generic_object_json(json_data, values, mapping)
    stored = json.loads(json.dumps(json_data))
    return stored, _parse(stored)[0]


def _field(json_data, key):
    return next(f for f in json_data['properties']['layers']['one']['fields'] if f['field'] == key)


# --- select-multi -------------------------------------------------------------------------------

def test_select_multi_reads_the_selected_keys_from_sub_fields():
    data = _element()
    _field(data, 'multi')['sub_fields'] = [{'value': 'red'}, {'value': 'blue'}]
    values, _ = _parse(data)
    assert values['L']['Multi'] == ['red', 'blue']

    _field(data, 'multi')['sub_fields'] = []
    assert _parse(data)[0]['L']['Multi'] == []


def test_select_multi_writes_keys_as_the_ui_does():
    data = _element()
    values, mapping = _parse(data)
    values['L']['Multi'] = ['Green colour', 'red', 'green']
    stored, reloaded = _save(data, values, mapping)
    assert _field(stored, 'multi')['sub_fields'] == [{'value': 'green'}, {'value': 'red'}]
    assert reloaded['L']['Multi'] == ['green', 'red']

    values, mapping = _parse(stored)
    values['L']['Multi'] = []
    stored, reloaded = _save(stored, values, mapping)
    assert _field(stored, 'multi')['sub_fields'] == [] and reloaded['L']['Multi'] == []


def test_select_multi_refuses_unknown_options():
    data = _element()
    values, mapping = _parse(data)
    values['L']['Multi'] = ['red', 'purple']
    with pytest.raises(ValueError, match='purple'):
        clean_generic_object_json(data, values, mapping)


def test_select_multi_of_the_system_user_list_takes_user_ids():
    data = _element()
    _field(data, 'multi')['option_layers'] = '-su03-'
    values, mapping = _parse(data)
    values['L']['Multi'] = [4, '5']
    stored, reloaded = _save(data, values, mapping)
    assert _field(stored, 'multi')['sub_fields'] == [{'value': '4'}, {'value': '5'}]


# --- datetime-range -----------------------------------------------------------------------------

def test_datetime_range_reads_its_sub_fields():
    data = _element()
    _field(data, 'range')['sub_fields'] = [
        {'id': 'a', 'type': 'text', 'value': '01/02/2025 10:00:00', 'col_name': 'timeStart'},
        {'id': 'b', 'type': 'text', 'value': '02/02/2025 10:00:00', 'col_name': 'timeStop'},
        {'id': 'c', 'type': 'text', 'value': '', 'col_name': 'durationCalc'},
        {'id': 'd', 'type': 'text', 'value': 24, 'col_name': 'duration', 'option_layers': 'duration',
         'value_system': 'h'},
    ]
    values, _ = _parse(data)
    assert values['L']['Range'] == {'timeStart': '01/02/2025 10:00:00', 'timeStop': '02/02/2025 10:00:00',
                                    'duration': {'value': 24, 'unit': 'h'}}


def test_datetime_range_without_sub_fields_reads_as_empty():
    values, _ = _parse(_element())
    assert values['L']['Range'] == {'timeStart': '', 'timeStop': '', 'duration': {'value': '', 'unit': 'd'}}


def test_datetime_range_writes_the_four_sub_fields_of_the_ui():
    data = _element()
    values, mapping = _parse(data)
    values['L']['Range'] = {'timeStart': datetime.datetime(2025, 2, 1, 9, 5, 7),
                            'timeStop': '02/02/2025 10:00:00', 'duration': {'value': 1.5, 'unit': 'd'}}
    stored, reloaded = _save(data, values, mapping)
    sub_fields = _field(stored, 'range')['sub_fields']
    assert [s['col_name'] for s in sub_fields] == ['timeStart', 'timeStop', 'durationCalc', 'duration']
    assert all(s['type'] == 'text' and s['id'] for s in sub_fields)
    assert sub_fields[0]['value'] == '01/02/2025 09:05:07'
    assert sub_fields[2]['value'] == ''
    assert (sub_fields[3]['option_layers'], sub_fields[3]['value_system'], sub_fields[3]['value']) == \
        ('duration', 'd', 1.5)
    assert reloaded['L']['Range'] == {'timeStart': '01/02/2025 09:05:07', 'timeStop': '02/02/2025 10:00:00',
                                      'duration': {'value': 1.5, 'unit': 'd'}}

    # a partial dict changes only the given parts and keeps the sub-field ids
    ids = [s['id'] for s in sub_fields]
    values, mapping = _parse(stored)
    values['L']['Range'] = {'duration': 3}
    stored, reloaded = _save(stored, values, mapping)
    assert [s['id'] for s in _field(stored, 'range')['sub_fields']] == ids
    assert reloaded['L']['Range']['duration'] == {'value': 3, 'unit': 'd'}
    assert reloaded['L']['Range']['timeStart'] == '01/02/2025 09:05:07'


def test_datetime_range_refuses_bad_parts():
    data = _element()
    values, mapping = _parse(data)
    values['L']['Range'] = {'start': '01/02/2025 10:00:00'}
    with pytest.raises(ValueError, match='start'):
        clean_generic_object_json(copy.deepcopy(data), values, mapping)
    values['L']['Range'] = {'duration': {'value': 2, 'unit': 'weeks'}}
    with pytest.raises(ValueError, match='weeks'):
        clean_generic_object_json(copy.deepcopy(data), values, mapping)


# --- tables -------------------------------------------------------------------------------------

def _table_data():
    data = _element()
    _field(data, 'table')['sub_values'] = [
        {'id': 'r1', 'c-text': 'one', 'c-num': {'value': 1}, 'c-sel': {'value': 'red'},
         'c-multi': {'value': ['red', 'blue']}, 'c-sys': {'value': 20, 'value_system': 'C'},
         'c-form': {'value': 2}, 'c-mol': {'value': MOLECULE_CELL}, 'c-sam': {'value': ''}},
        {'id': 'r2', 'c-text': 'two', 'c-num': {'value': 2}},
        {'id': 'r3', 'c-text': 'three', 'c-num': {'value': 3}},
    ]
    return data


def test_table_reads_cells_in_the_shape_of_the_fields():
    values, _ = _parse(_table_data())
    rows = values['L']['Table']
    assert [r.row_id for r in rows] == ['r1', 'r2', 'r3']
    assert rows[0] == {'Text': 'one', 'Num': 1, 'Sel': 'red', 'Multi': ['red', 'blue'],
                       'Temp': {'value': 20, 'unit': 'C'}, 'Form': 2, 'Mol': MOLECULE_CELL, 'Sam': ''}
    # cells of columns added after the row was stored do not break reading
    assert rows[1] == {'Text': 'two', 'Num': 2, 'Sel': None, 'Multi': [], 'Temp': {'value': None, 'unit': 'C'},
                       'Form': None, 'Mol': None, 'Sam': None}


def test_table_keeps_exactly_the_rows_given():
    data = _table_data()
    values, mapping = _parse(data)
    rows = values['L']['Table']
    del rows[0]
    stored, reloaded = _save(data, values, mapping)
    sub_values = _field(stored, 'table')['sub_values']
    assert [r['id'] for r in sub_values] == ['r2', 'r3']
    assert [r['Text'] for r in reloaded['L']['Table']] == ['two', 'three']

    values, mapping = _parse(stored)
    values['L']['Table'] = [values['L']['Table'][1]]
    stored, reloaded = _save(stored, values, mapping)
    assert [r['id'] for r in _field(stored, 'table')['sub_values']] == ['r3']

    values, mapping = _parse(stored)
    values['L']['Table'] = []
    stored, reloaded = _save(stored, values, mapping)
    assert _field(stored, 'table')['sub_values'] == [] and reloaded['L']['Table'] == []


def test_table_new_rows_start_from_the_ui_defaults():
    data = _element()
    values, mapping = _parse(data)
    values['L']['Table'].append({'Text': 'new'})
    stored, _ = _save(data, values, mapping)
    row = _field(stored, 'table')['sub_values'][0]
    assert row.pop('id')
    assert row == {'c-text': 'new', 'c-num': {'value': ''}, 'c-sel': {'value': ''}, 'c-multi': {'value': []},
                   'c-sys': {'value': '', 'value_system': 'C'}, 'c-form': {'value': ''}, 'c-mol': {'value': ''},
                   'c-sam': {'value': ''}}


def test_table_writes_cells_as_the_ui_stores_them():
    data = _table_data()
    values, mapping = _parse(data)
    row = values['L']['Table'][1]
    row.update({'Num': '12.5', 'Sel': 'Blue colour', 'Multi': ['Green colour', 'red'], 'Temp': 300,
                'Mol': MOLECULE_CELL})
    values['L']['Table'][2]['Temp'] = {'value': 5, 'unit': 'K'}
    stored, reloaded = _save(data, values, mapping)
    r2, r3 = _field(stored, 'table')['sub_values'][1:]
    assert r2['c-num'] == {'value': 12.5}
    assert r2['c-sel'] == {'value': 'blue'}
    assert r2['c-multi'] == {'value': ['green', 'red']}
    assert r2['c-sys'] == {'value': 300, 'value_system': 'C'}
    assert r2['c-mol'] == {'value': MOLECULE_CELL}
    assert r3['c-sys'] == {'value': 5, 'value_system': 'K'}
    # the unchanged first row is stored as it was
    assert _field(stored, 'table')['sub_values'][0] == _field(_table_data(), 'table')['sub_values'][0]
    assert reloaded['L']['Table'][1]['Sel'] == 'blue'


def test_table_accepts_cells_in_the_stored_shape():
    data = _table_data()
    values, mapping = _parse(data)
    values['L']['Table'][1].update({'Sel': {'value': 'green'}, 'Temp': {'value': 4, 'value_system': 'K'},
                                    'Num': {'value': 7}})
    stored, _ = _save(data, values, mapping)
    r2 = _field(stored, 'table')['sub_values'][1]
    assert (r2['c-sel'], r2['c-sys'], r2['c-num']) == ({'value': 'green'}, {'value': 4, 'value_system': 'K'},
                                                       {'value': 7})


@pytest.mark.parametrize('column, value, match', [
    ('Sel', 'purple', 'purple'),
    ('Multi', ['purple'], 'purple'),
    ('Num', 'abc', 'number'),
    ('Num', 1.234, 'decimal'),
    ('Num', 101, 'at most'),
    ('Temp', {'value': 1, 'unit': 'mA'}, 'mA'),
    ('Nope', 1, 'Nope'),
])
def test_table_refuses_bad_cells(column, value, match):
    data = _table_data()
    values, mapping = _parse(data)
    values['L']['Table'][1][column] = value
    with pytest.raises(ValueError, match=match):
        clean_generic_object_json(data, values, mapping)


def test_table_row_is_a_dict_that_keeps_its_id_through_a_copy():
    row = TableRow({'A': 1}, row_id='x')
    assert row == {'A': 1} and copy.deepcopy(row).row_id == 'x'
    assert TableRow({'A': 1}).row_id is None


# --- number, ontology-select and other types ----------------------------------------------------

def test_number_is_checked_against_its_numeric_settings_and_stored_as_a_number():
    data = _element()
    values, mapping = _parse(data)
    values['L']['Number'] = '12.5'
    values['L']['Plain number'] = 3.0
    stored, reloaded = _save(data, values, mapping)
    assert _field(stored, 'number')['value'] == 12.5 and _field(stored, 'number_plain')['value'] == 3
    assert reloaded['L']['Number'] == 12.5

    for value, match in [('x', 'number'), (1.25, 'decimal'), (-6, 'at least'), (51, 'at most'),
                         (True, 'number')]:
        values, mapping = _parse(stored)
        values['L']['Number'] = value
        with pytest.raises(ValueError, match=match):
            clean_generic_object_json(copy.deepcopy(stored), values, mapping)
    values['L']['Number'] = ''
    stored, reloaded = _save(stored, values, mapping)
    assert reloaded['L']['Number'] == ''


def test_number_without_numeric_settings_takes_integers_only():
    data = _element()
    values, mapping = _parse(data)
    values['L']['Plain number'] = 1.5
    with pytest.raises(ValueError, match='decimal'):
        clean_generic_object_json(data, values, mapping)


def test_ontology_select_stores_the_term_label():
    data = _element()
    values, mapping = _parse(data)
    values['L']['Onto'] = 'nuclear magnetic resonance spectroscopy'
    stored, reloaded = _save(data, values, mapping)
    assert _field(stored, 'onto')['value'] == 'nuclear magnetic resonance spectroscopy'
    values['L']['Onto'] = 12
    with pytest.raises(ValueError, match='Onto'):
        clean_generic_object_json(data, values, mapping)


def test_checkbox_and_datetime_take_the_ui_shapes():
    data = _element()
    values, mapping = _parse(data)
    assert values['L']['When'] is None
    values['L']['Checkbox'] = True
    values['L']['When'] = datetime.datetime(2025, 12, 24, 18, 30, 0)
    stored, reloaded = _save(data, values, mapping)
    assert _field(stored, 'checkbox')['value'] is True
    assert _field(stored, 'when')['value'] == '24/12/2025 18:30:00'
    assert reloaded['L']['When'] == '24/12/2025 18:30:00'

    values, mapping = _parse(stored)
    values['L']['When'] = None
    stored, _ = _save(stored, values, mapping)
    assert 'value' not in _field(stored, 'when')

    values['L']['Checkbox'] = 'yes'
    with pytest.raises(ValueError, match='Checkbox'):
        clean_generic_object_json(stored, values, mapping)


def test_input_group_keeps_its_list_shape_and_checks_numbers():
    data = _element()
    values, mapping = _parse(data)
    assert values['L']['Group'] == ['Fixed', '', '', {'value': '', 'unit': 'K'}]
    values['L']['Group'][1] = -1.5e3
    values['L']['Group'][2] = 'abc'
    values['L']['Group'][3] = 300
    stored, reloaded = _save(data, values, mapping)
    assert reloaded['L']['Group'] == ['Fixed', -1500.0, 'abc', {'value': 300, 'unit': 'K'}]

    values['L']['Group'][1] = 'abc'
    with pytest.raises(ValueError, match='number'):
        clean_generic_object_json(copy.deepcopy(stored), values, mapping)
    values['L']['Group'] = ['Fixed', 1, 'a', 2, 'too many']
    with pytest.raises(ValueError, match='4'):
        clean_generic_object_json(copy.deepcopy(stored), values, mapping)


def test_every_field_type_survives_an_unchanged_round_trip():
    data = _table_data()
    _field(data, 'multi')['sub_fields'] = [{'value': 'red'}]
    _field(data, 'link')['value'] = {'el_id': 3, 'el_type': 'element', 'el_label': 'X-1'}
    _field(data, 'sample')['value'] = {'el_id': 4, 'el_type': 'sample', 'el_label': 'S-1', 'is_new': True,
                                       'cr_opt': 0}
    _field(data, 'molecule')['value'] = {'el_id': 5, 'el_type': 'molecule', 'el_label': 'water',
                                         'el_tip': 'X@@O'}
    _field(data, 'when')['value'] = '24/12/2025 18:30:00'
    _field(data, 'int')['value'] = 'stale'
    before = copy.deepcopy(data)
    values, mapping = _parse(data)
    stored, reloaded = _save(data, values, mapping)
    assert stored == json.loads(json.dumps(before))
    assert reloaded == values
    assert reloaded['L']['Upload'] == {'files': [{'uid': 'u1', 'filename': 'a.txt', 'aid': 3}]}
    assert reloaded['L']['Link'] == {'value': {'el_id': 3, 'el_type': 'element', 'el_label': 'X-1'}}


def test_select_options_of_a_saved_record_come_from_its_release():
    """The ELN does not keep select_options in a saved record's properties, only in properties_release."""
    data = _element()
    data['properties_release'] = {'select_options': data['properties'].pop('select_options')}
    values, mapping = _parse(data)
    values['L']['Select'] = 'Blue colour'
    values['L']['Multi'] = ['Red colour']
    stored, reloaded = _save(data, values, mapping)
    assert (reloaded['L']['Select'], reloaded['L']['Multi']) == ('blue', ['red'])
