"""Tests for agent_server.utils — identity and session helpers."""
from unittest.mock import MagicMock

from agent_server.utils import get_user_email, get_session_id


def test_get_user_email_reads_forwarded_header():
    request = MagicMock()
    request.headers = {"X-Forwarded-Email": "tech@flightsafety.com"}
    assert get_user_email(request) == "tech@flightsafety.com"


def test_get_user_email_returns_none_when_missing():
    request = MagicMock()
    request.headers = {}
    assert get_user_email(request) is None


def test_get_session_id_reads_custom_inputs():
    req = MagicMock()
    req.custom_inputs = {"thread_id": "abc-123"}
    assert get_session_id(req) == "abc-123"


def test_get_session_id_returns_none_when_missing():
    req = MagicMock()
    req.custom_inputs = {}
    assert get_session_id(req) is None


def test_get_session_id_handles_none_custom_inputs():
    req = MagicMock()
    req.custom_inputs = None
    assert get_session_id(req) is None
