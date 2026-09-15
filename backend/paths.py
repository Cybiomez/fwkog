"""
Где приложение хранит свои данные.

Правило из ТЗ: приложение портативное, данные — нет. Exe можно носить с собой,
а конфиги остаются на машине, в пользовательском каталоге:

    Windows:      %LOCALAPPDATA%\\FWKOG\\
    Linux/macOS:  ~/.local/share/fwkog/  (или $XDG_DATA_HOME/fwkog)

LOCALAPPDATA (а не APPDATA) — потому что в домене APPDATA «роумится» между
машинами, а секретам ездить по сети незачем.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "FWKOG"


def data_dir() -> Path:
    """Каталог данных под текущую ОС. Создаётся, если его ещё нет."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        path = base / APP_DIR_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        path = base / APP_DIR_NAME.lower()
    path.mkdir(parents=True, exist_ok=True)
    return path


def vault_file() -> Path:
    """Зашифрованный файл со стойками."""
    return data_dir() / "configs.enc"


def settings_file() -> Path:
    """Настройки приложения — не секретны, лежат открытым JSON рядом."""
    return data_dir() / "settings.json"


def user_fwknoprc() -> Path:
    """Штатный ~/.fwknoprc — тот же путь, что ищет сам клиент fwknop
    (на Windows это %USERPROFILE%\\.fwknoprc). Нужен для импорта."""
    if sys.platform == "win32":
        home = Path(os.environ.get("USERPROFILE", Path.home()))
    else:
        home = Path.home()
    return home / ".fwknoprc"
