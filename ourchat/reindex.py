#!/usr/bin/env python3
"""
reindex.py — build web/public/data/index.json from every analyzed room under
web/public/data/rooms/<slug>/. Powers the multi-room dashboard switcher.
Each room dir has the standard artifacts (meta.json, etc). The index lists them
with the device/account they came from (rooms/<slug>/source.json, optional).
"""
import json, os, glob, sys

WEB = os.environ.get("OURCHAT_WEB") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
ROOMS = f"{WEB}/public/data/rooms"


def main():
    out = []
    for meta_path in sorted(glob.glob(f"{ROOMS}/*/meta.json")):
        slug = os.path.basename(os.path.dirname(meta_path))
        try:
            meta = json.load(open(meta_path, encoding="utf-8"))
        except Exception:
            continue
        src = {}
        sp = f"{ROOMS}/{slug}/source.json"
        if os.path.exists(sp):
            try: src = json.load(open(sp, encoding="utf-8"))
            except Exception: pass
        out.append({
            "slug": slug, "room": meta.get("room", slug),
            "messages": meta.get("messages", 0), "participants": meta.get("participants", 0),
            "date_span": meta.get("date_span"),
            "device": src.get("device", ""), "account": src.get("account", ""),
            "chatId": meta.get("chatId"),
        })
    out.sort(key=lambda r: -(r.get("messages") or 0))
    idx = {"rooms": out, "count": len(out)}
    json.dump(idx, open(f"{WEB}/public/data/index.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"ok": True, "rooms": [r["slug"] for r in out]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
