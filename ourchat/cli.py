#!/usr/bin/env python3
"""
OurChat CLI — turn a KakaoTalk chat export into a knowledge-graph dashboard.

  python -m ourchat analyze <export.csv|.txt> --room "우리 단톡방"
  python -m ourchat demo                 # run on the bundled synthetic sample
  python -m ourchat serve                # serve the built dashboard

Pipeline: parse → characterize (room rubric) → analyze → topics → summarize →
daily → [narrate if an LLM is configured] → publish to the dashboard.

AI is optional (see llm.py):
  no LLM     → universal behavioral personas + deterministic summaries (free/offline)
  your LLM   → room-tailored personas, AI narratives + character profiles + chat
  hosted     → same, run on our servers (paid)
"""
import argparse, os, sys, subprocess, json, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
WEBDATA = os.path.join(ROOT, "web", "public", "data")


def run(script, *args):
    r = subprocess.run([PY, os.path.join(HERE, script), *args], capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(f"[{script}] {r.stderr[-800:]}\n")
    else:
        line = (r.stdout.strip().splitlines() or [""])[-1]
        print(f"  ✓ {script}: {line[:160]}")
    return r.returncode == 0


def slugify(s):
    s = re.sub(r"[^0-9a-zA-Z가-힣]+", "-", s).strip("-").lower()
    return s[:32] or "room"


WORKROOT = os.path.join(ROOT, ".ourchat")   # persistent per-room working data (gitignored)

def analyze(export, room, slug, outdir, append=False):
    os.makedirs(outdir, exist_ok=True)
    have = os.path.exists(os.path.join(outdir, "corpus.jsonl"))
    if append and have:
        print(f"OurChat · appending '{export}' to '{room}' (incremental)")
        tmp = outdir + "-incoming"; os.makedirs(tmp, exist_ok=True)
        if not run("parse_export.py", "--input", export, "--outdir", tmp, "--room", room):
            sys.exit("parse failed — is this a KakaoTalk export (.csv/.txt)?")
        run("merge.py", "--base", outdir, "--add", tmp, "--room", room)   # union + dedup
    else:
        print(f"OurChat · analyzing '{room}'  ({export})")
        if not run("parse_export.py", "--input", export, "--outdir", outdir, "--room", room):
            sys.exit("parse failed — is this a KakaoTalk export (.csv/.txt)?")
    run("characterize.py", "--dir", outdir)          # room rubric (LLM or universal)
    run("analyze.py", "--dir", outdir)               # graph + personas + rankings + timeline
    run("topics.py", "--dir", outdir)                # topic clusters (offline TF-IDF by default)
    run("summarize.py", "--dir", outdir)             # per-person one-liners (all participants)
    run("daily.py", "--dir", outdir)                 # per-day digests
    # optional AI layer
    try:
        sys.path.insert(0, HERE); import llm
        if llm.available():
            run("narrate.py", "--dir", outdir)       # topic names, arc, character profiles
    except Exception:
        pass
    # publish into the dashboard (multi-room)
    roomdir = os.path.join(WEBDATA, "rooms", slug); os.makedirs(roomdir, exist_ok=True)
    for f in os.listdir(outdir):
        if f.endswith(".json"):
            shutil.copy(os.path.join(outdir, f), os.path.join(roomdir, f))
    json.dump({"source": os.path.basename(export), "scratch": outdir},
              open(os.path.join(roomdir, "source.json"), "w"), ensure_ascii=False)
    run("reindex.py")
    print(f"\nDone. View: python -m ourchat serve   →  http://localhost:4173/?room={slug}")


def main():
    ap = argparse.ArgumentParser(prog="ourchat")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze"); a.add_argument("export"); a.add_argument("--room", default="")
    a.add_argument("--slug", default=""); a.add_argument("--out", default="")
    a.add_argument("--append", action="store_true", help="merge a newer export into this room (incremental update)")
    sub.add_parser("demo")
    s = sub.add_parser("serve"); s.add_argument("--port", default="4173")
    args = ap.parse_args()

    if args.cmd == "demo":
        sample = os.path.join(ROOT, "samples", "sample_export.csv")
        analyze(sample, "데모 단톡방", "demo", os.path.join(WORKROOT, "demo"))
    elif args.cmd == "analyze":
        room = args.room or "우리 단톡방"
        slug = args.slug or slugify(room)
        out = args.out or os.path.join(WORKROOT, slug)   # persistent → re-runs accumulate
        analyze(args.export, room, slug, out, append=args.append)
    elif args.cmd == "serve":
        web = os.path.join(ROOT, "web")
        if not os.path.isdir(os.path.join(web, "dist")):
            print("building dashboard…"); subprocess.run(["npm", "install"], cwd=web); subprocess.run(["npm", "run", "build"], cwd=web)
        subprocess.run(["npx", "vite", "preview", "--host", "0.0.0.0", "--port", args.port, "--outDir", "dist"], cwd=web)


if __name__ == "__main__":
    main()
