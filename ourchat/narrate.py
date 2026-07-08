#!/usr/bin/env python3
"""
narrate.py — the OPTIONAL AI layer. Runs only when an LLM is configured
(KAKAO_LLM_PROVIDER != none). Pre-generates rich text into static JSON so the
dashboard stays a pure static site (no runtime backend):

  topics_named.json   topic names + categories (from topic exemplars)
  narrative.json      the room's overall arc + per-month headlines
  characters.json     data-grounded character profiles for notable members

Everything degrades gracefully: if the LLM is absent or a call fails, the file is
skipped and the deterministic dashboard still works. No raw messages are stored;
only the generated summaries.
"""
import argparse, json, os, sys, subprocess, collections, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm

HERE = os.path.dirname(os.path.abspath(__file__))


def name_topics(D):
    tp = json.load(open(os.path.join(D, "topics.json"), encoding="utf-8"))
    out = []
    for t in tp.get("topics", []):
        ex = "\n".join(f"- {e['text']}" for e in t.get("exemplars", [])[:6])
        o = llm.chat_json(
            "Name a chat topic cluster. Output JSON only. Use the room's language.",
            f"Frequent terms: {', '.join(t.get('terms', [])[:10])}\nSample messages:\n{ex}\n\n"
            'JSON: {"name":"<short specific label>","category":"<one word>","summary":"<1 sentence>"}',
            max_tokens=200, temperature=0.4) or {}
        out.append({"id": t["id"], "name": o.get("name") or t["label"], "category": o.get("category", ""),
                    "summary": o.get("summary", ""), "size": t["size"], "peak_week": t.get("peak_week")})
    json.dump({"topics": out}, open(os.path.join(D, "topics_named.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return len(out)


def arc(D):
    meta = json.load(open(os.path.join(D, "meta.json"), encoding="utf-8"))
    tl = json.load(open(os.path.join(D, "timeline.json"), encoding="utf-8"))
    months = tl.get("month", [])
    digest = " | ".join(f"{m['key']}: {m['n']}건, {'/'.join(m['keywords'][:4])}" for m in months)
    o = llm.chat_json(
        "You write a short history of a group chat from its monthly stats. Output JSON only, in the room's language.",
        f"Room: {meta.get('room')} · {meta.get('messages')} msgs · {meta.get('participants')} people\n"
        f"Monthly: {digest}\n\n"
        'JSON: {"arc":"<3-5 sentence overall story>","months":[{"key":"YYYY-MM","headline":"<short>","summary":"<1-2 sentences>"}]}',
        max_tokens=1200, temperature=0.5) or {}
    if o:
        json.dump(o, open(os.path.join(D, "narrative.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return bool(o)


def characters(D, top=16):
    # build dossiers first
    subprocess.run([sys.executable, os.path.join(HERE, "char_dossier.py"), "--dir", D, "--top", str(top)],
                   capture_output=True)
    inp = os.path.join(D, "char_input.json")
    if not os.path.exists(inp):
        return 0
    people = json.load(open(inp, encoding="utf-8")).get("people", [])
    out = []
    for p in people:
        feats = p.get("stats", {})
        samples = "\n".join(f"- {s['text']}" for s in (p.get("top_reacted", []) + p.get("samples", []))[:6])
        conns = ", ".join(c["name"] for c in p.get("partners", [])[:4])
        o = llm.chat_json(
            "Write a 3rd-person character profile of a chat member from their data. JSON only, room's language. "
            "No emoji/markdown. Never invent personal info (phone/real name).",
            f'Person: "{p["name"]}" · {feats}\nOften talks with: {conns}\nTheir messages:\n{samples or "(few)"}\n\n'
            'JSON: {"title":"<8-16 char nickname>","personality":"<2-3 sentences>","style":"<1-2>",'
            '"role":"<1 sentence>","signature_quote":"<short quote>","stat_highlight":"<one standout number in words>"}',
            max_tokens=500, temperature=0.6) or {}
        if o.get("personality"):
            out.append({"name": p["name"], "archetype": p.get("archetype", ""), **o,
                        "hangs_with": [c["name"] for c in p.get("partners", [])[:3]]})
    if out:
        json.dump({"characters": out}, open(os.path.join(D, "characters.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    return len(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    if not llm.available():
        print(json.dumps({"ok": True, "skipped": "no LLM configured"}, ensure_ascii=False)); return
    r = {"topics_named": 0, "arc": False, "characters": 0}
    try: r["topics_named"] = name_topics(a.dir)
    except Exception as e: print(f"[narrate] topics: {e}")
    try: r["arc"] = arc(a.dir)
    except Exception as e: print(f"[narrate] arc: {e}")
    try: r["characters"] = characters(a.dir)
    except Exception as e: print(f"[narrate] characters: {e}")
    print(json.dumps({"ok": True, **r}, ensure_ascii=False))


if __name__ == "__main__":
    main()
