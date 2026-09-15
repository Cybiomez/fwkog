#!/usr/bin/env bash
#
# Сборка клиента fwknop.exe под Windows из официальных исходников.
#
# Запускается на Linux с кросс-компилятором mingw-w64 (пакет mingw-w64).
# Это тот же самый клиент, что и всегда, — мы его не меняем, только собираем:
# готовых сборок под Windows проект не публикует, в релизах только исходники.
#
#   Использование:  build/fwknop-windows.sh [каталог для результата]
#   По умолчанию результат:  dist/fwknop/fwknop.exe
#
# Почему нужны нештатные ключи сборки (подробности — в docs/decisions.md):
#   --disable-execvp    в Windows нет fork/pipe/waitpid; клиент сам умеет
#                       запасной путь через popen(), этим ключом он и выбирается;
#   ac_cv_func_fstat=no отключает проверку прав rc-файла — она про права Unix
#                       (getuid, S_ISLNK), в Windows смысла не имеет;
#   правка Makefile.in  в исходниках статической библиотеке ошибочно передают
#                       ключи -lwsock32/-lws2_32; современный ar это отвергает;
#   -Wl,-Bstatic -lssp  прилинковать защиту стека статически, чтобы рядом с exe
#                       не требовалась libssp-0.dll.

set -euo pipefail

FWKNOP_VERSION="2.6.11"
FWKNOP_SHA256="bcb4e0e2eb5fcece5083d506da8471f68e33fb6b17d9379c71427a95f9ca1ec8"
FWKNOP_URL="https://github.com/mrash/fwknop/releases/download/${FWKNOP_VERSION}/fwknop-${FWKNOP_VERSION}.tar.gz"

HOST="x86_64-w64-mingw32"
OUT_DIR="${1:-dist/fwknop}"
OUT_DIR="$(mkdir -p "$OUT_DIR" && cd "$OUT_DIR" && pwd)"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "==> Скачиваю fwknop ${FWKNOP_VERSION}"
curl -fsSL -o "$WORK/fwknop.tar.gz" "$FWKNOP_URL"

echo "==> Проверяю контрольную сумму"
echo "${FWKNOP_SHA256}  $WORK/fwknop.tar.gz" | sha256sum -c -

echo "==> Распаковываю"
tar xzf "$WORK/fwknop.tar.gz" -C "$WORK"
SRC="$WORK/fwknop-${FWKNOP_VERSION}"

echo "==> Правлю ключи архиватора статической библиотеки"
sed -i 's/^@USE_MINGW_TRUE@libfko_util_a_LIBADD = -lwsock32 -lws2_32$/@USE_MINGW_TRUE@libfko_util_a_LIBADD =/' \
    "$SRC/common/Makefile.in"

echo "==> Настраиваю сборку под ${HOST}"
cd "$SRC"
./configure \
    --host="$HOST" \
    --disable-server \
    --disable-execvp \
    --enable-static \
    --disable-shared \
    CPPFLAGS="-DWIN32" \
    LIBS="-lwsock32 -lws2_32 -Wl,-Bstatic -lssp" \
    ac_cv_func_fstat=no \
    -q

echo "==> Собираю"
make -j"$(nproc)"

echo "==> Проверяю результат"
file client/fwknop.exe | grep -q "PE32+ executable" || {
    echo "Собрался не Windows-бинарник" >&2
    exit 1
}
# Посторонних библиотек рядом с exe быть не должно — только системные Windows.
if "${HOST}-objdump" -p client/fwknop.exe | grep "DLL Name" | grep -qvE "ADVAPI32|KERNEL32|msvcrt|WS2_32|WSOCK32"; then
    echo "Появилась лишняя зависимость от DLL:" >&2
    "${HOST}-objdump" -p client/fwknop.exe | grep "DLL Name" >&2
    exit 1
fi

cp client/fwknop.exe "$OUT_DIR/fwknop.exe"
cp LICENSE "$OUT_DIR/fwknop-LICENSE.txt" 2>/dev/null || cp COPYING "$OUT_DIR/fwknop-LICENSE.txt"
echo "==> Готово: $OUT_DIR/fwknop.exe"
