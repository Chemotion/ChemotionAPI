"""Fields the ELN's routes do not declare are dropped without an error; the client refuses them.

Found by comparing what the client sends on create and update with ELN v4.0.1's declared
parameters (2026-11-14).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from test_sample_properties import SEGMENTS, SESSION, _sample_json  # noqa: E402

from chemotion_api.elements.reaction import Reaction  # noqa: E402
from chemotion_api.elements.sample import Sample  # noqa: E402


def _sample():
    sample = Sample(SEGMENTS, SESSION, json_data=_sample_json(2))
    sample._data_loaded = True
    return sample


@pytest.mark.parametrize('field, value', [('waste', True), ('reference', True), ('coefficient', 2)])
def test_a_link_field_changed_on_a_sample_cannot_be_saved_through_the_sample(field, value):
    sample = _sample()
    sample.properties[field] = value
    with pytest.raises(ValueError, match='reaction.save'):
        sample.save()


def test_a_saved_samples_short_label_cannot_be_changed():
    with pytest.raises(ValueError, match='short label'):
        _sample().properties['short_label'] = 'X-1'


def test_reaction_rinchi_cannot_be_set():
    reaction = Reaction(SEGMENTS, SESSION, json_data={
        'id': 1, 'type': 'reaction', 'name': '', 'starting_materials': [], 'reactants': [],
        'products': [], 'solvents': [], 'purification_solvents': []})
    reaction._data_loaded = True
    with pytest.raises(ValueError, match='computed by the ELN'):
        reaction.properties['rinchi_string'] = 'RInChI=1.00.1S/'


def test_display_units_set_on_a_new_sample_are_sent_again_after_create(monkeypatch):
    """The create route does not take `metrics`; the update route does."""
    from chemotion_api.elements.abstract_element import AbstractElement
    sample = Sample(SEGMENTS, SESSION, json_data=_sample_json(None) | {'id': None, 'is_new': True})
    sample.properties['metrics'] = 'nmmm'
    calls = []

    def fake_save(self, load_after_save=False):
        calls.append(self.properties['metrics'])
        if self.is_new:                     # what the create answers: the server's default
            self.id = 9
            self.json_data['metrics'] = 'mmmm'
    monkeypatch.setattr(AbstractElement, 'save', fake_save)
    sample.save()
    assert calls == ['nmmm', 'nmmm']


def test_a_rejected_link_field_write_does_not_block_saving():
    sample = _sample()
    with pytest.raises(ValueError):
        sample.properties['coefficient'] = 0
    assert not sample._pending_link_fields


def test_a_reaction_save_that_rebuilds_its_materials_clears_the_callers_objects(monkeypatch):
    """A create or load_after_save re-parses the reaction into new material objects."""
    from chemotion_api.elements.abstract_element import AbstractElement
    material = _sample_json(2) | {'reference': False, 'coefficient': 1}
    record = {'id': 1, 'type': 'reaction', 'name': '', 'starting_materials': [material], 'reactants': [],
              'products': [], 'solvents': [], 'purification_solvents': []}
    reaction = Reaction(SEGMENTS, SESSION, json_data=dict(record))
    reaction._data_loaded = True
    held = reaction.starting_materials[0]
    held.properties['coefficient'] = 2
    monkeypatch.setattr(AbstractElement, 'save', lambda self, load_after_save=False: self._set_json_data(dict(record)))
    monkeypatch.setattr(Reaction, 'update_equivalent', lambda self: None)
    reaction.save()
    assert held is not reaction.starting_materials[0]
    assert not held._pending_link_fields
