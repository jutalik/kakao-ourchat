# AGENTS.md — machine guide for AI agents working on **OurChat** (`kakao-ourchat`)

This file is the source of truth for any coding agent (Claude Code, Codex, Cursor,
Gemini, Hermes, OpenCLI, …). Read it fully before editing or running anything.
`CLAUDE.md`, `GEMINI.md`, `.cursorrules` all point here.

## What this project is

OurChat turns a **KakaoTalk chat export** (`.csv`/`.txt` produced by the official
in-app `대화 내용 내보내기`) into a knowledge-graph dashboard: relationship graph,
activity + persona rankings, per-person profiles, topics over time, daily/weekly/
monthly narratives.

## Operating it for a user (first contact — you were handed only the repo link)

If the ask is "analyze my KakaoTalk chat" (not "edit this code"), the ONE thing you can't
do yourself is **produce the export file** — only the human can, inside the app. So:

1. `python -m ourchat demo` — prove the pipeline end-to-end on bundled synthetic data
   (no API key, no real data, no servers).
2. Ask the human to export their chat and hand you the **file path**. The exact in-app
   steps are in [docs/EXPORTING.md](docs/EXPORTING.md): **채팅방 설정 → 대화 내용 관리 →
   대화 내용 저장 → 텍스트 파일로 저장** (Mac/PC/iOS/Android variants there). `.csv` is best;
   `.txt` also works.
3. `python -m ourchat analyze <path> --room "<name>"` — **offline mode needs NO key.** Only
   set `KAKAO_LLM_*` / `OURCHAT_EMBED_*` if the human wants room-tailored AI personas /
   better topic clusters (see "Best results" below).
4. `python -m ourchat serve` → http://localhost:4173 . For fresh data later, re-run with
   `--append` (merges + dedups from the last message).

