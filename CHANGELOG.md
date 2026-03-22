# Changelog

All notable changes to VoxWave will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-03-22

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
