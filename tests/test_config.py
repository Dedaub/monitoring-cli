import stat

import pytest
from dedaub_auth.config import (
    Config,
    ConfigError,
    NotLoggedInError,
    Profile,
    ProfileNotFoundError,
    persist_refresh_token,
)


@pytest.fixture
def config_path(tmp_path, monkeypatch):
    path = tmp_path / ".config" / "dedaub" / "monitoring.json"
    monkeypatch.setenv("DEDAUB_CONFIG", str(path))
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


def _tok_profile(tok: str | None) -> Profile:
    return Profile(
        base_url="https://api.dedaub.com",
        oidc_host="https://auth.dedaub.com",
        client_id="watchdog-client",
        refresh_token=tok,
    )


def test_dedaub_config_env_overrides_path(tmp_path, monkeypatch):
    target = tmp_path / "elsewhere" / "cfg.json"
    monkeypatch.setenv("DEDAUB_CONFIG", str(target))
    Config(default="prod", profiles={"prod": _tok_profile("tok")}).save()
    assert target.exists()
    assert Config.load().get_profile().refresh_token == "tok"
    # 0700 dir / 0600 file hold under the override too.
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700


def test_default_path_without_env(tmp_path, monkeypatch):
    monkeypatch.delenv("DEDAUB_CONFIG", raising=False)
    target = tmp_path / "default.json"
    monkeypatch.setattr("dedaub_auth.config.CONFIG_PATH", target)
    Config(default="prod", profiles={}).save()
    assert target.exists()


def test_load_raises_config_error_when_corrupt(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text("{not json")
    with pytest.raises(ConfigError):
        Config.load()


def test_persist_refresh_token_updates_only_matching(config_path):
    Config(
        default="prod",
        profiles={"prod": _tok_profile("old"), "staging": _tok_profile("s")},
    ).save()
    assert persist_refresh_token("prod", "old", "new") is True
    loaded = Config.load()
    assert loaded.profiles["prod"].refresh_token == "new"
    assert loaded.profiles["staging"].refresh_token == "s"
    # A stale rotation (file already holds a newer login) is not written.
    assert persist_refresh_token("prod", "old", "newer") is False
    assert Config.load().profiles["prod"].refresh_token == "new"


def test_persist_refresh_token_without_profile_is_noop(config_path):
    Config(default="staging", profiles={"staging": _tok_profile("s")}).save()
    assert persist_refresh_token("prod", "s", "y") is False
    assert Config.load().profiles["staging"].refresh_token == "s"


def test_persist_refresh_token_without_config_is_noop(config_path):
    assert persist_refresh_token("prod", "a", "b") is False
    assert not config_path.exists()
