"""Dialogue de parametres VoxWave — UI moderne inspiree Wispr/Aqua."""

import logging
import os
import sys
from typing import Optional

from src.config.defaults import WHISPER_LANGUAGES

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QPushButton,
)

logger = logging.getLogger(__name__)

# ====================================================================
# Traductions Settings Dialog (en + fr)
# ====================================================================

_SETTINGS_T = {
    "en": {
        "title": "Settings",
        "nav_general": "General",
        "nav_audio": "Audio",
        "nav_writing": "Writing",
        "nav_account": "Account",
        "label_hotkey": "Keyboard shortcut",
        "hint_hotkey": "Click then press your combo (e.g. F8, Ctrl+Shift+V)",
        "label_interface_lang": "Interface language",
        "hint_interface_lang": "Changes menus and interface language",
        "label_dictation_lang": "Dictation language",
        "hint_dictation_lang": "Language used for voice recognition",
        "label_activation": "Activation method",
        "hint_activation": "How to start/stop dictation",
        "activation_hotkey": "Keyboard shortcut only",
        "activation_icon": "VoxWave icon only",
        "activation_both": "Both (keyboard + icon)",
        "section_writing": "WRITING MODE",
        "desc_writing": "How should VoxWave clean your dictations?",
        "tone_raw": "Raw",
        "tone_raw_desc": "No processing, exact transcription",
        "tone_auto": "Auto",
        "tone_auto_desc": "Detects the application and adapts automatically",
        "section_audio": "AUDIO DEVICE",
        "label_mic": "Microphone",
        "hint_mic": "Select the microphone to use for dictation",
        "label_auto_stop": "Auto-stop",
        "hint_auto_stop": "Automatically stop recording after silence",
        "label_auto_stop_duration": "Silence duration (seconds)",
        "hint_auto_stop_duration": "Stop recording after this many seconds of silence",
        "btn_close": "Save",
        "section_advanced": "ADVANCED",
        "label_trans_provider": "Transcription",
        "label_clean_provider": "Cleaning",
        "label_ollama_host": "Ollama address",
        "hint_ollama_host": "Change if Ollama runs on a different port",
        "section_help": "HELP",
        "help_shortcut_label": "Current shortcut:",
        "help_how_title": "How it works",
        "help_how_text": (
            "1. Press shortcut to start dictating\n"
            "2. Speak into your mic\n"
            "3. Press again to stop\n"
            "4. Clean text is pasted automatically"
        ),
        "help_report_title": "Report an issue",
        "help_report_hint": "Contact us: support@voxwave.app",
        "help_open_logs": "Open logs folder",
        "section_telemetry": "TELEMETRY",
        "label_telemetry": "Usage telemetry",
        "hint_telemetry": "Sends anonymous stats (dictation count, session duration). No dictated text is sent.",
    },
    "fr": {
        "title": "Parametres",
        "nav_general": "General",
        "nav_audio": "Audio",
        "nav_writing": "Ecriture",
        "nav_account": "Compte",
        "label_hotkey": "Raccourci clavier",
        "hint_hotkey": "Cliquez puis appuyez sur la combinaison souhaitee (ex: F8, Ctrl+Shift+V)",
        "label_interface_lang": "Langue de l'interface",
        "hint_interface_lang": "Change la langue des menus et de l'interface",
        "label_dictation_lang": "Langue de dictee",
        "hint_dictation_lang": "Langue utilisee pour la reconnaissance vocale",
        "label_activation": "Methode d'activation",
        "hint_activation": "Comment demarrer/arreter la dictee",
        "activation_hotkey": "Raccourci clavier uniquement",
        "activation_icon": "Icone VoxWave uniquement",
        "activation_both": "Les deux (clavier + icone)",
        "section_writing": "MODE D'ECRITURE",
        "desc_writing": "Comment VoxWave doit nettoyer vos dictees ?",
        "tone_raw": "Brut",
        "tone_raw_desc": "Aucun traitement, texte exact de la transcription",
        "tone_auto": "Auto",
        "tone_auto_desc": "Détecte l'application et adapte automatiquement",
        "section_audio": "PERIPHERIQUE AUDIO",
        "label_mic": "Microphone",
        "hint_mic": "Selectionnez le micro a utiliser pour la dictee",
        "label_auto_stop": "Arret auto",
        "hint_auto_stop": "Arreter automatiquement l'enregistrement apres un silence",
        "label_auto_stop_duration": "Duree de silence (secondes)",
        "hint_auto_stop_duration": "Arreter apres ce nombre de secondes de silence",
        "btn_close": "Sauvegarder",
        "section_advanced": "AVANCE",
        "label_trans_provider": "Transcription",
        "label_clean_provider": "Nettoyage",
        "label_ollama_host": "Adresse Ollama",
        "hint_ollama_host": "Modifier si Ollama tourne sur un autre port",
        "section_help": "AIDE",
        "help_shortcut_label": "Raccourci actuel :",
        "help_how_title": "Comment ca marche",
        "help_how_text": (
            "1. Appuyez sur le raccourci pour commencer a dicter\n"
            "2. Parlez normalement dans votre micro\n"
            "3. Appuyez a nouveau pour arreter\n"
            "4. Le texte nettoye est colle automatiquement"
        ),
        "help_report_title": "Signaler un probleme",
        "help_report_hint": "Contactez-nous : support@voxwave.app",
        "help_open_logs": "Ouvrir le dossier logs",
        "section_telemetry": "TELEMETRIE",
        "label_telemetry": "Telemetrie d'usage",
        "hint_telemetry": "Envoie des statistiques anonymes (nombre de dictees, duree de session). Aucun texte dicte n'est envoye.",
    },
    "es": {
        "title": "Configuracion",
        "nav_general": "General", "nav_audio": "Audio",
        "nav_writing": "Escritura", "nav_account": "Cuenta",
        "label_hotkey": "Atajo de teclado",
        "hint_hotkey": "Haga clic y presione la combinacion (ej: F8, Ctrl+Shift+V)",
        "label_interface_lang": "Idioma de la interfaz",
        "hint_interface_lang": "Cambia el idioma de los menus",
        "label_dictation_lang": "Idioma de dictado",
        "hint_dictation_lang": "Idioma usado para el reconocimiento de voz",
        "label_activation": "Metodo de activacion",
        "hint_activation": "Como iniciar/detener el dictado",
        "activation_hotkey": "Solo atajo de teclado",
        "activation_icon": "Solo icono VoxWave",
        "activation_both": "Ambos (teclado + icono)",
        "section_writing": "MODO DE ESCRITURA",
        "desc_writing": "Como debe limpiar VoxWave sus dictados?",
        "tone_raw": "Bruto", "tone_raw_desc": "Sin procesamiento, transcripcion exacta",
        "tone_auto": "Auto", "tone_auto_desc": "Detecta la aplicacion y adapta automaticamente",
        "section_audio": "DISPOSITIVO DE AUDIO",
        "label_mic": "Microfono",
        "hint_mic": "Seleccione el microfono para el dictado",
        "label_auto_stop": "Parada automatica",
        "hint_auto_stop": "Detener la grabacion automaticamente despues del silencio",
        "label_auto_stop_duration": "Duracion del silencio (segundos)",
        "hint_auto_stop_duration": "Detener despues de este numero de segundos de silencio",
        "btn_close": "Guardar",
        "section_advanced": "AVANZADO",
        "label_trans_provider": "Transcripcion",
        "label_clean_provider": "Limpieza",
        "label_ollama_host": "Direccion Ollama",
        "hint_ollama_host": "Cambiar si Ollama usa un puerto diferente",
        "section_help": "AYUDA",
        "help_shortcut_label": "Atajo actual:",
        "help_how_title": "Como funciona",
        "help_how_text": (
            "1. Presiona el atajo para dictar\n"
            "2. Habla al microfono\n"
            "3. Presiona de nuevo para parar\n"
            "4. El texto limpio se pega automaticamente"
        ),
        "help_report_title": "Reportar un problema",
        "help_report_hint": "Contactenos: support@voxwave.app",
        "help_open_logs": "Abrir carpeta de logs",
        "section_telemetry": "TELEMETRIA",
        "label_telemetry": "Telemetria de uso",
        "hint_telemetry": "Envia estadisticas anonimas (conteo de dictados, duracion de sesion). No se envia texto dictado.",
    },
    "de": {
        "title": "Einstellungen",
        "nav_general": "Allgemein", "nav_audio": "Audio",
        "nav_writing": "Schreiben", "nav_account": "Konto",
        "label_hotkey": "Tastenkurzel",
        "hint_hotkey": "Klicken und Kombination drucken (z.B. F8, Strg+Umschalt+V)",
        "label_interface_lang": "Oberflachensprache",
        "hint_interface_lang": "Andert die Sprache der Menus",
        "label_dictation_lang": "Diktiersprache",
        "hint_dictation_lang": "Sprache fur die Spracherkennung",
        "label_activation": "Aktivierungsmethode",
        "hint_activation": "Wie Diktat starten/stoppen",
        "activation_hotkey": "Nur Tastenkurzel",
        "activation_icon": "Nur VoxWave Symbol",
        "activation_both": "Beides (Tastatur + Symbol)",
        "section_writing": "SCHREIBMODUS",
        "desc_writing": "Wie soll VoxWave Ihre Diktate bereinigen?",
        "tone_raw": "Roh", "tone_raw_desc": "Keine Verarbeitung, genaue Transkription",
        "tone_auto": "Auto", "tone_auto_desc": "Erkennt die App und passt sich automatisch an",
        "section_audio": "AUDIOGERAET",
        "label_mic": "Mikrofon",
        "hint_mic": "Wahlen Sie das Mikrofon fur das Diktat",
        "label_auto_stop": "Automatisch stoppen",
        "hint_auto_stop": "Aufnahme nach Stille automatisch stoppen",
        "label_auto_stop_duration": "Stille-Dauer (Sekunden)",
        "hint_auto_stop_duration": "Stoppen nach dieser Anzahl Sekunden Stille",
        "btn_close": "Speichern",
        "section_advanced": "ERWEITERT",
        "label_trans_provider": "Transkription",
        "label_clean_provider": "Bereinigung",
        "label_ollama_host": "Ollama-Adresse",
        "hint_ollama_host": "Andern wenn Ollama auf einem anderen Port lauft",
        "section_help": "HILFE",
        "help_shortcut_label": "Aktuelles Kurzel:",
        "help_how_title": "So funktioniert es",
        "help_how_text": (
            "1. Kurzel drucken um zu diktieren\n"
            "2. In Mikrofon sprechen\n"
            "3. Erneut drucken um zu stoppen\n"
            "4. Bereinigter Text wird eingefugt"
        ),
        "help_report_title": "Problem melden",
        "help_report_hint": "Kontakt: support@voxwave.app",
        "help_open_logs": "Log-Ordner offnen",
        "section_telemetry": "TELEMETRIE",
        "label_telemetry": "Nutzungstelemetrie",
        "hint_telemetry": "Sendet anonyme Statistiken (Anzahl Diktate, Sitzungsdauer). Kein diktierter Text wird gesendet.",
    },
    "it": {
        "title": "Impostazioni",
        "nav_general": "Generale", "nav_audio": "Audio",
        "nav_writing": "Scrittura", "nav_account": "Account",
        "label_hotkey": "Scorciatoia tastiera",
        "hint_hotkey": "Clicca e premi la combinazione (es: F8, Ctrl+Shift+V)",
        "label_interface_lang": "Lingua interfaccia",
        "hint_interface_lang": "Cambia la lingua dei menu",
        "label_dictation_lang": "Lingua di dettatura",
        "hint_dictation_lang": "Lingua per il riconoscimento vocale",
        "label_activation": "Metodo di attivazione",
        "hint_activation": "Come avviare/fermare la dettatura",
        "activation_hotkey": "Solo scorciatoia tastiera",
        "activation_icon": "Solo icona VoxWave",
        "activation_both": "Entrambi (tastiera + icona)",
        "section_writing": "MODALITA DI SCRITTURA",
        "desc_writing": "Come deve pulire VoxWave i tuoi dettati?",
        "tone_raw": "Grezzo", "tone_raw_desc": "Nessuna elaborazione, trascrizione esatta",
        "tone_auto": "Auto", "tone_auto_desc": "Rileva l'app e si adatta automaticamente",
        "section_audio": "DISPOSITIVO AUDIO",
        "label_mic": "Microfono",
        "hint_mic": "Seleziona il microfono per la dettatura",
        "label_auto_stop": "Stop automatico",
        "hint_auto_stop": "Ferma automaticamente la registrazione dopo il silenzio",
        "label_auto_stop_duration": "Durata silenzio (secondi)",
        "hint_auto_stop_duration": "Ferma dopo questi secondi di silenzio",
        "btn_close": "Salva",
        "section_advanced": "AVANZATE",
        "label_trans_provider": "Trascrizione",
        "label_clean_provider": "Pulizia",
        "label_ollama_host": "Indirizzo Ollama",
        "hint_ollama_host": "Modifica se Ollama usa una porta diversa",
        "section_help": "AIUTO",
        "help_shortcut_label": "Scorciatoia attuale:",
        "help_how_title": "Come funziona",
        "help_how_text": (
            "1. Premi la scorciatoia per dettare\n"
            "2. Parla al microfono\n"
            "3. Premi di nuovo per fermare\n"
            "4. Il testo pulito viene incollato"
        ),
        "help_report_title": "Segnala un problema",
        "help_report_hint": "Contattaci: support@voxwave.app",
        "help_open_logs": "Apri cartella log",
        "section_telemetry": "TELEMETRIA",
        "label_telemetry": "Telemetria di utilizzo",
        "hint_telemetry": "Invia statistiche anonime (conteggio dettature, durata sessione). Nessun testo dettato viene inviato.",
    },
    "pt": {
        "title": "Configuracoes",
        "nav_general": "Geral", "nav_audio": "Audio",
        "nav_writing": "Escrita", "nav_account": "Conta",
        "label_hotkey": "Atalho de teclado",
        "hint_hotkey": "Clique e pressione a combinacao (ex: F8, Ctrl+Shift+V)",
        "label_interface_lang": "Idioma da interface",
        "hint_interface_lang": "Altera o idioma dos menus",
        "label_dictation_lang": "Idioma de ditado",
        "hint_dictation_lang": "Idioma usado para reconhecimento de voz",
        "label_activation": "Metodo de ativacao",
        "hint_activation": "Como iniciar/parar o ditado",
        "activation_hotkey": "Somente atalho de teclado",
        "activation_icon": "Somente icone VoxWave",
        "activation_both": "Ambos (teclado + icone)",
        "section_writing": "MODO DE ESCRITA",
        "desc_writing": "Como o VoxWave deve limpar seus ditados?",
        "tone_raw": "Bruto", "tone_raw_desc": "Sem processamento, transcricao exata",
        "tone_auto": "Auto", "tone_auto_desc": "Detecta o aplicativo e adapta automaticamente",
        "section_audio": "DISPOSITIVO DE AUDIO",
        "label_mic": "Microfone",
        "hint_mic": "Selecione o microfone para o ditado",
        "label_auto_stop": "Parada automatica",
        "hint_auto_stop": "Parar automaticamente a gravacao apos silencio",
        "label_auto_stop_duration": "Duracao do silencio (segundos)",
        "hint_auto_stop_duration": "Parar apos este numero de segundos de silencio",
        "btn_close": "Salvar",
        "section_advanced": "AVANCADO",
        "label_trans_provider": "Transcricao",
        "label_clean_provider": "Limpeza",
        "label_ollama_host": "Endereco Ollama",
        "hint_ollama_host": "Alterar se Ollama usar uma porta diferente",
        "section_help": "AJUDA",
        "help_shortcut_label": "Atalho atual:",
        "help_how_title": "Como funciona",
        "help_how_text": (
            "1. Pressione o atalho para ditar\n"
            "2. Fale no microfone\n"
            "3. Pressione novamente para parar\n"
            "4. O texto limpo e colado automaticamente"
        ),
        "help_report_title": "Reportar um problema",
        "help_report_hint": "Contato: support@voxwave.app",
        "help_open_logs": "Abrir pasta de logs",
        "section_telemetry": "TELEMETRIA",
        "label_telemetry": "Telemetria de uso",
        "hint_telemetry": "Envia estatisticas anonimas (contagem de ditados, duracao da sessao). Nenhum texto ditado e enviado.",
    },
    "nl": {
        "title": "Instellingen",
        "nav_general": "Algemeen", "nav_audio": "Audio",
        "nav_writing": "Schrijven", "nav_account": "Account",
        "label_hotkey": "Sneltoets",
        "hint_hotkey": "Klik en druk op combinatie (bijv. F8, Ctrl+Shift+V)",
        "label_interface_lang": "Interfacetaal",
        "hint_interface_lang": "Verandert de taal van de menus",
        "label_dictation_lang": "Dicteertaal",
        "hint_dictation_lang": "Taal voor spraakherkenning",
        "label_activation": "Activeringsmethode",
        "hint_activation": "Hoe dicteren te starten/stoppen",
        "activation_hotkey": "Alleen sneltoets",
        "activation_icon": "Alleen VoxWave icoon",
        "activation_both": "Beide (toetsenbord + icoon)",
        "section_writing": "SCHRIJFMODUS",
        "desc_writing": "Hoe moet VoxWave uw dictaten verwerken?",
        "tone_raw": "Rauw", "tone_raw_desc": "Geen verwerking, exacte transcriptie",
        "tone_auto": "Auto", "tone_auto_desc": "Detecteert de app en past automatisch aan",
        "section_audio": "AUDIOAPPARAAT",
        "label_mic": "Microfoon",
        "hint_mic": "Selecteer de microfoon voor dicteren",
        "label_auto_stop": "Automatisch stoppen",
        "hint_auto_stop": "Opname automatisch stoppen na stilte",
        "label_auto_stop_duration": "Stilteduur (seconden)",
        "hint_auto_stop_duration": "Stoppen na dit aantal seconden stilte",
        "btn_close": "Opslaan",
        "section_advanced": "GEAVANCEERD",
        "label_trans_provider": "Transcriptie",
        "label_clean_provider": "Verwerking",
        "label_ollama_host": "Ollama-adres",
        "hint_ollama_host": "Wijzig als Ollama op een andere poort draait",
        "section_help": "HELP",
        "help_shortcut_label": "Huidige sneltoets:",
        "help_how_title": "Hoe het werkt",
        "help_how_text": (
            "1. Druk op sneltoets om te dicteren\n"
            "2. Spreek in uw microfoon\n"
            "3. Druk opnieuw om te stoppen\n"
            "4. Schone tekst wordt automatisch geplakt"
        ),
        "help_report_title": "Probleem melden",
        "help_report_hint": "Contact: support@voxwave.app",
        "help_open_logs": "Open logmap",
        "section_telemetry": "TELEMETRIE",
        "label_telemetry": "Gebruikstelemetrie",
        "hint_telemetry": "Stuurt anonieme statistieken (aantal dictaten, sessieduur). Er wordt geen gedicteerde tekst verzonden.",
    },
    "ja": {
        "title": "設定",
        "nav_general": "一般", "nav_audio": "音声",
        "nav_writing": "書き方", "nav_account": "アカウント",
        "label_hotkey": "ショートカットキー",
        "hint_hotkey": "クリックしてキーを押す (例: F8, Ctrl+Shift+V)",
        "label_interface_lang": "表示言語",
        "hint_interface_lang": "メニューの言語を変更",
        "label_dictation_lang": "音声入力言語",
        "hint_dictation_lang": "音声認識に使用する言語",
        "label_activation": "起動方法",
        "hint_activation": "ディクテーションの開始/停止方法",
        "activation_hotkey": "ショートカットキーのみ",
        "activation_icon": "VoxWaveアイコンのみ",
        "activation_both": "両方 (キーボード + アイコン)",
        "section_writing": "書き方モード",
        "desc_writing": "VoxWaveはどのようにテキストを整理しますか？",
        "tone_raw": "そのまま", "tone_raw_desc": "処理なし、正確な書き起こし",
        "tone_auto": "自動", "tone_auto_desc": "アプリを検出して自動的に適応",
        "section_audio": "音声デバイス",
        "label_mic": "マイク",
        "hint_mic": "ディクテーションに使用するマイクを選択",
        "label_auto_stop": "自動停止",
        "hint_auto_stop": "無音後に録音を自動停止",
        "label_auto_stop_duration": "無音時間（秒）",
        "hint_auto_stop_duration": "この秒数の無音後に停止",
        "btn_close": "保存",
        "section_advanced": "詳細設定",
        "label_trans_provider": "文字起こし",
        "label_clean_provider": "クリーニング",
        "label_ollama_host": "Ollamaアドレス",
        "hint_ollama_host": "Ollamaが別ポートで動く場合は変更",
        "section_help": "ヘルプ",
        "help_shortcut_label": "現在のショートカット:",
        "help_how_title": "使い方",
        "help_how_text": (
            "1. ショートカットを押してディクテーション開始\n"
            "2. マイクに話しかける\n"
            "3. 再度押して停止\n"
            "4. 整理されたテキストが自動で貼り付けられる"
        ),
        "help_report_title": "問題を報告",
        "help_report_hint": "お問い合わせ: support@voxwave.app",
        "help_open_logs": "ログフォルダを開く",
        "section_telemetry": "テレメトリー",
        "label_telemetry": "利用テレメトリー",
        "hint_telemetry": "匿名の統計情報（音声入力回数、セッション時間）を送信します。入力テキストは送信されません。",
    },
    "ko": {
        "title": "설정",
        "nav_general": "일반", "nav_audio": "오디오",
        "nav_writing": "작성", "nav_account": "계정",
        "label_hotkey": "단축키",
        "hint_hotkey": "클릭 후 단축키 입력 (예: F8, Ctrl+Shift+V)",
        "label_interface_lang": "인터페이스 언어",
        "hint_interface_lang": "메뉴 언어 변경",
        "label_dictation_lang": "받아쓰기 언어",
        "hint_dictation_lang": "음성 인식에 사용할 언어",
        "label_activation": "활성화 방법",
        "hint_activation": "받아쓰기 시작/중지 방법",
        "activation_hotkey": "단축키만 사용",
        "activation_icon": "VoxWave 아이콘만 사용",
        "activation_both": "둘 다 (키보드 + 아이콘)",
        "section_writing": "작성 모드",
        "desc_writing": "VoxWave가 받아쓰기를 어떻게 정리할까요?",
        "tone_raw": "원본", "tone_raw_desc": "처리 없음, 정확한 전사",
        "tone_auto": "자동", "tone_auto_desc": "앱을 감지하여 자동으로 적응",
        "section_audio": "오디오 장치",
        "label_mic": "마이크",
        "hint_mic": "받아쓰기에 사용할 마이크 선택",
        "label_auto_stop": "자동 중지",
        "hint_auto_stop": "무음 후 자동으로 녹음 중지",
        "label_auto_stop_duration": "무음 시간(초)",
        "hint_auto_stop_duration": "이 초 동안 무음이면 중지",
        "btn_close": "저장",
        "section_advanced": "고급",
        "label_trans_provider": "전사",
        "label_clean_provider": "정리",
        "label_ollama_host": "Ollama 주소",
        "hint_ollama_host": "Ollama가 다른 포트에서 실행될 경우 변경",
        "section_help": "도움말",
        "help_shortcut_label": "현재 단축키:",
        "help_how_title": "사용 방법",
        "help_how_text": (
            "1. 단축키를 눌러 받아쓰기 시작\n"
            "2. 마이크에 말하기\n"
            "3. 다시 눌러 중지\n"
            "4. 정리된 텍스트가 자동으로 붙여넣기"
        ),
        "help_report_title": "문제 신고",
        "help_report_hint": "문의: support@voxwave.app",
        "help_open_logs": "로그 폴더 열기",
        "section_telemetry": "텔레메트리",
        "label_telemetry": "사용 텔레메트리",
        "hint_telemetry": "익명 통계(받아쓰기 횟수, 세션 시간)를 전송합니다. 받아쓴 텍스트는 전송되지 않습니다.",
    },
    "zh": {
        "title": "设置",
        "nav_general": "常规", "nav_audio": "音频",
        "nav_writing": "写作", "nav_account": "账户",
        "label_hotkey": "快捷键",
        "hint_hotkey": "点击后按下组合键 (例: F8, Ctrl+Shift+V)",
        "label_interface_lang": "界面语言",
        "hint_interface_lang": "更改菜单和界面语言",
        "label_dictation_lang": "听写语言",
        "hint_dictation_lang": "语音识别使用的语言",
        "label_activation": "激活方式",
        "hint_activation": "如何开始/停止听写",
        "activation_hotkey": "仅使用快捷键",
        "activation_icon": "仅使用VoxWave图标",
        "activation_both": "两者 (键盘 + 图标)",
        "section_writing": "写作模式",
        "desc_writing": "VoxWave应如何整理您的听写内容？",
        "tone_raw": "原始", "tone_raw_desc": "不处理，精确转录",
        "tone_auto": "自动", "tone_auto_desc": "检测应用并自动适应",
        "section_audio": "音频设备",
        "label_mic": "麦克风",
        "hint_mic": "选择用于听写的麦克风",
        "label_auto_stop": "自动停止",
        "hint_auto_stop": "静音后自动停止录音",
        "label_auto_stop_duration": "静音时长（秒）",
        "hint_auto_stop_duration": "静音持续此秒数后停止",
        "btn_close": "保存",
        "section_advanced": "高级",
        "label_trans_provider": "转录",
        "label_clean_provider": "清理",
        "label_ollama_host": "Ollama地址",
        "hint_ollama_host": "如果Ollama使用其他端口请更改",
        "section_help": "帮助",
        "help_shortcut_label": "当前快捷键：",
        "help_how_title": "使用方法",
        "help_how_text": (
            "1. 按快捷键开始听写\n"
            "2. 对麦克风说话\n"
            "3. 再次按下停止\n"
            "4. 整理后的文本自动粘贴"
        ),
        "help_report_title": "报告问题",
        "help_report_hint": "联系我们: support@voxwave.app",
        "help_open_logs": "打开日志文件夹",
        "section_telemetry": "遥测",
        "label_telemetry": "使用遥测",
        "hint_telemetry": "发送匿名统计数据（听写次数、会话时长）。不会发送听写文本。",
    },
    "ru": {
        "title": "Nastrojki",
        "nav_general": "Obshie", "nav_audio": "Audio",
        "nav_writing": "Pismo", "nav_account": "Akkaunt",
        "label_hotkey": "Gorjachaja klavisha",
        "hint_hotkey": "Nazhмite i vvedite kombinaciju (napr. F8, Ctrl+Shift+V)",
        "label_interface_lang": "Jazyk interfejsa",
        "hint_interface_lang": "Менjaet jazyk menyu i interfejsa",
        "label_dictation_lang": "Jazyk diktovki",
        "hint_dictation_lang": "Jazyk dlja raspoznavanija rechi",
        "label_activation": "Metod aktivacii",
        "hint_activation": "Kak nachat/ostanovit diktovku",
        "activation_hotkey": "Tolko gorjachaja klavisha",
        "activation_icon": "Tolko ikonka VoxWave",
        "activation_both": "Oba (klaviatura + ikonka)",
        "section_writing": "REZHIM NAPISANIJA",
        "desc_writing": "Kak VoxWave dolzhen obrabatyvat vashi diktovki?",
        "tone_raw": "Syroj", "tone_raw_desc": "Bez obrabotki, tochnaja transkriptsija",
        "tone_auto": "Avto", "tone_auto_desc": "Opredeljaet prilozhenie i adaptiruetsja avtomaticheski",
        "section_audio": "AUDIOUSTROJSTVO",
        "label_mic": "Mikrofon",
        "hint_mic": "Vyberite mikrofon dlja diktovki",
        "label_auto_stop": "Avto-ostanovka",
        "hint_auto_stop": "Avtomaticheski ostanovit zapis posle tishiny",
        "label_auto_stop_duration": "Dlitelnost tishiny (sekundy)",
        "hint_auto_stop_duration": "Ostanovit posle etogo kolichestva sekund tishiny",
        "btn_close": "Sohranit",
        "section_advanced": "DOPOLNITELNO",
        "label_trans_provider": "Transkriptsija",
        "label_clean_provider": "Obrabotka",
        "label_ollama_host": "Adres Ollama",
        "hint_ollama_host": "Izmenite esli Ollama rabotaet na drugom porte",
        "section_help": "POMOSH",
        "help_shortcut_label": "Tekushij jarlik:",
        "help_how_title": "Kak eto rabotaet",
        "help_how_text": (
            "1. Nazhмite jarlik dlja nachala diktovki\n"
            "2. Govorite v mikrofon\n"
            "3. Nazhмite snova dlja ostanovki\n"
            "4. Chistyj tekst vstavljaetsja avtomaticheski"
        ),
        "help_report_title": "Soobshit o probleme",
        "help_report_hint": "Kontakt: support@voxwave.app",
        "help_open_logs": "Otkrit papku logov",
        "section_telemetry": "ТЕЛЕМЕТРИЯ",
        "label_telemetry": "Телеметрия использования",
        "hint_telemetry": "Отправляет анонимную статистику (количество диктовок, длительность сессии). Текст диктовки не отправляется.",
    },
    "ar": {
        "title": "الإعدادات",
        "nav_general": "عام", "nav_audio": "الصوت",
        "nav_writing": "الكتابة", "nav_account": "الحساب",
        "label_hotkey": "اختصار لوحة المفاتيح",
        "hint_hotkey": "انقر ثم اضغط المفاتيح (مثال: F8, Ctrl+Shift+V)",
        "label_interface_lang": "لغة الواجهة",
        "hint_interface_lang": "يغير لغة القوائم والواجهة",
        "label_dictation_lang": "لغة الإملاء",
        "hint_dictation_lang": "اللغة المستخدمة للتعرف على الصوت",
        "label_activation": "طريقة التفعيل",
        "hint_activation": "كيفية بدء/إيقاف الإملاء",
        "activation_hotkey": "اختصار لوحة المفاتيح فقط",
        "activation_icon": "أيقونة VoxWave فقط",
        "activation_both": "كلاهما (لوحة المفاتيح + الأيقونة)",
        "section_writing": "وضع الكتابة",
        "desc_writing": "كيف يجب أن يعالج VoxWave إملاءاتك؟",
        "tone_raw": "خام", "tone_raw_desc": "بدون معالجة، نسخ دقيق",
        "tone_auto": "تلقائي", "tone_auto_desc": "يكتشف التطبيق ويتكيف تلقائيًا",
        "section_audio": "جهاز الصوت",
        "label_mic": "الميكروفون",
        "hint_mic": "اختر الميكروفون للإملاء",
        "label_auto_stop": "إيقاف تلقائي",
        "hint_auto_stop": "إيقاف التسجيل تلقائيًا بعد الصمت",
        "label_auto_stop_duration": "مدة الصمت (ثوانٍ)",
        "hint_auto_stop_duration": "إيقاف بعد هذا العدد من ثواني الصمت",
        "btn_close": "حفظ",
        "section_advanced": "متقدم",
        "label_trans_provider": "النسخ",
        "label_clean_provider": "التنظيف",
        "label_ollama_host": "عنوان Ollama",
        "hint_ollama_host": "غير اذا كان Ollama يعمل على منفذ اخر",
        "section_help": "المساعدة",
        "help_shortcut_label": "الاختصار الحالي:",
        "help_how_title": "كيف يعمل",
        "help_how_text": (
            "1. اضغط الاختصار لبدء الإملاء\n"
            "2. تحدث في الميكروفون\n"
            "3. اضغط مرة أخرى للإيقاف\n"
            "4. يتم لصق النص تلقائياً"
        ),
        "help_report_title": "الإبلاغ عن مشكلة",
        "help_report_hint": "تواصل معنا: support@voxwave.app",
        "help_open_logs": "فتح مجلد السجلات",
        "section_telemetry": "القياس عن بعد",
        "label_telemetry": "قياس الاستخدام",
        "hint_telemetry": "يرسل إحصائيات مجهولة (عدد الإملاءات، مدة الجلسة). لا يتم إرسال النص المُملى.",
    },
    "tr": {
        "title": "Ayarlar",
        "nav_general": "Genel", "nav_audio": "Ses",
        "nav_writing": "Yazma", "nav_account": "Hesap",
        "label_hotkey": "Klavye kisayolu",
        "hint_hotkey": "Tiklayip kombinasyonu girin (orn: F8, Ctrl+Shift+V)",
        "label_interface_lang": "Arayuz dili",
        "hint_interface_lang": "Menulerin dilini degistirir",
        "label_dictation_lang": "Dikte dili",
        "hint_dictation_lang": "Ses tanima icin kullanilan dil",
        "label_activation": "Etkinlestirme yontemi",
        "hint_activation": "Dikte nasil baslatilir/durdurulur",
        "activation_hotkey": "Sadece klavye kisayolu",
        "activation_icon": "Sadece VoxWave simgesi",
        "activation_both": "Ikisi de (klavye + simge)",
        "section_writing": "YAZMA MODU",
        "desc_writing": "VoxWave diktelerinizi nasil duzenlemelidir?",
        "tone_raw": "Ham", "tone_raw_desc": "Islem yok, tam transkripsiyon",
        "tone_auto": "Otomatik", "tone_auto_desc": "Uygulamayi tespit eder ve otomatik olarak uyarlar",
        "section_audio": "SES CIHAZI",
        "label_mic": "Mikrofon",
        "hint_mic": "Dikte icin kullanilacak mikrofonu secin",
        "label_auto_stop": "Otomatik dur",
        "hint_auto_stop": "Sessizlikten sonra kaydi otomatik durdur",
        "label_auto_stop_duration": "Sessizlik suresi (saniye)",
        "hint_auto_stop_duration": "Bu kadar saniye sessizlikten sonra dur",
        "btn_close": "Kaydet",
        "section_advanced": "GELISMIS",
        "label_trans_provider": "Transkripsiyon",
        "label_clean_provider": "Temizleme",
        "label_ollama_host": "Ollama adresi",
        "hint_ollama_host": "Ollama baska bir portta calisiyorsa degistirin",
        "section_help": "YARDIM",
        "help_shortcut_label": "Mevcut kisayol:",
        "help_how_title": "Nasil calisir",
        "help_how_text": (
            "1. Dikte etmek icin kisayola basin\n"
            "2. Mikrofonunuza konusun\n"
            "3. Durdurmak icin tekrar basin\n"
            "4. Temiz metin otomatik yapistiriliyor"
        ),
        "help_report_title": "Sorun bildir",
        "help_report_hint": "Iletisim: support@voxwave.app",
        "help_open_logs": "Log klasorunu ac",
        "section_telemetry": "TELEMETRI",
        "label_telemetry": "Kullanim telemetrisi",
        "hint_telemetry": "Anonim istatistikler gonderir (dikte sayisi, oturum suresi). Dikte edilen metin gonderilmez.",
    },
    "pl": {
        "title": "Ustawienia",
        "nav_general": "Ogolne", "nav_audio": "Audio",
        "nav_writing": "Pisanie", "nav_account": "Konto",
        "label_hotkey": "Skrot klawiszowy",
        "hint_hotkey": "Kliknij i nacisnij kombinacje (np. F8, Ctrl+Shift+V)",
        "label_interface_lang": "Jezyk interfejsu",
        "hint_interface_lang": "Zmienia jezyk menu i interfejsu",
        "label_dictation_lang": "Jezyk dyktowania",
        "hint_dictation_lang": "Jezyk uzywany do rozpoznawania mowy",
        "label_activation": "Metoda aktywacji",
        "hint_activation": "Jak rozpoczac/zatrzymac dyktowanie",
        "activation_hotkey": "Tylko skrot klawiszowy",
        "activation_icon": "Tylko ikona VoxWave",
        "activation_both": "Oba (klawiatura + ikona)",
        "section_writing": "TRYB PISANIA",
        "desc_writing": "Jak VoxWave ma czyscic twoje dyktowania?",
        "tone_raw": "Surowy", "tone_raw_desc": "Bez przetwarzania, dokladna transkrypcja",
        "tone_auto": "Auto", "tone_auto_desc": "Wykrywa aplikacje i automatycznie dostosowuje",
        "section_audio": "URZADZENIE AUDIO",
        "label_mic": "Mikrofon",
        "hint_mic": "Wybierz mikrofon do dyktowania",
        "label_auto_stop": "Automatyczne zatrzymanie",
        "hint_auto_stop": "Automatycznie zatrzymaj nagrywanie po ciszy",
        "label_auto_stop_duration": "Czas ciszy (sekundy)",
        "hint_auto_stop_duration": "Zatrzymaj po tej liczbie sekund ciszy",
        "btn_close": "Zapisz",
        "section_advanced": "ZAAWANSOWANE",
        "label_trans_provider": "Transkrypcja",
        "label_clean_provider": "Czyszczenie",
        "label_ollama_host": "Adres Ollama",
        "hint_ollama_host": "Zmien jesli Ollama dziala na innym porcie",
        "section_help": "POMOC",
        "help_shortcut_label": "Aktualny skrot:",
        "help_how_title": "Jak to dziala",
        "help_how_text": (
            "1. Nacisnij skrot, aby rozpoczac dyktowanie\n"
            "2. Mow do mikrofonu\n"
            "3. Nacisnij ponownie, aby zatrzymac\n"
            "4. Czysty tekst jest automatycznie wklejony"
        ),
        "help_report_title": "Zglos problem",
        "help_report_hint": "Kontakt: support@voxwave.app",
        "help_open_logs": "Otworz folder logow",
        "section_telemetry": "TELEMETRIA",
        "label_telemetry": "Telemetria uzytkowania",
        "hint_telemetry": "Wysyla anonimowe statystyki (liczba dyktowań, czas sesji). Żaden dyktowany tekst nie jest wysyłany.",
    },
    "sv": {
        "title": "Installningar",
        "nav_general": "Allman", "nav_audio": "Ljud",
        "nav_writing": "Skrivning", "nav_account": "Konto",
        "label_hotkey": "Kortkommando",
        "hint_hotkey": "Klicka och tryck kombinationen (t.ex. F8, Ctrl+Shift+V)",
        "label_interface_lang": "Grässnittssprak",
        "hint_interface_lang": "Andrar sprak for menyer",
        "label_dictation_lang": "Dikteringssprak",
        "hint_dictation_lang": "Sprak for rostigenkanningsprogram",
        "label_activation": "Aktiveringsmetod",
        "hint_activation": "Hur man startar/stoppar diktering",
        "activation_hotkey": "Endast kortkommando",
        "activation_icon": "Endast VoxWave-ikon",
        "activation_both": "Bada (tangentbord + ikon)",
        "section_writing": "SKRIVLAGE",
        "desc_writing": "Hur ska VoxWave rensa dina dikteringar?",
        "tone_raw": "Rakt", "tone_raw_desc": "Ingen behandling, exakt transkription",
        "tone_auto": "Auto", "tone_auto_desc": "Identifierar appen och anpassar automatiskt",
        "section_audio": "LJUDENHET",
        "label_mic": "Mikrofon",
        "hint_mic": "Valj mikrofon for diktering",
        "label_auto_stop": "Automatiskt stopp",
        "hint_auto_stop": "Stoppa inspelningen automatiskt efter tystnad",
        "label_auto_stop_duration": "Tystnadstid (sekunder)",
        "hint_auto_stop_duration": "Stoppa efter detta antal sekunders tystnad",
        "btn_close": "Spara",
        "section_advanced": "AVANCERAT",
        "label_trans_provider": "Transkription",
        "label_clean_provider": "Rensning",
        "label_ollama_host": "Ollama-adress",
        "hint_ollama_host": "Andra om Ollama koer pa en annan port",
        "section_help": "HJALP",
        "help_shortcut_label": "Aktuellt kortkommando:",
        "help_how_title": "Hur det fungerar",
        "help_how_text": (
            "1. Tryck kortkommando for att diktera\n"
            "2. Tala i mikrofonen\n"
            "3. Tryck igen for att stoppa\n"
            "4. Ren text klistras automatiskt in"
        ),
        "help_report_title": "Rapportera ett problem",
        "help_report_hint": "Kontakt: support@voxwave.app",
        "help_open_logs": "Oppna loggmapp",
        "section_telemetry": "TELEMETRI",
        "label_telemetry": "Anvandningstelemetri",
        "hint_telemetry": "Skickar anonym statistik (antal dikteringar, sessionslangd). Ingen dikterad text skickas.",
    },
}


