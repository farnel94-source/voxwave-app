"""Script de build automatise multi-plateforme pour VoxWave.

Usage:
    python build.py build                   # Detecte la plateforme
    python build.py build --platform linux  # AppImage Linux
    python build.py build --platform windows # exe + ZIP Windows
    python build.py installer               # Cree l'installer (Inno Setup Windows)
    python build.py clean                   # Nettoie les artefacts
    python build.py all                     # Clean + Build + Package + Installer
"""

import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "voxwave.spec"


def detect_platform() -> str:
    """Detecte la plateforme courante.

    Returns:
        'linux', 'windows', ou 'darwin'.
    """
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    elif system == "darwin":
        return "darwin"
    else:
        print(f"Plateforme non supportee: {system}")
        sys.exit(1)


def clean() -> None:
    """Supprime les artefacts de build."""
    for d in [DIST, BUILD]:
        if d.exists():
            print(f"Suppression {d}...")
            shutil.rmtree(d)
    print("Clean termine.")


def build_pyinstaller() -> None:
    """Lance PyInstaller avec le spec."""
    print("Build VoxWave (PyInstaller)...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC),
        "--noconfirm",
        "--clean",
    ]
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print("Build echoue !")
        sys.exit(1)
    print("Build PyInstaller termine.")


def build_linux() -> None:
    """Build Linux : PyInstaller + AppImage."""
    build_pyinstaller()

    exe_path = DIST / "VoxWave"
    if not exe_path.exists():
        print(f"Erreur: {exe_path} introuvable apres build.")
        sys.exit(1)

    # Creer la structure AppDir
    appdir = DIST / "VoxWave.AppDir"
    if appdir.exists():
        shutil.rmtree(appdir)
    appdir.mkdir(parents=True)

    usr_bin = appdir / "usr" / "bin"
    usr_bin.mkdir(parents=True)
    shutil.copy2(exe_path, usr_bin / "VoxWave")

    # Desktop file
    desktop = appdir / "VoxWave.desktop"
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=VoxWave\n"
        "Exec=VoxWave\n"
        "Icon=voxwave\n"
        "Comment=Dictee vocale intelligente\n"
        "Categories=Utility;Audio;\n"
        "Terminal=false\n"
    )

    # Icon (simple placeholder PNG si pas d'icone)
    icon_src = ROOT / "assets" / "icon.png"
    icon_dst = appdir / "voxwave.png"
    if icon_src.exists():
        shutil.copy2(icon_src, icon_dst)
    else:
        # Generer une icone placeholder
        _create_placeholder_icon(icon_dst)

    # AppRun script
    apprun = appdir / "AppRun"
    apprun.write_text(
        "#!/bin/bash\n"
        'HERE="$(dirname "$(readlink -f "$0")")"\n'
        'exec "$HERE/usr/bin/VoxWave" "$@"\n'
    )
    apprun.chmod(0o755)

    # Copier config et .env.example
    for extra in ["config.yaml", ".env.example"]:
        src = ROOT / extra
        if src.exists():
            shutil.copy2(src, usr_bin / extra)

    # Creer l'AppImage avec appimagetool si disponible
    appimagetool = shutil.which("appimagetool")
    if appimagetool:
        appimage_path = DIST / "VoxWave-x86_64.AppImage"
        print(f"Creation AppImage avec appimagetool...")
        result = subprocess.run(
            [appimagetool, str(appdir), str(appimage_path)],
            cwd=str(DIST),
        )
        if result.returncode == 0:
            size_mb = appimage_path.stat().st_size / (1024 * 1024)
            print(f"AppImage cree: {appimage_path} ({size_mb:.1f} MB)")
        else:
            print("Erreur creation AppImage. AppDir disponible dans dist/VoxWave.AppDir/")
    else:
        print(
            "appimagetool non trouve. AppDir disponible dans dist/VoxWave.AppDir/\n"
            "Pour creer l'AppImage, installez appimagetool:\n"
            "  wget https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage\n"
            "  chmod +x appimagetool-x86_64.AppImage && sudo mv appimagetool-x86_64.AppImage /usr/local/bin/appimagetool"
        )


