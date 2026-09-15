"""
Зашифрованное хранилище стоек.

Что лежит внутри: ровно те же стойки, что в .fwknoprc, — имя и набор
переменных fwknop. Разница только в том, что файл зашифрован мастер-паролем,
а не лежит открытым текстом, как штатный ~/.fwknoprc.

Конверт файла — обычный JSON, чтобы формат можно было разобрать чем угодно,
а не только этим приложением:

    {
      "format": "fwkog-vault", "version": 1,
      "kdf": {"name": "scrypt", "n": 32768, "r": 8, "p": 1, "salt": "<base64>"},
      "cipher": "AES-256-GCM", "nonce": "<base64>", "data": "<base64>"
    }

Криптография: scrypt растягивает пароль в 32-байтный ключ (KDF — функция,
которая делает перебор пароля дорогим), AES-256-GCM шифрует и одновременно
подписывает — подменить содержимое незаметно нельзя.

Тот же формат используется для файла экспорта: перенос стоек на другую машину
идёт зашифрованным файлом со своим паролем, а не открытым текстом.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from .paths import vault_file

FORMAT = "fwkog-vault"
VERSION = 1

# Параметры scrypt. n=32768 (2^15) при r=8 — это ~32 МБ памяти на проверку
# пароля: заметно для перебора, незаметно для человека при запуске.
SCRYPT_N = 32768
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LEN = 32      # AES-256
SALT_LEN = 16
NONCE_LEN = 12    # штатная длина для GCM


class VaultError(Exception):
    """Общая ошибка хранилища."""


class WrongPassword(VaultError):
    """Пароль не подошёл (или файл повреждён — GCM не отличает одно от другого)."""


def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    """Пароль -> ключ шифрования. Параметры берём из файла: если в будущем
    поднимем стойкость, старые файлы всё равно откроются своими параметрами."""
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    return Scrypt(salt=salt, length=KEY_LEN, n=n, r=r, p=p).derive(password.encode("utf-8"))


def encrypt(payload: dict, password: str) -> str:
    """Зашифровать содержимое хранилища в текст конверта."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = _derive(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    plain = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    data = AESGCM(key).encrypt(nonce, plain, None)
    envelope = {
        "format": FORMAT,
        "version": VERSION,
        "kdf": {"name": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P, "salt": _b64e(salt)},
        "cipher": "AES-256-GCM",
        "nonce": _b64e(nonce),
        "data": _b64e(data),
    }
    return json.dumps(envelope, ensure_ascii=False, indent=2)


def decrypt(text: str, password: str) -> dict:
    """Расшифровать конверт. Неверный пароль -> WrongPassword."""
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    try:
        envelope = json.loads(text)
        kdf = envelope["kdf"]
        key = _derive(password, _b64d(kdf["salt"]), int(kdf["n"]), int(kdf["r"]), int(kdf["p"]))
        plain = AESGCM(key).decrypt(_b64d(envelope["nonce"]), _b64d(envelope["data"]), None)
    except InvalidTag as e:
        raise WrongPassword("неверный пароль или файл повреждён") from e
    except (KeyError, ValueError, TypeError) as e:
        raise VaultError(f"не похоже на файл FWKOG: {e}") from e
    return json.loads(plain.decode("utf-8"))


class Vault:
    """Хранилище стоек: открыть мастер-паролем, поменять, сохранить.

    Пока хранилище не открыто (`unlocked` == False), стойки недоступны —
    расшифрованные данные живут только в памяти открытого приложения.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or vault_file()
        self._password: str | None = None
        self._stanzas: list[dict] = []

    # --- состояние ---

    @property
    def exists(self) -> bool:
        return self.path.is_file()

    @property
    def unlocked(self) -> bool:
        return self._password is not None

    def lock(self) -> None:
        """Забыть пароль и содержимое (выход «на замок» без закрытия приложения)."""
        self._password = None
        self._stanzas = []

    # --- открытие и создание ---

    def create(self, password: str) -> None:
        """Первый запуск: завести пустое хранилище под новым мастер-паролем."""
        if self.exists:
            raise VaultError("хранилище уже существует")
        self._password = password
        self._stanzas = []
        self.save()

    def unlock(self, password: str) -> None:
        """Открыть существующее хранилище."""
        payload = decrypt(self.path.read_text(encoding="utf-8"), password)
        self._password = password
        self._stanzas = list(payload.get("stanzas", []))

    def change_password(self, old: str, new: str) -> None:
        """Сменить мастер-пароль (старый проверяем, чтобы не затереть по ошибке)."""
        self.unlock(old)
        self._password = new
        self.save()

    # --- стойки ---

    def list_stanzas(self) -> list[dict]:
        """Копия списка стоек: [{"name": ..., "vars": {...}}, ...]."""
        self._require_unlocked()
        return [{"name": s["name"], "vars": dict(s.get("vars", {}))} for s in self._stanzas]

    def set_stanzas(self, stanzas: list[dict]) -> None:
        """Заменить весь список целиком и сохранить."""
        self._require_unlocked()
        self._stanzas = [{"name": s["name"], "vars": dict(s.get("vars", {}))} for s in stanzas]
        self.save()

    def save(self) -> None:
        """Записать хранилище на диск. Запись атомарная — через временный файл."""
        self._require_unlocked()
        payload = {"format": FORMAT, "version": VERSION, "stanzas": self._stanzas}
        text = encrypt(payload, self._password or "")
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        _restrict(tmp)
        tmp.replace(self.path)

    # --- перенос ---

    def export_to(self, target: Path, password: str) -> None:
        """Выгрузить стойки в отдельный файл под своим паролем."""
        self._require_unlocked()
        payload = {"format": FORMAT, "version": VERSION, "stanzas": self._stanzas}
        target.write_text(encrypt(payload, password), encoding="utf-8")
        _restrict(target)

    @staticmethod
    def read_export(source: Path, password: str) -> list[dict]:
        """Прочитать файл экспорта и вернуть стойки (в хранилище пока не кладём)."""
        payload = decrypt(source.read_text(encoding="utf-8"), password)
        return list(payload.get("stanzas", []))

    def _require_unlocked(self) -> None:
        if not self.unlocked:
            raise VaultError("хранилище закрыто")


def _restrict(path: Path) -> None:
    """Права «только владелец» — на Unix через chmod. На Windows файл и так
    лежит в профиле пользователя, куда чужие учётки не ходят."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass  # не вышло — не повод ронять сохранение
