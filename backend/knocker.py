"""
Учёт открытых окон доступа.

Клиент fwknop «стреляет и забывает»: обратной связи от сервера нет, узнать
фактическую длительность окна неоткуда. Поэтому отсчёт ведём от того, что сами
запросили — от FW_TIMEOUT стойки.

Важная оговорка (она же в README): демон применяет запрошенное значение, но не
выше своего потолка MAX_FW_TIMEOUT (по умолчанию 300 с). Если сервер срезал
окно, наш таймер покажет больше, чем есть на самом деле.

Без FW_TIMEOUT длительность задаёт сервер своим FW_ACCESS_TIMEOUT — считаем от
его значения по умолчанию (DEFAULT_TIMEOUT). Это тоже предположение, но лучше
показать ожидаемый отсчёт, чем не показать ничего.
"""

from __future__ import annotations

import time

# Умолчание демона fwknopd (FW_ACCESS_TIMEOUT в fwknopd.conf): сколько держится
# окно доступа, если клиент не запросил свою длительность.
DEFAULT_TIMEOUT = 30


class OpenWindows:
    """Какие стойки сейчас «открыты» и сколько им осталось."""

    def __init__(self) -> None:
        self._until: dict[str, float] = {}

    def opened(self, stanza_id: str, seconds: int | None) -> None:
        """Отметить удачный стук. seconds=None — стойка не задала длительность,
        берём умолчание сервера."""
        self._until[stanza_id] = time.time() + (seconds or DEFAULT_TIMEOUT)

    def remaining(self, stanza_id: str) -> int:
        """Сколько секунд осталось. 0 — окно уже закрылось."""
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
