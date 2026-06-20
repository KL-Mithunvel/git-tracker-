"""
Web version of Git Battle Tracker.

A small Flask app that reuses the *exact same* data-fetching and scoring logic
as the desktop app (api/github_client.py + engine/metrics.py), but serves the
scoreboard as a web page so it can be hosted and visited from anywhere.

Run locally:
    pip install -r web/requirements.txt
    python web/app.py            # then open http://localhost:8000

Deploy (Render): see web/README.md
"""

import os
import sys
import time
from pathlib import Path

# --- Make the repo root importable so we can reuse the existing modules ---
# web/app.py lives in <repo>/web/, so the repo root is one level up.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from flask import Flask, render_template, jsonify
from dotenv import load_dotenv

import config
from api.github_client import GitHubClient
from engine.metrics import (
    calculate_score,
    calculate_streak,
    get_today_commits,
    get_peak_day,
    competition_days_elapsed,
)

# Load .env from the repo root if present (local dev). On Render the same
# variables are provided as real environment variables, so override=False
# means we never clobber what the host already set.
load_dotenv(REPO_ROOT / ".env", override=False)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Simple in-memory cache so refreshing the page (or multiple visitors) doesn't
# call the GitHub API on every single request and burn through the rate limit.
# ---------------------------------------------------------------------------
CACHE_TTL_SECONDS = 60
_cache: dict = {"payload": None, "fetched_at": 0.0}


def _read_config() -> dict | None:
    """Read the two usernames + token(s) from environment variables."""
    token = os.getenv("GITHUB_TOKEN", "").strip()
    player1 = os.getenv("PLAYER1_USERNAME", "").strip()
    player2 = os.getenv("PLAYER2_USERNAME", "").strip()
    player2_token = os.getenv("PLAYER2_TOKEN", "").strip()
    if not (token and player1 and player2):
        return None
    return {
        "token": token,
        "player1": player1,
        "player2": player2,
        # Fall back to player1's token if the opponent didn't share one.
        "player2_token": player2_token or token,
    }


def _player_view(stats: dict | None) -> dict | None:
    """Turn a raw stats dict into everything the dashboard needs to render."""
    if not stats:
        return None
    daily = stats.get("daily_commits", {})
    peak_date, peak_val = get_peak_day(daily)
    return {
        "username": stats.get("username", "?"),
        "avatar_url": stats.get("avatar_url", ""),
        "commits": stats.get("commits", 0),
        "score": calculate_score(stats),
        "prs_opened": stats.get("prs_opened", 0),
        "prs_merged": stats.get("prs_merged", 0),
        "issues_created": stats.get("issues_created", 0),
        "reviews": stats.get("reviews", 0),
        "streak": calculate_streak(daily),
        "today": get_today_commits(daily),
        "peak_date": peak_date,
        "peak_val": peak_val,
        "daily_commits": daily,
    }


def _build_payload() -> dict:
    """Fetch both players live and assemble the full scoreboard JSON."""
    cfg = _read_config()
    if cfg is None:
        return {
            "error": (
                "Missing configuration. Set GITHUB_TOKEN, PLAYER1_USERNAME and "
                "PLAYER2_USERNAME (PLAYER2_TOKEN optional)."
            )
        }

    since = config.COMPETITION_START_DATE
    client_p1 = GitHubClient(cfg["token"])
    client_p2 = GitHubClient(cfg["player2_token"])

    p1_stats = client_p1.fetch_user_stats(cfg["player1"], since)
    p2_stats = client_p2.fetch_user_stats(cfg["player2"], since)

    p1 = _player_view(p1_stats)
    p2 = _player_view(p2_stats)

    p1_score = p1["score"] if p1 else 0
    p2_score = p2["score"] if p2 else 0
    p1_leads = p1_score >= p2_score
    diff = abs(p1_score - p2_score)

    if diff == 0:
        leader_text = "TIE!"
    else:
        leader = cfg["player1"] if p1_leads else cfg["player2"]
        leader_text = f"↑ {leader}  +{diff:,} pts"

    return {
        "player1": p1,
        "player2": p2,
        "p1_leads": p1_leads,
        "diff": diff,
        "leader_text": leader_text,
        "score_line": f"{p1_score:,} vs {p2_score:,} pts",
        "day": competition_days_elapsed(),
        "start_date": config.COMPETITION_START_DATE,
        "synced_at": time.strftime("%I:%M %p"),
    }


def _get_payload(force: bool = False) -> dict:
    """Return cached payload if fresh, otherwise fetch a new one."""
    now = time.time()
    if (
        not force
        and _cache["payload"] is not None
        and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS
    ):
        return _cache["payload"]

    payload = _build_payload()
    # Only cache successful payloads; let errors retry next request.
    if "error" not in payload:
        _cache["payload"] = payload
        _cache["fetched_at"] = now
    return payload


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template(
        "index.html",
        colors=config.COLORS,
        refresh_seconds=config.REFRESH_INTERVAL_SECONDS,
    )


@app.route("/api/stats")
def api_stats():
    # ?force=1 bypasses the cache (used by the manual Refresh button).
    from flask import request

    force = request.args.get("force") == "1"
    payload = _get_payload(force=force)
    status = 200 if "error" not in payload else 503
    return jsonify(payload), status


@app.route("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    # Local dev server. On Render this is started by gunicorn instead.
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
