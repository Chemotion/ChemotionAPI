"""
Live check: every LabIMotion field type of a generic element, a segment and a dataset gets a value, is saved and
reloaded from the server, and reads back as it was written (in the shape the ELN web form stores).

The templates are built from raw JSON (as the web designer saves them) and released through
``generic_elements/update_template``, so this test does not depend on the client's template API.
"""
import copy
import datetime
import os
import uuid

from chemotion_api import Instance
from chemotion_api.elements.abstract_element import Dataset
from chemotion_api.labImotion.items.options import ElementType, SaveActionType

HERE = os.path.dirname(os.path.abspath(__file__))

SELECT_OPTIONS = {
    'colours': {'options': [{'key': 'red', 'label': 'Red colour'},
                            {'key': 'green', 'label': 'Green colour'},
                            {'key': 'blue', 'label': 'Blue colour'}]},
}


def _field(position, field_type, name, **extra):
    return {'type': field_type, 'field': name, 'label': name.capitalize(), 'default': '', 'position': position,
            'required': False, 'sub_fields': [], 'text_sub_fields': [], 'cols': 1} | extra


def _columns():
    return [
        {'id': str(uuid.uuid4()), 'type': 'text', 'value': '', 'col_name': 'Text'},
        {'id': str(uuid.uuid4()), 'type': 'number', 'value': '', 'col_name': 'Num',
         'numeric': {'decimals': 2, 'min': '', 'max': ''}},
        {'id': str(uuid.uuid4()), 'type': 'select', 'value': '', 'col_name': 'Sel', 'option_layers': 'colours'},
        {'id': str(uuid.uuid4()), 'type': 'select-multi', 'value': '', 'col_name': 'Multi',
         'option_layers': 'colours'},
        {'id': str(uuid.uuid4()), 'type': 'system-defined', 'value': '', 'col_name': 'Temp',
         'option_layers': 'temperature', 'value_system': 'C'},
        {'id': 'formula-col', 'type': 'formula-field', 'value': '', 'col_name': 'Form', 'formula': 'a*2',
         'decimal': 5, 'refs': []},
        {'id': str(uuid.uuid4()), 'type': 'drag_molecule', 'value': 'inchikey', 'col_name': 'Mol'},
        {'id': str(uuid.uuid4()), 'type': 'drag_sample', 'value': 'name', 'col_name': 'Sam'},
    ]


def _dataset_fields():
    """The field types a dataset template may use (the designer's base list)."""
    return [
        _field(1, 'text', 'text'),
        _field(2, 'textarea', 'textarea'),
        _field(3, 'number', 'number', numeric={'decimals': 1, 'min': -5, 'max': 50}),
        _field(4, 'checkbox', 'checkbox', value=False),
        _field(5, 'select', 'select', option_layers='colours'),
        _field(6, 'select-multi', 'multi', option_layers='colours'),
        _field(7, 'system-defined', 'temp', option_layers='temperature', value_system='C'),
        _field(8, 'datetime', 'when'),
        _field(9, 'datetime-range', 'range'),
        _field(10, 'drag_element', 'link'),
        _field(11, 'formula-field', 'formula', formula='number*2', decimal='3', canAdjust=True),
    ]


def _all_fields():
    """Every field type an element or segment template may use."""
    return _dataset_fields() + [
        _field(12, 'drag_molecule', 'molecule'),
        _field(13, 'drag_sample', 'sample'),
        _field(14, 'input-group', 'group', sub_fields=[
            {'id': str(uuid.uuid4()), 'type': 'label', 'value': 'Fixed'},
            {'id': str(uuid.uuid4()), 'type': 'number', 'value': ''},
            {'id': str(uuid.uuid4()), 'type': 'text', 'value': ''},
            {'id': str(uuid.uuid4()), 'type': 'system-defined', 'value': '', 'option_layers': 'temperature',
             'value_system': 'K'},
        ]),
        _field(15, 'table', 'table', sub_fields=_columns(), sub_values=[]),
        _field(16, 'text-formula', 'tformula',
               text_sub_fields=[{'id': str(uuid.uuid4()), 'layer': 'main', 'field': 'text', 'separator': '-'}]),
        _field(17, 'ontology-select', 'onto', ontology_term='http://purl.obolibrary.org/obo/CHMO_0000575'),
        _field(18, 'upload', 'upload'),
        _field(19, 'dummy', 'dummy', label=''),
        _field(20, 'integer', 'int'),
    ]


def _release(instance: Instance, klass, fields: list[dict] | None):
    """
    Saves a template with one layer 'All' holding the fields and releases it as a minor version. Without
    fields, the klass's own template is released again.
    """
    data = copy.deepcopy(klass._json_data)
    if fields is not None:
        template = data['properties_template']
        template['select_options'] = copy.deepcopy(SELECT_OPTIONS)
        template['layers'] = {'main': {'key': 'main', 'label': 'All', 'cols': 1, 'color': 'none',
                                       'style': 'panel_generic_heading', 'position': 10, 'wf': False,
                                       'wf_position': 0, 'timeRecord': '', 'fields': fields}}
    res = instance._con.post(klass.url_save_template, data=data | {
        'release': SaveActionType.MINOR.value, 'klass': klass.element_type.value, 'version': None})
    assert res.status_code == 201, res.text


