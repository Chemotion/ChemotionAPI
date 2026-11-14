"""Collection export waits for its own notification, and says so when the wording does not match."""
from types import SimpleNamespace

import pytest

from chemotion_api.utils import collection_zip

SUBJECT = 'Collection Import and Export'


class _Server:
    """Answers /messages/list from a script: the n-th listing returns ``script[n]`` (then the last)."""

    def __init__(self, script):
        self.script, self.listings, self.downloaded = script, 0, []

    def get(self, url, params=None, stream=False, **kw):
        if url == '/api/v1/messages/list':
            batch = self.script[min(self.listings, len(self.script) - 1)]
            self.listings += 1
            return SimpleNamespace(status_code=200, json=lambda: {'messages': batch})
        self.downloaded.append(url)
        return SimpleNamespace(status_code=200, iter_content=lambda n: [b'PK'])

    def post(self, url, **kw):
        return SimpleNamespace(status_code=204)


def _msg(i, text, url='http://0.0.0.0:3000/zip/abc.zip'):
    return {'id': i, 'subject': SUBJECT, 'content': {'data': text, 'url': url}}


def test_the_export_of_another_collection_is_not_taken(tmp_path):
    other = _msg(2, 'Collection Export: ["NMR 2024"] processed successfully. x', 'http://h/zip/other.zip')
    ours = _msg(3, 'Collection Export: ["NMR"] processed successfully. x', 'http://h/zip/ours.zip')
    server = _Server([[], [other], [other, ours]])
    collection_zip.export_collection_zip(server, 1, 'NMR', tmp_path / 'a.zip', timeout=5, poll_interval=0)
    assert server.downloaded == ['/zip/ours.zip']


def test_a_timeout_quotes_notifications_that_did_not_match(tmp_path):
    reworded = _msg(2, 'Export of collection NMR finished.')
    server = _Server([[], [reworded]])
    with pytest.raises(TimeoutError, match="wording has changed") as exc:
        collection_zip.export_collection_zip(server, 1, 'NMR', tmp_path / 'a.zip', timeout=0, poll_interval=0)
    assert 'Export of collection NMR finished.' in str(exc.value)


def test_a_failed_export_raises(tmp_path):
    failed = _msg(2, 'Collection Export: There was an issue while processing ["NMR"].') | {
        'subject': 'Collection Import and Export Failure'}
    server = _Server([[], [failed]])
    with pytest.raises(ConnectionError, match='could not export'):
        collection_zip.export_collection_zip(server, 1, 'NMR', tmp_path / 'a.zip', timeout=5, poll_interval=0)


def test_a_label_that_reads_like_a_failure_is_not_one(tmp_path):
    """Failure is decided by the channel, not by words in the text."""
    ok = _msg(3, 'Collection Export: ["Data issue while processing"] processed successfully. x')
    server = _Server([[], [ok]])
    collection_zip.export_collection_zip(server, 1, 'Data issue while processing', tmp_path / 'a.zip',
                                         timeout=5, poll_interval=0)
    assert server.downloaded == ['/zip/abc.zip']
