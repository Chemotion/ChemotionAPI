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
