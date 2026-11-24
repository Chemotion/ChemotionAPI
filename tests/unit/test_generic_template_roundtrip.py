"""Template building (the LabIMotion designer side): a template loaded and saved by the client
keeps every key it was loaded with, and the client can build every field type the released
designer (chem-generic-ui 2.3.2, LabIMotion 2.3.4, ELN 4.0.2) offers.

The expected shapes are those the web designer writes; the cgu identifiers in the docstrings
point at ``chem-generic-ui.es.js`` 2.3.2.
"""
import copy
import json
import os

import pytest

from chemotion_api.labImotion import GenericDataset, GenericElementKlass, GenericSegment
from chemotion_api.labImotion.items.fields import fields as F
from chemotion_api.labImotion.items.options import FieldType, SubFieldType, SubTableFieldType

FIXTURE = os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'GenericElement.json')


def _klass_json() -> dict:
    with open(FIXTURE) as f:
        return json.load(f)


def _field(layer: dict, field_type: str) -> dict:
    return next(f for f in layer['fields'] if f['type'] == field_type)


def _assert_kept(original, saved, path='template'):
    """Every key of ``original`` is in ``saved`` with the same value (``saved`` may add keys)."""
    if isinstance(original, dict):
        assert isinstance(saved, dict), f'{path}: {saved!r} is no longer a dict'
        for key, value in original.items():
            assert key in saved, f'{path}.{key} was dropped'
            _assert_kept(value, saved[key], f'{path}.{key}')
    elif isinstance(original, list):
        assert isinstance(saved, list) and len(saved) == len(original), f'{path}: {saved!r} != {original!r}'
        for i, (a, b) in enumerate(zip(original, saved)):
            _assert_kept(a, b, f'{path}[{i}]')
    else:
        assert saved == original, f'{path}: {saved!r} != {original!r}'


def _ui_template() -> dict:
    """The fixture template with what the web designer and the element form add to it."""
    data = _klass_json()
    tpl = data['properties_template']
    tpl['x_template_key'] = {'kept': True}
    layer = tpl['layers']['aaa']
    layer.update({'label_fields': ['text'], 'wf_info': {'node_id': 'n1', 'source_layer': 'aaa'},
              'ai': [12], 'wf_uuid': None, 'x_layer_key': 1, 'timeRecord': '01/02/2024 10:00:00'})
    _field(layer, 'text').update({'placeholder': 'e.g. E. coli', 'description': 'hover info', 'hasOwnRow': True,
                               'readonly': True, 'x_field_key': [1, 2]})
    _field(layer, 'datetime')['readonly'] = True
    _field(layer, 'text-formula')['text_sub_fields'] = [
        {'id': 'tsf1', 'layer': 'aaa', 'field': 'text', 'separator': '.'}]
    _field(layer, 'integer').update({'numeric': {'decimals': 2, 'min': -5, 'max': ''}, 'placeholder': '0'})
    layer['fields'].append({'type': 'number', 'field': 'num', 'label': 'Num', 'default': '', 'position': 99,
                            'required': False, 'sub_fields': [], 'text_sub_fields': [],
                            'numeric': {'decimals': 1, 'min': '', 'max': 10}, 'value': 2.5})
    layer['fields'].append({'type': 'ontology-select', 'field': 'onto', 'label': 'Onto', 'default': '',
                            'position': 100, 'ontology_term': {'value': 'chmo:class:http://x/CHMO_1',
                                                               'label': 'spectroscopy'}})
    layer['fields'].append({'type': 'select-multi', 'field': 'multi', 'label': 'Multi', 'default': '',
                            'position': 101, 'option_layers': next(iter(tpl['select_options'])),
                            'sub_fields': [{'value': 'a'}]})
    table = _field(layer, 'table')
    table['sub_fields'] = [
        {'id': 'c1', 'col_name': 'n', 'type': 'number', 'value': '',
         'numeric': {'decimals': 0, 'min': '', 'max': ''}, '_checksum': 'abc'},
        {'id': 'c2', 'col_name': 'f', 'type': 'formula-field', 'value': '', 'formula': 'a*2', 'decimal': 5,
         'refs': [{'id': 'c1', 'abbr': 'a'}]},
        {'id': 'c3', 'col_name': 'el', 'type': 'drag_element', 'value': ''},  # LabIMotion 2.4 column
    ]
    table['sub_values'] = [{'id': 'r1', 'c1': {'value': 3}}]
    group = _field(layer, 'input-group')
    group['sub_fields'] = [{'id': 's1', 'type': 'number', 'value': '-1.5e3', 'x_sub_key': 'kept'}]
    return data


@pytest.fixture
def klass():
    return GenericElementKlass(_klass_json(), None)