def _st(lang: str, key: str) -> str:
    """Retourne la traduction settings pour une cle dans la langue donnee."""
    d = _SETTINGS_T.get(lang, _SETTINGS_T["en"])
    return d.get(key, _SETTINGS_T["en"].get(key, key))


# Mapping Qt modifier flags -> noms
_QT_MODIFIER_NAMES = {
    Qt.KeyboardModifier.ControlModifier: "Ctrl",
    Qt.KeyboardModifier.ShiftModifier: "Shift",
    Qt.KeyboardModifier.AltModifier: "Alt",
    Qt.KeyboardModifier.MetaModifier: "Cmd",
}

# Mapping Qt key codes -> noms lisibles
_QT_KEY_NAMES: dict = {}
for _i in range(1, 13):
    _QT_KEY_NAMES[getattr(Qt.Key, f"Key_F{_i}")] = f"F{_i}"
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    _QT_KEY_NAMES[getattr(Qt.Key, f"Key_{_c}")] = _c
for _d in "0123456789":
    _QT_KEY_NAMES[getattr(Qt.Key, f"Key_{_d}")] = _d
_QT_KEY_NAMES.update({
    Qt.Key.Key_Space: "Space",
    Qt.Key.Key_Return: "Enter",
    Qt.Key.Key_Tab: "Tab",
    Qt.Key.Key_Escape: "Esc",
    Qt.Key.Key_Backspace: "Backspace",
    Qt.Key.Key_Delete: "Delete",
    Qt.Key.Key_Home: "Home",
    Qt.Key.Key_End: "End",
    Qt.Key.Key_PageUp: "PageUp",
    Qt.Key.Key_PageDown: "PageDown",
    Qt.Key.Key_Up: "Up",
    Qt.Key.Key_Down: "Down",
    Qt.Key.Key_Left: "Left",
    Qt.Key.Key_Right: "Right",
    Qt.Key.Key_Insert: "Insert",
})

