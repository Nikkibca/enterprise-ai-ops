
import pytest
from pydantic import ValidationError

from app.auth_settings import AuthSettings


def test_jwt_secret_of_at_least_32_characters_is_accepted():
    settings = AuthSettings(jwt_secret_key="a" * 32)

    assert settings.jwt_secret_key == "a" * 32


@pytest.mark.parametrize(
    "secret",
    [
        "",
        "short",
        "a" * 31,
    ],
)
def test_jwt_secret_shorter_than_32_characters_is_rejected(secret):
    with pytest.raises(ValidationError):
        AuthSettings(jwt_secret_key=secret)