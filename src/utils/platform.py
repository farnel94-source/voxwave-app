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
