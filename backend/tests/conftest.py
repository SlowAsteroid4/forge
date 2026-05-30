"""Fixtures compartidas para tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from forge.db.base import Base


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
