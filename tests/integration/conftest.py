import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.infrastructure.persistence.unit_of_work import UnitOfWork, AsyncUnitOfWork

@pytest.fixture(scope="function")
def test_session():
    """Create a new database session for a test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def uow(test_session):
    """Create a UnitOfWork instance for a test."""
    return UnitOfWork(session_factory=lambda: test_session)

@pytest.fixture(scope="function")
def async_uow(test_session):
    """Create an AsyncUnitOfWork instance for a test."""
    return AsyncUnitOfWork(session_factory=lambda: test_session)
