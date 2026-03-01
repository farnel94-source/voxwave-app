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
│   │   ├── keyboard.py         # Injection texte (paste/type) Windows+Linux, warning macOS
│   │   └── progressive_injector.py  # Injection en 2 temps : brut immédiat → nettoyé (Backspace×N + garde-fous)
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
│   │   └── icons.py            # Generation icones dynamiques + force_taskbar_icon_win32 (WM_SETICON Win32)
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
- **orb.html** : logo The Wave + pill expandable avec anneau reactif + timer + hover icons (settings/quit)
  - **Idle** : logo seul avec animation de respiration subtile (glow blanc pulse 3.5s)
  - **Recording** : logo + anneau reactif a l'amplitude + timer (pill s'ouvre a droite)
  - **Processing** : logo + "Traitement" + dots animes (3 points qui rebondissent)
  - **Error** : logo avec glow rouge + texte "Erreur" + animation shake
  - **Transition processing → idle** : flash de succes vert (glow + bounce) avant retour idle
- **Anneau reactif** : cercle positionne autour du logo, scale/opacite/couleur drives par amplitude Python (frame-par-frame via `requestAnimationFrame`, pas de CSS transition)
- **Hover icons** : au survol du logo (idle uniquement), 2 boutons ronds apparaissent (settings + quit)
- **Bridge Python ↔ JS** : QWebChannel (setState, updateAmplitude, updateStep, setErrorText, showPreview, on_quit_clicked)
- **Tray icon** : menu avec icones unicode et separateurs (▶ Dictee / ⚙ Parametres / ❓ Aide / ✧ Licence / ⓘ A propos / ✕ Quitter). Clic gauche tray → ouvre directement les Parametres (via `_on_settings`)
- **Barre des taches Windows** : `_TaskbarWindow` (dans `app.py`) — fenetre fantome minimisee (opacity=0, WA_ShowWithoutActivating) qui donne a l'app une presence permanente dans la barre des taches avec le logo The Wave.
  - Necessite `SetCurrentProcessExplicitAppUserModelID("com.thewave.app")` (via `ctypes`) appele avant la creation de la fenetre
  - **Clic sur l'icone** : intercepte via `nativeEvent` + `WM_SYSCOMMAND SC_RESTORE` (0x0112 / 0xF120). Message consomme (`return True, 0`) pour empecher le flash. Appele EXACTEMENT une fois par clic. Sur Linux : fallback via `changeEvent`.
  - **Logo** : `force_taskbar_icon_win32(hwnd)` dans `icons.py` — sauvegarde logo en ICO temporaire, envoie `WM_SETICON` via `LoadImageW` + `SendMessageW`. Appele avec `QTimer.singleShot(300ms)` apres demarrage event loop (l'Explorateur Windows cree le bouton taskbar de maniere asynchrone).
  - **PIEGE** : ne jamais appeler `force_taskbar_icon_win32` immediatement dans `__init__` — l'Explorateur n'a pas encore cree le bouton, l'icone est ignoree.
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
- `_rebuild_pipeline()` : recrée le `CleaningPipeline` complet avec la config courante — appele quand `cleaning.mode` ou `cleaning.provider` change en cours de session (garantit que les cleaners LLM sont bien re-initialises)
- Onboarding sauvegarde aussi la langue choisie via `_save_config_nested("whisper", "language", ...)`
- Notification tray "Parametres mis a jour" apres sauvegarde

## Internationalisation (i18n)

15 langues supportees dans l'interface, **toutes completement traduites** :
`en`, `fr`, `es`, `de`, `it`, `pt`, `nl`, `ja`, `ko`, `zh`, `ru`, `ar`, `tr`, `pl`, `sv`

3 dictionnaires de traduction (tous couvrent les 15 langues) :
- `_SETTINGS_T` dans `settings_dialog.py` — labels, tooltips, sections, textes d'aide
- `_TRAY_T` dans `tray_icon.py` — menu tray (start, stop, settings, quit, tooltip...)
- `_APP_STEP_T` + `_ERROR_T` dans `app.py` — etapes du pipeline (transcription, cleaning, injection) + mot "Erreur"

Fonction de lookup avec fallback vers `"en"` si cle manquante :
```python
_st(lang, key)   # settings_dialog.py
_tt(lang, key)   # tray_icon.py
_app_t(lang, key)  # app.py
```

La langue est sauvegardee dans `config.yaml` → `whisper.language` et rechargee au demarrage.

## Hotkey personnalisable
- Supporte les combos : `Ctrl+Shift+V`, `Alt+R`, `F1`-`F12`, lettres seules, etc.
- `parse_hotkey(str)` → `(frozenset_modifiers, main_key)` dans `listener.py`
- Hot-reload via `update_hotkey(new_hotkey)` sans redemarrer l'app
- Configurable via Tray → Parametres → capture combo → sauvegarde dans config.yaml
- Validation dans `config/validator.py` via `_validate_hotkey()`

## Injection progressive (progressive_injector.py)

Pipeline en 2 temps pour la latence < 1s :
1. `inject_raw(raw_text)` → texte brut via clipboard + Ctrl+V immédiatement (~100ms)
2. `replace_with_clean(raw_text, generator)` → Backspace × N + Ctrl+V (texte nettoyé)

### Stratégie Backspace × N
- `Backspace` = touche simple sans modificateur → aucun problème de timing
- Fonctionne dans VS Code, Terminal, Notepad, Word, toutes les apps Electron
- `Shift+Left × N` échouait sur Electron (timing asynchrone Chromium)
- `Ctrl+Z` échouait en terminal (doublon) et dans les apps Electron (comportement inattendu)
- **PIÈGE WinUI3** : `keyboard` lib causait une race condition sur Win11 Notepad (WinUI3)
  → utiliser **pynput uniquement** pour `_backspace_pynput` (cohérent avec `_do_pynput_paste`)
- **350ms** de sleep avant Ctrl+V (WinUI3 traite `WM_CLIPBOARDUPDATE` en async — les 6 derniers
  backspaces peuvent arriver après le paste si le buffer est trop court ; 150ms insuffisant)

### Garde-fous anti-effacement accidentel
Avant d'envoyer les Backspaces, 2 conditions vérifiées dans l'ordre :
1. **Délai < 1.5s** depuis `inject_raw` (via `time.monotonic()`, immunisé NTP)
2. **Aucune action utilisateur** (touche ou clic) — listeners pynput clavier + souris en arrière-plan

Si une condition échoue → `_stop_user_watch()` + `return` (texte brut conservé, silent fallback).
`_stop_user_watch()` est appelé dans **toutes** les branches (pas de thread actif qui traîne).

### PIEGE : dossier Windows
Toujours synchroniser vers `voice_text_latency`, PAS `voice_text1`.

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
- **WSL** : `/home/farne/projets/voice_text` (dev principal, branche master)
- **WSL worktree** : `/home/farne/projets/voice_text/.worktrees/feat-low-latency-pipeline` (branche feat/low-latency-pipeline)
- **Windows stable** : `C:\projets\voice_text1` (test master) — accessible via `/mnt/c/projets/voice_text1/`
- **Windows latency** : `C:\projets\voice_text_latency` (test feat/low-latency-pipeline) — accessible via `/mnt/c/projets/voice_text_latency/`
- Toujours synchroniser les fichiers modifies vers le BON dossier Windows apres chaque changement :
  - Changements sur master → `voice_text1`
  - Changements sur feat/low-latency-pipeline → `voice_text_latency`

## Priorites
1. Fonctionnel (ca marche)
2. Fiable (pas de crash)
3. Rapide (pipeline < 3s)
4. Propre (maintenable)
