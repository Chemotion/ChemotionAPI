"""Smaller fixes from the 2026-11 code review, one section per finding (#ISSUE).
Each test reproduces the reported failure; the ones marked as guards pass before and after."""
from types import SimpleNamespace

import pytest
import requests

from chemotion_api.connection import ChemotionRequestError, ChemotionServerError


def _response(status, text='', method='POST', url='https://eln.example.org/api/v1/x', json=None):
    res = requests.Response()
    res.status_code = status
    res._content = text.encode()
    res.request = requests.Request(method=method, url=url).prepare()
    res.url = url
    if json is not None:
        res.json = lambda: json  # type: ignore[method-assign]
    return res


# F11: AnalysesManager.upload_file

def _upload(tmp_path, chunk_status, complete_status=200):
    from chemotion_api.elements.analyses_manager import AnalysesManager
    f = tmp_path / 'spectrum.jdx'
    f.write_bytes(b'x' * 10)

    def post(url, **kwargs):
        status = complete_status if url.endswith('upload_chunk_complete') else chunk_status
        return _response(status, 'server said no', url='https://eln.example.org' + url)
    return AnalysesManager.upload_file(SimpleNamespace(post=post), str(f), 'key-1')


def test_a_refused_upload_does_not_talk_about_deleting_a_device(tmp_path):
    with pytest.raises(PermissionError) as err:
        _upload(tmp_path, 401)
    message = str(err.value)
    assert 'device' not in message and 'upload' in message
    assert '401' in message and 'server said no' in message and 'spectrum.jdx' in message


def test_a_failed_chunk_says_what_failed(tmp_path):
    with pytest.raises(ConnectionError) as err:
        _upload(tmp_path, 500)
    assert isinstance(err.value, ChemotionServerError)
    assert '500' in str(err.value) and 'server said no' in str(err.value)
    assert 'spectrum.jdx' in str(err.value)


def test_a_failed_completion_says_what_failed(tmp_path):
    with pytest.raises(ConnectionError, match='completing the upload'):
        _upload(tmp_path, 200, complete_status=422)


# F12: ElementManager

def test_a_failed_klass_listing_raises_a_request_error_with_the_status():
    from chemotion_api.element_manager import ElementManager
    em = ElementManager(SimpleNamespace(get=lambda url, **kw: _response(500, 'boom', 'GET')))
    with pytest.raises(ChemotionServerError, match='500') as err:
        em.get_all_classes()
    assert isinstance(err.value, requests.exceptions.RequestException)  # what it raised before


def test_get_next_shot_label_works_on_an_instance(monkeypatch):
    from chemotion_api.element_manager import ElementManager
    em = ElementManager(SimpleNamespace())
    monkeypatch.setattr(em, '_get_short_label', lambda type_name: f'API-{type_name}-1')
    assert em.get_next_shot_label('sample', None) == 'API-sample-1'
    assert em.get_next_shot_label('sample') == 'API-sample-1'


# F14: temperature conversion

def test_a_temperature_below_absolute_zero_is_not_turned_positive():
    from chemotion_api.elements.utils.converter import convert_value
    assert convert_value(-300, '°C', 'K') == pytest.approx(-26.85)
    assert convert_value(-300, '°C', '°F') == pytest.approx(-508)
    assert convert_value(-5, 'K', '°C') == pytest.approx(-278.15)


def test_valid_temperatures_convert_as_before():
    """Guard."""
    from chemotion_api.elements.utils.converter import convert_value
    assert convert_value(25, '°C', 'K') == pytest.approx(298.15)
    assert convert_value(212, '°F', '°C') == pytest.approx(100)


def test_gas_phase_kelvin_stays_absolute_like_the_eln():
    """Guard: the ELN computes gas amounts with |T in K| (frontend convertTemperatureToKelvin,
    backend Reactable#convert_temperature_to_kelvin), so the client keeps doing that there."""
    from chemotion_api.elements.sample import GasPhaseObj
    data = {**GasPhaseObj.default_val, 'temperature': {'unit': '°C', 'value': -300}}
    assert GasPhaseObj(None, data).temperature_in_k == pytest.approx(26.85)  # type: ignore[arg-type]
    assert GasPhaseObj(None).temperature_in_k is None  # type: ignore[arg-type]


# F15: research plan table columns

def test_a_table_gets_a_27th_column():
    from chemotion_api.elements.research_plan import Table
    table = Table('t', {'columns': [], 'rows': [{}]})
    ids = table.add_columns(*[f'C{i}' for i in range(28)])
    assert ids[:26] == [chr(ord('a') + i) for i in range(26)]
    assert all(isinstance(i, str) and i for i in ids)
    assert len(set(ids)) == 28
    assert set(table['value']['rows'][0]) == set(ids)


# F17: converter profiles

PROFILE = {'id': 'p1', 'title': 'NMR', 'description': '', 'identifiers': [], 'tables': [], 'data': {}}


