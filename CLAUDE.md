# CLAUDE.md — Instructions pour Claude Code

## Projet
**The Wave** (anciennement VoxTool) : Outil de dictee vocale desktop (Windows + Linux).
Parle → Transcrit (Whisper) → Nettoie (regex + LLM) → Colle le texte propre.

## Stack
- Python 3.11+
- PySide6 + QWebEngineView (GUI : widget flottant, tray icon, onboarding, parametres)
- faster-whisper (transcription locale, fallback)
- Groq API + whisper-large-v3-turbo (transcription cloud, prioritaire)
- OpenAI GPT-4o-mini (nettoyage cloud, prioritaire)
- Ollama local gemma3:4b (nettoyage local, fallback)
- sounddevice (capture audio)
- webrtcvad (detection de voix)
- pynput (hotkey + injection clavier)
- pyperclip (clipboard)
- PyInstaller (packaging)
- LemonSqueezy (licensing)
- python-dotenv (chargement .env)

## Structure
```
voxtool/
├── src/
│   ├── __init__.py
│   ├── app.py                  # Point d'entree (classe TheWave), shutdown gracieux, check macOS, sauvegarde config
│   ├── audio/
│   │   ├── capture.py          # Capture micro + VAD
│   │   ├── device_manager.py   # Liste et validation des peripheriques audio
│   │   ├── feedback.py         # Sons feedback (start/stop/complete/error)
│   │   └── processor.py        # Traitement audio (chunking, validation duree)
│   ├── transcription/
│   │   ├── whisper_engine.py    # Moteur faster-whisper (local)
│   │   ├── groq_engine.py      # Moteur Groq API (cloud) — flag _available, circuit breaker
│   │   ├── hybrid_engine.py    # Hybride: Groq → Whisper local, callback on_fallback
│   │   └── hallucinations.py   # Detection hallucinations Whisper
│   ├── cleaning/
│   │   ├── regex_cleaner.py    # Nettoyage rapide regex (15 langues de filler words)
│   │   └── llm_cleaner.py     # Nettoyage: mode raw/verbatim/quality — OpenAI cloud + Ollama local — circuit breaker
│   ├── injection/
│   │   └── keyboard.py         # Injection texte (paste/type) Windows+Linux, warning macOS
│   ├── hotkey/
│   │   └── listener.py         # Ecoute raccourci clavier — combos (Ctrl+Shift+V, etc.)
│   ├── licensing/
│   │   └── validator.py        # Validation licence LemonSqueezy (free tier + pro)
│   ├── gui/
│   │   ├── orb/
│   │   │   ├── orb.html        # Widget Voice Input HTML/CSS/JS (barres animees + hover icons settings/quit)
│   │   │   └── logo.png        # Logo The Wave
│   │   ├── waveform_widget.py  # QWebEngineView frameless, always-on-top, draggable + hover icons
│   │   ├── tray_icon.py        # Icone system tray PySide6 (QSystemTrayIcon) + icones unicode
│   │   ├── settings_dialog.py  # Parametres modernes (sidebar navigation, 5 sections dont Aide)
│   │   ├── welcome_dialog.py   # Onboarding v2.1 (8 pages, inspire Wispr Flow, page langue)
│   │   └── icons.py            # Generation icones dynamiques
│   ├── config/
│   │   ├── defaults.py         # Valeurs par defaut de la configuration
│   │   └── validator.py        # Validation et merge de la config
│   └── utils/
│       ├── circuit_breaker.py  # Circuit breaker thread-safe (CLOSED/OPEN/HALF_OPEN)
│       ├── exceptions.py       # Exceptions personnalisees
│       ├── platform.py         # Utilitaires plateforme (resource_path)
│       └── retry.py            # Logique de retry
├── tests/
├── marketing/
│   └── AUDIT_VOXTOOL.md        # Audit concurrentiel complet
├── config.yaml
├── requirements.txt
└── setup.py
```

## Pipeline
```
Hotkey (start) → Capture audio → Hotkey (stop) → Transcription (Groq → Whisper local) → Nettoyage (OpenAI → Ollama → regex) → Injection texte
```

