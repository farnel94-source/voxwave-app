"""Verifie la detection plateforme et les outils disponibles."""

from src.utils.platform import get_display_server
import shutil

display = get_display_server()
print(f"Display server : {display}")
print(f"xdotool        : {'OK' if shutil.which('xdotool') else 'MANQUANT'}")
print(f"wtype          : {'OK' if shutil.which('wtype') else 'MANQUANT'}")
print(f"wl-copy        : {'OK' if shutil.which('wl-copy') else 'MANQUANT'}")
print(f"xclip          : {'OK' if shutil.which('xclip') else 'MANQUANT'}")

try:
    import evdev
    devices = evdev.list_devices()
    print(f"evdev          : OK ({len(devices)} devices)")
except ImportError:
    print("evdev          : NON INSTALLE")
except PermissionError:
    print("evdev          : PERMISSION REFUSEE (ajoutez l'user au groupe 'input')")
