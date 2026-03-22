# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in VoxWave, please report it responsibly.

**Do NOT open a public issue.** Instead, email the maintainer directly or use GitHub's private vulnerability reporting feature.

### What to include
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

### Response time
- Acknowledgment within 48 hours
- Fix or mitigation within 7 days for critical issues

## Scope

Security issues we care about:
- Code injection or arbitrary code execution
- API key exposure or credential leaks
- Clipboard data leaking to unauthorized processes
- Privilege escalation

## Design decisions

- **Audio is never stored on disk** — processed in RAM only
- **API keys are stored in `.env`** (gitignored) — never hardcoded
- **No telemetry** — VoxWave sends no data except to the transcription/cleaning APIs you configure
- **Local mode** — 100% offline option, no data leaves your machine
