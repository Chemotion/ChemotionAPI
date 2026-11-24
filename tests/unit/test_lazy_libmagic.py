"""Issue #24: ``import chemotion_api`` must not need python-magic / the native libmagic.

``magic`` is only used to detect the MIME type of a file being uploaded, so it is imported
lazily there, with a fallback to the standard library's :mod:`mimetypes`.
"""
import importlib
import sys


def test_package_imports_without_magic(monkeypatch):
    """With ``magic`` unavailable (``sys.modules['magic'] = None`` makes ``import magic`` raise
    ImportError, as on Windows without libmagic), the package must still import."""
    for name in [m for m in sys.modules if m == 'chemotion_api' or m.startswith('chemotion_api.')]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, 'magic', None)
    try:
        importlib.import_module('chemotion_api')
        importlib.import_module('chemotion_api.elements.attachments')
        importlib.import_module('chemotion_api.inbox')
    finally:
        # drop the modules imported above; monkeypatch then puts the original ones back
        for name in [m for m in sys.modules if m == 'chemotion_api' or m.startswith('chemotion_api.')]:
            del sys.modules[name]


def test_guess_mime_type_falls_back_to_mimetypes_without_magic(monkeypatch, tmp_path):
    from chemotion_api.utils import guess_mime_type

    monkeypatch.setitem(sys.modules, 'magic', None)
    txt = tmp_path / 'notes.txt'
    txt.write_bytes(b'hello')
    unknown = tmp_path / 'data.unknownext'
    unknown.write_bytes(b'\x00\x01')
    assert guess_mime_type(str(txt)) == 'text/plain'
    assert guess_mime_type(str(unknown)) == 'application/octet-stream'
