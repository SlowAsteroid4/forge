"""Fixtures compartidas para tests."""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from forge.db.base import Base

_TEST_ENV_DEFAULTS = {
    "JIRA_INSTANCE_URL": "https://test.atlassian.net",
    "JIRA_USER_EMAIL": "test@test.com",
    "JIRA_API_TOKEN": "test-api-token",
    "ENCRYPTION_KEY": "test-encryption-key-for-unit-tests-only",
}


@pytest.fixture(autouse=True, scope="session")
def configure_test_settings() -> None:
    """Set dummy env vars so Settings() doesn't require a .env file in unit tests."""
    for key, val in _TEST_ENV_DEFAULTS.items():
        os.environ.setdefault(key, val)
    # Clear lru_cache so Settings re-reads env with the new values.
    from forge.core.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
def test_db_engine():
    """Engine de SQLite en memoria para tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session(test_db_engine):
    """Sesión de DB para tests."""
    TestSessionLocal = sessionmaker(bind=test_db_engine)
    session = TestSessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_player(test_session: Session):
    """Player de ejemplo."""
    from forge.db.models.player import Player

    player = Player(
        jira_account_id="test123",
        display_name="Test Dev",
        email="test@yapsi.com",
        area="BE",
        employment_type="internal",
        is_lead=False,
        is_active=True,
    )
    test_session.add(player)
    test_session.commit()
    return player