def _fill(values: dict, link: dict, sample: dict | None, molecule: dict | None, dataset: bool = False):
    """Sets a value for every field of the 'All' layer."""
    layer = values['All']
    layer['Text'] = 'some text'
    layer['Textarea'] = 'line 1\nline 2'
    layer['Number'] = '12.5'
    layer['Checkbox'] = True
    layer['Select'] = 'Green colour'
    layer['Multi'] = ['blue', 'Red colour']
    layer['Temp'] = {'value': 300, 'unit': 'K'}
    layer['When'] = datetime.datetime(2025, 12, 24, 18, 30, 5)
    layer['Range'] = {'timeStart': '01/02/2025 10:00:00', 'timeStop': datetime.datetime(2025, 2, 2, 12, 0),
                      'duration': {'value': 26, 'unit': 'h'}}
    layer['Link'] = {'value': link}
    layer['Formula'] = '25'
    if dataset:
        return
    layer['Molecule'] = molecule
    layer['Sample'] = sample
    layer['Group'][1] = -1.5
    layer['Group'][2] = 'group text'
    layer['Group'][3] = 280
    layer['Table'].append({'Text': 'row 1', 'Num': 1.25, 'Sel': 'red', 'Multi': ['Green colour'], 'Temp': 20,
                           'Form': 2.5, 'Mol': molecule, 'Sam': sample})
    layer['Table'].append({'Text': 'row 2', 'Temp': {'value': 4, 'unit': 'K'}})
    layer['Table'].append({'Text': 'row 3'})
    layer['Onto'] = 'nuclear magnetic resonance spectroscopy'
    layer['Int'] = 7


def _expected(dataset: bool = False) -> dict:
    """What the values written by :func:`_fill` read back as (drag fields are compared by el_id only)."""
    expected = {
        'Text': 'some text', 'Textarea': 'line 1\nline 2', 'Number': 12.5, 'Checkbox': True, 'Select': 'green',
        'Multi': ['blue', 'red'], 'Temp': {'value': 300, 'unit': 'K'}, 'When': '24/12/2025 18:30:05',
        'Range': {'timeStart': '01/02/2025 10:00:00', 'timeStop': '02/02/2025 12:00:00',
                  'duration': {'value': 26, 'unit': 'h'}},
        'Formula': '25',
    }
    if not dataset:
        expected |= {'Group': ['Fixed', -1.5, 'group text', {'value': 280, 'unit': 'K'}],
                     'Onto': 'nuclear magnetic resonance spectroscopy', 'Int': 7, 'Tformula': None, 'Upload': None}
    return expected


def _check(layer: dict, link: dict, sample: dict | None, molecule: dict | None, dataset: bool = False):
    for name, value in _expected(dataset).items():
        assert layer[name] == value, name
    assert layer['Link']['value']['el_id'] == link['el_id']
    if dataset:
        return
    assert layer['Molecule']['el_id'] == molecule['el_id']
    assert layer['Sample']['el_id'] == sample['el_id']
    rows = layer['Table']
    assert [r['Text'] for r in rows] == ['row 1', 'row 2', 'row 3']
    assert all(r.row_id for r in rows)
    first = rows[0]
    assert (first['Num'], first['Sel'], first['Multi'], first['Temp'], first['Form']) == \
        (1.25, 'red', ['green'], {'value': 20, 'unit': 'C'}, 2.5)
    assert first['Mol']['el_id'] == molecule['el_id'] and first['Sam']['el_id'] == sample['el_id']
    assert rows[1]['Temp'] == {'value': 4, 'unit': 'K'}
    assert (rows[2]['Num'], rows[2]['Sel'], rows[2]['Multi'], rows[2]['Form']) == ('', '', [], '')


def _links(instance: Instance, col):
    sample = col.new_sample_smiles('CCO')
    sample.save()
    sample = instance.get_sample(sample.id)
    molecule = sample.molecule
    sample_value = {'el_id': sample.id, 'el_type': 'sample', 'el_label': sample.short_label,
                    'el_name': sample.name or '', 'el_tip': sample.short_label, 'is_new': False, 'cr_opt': 0,
                    'isAssoc': False, 'el_decoupled': False, 'el_klass': 'sample'}
    molecule_value = {'el_id': molecule['id'], 'el_type': 'molecule', 'el_label': molecule.get('iupac_name') or '',
                      'el_tip': f"{molecule['inchikey']}@@{molecule['cano_smiles']}"}
    return sample_value, molecule_value