## Mode hybride
- **Transcription** : Groq API (whisper-large-v3-turbo) en priorite, fallback faster-whisper local
- **Nettoyage** : OpenAI GPT-4o-mini en priorite, fallback Ollama local, fallback regex
- Config `transcription.provider` et `cleaning.provider` : `hybrid` | `cloud` | `local`
- Config `cleaning.mode` : `raw` (brut, zero traitement) | `verbatim` (naturel) | `quality` (professionnel)
- Cles API dans `.env` : `GROQ_API_KEY`, `OPENAI_API_KEY`

## Resilience hors-ligne
- **Circuit breaker** (`src/utils/circuit_breaker.py`) : 3 etats (CLOSED → OPEN → HALF_OPEN), thread-safe
- Groq : 3 echecs consecutifs → skip cloud pendant 60s → fallback Whisper local
- OpenAI : 2 echecs consecutifs → skip cloud pendant 60s → fallback Ollama/regex
- Sans cle API : flag `_available = False`, pas de crash (ValueError supprime)
- Check connectivite au demarrage : ping Groq/OpenAI (timeout 3s), pre-ouverture circuit si injoignable
- Notification tray lors d'un fallback : "Transcription : mode local (cloud indisponible)"

## GUI (PySide6 + QWebEngineView)
- **Widget flottant** (`waveform_widget.py`) : fenetre frameless, always-on-top, draggable, 300x116px
- **orb.html** : logo The Wave + pill expandable avec barres de frequences animees + timer + hover icons (settings/quit)
  - **Idle** : logo seul (transparent, pas de pill)
  - **Recording** : logo reste visible + pill s'ouvre a droite (barres + timer)
  - **Processing** : logo + pill avec "Traitement..."
  - **Error** : logo + pill avec "Erreur" en rouge + animation shake
- **Barres de frequences** : 12 barres, 3px large, hauteur max 80px, animees par l'amplitude audio
- **Hover icons** : au survol du logo (idle uniquement), 2 boutons ronds apparaissent (settings + quit)
- **Bridge Python ↔ JS** : QWebChannel (setState, updateAmplitude, updateStep, showPreview, on_quit_clicked)
- **Tray icon** : menu avec icones unicode et separateurs (▶ Dictee / ⚙ Parametres / ❓ Aide / ✧ Licence / ⓘ A propos / ✕ Quitter). Clic gauche tray → ouvre directement les Parametres (via `_on_settings`)
- **Barre des taches Windows** : `_TaskbarWindow` (dans `app.py`) — fenetre fantome minimisee qui donne a l'app une presence permanente dans la barre des taches avec le logo The Wave. Clic sur l'icone → ouvre les Parametres. Necessite `SetCurrentProcessExplicitAppUserModelID("com.thewave.app")` (via `ctypes`) pour que Windows traite l'app independamment de Python.
- **`setQuitOnLastWindowClosed(False)`** : l'app ne quitte plus quand on ferme un dialog

## Plateforme
- **Windows + Linux uniquement** — macOS non supporte (check au demarrage dans `app.py`, `sys.exit(1)`)
- Warning dans `keyboard.py` et `waveform_widget.py` si `sys.platform == "darwin"`
- Raison : Wispr Flow et Aqua Voice dominent sur Mac, aucun concurrent serieux sur Windows/Linux

## Onboarding v2.1 (welcome_dialog.py) — Inspire Wispr Flow
8 pages avec indicateur de progression (dots + messages encourageants) :
1. **Bienvenue** : logo + bullets + bouton Commencer
2. **Pourquoi The Wave ?** : 4 cartes multi-select (motivations), Suivant bloque sans selection
3. **Raccourci clavier** : HotkeyCapture, no-skip 3s (Suivant desactive temporairement)
4. **Langue** : QComboBox (15 langues), sauvegardee dans config
5. **Test micro** : test 3s avec barre de volume + bip audio (play_start/play_stop via AudioFeedback)
6. **Demo interactive** : bouton Dicter toggle, QTextEdit resultat, transcription dans un thread, bouton Passer apres 10s
7. **Ton d'ecriture** : 3 cartes radio (Brut/Naturel/Professionnel) avec exemples
8. **Pret !** : rappel hotkey + mode d'ecriture + indication tray

