"""
Определение своего внешнего IP-адреса.

Зачем это здесь. У стойки может стоять `ALLOW_IP resolve` — «открыть доступ
тому адресу, с которого я выхожу в интернет». Сам клиент fwknop в этом режиме
запускает внешнюю программу wget по пути, зашитому при сборке (`/usr/bin/wget`),
и на Windows падает: wget там нет. Поэтому адрес узнаёт приложение, а клиенту
передаётся уже конкретный `ALLOW_IP 203.0.113.10` — для fwknop это штатный
вариант «адрес указан вручную», никакой самодеятельности в протоколе.

Адрес спрашиваем у того же сервиса, что и сам fwknop, и тем же именем клиента.
Если в стойке задан RESOLVE_URL — используем его.
"""

from __future__ import annotations

import ipaddress
import urllib.error
import urllib.request

# Тот же адрес и то же имя клиента, что использует fwknop 2.6.11.
DEFAULT_URL = "https://www.cipherdyne.org/cgi-bin/myip"
USER_AGENT = "Fwknop/2.6.11"
TIMEOUT_SEC = 12


class ResolveError(Exception):
    """Не удалось узнать внешний адрес."""


def external_ip(url: str | None = None) -> str:
    """Вернуть свой внешний IPv4. Ошибка сети или мусор в ответе -> ResolveError."""
    target = (url or DEFAULT_URL).strip() or DEFAULT_URL
    request = urllib.request.Request(target, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SEC) as response:
            body = response.read(256).decode("ascii", errors="replace")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ResolveError(f"не удалось обратиться к {target}: {e}") from e

    candidate = body.strip().splitlines()[0].strip() if body.strip() else ""
    try:
        address = ipaddress.IPv4Address(candidate)
    except ipaddress.AddressValueError as e:
        raise ResolveError(f"сервис {target} вернул не адрес: {candidate!r}") from e
    return str(address)
