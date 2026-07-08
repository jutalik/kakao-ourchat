#!/usr/bin/env python3
"""
topics.py — cluster the room's conversation into topics. Works with ZERO external
services by default (offline TF-IDF + MiniBatchKMeans via scikit-learn); optionally uses an
OpenAI-compatible embeddings endpoint for better clusters.

  OURCHAT_EMBED = offline | api        (default: offline)
  OURCHAT_EMBED_URL   = <base>/embeddings   (api mode; OpenAI/Ollama/vLLM compatible)
  OURCHAT_EMBED_MODEL = e.g. text-embedding-3-small / nomic-embed-text
  OURCHAT_EMBED_KEY   = api key (omit for local)

Topic *labels* here are the top terms; the optional narrate step renames them with
an LLM. Output topics.json matches the analyzer/dashboard contract.
"""
import argparse, json, os, re, collections, datetime, urllib.request

def toks(s):
    return re.findall(r"[가-힣]{2,}|[A-Za-z]{3,}", s)

STOP = set("그리고 근데 그냥 진짜 이거 저거 그거 저는 제가 있는 없는 하는 하고 해서 그럼 그래서 "
           "그러면 이제 약간 조금 많이 너무 정말 이런 저런 그런 는데 합니다 하네요 같아요 있어요 "
           "없어요 되는 되요 이나 에서 으로 네요 어요 아요 니까 까지 부터 처럼 만큼 이라 라고 라는 "
           "저도 저희 우리 그게 이게 그건 이건 뭔가 지금 혹시 요즘 감사합니다 하나 다시 일단 사실 "
           "the and for that this you your are was with have not but just".split() + "하더라구요 하면 있는데 그렇게 어떻게 다들 계속 아직 보면 만들고 될까요 같습니다 어느정도 그래도 바로 이미 보니까 요새 혼자 엄청 좋아요 생각보다 그리고 근데 그러면 아니 그건 이제 진짜 약간".split())

LAUGH = re.compile(r"^[ㅋㅎㅠㅜㄷㄱ\s~!.?,ㆍ·ㅇ]+$")


def api_embed(texts, batch=64):
    import numpy as np
    url = os.environ["OURCHAT_EMBED_URL"]; model = os.environ.get("OURCHAT_EMBED_MODEL", "text-embedding-3-small")
    key = os.environ.get("OURCHAT_EMBED_KEY", "")
    out = []
    for i in range(0, len(texts), batch):
        h = {"content-type": "application/json"}
        if key: h["authorization"] = f"Bearer {key}"
        req = urllib.request.Request(url, data=json.dumps({"model": model, "input": texts[i:i+batch]}).encode(), headers=h)
        d = json.loads(urllib.request.urlopen(req, timeout=120).read())
        out.extend(e["embedding"] for e in d["data"])
    v = np.array(out, dtype="float32"); v /= (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
    return v


def week_key(dstr):
    iso = datetime.datetime.strptime(dstr, "%Y-%m-%d").isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def main():
    import numpy as np
    from sklearn.cluster import MiniBatchKMeans   # low-memory / low-CPU, ~same clusters
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--cap", type=int, default=6000)
    a = ap.parse_args()
    D = a.dir
    rows = []
    for line in open(os.path.join(D, "corpus.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        if r["type"] != 1: continue
        t = r["text"].strip()
        if len(t) < 15 or LAUGH.match(t): continue
        rows.append(r)
    if len(rows) > a.cap:
        step = len(rows) / a.cap
        rows = [rows[int(i*step)] for i in range(a.cap)]
    if len(rows) < a.k * 5:
        json.dump({"topics": [], "sampled": len(rows), "k": 0, "note": "too few messages"},
                  open(os.path.join(D, "topics.json"), "w", encoding="utf-8"), ensure_ascii=False)
        print(json.dumps({"ok": True, "topics": 0}, ensure_ascii=False)); return

    texts = [r["text"][:400] for r in rows]
    mode = os.environ.get("OURCHAT_EMBED", "offline")
    if mode == "api":
        V = api_embed(texts)
    else:  # offline TF-IDF — no server needed
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(tokenizer=lambda s: [w for w in toks(s) if w not in STOP and len(w) >= 2],
                              token_pattern=None, min_df=3, max_df=0.5, max_features=4000, dtype='float32')
        V = vec.fit_transform(texts)

    k = min(a.k, max(2, len(rows)//30))
    km = MiniBatchKMeans(n_clusters=k, n_init=3, batch_size=1024, random_state=0).fit(V)
    lab = km.labels_; cents = km.cluster_centers_
    topics = []
    for c in range(k):
        idx = [i for i in range(len(rows)) if lab[i] == c]
        if not idx: continue
        tf = collections.Counter()
        for i in idx:
            for w in set(toks(rows[i]["text"])):
                if w not in STOP and len(w) >= 2: tf[w] += 1
        terms = [w for w, _ in tf.most_common(10)]
        # exemplars nearest centroid
        try:
            import numpy as np
            sub = V[idx]
            d = (sub @ cents[c].T)
            d = d.toarray().ravel() if hasattr(d, "toarray") else np.asarray(d).ravel()
            order = sorted(range(len(idx)), key=lambda j: -d[j])
        except Exception:
            order = range(len(idx))
        exemplars = [{"author": rows[idx[j]]["author"], "date": rows[idx[j]]["date"],
                      "text": rows[idx[j]]["text"][:200]} for j in list(order)[:6]]
        weekly = collections.Counter(week_key(rows[i]["date"]) for i in idx)
        authors = collections.Counter(rows[i]["author"] for i in idx)
        topics.append({"id": c, "size": len(idx), "label": " · ".join(terms[:4]), "terms": terms,
                       "exemplars": exemplars, "weekly": dict(sorted(weekly.items())),
                       "authors": authors.most_common(8),
                       "peak_week": weekly.most_common(1)[0][0] if weekly else None})
    topics.sort(key=lambda t: -t["size"])
    json.dump({"topics": topics, "sampled": len(rows), "k": k, "embed": mode},
              open(os.path.join(D, "topics.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"ok": True, "k": k, "sampled": len(rows), "embed": mode,
                      "labels": [t["label"] for t in topics[:10]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
