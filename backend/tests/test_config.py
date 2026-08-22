from app.config import normalize_database_url


def test_normalize_database_url_keeps_psycopg_url() -> None:
    url = "postgresql+psycopg://user:password@host:5432/db"

    assert normalize_database_url(url) == url


def test_normalize_database_url_converts_postgresql_url() -> None:
    url = "postgresql://user:password@host:5432/db"

    assert (
        normalize_database_url(url)
        == "postgresql+psycopg://user:password@host:5432/db"
    )


def test_normalize_database_url_converts_postgres_url() -> None:
    url = "postgres://user:password@host:5432/db"

    assert (
        normalize_database_url(url)
        == "postgresql+psycopg://user:password@host:5432/db"
    )
