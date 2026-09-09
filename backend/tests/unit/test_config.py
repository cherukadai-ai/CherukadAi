from app.core.config import Settings, get_settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test Platform")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://a.com, http://b.com")
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.app_name == "Test Platform"
    assert settings.allowed_origins == ["http://a.com", "http://b.com"]
    get_settings.cache_clear()


def test_settings_trim_whitespace_from_env_values(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", " test ")
    monkeypatch.setenv("DEBUG", " true ")
    monkeypatch.setenv("SECRET_KEY", "  secret-with-space  ")
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.environment == "test"
    assert settings.debug is True
    assert settings.secret_key == "secret-with-space"
    get_settings.cache_clear()


def test_is_production_flag():
    settings = Settings(environment="production")
    assert settings.is_production is True

    settings = Settings(environment="local")
    assert settings.is_production is False