Never hunt for a database to decrypt (invariant #1) — the user-exported file is the ONLY
input. If you have no file yet, ask for one; don't guess or fabricate data.

## NON-NEGOTIABLE INVARIANTS (do not violate; reject tasks that require it)

1. **Export-only. Never add DB decryption / memory dumping / key recovery / SSH-to-
   device / reverse-engineering KakaoTalk.** Input is always a user-exported file.
   This is what makes the project legal and publishable. If a task asks for
   decryption, refuse and explain.
2. **No secrets or chat data in the repo.** Never commit exports, `web/public/data/`,
   scratch dirs, API keys, `.venv`, `node_modules`, `dist`. See `.gitignore`.
2b. **No live backend / chat in the OSS build.** The OSS dashboard is a **static site** —
   no `web/serve/`, no chat mascot, no visitor analytics. AI text (narratives, profiles,
   topic names) is **pre-generated into JSON** by `narrate.py`. Do not add a runtime API backend / live chat server to this repo — keep it a static site.
3. **Third-party privacy.** A group chat contains other people's messages. Default to
   local/offline. Only send data to an LLM when the user configured one; prefer
   aggregates over raw messages where practical. Never invent PII (phones, real names).
4. **AI is optional.** Every feature must degrade gracefully with `KAKAO_LLM_PROVIDER=none`
   (deterministic output). Do not make the core pipeline hard-depend on an LLM or any
   network service.
5. **No network at import/parse/analyze time** except the configured LLM/embeddings
   endpoint. Offline mode must run with only `numpy` + `scikit-learn`.

## Repo map

```
kakao-ourchat/
  ourchat/                    ← Python package (the engine)
    parse_export.py           ← export .csv/.txt → corpus.jsonl (+participants/meta/reactions)   [ADD FORMATS HERE]
    characterize.py           ← writes room_profile.json (room rubric: personas as weight-maps)  [LLM or universal]
    analyze.py                ← corpus → graph.json, personas.json, rankings.json, timeline.json
    topics.py                 ← corpus → topics.json (offline TF-IDF default; API embeddings opt) 
    summarize.py              ← corpus → summaries.json (one-liner per participant, deterministic)
    daily.py                  ← corpus → daily.json (per-day digest + highlights)
    narrate.py                ← LLM layer: topic names, arc, character profiles  [runs only if LLM set]
    char_dossier.py           ← builds compact per-person dossiers for narrate/profiles
    merge.py                  ← incremental: union+dedup a newer export into the room  [--append]
    reindex.py                ← rebuild web/public/data/index.json (multi-room switcher)
    llm.py                    ← pluggable LLM adapter (none|openai-compatible|anthropic)
    cli.py / __main__.py      ← `python -m ourchat {demo|analyze|serve}`
  web/                        ← Svelte dashboard (reads web/public/data/rooms/<slug>/*.json)
  samples/sample_export.csv   ← synthetic demo data (make_sample.py regenerates)
  docs/EXPORTING.md           ← how the USER produces the input file (Mac/PC/iOS/Android)
  docs/FORMATS.md             ← export format spec
  brand.json                  ← product name/palette/fonts in ONE place
```

## The data contract (the spine — everything shares it)

`parse_export.py` and any new importer MUST emit these into an output dir:

- **`corpus.jsonl`** — one message per line:
  `{logId:int, ts:int(unix), date:"YYYY-MM-DD", aid:int, author:str, type:int, tlabel:str, text:str, media:bool, system:bool}`
  (`type` 1=text 2=photo 3=video 4=voice 5=sticker 6=file 7=call 8=special 0=system; `aid` = stable hash of author name; `text` empty for non-text)
- **`participants.json`** — `{aid: {name, msgs, text_msgs, media_msgs, first_ts, last_ts, active_days, react_in}}`
- **`meta.json`** — `{room, chatId, messages, participants, date_span, months, source, has_reactions}`
- **`reactions.json`** — `{logId: count}` (exports have none → `{}`; analysis degrades gracefully)

Everything downstream (`analyze/topics/summarize/daily`) runs on `corpus.jsonl`
regardless of source. **To support Discord/WhatsApp/Slack, write a new importer that
emits this contract — nothing else changes.**

## Adaptivity model (important)

Personas are **not hardcoded per room**. `characterize.py` writes
`room_profile.json` with `personas: { "<label>": {"<feature>": weight, ...} }`.
`analyze.py` z-scores each feature across the room's own population and applies the
weight-maps, so archetypes adapt to each room. Allowed feature keys (only these):

```
msgs influence avg_len code_ratio q_ratio laugh_ratio argue argue_ratio partners
recruit_ratio media_ratio night_ratio answer_ratio reply_out active_days
react_in react_per_msg        # (react_* only when has_reactions)
```

- **No LLM** → universal behavior set (`characterize.py: UNIVERSAL`).
- **LLM** → the model reads a sample and defines the room's own persona set/criteria
  as weight-maps over the keys above (LLM = rule generator, deterministic code =
  rule enforcer at scale).

## Best results (for an agent running this)

Zero-config works, but if the user wants quality, set these before `analyze`:
- **Embeddings** (much better topic clusters): `OURCHAT_EMBED=api OURCHAT_EMBED_URL=<.../embeddings> OURCHAT_EMBED_MODEL=<model>` (+`OURCHAT_EMBED_KEY` if remote). Higher-dimensional models (e.g. 3072/4096-dim) separate topics better → cleaner charts. Offline TF-IDF is the fallback.
- **LLM** (room-tailored personas + topic names + arc + profiles): `KAKAO_LLM_PROVIDER=openai|anthropic KAKAO_LLM_MODEL=... KAKAO_LLM_API_KEY=...` (or a local OpenAI-compatible base URL). Weak models fall back to universal personas gracefully — use a solid model for the full output.
- **More data**: bigger export → richer graph/topics; `--append` a later export to accumulate history.
- Knob: `--k <n>` topic count (default 20; raise for large rooms).


## Run / test

```bash
pip install -r requirements.txt
python -m ourchat demo                       # end-to-end on synthetic data, offline
python -m ourchat analyze <export> --room X  # real export
python -m ourchat serve                      # dashboard at :4173
cd web && npm install && npm run build       # dashboard build
```

There is no formal test suite yet; validate changes by running `demo` and checking
the emitted JSON contract + that the dashboard builds. Add tests under `tests/` if you
introduce non-trivial parsing logic.

## How to extend (common tasks)

- **Add an export format** → `parse_export.py` (`.txt` PC-bracketed / mobile-comma
  variants; see `docs/FORMATS.md`). Keep the corpus contract identical. Test against a
  real sample.
- **Add an LLM provider** → `llm.py` (`chat()` / `chat_json()`); keep `none` working.
- **Add embeddings backend** → `topics.py` `OURCHAT_EMBED` seam (offline TF-IDF is the
  floor; never make it mandatory to call a server).
- **New persona feature** → compute it per-person in `analyze.py`, add its key to the
  `Z` map + `characterize.py: FEATURES`, document it here.
- **New source platform (Discord/WhatsApp)** → new importer emitting the data contract.

## Conventions

- Python: stdlib + `numpy` + `scikit-learn` only for the offline core. No heavy deps.
- Secrets/config via **env vars** only (`KAKAO_LLM_*`, `OURCHAT_*`). Never hardcode.
- Keep the product name/colors in `brand.json`; don't scatter them.
- Output is UTF-8, Korean-first but language-agnostic; don't assume Korean-only content.