def build_windows() -> None:
    """Build Windows : PyInstaller + ZIP."""
    build_pyinstaller()
    package_windows()


def package_windows() -> None:
    """Cree un ZIP de distribution Windows."""
    exe_path = DIST / "VoxWave.exe"
    if not exe_path.exists():
        print(f"Erreur: {exe_path} introuvable.")
        sys.exit(1)

    zip_path = DIST / "VoxWave-windows.zip"
    print(f"Packaging {zip_path}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_path, "VoxWave.exe")
        for extra in ["config.yaml", ".env.example"]:
            src = ROOT / extra
            if src.exists():
                zf.write(src, extra)
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Package cree: {zip_path} ({size_mb:.1f} MB)")


def _create_placeholder_icon(path: Path) -> None:
    """Genere une icone PNG placeholder."""
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([32, 32, 224, 224], fill="#4cc9f0", outline="#1a1a2e", width=4)
        draw.text((80, 100), "VW", fill="#1a1a2e")
        img.save(str(path))
    except ImportError:
        # Pas de Pillow — skip l'icone
        pass


def build_installer_windows() -> None:
    """Compile l'installer Windows avec Inno Setup (ISCC)."""
    exe_path = DIST / "VoxWave.exe"
    if not exe_path.exists():
        print(f"Erreur: {exe_path} introuvable. Lancez 'python build.py build' d'abord.")
        sys.exit(1)

    iss_path = ROOT / "installers" / "voxwave.iss"
    if not iss_path.exists():
        print(f"Erreur: {iss_path} introuvable.")
        sys.exit(1)

    # Chercher ISCC (Inno Setup Compiler)
    iscc = shutil.which("iscc") or shutil.which("ISCC")
    if not iscc:
        # Chemins Windows courants
        for candidate in [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
        ]:
            if os.path.exists(candidate):
                iscc = candidate
                break

    if not iscc:
        print(
            "ISCC (Inno Setup Compiler) non trouve.\n"
            "Installez Inno Setup 6 : https://jrsoftware.org/isdown.php\n"
            "Ou ajoutez ISCC.exe au PATH."
        )
        sys.exit(1)

    print("Creation installer Windows (Inno Setup)...")
    result = subprocess.run([iscc, str(iss_path)], cwd=str(ROOT))
    if result.returncode != 0:
        print("Erreur creation installer !")
        sys.exit(1)

    # Trouver le fichier genere
    for f in DIST.glob("VoxWave-Setup-*.exe"):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"Installer cree: {f} ({size_mb:.1f} MB)")
        break


def build(target_platform: str = None) -> None:
    """Build pour la plateforme cible.

    Args:
        target_platform: 'linux', 'windows', ou None (auto-detect).
    """
    if target_platform is None:
        target_platform = detect_platform()

    print(f"Build pour: {target_platform}")
    if target_platform == "linux":
        build_linux()
    elif target_platform == "windows":
        build_windows()
    elif target_platform == "darwin":
        # macOS utilise le meme flow que Windows (exe/app)
        build_pyinstaller()
    else:
        print(f"Plateforme non supportee: {target_platform}")
        sys.exit(1)


def main() -> None:
    """Point d'entree."""
    args = sys.argv[1:]

    if not args or args[0] == "build":
        target = None
        for i, arg in enumerate(args):
            if arg == "--platform" and i + 1 < len(args):
                target = args[i + 1]
        build(target)
    elif args[0] == "clean":
        clean()
    elif args[0] == "package":
        package_windows()
    elif args[0] == "installer":
        build_installer_windows()
    elif args[0] == "all":
        target = None
        for i, arg in enumerate(args):
            if arg == "--platform" and i + 1 < len(args):
                target = args[i + 1]
        clean()
        build(target)
        # Sur Windows, creer aussi l'installer Inno Setup
        if (target or detect_platform()) == "windows":
            build_installer_windows()
    else:
        print("Usage: python build.py [clean|build|package|installer|all] [--platform linux|windows]")
        sys.exit(1)


if __name__ == "__main__":
    main()
