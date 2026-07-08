#!/usr/bin/env python3
"""
daily.py — per-day conversation digest (deterministic, instant). One entry per
calendar day with volume, active people, keywords, busiest hour, the day's most-
reacted messages (highlights), and a templated auto-summary. The Claude daily
narrative step (daily_narrative.json) may enrich each day with a headline/summary;
this file always exists and stays fresh via the 10-min updater.

Reads corpus.jsonl + reactions.json from --dir. Writes daily.json (latest first).
"""
import argparse, json, os, re, collections, datetime

LAUGH = re.compile(r"^[ㅋㅎㅠㅜㄷㄱ\s~!.?,ㆍ·ㅇ]+$")
def toks(s): return re.findall(r"[가-힣]{2,}|[A-Za-z]{3,}", s)
STOP = set("그리고 근데 그냥 진짜 이거 저거 그거 저는 제가 있는 없는 하는 하고 해서 그럼 그래서 "
           "그러면 이제 약간 조금 많이 너무 정말 이런 저런 그런 는데 합니다 하네요 같아요 있어요 "
           "없어요 되는 되요 이나 에서 으로 네요 어요 아요 니까 까지 부터 처럼 만큼 이라 라고 라는 "
           "저도 저희 우리 그게 이게 그건 이건 뭔가 지금 혹시 요즘 감사합니다 하나 다시 일단 사실 "
           "어떻게 그렇게 아직 엄청 한번 맞아요 보통 여기 거의 계속 있는데 있습니다 입니다 됩니다".split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    D = a.dir
    reactions = json.load(open(os.path.join(D, "reactions.json"), encoding="utf-8"))

    day = collections.defaultdict(lambda: {
        "n": 0, "users": set(), "media": 0, "authors": collections.Counter(),
        "kw": collections.Counter(), "hours": collections.Counter(), "msgs": []})
    for line in open(os.path.join(D, "corpus.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        if r["system"]:
            continue
        d = day[r["date"]]
        d["n"] += 1; d["users"].add(r["aid"]); d["authors"][r["author"]] += 1
        dt = datetime.datetime.fromtimestamp(r["ts"]); d["hours"][dt.hour] += 1
        if r["media"]:
            d["media"] += 1
        if r["type"] == 1 and r["text"]:
            t = r["text"].strip()
            for w in set(toks(t)):
                if w not in STOP and len(w) >= 2:
                    d["kw"][w] += 1
            rc = reactions.get(str(r["logId"]), 0)
            if len(t) >= 12 and not LAUGH.match(t):
                d["msgs"].append((rc, r["author"], t[:220], r["ts"]))

    out = []
    for date in sorted(day, reverse=True):
        d = day[date]
        top_authors = d["authors"].most_common(6)
        keywords = [w for w, _ in d["kw"].most_common(12)]
        peak_hour = d["hours"].most_common(1)[0][0] if d["hours"] else None
        highlights = [{"author": au, "text": tx, "react": rc}
                      for rc, au, tx, _ in sorted(d["msgs"], key=lambda x: (-x[0], -len(x[2])))[:5]]
        auto = (f"메시지 {d['n']}건, 참여 {len(d['users'])}명. "
                f"주요 참여자 {', '.join(n for n, _ in top_authors[:3])}. "
                f"화제 키워드 {', '.join(keywords[:6])}."
                + (f" 가장 활발한 시간대 {peak_hour}시." if peak_hour is not None else ""))
        out.append({
            "date": date, "n": d["n"], "users": len(d["users"]), "media": d["media"],
            "top_authors": top_authors, "keywords": keywords, "peak_hour": peak_hour,
            "highlights": highlights, "auto": auto})
    json.dump({"days": out, "count": len(out)},
              open(os.path.join(D, "daily.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    print(json.dumps({"ok": True, "days": len(out), "latest": out[0]["date"] if out else None},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
