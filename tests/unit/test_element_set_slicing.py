"""ElementSet slices return the elements at those positions, read at the set's own page size.

A slice with a start used the start as the page size and began on page 2: `elements[0:3]` asked
for per_page=0, and `elements[150:160]` asked for more per page than the server serves (100), so
page 2 began at element 100, not 150.
"""
import math
from types import SimpleNamespace

import pytest

from chemotion_api.elements import ElementSet

TOTAL = 25


class _Server:
    """TOTAL samples with ids 0..TOTAL-1; per_page is capped at `max_per_page`, as the ELN does."""

    def __init__(self, max_per_page):
        self.max_per_page = max_per_page
        self.requests = []

    def get(self, url, data=None, **kw):
        self.requests.append((data['page'], data['per_page']))
        per_page = min(data['per_page'], self.max_per_page)
        first = (data['page'] - 1) * per_page
        ids = range(first, min(first + per_page, TOTAL)) if per_page > 0 else range(0)
        rows = [{'id': i, 'type': 'sample', 'short_label': f'S-{i}', 'name': f's{i}'} for i in ids]
        pages = math.ceil(TOTAL / per_page) if per_page > 0 else 0
        return SimpleNamespace(status_code=200, headers={'X-Total-Pages': str(pages), 'X-Total': str(TOTAL)},
                               json=lambda: {'samples': rows})


def _set(monkeypatch, per_page=10, max_per_page=10, **kwargs):
    server = _Server(max_per_page)
    monkeypatch.setattr('chemotion_api.elements.GenericSegments', lambda session: SimpleNamespace(all_classes=[]))
    monkeypatch.setattr(ElementSet, '_get_element_class',
                        lambda self: lambda seg, ses, json_data: SimpleNamespace(
                            json_data=json_data, id=json_data['id'], mark_partial=lambda: None))
    es = ElementSet(server, {'name': 'sample', 'is_generic': False, 'label': 'Sample'}, 7, **kwargs)
    es._per_page = per_page
    return es, server


@pytest.mark.parametrize('start, stop', [(0, 3), (2, 5), (12, 15), (8, 13), (20, 25)])
def test_a_slice_returns_the_elements_at_its_positions(monkeypatch, start, stop):
    es, server = _set(monkeypatch)
    assert [e.id for e in es[start:stop]] == list(range(start, stop))
    assert all(per_page == 10 for _, per_page in server.requests)
    assert es._per_page == 10


def test_a_slice_starting_past_the_server_page_cap(monkeypatch):
    es, server = _set(monkeypatch, per_page=5, max_per_page=5)
    es.page = 1
    assert [e.id for e in es[17:19]] == [17, 18]
    assert server.requests == [(1, 5), (4, 5)]


def test_a_slice_after_loading_with_an_explicit_page_size(monkeypatch):
    es, server = _set(monkeypatch)
    es.load_elements(per_page=10)
    assert [e.id for e in es[0:3]] == [0, 1, 2]
    assert [e.id for e in es[13:16]] == [13, 14, 15]


def test_a_slice_runs_to_the_end_of_the_set(monkeypatch):
    es, _ = _set(monkeypatch)
    assert [e.id for e in es[22:40]] == [22, 23, 24]


def test_a_slice_of_search_results(monkeypatch):
    """A fixed-length set (search results) holds all its elements on page 1."""
    es, server = _set(monkeypatch, fixed_length=True)
    list.extend(es, [SimpleNamespace(id=i) for i in range(4)])
    assert [e.id for e in es[1:3]] == [1, 2]
    assert server.requests == []