def test_a_template_saved_by_the_client_keeps_every_key_it_was_loaded_with():
    original = _ui_template()
    klass = GenericElementKlass(copy.deepcopy(original), None)
    _assert_kept(original['properties_template'], klass.to_dict()['properties_template'])


@pytest.mark.parametrize(('fixture', 'cls'), [
    ('GenericElement.json', GenericElementKlass),
    ('GenericSegment.json', GenericSegment),
    ('GenericDataset.json', GenericDataset),
    ('legacy_klasses/demo.json', GenericElementKlass),
    ('legacy_klasses/dev_mass.json', GenericSegment),
    ('legacy_klasses/gas_chromatography__gc.json', GenericDataset),
    ('legacy_klasses/gas_chromatography_mass_spectrometry__gcms.json', GenericDataset),
    ('legacy_klasses/single_crystal_x_ray_diffraction__single_crystal.json', GenericDataset),
])
def test_real_templates_survive_load_and_save(fixture, cls):
    """Templates captured from real servers. Before, five of them lost field keys on save (a preset
    ``value``, ``option_layers`` of a text field, ``description``, the joined fields of a text-formula)."""
    with open(os.path.join(os.path.dirname(FIXTURE), fixture), encoding='utf-8') as f:
        data = json.load(f)
    original = copy.deepcopy(data['properties_template'])
    _assert_kept(original, cls(data, None).to_dict()['properties_template'])


def test_number_and_ontology_select_fields_load_as_their_own_classes():
    klass = GenericElementKlass(_ui_template(), None)
    layer = klass.properties.get_layer_by_key('aaa')
    by_key = {f.field: f for f in layer.fields}
    assert isinstance(by_key['num'], F.NumberField)
    assert isinstance(by_key['onto'], F.OntologySelectField)
    assert isinstance(next(f for f in layer.fields if f.field_type == FieldType.INTEGER), F.IntegerField)


def test_ui_attributes_can_be_set_and_cleared(klass):
    layer = klass.properties.add_new_layer('Strain')
    field = layer.add_field(FieldType.TEXT, 'Name')
    field.placeholder = 'e.g. K12'
    field.description = 'The strain name'
    field.hasOwnRow = True
    field.readonly = True
    saved = field.to_dict()
    assert (saved['placeholder'], saved['description'], saved['hasOwnRow'], saved['readonly']) == \
           ('e.g. K12', 'The strain name', True, True)
    field.placeholder = None
    field.description = None
    assert 'placeholder' not in field.to_dict() and 'description' not in field.to_dict()
    with pytest.raises(TypeError):
        field.hasOwnRow = 'yes'


def test_ui_attributes_follow_the_designer_per_type(klass):
    """cgu: placeholder only for text/integer/number (``[y.F_INTEGER, y.F_TEXT]`` and the number
    block), hasOwnRow for everything but dummy and table (``S42``)."""
    layer = klass.properties.add_new_layer('Types')
    assert not hasattr(layer.add_field(FieldType.CHECKBOX, 'Check'), 'placeholder')
    layer.add_field(FieldType.NUMBER, 'Count').placeholder = '0'
    with pytest.raises(ValueError):
        layer.add_field(FieldType.TABLE, 'Grid').hasOwnRow = True


def test_datetime_readonly_is_saved(klass):
    field = klass.properties.add_new_layer('Times').add_field(FieldType.DATETIME, 'Start')
    field.readonly = True
    assert field.to_dict()['readonly'] is True


def test_text_formula_fields_can_be_set(klass):
    layer = klass.properties.add_new_layer('Naming')
    first = layer.add_field(FieldType.TEXT, 'First')
    layer.add_field(FieldType.CHECKBOX, 'Flag')
    formula = layer.add_field(FieldType.TEXT_FORMULA, 'Joined')
    entry = formula.add_text_sub_field(first, separator='-')
    assert entry['layer'] == layer.key and entry['field'] == first.field and entry['separator'] == '-'
    assert formula.to_dict()['text_sub_fields'] == [entry]
    with pytest.raises(ValueError, match='text'):
        formula.add_text_sub_field('flag', layer=layer.key)
    formula.text_sub_fields = []
    assert formula.to_dict()['text_sub_fields'] == []


def test_layer_time_record_is_kept_and_settable():
    data = _klass_json()
    data['properties_template']['layers']['aaa']['timeRecord'] = '01/02/2024 10:00:00'
    klass = GenericElementKlass(data, None)
    layer = klass.properties.get_layer_by_key('aaa')
    assert layer.timeRecord == '01/02/2024 10:00:00'
    assert layer.to_dict()['timeRecord'] == '01/02/2024 10:00:00'
    layer.timeRecord = ''
    assert layer.to_dict()['timeRecord'] == ''
    with pytest.raises(TypeError):
        layer.timeRecord = 5


