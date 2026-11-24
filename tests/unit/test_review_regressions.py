"""Two regressions introduced while fixing other things, and caught only by review.

Both slipped through a green integration suite, which is why they are pinned offline:

* removing the side effect from ``Sample.gas_type`` also removed a guard the amount maths relied
  on — a detached sample with a gas role pushed ``None`` into the gas arithmetic;
* adding the issue #14 type check read ``klass_name`` unconditionally, so asking for a *built-in*
  type raised ``AttributeError``. A built-in type is now refused before any request, with a
  ``ValueError`` that names its own accessor.

These assert behaviour, not the source text: a test that greps the implementation passes for the
wrong reason and fails on an equivalent rewrite.
"""
import pytest

import chemotion_api.elements.sample as sample_mod
from chemotion_api.elements.sample import GasType, Sample


class _Stub:
    """The attributes `Sample._get_converted_amount` reads, with a settable reaction."""

    def __init__(self, gas_type, reaction):
        self._properties = {'gas_type': gas_type}
        self.reaction = self._reaction = reaction
        self.role_in_reaction = 'starting_materials'
        self.vessel_size = None if reaction is None else 1.0
        self.molecule = {'molecular_weight': 100.0}
        self.properties = {
            'target_amount': {'value': 1.0, 'unit': 'g'},
            'purity': 1.0,
            'molarity': {'value': 0.0},
            'density': 0.0,
            'gas_phase_data': None,
        }

    gas_type = property(lambda self: Sample.gas_type.fget(self))

    def _tagged_reaction_id(self):
        return None


# --- reading gas_type is pure -------------------------------------------------------------

@pytest.mark.parametrize("stored", [GasType.OFF, GasType.GAS])
def test_reading_gas_type_makes_no_request_and_no_write(stored):
    """It used to load the linked reaction and write `OFF` back when there was none.

    So reading one property issued a request *and* mutated the sample — and raised when that
    reaction held a field this client could not parse. `reaction` here is a sentinel that fails
    loudly if the getter touches it.
    """
    class _Explode:
        def __getattr__(self, _):
            raise AssertionError("reading gas_type must not touch the reaction")

    stub = _Stub(stored, reaction=_Explode())
    assert stub.gas_type is stored
    assert stub._properties['gas_type'] is stored, "reading must not rewrite the sample"


# --- but the amount maths must still be protected -----------------------------------------

@pytest.mark.parametrize("reaction, expected", [
    (None, GasType.OFF),      # detached: gas role neutralised, vessel_size would be None
    (object(), GasType.GAS),  # in a reaction: the real role is used
])
def test_amount_conversion_neutralises_gas_for_a_detached_sample(monkeypatch, reaction, expected):
    """`vessel_size` comes from the reaction, so a detached gas sample would pass `None` in.

    The getter reports OFF for a sample in no reaction — without rewriting the sample — and the
    conversion takes its role from the getter.
    """
    seen = {}
    monkeypatch.setattr(sample_mod, 'calculate_quantity',
                        lambda **kw: seen.update(kw) or 0.0)
    Sample._get_converted_amount(_Stub(GasType.GAS, reaction), 'g')
    assert seen['gas_type'] is expected


# --- the issue #14 type check must not break built-in types -------------------------------

def _instance_with(element):
    """An `Instance` whose generic lookup yields `element`, with no server involved."""
    from chemotion_api import Instance

    inst = Instance.__new__(Instance)
    inst._con = None
    type(inst).all_element_classes = property(
        lambda self: {'sample': {'name': 'sample', 'is_generic': False},
                      'sequence_based_macromolecule_sample': {
                          'name': 'sequence_based_macromolecule_sample', 'is_generic': False},
                      'try': {'name': 'try', 'is_generic': True}})
    monkey = type('ES', (), {'__init__': lambda s, *a: None,
                             'load_element': lambda s, _id: element})
    return inst, monkey


@pytest.mark.parametrize('name, accessor', [
    ('sample', 'get_sample'),
    ('sequence_based_macromolecule_sample', 'get_sbmm_sample'),
])
def test_a_builtin_type_is_refused_with_its_accessor(monkeypatch, name, accessor):
    """`all_element_classes` holds built-ins too. `get_generic_by_name('sample', 1)` used to
    return a `Sample` despite `-> GenericElement`; it now refuses and names the right accessor.

    This replaces a test that pinned the old behaviour (a built-in returned without an
    AttributeError): that only guarded the #14 check, and the built-in no longer reaches it.
    """
    import chemotion_api as pkg

    element = object()  # deliberately has no `klass_name`
    inst, es = _instance_with(element)
    monkeypatch.setattr(pkg, 'ElementSet', es)
    with pytest.raises(ValueError, match=rf'built-in element type.*Instance\.{accessor}\(\)'):
        pkg.Instance.get_generic_by_name(inst, name, 1)


def test_a_mismatched_generic_type_is_refused(monkeypatch):
    """The #14 guard still fires once made defensive."""
    import chemotion_api as pkg

    element = type('G', (), {'klass_name': 'wrk'})()
    inst, es = _instance_with(element)
    monkeypatch.setattr(pkg, 'ElementSet', es)
    with pytest.raises(ValueError, match='is a "wrk", not a "try"'):
        pkg.Instance.get_generic_by_name(inst, 'try', 1)
