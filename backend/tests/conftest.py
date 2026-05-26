import pytest
from app.db import create_tables


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test module."""
    create_tables()