def test_conditions_on_a_new_layer_are_sent(klass):
    source = klass.properties.add_new_layer('Source')
    check = source.add_field(FieldType.CHECKBOX, 'Done')
    target = klass.properties.add_new_layer('Target')
    target.add_condition(check, True)
    saved = klass.to_dict()['properties_template']['layers'][target.key]
    assert saved['cond_operator'] == 1
    assert saved['cond_fields'] == [{'id': saved['cond_fields'][0]['id'], 'field': check.field,
                                     'layer': source.key, 'value': True, 'label': ''}]
    assert saved['cond_fields'][0]['id'].endswith('-fc')


def test_a_select_condition_takes_the_key_or_the_label_and_stores_the_key(klass):
    props = klass.properties
    layer = props.add_new_layer('Medium')
    props.select_options = props.select_options | {
        'medium': {'options': [{'key': 'lb', 'label': 'LB broth'}, {'key': 'tb', 'label': 'Terrific broth'}]}}
    select = layer.add_field(FieldType.SELECT, 'Medium')
    select.option_layers = 'medium'
    other = layer.add_field(FieldType.TEXT, 'Notes')
    other.add_condition(select, 'Terrific broth', label='TB only')
    other.add_condition(select, 'lb')
    assert [(c['value'], c['label']) for c in other.to_dict()['cond_fields']] == [('tb', 'TB only'), ('lb', '')]
    with pytest.raises(ValueError, match='LB broth'):
        other.add_condition(select, 'Water')


def test_conditions_can_be_cleared(klass):
    layer = klass.properties.add_new_layer('Clear')
    check = layer.add_field(FieldType.CHECKBOX, 'Done')
    field = layer.add_field(FieldType.TEXT, 'Notes')
    field.add_condition(check, False)
    assert field.to_dict()['cond_fields'][0]['value'] is False
    field.cond_fields = None
    saved = field.to_dict()
    assert 'cond_fields' not in saved and 'cond_operator' not in saved
    layer.add_condition(check, True)
    layer.cond_fields = []
    saved = layer.to_dict()
    assert 'cond_fields' not in saved and 'cond_operator' not in saved


def test_loaded_conditions_can_be_cleared():
    data = _klass_json()
    data['properties_template']['layers']['aaa'] |= {
        'cond_fields': [{'id': 'c-fc', 'layer': 'con', 'field': 'x', 'value': 'y'}], 'cond_operator': 0}
    klass = GenericElementKlass(data, None)
    layer = klass.properties.get_layer_by_key('aaa')
    field = next(f for f in layer.fields if f.cond_fields)
    field.cond_fields = None
    assert 'cond_fields' not in field.to_dict()
    layer.cond_fields = None
    assert 'cond_fields' not in layer.to_dict() and 'cond_operator' not in layer.to_dict()


def test_a_loaded_empty_condition_list_is_kept():
    data = _klass_json()
    original = copy.deepcopy(data['properties_template']['layers']['aaa'])
    assert original['cond_fields'] == []
    klass = GenericElementKlass(data, None)
    saved = klass.properties.get_layer_by_key('aaa').to_dict()
    assert (saved['cond_fields'], saved['cond_operator']) == ([], original['cond_operator'])


@pytest.mark.parametrize('value', ['-1', '-2.5', '1e3', '1.5E-4', '.5', -3, 2.5e-7, ''])
def test_input_group_number_accepts_negatives_and_exponents(klass, value):
    group = klass.properties.add_new_layer('Group').add_field(FieldType.INPUT_GROUP, 'Group')
    group.add_subfield(SubFieldType.NUMBER).value = value


@pytest.mark.parametrize('value', ['abc', '1-2', '1e', 'nan'])
def test_input_group_number_still_rejects_non_numbers(klass, value):
    group = klass.properties.add_new_layer('Group').add_field(FieldType.INPUT_GROUP, 'Group')
    with pytest.raises(ValueError):
        group.add_subfield(SubFieldType.NUMBER).value = value


def test_a_new_number_field_has_the_designer_shape(klass):
    """cgu ``case "type"``: a field switched to number gets ``numeric = {decimals: 0, min: '', max: ''}``."""
    layer = klass.properties.add_new_layer('Numbers')
    field = layer.add_field(FieldType.NUMBER, 'Count')
    saved = field.to_dict()
    assert saved['type'] == 'number'
    assert saved['numeric'] == {'decimals': 0, 'min': '', 'max': ''}
    field.set_numeric(decimals=2, min=-1, max=10.5)
    assert field.to_dict()['numeric'] == {'decimals': 2, 'min': -1, 'max': 10.5}
    with pytest.raises(ValueError):
        field.set_numeric(min=5, max=1)
    with pytest.raises(ValueError):
        field.set_numeric(decimals=-1)


