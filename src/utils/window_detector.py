"""Détection de la fenêtre active pour le profil de nettoyage contextuel.

Retourne le profil de correction adapté à l'app courante :
"code" | "casual" | "email" | "document" | "default"
"""

import logging
import os
import subprocess
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# Mapping exe → profil de nettoyage
_APP_PROFILES: dict[str, str] = {
    # Éditeurs de code
    "code": "code",
    "cursor": "code",
    "windsurf": "code",
    "pycharm64": "code",
    "pycharm": "code",
    "idea64": "code",
    "idea": "code",
    "webstorm64": "code",
    "sublime_text": "code",
    "atom": "code",
    "notepad++": "code",
    "zed": "code",
    "fleet": "code",
    "lapce": "code",
    "emacs": "code",
    "vim": "code",
    "nvim": "code",
    # Terminaux
    "windowsterminal": "code",
    "cmd": "code",
    "powershell": "code",
    "pwsh": "code",
    "bash": "code",
    "zsh": "code",
    "fish": "code",
    "konsole": "code",
    "gnome-terminal": "code",
    "alacritty": "code",
    "wezterm": "code",
    "kitty": "code",
    "rio": "code",
    "ghostty": "code",
    # Messagerie (casual)
    "slack": "casual",
    "discord": "casual",
    "telegram": "casual",
    "whatsapp": "casual",
    "signal": "casual",
    "teams": "casual",
    "msteams": "casual",
    "zoom": "casual",
    # Email
    "outlook": "email",
    "thunderbird": "email",
    "mailspring": "email",
    "olk": "email",
    # Documents
    "winword": "document",
    "soffice": "document",
    "libreoffice": "document",
    "notion": "document",
    "obsidian": "document",
    "logseq": "document",
}


def get_app_profile(exe_name: Optional[str]) -> str:
    """Retourne le profil de nettoyage pour un nom d'exécutable.

    Args:
        exe_name: Nom de l'exécutable (avec ou sans .exe, majuscules ok).

    Returns:
        "code" | "casual" | "email" | "document" | "default"
    """
    if not exe_name:
        return "default"
    normalized = exe_name.lower().replace(".exe", "").replace(".app", "").strip()
    return _APP_PROFILES.get(normalized, "default")


def get_active_exe() -> str:
    """Retourne le nom de l'exécutable de la fenêtre active.

    Returns:
        Nom de l'exécutable (ex: "code.exe" sur Windows, "code" sur Linux).
        Chaîne vide en cas d'échec.
    """
    if sys.platform == "win32":
        return _get_active_exe_windows()
    elif sys.platform == "linux":
        return _get_active_exe_linux()
    return ""


def _get_active_exe_windows() -> str:
    """Détection Windows via ctypes (GetForegroundWindow + GetModuleFileNameExW)."""
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        handle = kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value
        )
        if not handle:
            return ""

        try:
            buf = ctypes.create_unicode_buffer(260)
            if psapi.GetModuleFileNameExW(handle, None, buf, 260):
                return os.path.basename(buf.value)
        finally:
            kernel32.CloseHandle(handle)

    except Exception as e:
        logger.debug(f"window_detector Windows: {e}")
    return ""


def _get_active_exe_linux() -> str:
    """Détection Linux : xdotool → /proc/pid/comm (fallback wnck)."""
    # Essai 1 : xdotool (X11)
    try:
        pid_bytes = subprocess.check_output(
            ["xdotool", "getactivewindow", "getwindowpid"],
            stderr=subprocess.DEVNULL,
            timeout=1,
        )
        pid = int(pid_bytes.decode().strip())
        with open(f"/proc/{pid}/comm") as f:
            return f.read().strip()
    except Exception:
        pass

    # Essai 2 : wnck (Wayland)
    try:
        import gi
        gi.require_version("Wnck", "3")
        from gi.repository import Wnck

        screen = Wnck.Screen.get_default()
        screen.force_update()
        window = screen.get_active_window()
        if window:
            pid = window.get_pid()
            with open(f"/proc/{pid}/comm") as f:
                return f.read().strip()
    except Exception:
        pass

    logger.debug("window_detector Linux: xdotool et wnck indisponibles")
    return ""
