"""A molecule whose ``cas`` is ``[null]``, as the ELN sends it for some molecules, loads (#23)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from test_sample_properties import SEGMENTS, SESSION, _sample_json  # noqa: E402

from chemotion_api.elements.reaction import Reaction  # noqa: E402
from chemotion_api.elements.sample import Sample  # noqa: E402

MOLECULE = {'id': 1, 'molecular_weight': 329.27, 'cas': [None]}


def test_a_sample_whose_molecule_has_cas_null_loads():
    sample = Sample(SEGMENTS, SESSION, json_data=_sample_json(2, molecule=dict(MOLECULE)))
    assert sample.molecule['cas'] == [None]


def test_a_reaction_whose_reactant_molecule_has_cas_null_loads():
    reactant = _sample_json(2, molecule=dict(MOLECULE)) | {'reference': False, 'coefficient': 1, 'waste': False}
    reaction = Reaction(SEGMENTS, SESSION, json_data={
        'id': 1, 'type': 'reaction', 'name': '', 'starting_materials': [], 'reactants': [reactant],
        'products': [], 'solvents': [], 'purification_solvents': []})
    assert reaction.properties['reactants'][0].molecule['cas'] == [None]
    assert reaction.json_data['reactants'][0]['molecule']['cas'] == [None]