def test_add_field_integer_creates_the_number_type_the_designer_saves(klass):
    """cgu ``Uu``: every template save turns ``integer`` into ``number`` with ``numeric.decimals = 0``."""
    layer = klass.properties.add_new_layer('Numbers')
    with pytest.warns(DeprecationWarning):
        field = layer.add_field(FieldType.INTEGER, 'Count')
    assert isinstance(field, F.NumberField)
    assert field.to_dict()['type'] == 'number' and field.numeric['decimals'] == 0


def test_a_formula_may_use_number_fields(klass):
    layer = klass.properties.add_new_layer('Formula')
    layer.add_field(FieldType.NUMBER, 'Mass', field='mass')
    formula = layer.add_field(FieldType.FORMULA_FIELD, 'Double')
    formula.formula = 'mass*2'
    assert formula.to_dict()['formula'] == 'mass*2'


def test_ontology_select_field(klass):
    """cgu: the term picker stores ``ontology_term = {value: <search doc id>, label}``."""
    layer = klass.properties.add_new_layer('Onto')
    field = layer.add_field(FieldType.ONTOLOGY_SELECT, 'Technique')
    assert 'ontology_term' not in field.to_dict()
    field.ontology_term = {'id': 'chmo:class:http://purl.obolibrary.org/obo/CHMO_0000228', 'label': 'spectroscopy',
                           'iri': 'http://purl.obolibrary.org/obo/CHMO_0000228'}
    assert field.to_dict()['ontology_term'] == {
        'value': 'chmo:class:http://purl.obolibrary.org/obo/CHMO_0000228', 'label': 'spectroscopy'}
    field.ontology_term = {'value': 'x:class:y', 'label': 'Y'}
    assert field.ontology_term == {'value': 'x:class:y', 'label': 'Y'}
    field.ontology_term = None
    assert 'ontology_term' not in field.to_dict()


def test_table_columns_formula_number_and_select_multi(klass):
    """cgu table column type switch: number gets ``numeric``; select-multi the first option set;
    formula-field ``formula: ''``, ``decimal: 5``, ``refs: []``."""
    props = klass.properties
    option_set = props.add_select_option('colours', ['red', 'blue'])
    table = props.add_new_layer('Table').add_field(FieldType.TABLE, 'Grid')
    number = table.add_subfield(SubTableFieldType.NUMBER, 'Amount')
    multi = table.add_subfield(SubTableFieldType.SELECT_MULTI, 'Colours')
    multi.option_layers = option_set
    formula = table.add_subfield(SubTableFieldType.FORMULA_FIELD, 'Double')
    formula.add_ref(number, 'a')
    formula.formula = 'a*2'
    formula.decimal = 3
    cols = {c['col_name']: c for c in table.to_dict()['sub_fields']}
    assert cols['Amount'] | {'id': None} == {'id': None, 'col_name': 'Amount', 'type': 'number', 'value': '',
                                             'numeric': {'decimals': 0, 'min': '', 'max': ''}}
    assert cols['Colours']['type'] == 'select-multi' and cols['Colours']['option_layers'] == option_set
    assert cols['Double'] | {'id': None} == {'id': None, 'col_name': 'Double', 'type': 'formula-field',
                                             'value': '', 'formula': 'a*2', 'decimal': 3,
                                             'refs': [{'id': number.id, 'abbr': 'a'}]}
    with pytest.raises(ValueError):
        formula.add_ref(multi, 'b')


def test_a_table_with_an_unknown_column_type_stays_editable():
    klass = GenericElementKlass(_ui_template(), None)
    table = next(f for f in klass.properties.get_layer_by_key('aaa').fields if isinstance(f, F.TableField))
    table.add_subfield(SubTableFieldType.TEXT, 'Note')
    cols = table.to_dict()['sub_fields']
    assert [c['type'] for c in cols] == ['number', 'formula-field', 'drag_element', 'text']
    assert cols[2] == {'id': 'c3', 'col_name': 'el', 'type': 'drag_element', 'value': ''}


def test_assigning_layers_replaces_them(klass):
    props = klass.properties
    kept = props.layers[0]
    props.layers = [kept]
    assert props.layers == [kept]


def test_a_select_can_use_the_system_user_list(klass):
    """cgu: ``f4 = "-su03-"``, offered as "System user list" next to the template's option sets."""
    select = klass.properties.add_new_layer('People').add_field(FieldType.SELECT, 'Operator')
    select.option_layers = '-su03-'
    assert select.to_dict()['option_layers'] == '-su03-'


def test_the_structure_of_an_unparsed_template_tolerates_unknown_field_types():
    klass = GenericElementKlass(_klass_json(), None)
    klass._properties = None   # as for a non-generic klass: the structure comes from the raw template
    klass._json_data['properties_template']['layers']['aaa']['fields'].append(
        {'type': 'brand-new', 'field': 'new', 'label': 'New', 'default': '', 'position': 50})
    assert klass._sr.get_structure()['aaa']['new'] == 'brand-new'
