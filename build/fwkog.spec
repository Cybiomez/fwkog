# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller-спека (формат PyInstaller 6): собирает FWKOG в один
# исполняемый файл — портативно, двойным кликом, без установки.
#
# Запуск из корня репозитория:  pyinstaller build/fwkog.spec
# Перед сборкой нужен собранный UI:  cd frontend && npm run build
#
# Клиент fwknop.exe внутрь НЕ кладём: он лежит рядом с приложением в архиве
# релиза. Так видно, что начинка — обычный, ничем не изменённый fwknop, и его
# можно заменить своей сборкой.

# Пути PyInstaller разрешает относительно каталога спеки (build/), поэтому до
# корня репозитория поднимаемся через "..".
a = Analysis(
    ["../main.py"],
    pathex=[".."],
    binaries=[],
    # Собранный интерфейс (один самодостаточный index.html) и иконка.
    datas=[
        ("../frontend/dist", "frontend/dist"),
        ("../backend/assets", "backend/assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FWKOG",
    icon="../backend/assets/icon.ico",  # иконка exe (Windows); на Linux игнорируется
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # обычное оконное приложение, без чёрного окна консоли
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
