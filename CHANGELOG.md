# Changelog

All notable changes to VoxWave will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.1] — 2026-04-01

### Fixed
- Orb widget transparency on Linux (offscreen QImage rendering with X11 alpha compensation)
- Clipboard injection on X11 with xclip verification and xdotool fallback
- Whisper language detection: neutral hints on first call, interface language fallback
- PyInstaller windowed mode crash (sys.stdout None guard)
- Cross-platform build: automatic site-packages detection for Windows and Linux
- Dark background for settings dialog on Linux
- Orb corner clipping using native X11 QRegion
- Hallucination detection with new patterns

### Added
- Single-instance lock to prevent double-launch (Linux + Windows)
- Bundled Silero VAD model in AppImage for reliable voice activity detection
- AppImage icon discovery via .DirIcon symlink
- Interface language parameter for local Whisper provider

## [0.1.0] — 2026-03-23

### Added
- Hybrid transcription: Groq cloud (whisper-large-v3-turbo) + local Whisper fallback
- LLM cleaning cascade: OpenAI GPT-4o-mini → Ollama gemma3:4b → regex
- Progressive injection: raw text in <1s, silently replaced with cleaned version
- 15 interface languages (EN, FR, ES, DE, IT, PT, NL, JA, KO, ZH, RU, AR, TR, PL, SV)
- 15 filler word languages for regex cleanup
- Hallucination detection: 35+ known Whisper patterns rejected
- Circuit breaker: automatic cloud → local failover
- Custom hotkey with live capture (F8 default)
- 9-page onboarding wizard (hotkey, language, mic test, demo, writing tone)
- Modern settings dialog with sidebar navigation (5 sections)
- Floating orb widget with reactive aura canvas and 4 states
- Auto-stop via Silero VAD (configurable silence duration)
- Context-aware cleanup: adapts writing style per app (Slack, Word, terminal, etc.)
- Auto-update via GitHub Releases API (12h cache)
- Windows installer (Inno Setup, 10 languages)
- Linux AppImage
- Licensing system (LemonSqueezy integration)
- Full offline mode (Whisper + Ollama + regex)
- 40+ test files covering audio, transcription, cleaning, injection, licensing

### Security
- Audio processed in RAM only, never stored on disk
- API keys in .env (gitignored), never hardcoded
- No telemetry