def test_generic_element_and_segment_values_round_trip(instance_with_collection):
    instance: Instance = instance_with_collection['instance']
    col = instance_with_collection['main_collection']
    gm = instance.generic_manager()
    suffix = uuid.uuid4().hex[:6]
    klass = gm.create_new_element(f'Values {suffix}', 'flask', name=f'val{suffix}', prefix='VAL')
    # the segment klass is created first: the client's template parser does not know every field type
    # (e.g. 'number') yet, so the klasses cannot be loaded through it once these templates are released
    gm.create_new_segment(f'Values segment {suffix}', 'all field types', klass)
    segment_klass = gm.get_segment(f'Values segment {suffix}')
    segment_klass.is_active = True
    try:
        _release(instance, klass, _all_fields())
        _release(instance, segment_klass, _all_fields())
        instance.element_manager.reload()
        _element_round_trip(instance, col, klass.name, f'Values segment {suffix}')
    finally:
        # other tests count the generic klasses of the seed
        segment_klass.delete(confirm=segment_klass.label)
        klass.delete(confirm=klass.label)
        instance.element_manager.reload()


def _element_round_trip(instance: Instance, col, name: str, segment_label: str):
    target = col.new_generic('try')
    target.save()
    link = {'el_id': target.id, 'el_type': 'element', 'el_label': target.short_label, 'el_name': target.name,
            'el_tip': f'Tryout@@{target.name}', 'el_klass': 'try', 'icon_name': ''}
    sample, molecule = _links(instance, col)

    elem = col.new_generic(name)
    _fill(elem.properties, link, sample, molecule)
    segment = elem.segments.get(segment_label)
    _fill(segment, link, sample, molecule)
    elem.save()

    loaded = instance.get_generic_by_name(name, elem.id)
    _check(loaded.properties['All'], link, sample, molecule)
    _check(loaded.segments[segment_label]['All'], link, sample, molecule)

    # removing a row and changing the selections is stored as such; the other rows keep their ids
    rows = loaded.properties['All']['Table']
    kept_ids = [rows[0].row_id, rows[2].row_id]
    del rows[1]
    rows[1]['Multi'] = ['red', 'blue']
    loaded.properties['All']['Multi'] = []
    loaded.properties['All']['Range'] = {'duration': 3}
    loaded.save()
    reloaded = instance.get_generic_by_name(name, elem.id)
    layer = reloaded.properties['All']
    assert [r.row_id for r in layer['Table']] == kept_ids
    assert [r['Text'] for r in layer['Table']] == ['row 1', 'row 3']
    assert layer['Table'][1]['Multi'] == ['red', 'blue']
    assert layer['Multi'] == []
    assert layer['Range'] == {'timeStart': '01/02/2025 10:00:00', 'timeStop': '02/02/2025 12:00:00',
                              'duration': {'value': 3, 'unit': 'h'}}

    # an unchanged save leaves the stored properties as they are
    before = copy.deepcopy(reloaded.json_data['properties']['layers'])
    reloaded.save()
    again = instance.get_generic_by_name(name, elem.id)
    assert again.json_data['properties']['layers']['main']['fields'] == before['main']['fields']


def test_generic_dataset_values_round_trip(instance_with_collection):
    instance: Instance = instance_with_collection['instance']
    col = instance_with_collection['main_collection']
    gm = instance.generic_manager()
    # a seeded dataset klass no other test relies on; its own template is released again afterwards, because
    # the client's template parser does not know every field type (e.g. 'number') yet and would skip it
    ds_klass = next(x for x in gm.load_all_datasets() if x.ols_term_id != 'CHMO:0000593')
    _release(instance, ds_klass, _dataset_fields())
    try:
        _dataset_round_trip(instance, col, ds_klass)
    finally:
        _release(instance, ds_klass, None)


def _dataset_round_trip(instance: Instance, col, ds_klass):
    res = instance._con.get(ds_klass.url)
    ds_json = next(x for x in res.json()['klass'] if x['id'] == ds_klass.id)
    release = ds_json['properties_release']

    target = col.new_generic('try')
    target.save()
    link = {'el_id': target.id, 'el_type': 'element', 'el_label': target.short_label, 'el_name': target.name,
            'el_tip': f'Tryout@@{target.name}', 'el_klass': 'try', 'icon_name': ''}

    sample = col.new_sample_smiles('CC')
    sample.analyses.add_analyses('With dataset').add_dataset(os.path.join(HERE, 'data', 'SG-V3545-6-13.cif'))
    sample.save()
    sample = instance.get_sample(sample.id)
    analysis = sample.analyses.by_name('With dataset')
    container = analysis.datasets[0].json_data
    # attach the dataset template as the web form's buildEmpty does
    container['dataset'] = {'dataset_klass_id': ds_klass.id, 'element_type': 'Container',
                            'element_id': container['id'], 'metadata': {},
                            'properties': copy.deepcopy(release) | {'klass_uuid': ds_json['uuid']},
                            'properties_release': copy.deepcopy(release), 'changed': True}
    dataset = Dataset(instance._con, container)
    analysis.datasets[0] = dataset
    _fill(dataset, link, None, None, dataset=True)
    sample.save()

    loaded = instance.get_sample(sample.id).analyses.by_name('With dataset').datasets[0]
    _check(loaded['All'], link, None, None, dataset=True)
