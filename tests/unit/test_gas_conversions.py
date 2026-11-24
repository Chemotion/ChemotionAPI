"""Gas-phase amount conversions follow the ELN 4.0.2 formulas (UnitsConversion.js, Sample.js).

Feedstock: n = V * purity / (R * T_default), and back V = n * R * T_default / purity.
Gas product: n = ppm * V_vessel / (R * T * 10^6) with the vessel volume in litres; no amount when
the vessel size, temperature or concentration is missing.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from chemotion_api.elements.reaction import Variation
from chemotion_api.elements.utils import GasCalculations, GasType, QuantityUnit, calculate_quantity

R = GasCalculations.IDEAL_GAS_CONSTANT
T0 = GasCalculations.DEFAULT_TEMPERATURE_IN_KELVIN


def _convert(value, current, output, gas_type, **kwargs):
    return calculate_quantity(value, current, output, molecular_weight=28.0, purity=kwargs.pop('purity', 1.0),
                              gas_type=gas_type, **kwargs)


@pytest.mark.parametrize('purity', [1.0, 0.5])
def test_feedstock_mol_to_litre_is_the_inverse_of_litre_to_mol(purity):
    mol = _convert(10.0, QuantityUnit.Liter, QuantityUnit.Mole, GasType.FEEDSTOCK, purity=purity)
    assert _convert(mol, QuantityUnit.Mole, QuantityUnit.Liter, GasType.FEEDSTOCK, purity=purity) == pytest.approx(10.0)


def test_feedstock_volume_grows_with_the_amount():
    # V = n * R * T / purity
    assert _convert(2.0, QuantityUnit.Mole, QuantityUnit.Liter, GasType.FEEDSTOCK) == pytest.approx(2.0 * R * T0)
    assert _convert(0.0, QuantityUnit.Mole, QuantityUnit.Liter, GasType.FEEDSTOCK) == 0.0


def test_feedstock_without_purity_counts_as_pure():
    assert _convert(2.0, QuantityUnit.Mole, QuantityUnit.Liter, GasType.FEEDSTOCK, purity=None) == pytest.approx(2.0 * R * T0)


def test_gas_product_amount_from_vessel_ppm_and_temperature():
    kwargs = dict(vessel_size=0.5, temperature_in_k=300.0, ppm=1000.0)
    mol = _convert(0, QuantityUnit.Mole, QuantityUnit.Mole, GasType.GAS, **kwargs)
    assert mol == pytest.approx(1000.0 * 0.5 / (R * 300.0 * 1_000_000))
    assert _convert(0, QuantityUnit.Mole, QuantityUnit.Liter, GasType.GAS, **kwargs) == pytest.approx(mol * R * 300.0)


@pytest.mark.parametrize('missing', [
    dict(vessel_size=None), dict(vessel_size=0), dict(temperature_in_k=0), dict(temperature_in_k=None),
    dict(ppm=None), dict(ppm=0),
])
@pytest.mark.parametrize('output', [QuantityUnit.Mole, QuantityUnit.Liter])
def test_gas_product_without_vessel_temperature_or_ppm_has_no_amount(missing, output):
    kwargs = dict(vessel_size=0.5, temperature_in_k=300.0, ppm=1000.0) | missing
    assert math.isnan(_convert(0, QuantityUnit.Mole, output, GasType.GAS, **kwargs))


@pytest.mark.parametrize('given, litres', [
    (None, None), ({'amount': None, 'unit': 'ml'}, None),
    ({'amount': 250, 'unit': 'ml'}, 0.25), ({'amount': 2, 'unit': 'l'}, 2.0),
])
def test_vessel_volume_in_litres(given, litres):
    from chemotion_api.elements.utils import vessel_volume_l

    assert vessel_volume_l(given) == litres


def test_a_variation_records_the_vessel_volume_in_litres():
    # The ELN writes aux.vesselVolume in litres (ReactionVariations.js, GasPhaseReactionStore).
    assert Variation._get_vessel_volume({'amount': 250, 'unit': 'ml'}) == 0.25


def test_a_sample_passes_its_vessel_volume_in_litres(monkeypatch):
    # `Sample.vessel_size` is in ml; the gas maths take litres, as the ELN does.
    import chemotion_api.elements.sample as sample_mod
    from test_review_regressions import _Stub

    stub = _Stub(GasType.GAS, reaction=object())
    stub.vessel_size = 250.0
    seen = {}
    monkeypatch.setattr(sample_mod, 'calculate_quantity', lambda **kw: seen.update(kw) or 0.0)
    sample_mod.Sample._get_converted_amount(stub, QuantityUnit.Mole)
    assert seen['vessel_size'] == 0.25
