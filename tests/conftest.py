import pytest
from monitoring_cli.config import Profile


@pytest.fixture
def profile() -> Profile:
    return Profile(
        base_url="https://api.dedaub.com",
        oidc_host="https://auth.dedaub.com",
        client_id="watchdog-client",
        realm="dedaub",
        refresh_token="test-refresh-token",
    )
