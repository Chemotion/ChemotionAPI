"""TypedList item and slice assignment check and prepare every item, as append() does.

A slice assignment type-checked the iterable instead of its items, so `materials[:] = [sample]`
always raised TypeError, and it handed the whole iterable to `_prepare_element`. Neither form of
assignment called `after_append`, so a MaterialList entry set by index got no amount initialised.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from chemotion_api.utils import TypedList
from test_sample_properties import _reaction, _sample


class _Recording(TypedList):
    def __init__(self, *args):
        self.prepared, self.appended = [], []
        super().__init__(int, *args)

    def _prepare_element(self, element):
        self.prepared.append(element)
        return element * 10

    def after_append(self, element):
        self.appended.append(element)


def test_slice_assignment_checks_and_prepares_each_item():
    tl = _Recording([1, 2, 3])
    tl[0:2] = [4, 5]
    assert list(tl) == [40, 50, 3]
    assert tl.prepared == [4, 5] and tl.appended == [40, 50]


def test_slice_assignment_takes_any_iterable():
    tl = _Recording([1])
    tl[:] = (x for x in (7, 8))
    assert list(tl) == [70, 80]


def test_slice_assignment_refuses_a_wrong_item_and_keeps_the_list():
    tl = _Recording([1, 2])
    with pytest.raises(TypeError, match='int'):
        tl[:] = [3, 'x']
    assert list(tl) == [1, 2] and tl.prepared == []


def test_index_assignment_prepares_and_calls_after_append():
    tl = _Recording([1, 2])
    tl[1] = 6
    assert list(tl) == [1, 60] and tl.appended == [60]
    with pytest.raises(TypeError):
        tl[0] = 'x'


def test_slice_assignment_binds_samples_to_the_reaction():
    reaction = _reaction([_sample(1)])
    first, second = _sample(2), _sample(3)
    reaction.properties['solvents'][:] = [first, second]
    assert list(reaction.properties['solvents']) == [first, second]
    for sample in (first, second):
        assert sample.reaction is reaction and sample.role_in_reaction == 'solvents'


def test_slice_assignment_gives_each_sample_its_position():
    reaction = _reaction([])
    a, b, c = _sample(11), _sample(12), _sample(13)
    reaction.solvents.extend([a, b])
    reaction.solvents[0:1] = [c]
    assert [s.properties['position'] for s in reaction.solvents] == [0, 1]
    reaction.solvents[1] = a
    assert a.properties['position'] == 1


def test_slice_assignment_refuses_a_sample_given_twice():
    reaction = _reaction([])
    solvent = _sample(14)
    with pytest.raises(ValueError, match='given twice'):
        reaction.solvents[0:0] = [solvent, solvent]
    assert list(reaction.solvents) == []


def test_a_slice_may_put_back_the_samples_it_replaces():
    reaction = _reaction([])
    a, b = _sample(15), _sample(16)
    reaction.solvents.extend([a, b])
    reaction.solvents[:] = [b, a]
    assert list(reaction.solvents) == [b, a]
    assert [s.properties['position'] for s in reaction.solvents] == [0, 1]
