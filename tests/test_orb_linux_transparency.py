"""Test: OrbWidget Linux — pas de fond opaque, transparence native."""
import inspect
import pytest


class TestLinuxTransparencyFix:
    """Sur Linux, le widget doit être transparent nativement.
    Pas de WA_OpaquePaintEvent, pas de fond opaque, pas de masque."""

    def test_no_opaque_paint_event(self):
        """WA_OpaquePaintEvent ne doit JAMAIS être utilisé (conflit avec transparence)."""
        source = open("src/gui/orb_widget.py").read()
        assert "WA_OpaquePaintEvent" not in source, (
            "WA_OpaquePaintEvent entre en conflit avec WA_TranslucentBackground"
        )

    def test_no_opaque_background(self):
        """Pas de fond opaque peint sur Linux."""
        source = open("src/gui/orb_widget.py").read()
        assert "_paint_linux_background" not in source, (
            "Le fond opaque ne doit pas être peint — la transparence native suffit"
        )

    def test_no_linux_mask(self):
        """Pas de masque QRegion — la transparence native gère les contours."""
        source = open("src/gui/orb_widget.py").read()
        assert "_apply_linux_mask" not in source, (
            "Le masque QRegion n'est pas nécessaire avec la transparence native"
        )

    def test_translucent_background_set(self):
        """WA_TranslucentBackground doit être activé sur Linux."""
        source = open("src/gui/orb_widget.py").read()
        assert "WA_TranslucentBackground" in source

    def test_no_system_background_set(self):
        """WA_NoSystemBackground doit être activé pour empêcher le fond système."""
        source = open("src/gui/orb_widget.py").read()
        assert "WA_NoSystemBackground" in source

    def test_no_xprop_dependency(self):
        """Pas de dépendance à xprop (pas installé par défaut sur Linux Mint)."""
        source = open("src/gui/orb_widget.py").read()
        assert "xprop" not in source
        assert "import subprocess" not in source
