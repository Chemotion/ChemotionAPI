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


@pytest.mark.parametrize('release', [None, {}])
def test_build_new_names_a_template_without_a_release(release):
    """Never released: null, or `{}` as the column default stores it."""
    body = {'klass': {'id': 1, 'name': 'try', 'label': 'Tryout', 'properties_release': release}}
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


# --- Instance.get_json_ld_id: the id must be from this instance --------------------------------

def _instance_at(monkeypatch, host_url):
    import chemotion_api as pkg

    inst = pkg.Instance.__new__(pkg.Instance)
    inst._con = SimpleNamespace(host_url=host_url)
    monkeypatch.setattr(pkg.Instance, 'all_element_classes',
                        property(lambda self: {'sample': {'name': 'sample', 'is_generic': False}}))
    monkeypatch.setattr(pkg, 'ElementSet', type('ES', (), {
        '__init__': lambda s, *a: None, 'load_element': lambda s, id: ('loaded', id)}))
    return inst


@pytest.mark.parametrize('host_url', ['https://eln.example.org.evil.com', 'https://eln.example.org:8443',
                                      'http://eln.example.org'])
def test_json_ld_id_of_another_origin_is_refused(monkeypatch, host_url):
    """The check compared a prefix only, without the port."""
    inst = _instance_at(monkeypatch, host_url)
    with pytest.raises(ValueError, match='Host does not fit'):
        inst.get_json_ld_id('https://eln.example.org/api/v1/samples/1.json')


@pytest.mark.parametrize('host_url', ['https://eln.example.org', 'https://ELN.example.org:443/'])
def test_json_ld_id_of_this_origin_is_loaded(monkeypatch, host_url):
    inst = _instance_at(monkeypatch, host_url)
    assert inst.get_json_ld_id('https://eln.example.org/api/v1/samples/1.json') == ('loaded', 1)
