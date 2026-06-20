# ⚔ Git Battle — Web Version

The same head-to-head GitHub tracker as the desktop app, but as a web page you
can host once and visit from anywhere. It **reuses** the desktop app's data
logic (`api/github_client.py` + `engine/metrics.py`) — only the UI is new.

```
Browser ──► Flask (web/app.py)
              ├─ /            → dashboard page (templates/index.html)
              └─ /api/stats   → JSON (reuses github_client + metrics)
                                   └─ GitHub GraphQL/REST API
```

The GitHub token lives **only on the server** as an environment variable — it is
never sent to the browser.

---

## Run it locally

From the **repo root** (the folder above `web/`):

```bash
pip install -r web/requirements.txt
python web/app.py
```

Then open <http://localhost:8000>. It reads the same `.env` you already use for
the desktop app (`GITHUB_TOKEN`, `PLAYER1_USERNAME`, `PLAYER2_USERNAME`,
optional `PLAYER2_TOKEN`).

---

## Host it on Render (free)

1. Push this branch to GitHub (already connected to your repo).
2. Go to <https://render.com> → sign in with GitHub → **New → Web Service**.
3. Pick this repository. Render auto-detects `render.yaml`. If asked manually:
   - **Build command:** `pip install -r web/requirements.txt`
   - **Start command:** `gunicorn web.app:app`
4. Open **Environment** and add these as secrets (do **not** commit them):
   | Key | Value |
   |-----|-------|
   | `GITHUB_TOKEN` | your GitHub token |
   | `PLAYER1_USERNAME` | your GitHub username |
   | `PLAYER2_USERNAME` | opponent's GitHub username |
   | `PLAYER2_TOKEN` | *(optional)* opponent's token for their private commits |
5. Click **Create Web Service**. After it builds you get a public URL like
   `https://git-battle-web.onrender.com` — bookmark it.

> Free Render services sleep after ~15 min of inactivity, so the first visit
> after idle takes a few seconds to wake. Fine for "check it whenever."

---

## Notes

- `/api/stats` caches results for 60 seconds so refreshing the page (or several
  visitors) doesn't blow through GitHub's API rate limit. The **Refresh** button
  forces a fresh fetch (`?force=1`).
- No database is used — the web version fetches live each time (with the cache
  above), which keeps it stateless and easy to host on free tiers.
- Scoring, streak, and private-repo handling are identical to the desktop app
  because the same modules are imported.
