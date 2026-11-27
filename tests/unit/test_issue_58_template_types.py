"""Issue #58: LabIMotion templates the ELN web UI writes must stay readable, and the field types
it offers must be authorable.

The shapes below are taken from the chem-generic-ui bundled with ELN 4.0.2: its field schema
declares ``value_system_base`` (a unit key the designer backfills on system-defined fields) and
``numeric`` (``{decimals, min, max}`` of a ``number`` field), its designer offers ``number`` and
``ontology-select``, and it stores an ontology-select's root term as
``ontology_term = {'value': <TIB term id>, 'label': <term label>}``.
"""
import copy
import json
import os

import pytest

from chemotion_api.labImotion import GenericElementKlass, GenericManager
from chemotion_api.labImotion.items.fields import fields as F
from chemotion_api.labImotion.items.options import FieldType, FieldUnit

FIXTURE = os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'GenericElement.json')
LAYER = 'aaa'


def _payload(*extra_fields):
    with open(FIXTURE) as f:
        data = json.load(f)
    for where in ('properties_template', 'properties_release'):
        layer = data[where]['layers'][LAYER]
        for i, field in enumerate(extra_fields):
            layer['fields'].append({'label': field['field'], 'default': '', 'position': 100 + i,
                                    'required': False, 'sub_fields': [], 'text_sub_fields': [],
                                    **copy.deepcopy(field)})
    return data


def _field(klass, name):
    layer = next(lay for lay in klass.properties.layers if lay.key == LAYER)
    return next(f for f in layer.fields if f.field == name)


def _saved(klass, name):
    layers = klass.to_dict()['properties_template']['layers']
    return next(f for f in layers[LAYER]['fields'] if f['field'] == name)


def _new_layer():
    with open(FIXTURE) as f:
        klass = GenericElementKlass(json.load(f), None)
    return klass, klass.properties.add_new_layer('Extra')


# --- 1. value_system_base -------------------------------------------------------------------

SYSTEM_DEFINED = {'type': 'system-defined', 'field': 'temp', 'option_layers': 'temperature',
                  'value_system': 'C', 'value_system_base': 'C'}


def test_a_template_with_value_system_base_loads():
    klass = GenericElementKlass(_payload(SYSTEM_DEFINED), None)
    assert _field(klass, 'temp').value_system_base == 'C'


def test_value_system_base_survives_a_save():
    klass = GenericElementKlass(_payload(SYSTEM_DEFINED), None)
    assert _saved(klass, 'temp')['value_system_base'] == 'C'


def test_value_system_base_is_not_invented():
    plain = {k: v for k, v in SYSTEM_DEFINED.items() if k != 'value_system_base'}
    klass = GenericElementKlass(_payload(plain), None)
    assert _field(klass, 'temp').value_system_base is None
    assert 'value_system_base' not in _saved(klass, 'temp')


def test_value_system_base_must_be_a_unit_of_the_field():
    _, layer = _new_layer()
    sf = layer.add_field(FieldType.SYSTEM_DEFINED, 'T')
    sf.option_layers = FieldUnit.TEMPERATURE
    sf.value_system_base = 'K'
    assert sf.value_system_base == 'K'
    with pytest.raises(ValueError):
        sf.value_system_base = 'kg'


# --- 2. number -------------------------------------------------------------------------------

NUMBER = {'type': 'number', 'field': 'count', 'numeric': {'decimals': 0, 'min': 0, 'max': '100'}}


def test_a_template_with_a_number_field_loads():
    klass = GenericElementKlass(_payload(NUMBER), None)
    field = _field(klass, 'count')
    assert field.field_type == FieldType.NUMBER
    assert field.numeric == {'decimals': 0, 'min': 0, 'max': '100'}


def test_numeric_survives_a_save():
    klass = GenericElementKlass(_payload(NUMBER), None)
    saved = _saved(klass, 'count')
    assert saved['type'] == 'number'
    assert saved['numeric'] == {'decimals': 0, 'min': 0, 'max': '100'}


def test_a_number_field_can_be_authored():
    _, layer = _new_layer()
    field = layer.add_field(FieldType.NUMBER, 'Count')
    field.numeric = {'decimals': 2, 'min': -1.5}
    assert field.to_dict()['type'] == 'number'
    assert field.to_dict()['numeric'] == {'decimals': 2, 'min': -1.5}


@pytest.mark.parametrize('numeric, error', [
    ({'decimals': -1}, ValueError), ({'decimals': 1.5}, TypeError), ({'decimals': True}, TypeError),
    ({'min': True}, TypeError), ({'step': 1}, ValueError), ('2', TypeError)])
