import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

import config


class Database:
    def __init__(self, db_path: str = config.DB_PATH):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_stats (
                username        TEXT PRIMARY KEY,
                commits         INTEGER DEFAULT 0,
                prs_opened      INTEGER DEFAULT 0,
                prs_merged      INTEGER DEFAULT 0,
                issues_created  INTEGER DEFAULT 0,
                reviews         INTEGER DEFAULT 0,
                repos_created   INTEGER DEFAULT 0,
                daily_commits   TEXT    DEFAULT '{}',
                avatar_url      TEXT    DEFAULT '',
                synced_at       TEXT
            );

            CREATE TABLE IF NOT EXISTS sync_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                synced_at   TEXT    NOT NULL,
                status      TEXT    NOT NULL,
                message     TEXT    DEFAULT ''
            );
        """)
        self.conn.commit()

    def save_stats(self, stats: dict):
        daily_json = json.dumps(stats.get("daily_commits", {}))
        self.conn.execute(
            """
            INSERT INTO user_stats
                (username, commits, prs_opened, prs_merged, issues_created,
                 reviews, repos_created, daily_commits, avatar_url, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                commits         = excluded.commits,
                prs_opened      = excluded.prs_opened,
                prs_merged      = excluded.prs_merged,
                issues_created  = excluded.issues_created,
                reviews         = excluded.reviews,
                repos_created   = excluded.repos_created,
                daily_commits   = excluded.daily_commits,
                avatar_url      = excluded.avatar_url,
                synced_at       = excluded.synced_at
            """,
            (
                stats["username"],
                stats.get("commits", 0),
                stats.get("prs_opened", 0),
                stats.get("prs_merged", 0),
                stats.get("issues_created", 0),
                stats.get("reviews", 0),
                stats.get("repos_created", 0),
                daily_json,
                stats.get("avatar_url", ""),
                stats.get("synced_at", ""),
            ),
        )
        self.conn.commit()

    def get_stats(self, username: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM user_stats WHERE username = ?", (username,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["daily_commits"] = json.loads(result.get("daily_commits", "{}"))
        return result

    def log_sync(self, status: str, message: str = ""):
        self.conn.execute(
            "INSERT INTO sync_log (synced_at, status, message) VALUES (?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), status, message),
        )
        self.conn.commit()
