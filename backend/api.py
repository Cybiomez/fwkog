"""
Мост UI <-> Python (js_api для pywebview).

Каждый метод этого класса виден из JavaScript как
window.pywebview.api.<имя_метода>. Логики тут нет — только перевод вызовов
интерфейса в вызовы хранилища, клиента fwknop и импорта/экспорта.

Ответы единообразные: {"ok": True, ...} либо {"ok": False, "error": "текст"},
чтобы интерфейсу не приходилось разбирать исключения.
"""

from __future__ import annotations

from pathlib import Path

from . import fwknop, rcfile, session, settings as settings_mod
from .knocker import OpenWindows
from .paths import user_fwknoprc
from .vault import Vault, VaultError, WrongPassword
from .version import VERSION


def _ok(**extra) -> dict:
    return {"ok": True, **extra}


def _fail(error: str) -> dict:
    return {"ok": False, "error": error}


class Api:
    def __init__(self, vault: Vault | None = None) -> None:
        self._vault = vault or Vault()
        self._windows = OpenWindows()
        self._window = None  # окно pywebview — нужно для файловых диалогов

    def set_window(self, window) -> None:
        self._window = window

    # --- замок ---

    def state(self) -> dict:
        """Что показывать при старте: экран создания, ввода пароля или список."""
        return {
            "version": VERSION,
            "exists": self._vault.exists,
            "unlocked": self._vault.unlocked,
            "can_remember": session.available(),
        }

    def create_vault(self, password: str) -> dict:
        """Первый запуск: завести хранилище под новым мастер-паролем."""
        if not password:
            return _fail("Пустой пароль не годится.")
        try:
            self._vault.create(password)
        except VaultError as e:
            return _fail(str(e))
        return _ok()

    def unlock(self, password: str, remember_hours: int = 0) -> dict:
        """Открыть хранилище мастер-паролем."""
        try:
            self._vault.unlock(password)
        except WrongPassword:
            return _fail("Пароль не подошёл.")
        except (VaultError, OSError) as e:
            return _fail(str(e))
        hours = int(remember_hours or 0)
        if hours > 0:
            session.remember(password, hours)
        else:
            session.forget()
        current = settings_mod.load()
        current["remember_hours"] = hours
        settings_mod.save(current)
        return _ok()

    def unlock_remembered(self) -> dict:
        """Попробовать открыть хранилище запомненным паролем (без вопросов)."""
        password = session.recall()
        if not password:
            return _fail("нет запомненного пароля")
        try:
            self._vault.unlock(password)
        except (VaultError, OSError):
            session.forget()
            return _fail("запомненный пароль больше не подходит")
        return _ok()

    def lock(self) -> dict:
        """Закрыть хранилище и забыть запомненный пароль."""
        self._vault.lock()
        session.forget()
        return _ok()

    def change_password(self, old: str, new: str) -> dict:
        if not new:
            return _fail("Пустой пароль не годится.")
        try:
            self._vault.change_password(old, new)
        except WrongPassword:
            return _fail("Текущий пароль не подошёл.")
        except (VaultError, OSError) as e:
            return _fail(str(e))
        session.forget()  # запомненный старый пароль больше не нужен
        return _ok()

    # --- стойки ---

    def list_stanzas(self) -> list[dict]:
        """Стойки для списка: имя, переменные и остаток окна доступа."""
        if not self._vault.unlocked:
            return []
        result = []
        for stanza in self._vault.list_stanzas():
            result.append(
                {
                    "name": stanza["name"],
                    "vars": stanza["vars"],
                    "remaining": self._windows.remaining(stanza["name"]),
                }
            )
        return result

    def save_stanza(self, original_name: str, name: str, variables: dict) -> dict:
        """Добавить или изменить стойку. original_name пустое — это добавление."""
        name = (name or "").strip()
        if not name:
            return _fail("У стойки должно быть имя.")
        if "[" in name or "]" in name:
            return _fail("В имени стойки нельзя использовать скобки [ ].")

        cleaned = {k: str(v).strip() for k, v in (variables or {}).items() if str(v).strip()}
        if not cleaned.get("SPA_SERVER"):
            return _fail("Не указан сервер (SPA_SERVER).")
        if not cleaned.get("ACCESS"):
            return _fail("Не указан доступ (ACCESS), например tcp/22.")

        stanzas = self._vault.list_stanzas()
        names = [s["name"] for s in stanzas]
        if name in names and name != original_name:
            return _fail(f"Стойка «{name}» уже есть.")

        if original_name and original_name in names:
            index = names.index(original_name)
            stanzas[index] = {"name": name, "vars": cleaned}
            if name != original_name:
                self._windows.forget(original_name)
        else:
            stanzas.append({"name": name, "vars": cleaned})

        try:
            self._vault.set_stanzas(stanzas)
        except (VaultError, OSError) as e:
            return _fail(str(e))
        return _ok()

    def remove_stanza(self, name: str) -> dict:
        stanzas = [s for s in self._vault.list_stanzas() if s["name"] != name]
        try:
            self._vault.set_stanzas(stanzas)
        except (VaultError, OSError) as e:
            return _fail(str(e))
        self._windows.forget(name)
        return _ok()

    # --- стук ---

    def knock(self, name: str) -> dict:
        """Выстрелить SPA-пакет по стойке и завести отсчёт окна доступа."""
        stanza = next((s for s in self._vault.list_stanzas() if s["name"] == name), None)
        if stanza is None:
            return _fail("Стойка не найдена.")

        configured = settings_mod.load().get("fwknop_path") or None
        try:
            result = fwknop.knock(stanza["vars"], configured)
        except fwknop.FwknopNotFound as e:
            return _fail(str(e))
        except OSError as e:
            return _fail(f"Не удалось запустить клиент: {e}")

        if not result["ok"]:
            return _fail(result["output"] or f"Клиент fwknop вернул код {result['code']}.")

        window = _int_or_none(stanza["vars"].get("FW_TIMEOUT"))
        self._windows.opened(name, window)
        return _ok(window=window or 0, output=result["output"])

    # --- клиент fwknop ---

    def fwknop_status(self) -> dict:
        """Найден ли клиент, где именно и какой версии."""
        configured = settings_mod.load().get("fwknop_path") or None
        try:
            path = str(fwknop.find_exe(configured))
            return _ok(path=path, version=fwknop.version(configured))
        except fwknop.FwknopNotFound as e:
            return _fail(str(e))
        except OSError as e:
            return _fail(f"Клиент не запускается: {e}")

    def get_settings(self) -> dict:
        data = settings_mod.load()
        data["can_remember"] = session.available()
        return data

    def set_remember_hours(self, hours: int) -> dict:
        """Сменить срок запоминания мастер-пароля — сразу, без перезапуска."""
        hours = max(0, int(hours or 0))
        data = settings_mod.load()
        data["remember_hours"] = hours
        settings_mod.save(data)
        if hours and self._vault.password:
            session.remember(self._vault.password, hours)
        else:
            session.forget()
        return _ok(remember_hours=hours)

    def set_fwknop_path(self, path: str) -> dict:
        data = settings_mod.load()
        data["fwknop_path"] = (path or "").strip()
        settings_mod.save(data)
        return self.fwknop_status()

    def pick_fwknop(self) -> dict:
        """Выбрать файл клиента через системный диалог."""
        chosen = self._open_dialog("Выберите fwknop")
        if not chosen:
            return _fail("отменено")
        return self.set_fwknop_path(chosen)

    # --- перенос ---

    def import_fwknoprc(self, path: str = "") -> dict:
        """Забрать стойки из существующего .fwknoprc (по умолчанию — штатного).

        Стойка [default] задаёт значения по умолчанию для остальных, отдельной
        «стойкой доступа» она не является — поэтому её не переносим.
        """
        source = Path(path) if path else user_fwknoprc()
        if not source.is_file():
            return _fail(f"Файл не найден: {source}")
        try:
            parsed = rcfile.parse(source.read_text(encoding="utf-8", errors="replace"))
        except OSError as e:
            return _fail(f"Не прочитать файл: {e}")

        incoming = [
            {"name": name, "vars": dict(variables)}
            for name, variables in parsed.items()
            if name.lower() != "default" and variables
        ]
        if not incoming:
            return _fail("В файле нет стоек, кроме [default].")
        return self._merge(incoming)

    def pick_and_import_fwknoprc(self) -> dict:
        chosen = self._open_dialog("Выберите файл .fwknoprc")
        if not chosen:
            return _fail("отменено")
        return self.import_fwknoprc(chosen)

    def export_vault(self, password: str) -> dict:
        """Выгрузить все стойки в зашифрованный файл под отдельным паролем."""
        if not password:
            return _fail("Задайте пароль для файла экспорта.")
        target = self._save_dialog("fwkog-export.fwkog")
        if not target:
            return _fail("отменено")
        try:
            self._vault.export_to(Path(target), password)
        except (VaultError, OSError) as e:
            return _fail(str(e))
        return _ok(path=target)

    def import_vault(self, password: str) -> dict:
        """Забрать стойки из файла экспорта FWKOG."""
        chosen = self._open_dialog("Выберите файл экспорта FWKOG")
        if not chosen:
            return _fail("отменено")
        try:
            incoming = Vault.read_export(Path(chosen), password)
        except WrongPassword:
            return _fail("Пароль к файлу не подошёл.")
        except (VaultError, OSError) as e:
            return _fail(str(e))
        if not incoming:
            return _fail("В файле нет стоек.")
        return self._merge(incoming)

    # --- служебное ---

    def _merge(self, incoming: list[dict]) -> dict:
        """Добавить стойки к существующим: совпадающие имена — заменяются."""
        stanzas = self._vault.list_stanzas()
        index = {s["name"]: i for i, s in enumerate(stanzas)}
        added = replaced = 0
        for stanza in incoming:
            item = {"name": stanza["name"], "vars": dict(stanza.get("vars", {}))}
            if item["name"] in index:
                stanzas[index[item["name"]]] = item
                replaced += 1
            else:
                index[item["name"]] = len(stanzas)
                stanzas.append(item)
                added += 1
        try:
            self._vault.set_stanzas(stanzas)
        except (VaultError, OSError) as e:
            return _fail(str(e))
        return _ok(added=added, replaced=replaced)

    def _open_dialog(self, title: str) -> str:
        import webview

        if self._window is None:
            return ""
        chosen = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False)
        return chosen[0] if chosen else ""

    def _save_dialog(self, filename: str) -> str:
        import webview

        if self._window is None:
            return ""
        chosen = self._window.create_file_dialog(webview.SAVE_DIALOG, save_filename=filename)
        if isinstance(chosen, (list, tuple)):
            return chosen[0] if chosen else ""
        return chosen or ""


def _int_or_none(value) -> int | None:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
