"""Tests for ExpirableTokenDict in backend/session.py."""
from datetime import datetime, timedelta

import pytest

from backend.session import ExpirableTokenDict


@pytest.fixture
def store():
    """A fresh store with a 1-hour TTL and effectively-never sweep for each test."""
    return ExpirableTokenDict(ttl=timedelta(hours=1), sweep_interval=timedelta(hours=99))


def test_create_returns_string(store):
    """create() must return a non-empty string."""
    token = store.create()
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_returns_unique_tokens(store):
    """Each call to create() must return a different token."""
    tokens = {store.create() for _ in range(10)}
    assert len(tokens) == 10


def test_validate_fresh_token(store):
    """A freshly created token must validate successfully."""
    token = store.create()
    assert store.validate_and_refresh(token) is True


def test_validate_unknown_token(store):
    """A token that was never created must not validate."""
    assert store.validate_and_refresh("not-a-real-token") is False


def test_validate_expired_token(store):
    """A token whose expiry is in the past must not validate."""
    token = store.create()
    # Manually backdate the expiry to simulate elapsed time.
    store._tokens[token] = datetime.now() - timedelta(seconds=1)
    assert store.validate_and_refresh(token) is False


def test_validate_refreshes_expiry(store):
    """After a successful validate_and_refresh, the expiry is extended by the full TTL."""
    token = store.create()
    # Set expiry to 10 seconds from now — well below the 1-hour TTL.
    store._tokens[token] = datetime.now() + timedelta(seconds=10)
    store.validate_and_refresh(token)
    # After refresh the expiry must be ~1 hour from now (at least 59 minutes).
    assert store._tokens[token] > datetime.now() + timedelta(minutes=59)


def test_revoke_invalidates_token(store):
    """revoke() must make the token fail future validation."""
    token = store.create()
    store.revoke(token)
    assert store.validate_and_refresh(token) is False


def test_revoke_nonexistent_is_safe(store):
    """revoke() must not raise for a token that does not exist."""
    store.revoke("does-not-exist")  # Must not raise


def test_clear_removes_all_tokens(store):
    """clear() must empty the internal token dict."""
    store.create()
    store.create()
    store.clear()
    assert store._tokens == {}


def test_sweep_removes_expired(store):
    """_sweep() must delete entries whose expiry is in the past."""
    token = store.create()
    store._tokens[token] = datetime.now() - timedelta(seconds=1)
    store._sweep()
    assert token not in store._tokens


def test_sweep_keeps_valid(store):
    """_sweep() must not delete entries that are still live."""
    token = store.create()
    store._sweep()
    assert token in store._tokens
