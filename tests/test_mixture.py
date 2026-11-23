"""Mixture components survive a save made through this client.

ELN 3.1.4 reconciles a mixture's components whenever a reaction is saved
(``Usecases::Components::Reconcile``): an explicit ``components: []`` deletes them, a missing key
leaves them alone. The client passes the components it loaded straight back, so a save must keep
them. These tests pin that down, for a plain sample save and for a mixture used in a reaction.

The client cannot create a mixture's components itself, so the test builds the mixture with the
server's own components endpoint (``PUT /api/v1/components``), as the web UI does.
"""
import pytest


def _components(instance, sample_id: int) -> list[dict]:
    res = instance._con.get(f'/api/v1/components/{sample_id}')
    assert res.status_code == 200, res.text
    return res.json()


@pytest.fixture()
def mixture(instance_with_collection):
    instance = instance_with_collection['instance']
    col = instance_with_collection['main_collection']

    parts = []
    for smiles in ['CCO', 'O']:
        s = col.new_sample_smiles(smiles)
        s.save()
        parts.append(s)

    mix = col.new_sample_smiles('CCO')
    mix.json_data['sample_type'] = 'Mixture'
    mix.properties['name'] = 'API_TEST mixture'
    mix.save()
    assert instance.get_sample(mix.id).is_mixture

    payload = {'sample_id': mix.id, 'components': [
        {'id': f'new_{i}', 'name': p.molecule['iupac_name'] or f'part {i}', 'position': i,
         'component_properties': {'molecule_id': p.molecule.id, 'amount_mol': 0.001 * (i + 1),
                                  'material_group': 'liquid'}}
        for i, p in enumerate(parts)
    ]}
    res = instance._con.put('/api/v1/components', json=payload)
    assert res.status_code == 200, res.text
    assert len(_components(instance, mix.id)) == 2

    yield instance_with_collection | {'mixture_id': mix.id}


def test_mixture_save_keeps_components(mixture):
    instance = mixture['instance']
    mix = instance.get_sample(mixture['mixture_id'])
    assert len(mix.json_data['components']) == 2

    data = mix.clean_data()
    assert data['sample_type'] == 'Mixture'
    assert len(data['components']) == 2  # the loaded components go back, never an empty list

    mix.properties['description'] = 'saved by the client'
    mix.save()
    reloaded = instance.get_sample(mix.id)
    assert reloaded.is_mixture
    assert len(_components(instance, mix.id)) == 2


def test_mixture_in_reaction_keeps_components(mixture):
    instance = mixture['instance']
    col = mixture['main_collection']

    reaction = col.new_reaction()
    reaction.properties['starting_materials'].append(instance.get_sample(mixture['mixture_id']))
    reaction.save()

    # The reaction holds a sub-sample of the mixture; the server copies the components onto it.
    reaction = instance.get_reaction(reaction.id)
    material = reaction.properties['starting_materials'][0]
    assert material.is_mixture
    assert len(_components(instance, material.id)) == 2

    # Save the reaction again: the material is now an existing sample, and 3.1.4 reconciles its
    # components against what the client sends.
    reaction.properties['name'] = 'API_TEST mixture reaction'
    reaction.save()
    reaction = instance.get_reaction(reaction.id)
    material = reaction.properties['starting_materials'][0]
    assert len(_components(instance, material.id)) == 2
    assert len(material.json_data['components']) == 2

    # The parent mixture is untouched by all of this.
    assert len(_components(instance, mixture['mixture_id'])) == 2
