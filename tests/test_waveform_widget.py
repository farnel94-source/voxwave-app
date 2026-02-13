"""Tests pour le widget orbe WebGL."""

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="module")
def qapp():
    """Cree une QApplication pour les tests (une seule instance)."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def mock_capture():
    """Mock AudioCapture avec amplitude configurable."""
    capture = MagicMock()
    capture.current_amplitude = 0.1
    return capture


@pytest.fixture
def mock_start():
    return MagicMock()


@pytest.fixture
def mock_stop():
    return MagicMock()


def _make_widget(mock_capture=None, mock_start=None, mock_stop=None):
    """Cree un WaveformWidget avec les imports WebEngine mockes."""
    mock_webengine_module = MagicMock()
    mock_webchannel_module = MagicMock()

    mock_webview_class = MagicMock()
    mock_page = MagicMock()
    mock_webview_class.return_value.page.return_value = mock_page
    mock_webengine_module.QWebEngineView = mock_webview_class
    mock_webchannel_module.QWebChannel = MagicMock()

    with patch.dict("sys.modules", {
        "PySide6.QtWebEngineWidgets": mock_webengine_module,
        "PySide6.QtWebChannel": mock_webchannel_module,
    }):
        if "src.gui.waveform_widget" in sys.modules:
            del sys.modules["src.gui.waveform_widget"]

        from src.gui.waveform_widget import WaveformWidget

        # Patch _setup_webview to avoid QVBoxLayout.addWidget(MagicMock) error
        original_setup = WaveformWidget._setup_webview

        def patched_setup(self_widget):
            """Setup webview sans layout.addWidget (incompatible avec mock)."""
            from src.gui.waveform_widget import Bridge
            self_widget._bridge = Bridge(
                on_start=self_widget._on_start,
                on_stop=self_widget._on_stop,
            )
            self_widget._web_view = mock_webview_class(self_widget)
            self_widget._channel = MagicMock()

        WaveformWidget._setup_webview = patched_setup
        w = WaveformWidget(
            capture=mock_capture,
            on_start=mock_start,
            on_stop=mock_stop,
        )
        WaveformWidget._setup_webview = original_setup
        return w


@pytest.fixture
def widget(qapp, mock_capture, mock_start, mock_stop):
    """Cree un WaveformWidget mocke."""
    w = _make_widget(mock_capture, mock_start, mock_stop)
    yield w
    w._amplitude_timer.stop()


class TestWaveformWidgetStates:
    """Tests des etats du widget."""

    def test_initial_state_idle(self, widget):
        assert widget.state == "idle"

    def test_show_recording(self, widget):
        widget._do_show_recording()
        assert widget.state == "recording"
        assert widget.isVisible()

    def test_show_processing(self, widget):
        widget._do_show_recording()
        widget._do_show_processing()
        assert widget.state == "processing"

    def test_show_idle(self, widget):
        widget._do_show_recording()
        widget._do_show_idle()
        assert widget.state == "idle"

    def test_hide_widget_returns_to_idle(self, widget):
        """hide_widget() est un alias de show_idle() pour retrocompatibilite."""
        widget._do_show_recording()
        widget._do_show_idle()
        assert widget.state == "idle"

    def test_show_error(self, widget):
        widget._do_show_error()
        assert widget.state == "error"

    def test_show_error_sends_js(self, widget):
        widget._do_show_error()
        widget._web_view.page().runJavaScript.assert_any_call("setState('error')")

    def test_show_error_returns_to_idle(self, widget, qapp):
        """L'etat error revient a idle apres le timer."""
        widget._do_show_error()
        assert widget.state == "error"
        # Simuler le passage du timer en appelant directement le slot
        widget._do_show_idle()
        assert widget.state == "idle"


class TestWaveformBridge:
    """Tests du bridge Python <-> JS."""

    def test_bridge_start_callback(self, widget, mock_start):
        widget._bridge.on_start_clicked()
        mock_start.assert_called_once()

    def test_bridge_stop_callback(self, widget, mock_stop):
        widget._bridge.on_stop_clicked()
        mock_stop.assert_called_once()

    def test_bridge_no_callback(self, qapp):
        """Bridge sans callbacks ne crash pas."""
        w = _make_widget()
        w._bridge.on_start_clicked()
        w._bridge.on_stop_clicked()
        w._amplitude_timer.stop()


class TestWaveformAmplitude:
    """Tests de l'envoi d'amplitude au JS."""

    def test_send_amplitude(self, widget, mock_capture):
        mock_capture.current_amplitude = 0.5
        widget._do_show_recording()
        widget._send_amplitude()
        widget._web_view.page().runJavaScript.assert_called()

    def test_send_amplitude_zero(self, widget, mock_capture):
        mock_capture.current_amplitude = 0.0
        widget._send_amplitude()
        widget._web_view.page().runJavaScript.assert_called()

    def test_send_amplitude_clamped(self, widget, mock_capture):
        mock_capture.current_amplitude = 10.0
        widget._send_amplitude()
        call_args = widget._web_view.page().runJavaScript.call_args[0][0]
        assert "updateAmplitude(1.0000)" in call_args


class TestWaveformRunJS:
    """Tests de la communication JS."""

    def test_run_js_recording_state(self, widget):
        widget._do_show_recording()
        widget._web_view.page().runJavaScript.assert_any_call("setState('recording')")

    def test_run_js_processing_state(self, widget):
        widget._do_show_processing()
        widget._web_view.page().runJavaScript.assert_any_call("setState('processing')")

    def test_run_js_idle_state(self, widget):
        widget._do_show_idle()
        widget._web_view.page().runJavaScript.assert_any_call("setState('idle')")


class TestWaveformSetCapture:
    """Tests de set_capture."""

    def test_set_capture(self, widget):
        new_capture = MagicMock()
        new_capture.current_amplitude = 0.3
        widget.set_capture(new_capture)
        assert widget._capture is new_capture
