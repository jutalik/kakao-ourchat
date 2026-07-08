#!/usr/bin/env python3
"""
analyze.py — deterministic analytics over an extracted corpus (no LLM).

Reads corpus.jsonl + participants.json from --dir and writes:
  graph.json      interaction network (nodes = top participants, edges = who
                  replies to whom via temporal adjacency; degree/centrality)
  personas.json   per-participant feature vector + assigned archetype
  rankings.json   activity leaderboards + per-persona top lists
  timeline.json   day / week / month buckets: volume, active users, top authors,
                  media, keyword histogram

Heuristics (open chat has no reply pointer): a message by A within REPLY_WINDOW
seconds after a message by a different author B is treated as A→B interaction.
Argument intensity = rapid A-B-A-B alternations + negative/rebuttal lexicon.
"""
import argparse, json, os, math, collections, datetime, re

REPLY_WINDOW = 120      # s: "responds to the previous different author"
BURST_GAP = 600         # s: conversation session boundary
MIN_RANKABLE = 15       # min text msgs to receive persona badges

Q_WORDS = ("?", "뭐", "어떻게", "어케", "왜", "인가요", "나요", "까요", "궁금",
           "질문", "가능한가", "되나요", "있나요", "어디", "무엇", "how", "which")
LAUGH = re.compile(r"(ㅋ{2,}|ㅎ{2,}|ㅋㅎ|하하|크크)")
URL = re.compile(r"https?://")
CODE = re.compile(r"(```|def |class |import |const |function|npm |pip |git |sudo |SELECT |http)")
RECRUIT = ("채용", "모집", "구인", "지원", "이력서", "포지션", "홍보", "링크", "카페",
           "오픈채팅", "초대", "안내", "이벤트", "무료", "신청")
ARGUE = ("아니", "아니요", "아닌데", "그건 아니", "틀렸", "틀린", "왜요", "님아", "ㅡㅡ",
         "말이 안", "말이안", "무슨", "근거", "팩트", "반박", "우기", "억지", "싸우",
         "논리", "그게 아니", "동의 안", "인정 안", "잘못", "말도 안")


def toks(s):
    # rough Korean/alnum tokenizer for keyword histograms
    return [t for t in re.findall(r"[가-힣]{2,}|[A-Za-z]{3,}", s)]


STOP = set("그리고 근데 그냥 진짜 이거 저거 그거 저는 제가 있는 없는 하는 하고 해서 "
           "그럼 그래서 그러면 이제 약간 조금 많이 너무 정말 이런 저런 그런 는데 "
           "합니다 하네요 같아요 있어요 없어요 되는 되요 이나 에서 으로 "
           "네요 어요 아요 니까 까지 부터 처럼 만큼 이라 라고 라는 "
           "저도 저희 우리 그게 이게 그건 이건 뭔가".split())


