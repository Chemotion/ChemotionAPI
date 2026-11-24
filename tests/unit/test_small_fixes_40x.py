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
