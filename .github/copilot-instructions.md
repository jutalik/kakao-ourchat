This repo is agent-configured via **AGENTS.md** (the cross-tool standard) — read it fully:
architecture, invariants, data contract, how to run/extend, and the "first contact"
runbook for operating it on a user's chat.

Key invariants (do not violate):
- **Export-only.** Never add KakaoTalk DB decryption / key recovery / reverse-engineering.
  The input is always a file the user exported from the app (`.csv`/`.txt`).
- **Static site.** The OSS dashboard has no runtime backend or chat server; all AI text is
  pre-generated into JSON at analyze time.
- Never commit chat data or API keys. Offline mode (numpy + scikit-learn) must keep working
  with no LLM configured.
