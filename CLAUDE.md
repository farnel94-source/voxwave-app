# CLAUDE.md — Instructions pour Claude Code

## Projet
**VoxWave** : Outil de dictee vocale desktop (Windows + Linux).
Parle → Transcrit (Whisper) → Nettoie (regex + LLM) → Colle le texte propre.

## Stack
- Python 3.11+
- PySide6 + QPainter natif (GUI : widget flottant, tray icon, onboarding, parametres)
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
voxwave/
├── src/
│   ├── __init__.py
│   ├── app.py                  # Point d'entree (classe VoxWave), shutdown gracieux, check macOS, sauvegarde config
│   ├── audio/
│   │   ├── capture.py          # Capture micro + VAD + auto-stop (seuil dynamique amplitude)
│   │   ├── device_manager.py   # Liste et validation des peripheriques audio
│   │   ├── feedback.py         # Sons feedback (start/stop/complete/error)
│   │   └── processor.py        # Traitement audio (chunking, validation duree, _iter_frames)
│   ├── transcription/
│   │   ├── whisper_engine.py    # Moteur faster-whisper (local) — model=small, condition_on_previous_text=False, interface_language fallback
│   │   ├── groq_engine.py      # Moteur Groq API (cloud) — flag _available, circuit breaker, is_hallucination() TOUJOURS vérifié (quel que soit logprob), hint auto langue via prompt=
│   │   ├── hybrid_engine.py    # Hybride: proxy → Groq → Whisper local, callback on_fallback
│   │   ├── proxy_engine.py     # Moteur proxy (forward audio au backend via requests) — circuit breaker, hallucination check, X-App-Token auth
│   │   └── hallucinations.py   # Detection hallucinations Whisper
│   ├── cleaning/
│   │   ├── regex_cleaner.py    # Nettoyage rapide regex (15 langues de filler words)
│   │   └── llm_cleaner.py     # Nettoyage: mode raw/verbatim/quality — ProxyLLMCleaner + OpenAI cloud + Ollama local — circuit breaker
│   ├── injection/
│   │   ├── keyboard.py         # Injection texte (paste/type) Windows+Linux, warning macOS
│   │   └── progressive_injector.py  # Injection en 2 temps : brut immédiat → nettoyé (Backspace×N + garde-fous)
│   ├── hotkey/
│   │   └── listener.py         # Ecoute raccourci clavier — combos (Ctrl+Shift+V, etc.)
│   ├── licensing/
│   │   └── validator.py        # Validation licence LemonSqueezy (free tier + pro)
│   ├── gui/
│   │   ├── orb_widget.py       # QPainter orb widget (UpdateLayeredWindow Win32 pour transparence)
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
│   └── AUDIT_VOXWAVE.md        # Audit concurrentiel complet
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
- Config `transcription.provider` et `cleaning.provider` : `hybrid` | `cloud` | `local` | `proxy`
- Config `cleaning.mode` : `raw` (brut, zero traitement) | `verbatim` (naturel) | `quality` (professionnel)
- Cles API dans `.env` : `GROQ_API_KEY`, `OPENAI_API_KEY`

## Mode proxy (v0.2.0)
- **Objectif** : securiser les cles API (Groq/OpenAI) cote serveur, l'app ne les contient plus
- **Transcription** : App → Backend proxy → Groq API → retour texte
- **Nettoyage** : App → Backend proxy → OpenAI API → retour texte nettoye
- **Auth** : header `X-App-Token` (shared secret) — bloque les requetes sans token
- **Fallback** : si proxy injoignable → circuit breaker → Whisper local / Ollama / regex
- **Config app** : `transcription.provider: proxy`, `transcription.proxy_url`, `transcription.proxy_app_token`
- **Config backend** : env vars `GROQ_API_KEY`, `OPENAI_API_KEY`, `PROXY_APP_TOKEN` sur Render
- **Keep-alive** : self-ping asyncio toutes les 14 min (evite le sleep Render free tier)
- **Rate limiting** : 20/min transcription, 40/min nettoyage (par IP)
- **Endpoints** : `POST /api/v1/transcribe` (multipart audio) + `POST /api/v1/clean` (JSON texte)
- **Context profiles** : le proxy respecte `context_profile` (code/casual/email/document/default) — prompt adapte cote serveur
- **PIEGE** : `app.py._create_transcription_engine()` doit passer `transcription_provider`, `proxy_url` et `proxy_app_token` a `HybridTranscriptionEngine`. Idem pour `CleaningPipeline` dans `_rebuild_pipeline()`.

