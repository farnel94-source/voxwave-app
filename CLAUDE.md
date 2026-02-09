# CLAUDE.md — Instructions pour Claude Code

## Projet
**VoxTool** : Outil de dictée vocale desktop.
Parle → Transcrit (Whisper) → Nettoie (regex + LLM) → Colle le texte propre.

## Stack
- Python 3.11+
- faster-whisper (transcription locale, fallback)
- Groq API + whisper-large-v3 (transcription cloud, prioritaire)
- OpenAI GPT-4o-mini (nettoyage cloud, prioritaire)
- Ollama local gemma3:4b (nettoyage local, fallback)
- sounddevice (capture audio)
- webrtcvad (détection de voix)
- pynput (hotkey + injection clavier)
- pyperclip (clipboard)
- pystray (icône system tray)
- PyInstaller (packaging)
- LemonSqueezy (licensing)
- python-dotenv (chargement .env)

## Structure
```
voxtool/
├── src/
│   ├── __init__.py
│   ├── app.py                # Point d'entrée principal
│   ├── audio/
│   │   ├── capture.py        # Capture micro + VAD
│   │   └── processor.py      # Traitement audio
│   ├── transcription/
│   │   ├── whisper_engine.py  # Moteur faster-whisper (local)
│   │   ├── groq_engine.py    # Moteur Groq API (cloud)
│   │   └── hybrid_engine.py  # Hybride: Groq → Whisper local
│   ├── cleaning/
│   │   ├── regex_cleaner.py   # Nettoyage rapide regex
│   │   └── llm_cleaner.py    # Nettoyage: OpenAI cloud + Ollama local
│   ├── injection/
│   │   └── keyboard.py       # Injection texte
│   └── hotkey/
│       └── listener.py       # Écoute raccourci clavier
├── tests/
├── config.yaml
├── requirements.txt
└── setup.py
```

## Pipeline
```
F8 (start) → Capture audio → F8 (stop) → Transcription (Groq cloud → Whisper local) → Nettoyage (OpenAI → Ollama → regex) → Injection texte
```

## Mode hybride
- **Transcription** : Groq API (whisper-large-v3) en priorité, fallback faster-whisper local
- **Nettoyage** : OpenAI GPT-4o-mini en priorité, fallback Ollama local, fallback regex
- Config `transcription.provider` et `cleaning.provider` : `hybrid` | `cloud` | `local`
- Clés API dans `.env` : `GROQ_API_KEY`, `OPENAI_API_KEY`

## Règles de code
1. Type hints sur toutes les fonctions
2. Docstrings Google style
3. logging (jamais print)
4. Tests pytest pour chaque module
5. Gestion erreurs gracieuse, jamais de crash silencieux
6. Multiplateforme : macOS, Windows, Linux
7. Config via config.yaml, pas de valeurs hardcodées

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

## Priorités
1. Fonctionnel (ça marche)
2. Fiable (pas de crash)
3. Rapide (pipeline < 3s)
4. Propre (maintenable)
