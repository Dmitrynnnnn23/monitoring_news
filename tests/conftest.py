import pytest

from app import config


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Изолированная БД для каждого теста."""
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    from app import db

    db.init_db()
    return db
