"""Serialising a reaction or research plan does not change it, so a failed save loses nothing.

`Reaction._clean_variations` dropped the Variations object while serialising, before the request;
when the save then failed, `reaction.variations` was rebuilt from the stale server data and the
unsaved edits were gone. `ResearchPlan._clean_properties_data` wrote the serialised body into
`json_data` before the request.
"""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from chemotion_api.elements.abstract_element import AbstractElement
from chemotion_api.elements.research_plan import ResearchPlan
from test_sample_properties import SEGMENTS, SESSION, _reaction, _sample


def _failing_save(self, load_after_save=False):
    """Serialises as AbstractElement.save does, then the request fails."""
    self._clean_properties_data()
    raise ConnectionError('500 from the server')


def _edited_reaction():
    reaction = _reaction([_sample(1)])
    reaction._properties['description'] = {'ops': []}
    reaction._properties['observation'] = {'ops': []}
    reaction.variations.add_new().notes = 'draft'
    return reaction


def test_a_failed_reaction_save_keeps_the_variation_edits(monkeypatch):
    reaction = _edited_reaction()
    monkeypatch.setattr(AbstractElement, 'save', _failing_save)
    with pytest.raises(ConnectionError):
        reaction.save()
    assert [v.notes for v in reaction.variations] == ['draft']


def test_serialising_a_reaction_keeps_the_variation_edits():
    reaction = _edited_reaction()
    assert reaction._clean_properties_data()['variations'][0]['metadata']['notes'] == 'draft'
    assert [v.notes for v in reaction.variations] == ['draft']


def test_a_successful_reaction_save_rebuilds_the_variations(monkeypatch):
    reaction = _edited_reaction()
    monkeypatch.setattr(AbstractElement, 'save', lambda self, load_after_save=False: self._clean_properties_data())
    reaction.save()
    assert reaction._variations is None


def test_saved_variations_stay_after_a_successful_save(monkeypatch):
    """A PUT does not refresh `json_data`: the rebuild read the variations as loaded, and the next
    save (variations untouched) sent those back over the saved ones."""
    sent = []
    monkeypatch.setattr(AbstractElement, 'save',
                        lambda self, load_after_save=False: sent.append(self._clean_properties_data()['variations']))
    reaction = _edited_reaction()
    reaction.save()
    assert [v.notes for v in reaction.variations] == ['draft']
    reaction._variations = None  # the next save does not touch the variations
    reaction.save()
    assert sent[1][0]['metadata']['notes'] == 'draft'


BODY = [{'id': 'b1', 'type': 'richtext', 'value': {'ops': [{'insert': 'old\n'}]}}]


def _plan():
    return ResearchPlan(SEGMENTS, SESSION, json_data={'id': 3, 'type': 'research_plan', 'name': 'P',
                                                      'body': copy.deepcopy(BODY), 'user_labels': []})


def test_serialising_a_research_plan_leaves_its_json_data_alone():
    plan = _plan()
    plan.add_richtext('new')
    sent = plan._clean_properties_data()
    assert [elem['id'] for elem in sent['body']][0] == 'b1' and len(sent['body']) == 2
    assert plan.json_data['body'] == BODY


def test_a_failed_research_plan_save_leaves_its_json_data_alone(monkeypatch):
    plan = _plan()
    plan.add_richtext('new')
    monkeypatch.setattr(AbstractElement, 'save', _failing_save)
    with pytest.raises(ConnectionError):
        plan.save()
    assert plan.json_data['body'] == BODY
    assert len(plan.body) == 2
