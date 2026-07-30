# Remote Mouse Wiki

Welcome to the Remote Mouse project wiki. This is a collaborative knowledge base for contributors and maintainers.

## Contents

| Page | Description |
|------|-------------|
| [SETUP](SETUP.md) | Development environment setup and prerequisites |
| [ARCHITECTURE](ARCHITECTURE.md) | Design decisions and architecture rationale |
| [DEVELOPMENT](DEVELOPMENT.md) | Development workflow, testing, and conventions |
| [FAQ](FAQ.md) | Frequently asked questions |
| [CHANGELOG](CHANGELOG.md) | Version history and release notes |
| [PLAN](PLAN.md) | Roadmap and future version plan |
| [Version Control](../version_control.md) | Version plan and roadmap |

---

## Quick Links

- **User Documentation:** [`docs/`](../docs/) (HTML pages)
- **Source Code:** [`src/`](../src/)
- **Frontend:** [`frontend/`](../frontend/)
- **Version Control Plan:** [`version_control.md`](../version_control.md) (local only)

---

## Project Status

- **Current Version:** v1.1.0 (Security Release)
- **Phase:** Active development
- **Target:** v6.0.0 (120 versions across 30 mouse hardware specs)
- **Current Score:** 35/100 vs wired mouse

## Security Features

v1.1.0 introduced comprehensive security hardening:

- **Pairing auth** — 6-char code displayed on laptop, must be entered on phone
- **Rate limiting** — 30 calls/sec per action per session
- **CORS validation** — dynamic origin checking (no wildcard)
- **Action allowlist** — only 9 approved socket events
- **FAILSAFE re-enabled** — pyautogui emergency kill switch
- **OS key blocklist** — Ctrl+Alt+Del, Win+L, etc.
- **PII redaction** — all logs scrubbed of emails, URLs, IPs
- **Security headers** — CSP, X-Frame-Options, etc.
- **Static whitelist** — only approved extensions served
- **Dependency pins** — minimum secure versions enforced
- **Subprocess hardening** — shutil.which + stdin=DEVNULL
- **Buffer limit** — 64 KB max WebSocket payload
