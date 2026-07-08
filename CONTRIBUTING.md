# Contributing to OurChat

Thanks for helping! OurChat turns a KakaoTalk chat export into a knowledge-graph dashboard.

## Ground rules (please read [AGENTS.md](AGENTS.md))
- **Export-only.** Never add DB decryption, key recovery, or device access. Input is always a
  file the user exported themselves. PRs that add decryption will be closed.
- **No chat data or secrets** in commits (see `.gitignore`). Config via env vars only.
- **AI is optional.** Everything must still work with `KAKAO_LLM_PROVIDER=none`.

## Dev setup
```bash
pip install -r requirements.txt
python -m ourchat demo          # runs the whole pipeline on synthetic data
python -m ourchat serve         # dashboard at :4173
cd web && npm install && npm run build
```

## Good first contributions
- A new export importer (Discord / WhatsApp / Slack) emitting the [corpus contract](AGENTS.md).
- A new LLM provider in `ourchat/llm.py`.
- Multilingual persona/lexicon improvements (OurChat is Korean-first but language-agnostic).
- Dashboard polish and accessibility.

## PRs
Keep them focused. Run `python -m ourchat demo` and confirm the dashboard builds before opening.
By contributing you agree your work is MIT-licensed.
