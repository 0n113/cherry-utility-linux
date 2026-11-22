#!/usr/bin/env bash
# Build cherryctl-VERSION-x86_64.AppImage into dist/.
#
#   packaging/appimage/build.sh
#
# Needs curl and network access. Downloads a relocatable Python
# (github.com/niess/python-appimage) and appimagetool, installs cherryctl with
# PySide6 into it and packs the result. Nothing is installed on the host.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
work="${WORK_DIR:-$repo/build/appimage}"
python_tag="python3.12"
python_abi="cp312-cp312-manylinux_2_28_x86_64"

fetch() { curl -fsSL --retry 8 --retry-all-errors --retry-delay 3 "$@"; }

version="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$repo/cherryctl/__init__.py")"
rm -rf "$work" && mkdir -p "$work" "$repo/dist"
cd "$work"

# The Python AppImage's file name contains its patch version; ask the API.
# Unauthenticated API requests are rate limited per address, which shared CI
# runners exceed, so use GITHUB_TOKEN when it is set.
auth=()
[[ -z "${GITHUB_TOKEN:-}" ]] || auth=(-H "Authorization: Bearer $GITHUB_TOKEN")
python_url="$(fetch "${auth[@]}" "https://api.github.com/repos/niess/python-appimage/releases/tags/$python_tag" |
	grep -o "https://[^\"]*-$python_abi\.AppImage" | head -n 1)"
[[ -n "$python_url" ]] || { echo "no Python AppImage found for $python_abi" >&2; exit 1; }
fetch -o python.AppImage "$python_url"
fetch -o appimagetool "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
chmod +x python.AppImage appimagetool

./python.AppImage --appimage-extract >/dev/null
mv squashfs-root AppDir
python="AppDir/opt/python3.12/bin/python3.12"
"$python" -I -m pip install --no-cache-dir --no-warn-script-location "$repo[gui]"

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
