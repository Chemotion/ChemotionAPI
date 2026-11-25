"""Restrictions of LabIMotion template fields and layers (``ConditionHandler``): a select option
can be chosen by its label, and restrictions can be cleared."""
import json
import os

import pytest

from chemotion_api.labImotion import GenericElementKlass
from chemotion_api.labImotion.items.layer import Layer
from chemotion_api.labImotion.items.options import ConditionOperator, FieldType

FIXTURE = os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'GenericElement.json')


@pytest.fixture
def klass() -> GenericElementKlass:
    with open(FIXTURE) as f:
        return GenericElementKlass(json.load(f), None)


def _select_and_target(klass):
    props = klass.properties
    layer = props.add_new_layer('Medium')
    props.select_options = props.select_options | {'medium': {'options': [
        {'key': 'lb_broth', 'label': 'LB broth'}, {'key': 'tb_broth', 'label': 'Terrific broth'}]}}
    select = layer.add_field(FieldType.SELECT, 'Medium')
    select.option_layers = 'medium'
    return select, layer.add_field(FieldType.TEXT, 'Notes')


def test_a_select_condition_takes_an_option_label_and_stores_its_key(klass):
    select, target = _select_and_target(klass)
    target.add_condition(select, 'Terrific broth')
    target.add_condition(select, 'lb_broth')
    assert [c['value'] for c in target.cond_fields] == ['tb_broth', 'lb_broth']
    assert [c['value'] for c in target.to_dict()['cond_fields']] == ['tb_broth', 'lb_broth']


def test_a_select_condition_refuses_a_value_that_is_neither_key_nor_label(klass):
    select, target = _select_and_target(klass)
    with pytest.raises(ValueError, match='LB broth, Terrific broth'):
        target.add_condition(select, 'Water')
    assert target.cond_fields is None


def test_the_conditions_of_a_field_can_be_cleared(klass):
    select, target = _select_and_target(klass)
    target.add_condition(select, 'lb_broth')
    target.cond_fields = None
    assert target.cond_fields is None and target.cond_operator is None
    saved = target.to_dict()
    assert 'cond_fields' not in saved and 'cond_operator' not in saved


def test_the_loaded_conditions_of_a_layer_can_be_cleared(klass):
    layer = klass.properties.get_layer_by_key('con')
    assert len(layer.cond_fields) == 2
    layer.cond_fields = None
    saved = layer.to_dict()
    assert 'cond_fields' not in saved and 'cond_operator' not in saved
    Layer(layer._sr, saved)  # validates: a null would not load again


def test_a_loaded_empty_condition_list_is_kept(klass):
    saved = klass.properties.get_layer_by_key('aaa').to_dict()
    assert (saved['cond_fields'], saved['cond_operator']) == ([], 1)


def test_conditions_added_again_after_clearing_are_saved(klass):
    """Clearing dropped the keys from the layer's data, and `to_dict` only wrote keys it had."""
    select, _ = _select_and_target(klass)
    layer = klass.properties.get_layer_by_key('con')
    layer.cond_fields = None
    layer.to_dict()
    layer.add_condition(select, 'lb_broth')
    saved = layer.to_dict()
    assert [c['value'] for c in saved['cond_fields']] == ['lb_broth']
    assert saved['cond_operator'] == 1


def test_conditions_of_a_new_layer_are_saved(klass):
    select, _ = _select_and_target(klass)
    layer = klass.properties.add_new_layer('Restricted')
    layer.add_condition(select, 'tb_broth')
    saved = layer.to_dict()
    assert [c['value'] for c in saved['cond_fields']] == ['tb_broth']
    Layer(layer._sr, saved)  # validates


def test_the_operator_falls_back_to_match_one_when_set_to_none(klass):
    select, target = _select_and_target(klass)
    target.add_condition(select, 'lb_broth')
    target.cond_operator = None
    assert target.cond_operator == ConditionOperator.MATCH_ONE