def week_key(dt):
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    D = a.dir
    parts = json.load(open(os.path.join(D, "participants.json"), encoding="utf-8"))

    # ---- single pass over the ordered corpus ----
    feat = collections.defaultdict(lambda: {
        "msgs": 0, "text": 0, "media": 0, "q": 0, "laugh": 0, "url": 0, "code": 0,
        "recruit": 0, "argue": 0, "len_sum": 0, "reply_out": 0, "reply_in": 0,
        "answer": 0, "night": 0, "mentions": 0,
        "partners": collections.Counter(), "hours": collections.Counter()})
    edges = collections.Counter()          # (A,B) A responded to B
    pair_alt = collections.Counter()       # undirected rapid-alternation intensity
    day = collections.defaultdict(lambda: {"n": 0, "users": set(), "media": 0,
                                           "authors": collections.Counter(),
                                           "kw": collections.Counter()})
    prev_a = prev_ts = None
    prev_prev_a = None
    last_q_ts = None                        # last question timestamp (any author)

    for line in open(os.path.join(D, "corpus.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        if r["system"]:
            continue
        aid, ts, txt = str(r["aid"]), r["ts"], r["text"]
        f = feat[aid]; f["msgs"] += 1
        dt = datetime.datetime.fromtimestamp(ts)
        hr = dt.hour
        f["hours"][hr] += 1
        if hr >= 0 and hr < 6:
            f["night"] += 1
        dkey = r["date"]
        dd = day[dkey]; dd["n"] += 1; dd["users"].add(aid); dd["authors"][r["author"]] += 1
        if r["media"]:
            f["media"] += 1; dd["media"] += 1
        if r["type"] == 1 and txt:
            f["text"] += 1
            low = txt
            f["len_sum"] += len(txt)
            if any(w in low for w in Q_WORDS): f["q"] += 1
            if LAUGH.search(low): f["laugh"] += 1
            if URL.search(low): f["url"] += 1
            if CODE.search(low): f["code"] += 1
            if any(w in low for w in RECRUIT): f["recruit"] += 1
            if any(w in low for w in ARGUE): f["argue"] += 1
            f["mentions"] += low.count("@")
            for t in toks(low):
                if t not in STOP and len(t) >= 2:
                    dd["kw"][t] += 1
            # answering: this text comes soon after someone else's question
            if last_q_ts is not None and 0 < ts - last_q_ts <= 300:
                f["answer"] += 1
            if "?" in low or any(w in low for w in Q_WORDS[1:6]):
                last_q_ts = ts

        # interaction edge: responded to previous different author within window
        if prev_a is not None and prev_a != aid and ts - prev_ts <= REPLY_WINDOW:
            edges[(aid, prev_a)] += 1
            f["reply_out"] += 1
            feat[prev_a]["reply_in"] += 1
            f["partners"][prev_a] += 1
            feat[prev_a]["partners"][aid] += 1
            # rapid A-B-A-B alternation → argument intensity for the pair
            if prev_prev_a == aid and ts - prev_ts <= 60:
                key = tuple(sorted((aid, prev_a)))
                pair_alt[key] += 1
        prev_prev_a = prev_a
        prev_a, prev_ts = aid, ts

    # fold pair alternation into per-user argue intensity
    for (x, y), c in pair_alt.items():
        feat[x]["argue"] += c * 0.5
        feat[y]["argue"] += c * 0.5

    # ---- assemble per-participant records ----
    def rec(aid):
        f = feat[aid]; p = parts.get(aid, {})
        text = f["text"] or 1
        return {
            "aid": aid, "name": p.get("name", aid), "msgs": f["msgs"],
            "text": f["text"], "media": f["media"], "active_days": p.get("active_days", 0),
            "first_ts": p.get("first_ts"), "last_ts": p.get("last_ts"),
            "avg_len": round(f["len_sum"] / text, 1),
            "q_ratio": round(f["q"] / text, 3),
            "laugh_ratio": round(f["laugh"] / text, 3),
            "urls": f["url"], "code": f["code"], "recruit": f["recruit"],
            "argue": round(f["argue"], 1),
            "reply_in": f["reply_in"], "reply_out": f["reply_out"],
            "answer": f["answer"], "night_ratio": round(f["night"] / f["msgs"], 3),
            "partners": len(f["partners"]),
            "influence": round(f["reply_in"] / (f["msgs"] or 1), 3),
            "react_in": p.get("react_in", 0),
            "react_per_msg": round(p.get("react_in", 0) / (f["msgs"] or 1), 3),
            # rate features → surface *character*, not just volume
            "argue_ratio": round(f["argue"] / text, 3),
            "recruit_ratio": round(f["recruit"] / text, 3),
            "media_ratio": round(f["media"] / (f["msgs"] or 1), 3),
            "answer_ratio": round(f["answer"] / text, 3),
            "code_ratio": round(f["code"] / text, 3),
        }

    people = {aid: rec(aid) for aid in feat}

    # ---- per-person REAL connections (undirected adjacency weight, full room) ----
    pair = collections.Counter()
    for (a2, b), w in edges.items():
        pair[tuple(sorted((a2, b)))] += w
    adj = collections.defaultdict(list)
    for (x, y), w in pair.items():
        adj[x].append((y, w)); adj[y].append((x, w))
    for aid, r in people.items():
        allc = sorted(adj.get(aid, []), key=lambda t: -t[1])
        # keep ALL of a person's relationships (not a top-N slice)
        r["connections"] = [{"name": people[o]["name"] if o in people else o,
                             "aid": o, "weight": w} for o, w in allc]
        r["degree"] = len(allc)

    # filter obvious bots (official 오픈채팅봇 etc.) from ranking/personas
    BOTS = {"오픈채팅봇", "카카오톡", "채널봇"}
    def is_bot(r):
        nm = r.get("name", "")
        return nm in BOTS or nm.endswith("봇")
    rankable = [r for r in people.values() if r["text"] >= MIN_RANKABLE and not is_bot(r)]

    # graceful degrade: chat EXPORTS carry no reactions(공감). If nobody has any,
    # drop reaction-based signals so 지식인/인기인 don't collapse to noise.
    has_react = any(r.get("react_in", 0) for r in people.values())

    # ---- z-scored persona scoring ----
    def zmap(key, pool):
        vals = [p[key] for p in pool]
        mu = sum(vals) / len(vals)
        sd = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5 or 1.0
        return {id(p): (p[key] - mu) / sd for p in pool}

    keys = ["msgs", "influence", "avg_len", "code_ratio", "q_ratio", "laugh_ratio",
            "argue", "argue_ratio", "partners", "recruit_ratio", "media_ratio",
            "night_ratio", "answer_ratio", "reply_out", "active_days",
            "react_in", "react_per_msg"]
    Z = {k: zmap(k, rankable) for k in keys}
    def z(p, k): return Z[k][id(p)]

    PERSONAS = {
        # label: feature weights. Rate features (…_ratio) capture *character*
        # independent of volume; msgs/partners capture reach.
        "지식인":   {"react_per_msg": 1.1, "influence": 0.9, "answer_ratio": 0.8, "avg_len": 0.5, "code_ratio": 0.6},
        "인기인":   {"react_in": 1.8, "react_per_msg": 0.6},
        "싸움꾼":   {"argue_ratio": 1.6, "argue": 0.6, "avg_len": 0.3},
        "질문러":   {"q_ratio": 1.8, "answer_ratio": -0.4},
        "인싸":     {"partners": 1.6, "msgs": 0.5},
        "수다왕":   {"msgs": 1.8, "active_days": 0.4},
        "유머러":   {"laugh_ratio": 1.8},
        "홍보러":   {"recruit_ratio": 1.5, "influence": -0.3},
        "미디어러": {"media_ratio": 1.8},
        "야행성":   {"night_ratio": 1.7},
    }
    if not has_react:
        # no reaction data (export source): 인기인 is meaningless; 지식인 leans on
        # answer/influence/length/code instead of 공감.
        PERSONAS.pop("인기인", None)
        PERSONAS["지식인"] = {"influence": 1.1, "answer_ratio": 1.0, "avg_len": 0.7, "code_ratio": 0.8}

    # ADAPTIVE: each room is different — a family chat / gaming clan / study group
    # needs its own archetypes & criteria. If a room_profile.json (AI-characterized)
    # supplies a persona set as weight-maps over the SAME universal feature keys,
    # use it; otherwise fall back to the built-in default above.
    try:
        prof = json.load(open(os.path.join(D, "room_profile.json"), encoding="utf-8"))
        pers = prof.get("personas")
        if isinstance(pers, dict) and pers:
            PERSONAS = {k: {kk: float(vv) for kk, vv in w.items() if kk in Z}
                        for k, w in pers.items() if isinstance(w, dict)}
        elif isinstance(pers, list) and pers:
            PERSONAS = {p["key"]: {kk: float(vv) for kk, vv in (p.get("weights") or {}).items() if kk in Z}
                        for p in pers if p.get("key")}
    except Exception:
        pass
    PERSONAS = {k: v for k, v in PERSONAS.items() if v} or {"활동왕": {"msgs": 1.8}}

    persona_scores = collections.defaultdict(dict)   # label -> {aid: score}
    for p in rankable:
        for label, w in PERSONAS.items():
            s = sum(coef * z(p, k) for k, coef in w.items())
            persona_scores[label][p["aid"]] = round(s, 3)
        # primary archetype = best-scoring persona for this person
        best = max(PERSONAS, key=lambda L: persona_scores[L][p["aid"]])
        p["archetype"] = best
        p["archetype_score"] = persona_scores[best][p["aid"]]

    # ---- rankings ----
    by_msgs = sorted(rankable, key=lambda r: -r["msgs"])
    rankings = {
        "most_active": [(r["name"], r["msgs"], r["active_days"]) for r in by_msgs[:25]],
        "least_active": [(r["name"], r["msgs"], r["active_days"])
                         for r in sorted(rankable, key=lambda r: r["msgs"])[:15]],
        "lurkers": [(r["name"], r["msgs"], r["active_days"])
                    for r in sorted(rankable, key=lambda r: (r["msgs"] / (r["active_days"] or 1)))[:15]],
        "most_reacted": [(r["name"], r["react_in"], r["msgs"])
                         for r in sorted(rankable, key=lambda r: -r["react_in"])[:15]],
        "best_ratio_reacted": [(r["name"], r["react_per_msg"], r["react_in"])
                               for r in sorted([r for r in rankable if r["msgs"] >= 30],
                                               key=lambda r: -r["react_per_msg"])[:15]],
        "personas": {L: [(people[aid]["name"], sc)
                         for aid, sc in sorted(sc.items(), key=lambda kv: -kv[1])[:10]]
                     for L, sc in persona_scores.items()},
    }

    # ---- FULL interaction graph (every participant + every relationship) ----
    # edges: all undirected pairs with weight>=MIN_EDGE. nodes: everyone who has
    # at least one such edge. The UI filters by weight for readability, but the
    # data carries every relationship so a person's full network is always visible.
    MIN_EDGE = 2
    gedges = [{"source": x, "target": y, "weight": w}
              for (x, y), w in pair.items() if w >= MIN_EDGE]
    node_ids = set()
    for e in gedges:
        node_ids.add(e["source"]); node_ids.add(e["target"])
    nodes = [{"id": aid, "name": people[aid]["name"], "msgs": people[aid]["msgs"],
              "archetype": people[aid].get("archetype", ""),
              "degree": people[aid].get("degree", 0),
              "partners": people[aid]["partners"]} for aid in node_ids]
    graph = {"nodes": nodes, "edges": gedges, "min_edge": MIN_EDGE,
             "total_participants": len(people)}

    # ---- timeline: day / week / month ----
    def bucket_out(bk):
        return {"key": bk[0], "n": bk[1]["n"], "users": len(bk[1]["users"]),
                "media": bk[1]["media"],
                "top_authors": bk[1]["authors"].most_common(5),
                "keywords": [w for w, _ in bk[1]["kw"].most_common(12)]}
    days = [bucket_out((k, v)) for k, v in sorted(day.items())]
    week = collections.defaultdict(lambda: {"n": 0, "users": set(), "media": 0,
                                            "authors": collections.Counter(),
                                            "kw": collections.Counter()})
    month = collections.defaultdict(lambda: {"n": 0, "users": set(), "media": 0,
                                             "authors": collections.Counter(),
                                             "kw": collections.Counter()})
    for k, v in day.items():
        dt = datetime.datetime.strptime(k, "%Y-%m-%d")
        for agg, kk in ((week, week_key(dt)), (month, k[:7])):
            b = agg[kk]; b["n"] += v["n"]; b["users"] |= v["users"]; b["media"] += v["media"]
            b["authors"].update(v["authors"]); b["kw"].update(v["kw"])
    timeline = {"day": days,
                "week": [bucket_out((k, v)) for k, v in sorted(week.items())],
                "month": [bucket_out((k, v)) for k, v in sorted(month.items())]}

    J = lambda name, obj: json.dump(obj, open(os.path.join(D, name), "w",
                                              encoding="utf-8"), ensure_ascii=False, indent=1)
    J("graph.json", graph)
    J("personas.json", {"people": people, "min_rankable": MIN_RANKABLE})
    J("rankings.json", rankings)
    J("timeline.json", timeline)
    print(json.dumps({"ok": True, "rankable": len(rankable), "nodes": len(nodes),
                      "edges": len(gedges), "days": len(days),
                      "weeks": len(timeline["week"]), "months": len(timeline["month"])},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
