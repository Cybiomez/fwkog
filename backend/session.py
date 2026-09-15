"""
Запоминание мастер-пароля между запусками.

По умолчанию пароль спрашивается при каждом запуске. Если пользователь выбрал
«запомнить», ключ кладётся в файл `session.bin` в каталоге данных — но не
открытым текстом:

  - Windows: DPAPI (встроенное шифрование Windows, привязка к учётной записи).
    Файл бесполезен на другой машине и под другим пользователем.
  - Linux/macOS: запоминания нет — пароль живёт только в памяти процесса.
    Ставить ради этого лишнюю зависимость незачем, а класть пароль открытым
    текстом нельзя.

Это кэш, а не хранилище: потеря файла ничего не ломает — просто спросим пароль.
Перенос данных между машинами идёт экспортом, а не копированием этого файла.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from .paths import data_dir

CACHE_NAME = "session.bin"


def available() -> bool:
    """Поддерживается ли запоминание на этой ОС."""
    return sys.platform == "win32"


def _cache_file() -> Path:
    return data_dir() / CACHE_NAME


def remember(password: str, hours: int) -> bool:
    """Запомнить пароль на hours часов. Возвращает, получилось ли."""
    if not available() or hours <= 0:
        return False
    payload = json.dumps({"password": password, "until": time.time() + hours * 3600})
    try:
        blob = _protect(payload.encode("utf-8"))
    except OSError:
        return False
    _cache_file().write_bytes(blob)
    return True


def recall() -> str | None:
    """Вспомнить пароль, если он запомнен и срок не вышел."""
    path = _cache_file()
    if not available() or not path.is_file():
        return None
    try:
        data = json.loads(_unprotect(path.read_bytes()).decode("utf-8"))
    except (OSError, ValueError):
        forget()
        return None
    if time.time() > float(data.get("until", 0)):
        forget()
        return None
    return str(data.get("password") or "") or None


def forget() -> None:
    """Забыть запомненный пароль (смена пароля, выход «на замок», отказ)."""
    _cache_file().unlink(missing_ok=True)


# --- DPAPI: шифрование средствами Windows, без внешних зависимостей ---

def _protect(raw: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    src = Blob(len(raw), ctypes.cast(ctypes.create_string_buffer(raw), ctypes.POINTER(ctypes.c_char)))
    out = Blob()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(src), None, None, None, None, 0, ctypes.byref(out)
    )
    if not ok:
        raise OSError("CryptProtectData не сработала")
    return _take(out)


def _unprotect(blob: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    src = Blob(len(blob), ctypes.cast(ctypes.create_string_buffer(blob), ctypes.POINTER(ctypes.c_char)))
    out = Blob()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(src), None, None, None, None, 0, ctypes.byref(out)
    )
    if not ok:
        raise OSError("CryptUnprotectData не сработала")
    return _take(out)


def _take(blob) -> bytes:
    """Забрать данные из структуры Windows и освободить её память."""
    import ctypes

    data = ctypes.string_at(blob.pbData, blob.cbData)
    ctypes.windll.kernel32.LocalFree(blob.pbData)
    return data
