"""Looking up and creating elements: failures raise a clear error (#ISSUE)."""
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from test_sample_properties import SEGMENTS, SESSION  # noqa: E402

from chemotion_api.connection import ChemotionRequestError  # noqa: E402
from chemotion_api.element_manager import ElementManager  # noqa: E402
from chemotion_api.elements.generic_element import GenericElement  # noqa: E402


# --- ElementManager.build_new for a generic type ----------------------------------------------

def _manager(status, body):
    session = SimpleNamespace(get=lambda url, **kw: SimpleNamespace(
        status_code=status, text=str(body), url=url, json=lambda: body))
    manager = ElementManager(session)
    manager._all_classes = {'try': {'name': 'try', 'is_generic': True}}
    return manager


def test_build_new_raises_on_an_http_error():
    with pytest.raises(ChemotionRequestError, match='generic element type "try"'):
        _manager(500, {}).build_new('try', 1)


@pytest.mark.parametrize('body', [{'klass': None}, {'klass': []}])
def test_build_new_names_a_missing_klass(body):
    """The ELN answers 200 with `{"klass": null}` for an unknown name, `{"klass": []}` on a
    server-side failure."""
    with pytest.raises(ValueError, match='no generic element type "try"'):
        _manager(200, body).build_new('try', 1)


def test_build_new_names_a_template_without_a_release():
    body = {'klass': {'id': 1, 'name': 'try', 'label': 'Tryout', 'properties_release': None}}
    with pytest.raises(ValueError, match='"try" has no released template'):
        _manager(200, body).build_new('try', 1)


# --- GenericElement.field() and .workflow on a listed element whose load failed ---------------

def _listed_generic():
    """A generic element from a listing, whose full record cannot be fetched."""
    layers = {'gen': {'key': 'gen', 'label': 'General', 'position': 10, 'wf': False,
                      'fields': [{'field': 'strain', 'label': 'Strain', 'type': 'text', 'value': ''}]}}
    listing = {'id': 13, 'type': 'try', 'name': 'listed', 'short_label': 'API-TRY1',
               'properties': {'layers': layers, 'select_options': {}},
               'properties_release': {'layers': layers, 'select_options': {}},
               'element_klass': {'name': 'try'}}

    def failing_get(url, **kw):
        return SimpleNamespace(status_code=500, headers={}, text='boom', json=lambda: {},
                               request=None, url=url)
    element = GenericElement(SEGMENTS, SimpleNamespace(**vars(SESSION), get=failing_get), json_data=listing)
    element.mark_partial()
    return element


@pytest.mark.parametrize('access', [lambda e: e.field('General', 'Strain'), lambda e: e.workflow],
                         ids=['field', 'workflow'])
def test_a_failed_load_raises_instead_of_returning_listing_data(access):
    """`_load_if_partial()` raised on the first access only: `load()` clears `_is_partial` before
    its request, so the next access read the listing's data. The other accessors use
    `_require_loaded()`, which keeps raising."""
    element = _listed_generic()
    _ = element.properties                  # lenient: logs and falls back to the listing
    for _attempt in range(2):
        with pytest.raises(ConnectionError, match='could not be loaded'):
            access(element)