# ====================================================================
# Styles
# ====================================================================

_STYLESHEET = """
QDialog {
    background-color: #18181b;
    color: #ffffff;
}
QLabel {
    color: #ffffff;
    background: transparent;
}
QLabel#section-title {
    color: rgba(255, 255, 255, 0.4);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
}
QLabel#hint {
    color: rgba(255, 255, 255, 0.4);
    font-size: 11px;
}
QLabel#nav-item {
    color: rgba(255, 255, 255, 0.6);
    font-size: 13px;
    padding: 8px 16px;
    border-radius: 8px;
}
QLabel#nav-item-active {
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 8px;
    background-color: rgba(255, 255, 255, 0.08);
}
QLineEdit {
    background-color: rgba(255, 255, 255, 0.08);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    font-weight: bold;
}
QLineEdit:focus {
    border-color: #3b82f6;
}
QComboBox {
    background-color: rgba(255, 255, 255, 0.08);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    min-width: 180px;
}
QComboBox:hover {
    border-color: rgba(255, 255, 255, 0.3);
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid rgba(255, 255, 255, 0.5);
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #27272a;
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    selection-background-color: rgba(59, 130, 246, 0.3);
    padding: 4px;
}
QPushButton#close-btn {
    background-color: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
}
QPushButton#close-btn:hover {
    background-color: rgba(255, 255, 255, 0.12);
    color: #ffffff;
}
QPushButton#quit-btn {
    background-color: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#quit-btn:hover {
    background-color: rgba(239, 68, 68, 0.25);
    border-color: rgba(239, 68, 68, 0.5);
}
"""


