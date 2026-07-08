# Hosting OurChat

Run your dashboard locally, on a home server/VPS, or share it privately online.

---

## 1) Local only (simplest, fully private)

```bash
python -m ourchat analyze chats.csv --room "우리방"
python -m ourchat serve            # → http://localhost:4173
```

The dashboard is a **static site** (`web/dist`) reading JSON from
`web/public/data/rooms/<slug>/`. Nothing runs at request time — it's just files.

## 2) Serve on your LAN / a home server / VPS

Build once, then serve `web/dist` with any static server:

```bash
cd web && npm install && npm run build      # produces web/dist (static)

python -m ourchat serve --port 4173         # built-in (vite preview)
# or:  npx serve web/dist   |   caddy file-server --root web/dist   |   nginx
```

Example **Caddy** with an optional password (a group chat is other people's data):

```
:8080 {
    encode gzip
    root * /path/to/kakao-ourchat/web/dist
    file_server
    basic_auth { myname JDJhJDE0J...bcrypt-hash }   # caddy hash-password
}
```

## 3) Put it on the internet (no open ports) — Cloudflare Tunnel

Great for a private link without exposing your IP or forwarding ports:

```bash
cloudflared tunnel --url http://localhost:4173      # gives you a https://…trycloudflare.com link
# or a named tunnel bound to your own domain (chat.yourdomain.com)
```

Pair with the Caddy `basic_auth` above so it isn't world-readable.

## Docker (optional)

```dockerfile
FROM node:22-slim
WORKDIR /app
COPY web ./web
RUN cd web && npm ci && npm run build
EXPOSE 4173
CMD ["npx","--prefix","web","vite","preview","web","--host","0.0.0.0","--port","4173","--outDir","dist"]
```

Build data on the host with `python -m ourchat analyze …`, mount
`web/public/data` into the container (or copy before build).

---

## Before you make it public — please

- A shared dashboard exposes **other members' messages, nicknames, and highlights**.
  Get **consent**, and put it behind auth (Caddy `basic_auth`, Cloudflare Access, or a
  private link).
- Prefer **offline mode** (no LLM) or a **local model** for sensitive rooms.
- See [PRIVACY.md](../PRIVACY.md).
