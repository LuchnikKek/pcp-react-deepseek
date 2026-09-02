"""Загрузка переменных окружения из .env (DEEPSEEK_API_KEY, DEEPSEEK_API_BASE и т.п.) без внешних зависимостей."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: str | Path = ".env", override: bool = False) -> dict[str, str]:
    """Читает KEY=VALUE построчно (комментарии, пустые строки и кавычки допускаются) и кладёт в os.environ."""
    file = Path(path)
    if not file.exists():
        return {}
    loaded: dict[str, str] = {}
    for raw in file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip("'\"")
        if override or key not in os.environ:
            os.environ[key] = value
        loaded[key] = value
    return loaded
