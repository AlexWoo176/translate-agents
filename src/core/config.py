import os
import json
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent

def load_env_file():
    """
    Manually load .env file into os.environ if it exists.
    """
    env_file = WORKSPACE_ROOT / ".env"
    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key, val = parts[0].strip(), parts[1].strip()
                        if key not in os.environ:
                            os.environ[key] = val
        except Exception:
            pass

# Load environment variables from .env
load_env_file()

def load_config():
    """
    Load configuration from default.json, workspace.json (if exists),
    and check for standard environment variable overrides.
    """
    config = {
        "BOOKS_ROOT": "../books",
        "WEB_OUTPUT_ROOT": "../web-site"
    }

    # 1. Load default.json
    default_json = WORKSPACE_ROOT / "config" / "default.json"
    if default_json.is_file():
        try:
            with open(default_json, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception:
            pass

    # 2. Load workspace.json (if it exists)
    workspace_json = WORKSPACE_ROOT / "config" / "workspace.json"
    if workspace_json.is_file():
        try:
            with open(workspace_json, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception:
            pass

    # 3. Apply uppercase environment overrides initially
    for key in list(config.keys()):
        env_val = os.getenv(key)
        if env_val is not None:
            config[key] = env_val

    return config

_config = load_config()

def get_config(key, default=None):
    """
    Get config value with dynamic environment lookup as primary priority.
    """
    key_upper = key.upper()
    env_val = os.getenv(key_upper) or os.getenv(key.lower())
    if env_val is not None:
        return env_val
    return _config.get(key_upper, _config.get(key, default))