# ====================================================================
# HotkeyCapture (reutilise dans welcome_dialog aussi)
# ====================================================================

class HotkeyCapture(QLineEdit):
    """Champ de saisie qui capture les combos de touches."""

    def __init__(self, current_hotkey: str = "F8", parent: Optional[object] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Appuyez sur une combinaison de touches...")
        self.setText(current_hotkey)
        self._captured_hotkey = current_hotkey

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Capture les combos de touches."""
        key = event.key()

        # Ignorer les appuis de modifier seuls
        if key in (
            Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt,
            Qt.Key.Key_Meta, Qt.Key.Key_AltGr,
        ):
            return

        key_name = _QT_KEY_NAMES.get(key)
        if key_name is None:
            return

        # Construire la chaine combo
        parts = []
        modifiers = event.modifiers()
        for mod_flag, mod_name in _QT_MODIFIER_NAMES.items():
            if modifiers & mod_flag:
                parts.append(mod_name)
        parts.append(key_name)

        combo = "+".join(parts)
        self._captured_hotkey = combo
        self.setText(combo)

    @property
    def captured_hotkey(self) -> str:
        """Retourne le hotkey capture."""
        return self._captured_hotkey


# ====================================================================
# NavItem (bouton de navigation gauche)
# ====================================================================

class _NavItem(QLabel):
    """Item de navigation cliquable dans la sidebar."""

    clicked = Signal()

    def __init__(self, text: str, icon: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._text = text
        self._icon = icon
        self._active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText(f"{icon}  {text}" if icon else text)
        self.setObjectName("nav-item")

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = value
        self.setObjectName("nav-item-active" if value else "nav-item")
        self.setStyleSheet(self.styleSheet())  # force refresh

    def mousePressEvent(self, event: object) -> None:
        self.clicked.emit()


# ====================================================================
# ToneCard (carte cliquable pour le mode d'ecriture)
# ====================================================================

class _ToneCard(QWidget):
    """Carte de selection du ton d'ecriture."""

    clicked = Signal()

    _BG_NORMAL = QColor(255, 255, 255, 13)
    _BG_HOVER = QColor(255, 255, 255, 25)
    _BG_SELECTED = QColor(59, 130, 246, 38)
    _BORDER_NORMAL = QColor(255, 255, 255, 25)
    _BORDER_HOVER = QColor(255, 255, 255, 60)
    _BORDER_SELECTED = QColor(59, 130, 246, 255)

    def __init__(self, title: str, description: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._selected = False
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        self._check = QLabel("")
        self._check.setFixedWidth(18)
        self._check.setStyleSheet("font-size: 14px; color: #3b82f6; background: transparent; border: none;")
        self._check.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._check)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        title_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text_layout.addWidget(title_lbl)
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 11px; background: transparent; border: none;")
        desc_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text_layout.addWidget(desc_lbl)
        layout.addLayout(text_layout)

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool) -> None:
        self._selected = value
        self._check.setText("\u2713" if value else "")
        self.update()

    def enterEvent(self, event: object) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        self._hovered = False
        self.update()

    def mousePressEvent(self, event: object) -> None:
        self.clicked.emit()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        if self._selected:
            bg, border = self._BG_SELECTED, self._BORDER_SELECTED
        elif self._hovered:
            bg, border = self._BG_HOVER, self._BORDER_HOVER
        else:
            bg, border = self._BG_NORMAL, self._BORDER_NORMAL
        painter.setBrush(bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 10, 10)
        painter.setPen(QPen(border, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 10, 10)
        painter.end()


# ====================================================================
# SettingsDialog principal
# ====================================================================

class SettingsDialog(QDialog):
    """Dialogue de parametres VoxWave — design moderne avec navigation laterale."""

    def __init__(
        self,
        current_hotkey: str = "F8",
        current_cleaning_mode: str = "auto",
        current_language: str = "en",
        current_system_language: str = "en",
        current_device_id: Optional[int] = None,
        current_transcription_provider: str = "hybrid",
        current_cleaning_provider: str = "hybrid",
        current_ollama_host: str = "http://localhost:11434",
        current_activation_method: str = "both",
        current_auto_stop_enabled: bool = False,
        current_auto_stop_silence_duration: float = 2.0,
        current_telemetry_enabled: bool = True,
        on_quit: Optional[object] = None,
        on_activate_license: Optional[object] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._hotkey = current_hotkey
        self._cleaning_mode = current_cleaning_mode
        self._language = current_language
        self._system_language = current_system_language
        self._sys_lang = current_system_language  # alias utilisé pour les traductions
        self._device_id = current_device_id
        self._transcription_provider = current_transcription_provider
        self._cleaning_provider = current_cleaning_provider
        self._ollama_host = current_ollama_host
        self._activation_method = current_activation_method
        self._auto_stop_enabled = current_auto_stop_enabled
        self._auto_stop_silence_duration = current_auto_stop_silence_duration
        self._telemetry_enabled = current_telemetry_enabled
        self._on_quit = on_quit
        self._on_activate_license = on_activate_license

        self._setup_window()
        self._build_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle(f"VoxWave — {_st(self._sys_lang, 'title')}")
        self.setFixedSize(620, 580)
        self.setStyleSheet(_STYLESHEET)
        flags = (
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        if sys.platform == "win32":
            # Fenetre "tool" sous Windows: n'ajoute pas d'entree taskbar separee.
            flags |= Qt.WindowType.Tool
        self.setWindowFlags(flags)
        if sys.platform == "win32":
            logger.debug("SettingsDialog win32 flags: %s", int(self.windowFlags()))

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Sidebar gauche ----
        sidebar = QWidget()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet("background-color: rgba(255,255,255,0.03);")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(4)

        # Titre sidebar
        title = QLabel(_st(self._sys_lang, "title"))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff; padding: 0 16px 12px 16px;")
        sidebar_layout.addWidget(title)

        # Nav items (4 onglets)
        self._nav_items: list[_NavItem] = []
        nav_labels = [
            (_st(self._sys_lang, "nav_general"), "\u2699"),
            (_st(self._sys_lang, "nav_audio"), "\u266b"),
            (_st(self._sys_lang, "nav_writing"), "\u270e"),
            (_st(self._sys_lang, "nav_account"), "\u2606"),
        ]
        for i, (label, icon) in enumerate(nav_labels):
            nav = _NavItem(label, icon)
            nav.clicked.connect(lambda idx=i: self._navigate(idx))
            self._nav_items.append(nav)
            sidebar_layout.addWidget(nav)

        sidebar_layout.addStretch()

        # Version
        version = QLabel("VoxWave v2.1")
        version.setStyleSheet("color: rgba(255,255,255,0.25); font-size: 10px; padding: 0 16px;")
        sidebar_layout.addWidget(version)

        root.addWidget(sidebar)

        # ---- Contenu droite ----
        self._content_stack = QVBoxLayout()
        self._content_stack.setContentsMargins(24, 20, 24, 20)

        # Pages (4 onglets : General, Audio, Ecriture, Compte)
        self._pages: list[QWidget] = []
        self._pages.append(self._build_page_general())
        self._pages.append(self._build_page_audio())
        self._pages.append(self._build_page_writing())
        self._pages.append(self._build_page_account())

        # On utilise un stacked widget avec scroll pour chaque page
        from PySide6.QtWidgets import QStackedWidget
        self._stack = QStackedWidget()
        for page in self._pages:
            page.setObjectName("settings-page")
            scroll = QScrollArea()
            scroll.setWidget(page)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setStyleSheet(
                "QScrollArea { background: #18181b; border: none; }"
                "QScrollArea > QWidget > QWidget { background: #18181b; }"
            )
            scroll.viewport().setAutoFillBackground(False)
            self._stack.addWidget(scroll)
        self._content_stack.addWidget(self._stack)

        # Bouton Fermer en bas
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton(_st(self._sys_lang, "btn_close"))
        close_btn.setObjectName("close-btn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        self._content_stack.addLayout(close_row)

        content_widget = QWidget()
        content_widget.setLayout(self._content_stack)
        root.addWidget(content_widget)

        # Activer le premier onglet
        self._navigate(0)

    def _navigate(self, index: int) -> None:
        """Change l'onglet actif."""
        for i, nav in enumerate(self._nav_items):
            nav.active = (i == index)
        self._stack.setCurrentIndex(index)

    # ================================================================
    # Page General
    # ================================================================

    def _build_page_general(self) -> QWidget:
        t = _SETTINGS_T.get(self._sys_lang, _SETTINGS_T["en"])
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Section title
        layout.addWidget(self._section_title("GENERAL"))

        # Raccourci clavier
        layout.addWidget(self._field_label(t["label_hotkey"]))
        self._hotkey_capture = HotkeyCapture(self._hotkey)
        self._hotkey_capture.setMinimumHeight(40)
        layout.addWidget(self._hotkey_capture)
        hint = QLabel(t["hint_hotkey"])
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addSpacing(6)

        # Langue de l'interface
        layout.addWidget(self._field_label(t["label_interface_lang"]))
        self._sys_lang_combo = QComboBox()
        sys_languages = [
            ("en", "English"),
            ("fr", "Francais"),
            ("es", "Espanol"),
            ("de", "Deutsch"),
            ("it", "Italiano"),
            ("pt", "Portugues"),
            ("nl", "Nederlands"),
            ("ja", "Japanese"),
            ("ko", "Korean"),
            ("zh", "Chinese"),
            ("ru", "Russian"),
            ("ar", "Arabic"),
            ("tr", "Turkish"),
            ("pl", "Polish"),
            ("sv", "Swedish"),
        ]
        current_sys_lang_idx = 0
        for i, (code, name) in enumerate(sys_languages):
            self._sys_lang_combo.addItem(f"{name} ({code})", code)
            if code == self._system_language:
                current_sys_lang_idx = i
        self._sys_lang_combo.setCurrentIndex(current_sys_lang_idx)
        layout.addWidget(self._sys_lang_combo)
        sys_hint = QLabel(t["hint_interface_lang"])
        sys_hint.setObjectName("hint")
        layout.addWidget(sys_hint)

        layout.addSpacing(6)

        # Langue de dictee
        layout.addWidget(self._field_label(t["label_dictation_lang"]))
        self._lang_combo = QComboBox()
        self._lang_combo.addItem("🌐 Auto-detect", "auto")
        for code, name in WHISPER_LANGUAGES:
            self._lang_combo.addItem(f"{name} ({code})", code)
        current_lang_idx = 0
        all_lang_codes = ["auto"] + [c for c, _ in WHISPER_LANGUAGES]
        for i, code in enumerate(all_lang_codes):
            if code == self._language:
                current_lang_idx = i
                break
        self._lang_combo.setCurrentIndex(current_lang_idx)
        layout.addWidget(self._lang_combo)
        lang_hint = QLabel(t["hint_dictation_lang"])
        lang_hint.setObjectName("hint")
        layout.addWidget(lang_hint)

        layout.addSpacing(6)

        # Methode d'activation
        layout.addWidget(self._field_label(t["label_activation"]))
        activation_hint = QLabel(t["hint_activation"])
        activation_hint.setObjectName("hint")
        layout.addWidget(activation_hint)

        self._act_hotkey_card = _ToneCard(t["activation_hotkey"], "")
        self._act_hotkey_card.clicked.connect(lambda: self._select_activation("hotkey"))
        layout.addWidget(self._act_hotkey_card)

        self._act_icon_card = _ToneCard(t["activation_icon"], "")
        self._act_icon_card.clicked.connect(lambda: self._select_activation("icon"))
        layout.addWidget(self._act_icon_card)

        self._act_both_card = _ToneCard(t["activation_both"], "")
        self._act_both_card.clicked.connect(lambda: self._select_activation("both"))
        layout.addWidget(self._act_both_card)

        # Pre-select
        self._select_activation(self._activation_method)

        layout.addStretch()
        return page

    def _select_activation(self, method: str) -> None:
        self._activation_method = method
        self._act_hotkey_card.selected = (method == "hotkey")
        self._act_icon_card.selected = (method == "icon")
        self._act_both_card.selected = (method == "both")

    # ================================================================
    # Page Ecriture (mode + providers + ollama)
    # ================================================================

    def _build_page_writing(self) -> QWidget:
        t = _SETTINGS_T.get(self._sys_lang, _SETTINGS_T["en"])
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._section_title(t["section_writing"]))

        desc = QLabel(t["desc_writing"])
        desc.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(4)

        # Carte Brut
        self._tone_raw = _ToneCard(t["tone_raw"], t["tone_raw_desc"])
        self._tone_raw.clicked.connect(lambda: self._select_mode("raw"))
        layout.addWidget(self._tone_raw)

        layout.addSpacing(4)

        # Carte Auto
        self._tone_auto = _ToneCard(t["tone_auto"], t["tone_auto_desc"])
        self._tone_auto.clicked.connect(lambda: self._select_mode("auto"))
        layout.addWidget(self._tone_auto)

        # Pre-select avec migration backward-compat
        mode = self._cleaning_mode
        if mode in ("verbatim", "quality"):
            mode = "auto"
        if mode == "raw":
            self._tone_raw.selected = True
        else:
            self._tone_auto.selected = True

        # -- Separateur visuel --
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #2a2a3e;")
        layout.addWidget(sep)

        layout.addSpacing(4)

        # -- Section Avance (providers) integree --
        layout.addWidget(self._section_title(t["section_advanced"]))

        # Provider transcription
        layout.addWidget(self._field_label(t["label_trans_provider"]))
        self._trans_combo = QComboBox()
        trans_options = [
            ("hybrid", "Hybride (cloud + local)"),
            ("cloud", "Cloud uniquement (Groq)"),
            ("local", "Local uniquement (Whisper)"),
        ]
        current_trans_idx = 0
        for i, (val, label) in enumerate(trans_options):
            self._trans_combo.addItem(label, val)
            if val == self._transcription_provider:
                current_trans_idx = i
        self._trans_combo.setCurrentIndex(current_trans_idx)
        layout.addWidget(self._trans_combo)

        layout.addSpacing(8)

        # Provider nettoyage
        layout.addWidget(self._field_label(t["label_clean_provider"]))
        self._clean_combo = QComboBox()
        clean_options = [
            ("hybrid", "Hybride (cloud + local)"),
            ("cloud", "Cloud uniquement (OpenAI)"),
            ("local", "Local uniquement (Ollama)"),
            ("regex", "Regex uniquement (natif, sans IA)"),
        ]
        current_clean_idx = 0
        for i, (val, label) in enumerate(clean_options):
            self._clean_combo.addItem(label, val)
            if val == self._cleaning_provider:
                current_clean_idx = i
        self._clean_combo.setCurrentIndex(current_clean_idx)
        layout.addWidget(self._clean_combo)

        hint = QLabel("Hybride = essaie le cloud d'abord, bascule en local si indisponible")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._ollama_hint = QLabel('<a href="https://ollama.com/download">\u2192 T\u00e9l\u00e9charger Ollama</a>')
        self._ollama_hint.setOpenExternalLinks(True)
        self._ollama_hint.setVisible(self._cleaning_provider == "local")
        self._clean_combo.currentIndexChanged.connect(self._update_ollama_hint)
        layout.addWidget(self._ollama_hint)

        layout.addSpacing(8)

        # Adresse Ollama
        layout.addWidget(self._field_label(t.get("label_ollama_host", "Ollama address")))
        self._ollama_host_edit = QLineEdit(self._ollama_host)
        self._ollama_host_edit.setPlaceholderText("http://localhost:11434")
        self._ollama_host_edit.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);"
            " border-radius: 6px; padding: 6px 10px; color: white; font-size: 13px; }"
            "QLineEdit:focus { border-color: rgba(255,255,255,0.35); }"
        )
        layout.addWidget(self._ollama_host_edit)
        hint_host = QLabel(t.get("hint_ollama_host", "Change if Ollama runs on a different port"))
        hint_host.setObjectName("hint")
        hint_host.setWordWrap(True)
        layout.addWidget(hint_host)

        # Telemetrie
        layout.addSpacing(12)
        layout.addWidget(self._section_title(t.get("section_telemetry", "TELEMETRY")))
        self._telemetry_check = QCheckBox(t.get("label_telemetry", "Usage telemetry"))
        self._telemetry_check.setChecked(self._telemetry_enabled)
        self._telemetry_check.setStyleSheet("color: #c0c0c0; font-size: 13px;")
        layout.addWidget(self._telemetry_check)
        telemetry_hint = QLabel(t.get("hint_telemetry",
            "Sends anonymous stats (dictation count, session duration). No dictated text is sent."))
        telemetry_hint.setObjectName("hint")
        telemetry_hint.setWordWrap(True)
        layout.addWidget(telemetry_hint)

        layout.addStretch()
        return page

    def _select_mode(self, mode: str) -> None:
        self._cleaning_mode = mode
        self._tone_raw.selected = (mode == "raw")
        self._tone_auto.selected = (mode == "auto")

    # ================================================================
    # Page Audio
    # ================================================================

    def _build_page_audio(self) -> QWidget:
        t = _SETTINGS_T.get(self._sys_lang, _SETTINGS_T["en"])
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(self._section_title(t["section_audio"]))

        layout.addWidget(self._field_label(t["label_mic"]))

        self._device_combo = QComboBox()
        self._device_combo.addItem("Defaut systeme", None)

        # Charger les devices disponibles
        try:
            from src.audio.device_manager import AudioDeviceManager
            devices = AudioDeviceManager.list_input_devices()
            current_idx = 0
            for dev in devices:
                self._device_combo.addItem(
                    f"{dev['name']} ({dev['channels']}ch)",
                    dev["id"],
                )
                if dev["id"] == self._device_id:
                    current_idx = self._device_combo.count() - 1
            self._device_combo.setCurrentIndex(current_idx)
        except Exception as e:
            logger.warning(f"Impossible de lister les peripheriques: {e}")

        layout.addWidget(self._device_combo)

        hint = QLabel(t["hint_mic"])
        hint.setObjectName("hint")
        layout.addWidget(hint)

        # Séparateur visuel
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #2a2a3e;")
        layout.addWidget(sep)

        # Auto-stop toggle
        self._auto_stop_check = QCheckBox(t["label_auto_stop"])
        self._auto_stop_check.setChecked(self._auto_stop_enabled)
        self._auto_stop_check.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        self._auto_stop_check.toggled.connect(self._on_auto_stop_toggled)
        layout.addWidget(self._auto_stop_check)

        hint_as = QLabel(t["hint_auto_stop"])
        hint_as.setObjectName("hint")
        layout.addWidget(hint_as)

        # Durée de silence (activée/désactivée selon le checkbox)
        dur_row = QHBoxLayout()
        dur_label = QLabel(t["label_auto_stop_duration"])
        dur_label.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        self._auto_stop_duration_spin = QDoubleSpinBox()
        self._auto_stop_duration_spin.setRange(0.5, 10.0)
        self._auto_stop_duration_spin.setSingleStep(0.5)
        self._auto_stop_duration_spin.setValue(self._auto_stop_silence_duration)
        self._auto_stop_duration_spin.setSuffix(" s")
        self._auto_stop_duration_spin.setEnabled(self._auto_stop_enabled)
        self._auto_stop_duration_spin.setFixedWidth(90)
        dur_row.addWidget(dur_label)
        dur_row.addStretch()
        dur_row.addWidget(self._auto_stop_duration_spin)
        layout.addLayout(dur_row)

        hint_dur = QLabel(t["hint_auto_stop_duration"])
        hint_dur.setObjectName("hint")
        layout.addWidget(hint_dur)

        layout.addStretch()
        return page

    def _on_auto_stop_toggled(self, checked: bool) -> None:
        """Active/désactive le spin box durée selon l'état du checkbox."""
        self._auto_stop_duration_spin.setEnabled(checked)

    # ================================================================
    # Page Compte (licence + aide + a propos + quitter)
    # ================================================================

    def _build_page_account(self) -> QWidget:
        t = _SETTINGS_T.get(self._sys_lang, _SETTINGS_T["en"])
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # -- Section Licence --
        layout.addWidget(self._section_title("LICENCE"))

        status_label = QLabel("Statut : Free tier")
        status_label.setStyleSheet("color: #60a5fa; font-size: 14px; font-weight: 600;")
        layout.addWidget(status_label)

        desc = QLabel(
            "Le free tier vous permet d'utiliser VoxWave avec un nombre\n"
            "limite de dictees par jour. Activez une licence pour un\n"
            "usage illimite."
        )
        desc.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        activate_btn = QPushButton("Activer une licence")
        activate_btn.setStyleSheet(
            "QPushButton { background-color: rgba(59,130,246,0.15); color: #3b82f6; "
            "border: 1px solid rgba(59,130,246,0.3); border-radius: 8px; "
            "padding: 10px 20px; font-size: 13px; font-weight: 600; }"
            "QPushButton:hover { background-color: rgba(59,130,246,0.25); "
            "border-color: rgba(59,130,246,0.5); }"
        )
        activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        activate_btn.clicked.connect(self._on_activate_license_clicked)
        layout.addWidget(activate_btn)

        # -- Separateur --
        sep1 = QLabel()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet("background: #2a2a3e;")
        layout.addWidget(sep1)

        # -- Section Aide --
        layout.addWidget(self._section_title(t["section_help"]))

        shortcut_label = QLabel(f"{t['help_shortcut_label']} {self._hotkey}")
        shortcut_label.setStyleSheet("color: #60a5fa; font-size: 14px; font-weight: 600;")
        layout.addWidget(shortcut_label)

        how_title = QLabel(t["help_how_title"])
        how_title.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 13px; font-weight: 600;")
        layout.addWidget(how_title)

        how_text = QLabel(t["help_how_text"])
        how_text.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 12px;")
        how_text.setWordWrap(True)
        layout.addWidget(how_text)

        report_label = QLabel(t["help_report_title"])
        report_label.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 13px; font-weight: 600;")
        layout.addWidget(report_label)

        report_hint = QLabel(t["help_report_hint"])
        report_hint.setObjectName("hint")
        layout.addWidget(report_hint)

        # -- Bouton ouvrir les logs --
        logs_btn = QPushButton(t["help_open_logs"])
        logs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logs_btn.setStyleSheet("""
            QPushButton {
                background: #2a2a3e; color: #60a5fa; border: 1px solid #3b3b5c;
                border-radius: 8px; padding: 10px 16px; font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background: #3b3b5c; }
        """)
        logs_btn.clicked.connect(self._on_open_logs)
        layout.addWidget(logs_btn)

        # -- Separateur --
        sep2 = QLabel()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: #2a2a3e;")
        layout.addWidget(sep2)

        # -- Section A propos --
        version_label = QLabel("VoxWave v2.1")
        version_label.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 12px;")
        layout.addWidget(version_label)

        tech_text = QLabel(
            "Whisper (transcription) + GPT-4o-mini (nettoyage)\n"
            "PySide6 (interface) + Groq API (cloud rapide)"
        )
        tech_text.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 11px;")
        tech_text.setWordWrap(True)
        layout.addWidget(tech_text)

        layout.addStretch()

        # Bouton Quitter (rouge, en bas)
        quit_btn = QPushButton("Quitter VoxWave")
        quit_btn.setObjectName("quit-btn")
        quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_btn.clicked.connect(self._on_quit_clicked)
        layout.addWidget(quit_btn)

        return page

    def _on_activate_license_clicked(self) -> None:
        """Lance l'activation de licence."""
        if self._on_activate_license:
            self._on_activate_license()

    def _on_open_logs(self) -> None:
        """Ouvre le dossier de logs dans l'explorateur de fichiers."""
        import subprocess
        from src.app import _get_log_dir

        log_dir = _get_log_dir()
        os.makedirs(log_dir, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(log_dir)
        else:
            subprocess.Popen(["xdg-open", log_dir])

    def _on_quit_clicked(self) -> None:
        """Quitte l'application via le bouton Quitter."""
        self.reject()
        if self._on_quit:
            self._on_quit()

    def navigate_to_help(self) -> None:
        """Ouvre directement sur l'onglet Compte qui contient l'aide (appele depuis tray)."""
        self._navigate(3)

    # ================================================================
    # Helpers
    # ================================================================

    def _update_ollama_hint(self) -> None:
        """Affiche le lien Ollama uniquement quand le provider 'local' est sélectionné."""
        self._ollama_hint.setVisible(self._clean_combo.currentData() == "local")

    def _section_title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section-title")
        return lbl

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 13px; font-weight: 600;")
        return lbl

    # ================================================================
    # Properties (lues par app.py apres dialog.exec)
    # ================================================================

    @property
    def hotkey(self) -> str:
        return self._hotkey_capture.captured_hotkey

    @property
    def cleaning_mode(self) -> str:
        return self._cleaning_mode

    @property
    def system_language(self) -> str:
        return self._sys_lang_combo.currentData()

    @property
    def language(self) -> str:
        return self._lang_combo.currentData()

    @property
    def device_id(self) -> Optional[int]:
        return self._device_combo.currentData()

    @property
    def transcription_provider(self) -> str:
        return self._trans_combo.currentData()

    @property
    def cleaning_provider(self) -> str:
        return self._clean_combo.currentData()

    @property
    def ollama_host(self) -> str:
        """Adresse Ollama saisie par l'utilisateur."""
        return self._ollama_host_edit.text().strip() or "http://localhost:11434"

    @property
    def activation_method(self) -> str:
        """Retourne la methode d'activation choisie : 'hotkey' | 'icon' | 'both'."""
        return self._activation_method

    @property
    def auto_stop_enabled(self) -> bool:
        return self._auto_stop_check.isChecked()

    @property
    def auto_stop_silence_duration(self) -> float:
        return self._auto_stop_duration_spin.value()

    @property
    def telemetry_enabled(self) -> bool:
        """Retourne l'etat du toggle telemetrie."""
        return self._telemetry_check.isChecked()
