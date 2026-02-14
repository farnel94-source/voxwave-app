# CLAUDE.md — Instructions pour Claude Code

## Projet
**VoxTool** : Outil de dictee vocale desktop.
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
│   ├── app.py                  # Point d'entree, shutdown gracieux, signal handlers, sauvegarde config
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
│   │   └── llm_cleaner.py     # Nettoyage: OpenAI cloud + Ollama local — circuit breaker
│   ├── injection/
│   │   └── keyboard.py         # Injection texte (paste/type) avec timeouts, fallback cascade
│   ├── hotkey/
│   │   └── listener.py         # Ecoute raccourci clavier — combos (Ctrl+Shift+V, etc.)
│   ├── licensing/
│   │   └── validator.py        # Validation licence LemonSqueezy (free tier + pro)
│   ├── gui/
│   │   ├── orb/
│   │   │   ├── orb.html        # Widget Voice Input HTML/CSS/JS (barres de frequences animees)
│   │   │   └── logo.png        # Logo VoxTool
│   │   ├── waveform_widget.py  # QWebEngineView frameless, always-on-top, draggable
│   │   ├── tray_icon.py        # Icone system tray PySide6 (QSystemTrayIcon)
│   │   ├── settings_dialog.py  # Parametres modernes (sidebar navigation, 4 sections)
│   │   ├── welcome_dialog.py   # Onboarding v2 (7 pages, inspire Wispr Flow)
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
- Config `cleaning.mode` : `verbatim` (naturel) | `quality` (professionnel)
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
- **orb.html** : logo VoxTool + pill expandable avec barres de frequences animees + timer
  - **Idle** : logo seul (transparent, pas de pill)
  - **Recording** : logo reste visible + pill s'ouvre a droite (barres + timer)
  - **Processing** : logo + pill avec "Traitement..."
  - **Error** : logo + pill avec "Erreur" en rouge + animation shake
- **Barres de frequences** : 12 barres, 3px large, hauteur max 80px, animees par l'amplitude audio
- **Bridge Python ↔ JS** : QWebChannel (setState, updateAmplitude, updateStep, showPreview)
- **Tray icon** : menu contextuel (Start/Stop, Parametres, Licence, A propos, Quitter)
- **`setQuitOnLastWindowClosed(False)`** : l'app ne quitte plus quand on ferme un dialog

## Onboarding v2 (welcome_dialog.py) — Inspire Wispr Flow
7 pages avec indicateur de progression (dots + messages encourageants) :
1. **Bienvenue** : logo + bullets + bouton Commencer
2. **Pourquoi VoxTool ?** : 4 cartes multi-select (motivations), Suivant bloque sans selection
3. **Raccourci clavier** : HotkeyCapture, no-skip 3s (Suivant desactive temporairement)
4. **Test micro** : test 3s avec barre de volume
5. **Demo interactive** : bouton Dicter toggle, QTextEdit resultat, transcription dans un thread, bouton Passer apres 10s
6. **Ton d'ecriture** : 2 cartes radio (Naturel/Professionnel) avec exemples avant/apres
7. **Pret !** : rappel hotkey + mode d'ecriture + indication tray

### Widgets custom onboarding
- `_ProgressDots` : 7 cercles peints via QPainter + "Etape X sur 7"
- `_ClickableCard` : carte avec paintEvent (3 etats visuels: normal/hover/selected) + checkmark
- `_TranscriptionWorker` : QObject avec signals finished/error, tourne dans un thread

## Settings Dialog v2 (settings_dialog.py) — Inspire Wispr/Aqua
Fenetre moderne dark theme avec **sidebar navigation a gauche** :
- **General** : raccourci clavier (HotkeyCapture) + langue (15 langues, QComboBox)
- **Ecriture** : mode Naturel/Professionnel (cartes cliquables `_ToneCard` avec checkmark)
- **Audio** : selection micro (liste des peripheriques via AudioDeviceManager)
- **Avance** : provider transcription + provider nettoyage (hybrid/cloud/local)

### Widgets custom settings
- `_NavItem` : QLabel cliquable avec etat actif/inactif pour la sidebar
- `_ToneCard` : carte avec paintEvent (hover/selected) + checkmark
- `HotkeyCapture` : QLineEdit read-only qui capture les combos de touches

### Integration app.py
- `_on_settings()` gere 6 parametres : hotkey, cleaning mode, langue, micro, transcription provider, cleaning provider
- `_save_config_nested()` : charge YAML complet, modifie la cle nested, re-ecrit (supporte cleaning.mode, whisper.language, etc.)
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
6. Multiplateforme : macOS, Windows, Linux
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
