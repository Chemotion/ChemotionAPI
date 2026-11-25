"""
Live check: select-multi and datetime-range values of a generic element are saved and read back in the shape the
ELN web form stores (``sub_fields``), a select value can be written to a saved element (whose ``properties`` the
ELN keeps without ``select_options``), and an unchanged save leaves the stored fields as they are.

The template is built from raw JSON (as the web designer saves it) and released through
``generic_elements/update_template``, so this test does not depend on the client's template API.
"""
import copy
import uuid

from chemotion_api import Instance
from chemotion_api.labImotion.items.options import SaveActionType

SELECT_OPTIONS = {'colours': {'options': [{'key': 'red', 'label': 'Red colour'},
                                          {'key': 'green', 'label': 'Green colour'},
                                          {'key': 'blue', 'label': 'Blue colour'}]}}


def _field(position, field_type, name, **extra):
    return {'type': field_type, 'field': name, 'label': name.capitalize(), 'default': '', 'position': position,
            'required': False, 'sub_fields': [], 'text_sub_fields': [], 'cols': 1} | extra


def _release(instance: Instance, klass):
    data = copy.deepcopy(klass._json_data)
    template = data['properties_template']
    template['select_options'] = copy.deepcopy(SELECT_OPTIONS)
    template['layers'] = {'main': {
        'key': 'main', 'label': 'All', 'cols': 1, 'color': 'none', 'style': 'panel_generic_heading',
        'position': 10, 'wf': False, 'wf_position': 0, 'timeRecord': '', 'fields': [
            _field(1, 'select-multi', 'multi', option_layers='colours'),
            _field(2, 'datetime-range', 'range'),
            _field(3, 'select', 'select', option_layers='colours'),
        ]}}
    res = instance._con.post(klass.url_save_template, data=data | {
        'release': SaveActionType.MINOR.value, 'klass': klass.element_type.value, 'version': None})
    assert res.status_code == 201, res.text


def test_select_multi_and_datetime_range_round_trip(instance_with_collection):
    instance: Instance = instance_with_collection['instance']
    col = instance_with_collection['main_collection']
    gm = instance.generic_manager()
    suffix = uuid.uuid4().hex[:6]
    klass = gm.create_new_element(f'Values {suffix}', 'flask', name=f'val{suffix}', prefix='VAL')
    try:
        _release(instance, klass)
        instance.element_manager.reload()
        _round_trip(instance, col, klass.name)
    finally:
        # other tests count the generic klasses of the seed
        klass.delete(confirm=klass.label)
        instance.element_manager.reload()


def _round_trip(instance: Instance, col, name: str):
    elem = col.new_generic(name)
    assert elem.properties['All']['Multi'] == []
    assert elem.properties['All']['Range'] == {'timeStart': '', 'timeStop': '',
                                               'duration': {'value': '', 'unit': 'd'}}
    elem.properties['All']['Multi'] = ['blue', 'red']
    elem.properties['All']['Range'] = {'timeStart': '01/02/2025 10:00:00', 'timeStop': '02/02/2025 12:00:00',
                                       'duration': {'value': 26, 'unit': 'h'}}
    elem.save()

    loaded = instance.get_generic_by_name(name, elem.id)
    assert loaded.klass_version == loaded.json_data['properties_release']['version']
    layer = loaded.properties['All']
    assert layer['Multi'] == ['blue', 'red']
    assert layer['Range'] == {'timeStart': '01/02/2025 10:00:00', 'timeStop': '02/02/2025 12:00:00',
                              'duration': {'value': 26, 'unit': 'h'}}
    fields = {f['field']: f for f in loaded.json_data['properties']['layers']['main']['fields']}
    assert fields['multi']['sub_fields'] == [{'value': 'blue'}, {'value': 'red'}]
    assert [p['col_name'] for p in fields['range']['sub_fields']] == \
        ['timeStart', 'timeStop', 'durationCalc', 'duration']

    # the ELN keeps a saved element's properties without select_options
    assert not loaded.json_data['properties'].get('select_options')
    assert [o['key'] for o in loaded.field('All', 'Select').options()] == ['red', 'green', 'blue']
    layer['Select'] = 'Green colour'
    layer['Multi'] = ['green']
    layer['Range'] = {'duration': 3}
    loaded.save()

    reloaded = instance.get_generic_by_name(name, elem.id)
    layer = reloaded.properties['All']
    assert (layer['Select'], layer['Multi']) == ('green', ['green'])
    assert layer['Range'] == {'timeStart': '01/02/2025 10:00:00', 'timeStop': '02/02/2025 12:00:00',
                              'duration': {'value': 3, 'unit': 'h'}}

    # an unchanged save leaves the stored fields as they are
    before = copy.deepcopy(reloaded.json_data['properties']['layers']['main']['fields'])
    reloaded.save()
    again = instance.get_generic_by_name(name, elem.id)
    assert again.json_data['properties']['layers']['main']['fields'] == before