def test_numeric_takes_what_the_designer_takes(numeric, error):
    _, layer = _new_layer()
    field = layer.add_field(FieldType.NUMBER, 'Count')
    with pytest.raises(error):
        field.numeric = numeric


# --- 3. ontology-select ----------------------------------------------------------------------

TERM = {'value': 'obi:class:http://purl.obolibrary.org/obo/OBI_0000070', 'label': 'assay'}
ONTOLOGY_SELECT = {'type': 'ontology-select', 'field': 'assay', 'ontology_term': TERM}


def test_a_template_with_an_ontology_select_field_loads():
    klass = GenericElementKlass(_payload(ONTOLOGY_SELECT), None)
    field = _field(klass, 'assay')
    assert field.field_type == FieldType.ONTOLOGY_SELECT
    assert field.ontology_term == TERM


def test_ontology_term_survives_a_save():
    klass = GenericElementKlass(_payload(ONTOLOGY_SELECT), None)
    assert _saved(klass, 'assay')['ontology_term'] == TERM


def test_an_ontology_select_field_can_be_authored_from_a_term_id(monkeypatch):
    found = {'id': TERM['value'], 'label': 'assay', 'iri': 'http://purl.obolibrary.org/obo/OBI_0000070',
             'obo_id': 'OBI:0000070'}
    monkeypatch.setattr(F, 'get_term', lambda term_id: found if term_id == 'OBI:0000070' else None)
    _, layer = _new_layer()
    field = layer.add_field(FieldType.ONTOLOGY_SELECT, 'Assay')
    field.ontology_term = 'OBI:0000070'
    assert field.to_dict()['ontology_term'] == TERM


def test_an_ontology_select_field_takes_a_term_dict_and_none():
    _, layer = _new_layer()
    field = layer.add_field(FieldType.ONTOLOGY_SELECT, 'Assay')
    field.ontology_term = {'id': TERM['value'], 'label': 'assay', 'iri': 'x'}   # as search_ontology_terms gives it
    assert field.ontology_term == TERM
    field.ontology_term = None
    assert 'ontology_term' not in field.to_dict()


# --- unknown future field types ----------------------------------------------------------------

def test_a_field_type_this_client_does_not_know_keeps_the_template_readable():
    future = {'type': 'future-widget', 'field': 'w', 'widget_options': {'a': 1}}
    klass = GenericElementKlass(_payload(future), None)
    field = _field(klass, 'w')
    assert isinstance(field, F.OpaqueField)
    assert _saved(klass, 'w')['widget_options'] == {'a': 1}


# --- 4. label collision with a built-in type -----------------------------------------------------

class _Res:
    def __init__(self, payload):
        self.status_code, self._payload, self.text = 200, payload, ''

    def json(self):
        return self._payload


class _NoCreate:
    """Lists the server's klasses (as ELN 4.0.2 does: built-ins except Sample) and fails any write."""

    def get(self, url, **kw):
        return _Res({'klass': [{'id': 1, 'name': 'reaction', 'label': 'Reaction', 'is_generic': False},
                               {'id': 2, 'name': 'cell_line', 'label': 'Cell Line', 'is_generic': False}]})

    def post(self, url, **kw):
        raise AssertionError(f'no template may be created: POST {url}')


@pytest.mark.parametrize('label', ['Sample', 'sample', 'Reaction', 'Research Plan', 'research_plan',
                                   'Cell line', 'Wellplate'])
def test_a_label_of_a_built_in_type_is_refused_before_anything_is_created(label, monkeypatch):
    monkeypatch.setattr(GenericElementKlass, 'load_all', classmethod(lambda cls, con, strict=False: []))
    with pytest.raises(ValueError, match='built-in'):
        GenericManager(_NoCreate()).create_new_element(label, 'leaf')


# --- 5. options of a select field on a template -----------------------------------------------------

def test_a_select_field_lists_its_options():
    _, layer = _new_layer()
    sel = layer.add_field(FieldType.SELECT, 'Medium', options=['LB', 'TB'])
    assert sel.options() == [{'key': 'LB', 'label': 'LB'}, {'key': 'TB', 'label': 'TB'}]


def test_a_select_field_without_an_option_list_has_no_options():
    _, layer = _new_layer()
    sel = layer.add_field(FieldType.SELECT_MULTI, 'Medium')
    sel._option_layers = ''
    assert sel.options() == []


def test_a_field_of_a_known_type_still_may_not_carry_unknown_keys():
    """Accepting unknown types must not loosen the check for the types this client models."""
    from jsonschema import ValidationError
    with pytest.raises(ValidationError, match='bogus'):
        GenericElementKlass(_payload({'type': 'text', 'field': 't', 'bogus': 1}), None)


# --- review follow-ups -----------------------------------------------------------------------------

