#!/usr/bin/env python3
"""
merge.py — incremental update. KakaoTalk re-exports the full visible history each
time (and old messages roll off the client), so the robust way to "continue from the
last data" is to UNION every export you've made and de-duplicate. Attach a newer
export → it merges with what's already there, picking up the new tail while keeping
older messages a fresh export may have dropped.

  merge.py --base <workdir> --add <new-parsed-dir>

Merges <new>/corpus.jsonl into <base>/corpus.jsonl (dedup on ts+author+text),
re-sorts by time, renumbers logId, and recomputes participants.json + meta.json.
"""
import argparse, json, os, datetime, collections


def load(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8")]


def key(r):
    return (r["ts"], r["aid"], r.get("tlabel", ""), (r.get("text") or "")[:120])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)   # working dir (accumulated)
    ap.add_argument("--add", required=True)     # freshly parsed new export dir
    ap.add_argument("--room", default="")
    a = ap.parse_args()
    os.makedirs(a.base, exist_ok=True)
    base = load(os.path.join(a.base, "corpus.jsonl"))
    add = load(os.path.join(a.add, "corpus.jsonl"))

    seen = set(); merged = []
    for r in base + add:                       # base first; dedup keeps first seen
        k = key(r)
        if k in seen: continue
        seen.add(k); merged.append(r)
    merged.sort(key=lambda r: (r["ts"], r["logId"]))
    added = len(merged) - len(base)

    part = collections.defaultdict(lambda: {"name": None, "msgs": 0, "text_msgs": 0,
        "media_msgs": 0, "first_ts": None, "last_ts": None, "days": set(), "react_in": 0})
    months = collections.Counter()
    with open(os.path.join(a.base, "corpus.jsonl"), "w", encoding="utf-8") as f:
        for i, r in enumerate(merged, 1):
            r["logId"] = i
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            months[r["date"][:7]] += 1
            p = part[r["aid"]]; p["name"] = r["author"]; p["msgs"] += 1
            if r["type"] == 1: p["text_msgs"] += 1
            if r.get("media"): p["media_msgs"] += 1
            p["first_ts"] = r["ts"] if p["first_ts"] is None else min(p["first_ts"], r["ts"])
            p["last_ts"] = r["ts"] if p["last_ts"] is None else max(p["last_ts"], r["ts"])
            p["days"].add(r["date"])
    participants = {str(aid): {"name": p["name"], "msgs": p["msgs"], "text_msgs": p["text_msgs"],
        "media_msgs": p["media_msgs"], "first_ts": p["first_ts"], "last_ts": p["last_ts"],
        "active_days": len(p["days"]), "react_in": 0} for aid, p in part.items()}
    json.dump(participants, open(os.path.join(a.base, "participants.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({}, open(os.path.join(a.base, "reactions.json"), "w"))
    fts = [p["first_ts"] for p in participants.values() if p["first_ts"]]
    span = [datetime.datetime.fromtimestamp(min(fts)).strftime("%Y-%m-%d"),
            datetime.datetime.fromtimestamp(max(p["last_ts"] for p in participants.values() if p["last_ts"])).strftime("%Y-%m-%d")] if fts else [None, None]
    room = a.room
    if not room:
        try: room = json.load(open(os.path.join(a.base, "meta.json")))["room"]
        except Exception: room = "KakaoTalk"
    meta = {"room": room, "chatId": 0, "messages": len(merged), "participants": len(participants),
            "date_span": span, "months": dict(sorted(months.items())), "source": "export-merged", "has_reactions": False}
    json.dump(meta, open(os.path.join(a.base, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"ok": True, "total": len(merged), "added": added, "span": span}, ensure_ascii=False))


if __name__ == "__main__":
    main()
