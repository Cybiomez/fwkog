"""
Точка входа FWKOG: окно вебвью с интерфейсом.

Запуск из исходников:  python main.py   (из корня репозитория)
Перед этим нужен собранный UI:  cd frontend && npm install && npm run build

Приложение однооконное: ни трея, ни фоновой работы — стук происходит только по
кнопке. Вся логика — в остальных модулях backend, здесь только окно.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .api import Api

WINDOW_W, WINDOW_H = 520, 720
MIN_W, MIN_H = 420, 560


def resolve_ui_index() -> str:
    """Найти собранный index.html (и в исходниках, и в собранном бинарнике)."""
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)  # каталог распаковки PyInstaller
    if meipass:
        candidates.append(Path(meipass) / "frontend" / "dist" / "index.html")
    here = Path(__file__).resolve().parent
    candidates.append(here.parent / "frontend" / "dist" / "index.html")

    for path in candidates:
        if path.is_file():
            return str(path)
    raise FileNotFoundError(
        "Не найден собранный UI (frontend/dist/index.html). "
        "Соберите его: cd frontend && npm install && npm run build"
    )


def main() -> None:
    try:
        import webview
    except ImportError as e:
        print(
            "Не установлены зависимости UI. Установите: "
            "pip install -r backend/requirements.txt\n"
            f"Детали: {e}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    api = Api()
    window = webview.create_window(
        "FWKOG",
        resolve_ui_index(),
        js_api=api,
        width=WINDOW_W,
        height=WINDOW_H,
        min_size=(MIN_W, MIN_H),
    )
    api.set_window(window)  # окну принадлежат файловые диалоги
    webview.start()


if __name__ == "__main__":
    main()
