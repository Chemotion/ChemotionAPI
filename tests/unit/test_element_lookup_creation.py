"""Looking up and creating elements: failures raise a clear error (#ISSUE)."""
from types import SimpleNamespace

import pytest

from chemotion_api.connection import ChemotionRequestError
from chemotion_api.element_manager import ElementManager


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
