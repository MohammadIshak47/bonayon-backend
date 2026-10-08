import pytest
from sqlalchemy.engine import make_url

from app.core.config import normalize_database_url as norm


def test_raw_password_with_at_sign_is_encoded_and_parses_correctly():
    url = norm("postgresql+psycopg://postgres:My@Pass1@localhost:5432/bonayon")
    u = make_url(url)
    assert (u.username, u.password, u.host, u.port, u.database) == ("postgres", "My@Pass1", "localhost", 5432, "bonayon")
    assert url == "postgresql+psycopg://postgres:My%40Pass1@localhost:5432/bonayon"


def test_already_encoded_password_is_not_double_encoded():
    assert norm("postgresql+psycopg://u:My%40Pass1@localhost/db") == "postgresql+psycopg://u:My%40Pass1@localhost/db"


@pytest.mark.parametrize("pw", ["p:w", "p/w", "p#w", "p?w", "p w", "a@b@c", "100%sure"])
def test_other_special_characters_round_trip(pw):
    u = make_url(norm(f"postgresql+psycopg://user:{pw}@db.example.com:5432/app"))
    assert (u.password, u.host, u.database) == (pw, "db.example.com", "app")


def test_normal_and_neon_style_urls_are_unchanged_except_driver():
    assert norm("postgres://u:pw@ep-x.neon.tech/db?sslmode=require") == "postgresql+psycopg://u:pw@ep-x.neon.tech/db?sslmode=require"
    assert norm("postgresql+psycopg://u@localhost/db") == "postgresql+psycopg://u@localhost/db"   # no password
    assert norm("postgresql+psycopg://postgres:@/mydb?host=/tmp/sock") == "postgresql+psycopg://postgres:@/mydb?host=/tmp/sock"  # unix socket
