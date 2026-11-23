"""Waiting for the server's background-job notifications (``/api/v1/messages/list``).

Several ELN actions — collection export and import, sample import, reports — run as background
jobs. The API answers right away without saying which job it started, and reports the outcome later
as a notification message to the user. These helpers find that message: remember the notifications
that exist before the request, then poll for a new one on the job's channel.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import urlparse

from chemotion_api.connection import Connection, request_error


def notifications(session: Connection, subjects: Iterable[str]) -> list[dict[str, Any]]:
    """Your notifications on the given channel subjects, acknowledged ones included, oldest first."""
    wanted = set(subjects)
    res = session.get('/api/v1/messages/list', params={'is_ack': 9})
    if res.status_code != 200:
        raise request_error(res, 'loading your notifications')
    return [m for m in res.json().get('messages') or [] if subject_of(m) in wanted]


def subject_of(message: dict[str, Any]) -> str | None:
    return (message.get('content') or {}).get('channel_subject') or message.get('subject')


def notification_ids(session: Connection, subjects: Iterable[str]) -> set[int]:
    """The ids of the notifications that exist now, to pass to :func:`wait_for_notification`."""
    return {m['id'] for m in notifications(session, subjects)}


def wait_for_notification(session: Connection, subjects: Iterable[str], seen: set[int], what: str,
                          match: Callable[[dict[str, Any]], bool] = lambda m: True,
                          timeout: float = 300, poll_interval: float = 2) -> dict[str, Any]:
    """Poll until a notification on ``subjects`` that is not in ``seen`` and passes ``match`` arrives.

    :param what: the job, for the timeout message (e.g. ``'The export of "Project A"'``).
    :raises TimeoutError: when nothing arrives within ``timeout`` seconds (the job may still run).
        It quotes any new notification on the channel that did not match, because a change in the
        server's wording looks exactly like a job that never finished.
    """
    subjects = tuple(subjects)
    deadline = time.monotonic() + timeout
    unmatched: dict[int, str] = {}
    while True:
        for message in notifications(session, subjects):
            if message['id'] in seen:
                continue
            if match(message):
                return message
            unmatched[message['id']] = message_text(message)
        if time.monotonic() >= deadline:
            hint = ''
            if unmatched:
                quoted = '; '.join(repr(t) for t in list(unmatched.values())[:3])
                hint = (f' {len(unmatched)} other notification(s) arrived on this channel, none '
                        f'about this job: {quoted}. If one of them is, the server\'s wording has '
                        'changed; please open an issue.')
            raise TimeoutError(f'{what} did not report back within {timeout} s; '
                               f'it may still be running on the server.{hint}')
        time.sleep(poll_interval)


def message_text(message: dict[str, Any]) -> str:
    """The human-readable text of a notification."""
    content = message.get('content') or {}
    return str(content.get('data') or '') if isinstance(content, dict) else str(content)


def server_path(url: str) -> str:
    """The path (and query) of a link in a notification.

    The server builds links from its configured root URL, which is often not the address the client
    reaches it by (``http://0.0.0.0:3000/zip/…`` in containers), so only the path is used.
    """
    parsed = urlparse(url)
    return parsed.path + (f'?{parsed.query}' if parsed.query else '')
