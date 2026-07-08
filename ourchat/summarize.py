#!/usr/bin/env python3
"""
summarize.py — a summary for EVERY participant with chat history, no exceptions.
Deterministic (instant, covers all). The Claude enrichment step may later overwrite
the substantive members with richer text; this guarantees full coverage.

Reads personas.json (people with features/archetype/connections) + meta.json.
Writes summaries.json: { name: {name, title, summary, msgs, react_in, archetype,
top_conn, span} }.
"""
import argparse, json, os, datetime

GLOSS = {
    '지식인': '공감과 답변으로 인정받는 편', '인기인': '받은 공감이 최상위권',
    '싸움꾼': '논쟁·반박이 잦은 편', '질문러': '질문을 많이 던지는 편',
    '인싸': '대화 상대 폭이 넓은 편', '수다왕': '발언량이 아주 많은 편',
    '유머러': 'ㅋㅋ·농담이 많은 편', '홍보러': '링크·모집·홍보가 잦은 편',
    '미디어러': '사진·파일 공유가 잦은 편', '야행성': '새벽 시간대에 주로 활동',
}


def lite_archetype(r):
    if r.get("archetype"):
        return r["archetype"]
    m = r["msgs"]
    if m <= 2: return "스쳐간 참여자"
    if m < 10: return "가벼운 참여자"
    return "잔잔한 참여자"


def dstr(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    D = a.dir
    people = json.load(open(os.path.join(D, "personas.json"), encoding="utf-8"))["people"]

    # rank by messages for "방에서 N번째 다변가" flavor
    order = sorted(people.values(), key=lambda r: -r["msgs"])
    rankpos = {r["aid"]: i + 1 for i, r in enumerate(order)}

    out = {}
    for r in people.values():
        arch = lite_archetype(r)
        conns = r.get("connections", [])
        top = [c["name"] for c in conns[:3]]
        react = r.get("react_in", 0)
        parts = []
        parts.append(f"{arch}. {GLOSS.get(arch, '대화 이력이 있는 참여자')}.")
        parts.append(f"활동일 {r.get('active_days',0)}일, 발언 {r['msgs']:,}개"
                     f"(방 {rankpos[r['aid']]}위)")
        if react:
            parts.append(f"받은 공감 {react}개")
        if r.get("q_ratio", 0) >= 0.35:
            parts.append("질문 비중이 높음")
        if r.get("laugh_ratio", 0) >= 0.35:
            parts.append("웃음(ㅋㅋ) 많음")
        if r.get("code", 0) >= 10:
            parts.append("코드·기술 얘기 잦음")
        if top:
            parts.append(f"주로 {' · '.join(top)} 와 대화")
        summary = " · ".join(parts) + "."
        # title
        if r.get("react_per_msg", 0) >= 0.4 and r["msgs"] >= 30:
            title = f"{arch} · 공감 {r['react_per_msg']}/msg"
        elif r["msgs"] >= 1000:
            title = f"{arch} · 발언 {r['msgs']:,}"
        else:
            title = arch
        out[r["name"]] = {
            "name": r["name"], "title": title, "summary": summary,
            "msgs": r["msgs"], "react_in": react, "archetype": arch,
            "top_conn": top, "span": f"{dstr(r.get('first_ts'))}~{dstr(r.get('last_ts'))}",
            "degree": r.get("degree", 0)}
    json.dump(out, open(os.path.join(D, "summaries.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    print(json.dumps({"ok": True, "summarized": len(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
