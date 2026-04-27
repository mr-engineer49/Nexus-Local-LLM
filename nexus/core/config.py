import json, os, sys
from pathlib import Path
from typing import Dict, Any

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

APP_VERSION   = "2.0"
SETTINGS_FILE = Path.home() / ".nexus_settings.json"
PROJECTS_FILE = Path.home() / ".nexus_projects.json"
AGENTS_FILE   = Path.home() / ".nexus_agents.json"
SESSIONS_DIR  = Path.home() / ".nexus_sessions"

class AppSettings:
    _defaults: Dict[str, Any] = {
        # Ollama
        "ollama_host":    "http://localhost:11434",
        "ollama_threads": 4,
        "gpu_layers":     0,
        "default_model":  "",
        # GitHub / Git
        "github_token":   "",
        "clone_dir":      str(Path.home() / "Projects"),
        # Agent
        "agent_approve":       False,
        "agent_max_steps":     12,
        "agent_tool_approval": True,
        "agent_memory_type":   "none",      # none | buffer | summary
        # LLM Provider
        "agent_provider":      "ollama",    # ollama | openai | anthropic | openai_compatible
        "openai_api_key":      "",
        "anthropic_api_key":   "",
        "openai_base_url":     "https://api.openai.com/v1",
        "openai_model":        "gpt-4o-mini",
        "anthropic_model":     "claude-3-5-sonnet-20241022",
        # LangSmith
        "langsmith_api_key":   "",
        "langsmith_project":   "nexus-default",
        "langsmith_endpoint":  "https://api.smith.langchain.com",
        "langchain_tracing":   False,
        # App
        "autoscroll":     True,
        "timestamps":     True,
        "theme_accent":   "#6e56cf",
    }
    def __init__(self):
        self._data = dict(self._defaults)
        self.load()

    def load(self):
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE) as f:
                    self._data.update(json.load(f))
        except Exception: pass

    def save(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception: pass

    def get(self, key, default=None):
        return self._data.get(key, self._defaults.get(key, default))

    def set(self, key, value):
        self._data[key] = value
        self.save()

SETTINGS = AppSettings()
