"""Script de build automatisé pour VoxTool.

Usage:
    python build.py          # Build seulement
    python build.py clean    # Nettoie les artefacts
    python build.py all      # Clean + Build + Package (ZIP)
"""

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "voxtool.spec"


def clean() -> None:
    """Supprime les artefacts de build."""
    for d in [DIST, BUILD]:
        if d.exists():
            print(f"Suppression {d}...")
            shutil.rmtree(d)
    print("Clean terminé.")


def build() -> None:
    """Lance PyInstaller."""
    print("Build VoxTool...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC),
        "--noconfirm",
        "--clean",
    ]
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print("Build échoué !")
        sys.exit(1)
    print("Build terminé.")


def package() -> None:
    """Crée un ZIP de distribution."""
    exe_path = DIST / "VoxTool.exe"
    if not exe_path.exists():
        print(f"Erreur: {exe_path} introuvable. Lancez d'abord 'python build.py' ou 'python build.py all'.")
        sys.exit(1)

    zip_path = DIST / "VoxTool-windows.zip"
    print(f"Packaging {zip_path}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_path, "VoxTool.exe")
        # Inclure config et .env.example
        for extra in ["config.yaml", ".env.example"]:
            src = ROOT / extra
            if src.exists():
                zf.write(src, extra)
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Package créé: {zip_path} ({size_mb:.1f} MB)")


def main() -> None:
    """Point d'entrée."""
    args = sys.argv[1:]

    if not args or args[0] == "build":
        build()
    elif args[0] == "clean":
        clean()
    elif args[0] == "package":
        package()
    elif args[0] == "all":
        clean()
        build()
        package()
    else:
        print(f"Usage: python build.py [clean|build|package|all]")
        sys.exit(1)


if __name__ == "__main__":
    main()