def _converter_session(calls, status=200):
    def request(method):
        def send(url, **kwargs):
            calls.append((method, url))
            code = 200 if method == 'get' else status
            return _response(code, 'refused', method.upper(), 'https://eln.example.org' + url,
                             json={'profiles': [PROFILE]})
        return send
    return SimpleNamespace(**{m: request(m) for m in ('get', 'put', 'post', 'delete')})


@pytest.mark.parametrize('action', ['save', 'delete'])
def test_a_refused_profile_request_raises(action):
    from chemotion_api.converter import ProfileManager
    profile = ProfileManager(_converter_session([], status=422)).get_profile('p1')
    with pytest.raises(ChemotionRequestError, match='422'):
        getattr(profile, action)()


def test_deleting_a_profile_clears_the_cached_list():
    from chemotion_api.converter import ProfileManager
    calls = []
    pm = ProfileManager(_converter_session(calls))
    pm.get_profile('p1').delete()
    pm.get_profile('p1')
    assert [c for c in calls if c[0] == 'get'] == [('get', '/api/v1/converter/profiles')] * 2


def test_a_deleted_profile_is_created_again_when_saved():
    from chemotion_api.converter import ProfileManager
    calls = []
    profile = ProfileManager(_converter_session(calls)).get_profile('p1')
    profile.delete()
    profile.save()
    assert calls[-1] == ('post', '/api/v1/converter/profiles')


def test_creating_a_profile_clears_the_cached_list(tmp_path):
    import json
    from chemotion_api.converter import ProfileManager
    calls = []
    pm = ProfileManager(_converter_session(calls))
    f = tmp_path / 'p.json'
    f.write_text(json.dumps(PROFILE))
    pm.new_profile_from_file(str(f)).save()
    pm.profiles
    assert [c for c in calls if c[0] == 'get'] == [('get', '/api/v1/converter/profiles')] * 2


# F18: bare except clauses

def test_get_or_create_collection_does_not_swallow_an_interrupt():
    from chemotion_api.collection import AbstractCollection
    created = []

    def get_collection(*args):
        raise KeyboardInterrupt
    fake = SimpleNamespace(get_collection=get_collection, add_collection=created.append)
    with pytest.raises(KeyboardInterrupt):
        AbstractCollection.get_or_create_collection(fake, 'new')  # type: ignore[arg-type]
    assert created == []


def test_get_or_create_collection_does_not_create_on_an_unexpected_error():
    from chemotion_api.collection import AbstractCollection
    created = []

    def get_collection(*args):
        raise RuntimeError('bug')
    fake = SimpleNamespace(get_collection=get_collection, add_collection=created.append)
    with pytest.raises(RuntimeError):
        AbstractCollection.get_or_create_collection(fake, 'new')  # type: ignore[arg-type]
    assert created == []


class _Headers(dict):
    def get(self, key, default=None):
        raise KeyboardInterrupt


def _element_set(monkeypatch, headers):
    from chemotion_api.elements import ElementSet
    session = SimpleNamespace(get=lambda url, data=None, **kw: SimpleNamespace(
        status_code=200, headers=headers, json=lambda: {'samples': []}))
    monkeypatch.setattr('chemotion_api.elements.GenericSegments', lambda session: SimpleNamespace(all_classes=[]))
    return ElementSet(session, {'name': 'sample', 'is_generic': False, 'label': 'Sample'}, 7)


def test_loading_elements_does_not_swallow_an_interrupt(monkeypatch):
    es = _element_set(monkeypatch, _Headers())
    with pytest.raises(KeyboardInterrupt):
        es.load_elements()


def test_loading_elements_still_tolerates_bad_paging_headers(monkeypatch):
    """Guard."""
    es = _element_set(monkeypatch, {'X-Total-Pages': 'many', 'X-Total': None})
    es.load_elements()
    assert es.max_page == 1


class _InterruptOnRead(list):
    def __getitem__(self, idx):
        raise KeyboardInterrupt


class _InterruptOnWrite(list):
    def __setitem__(self, idx, value):
        raise KeyboardInterrupt


@pytest.mark.parametrize('target', [_InterruptOnRead, _InterruptOnWrite])
def test_merging_lists_does_not_swallow_an_interrupt(target):
    from chemotion_api.utils import merge_dicts
    merged = target([1])
    with pytest.raises(KeyboardInterrupt):
        merge_dicts(merged, [2])
    assert list.__len__(merged) == 1


def test_merging_lists_still_appends_and_overwrites():
    """Guard."""
    from chemotion_api.utils import merge_dicts
    assert merge_dicts({'a': [1, {'x': 1}]}, {'a': [5, {'y': 2}, 3]}) == {'a': [5, {'x': 1, 'y': 2}, 3]}
    assert merge_dicts([1], {'k': 2}) == [1, 2]
