# Security & privacy

OurChat processes **personal conversation data belonging to real people**. We take that seriously.

## Design guarantees
- **No decryption / no device access.** OurChat only reads files a user exports from KakaoTalk.
- **Local-first.** Offline mode (`KAKAO_LLM_PROVIDER=none`) sends nothing anywhere.
- **No runtime backend / telemetry** in the OSS build — the dashboard is static files.
- Chat content and keys are never committed (`.gitignore`).

## For users
A group chat contains other members' messages. Get consent before sharing a dashboard, prefer
offline mode for sensitive rooms, and protect any public deployment (see [docs/HOSTING.md](docs/HOSTING.md)).

## Reporting a vulnerability
Please open a private security advisory on GitHub, or email the maintainers. Do not file public
issues for security problems. We aim to respond within 7 days.
