"""
Настройки приложения — то, что не секрет и не относится к стойкам.

Лежат открытым JSON рядом с хранилищем: путь к клиенту fwknop и на сколько
часов запоминать мастер-пароль. Секретов тут нет, шифровать нечего.
"""

from __future__ import annotations

import json

from .paths import settings_file

DEFAULTS: dict = {
    "fwknop_path": "",    # пусто = искать автоматически
    "remember_hours": 0,  # 0 = спрашивать пароль при каждом запуске
}


def load() -> dict:
    """Прочитать настройки, дополнив недостающие ключи значениями по умолчанию."""
    settings = dict(DEFAULTS)
    path = settings_file()
    if path.is_file():
        try:
            settings.update(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass  # битый файл настроек не повод не запуститься
    return settings


def save(settings: dict) -> None:
    """Записать настройки (атомарно — через временный файл)."""
    path = settings_file()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
