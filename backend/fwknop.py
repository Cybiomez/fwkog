"""
Запуск клиента fwknop.

Здесь FWKOG заканчивается и начинается базовый fwknop: своей криптографии и
своего протокола у приложения нет, оно только собирает стойку и зовёт клиент.

Как передаём параметры. Ключи в командной строке светились бы в списке
процессов, поэтому стойка пишется во временный rc-файл, а клиент вызывается
ровно так, как это задумано в самом fwknop:

    fwknop --rc-file <временный файл> -n fwkog --no-save-args

Временный файл лежит в каталоге данных (не в общем /tmp), создаётся с правами
«только владелец» и удаляется сразу после вызова.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import rcfile
from .paths import data_dir

# Имя стойки во временном файле. Своё и постоянное: имя стойки пользователя
# может содержать пробелы и скобки, а тут нужен предсказуемый идентификатор.
TEMP_STANZA = "fwkog"

# Сколько ждём клиент. Запас на случай ALLOW_IP=resolve — там клиент ходит
# в интернет узнавать свой внешний адрес.
TIMEOUT_SEC = 25

EXE_NAME = "fwknop.exe" if sys.platform == "win32" else "fwknop"


class FwknopNotFound(Exception):
    """Клиент fwknop не найден — нечего запускать."""


def app_dir() -> Path:
    """Каталог, из которого запущено приложение (рядом с exe в портативной сборке)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def candidates() -> list[Path]:
    """Места, где ищем клиент, в порядке предпочтения."""
    found: list[Path] = []

    # 1. Рядом с приложением — портативный комплект.
    base = app_dir()
    found += [base / EXE_NAME, base / "fwknop" / EXE_NAME, base / "bin" / EXE_NAME]

    # 2. В PATH.
    in_path = shutil.which("fwknop")
    if in_path:
        found.append(Path(in_path))

    # 3. Штатные места установки на Windows (в том числе комплект fwknop-gui).
    if sys.platform == "win32":
        for env in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            root = os.environ.get(env)
            if not root:
                continue
            found += [
                Path(root) / "fwknop" / EXE_NAME,
                Path(root) / "fwknop-gui" / EXE_NAME,
                Path(root) / "fwknop-gui" / "bin" / EXE_NAME,
            ]

    return found


def find_exe(configured: str | None = None) -> Path:
    """Найти клиент: сначала путь из настроек, потом автопоиск."""
    if configured:
        path = Path(configured)
        if path.is_file():
            return path
    for path in candidates():
        if path.is_file():
            return path
    raise FwknopNotFound(
        "Не найден клиент fwknop. Укажите путь к нему в настройках "
        "или положите рядом с приложением."
    )


def version(configured: str | None = None) -> str:
    """Версия клиента — для проверки пути в настройках."""
    exe = find_exe(configured)
    result = _run([str(exe), "--version"], timeout=10)
    return (result.stdout or result.stderr).strip()


def knock(variables: dict[str, str], configured: str | None = None) -> dict:
    """Выстрелить SPA-пакет по стойке.

    variables — переменные стойки в терминах .fwknoprc (SPA_SERVER, ACCESS,
    KEY_BASE64 и т.д.), то есть ровно то, что мы храним.

    Возвращает {"ok", "code", "output", "exe"}; текст вывода клиента отдаём в
    интерфейс как есть — по нему видно, что именно не понравилось fwknop.
    """
    exe = find_exe(configured)
    rc_path = data_dir() / ".fwkog-run.rc"
    _write_rc(rc_path, variables)
    try:
        result = _run(
            [str(exe), "--rc-file", str(rc_path), "-n", TEMP_STANZA, "--no-save-args"],
            timeout=TIMEOUT_SEC,
        )
    finally:
        rc_path.unlink(missing_ok=True)

    output = (result.stdout or "") + (result.stderr or "")
    return {
        "ok": result.returncode == 0,
        "code": result.returncode,
        "output": output.strip(),
        "exe": str(exe),
    }


def _write_rc(path: Path, variables: dict[str, str]) -> None:
    """Временный rc-файл со стойкой. Права выставляем до записи содержимого,
    чтобы ключи ни на мгновение не лежали в файле, открытом для чтения всем."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(rcfile.dump_stanza(TEMP_STANZA, variables))


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    """Запуск клиента без мигающего чёрного окна консоли на Windows."""
    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False, **kwargs
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", f"клиент не ответил за {timeout} с")
