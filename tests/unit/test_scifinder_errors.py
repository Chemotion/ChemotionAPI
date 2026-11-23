"""SciFinder-n search errors: only a missing token is a PermissionError (401.1)."""
from types import SimpleNamespace

import pytest

from chemotion_api import scifinder


@pytest.mark.parametrize('message, error', [
    ('SciFinder-n token missing or expired. Go to Account & Profile and get a new token.', PermissionError),
    ('Net::ReadTimeout. Go to Account & Profile and try to get the token again.', ConnectionError),
])
def test_only_a_missing_token_is_a_permission_error(message, error):
    session = SimpleNamespace(post=lambda url, **kw: SimpleNamespace(
        status_code=200, json=lambda: {'errors': [message]}))
    with pytest.raises(error):
        scifinder.search(session, 'molfile')
