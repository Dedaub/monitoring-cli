import stat

import pytest

from monitoring_cli.config import (
    Config,
    NotLoggedInError,
    Profile,
    ProfileNotFoundError,
)


@pytest.fixture
def config_path(tmp_path, monkeypatch):
    path = tmp_path / ".config" / "dedaub" / "monitoring.json"
    monkeypatch.setattr("monitoring_cli.config.CONFIG_PATH", path)
    return path


def test_profile_roundtrip():
    p = Profile(
        base_url="https://app.dedaub.com",
        oidc_host="https://auth.dedaub.com",
        client_id="watchdog-client",
        realm="dedaub",
        refresh_token="tok123",
    )
    assert p.base_url == "https://app.dedaub.com"
    assert p.refresh_token == "tok123"


def test_config_save_and_load(config_path):
    profile = Profile(
        base_url="https://staging.example.com",
        oidc_host="https://auth-staging.example.com",
        client_id="watchdog-client",
        realm="dedaub",
        refresh_token="tok456",
    )
    config = Config(default="staging", profiles={"staging": profile})
    config.save()

    assert config_path.exists()
    loaded = Config.load()
    assert loaded.default == "staging"
    assert loaded.profiles["staging"].base_url == "https://staging.example.com"
    assert loaded.profiles["staging"].refresh_token == "tok456"


def test_config_save_sets_chmod_600(config_path):
    profile = Profile(
        base_url="https://staging.example.com",
        oidc_host="https://auth-staging.example.com",
        client_id="watchdog-client",
        realm="dedaub",
    )
    Config(default="staging", profiles={"staging": profile}).save()
    mode = stat.S_IMODE(config_path.stat().st_mode)
    assert mode == 0o600


def test_load_raises_when_no_file(config_path):
    with pytest.raises(NotLoggedInError):
        Config.load()


def test_get_profile_returns_default(config_path):
    profile = Profile(
        base_url="https://app.dedaub.com",
        oidc_host="https://auth.dedaub.com",
        client_id="watchdog-client",
        realm="dedaub",
    )
    Config(default="prod", profiles={"prod": profile}).save()
    config = Config.load()
    p = config.get_profile(None)
    assert p.base_url == "https://app.dedaub.com"


def test_get_profile_raises_when_not_found(config_path):
    profile = Profile(
        base_url="https://app.dedaub.com",
        oidc_host="https://auth.dedaub.com",
        client_id="watchdog-client",
        realm="dedaub",
    )
    Config(default="prod", profiles={"prod": profile}).save()
    config = Config.load()
    with pytest.raises(ProfileNotFoundError):
        config.get_profile("nonexistent")


def test_upsert_profile(config_path):
    profile = Profile(
        base_url="https://app.dedaub.com",
        oidc_host="https://auth.dedaub.com",
        client_id="watchdog-client",
        realm="dedaub",
    )
    Config(default="prod", profiles={"prod": profile}).save()
    config = Config.load()

    new_profile = Profile(
        base_url="https://staging.example.com",
        oidc_host="https://auth-staging.example.com",
        client_id="watchdog-client",
        realm="dedaub",
        refresh_token="newtoken",
    )
    config.upsert_profile("staging", new_profile)
    config.save()

    reloaded = Config.load()
    assert "staging" in reloaded.profiles
    assert reloaded.profiles["staging"].refresh_token == "newtoken"


def test_remove_profile(config_path):
    prod = Profile(
        base_url="https://app.dedaub.com",
        oidc_host="https://auth.dedaub.com",
        client_id="watchdog-client",
        realm="dedaub",
    )
    staging = Profile(
        base_url="https://staging.example.com",
        oidc_host="https://auth-staging.example.com",
        client_id="watchdog-client",
        realm="dedaub",
    )
    Config(default="prod", profiles={"prod": prod, "staging": staging}).save()
    config = Config.load()
    config.remove_profile("staging")
    config.save()

    reloaded = Config.load()
    assert "staging" not in reloaded.profiles


def test_remove_profile_raises_when_not_found(config_path):
    prod = Profile(
        base_url="https://app.dedaub.com",
        oidc_host="https://auth.dedaub.com",
        client_id="watchdog-client",
        realm="dedaub",
    )
    Config(default="prod", profiles={"prod": prod}).save()
    config = Config.load()
    with pytest.raises(ProfileNotFoundError):
        config.remove_profile("nonexistent")
