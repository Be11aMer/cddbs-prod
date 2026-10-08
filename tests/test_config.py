import pytest

from src.cddbs.config import normalize_db_url


@pytest.mark.parametrize(
    "url, expected",
    [
        ("postgres://u:p@h:5432/db", "postgresql+psycopg2://u:p@h:5432/db"),
        ("postgresql://u:p@h/db?sslmode=require", "postgresql+psycopg2://u:p@h/db?sslmode=require"),
        ("postgresql+psycopg2://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
        ("sqlite:///x.db", "sqlite:///x.db"),
    ],
)
def test_normalize_db_url(url, expected):
    assert normalize_db_url(url) == expected


def test_normalized_url_loads_installed_driver():
    from sqlalchemy import create_engine

    engine = create_engine(normalize_db_url("postgresql://u:p@localhost/db"))
    assert engine.dialect.driver == "psycopg2"
