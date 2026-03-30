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

    def test_paint_event_uses_offscreen_qimage(self):
        """paintEvent doit dessiner dans un QImage intermediaire, pas directement
        sur le widget.

        Qt doc: 'Only QPainter on QImage fully supports all composition modes.'
        Les QRadialGradient semi-transparents (aura 5 couches) ne se blendent pas
        correctement sur un widget paint device X11. La solution : render offscreen
        dans un QImage(Format_ARGB32_Premultiplied), puis drawImage sur le widget.
        C'est le meme pattern que _render_layered() sur Windows.
        """
        source = open("src/gui/orb_widget.py").read()
        import re
        paint_event_match = re.search(
            r"def paintEvent\(self.*?\n(.*?)(?=\n    def |\nclass |\Z)",
            source,
            re.DOTALL,
        )
        assert paint_event_match, "paintEvent not found"
        paint_body = paint_event_match.group(1)
        # Must create a QImage for offscreen rendering
        assert "QImage(" in paint_body, (
            "paintEvent() must render to an offscreen QImage (Format_ARGB32_Premultiplied) "
            "before drawing to the widget. Direct QPainter(self) does not support "
            "all composition modes on X11 — gradients and alpha blending break."
        )
        # Must use an ARGB32 format for correct alpha blending
        assert "Format_ARGB32" in paint_body, (
            "The offscreen QImage must use Format_ARGB32 or Format_ARGB32_Premultiplied "
            "for correct alpha blending."
        )
        # Must drawImage to copy result to widget
        assert "drawImage" in paint_body, (
            "paintEvent() must use drawImage() to copy the offscreen QImage to the widget."
        )
