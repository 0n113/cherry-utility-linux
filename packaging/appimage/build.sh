#!/usr/bin/env bash
# Build cherryctl-VERSION-x86_64.AppImage into dist/.
#
#   packaging/appimage/build.sh
#
# Needs curl and network access. Downloads a relocatable Python
# (github.com/niess/python-appimage) and appimagetool, checks both against
# pinned checksums, installs cherryctl with PySide6 into the Python and packs
# the result. Nothing is installed on the host.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
work="${WORK_DIR:-$repo/build/appimage}"

# Build inputs, pinned by checksum. To update one, change its URL and replace
# the checksum with the output of sha256sum for the new file.
python_url="https://github.com/niess/python-appimage/releases/download/python3.12/python3.12.15-cp312-cp312-manylinux_2_28_x86_64.AppImage"
python_sha256="929ce69b45955bfc74af81fd65a65c3ad240593c99b3574466a94ebf0f987ebf"
tool_url="https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage"
tool_sha256="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"

fetch() { curl -fsSL --retry 8 --retry-all-errors --retry-delay 3 "$@"; }

version="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$repo/cherryctl/__init__.py")"
rm -rf "$work" && mkdir -p "$work" "$repo/dist"
cd "$work"

fetch -o python.AppImage "$python_url"
fetch -o appimagetool "$tool_url"
printf '%s  %s\n' "$python_sha256" python.AppImage "$tool_sha256" appimagetool | sha256sum --check --strict
chmod +x python.AppImage appimagetool

./python.AppImage --appimage-extract >/dev/null
mv squashfs-root AppDir
python="AppDir/opt/python3.12/bin/python3.12"
"$python" -I -m pip install --no-cache-dir --no-warn-script-location \
	--constraint "$repo/packaging/appimage/constraints.txt" "$repo[gui]"

# Qt parts the two windows do not use (QML, Quick, PDF, tools, translations).
site="AppDir/opt/python3.12/lib/python3.12/site-packages/PySide6"
rm -rf "$site"/Qt/qml "$site"/Qt/translations "$site"/Qt/libexec "$site"/Qt/resources \
	"$site"/Qt/lib/libQt6Quick* "$site"/Qt/lib/libQt6Qml* "$site"/Qt/lib/libQt6Pdf* \
	"$site"/Qt/lib/libQt6Designer* "$site"/Qt/lib/libQt6Help* "$site"/Qt/lib/libQt6Sql* \
	"$site"/Qt/lib/libQt6Test* "$site"/Qt/lib/libQt6Labs* "$site"/Qt/lib/libQt6ShaderTools* \
	"$site"/Qt/plugins/sqldrivers "$site"/Qt/plugins/qmltooling "$site"/Qt/plugins/qmllint \
	"$site"/QtQuick* "$site"/QtQml* "$site"/QtPdf* "$site"/QtDesigner* "$site"/QtHelp* \
	"$site"/QtSql* "$site"/QtTest* "$site"/assistant "$site"/designer "$site"/linguist \
	"$site"/lrelease "$site"/lupdate "$site"/qmllint "$site"/qmlls "$site"/qmlformat

# Replace the Python launcher's identity with ours.
rm -f AppDir/AppRun AppDir/*.desktop AppDir/*.png AppDir/.DirIcon
rm -rf AppDir/usr/share/applications AppDir/usr/share/metainfo AppDir/usr/share/icons
install -m 755 "$repo/packaging/appimage/AppRun" AppDir/AppRun
install -m 644 "$repo/share/cherryctl.desktop" AppDir/cherryctl.desktop
install -m 644 "$repo/share/cherryctl.svg" AppDir/cherryctl.svg
ln -s cherryctl.svg AppDir/.DirIcon

# Extraction leaves some directories readable by the owner only.
chmod -R a+rX AppDir

out="$repo/dist/cherryctl-$version-x86_64.AppImage"
ARCH=x86_64 ./appimagetool --appimage-extract-and-run --no-appstream AppDir "$out"
echo "built $out"
