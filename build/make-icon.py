"""
Генератор иконки приложения: backend/assets/icon.ico.

Рисовалки в зависимостях держать незачем — иконка простая и описывается кодом:
синий скруглённый квадрат, из точки слева расходятся три дуги (один пакет —
стук — уходит к серверу). Сглаживание — через отрисовку в четырёхкратном
размере с последующим усреднением.

Запуск:  python build/make-icon.py
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

SIZES = (16, 32, 48, 64, 128, 256)
SUPERSAMPLE = 4

BLUE = (31, 107, 184)      # тот же акцент, что в интерфейсе (--accent)
BLUE_DARK = (23, 84, 148)  # низ подложки: лёгкий вертикальный переход
WHITE = (255, 255, 255)


def draw(size: int) -> bytes:
    """Нарисовать иконку размера size и вернуть пиксели RGBA."""
    big = size * SUPERSAMPLE
    # Накопители цвета и прозрачности по каждому пикселю итогового размера.
    pixels = [[[0.0, 0.0, 0.0, 0.0] for _ in range(size)] for _ in range(size)]

    radius = big * 0.22          # скругление углов подложки
    cx, cy = big * 0.30, big * 0.5  # источник «стука»
    dot_r = big * 0.085
    arc_width = big * 0.075

    for y in range(big):
        for x in range(big):
            color = _sample(x + 0.5, y + 0.5, big, radius, cx, cy, dot_r, arc_width)
            if color is None:
                continue
            target = pixels[y // SUPERSAMPLE][x // SUPERSAMPLE]
            for i in range(4):
                target[i] += color[i]

    weight = SUPERSAMPLE * SUPERSAMPLE
    out = bytearray()
    for row in pixels:
        for r, g, b, a in row:
            out += bytes((round(r / weight), round(g / weight), round(b / weight), round(a / weight)))
    return bytes(out)


def _sample(x: float, y: float, big: float, radius: float, cx: float, cy: float,
            dot_r: float, arc_width: float) -> tuple[float, float, float, float] | None:
    """Цвет одной точки: подложка, точка-источник и три дуги поверх неё."""
    if not _inside_rounded_square(x, y, big, radius):
        return None

    # Подложка с лёгким переходом сверху вниз.
    k = y / big
    base = tuple(BLUE[i] + (BLUE_DARK[i] - BLUE[i]) * k for i in range(3))

    dist = math.hypot(x - cx, y - cy)
    if dist <= dot_r:
        return (*WHITE, 255)

    # Три дуги вправо от источника — «сигнал уходит к серверу».
    angle = math.atan2(y - cy, x - cx)
    if abs(angle) < math.radians(52):
        for n in (1, 2, 3):
            ring = dot_r + big * 0.10 * n
            if abs(dist - ring) <= arc_width / 2:
                return (*WHITE, 255)

    return (*base, 255)


def _inside_rounded_square(x: float, y: float, size: float, radius: float) -> bool:
    """Точка внутри скруглённого квадрата?"""
    nx = min(max(x, radius), size - radius)
    ny = min(max(y, radius), size - radius)
    if x == nx or y == ny:
        return True
    return math.hypot(x - nx, y - ny) <= radius


def png(size: int, rgba: bytes) -> bytes:
    """Упаковать пиксели в PNG (Windows понимает PNG внутри .ico с Vista)."""
    raw = bytearray()
    stride = size * 4
    for row in range(size):
        raw.append(0)  # тип фильтра строки: без фильтра
        raw += rgba[row * stride:(row + 1) * stride]

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def main() -> None:
    images = [png(size, draw(size)) for size in SIZES]

    header = struct.pack("<HHH", 0, 1, len(images))  # зарезервировано, тип 1 = ico, число картинок
    offset = len(header) + 16 * len(images)
    entries = b""
    for size, data in zip(SIZES, images):
        entries += struct.pack(
            "<BBBBHHII",
            size if size < 256 else 0,  # 0 означает 256
            size if size < 256 else 0,
            0, 0, 1, 32, len(data), offset,
        )
        offset += len(data)

    target = Path(__file__).resolve().parent.parent / "backend" / "assets" / "icon.ico"
    target.write_bytes(header + entries + b"".join(images))
    print(f"готово: {target} ({target.stat().st_size} байт)")


if __name__ == "__main__":
    main()
