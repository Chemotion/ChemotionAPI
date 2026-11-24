"""A template built by the client with every field type and the designer's attributes is stored by the
server as built, and a template saved again by the client keeps the keys the web designer added."""
import copy

import pytest

from chemotion_api import GenericManager
from chemotion_api.labImotion.items.options import FieldType, FieldUnit, SaveActionType, SubFieldType, \
    SubTableFieldType

#: A term as the designer's picker gets it from the TIB Terminology Service (no network needed).
TERM = {'id': 'chmo:class:http://purl.obolibrary.org/obo/CHMO_0000228', 'label': 'spectroscopy',
        'iri': 'http://purl.obolibrary.org/obo/CHMO_0000228'}


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


def _build(klass):
    props = klass.properties
    colours = props.add_select_option('colours', ['red', 'blue'])
    props.select_options = props.select_options | {
        'medium': {'options': [{'key': 'lb', 'label': 'LB broth'}, {'key': 'tb', 'label': 'Terrific broth'}]}}

    layer = props.add_new_layer('All types')
    fields = {}
    for field_type in FieldType:
        if field_type == FieldType.INTEGER:
            with pytest.warns(DeprecationWarning):
                fields[field_type] = layer.add_field(field_type, 'integer')
        else:
            fields[field_type] = layer.add_field(field_type, field_type.value)
    fields[FieldType.SELECT].option_layers = 'medium'
    fields[FieldType.SELECT_MULTI].option_layers = colours

    text = fields[FieldType.TEXT]
    text.placeholder = 'e.g. K12'
    text.description = 'hover info'
    text.hasOwnRow = True
    text.readonly = True
    fields[FieldType.DATETIME].readonly = True
    number = fields[FieldType.NUMBER]
    number.set_numeric(decimals=2, min=-10, max=10.5)
    number.placeholder = '0.00'
    fields[FieldType.ONTOLOGY_SELECT].ontology_term = TERM
    fields[FieldType.TEXT_FORMULA].add_text_sub_field(text, separator='-')
    formula = fields[FieldType.FORMULA_FIELD]
    formula.formula = f'({number.field}+3.5)*{fields[FieldType.INTEGER].field}'

    group = fields[FieldType.INPUT_GROUP]
    group.add_subfield(SubFieldType.LABEL).value = 'Range'
    group.add_subfield(SubFieldType.NUMBER).value = '-1.5e3'
    group.add_subfield(SubFieldType.TEXT).value = 'text'
    group.add_subfield(SubFieldType.SYSTEM_DEFINED).option_layers = FieldUnit.TEMPERATURE

    table = fields[FieldType.TABLE]
    columns = {t: table.add_subfield(t, t.value) for t in SubTableFieldType}
    columns[SubTableFieldType.SELECT].option_layers = 'medium'
    columns[SubTableFieldType.SELECT_MULTI].option_layers = colours
    columns[SubTableFieldType.SYSTEM_DEFINED].option_layers = FieldUnit.MASS
    columns[SubTableFieldType.NUMBER].set_numeric(decimals=1)
    columns[SubTableFieldType.DRAG_SAMPLE].set_sample_display(name=True, external_label=False, molecular_weight=True)
    columns[SubTableFieldType.FORMULA_FIELD].add_ref(columns[SubTableFieldType.NUMBER], 'n')
    columns[SubTableFieldType.FORMULA_FIELD].add_ref(columns[SubTableFieldType.SYSTEM_DEFINED], 'm')
    columns[SubTableFieldType.FORMULA_FIELD].formula = 'n*m'

    restricted = props.add_new_layer('Restricted')
    restricted.add_condition(fields[FieldType.SELECT], 'Terrific broth', label='TB')
    restricted.add_condition(fields[FieldType.CHECKBOX], True)
    restricted.timeRecord = ''
    note = restricted.add_field(FieldType.TEXT, 'Note')
    note.add_condition(fields[FieldType.SELECT], 'lb')
    cleared = restricted.add_field(FieldType.TEXT, 'Cleared')
    cleared.add_condition(fields[FieldType.CHECKBOX], False)
    cleared.cond_fields = None


def test_a_template_with_every_field_type_round_trips(instance_with_collection):
    gm: GenericManager = instance_with_collection['instance'].generic_manager()
    klass = gm.create_new_element('Round Trip', 'flask', release=False, activate=False)
    try:
        _build(klass)
        sent = copy.deepcopy(klass.to_dict()['properties_template'])
        klass.save(SaveActionType.MAJOR)

        reloaded = gm.get_element(name=klass.name)
        stored = reloaded._json_data['properties_template']
        _assert_kept(sent['layers'], stored['layers'], 'layers')
        _assert_kept(sent['select_options'], stored['select_options'], 'select_options')
        _assert_kept(sent['layers'], reloaded.release.to_dict()['layers'], 'release.layers')

        restricted = reloaded.properties.get_layer_by_label('Restricted')
        assert [c['value'] for c in restricted.cond_fields] == ['tb', True]
        assert [c['label'] for c in restricted.cond_fields] == ['TB', '']
        assert 'cond_fields' not in stored['layers'][restricted.key]['fields'][1]
        all_types = stored['layers'][reloaded.properties.get_layer_by_label('All types').key]['fields']
        by_type = {f['type']: f for f in all_types if f['field'] != 'integer'}
        assert by_type['number']['numeric'] == {'decimals': 2, 'min': -10, 'max': 10.5}
        assert by_type['ontology-select']['ontology_term'] == {'value': TERM['id'], 'label': TERM['label']}
        assert by_type['text']['placeholder'] == 'e.g. K12' and by_type['datetime']['readonly'] is True
        assert [c['type'] for c in by_type['table']['sub_fields']] == SubTableFieldType.list()

        # Keys the web designer and the element form add, which the client does not model, survive a
        # load-and-save by the client.
        layer = reloaded.properties.get_layer_by_label('All types')
        layer._json_data |= {'label_fields': [layer.fields[0].field], 'wf_info': {'node_id': 'n'}, 'x_layer': 1}
        layer.fields[0]._json_data |= {'is_voc': False, 'x_field': {'a': 1}}
        ui_layer = copy.deepcopy(layer.to_dict())
        reloaded.save()
        again = gm.get_element(name=klass.name)
        resaved = again._json_data['properties_template']['layers'][layer.key]
        _assert_kept(ui_layer, resaved, 'ui layer')
        again.save()
        _assert_kept(ui_layer, gm.get_element(name=klass.name)._json_data['properties_template']['layers'][layer.key],
                     'ui layer saved twice')
    finally:
        klass.delete(confirm=klass.label)
