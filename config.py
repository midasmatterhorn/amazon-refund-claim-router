"""Environment/config loading. Secrets never live in code or git.

The API key and model id are read from environment variables; a local .env file
(git-ignored) is supported so the key never passes through chat or commits.
"""
import os
from pathlib import Path
from typing import Optional


def load_env(path: Optional[Path] = None) -> None:
    """Set variables from a .env file without overriding the real environment."""
    env_path = path or Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing environment variable {name!r}. "
            "Copy .env.example to .env, fill it in, and never commit .env."
        )
    return value
