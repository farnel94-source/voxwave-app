# Changelog

All notable changes to VoxWave will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.1] — 2026-05-01

### Fixed
- Proxy transcription now rejects low-confidence audio (`no_speech_prob > 0.7`), aligning behavior with the direct Groq engine — silent or muted-mic audio no longer produces hallucinated text.
- Hallucination detection is now Unicode-robust: typographic apostrophes (`’` → `'`), non-breaking spaces, and composed/decomposed accents are normalized (NFKC) before lookup, so Whisper outputs like "merci d'avoir regardé" are correctly matched against the known set.

### Added
- Tray notification when no speech is detected (mic muted or weak signal).

## [0.2.0] — 2026-04-10

### Added
- Proxy mode: `transcribe` and `clean` endpoints route through the VoxWave backend so API keys (Groq, OpenAI) live server-side, never embedded in the desktop app.
- App-token authentication (`X-App-Token` header) on every proxy request.
- Anonymous usage telemetry (activate, heartbeat, error) with opt-out toggle in Settings → Advanced.
- Build-time injection of `proxy_app_token` from `config.production.yaml` (token stays out of the public repo).

### Fixed
- Hybrid mode now uses the proxy when no API key is present (instead of bypassing it and exposing `cloud` mode).
- `strip_hallucination_tails` returns the original text when stripping would empty it.
- Subprocess paths (xclip, xdotool, ollama) resolved to absolute form for security and reliability.

### Security
- Removed `.env` and `proxy_app_token` from build artifacts; tokens are now injected at build time only.
- Misleading `cloud_cleaner` warning suppressed when proxy is configured.

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
