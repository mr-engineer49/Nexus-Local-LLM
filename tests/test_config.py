import pytest
from pathlib import Path
from nexus.core.config import AppSettings

def test_settings_defaults():
    settings = AppSettings()
    assert settings.get("ollama_host") == "http://localhost:11434"
    assert settings.get("agent_max_steps") == 12

def test_settings_set_get():
    settings = AppSettings()
    settings.set("test_key", "test_value")
    assert settings.get("test_key") == "test_value"

def test_settings_save_load(tmp_path, monkeypatch):
    # Use a temporary file for settings
    test_file = tmp_path / "test_settings.json"
    monkeypatch.setattr("nexus.core.config.SETTINGS_FILE", test_file)
    
    settings = AppSettings()
    settings.set("my_val", 123)
    
    # Reload in a new instance
    new_settings = AppSettings()
    assert new_settings.get("my_val") == 123
