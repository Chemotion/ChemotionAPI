"""New elements start from the ELN editor's own defaults (401.1)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from test_sample_properties import SEGMENTS, SESSION  # noqa: E402

import chemotion_api  # noqa: E402

EMPTY = os.path.join(os.path.dirname(chemotion_api.__file__), 'elements', 'empty_elements')


def test_a_new_sbmm_samples_quantity_unit_can_be_changed():
    """The editor seeds the numeric values with '', which the quantity model (float|None) rejects."""
    from chemotion_api.elements.sbmm_sample import SbmmSample
    with open(os.path.join(EMPTY, 'sequence_based_macromolecule_sample.json')) as f:
        template = json.load(f)
    sample = SbmmSample(SEGMENTS, SESSION, json_data=template)
    sample._data_loaded = True
    sample.properties['activity']['unit'] = 'U/L'
    assert sample.properties['activity'] == {'value': None, 'unit': 'U/L'}


def test_a_new_reaction_carries_the_editors_concentration_mode():
    with open(os.path.join(EMPTY, 'reaction.json')) as f:
        assert json.load(f)['concentration_mode'] == 'solvents_only'