## Resilience hors-ligne
- **Circuit breaker** (`src/utils/circuit_breaker.py`) : 3 etats (CLOSED → OPEN → HALF_OPEN), thread-safe
- Groq : 3 echecs consecutifs → skip cloud pendant 60s → fallback Whisper local
- OpenAI : 2 echecs consecutifs → skip cloud pendant 60s → fallback Ollama/regex
- Sans cle API : flag `_available = False`, pas de crash (ValueError supprime)
- Check connectivite au demarrage : ping Groq/OpenAI (timeout 3s), pre-ouverture circuit si injoignable
- Notification tray lors d'un fallback : "Transcription : mode local (cloud indisponible)"
- **Rejet Groq** : `is_hallucination()` vérifié TOUJOURS (quel que soit le logprob). `avg_logprob < -0.7` seul = warning (texte conservé). `strip_hallucination_tails()` retourne vide si tout le texte est une hallucination. Hallucinations connues ajoutées : "Pas de sous-titres", "Sous-titrage Société Radio-Canada", "Merci d'avoir regardé mon promenage".
- **PIEGE Whisper local** : le modèle `base` (74M) est catastrophique en détection de langue multilingue (détecte russe/allemand au lieu de français). Utiliser `small` (244M) minimum. `WhisperEngine` a un paramètre `interface_language` : fallback vers la langue d'interface quand confiance < 0.7 et pas de langue connue précédente.
- **Mode auto langue** : En `whisper.language: auto`, Groq reçoit un hint `prompt=` (PAS `language=`) basé sur `_last_detected_language` ou `_interface_language` (langue d'interface). Évite le biais anglais de Whisper sans forcer de langue. `_GROQ_HINTS` contient des prompts localisés pour 15 langues.
- **Trim audio** : `prepare_for_whisper()` utilise `pad_ms=500` (pas 300) pour garder les fins de phrase à voix décroissante.
- **`_iter_frames()`** (processor.py) : itère sur TOUS les frames audio y compris le dernier (zero-padded si incomplet). PIEGE : ne JAMAIS utiliser `range(0, len(audio) - frame_size, frame_size)` — ça ignore le dernier frame et coupe les fins de phrase.
- **Auto-stop** (`capture.py`) : seuil dynamique = `max(peak_amplitude * 0.15, silence_threshold)`. Le seuil fixe `silence_threshold=0.01` est trop bas (bruit de fond > 0.01 → timer reset en permanence). Le seuil dynamique s'adapte au volume de parole réel.
- **PIEGE thread auto-stop** : `on_silence_detected` (Silero VAD) et `on_auto_stop` (amplitude) doivent pointer vers `_schedule_auto_stop` (pas `_on_stop`). `_schedule_auto_stop` utilise `QTimer.singleShot(0, ...)` pour dispatcher vers le thread Qt principal. Ne JAMAIS lancer le callback dans un `threading.Thread` — appel direct suffit.
- **`_detect_ollama_host()`** (app.py) : scanne les ports [11434, 11435, 11433] au demarrage (socket, timeout 0.5s) et retourne le premier qui repond. Stocke le resultat dans `config["cleaning"]["ollama_host"]`. PIEGE : toujours `try/finally: sock.close()` pour eviter un leak de socket.

## GUI (PySide6 natif QPainter)
- **Widget flottant** (`orb_widget.py`) : fenetre frameless, always-on-top, draggable, 300x116px, rendu 100% QPainter
  - **Remplace** l'ancien `waveform_widget.py` (QWebEngineView + orb.html) — plus de dependance Chromium
  - **`ensure_topmost()`** : re-applique `HWND_TOPMOST` via Win32 `SetWindowPos` (ctypes). Appelé par `_check_orb_health()` toutes les 30s. Nécessaire car Windows peut retirer le flag topmost (fullscreen, UAC, Explorer restart, lock/unlock).
  - **PIEGE** : Qt `raise_()` seul ne restaure PAS le flag `HWND_TOPMOST` au niveau Win32. Toujours utiliser `ensure_topmost()` en complément.
- **Transparence Windows** : Win32 `UpdateLayeredWindow` API (bypass complet de Qt compositing)
  - **PIEGE PySide6 6.11+** : `WA_TranslucentBackground` est CASSE sur Windows pour TOUS les widgets (pas seulement QWebEngineView). Rectangle opaque visible autour du widget. Bug general PySide6 6.11.0 + Chromium 134+.
  - **Solution** : `WS_EX_LAYERED` + `UpdateLayeredWindow` avec per-pixel alpha. Rend dans un `QImage(Format_ARGB32_Premultiplied)` puis envoie les pixels via Win32 API.
  - **DWM** : desactiver coins arrondis (`DWMWA_WINDOW_CORNER_PREFERENCE`), backdrop (`DWMWA_SYSTEMBACKDROP_TYPE`), NC rendering (`DWMWA_NCRENDERING_POLICY`)
  - **DPR** : rendre le QImage a `width*dpr × height*dpr` puis `painter.scale(dpr, dpr)` pour dessiner en coordonnees logiques
  - **`QImage.constBits()`** : sur Python 3.14/PySide6 6.11, retourne `bytes` pas un pointeur — utiliser `bytes(image.constBits())` pour `ctypes.memmove`
  - **Linux** : `WA_TranslucentBackground` + `WA_NoSystemBackground` uniquement. Pas de UpdateLayeredWindow, pas de fond opaque, pas de masque QRegion.
  - **PIEGE Linux** : ne JAMAIS utiliser `WA_OpaquePaintEvent` — conflit direct avec `WA_TranslucentBackground` (cree un rectangle opaque). Ne pas dependre de `xprop` (pas installe par defaut sur Linux Mint). Ne pas utiliser `QScreen.format()` (n'existe pas dans certaines versions PySide6 → crash).
  - **PIEGE Linux** : ne JAMAIS ajouter de fond opaque (`_paint_linux_background`) ni de masque QRegion — ca recree le carre noir. L'orb doit etre 100% transparent, seuls le logo et l'aura sont peints.
- **Etats visuels** (QPainter) :
  - **Idle** : logo seul avec bordure grise fine (1.5px), flash vert de succes apres transcription
  - **Recording** : logo + aura reactive (5 couches: shadow, outer, core glow, particules, edge ring) + timer
  - **Processing** : logo + "Traitement" + dots animes
  - **Error** : logo avec glow rouge + texte "Erreur"
  - **Transition processing → idle** : flash de succes vert (cercle solide qui fade out en 0.5s)
- **Aura recording** (5 couches QPainter, replique orb.html) :
  - **Shadow layer** (couche 0) : QRadialGradient noir, rayon serre autour du logo
  - **Outer aura** (couche 1) : QRadialGradient indigo→bleu
  - **Core glow** (couche 2) : QRadialGradient cyan→bleu
  - **Particules** (couche 3) : 15 points animes orbitant autour du logo
  - **Edge ring** (couche 4) : anneau fin noir semi-transparent au bord de l'aura
- **Hover icons** : au survol du logo (idle uniquement), 2 boutons ronds apparaissent (settings + quit)
- **API identique** a l'ancien WaveformWidget : `set_state()`, `update_amplitude()`, `update_step()`, `set_error_text()`, `show_preview()`, `on_quit_clicked`
- **Tray icon** : menu avec icones unicode et separateurs (▶ Dictee / ⚙ Parametres / ❓ Aide / ✧ Licence / ⓘ A propos / ✕ Quitter). Clic gauche tray → ouvre directement les Parametres (via `_on_settings`)
- **Barre des taches Windows** : `_TaskbarWindow` (dans `app.py`) — fenetre fantome minimisee (opacity=0, WA_ShowWithoutActivating) qui donne a l'app une presence permanente dans la barre des taches avec le logo VoxWave.
  - Necessite `SetCurrentProcessExplicitAppUserModelID("com.voxwave.app")` (via `ctypes`) appele avant la creation de la fenetre
  - **Clic sur l'icone** : intercepte via `nativeEvent` + `WM_SYSCOMMAND SC_RESTORE` (0x0112 / 0xF120). Message consomme (`return True, 0`) pour empecher le flash. Appele EXACTEMENT une fois par clic. Sur Linux : fallback via `changeEvent`.
  - **Logo** : `force_taskbar_icon_win32(hwnd)` dans `icons.py` — sauvegarde logo en ICO temporaire, envoie `WM_SETICON` via `LoadImageW` + `SendMessageW`. Appele avec `QTimer.singleShot(300ms)` apres demarrage event loop (l'Explorateur Windows cree le bouton taskbar de maniere asynchrone).
  - **PIEGE** : ne jamais appeler `force_taskbar_icon_win32` immediatement dans `__init__` — l'Explorateur n'a pas encore cree le bouton, l'icone est ignoree.
- **`setQuitOnLastWindowClosed(False)`** : l'app ne quitte plus quand on ferme un dialog

## Plateforme
- **Windows + Linux uniquement** — macOS non supporte (check au demarrage dans `app.py`, `sys.exit(1)`)
- Warning dans `keyboard.py` et `orb_widget.py` si `sys.platform == "darwin"`
- Raison : Wispr Flow et Aqua Voice dominent sur Mac, aucun concurrent serieux sur Windows/Linux

## Profils d'app (window_detector.py)
Detection automatique de l'app active → prompt LLM adapte. Mapping `_APP_PROFILES` (exe → profil) :
- **`code`** : VS Code, Cursor, Windsurf, PyCharm, IntelliJ, Sublime, Notepad++, Zed, Fleet, Lapce, Emacs, Vim/Neovim + terminaux (WindowsTerminal, cmd, PowerShell, bash, zsh, fish, Konsole, gnome-terminal, Alacritty, WezTerm, Kitty, Rio, Ghostty) → regex uniquement, pas de LLM
- **`casual`** : Slack, Discord, Telegram, WhatsApp, Signal, Teams, MS Teams (`msteams`), Zoom → ton decontracte
- **`email`** : Outlook, nouveau Outlook (`olk`), Thunderbird, Mailspring → grammaire formelle, ton professionnel
- **`document`** : Word, LibreOffice, Notion, Obsidian, Logseq → nettoyage adapte a la redaction structuree
- **`default`** : toute app non reconnue → correction maximale

Fichier : `src/utils/window_detector.py`. Fonction `get_app_profile(exe_name)` normalise le nom (.exe/.app supprime, lowercase) puis lookup dans `_APP_PROFILES`.

## Onboarding v2.2 (welcome_dialog.py) — Inspire Wispr Flow
9 pages avec indicateur de progression (dots + messages encourageants) :
1. **Bienvenue** : logo + bullets + bouton Commencer
2. **Langue interface** : QComboBox (15 langues), sauvegardee dans `config["language"]`
3. **Langue dictee** : QComboBox ("Auto-detect" + 99 langues Whisper), sauvegardee dans `config["whisper"]["language"]` — pre-selectionne la langue d'interface
4. **Pourquoi VoxWave ?** : 4 cartes multi-select (motivations), Suivant bloque sans selection
5. **Raccourci clavier** : HotkeyCapture, no-skip 3s (Suivant desactive temporairement)
6. **Test micro** : test 3s avec barre de volume + bip audio (play_start/play_stop via AudioFeedback)
7. **Demo interactive** : bouton Dicter toggle, QTextEdit resultat, transcription dans un thread, bouton Passer apres 10s
8. **Ton d'ecriture** : 2 cartes radio (Brut/Auto) avec exemples
9. **Pret !** : rappel hotkey + mode d'ecriture + indication tray

### Widgets custom onboarding
- `_ProgressDots` : 9 cercles peints via QPainter + "Etape X sur 9"
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
- Classe principale `VoxWave`
- `_on_settings()` gere 7 parametres : hotkey, cleaning mode, langue, micro, transcription provider, cleaning provider, ollama_host
- `_on_help()` ouvre les settings directement sur l'onglet Aide via `navigate_to_help()`
- **PIEGE `parent=`** : `SettingsDialog(parent=None)` — JAMAIS `parent=self._taskbar._win`. La fenetre taskbar est minimisee (opacity=0), Qt bloque `raise_()/activateWindow()` sur un child dont le parent est minimise. Le flag `Qt.WindowType.Tool` (dans `_setup_window`) gere le groupement taskbar sans parent.
- `_focus_existing_dialog()` : ramene un dialog existant au premier plan (show + raise + activateWindow + `_force_foreground_win32` Win32 API + retries 50/150ms)
- `_force_foreground_win32()` : AttachThreadInput + ShowWindow + BringWindowToTop + SetForegroundWindow + TOPMOST/NOTOPMOST
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
- **Thread safety** : callbacks `on_start`/`on_stop`/`on_busy` transitent via `_HotkeyBridge`
  (QObject avec signals) → dispatché vers le thread Qt principal. Ne jamais appeler directement
  des méthodes Qt depuis le thread pynput.
- **`on_busy` callback** : appelé quand hotkey pressé pendant `_is_processing = True` →
  déclenche une notification tray traduite (`_BUSY_T` dans `app.py`)

## Injection progressive (progressive_injector.py)

Pipeline en 2 temps pour la latence < 1s :
1. `inject_raw(raw_text)` → texte brut via clipboard (retry 3x + vérification) + Ctrl+V immédiatement (~200ms)
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
1. **Timeout dynamique** depuis `inject_raw` : `5s base + 10ms/char, cap 30s` (fonction `_compute_replace_timeout`, via `time.monotonic()`, immunisé NTP)
2. **Aucune action utilisateur** (touche ou clic) — listeners pynput clavier + souris en arrière-plan

Si une condition échoue → `_stop_user_watch()` + `return` (texte brut conservé, silent fallback).
`_stop_user_watch()` est appelé dans **toutes** les branches (pas de thread actif qui traîne).
- **PIÈGE mode raw** : si `cleaning_mode == "raw"`, `replace_with_clean()` n'est jamais appelé →
  appeler `self._prog_injector._stop_user_watch()` explicitement dans ce chemin.
- **Clipboard** : `inject_raw()` sauvegarde le clipboard AVANT l'injection et le restaure APRÈS
  (`saved_clipboard` variable locale) — l'utilisateur retrouve son Ctrl+C original intact.
- **Clipboard retry** : `_inject_direct()` tente 3 fois `pyperclip.copy()` + vérifie `pyperclip.paste() == text`
  avant d'envoyer Ctrl+V. Si le clipboard est verrouillé par un autre process → fallback `_injector.inject()`.
- **200ms buffer** : délai avant restauration du clipboard (100ms insuffisant pour apps Electron/WinUI3).

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
python -m voxwave
python -m voxwave --model small
python -m voxwave --test
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

## Release & Distribution
- **GitHub** : https://github.com/farnel94-source/voxwave-app (public, master)
- **Release v0.1.1** (latest) : https://github.com/farnel94-source/voxwave-app/releases/tag/v0.1.1
  - `VoxWave-Setup-0.1.1.exe` (109 MB) — installateur Windows (Inno Setup)
  - `VoxWave-x86_64.AppImage` (148 MB) — Linux
- **Release v0.1.0** : https://github.com/farnel94-source/voxwave-app/releases/tag/v0.1.0
- **Python Windows** : 3.14.2 (`C:\Python314`) — surveiller compatibilite libs
- **Python WSL** : 3.12.3 (`/usr/bin/python3`) — virtualenv `.venv` pour build
- **Icone** : `assets/icon.ico` genere depuis `create_icon("idle")` dans `icons.py` (cercle bleu fonce + vagues blanches). Ne PAS utiliser `logo.png` (ancien logo).

## Dependances Linux
```bash
sudo apt install libxcb-cursor0 xclip xdotool
```
- `libxcb-cursor0` — requis pour l'interface Qt
- `xclip` — requis pour les operations clipboard sur X11
- `xdotool` — fallback injection texte sur X11

## Mode local — Conseils utilisateur
- Recommander de **fixer la langue de dictee** (pas auto-detect) en mode local
- Le modele Whisper `base` est mauvais en auto-detection de langue mais OK avec langue fixee
- Le modele `small` est plus precis mais trop lent sur CPU sans GPU (RTF 5-11)
- Auto-detect fonctionne bien en mode cloud (Groq)

## Build — Pieges connus
- **webrtcvad-wheels** : ajouter `webrtcvad` dans `excludes` ET `hiddenimports` du `.spec` (hook PyInstaller incompatible avec `webrtcvad-wheels`)
- **Inno Setup** : `SetupIconFile` doit pointer vers un `.ico` (pas `.png`) — actuellement `assets/icon.ico`
- **PIL ICO multi-tailles** : utiliser `images[-1].save('icon.ico', format='ICO', append_images=images[:-1])`, pas `sizes=`
- **Cache icones Windows** : apres recompilation, `taskkill /IM explorer.exe /F` + `explorer.exe` pour voir la nouvelle icone
- **site-packages cross-platform** : Linux = `.venv/lib/python3.X/site-packages/`, Windows = `C:\Python314\Lib\site-packages/` (pas de `.venv` sur Windows de Farnel). Le `.spec` utilise `importlib.util.find_spec('faster_whisper')` sur Windows pour trouver le bon chemin automatiquement.
- **`sys.stdout` None en mode windowed** : PyInstaller `--noconsole` met `sys.stdout = None`. Toujours `if sys.stdout is not None:` avant `reconfigure()`.
- **`config.yaml` bundle** : PyInstaller copie le `config.yaml` du projet tel quel. Ne JAMAIS laisser `first_launch: false` dedans — ca skip l'onboarding pour tous les utilisateurs. Le config source ne doit PAS contenir `first_launch` (le defaut `True` vient de `DEFAULT_CONFIG`).
- **`silero_vad_v6.onnx`** : necessaire pour `faster_whisper` avec `vad_filter=True`. Doit etre bundle dans `faster_whisper/assets/` du build.

## Lancement — Avancement (2 avril 2026)
- [x] Repo GitHub public
- [x] Build Windows + Linux + Release v0.1.0 (rebuild QPainter 103 MB + AppImage 157 MB)
- [x] Mettre a jour liens download dans landing (8 corrections dans 5 fichiers)
- [x] Changelog landing mis a jour (fausses versions 1.x → vraie v0.1.0)
- [x] Landing page deployee sur Vercel : https://voxwave-landing.vercel.app/
- [x] Landing page repo GitHub prive : https://github.com/farnel94-source/voxwave-landing
- [x] Fixes Linux : branche fix/linux-bugs mergee dans master (16 commits, 15 fichiers)
- [x] Release v0.1.1 publiee (Windows 109 MB + Linux 148 MB)
- [x] README + CHANGELOG mis a jour (deps Linux, tips mode local, v0.1.1)
- [x] Landing mise a jour (changelog v0.1.1, guide Linux, tips mode local, liens download)
- [x] Backend deploye sur Render (free tier) + Neon PostgreSQL : https://voxwave-backend.onrender.com
- [x] Repo backend GitHub prive : https://github.com/farnel94-source/voxwave-backend
- [x] Newsletter connectee (landing → backend → Neon)
- [x] Download tracking connecte (landing → backend → Neon)
- [ ] Acheter domaine custom (voxwave.app ou autre) et configurer sur Vercel
- [ ] Configurer LemonSqueezy (non bloquant, lancement gratuit possible)
- [ ] Code signing Windows (optionnel, certificat ~$70-200/an)
- [x] Endpoints proxy v0.2.0 : POST /api/v1/transcribe + /api/v1/clean (securise les cles API)
- [x] Auth proxy : X-App-Token header, PROXY_APP_TOKEN sur Render
- [x] Keep-alive backend : self-ping toutes les 14 min (plus de cold start Render)
- [x] Mode proxy dans l'app : ProxyTranscriptionEngine + ProxyLLMCleaner + fallback local
- [ ] Integration telemetrie dans l'app VoxWave (activate, heartbeat, error, feedback dialog, opt-out)
- [ ] Rendre la version configurable dans build.py (actuellement renomme manuellement)
