#!/usr/bin/env python3
"""
char_dossier.py — build compact per-person dossiers for character analysis.
Deterministic: gathers each notable member's stats, most-reacted messages,
representative long messages, and top interaction partners. The LLM step
(char agent) turns each dossier into a character profile.

Reads corpus.jsonl, personas.json, rankings.json, reactions.json, graph.json,
insights.json (optional) from --dir. Writes char_input.json.
"""
import argparse, json, os, collections


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--top", type=int, default=18)
    ap.add_argument("--all", action="store_true",
                    help="dossiers for ALL rankable (text>=15), compact")
    ap.add_argument("--out", default="char_input.json")
    a = ap.parse_args()
    D = a.dir
    L = lambda n: json.load(open(os.path.join(D, n), encoding="utf-8"))
    people = L("personas.json")["people"]
    reactions = L("reactions.json")
    graph = L("graph.json")
    try:
        notable = [p["name"] for p in L("insights.json")["notable_people"]]
    except Exception:
        notable = []

    name_by_aid = {n["id"]: n["name"] for n in graph["nodes"]}
    # partner map from graph edges
    partners = collections.defaultdict(list)
    for e in graph["edges"]:
        partners[e["source"]].append((e["target"], e["weight"]))
        partners[e["target"]].append((e["source"], e["weight"]))

    # choose people: notable ∪ top-by-msgs ∪ top-by-reactions
    by_msgs = sorted(people.values(), key=lambda r: -r["msgs"])
    by_react = sorted(people.values(), key=lambda r: -r.get("react_in", 0))
    picked, seen = [], set()
    def add(r):
        if r["aid"] not in seen and r["text"] >= 15:
            seen.add(r["aid"]); picked.append(r)
    if a.all:
        for r in by_msgs: add(r)            # every rankable (text>=15), by activity
    else:
        for nm in notable:
            for r in people.values():
                if r["name"] == nm: add(r); break
        for r in by_msgs[:12]: add(r)
        for r in by_react[:12]: add(r)
        picked = picked[:a.top]
    pick_aids = {r["aid"] for r in picked}

    # scan corpus once: collect per-picked-person messages
    msgs = collections.defaultdict(list)   # aid -> [(react, len, date, text)]
    for line in open(os.path.join(D, "corpus.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        if r["type"] != 1 or not r["text"]:
            continue
        aid = str(r["aid"])
        if aid not in pick_aids:
            continue
        rc = reactions.get(str(r["logId"]), 0)
        msgs[aid].append((rc, len(r["text"]), r["date"], r["text"][:280]))

    out = []
    for r in picked:
        aid = r["aid"]; m = msgs.get(aid, [])
        nr = 3 if a.all else 8
        ns = 4 if a.all else 6
        top_react = sorted(m, key=lambda x: -x[0])[:nr]
        top_react = [{"react": x[0], "date": x[2], "text": x[3]} for x in top_react if x[0] > 0]
        longest = sorted(m, key=lambda x: -x[1])[:ns]
        samples = [{"date": x[2], "text": x[3]} for x in longest]
        prt = sorted(partners.get(aid, []), key=lambda x: -x[1])[:5]
        prt = [{"name": name_by_aid.get(t, t), "weight": w} for t, w in prt]
        out.append({
            "name": r["name"], "aid": aid, "archetype": r.get("archetype"),
            "stats": {k: r.get(k) for k in
                      ("msgs", "text", "active_days", "react_in", "react_per_msg",
                       "influence", "argue_ratio", "q_ratio", "laugh_ratio",
                       "answer_ratio", "avg_len", "code", "media", "night_ratio",
                       "partners")},
            "top_reacted": top_react, "samples": samples, "partners": prt})
    json.dump({"people": out}, open(os.path.join(D, a.out), "w",
                                    encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"ok": True, "people": [p["name"] for p in out]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
