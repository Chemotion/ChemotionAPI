"""Edits made to an element obtained from a listing survive the full load that follows.

A listing carries only part of each element; the full record is fetched on first use. Any edit
applied before that fetch is overwritten by it unless the edit loads first.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(__file__))
from test_sample_properties import SEGMENTS, SESSION, _sample_json  # noqa: E402

from chemotion_api.elements.sample import Molecule, Sample  # noqa: E402


def _listed_sample():
    full = _sample_json(2) | {'molecule': {'id': 1, 'molecular_weight': 100.0}}
    listing = {k: full[k] for k in ('id', 'type', 'name', 'short_label', 'molecule')}
    session = SimpleNamespace(**vars(SESSION), get=lambda url, **kw: SimpleNamespace(
        status_code=200, headers={}, json=lambda: {'sample': full, 'attachments': []}))
    sample = Sample(SEGMENTS, session, json_data=listing)
    sample.mark_partial()
    return sample


def test_a_molecule_assigned_to_a_listed_sample_is_kept():
    sample = _listed_sample()
    sample.molecule = Molecule({'id': 7, 'molecular_weight': 46.07, 'density': 0.789})
    assert sample.molecule['id'] == 7


def test_a_name_assigned_to_a_listed_sample_is_kept():
    sample = _listed_sample()
    sample.name = 'renamed'
    assert sample.name == 'renamed'


def test_a_file_queued_on_an_element_built_from_a_parent_survives_the_load(tmp_path):
    """Elements built from a parent's payload (a reaction's or wellplate's samples) are neither
    listed nor loaded. The attachments getter did not load them, so the load triggered by the next
    `properties` read replaced the container and dropped the queued file (review of PR #16,
    'patch each writer instead of the root cause')."""
    full = _sample_json(2)
    session = SimpleNamespace(**vars(SESSION), host_url='http://localhost', get=lambda url, **kw: SimpleNamespace(
        status_code=200, headers={}, json=lambda: {'sample': full, 'attachments': []}))
    sample = Sample(SEGMENTS, session, json_data=dict(full))
    assert not sample.is_loaded
    path = tmp_path / 'spectrum.txt'
    path.write_text('1 2 3')
    sample.attachments.add_file(str(path))
    _ = sample.properties
    assert any(a.get('filename') == 'spectrum.txt' for a in sample.attachments.attachment_data)


def test_a_failed_load_raises_from_the_accessors_instead_of_returning_listing_data():
    """Review of #18: analyses and attachments used to raise when the full record could not be
    fetched; after the switch to the lenient load they returned the listing's empty data."""
    import pytest
    listing = {k: _sample_json(2)[k] for k in ('id', 'type', 'name', 'short_label')}

    def failing_get(url, **kw):
        return SimpleNamespace(status_code=500, headers={}, text='boom', json=lambda: {},
                               request=None, url=url)
    sample = Sample(SEGMENTS, SimpleNamespace(**vars(SESSION), get=failing_get), json_data=listing)
    sample.mark_partial()
    with pytest.raises(ConnectionError):
        _ = sample.analyses


def test_a_failed_load_keeps_raising_on_later_accesses():
    """`load()` clears `_is_partial` before its request, so the second access used to return the
    listing's data."""
    import pytest
    listing = {k: _sample_json(2)[k] for k in ('id', 'type', 'name', 'short_label')}

    def failing_get(url, **kw):
        return SimpleNamespace(status_code=500, headers={}, text='boom', json=lambda: {},
                               request=None, url=url)
    sample = Sample(SEGMENTS, SimpleNamespace(**vars(SESSION), get=failing_get), json_data=listing)
    sample.mark_partial()
    _ = sample.properties                   # lenient: logs and falls back to the listing
    for _attempt in range(2):
        with pytest.raises(ConnectionError):
            _ = sample.analyses
