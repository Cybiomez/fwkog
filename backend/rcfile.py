"""
Формат .fwknoprc — чтение и запись.

FWKOG ничего своего не выдумывает: стойка (stanza) хранится ровно тем же
набором переменных, что понимает клиент fwknop. Этот модуль — единственное
место, где знают про текстовый формат:

    [имя стойки]
    SPA_SERVER          10.0.0.1
    ACCESS              tcp/22

Используется дважды:
  - импорт существующего ~/.fwknoprc (пересесть с fwknop-gui);
  - генерация временного rc-файла для самого стука (см. fwknop.py).

Список переменных взят из client/config_init.c базового fwknop (fko_var_array).
"""

from __future__ import annotations

import re
from collections import OrderedDict

# Все переменные, которые понимает клиент fwknop. Порядок — как в шаблоне
# самого клиента: сначала адрес и доступ, потом ключи, потом прочее.
KNOWN_VARS: tuple[str, ...] = (
    "SPA_SERVER",
    "SPA_SERVER_PORT",
    "SPA_SERVER_PROTO",
    "SPA_SOURCE_PORT",
    "ACCESS",
    "ALLOW_IP",
    "FW_TIMEOUT",
    "KEY",
    "KEY_BASE64",
    "KEY_FILE",
    "HMAC_KEY",
    "HMAC_KEY_BASE64",
    "HMAC_KEY_FILE",
    "USE_HMAC",
    "HMAC_DIGEST_TYPE",
    "DIGEST_TYPE",
    "ENCRYPTION_MODE",
    "NAT_ACCESS",
    "NAT_LOCAL",
    "NAT_PORT",
    "NAT_RAND_PORT",
    "RAND_PORT",
    "TIME_OFFSET",
    "SPOOF_USER",
    "SPOOF_SOURCE_IP",
    "RESOLVE_IP_HTTP",
    "RESOLVE_IP_HTTPS",
    "RESOLVE_HTTP_ONLY",
    "RESOLVE_URL",
    "SERVER_RESOLVE_IPV4",
    "HTTP_USER_AGENT",
    "USE_WGET_USER_AGENT",
    "WGET_CMD",
    "VERBOSE",
    "NO_SAVE_ARGS",
    "USE_GPG",
    "USE_GPG_AGENT",
    "GPG_RECIPIENT",
    "GPG_SIGNER",
    "GPG_HOMEDIR",
    "GPG_EXE",
    "GPG_SIGNING_PW",
    "GPG_SIGNING_PW_BASE64",
    "GPG_NO_SIGNING_PW",
)

# Переменные с секретами: в интерфейсе маскируются, в логи не попадают.
SECRET_VARS: frozenset[str] = frozenset(
    {
        "KEY",
        "KEY_BASE64",
        "HMAC_KEY",
        "HMAC_KEY_BASE64",
        "GPG_SIGNING_PW",
        "GPG_SIGNING_PW_BASE64",
    }
)

_STANZA_RE = re.compile(r"^\[(.+?)\]\s*$")
_VAR_RE = re.compile(r"^([A-Z][A-Z0-9_]*)\s+(.*?)\s*$")

# Ширина колонки значений — как в файлах, которые пишет сам fwknop.
_VAR_COLUMN = 20


def parse(text: str) -> "OrderedDict[str, OrderedDict[str, str]]":
    """Разобрать содержимое .fwknoprc: имя стойки -> переменные.

    Неизвестные переменные не выбрасываем: файл мог быть написан клиентом
    другой версии, и молча терять чужие строки при импорте нечестно.
    """
    stanzas: "OrderedDict[str, OrderedDict[str, str]]" = OrderedDict()
    current: "OrderedDict[str, str] | None" = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        header = _STANZA_RE.match(line)
        if header:
            name = header.group(1).strip()
            current = stanzas.setdefault(name, OrderedDict())
            continue

        if current is None:
            continue  # переменная до первой стойки — мусор, пропускаем

        var = _VAR_RE.match(line)
        if var:
            current[var.group(1)] = var.group(2)

    return stanzas


def dump_stanza(name: str, variables: dict[str, str]) -> str:
    """Собрать одну стойку в текст формата .fwknoprc."""
    lines = [f"[{name}]"]
    for key in sorted(variables, key=_var_order):
        value = str(variables[key]).strip()
        if value == "":
            continue  # пустое значение = переменная не задана
        lines.append(f"{key.ljust(_VAR_COLUMN)}{value}")
    return "\n".join(lines) + "\n"


def dump(stanzas: dict[str, dict[str, str]]) -> str:
    """Собрать целый .fwknoprc из нескольких стоек."""
    return "\n".join(dump_stanza(name, vars_) for name, vars_ in stanzas.items())


def _var_order(key: str) -> tuple[int, str]:
    """Сортировка переменных: известные — в порядке KNOWN_VARS, прочие — в конец."""
    try:
        return (KNOWN_VARS.index(key), "")
    except ValueError:
        return (len(KNOWN_VARS), key)
