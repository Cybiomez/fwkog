"""
Учёт открытых окон доступа.

Клиент fwknop «стреляет и забывает»: обратной связи от сервера нет, узнать
фактическую длительность окна неоткуда. Поэтому отсчёт ведём от того, что сами
запросили — от FW_TIMEOUT стойки.

Важная оговорка (она же в README): демон применяет запрошенное значение, но не
выше своего потолка MAX_FW_TIMEOUT (по умолчанию 300 с). Если сервер срезал
окно, наш таймер покажет больше, чем есть на самом деле. Без FW_TIMEOUT сервер
берёт своё FW_ACCESS_TIMEOUT (по умолчанию 30 с) — тогда длительность нам
неизвестна и таймер не показываем.
"""

from __future__ import annotations

import time


class OpenWindows:
    """Какие стойки сейчас «открыты» и сколько им осталось."""

    def __init__(self) -> None:
        self._until: dict[str, float] = {}

    def opened(self, stanza_id: str, seconds: int | None) -> None:
        """Отметить удачный стук. seconds=None — длительность неизвестна."""
        if seconds and seconds > 0:
            self._until[stanza_id] = time.time() + seconds
        else:
            self._until.pop(stanza_id, None)

    def remaining(self, stanza_id: str) -> int:
        """Сколько секунд осталось. 0 — окно закрыто или длительность неизвестна."""
        until = self._until.get(stanza_id)
        if until is None:
            return 0
        left = int(round(until - time.time()))
        if left <= 0:
            self._until.pop(stanza_id, None)
            return 0
        return left

    def forget(self, stanza_id: str) -> None:
        """Убрать отсчёт (стойку удалили или пользователь сбросил таймер)."""
        self._until.pop(stanza_id, None)
