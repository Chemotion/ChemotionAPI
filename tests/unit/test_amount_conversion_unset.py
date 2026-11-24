"""An unset density or molarity (0, the ELN's default, or None) gives no volume-based conversion.

`None != 0` is true, so None was taken as a known value (TypeError in the arithmetic), and a
volume with neither value set was returned unchanged as a mass in gram.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from test_sample_properties import _sample  # noqa: E402

from chemotion_api.elements.utils import QuantityUnit, calculate_quantity  # noqa: E402


@pytest.mark.parametrize('unset', [0, None])
@pytest.mark.parametrize('current, output', [
    (QuantityUnit.Liter, QuantityUnit.Gram),
    (QuantityUnit.Liter, QuantityUnit.Mole),
    (QuantityUnit.Gram, QuantityUnit.Liter),
    (QuantityUnit.Mole, QuantityUnit.Liter),
])
def test_no_volume_conversion_without_density_or_molarity(current, output, unset):
    value = calculate_quantity(2.0, current, output, molecular_weight=100.0, purity=1.0,
                               density=unset, molarity=unset)
    assert math.isnan(value)


def test_a_volume_without_density_or_molarity_has_no_mass():
    # ELN defaults: density 0, molarity 0
    sample = _sample(target_amount_value=5.0, target_amount_unit='l', density=0, molarity_value=0)
    assert sample.gram is None
    assert sample.liter == 5.0


def test_unset_density_and_molarity_as_none():
    sample = _sample(target_amount_value=1.0, target_amount_unit='g', density=None, molarity_value=None)
    assert sample.liter is None
    assert sample.mol == pytest.approx(0.01)
    assert QuantityUnit.Liter not in sample.allowed_quantity_units()


def test_known_density_and_molarity_still_convert():
    assert calculate_quantity(2.0, QuantityUnit.Liter, QuantityUnit.Gram, 100.0, 1.0, density=0.8) == 1600.0
    assert calculate_quantity(2.0, QuantityUnit.Liter, QuantityUnit.Mole, 100.0, 1.0, molarity=0.5) == 1.0
    assert calculate_quantity(2.0, QuantityUnit.Liter, QuantityUnit.Gram, 100.0, 1.0, molarity=0.5) == 100.0


def test_a_variation_with_molarity_none_converts_a_volume_by_density():
    from test_sample_variation import _variation

    sv = _variation(mw=100.0, purity=0.5, molarity=None, density=0.8)
    sv.set_quantity(2, QuantityUnit.Liter)
    assert sv.get_amount() == pytest.approx(8.0)
