"""Detection du serveur d'affichage et de la plateforme."""

import os
import sys


def resource_path(relative_path: str) -> str:
    """Retourne le chemin absolu vers une ressource, compatible PyInstaller.

    En mode PyInstaller (frozen), les fichiers datas sont extraits dans
    sys._MEIPASS. En mode developpement, on utilise le chemin relatif
    depuis la racine du projet.

    Args:
        relative_path: Chemin relatif depuis la racine du projet.

    Returns:
        Chemin absolu vers la ressource.
    """
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)


def user_config_path() -> str:
    """Retourne le chemin vers le config.yaml utilisateur (lecture/ecriture).

    - Dev (non frozen) : config.yaml a la racine du projet
    - Linux frozen : ~/.config/voxwave/config.yaml (XDG)
    - Windows frozen : %APPDATA%/VoxWave/config.yaml

    Au premier lancement frozen, copie le config.yaml du bundle.
    """
    import shutil

    if not getattr(sys, "frozen", False):
        return resource_path("config.yaml")

    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        config_dir = os.path.join(base, "VoxWave")
    else:
        xdg = os.environ.get(
            "XDG_CONFIG_HOME",
            os.path.join(os.path.expanduser("~"), ".config"),
        )
        config_dir = os.path.join(xdg, "voxwave")

    config_file = os.path.join(config_dir, "config.yaml")

    if not os.path.exists(config_file):
        os.makedirs(config_dir, exist_ok=True)
        bundled = resource_path("config.yaml")
        if os.path.exists(bundled):
            shutil.copy2(bundled, config_file)

    return config_file


def get_display_server() -> str:
    """Retourne le type de serveur d'affichage.

    Returns:
        'wayland', 'x11', 'windows', 'darwin', ou 'unknown'.
    """
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "darwin"
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session == "wayland":
        return "wayland"
    if session == "x11" or os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"
