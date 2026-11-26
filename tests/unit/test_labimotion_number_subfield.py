"""The number sub-field of a LabIMotion input-group takes what the designer's number input
(HTML ``type="number"``) takes: sign, decimals and an exponent, or '' for no value."""
import json
import os

import pytest

from chemotion_api.labImotion import GenericElementKlass
from chemotion_api.labImotion.items.options import FieldType, SubFieldType

FIXTURE = os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'GenericElement.json')


@pytest.fixture
def number():
    with open(FIXTURE) as f:
        klass = GenericElementKlass(json.load(f), None)
    group = klass.properties.add_new_layer('Group').add_field(FieldType.INPUT_GROUP, 'Group')
    return group.add_subfield(SubFieldType.NUMBER)


@pytest.mark.parametrize('value, stored', [
    ('-1', '-1'), ('-2.5', '-2.5'), ('1e3', '1e3'), ('1.5E-4', '1.5E-4'), ('.5', '.5'),
    (-3, '-3'), (2.5e-7, '2.5e-07'), (1e16, '1e+16')])
def test_negative_numbers_and_exponents_are_accepted(number, value, stored):
    number.value = value
    assert number.value == stored
    assert number.to_dict()['value'] == stored


def test_an_empty_value_clears_the_number(number):
    number.value = '1'
    number.value = ''
    assert number.to_dict()['value'] == ''


@pytest.mark.parametrize('value', ['...', '.', '1.2.3', '1-2', '1e', 'e3', '--1', 'abc', 'nan', 'inf', ' 1', '1\n'])
def test_text_that_is_not_a_number_is_refused(number, value):
    with pytest.raises(ValueError):
        number.value = value


def test_a_bool_is_refused(number):
    with pytest.raises(TypeError):
        number.value = True