### Widgets custom onboarding
- `_ProgressDots` : 8 cercles peints via QPainter + "Etape X sur 8"
- `_ClickableCard` : carte avec paintEvent (3 etats visuels: normal/hover/selected) + checkmark
- `_TranscriptionWorker` : QObject avec signals finished/error, tourne dans un thread

## Settings Dialog v2.1 (settings_dialog.py) — Inspire Wispr/Aqua
Fenetre moderne dark theme 620x580 avec **sidebar navigation a gauche** (7 onglets), pages scrollables (QScrollArea) :
- **General** : raccourci clavier (HotkeyCapture) + langue (15 langues, QComboBox)
- **Ecriture** : mode Brut/Naturel/Professionnel (3 cartes cliquables `_ToneCard` avec checkmark)
- **Audio** : selection micro (liste des peripheriques via AudioDeviceManager)
- **Avance** : provider transcription + provider nettoyage (hybrid/cloud/local)
- **Aide** : raccourci actuel, comment ca marche, signaler probleme, a propos, bouton Quitter rouge

### Widgets custom settings
- `_NavItem` : QLabel cliquable avec etat actif/inactif pour la sidebar
- `_ToneCard` : carte avec paintEvent (hover/selected) + checkmark
- `HotkeyCapture` : QLineEdit read-only qui capture les combos de touches

### Integration app.py
- Classe principale `TheWave` (anciennement `VoxTool`)
- `_on_settings()` gere 6 parametres : hotkey, cleaning mode, langue, micro, transcription provider, cleaning provider
- `_on_help()` ouvre les settings directement sur l'onglet Aide via `navigate_to_help()`
- `on_quit` callback passe a `SettingsDialog`, `WaveformWidget` et `TrayIcon`
- `_save_config_nested()` : charge YAML complet, modifie la cle nested, re-ecrit (supporte cleaning.mode, whisper.language, etc.)
- Onboarding sauvegarde aussi la langue choisie via `_save_config_nested("whisper", "language", ...)`
- Notification tray "Parametres mis a jour" apres sauvegarde

## Hotkey personnalisable
- Supporte les combos : `Ctrl+Shift+V`, `Alt+R`, `F1`-`F12`, lettres seules, etc.
- `parse_hotkey(str)` → `(frozenset_modifiers, main_key)` dans `listener.py`
- Hot-reload via `update_hotkey(new_hotkey)` sans redemarrer l'app
- Configurable via Tray → Parametres → capture combo → sauvegarde dans config.yaml
- Validation dans `config/validator.py` via `_validate_hotkey()`

## Shutdown gracieux
- `_shutting_down` flag pour eviter double-shutdown
- Signal handlers SIGINT/SIGTERM dans `run()` avant `exec()`
- QTimer no-op (500ms) pour que Python traite les signaux pendant la boucle Qt
- Ctrl+C dans le terminal → shutdown propre → retour terminal

## Regles de code
1. Type hints sur toutes les fonctions
2. Docstrings Google style
3. logging (jamais print)
4. Tests pytest pour chaque module
5. Gestion erreurs gracieuse, jamais de crash silencieux
6. Plateformes supportees : Windows, Linux (macOS non supporte)
7. Config via config.yaml, pas de valeurs hardcodees

## Commandes
```bash
pip install -r requirements.txt
python -m voxtool
python -m voxtool --model small
python -m voxtool --test
pytest tests/ -v
black src/ tests/
```

## Agents
- .claude/agents/audio-expert.md → capture micro, VAD
- .claude/agents/whisper-expert.md → transcription
- .claude/agents/cleaning-expert.md → nettoyage texte
- .claude/agents/python-expert.md → architecture, packaging
- .claude/agents/testing-expert.md → tests

## Skills
- .claude/skills/transcription-pipeline.md → pipeline complet
- .claude/skills/audio-debugging.md → debug audio
- .claude/skills/text-cleaning.md → patterns nettoyage

## Synchronisation
- **WSL** : `/home/farne/projets/voice_text` (dev principal)
- **Windows** : `C:\projets\voice_text1` (test) — accessible via `/mnt/c/projets/voice_text1/`
- Toujours synchroniser les fichiers modifies vers le dossier Windows apres chaque changement

## Priorites
1. Fonctionnel (ca marche)
2. Fiable (pas de crash)
3. Rapide (pipeline < 3s)
4. Propre (maintenable)
