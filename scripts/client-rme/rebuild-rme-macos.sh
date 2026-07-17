#!/usr/bin/env bash
# Recompila RME usando OpenGL nativo de macOS (no XQuartz/X11).
# El build con wxWidgets de vcpkg enlaza /opt/X11/lib/libGL → pantalla negra.
set -euo pipefail

RME_ROOT="${RME_ROOT:-$HOME/dev/rme}"
RME_BUILD="${RME_BUILD:-$RME_ROOT/build}"
VCPKG_ROOT="${VCPKG_ROOT:-$HOME/dev/vcpkg}"
WX_CONFIG="${WX_CONFIG:-/opt/homebrew/bin/wx-config}"
SDK="$(xcrun --show-sdk-path)"

if [[ ! -d "$RME_ROOT/.git" ]]; then
  echo "ERROR: No existe $RME_ROOT"
  exit 1
fi
if [[ ! -x "$WX_CONFIG" ]]; then
  echo "ERROR: Instalá wxWidgets: brew install wxwidgets"
  exit 1
fi
if [[ ! -f "$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" ]]; then
  echo "ERROR: No existe vcpkg en $VCPKG_ROOT"
  exit 1
fi

mkdir -p "$RME_BUILD"
cd "$RME_BUILD"

cmake "$RME_ROOT" \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_TOOLCHAIN_FILE="$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" \
  -DwxWidgets_CONFIG_EXECUTABLE="$WX_CONFIG" \
  -DCMAKE_FIND_FRAMEWORK=FIRST \
  -DOPENGL_gl_LIBRARY="$SDK/System/Library/Frameworks/OpenGL.framework/OpenGL.tbd" \
  -DOPENGL_glu_LIBRARY="$SDK/System/Library/Frameworks/OpenGL.framework/OpenGL.tbd" \
  -DOPENGL_INCLUDE_DIR="$SDK/System/Library/Frameworks/OpenGL.framework/Headers" \
  -DGLUT_glut_LIBRARY="$SDK/System/Library/Frameworks/GLUT.framework/Versions/A/GLUT.tbd" \
  -DGLUT_INCLUDE_DIR="$SDK/System/Library/Frameworks/GLUT.framework/Headers"

make -j"$(sysctl -n hw.ncpu 2>/dev/null || echo 4)"

echo ""
echo "=== Verificación OpenGL ==="
if otool -L "$RME_BUILD/rme" | grep -q '/opt/X11'; then
  echo "ERROR: sigue enlazado a XQuartz. Pantalla negra probable."
  otool -L "$RME_BUILD/rme" | grep -E 'GL|glut|X11' || true
  exit 1
fi

otool -L "$RME_BUILD/rme" | grep -E 'OpenGL|GLUT' || true
echo "OK — OpenGL nativo. Probá: ~/Desktop/yurots-principal/scripts/open-rme.sh"
