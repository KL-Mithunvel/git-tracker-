# ⚔ Git Battle Tracker

A local desktop scoreboard for tracking head-to-head GitHub activity between two developers.

**Competition start:** June 16, 2026

---

## What it tracks

| Metric | Points | Notes |
|--------|--------|-------|
| Commits | 10 pts each | Primary — shown as the hero number |
| PR merged | 25 pts | |
| PR opened | 10 pts | |
| Issues created | 3 pts | |
| Code reviews | 8 pts | |
| Repos created | 15 pts | |
| Streak | — | Consecutive days with ≥1 commit |
| Today / Peak day | — | Display only |

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get a GitHub token
Go to **github.com/settings/tokens → Generate new token (classic)**
Required scopes: `public_repo`, `read:user`

### 3. Run
```bash
python main.py
```

On first launch a setup wizard appears — enter your token, your GitHub username, and your competitor's GitHub username. Config is saved to `config.json` (gitignored).

---

## Architecture

```
GitHub Events API
      │
      ▼
api/github_client.py   ←  fetches up to 300 events per user
      │
      ▼
db/database.py         ←  SQLite cache  (data/tracker.db)
      │
      ▼
engine/metrics.py      ←  score, streak, today count
      │
      ▼
gui/app.py             ←  customtkinter main window
  ├─ gui/player_card.py
  └─ gui/charts.py
```

Data refreshes every **5 minutes** automatically. Click ↻ Refresh to force an immediate sync.

---

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point |
| `config.py` | Competition date, scoring weights, colours |
| `config.json` | Your token + usernames (gitignored, created on first run) |
| `api/github_client.py` | GitHub REST API client |
| `db/database.py` | SQLite wrapper |
| `engine/metrics.py` | Score, streak, peak-day calculations |
| `gui/app.py` | Main window |
| `gui/player_card.py` | Per-player stats widget |
| `gui/charts.py` | Commits-per-day bar chart |
| `gui/setup_wizard.py` | First-run config dialog |
| `data/tracker.db` | Local cache (gitignored) |

---

## Limitation

The GitHub Events API covers the last ~300 events per user. For an active competition this window covers many days of history. Commit totals reflect pushes to **public** repos; private repos require the competitor to share their own token (not required for the basic setup).
