#!/usr/bin/env python3
"""
characterize.py — figure out what KIND of room this is and DEFINE its analysis
rubric, per room. This is where the template adapts: instead of hardcoded personas,
the LLM reads a sample of the room and emits room_profile.json — room type, themes,
and a persona set tailored to THIS room, each as weights over the universal feature
keys. analyze.py then applies that rubric to everyone (LLM defines rules, deterministic
code enforces them at scale).

Modes:
  1) no LLM (KAKAO_LLM_PROVIDER=none) → writes a UNIVERSAL behavior-based persona set
     (works for any room/culture: volume, questioning, humor, connectivity, lurking…)
  2) BYO LLM / 3) hosted cloud → LLM tailors personas + themes to this specific room.

Runs on the corpus.jsonl produced by parse_export.py or extract.py.
"""
import argparse, json, os, collections, datetime, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm

# feature keys analyze.py can score on (must match its Z map)
FEATURES = ["msgs", "influence", "avg_len", "code_ratio", "q_ratio", "laugh_ratio",
            "argue", "argue_ratio", "partners", "recruit_ratio", "media_ratio",
            "night_ratio", "answer_ratio", "reply_out", "active_days"]

UNIVERSAL = {
    "수다왕":   {"msgs": 1.8, "active_days": 0.4},
    "질문러":   {"q_ratio": 1.8, "answer_ratio": -0.3},
    "답변가":   {"answer_ratio": 1.2, "influence": 0.9, "avg_len": 0.5},
    "분위기메이커": {"laugh_ratio": 1.8},
    "인싸":     {"partners": 1.6, "msgs": 0.5},
    "미디어러": {"media_ratio": 1.8},
    "링크러":   {"recruit_ratio": 1.5},
    "눈팅러":   {"msgs": -1.3, "active_days": 0.7},
    "야행성":   {"night_ratio": 1.7},
    "티키타카": {"reply_out": 1.3, "argue_ratio": 0.5},
}


def sample_messages(dir_, n=140):
    rows = [json.loads(l) for l in open(os.path.join(dir_, "corpus.jsonl"), encoding="utf-8")]
    texts = [r for r in rows if r["type"] == 1 and len(r["text"]) >= 6]
    if len(texts) > n:
        step = len(texts) / n
        texts = [texts[int(i * step)] for i in range(n)]
    return [f"{r['author']}: {r['text'][:120]}" for r in texts]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    meta = json.load(open(os.path.join(a.dir, "meta.json"), encoding="utf-8"))
    has_react = bool(meta.get("has_reactions", True))

    if not llm.available():
        prof = {"room_type": "unknown", "language": "auto", "themes": [],
                "personas": UNIVERSAL, "source": "universal-default", "llm": False}
        json.dump(prof, open(os.path.join(a.dir, "room_profile.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(json.dumps({"ok": True, "mode": "universal", "personas": list(UNIVERSAL)}, ensure_ascii=False))
        return

    sample = "\n".join(sample_messages(a.dir))
    feat = ", ".join(FEATURES) + ((", react_in, react_per_msg" if has_react else ""))
    system = ("You analyze a group chat and design its analysis rubric. Output STRICT JSON only. "
              "Personas must fit THIS room's actual culture/vibe (a family chat, gaming clan, study "
              "group, dev community and a fandom all need different archetypes). Each persona is a "
              "weight map over the allowed feature keys — positive weight = more of that feature means "
              "more this persona; negatives allowed. Use the room's own language for persona labels.")
    user = (f"Allowed feature keys (only these): {feat}\n\n"
            f"Room meta: {meta.get('messages')} messages, {meta.get('participants')} people, "
            f"span {meta.get('date_span')}.\n\nSample messages:\n{sample}\n\n"
            "Return JSON:\n{\n"
            '  "room_type": "<e.g. dev-community / friends / family / study / fandom / gaming / business>",\n'
            '  "language": "<primary language code>",\n'
            '  "tone": "<one line>",\n'
            '  "themes": ["<the room\'s real recurring themes, 4-8>"],\n'
            '  "personas": { "<label in room language>": {"<feature>": <weight>, ...}, ... 8-10 personas },\n'
            '  "topic_naming_hint": "<one line to guide topic labels>"\n}')
    prof = llm.chat_json(system, user, max_tokens=1200, temperature=0.4)
    if not prof or not isinstance(prof.get("personas"), dict):
        prof = {"room_type": "unknown", "personas": UNIVERSAL, "source": "fallback-universal", "llm": False}
    else:
        # keep only valid feature keys
        prof["personas"] = {k: {kk: float(vv) for kk, vv in w.items() if kk in FEATURES + ["react_in", "react_per_msg"]}
                            for k, w in prof["personas"].items() if isinstance(w, dict)}
        prof["source"] = "llm"; prof["llm"] = True
    json.dump(prof, open(os.path.join(a.dir, "room_profile.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"ok": True, "mode": prof.get("source"), "room_type": prof.get("room_type"),
                      "personas": list(prof["personas"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