def test_value_system_base_follows_a_change_of_unit_type_or_unit():
    """As the designer does: a base unit never names a unit of another unit type."""
    _, layer = _new_layer()
    sf = layer.add_field(FieldType.SYSTEM_DEFINED, 'T')
    sf.option_layers = FieldUnit.TEMPERATURE
    sf.value_system_base = 'K'
    sf.value_system = 'C'
    assert sf.value_system_base == 'C'
    sf.option_layers = FieldUnit.MASS
    assert sf.value_system_base == sf.value_system
    assert sf.to_dict()['value_system_base'] == sf.value_system


def test_a_stored_value_system_base_is_kept_while_loading():
    stored = dict(SYSTEM_DEFINED, value_system='K', value_system_base='C')
    klass = GenericElementKlass(_payload(stored), None)
    assert _field(klass, 'temp').value_system_base == 'C'


def test_a_formula_may_use_a_number_field():
    """The designer turns integer fields into number fields, so formulas reference those."""
    _, layer = _new_layer()
    count = layer.add_field(FieldType.NUMBER, 'Count')
    formula = layer.add_field(FieldType.FORMULA_FIELD, 'Twice')
    formula.formula = f'{count.field}*2'
    assert formula.formula == f'{count.field}*2'


DESIGNER_KEYS = {'value': 3.5, 'placeholder': 'n', 'readonly': True, 'hasOwnRow': True}


@pytest.mark.parametrize('field', [NUMBER, ONTOLOGY_SELECT, SYSTEM_DEFINED])
def test_keys_the_designer_writes_survive_a_save(field):
    klass = GenericElementKlass(_payload(dict(field, **DESIGNER_KEYS)), None)
    for _ in range(2):  # save() serializes more than once
        saved = _saved(klass, field['field'])
        assert {k: saved.get(k) for k in DESIGNER_KEYS} == DESIGNER_KEYS


def test_a_removed_numeric_is_not_restored_from_the_payload():
    klass = GenericElementKlass(_payload(NUMBER), None)
    _field(klass, 'count').numeric = None
    assert 'numeric' not in _saved(klass, 'count')


def test_an_unknown_field_type_survives_every_save():
    future = {'type': 'future-widget', 'field': 'w', 'widget_options': {'a': 1}}
    klass = GenericElementKlass(_payload(future), None)
    _saved(klass, 'w')
    assert _saved(klass, 'w')['widget_options'] == {'a': 1}


def test_a_gem_type_kept_opaque_may_carry_its_own_keys():
    klass = GenericElementKlass(_payload({'type': 'sys-reaction', 'field': 'r', 'reaction_opts': 1}), None)
    assert _saved(klass, 'r')['reaction_opts'] == 1


def test_numeric_cannot_be_changed_past_its_validation():
    _, layer = _new_layer()
    field = layer.add_field(FieldType.NUMBER, 'Count')
    field.numeric = {'decimals': 1}
    field.numeric['decimals'] = -5
    assert field.to_dict()['numeric'] == {'decimals': 1}


def test_an_unknown_ontology_term_id_raises_value_error(monkeypatch):
    def not_found(term_id):
        raise KeyError(term_id)
    monkeypatch.setattr(F, 'get_term', not_found)
    _, layer = _new_layer()
    field = layer.add_field(FieldType.ONTOLOGY_SELECT, 'Assay')
    with pytest.raises(ValueError):
        field.ontology_term = 'XYZ:0000001'


class _Klass:
    def __init__(self, name, label, is_generic):
        self.name, self.label, self.is_generic = name, label, is_generic


def test_the_server_s_built_in_klasses_count_as_built_in():
    from chemotion_api.labImotion import _built_in_label
    klasses = [_Klass('vessel', 'Vessel', False), _Klass('mbio', 'Micro Biology', True)]
    assert _built_in_label('vessel', klasses) == 'Vessel'
    assert _built_in_label('Micro Biology', klasses) is None


def test_an_integer_field_keeps_numeric():
    """The designer adds ``numeric`` to integer fields too."""
    integer = {'type': 'integer', 'field': 'n_int', 'numeric': {'decimals': 0, 'min': '', 'max': ''}}
    klass = GenericElementKlass(_payload(integer), None)
    assert _field(klass, 'n_int').numeric == integer['numeric']
    assert _saved(klass, 'n_int')['numeric'] == integer['numeric']


def test_a_name_of_a_built_in_type_is_refused(monkeypatch):
    monkeypatch.setattr(GenericElementKlass, 'load_all', classmethod(lambda cls, con, strict=False: []))
    with pytest.raises(ValueError, match='built-in'):
        GenericManager(_NoCreate()).create_new_element('My samples', 'leaf', name='sample')
