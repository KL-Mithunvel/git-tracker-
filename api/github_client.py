import requests
from datetime import datetime, timezone


BASE_URL = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def fetch_user_stats(self, username: str, since: str) -> dict:
        """Fetch all competition stats for a user since the given date (YYYY-MM-DD)."""
        stats = {
            "username": username,
            "commits": 0,
            "prs_opened": 0,
            "prs_merged": 0,
            "issues_created": 0,
            "reviews": 0,
            "repos_created": 0,
            "daily_commits": {},
            "avatar_url": "",
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

        events = self._fetch_events(username)

        for event in events:
            event_date = event["created_at"][:10]
            if event_date < since:
                continue

            event_type = event["type"]
            payload = event.get("payload", {})

            if event_type == "PushEvent":
                commits = payload.get("commits", [])
                count = len(commits)
                if count > 0:
                    stats["commits"] += count
                    stats["daily_commits"][event_date] = (
                        stats["daily_commits"].get(event_date, 0) + count
                    )

            elif event_type == "PullRequestEvent":
                action = payload.get("action", "")
                if action == "opened":
                    stats["prs_opened"] += 1
                elif action == "closed":
                    pr = payload.get("pull_request", {})
                    if pr.get("merged"):
                        stats["prs_merged"] += 1

            elif event_type == "IssuesEvent":
                if payload.get("action") == "opened":
                    stats["issues_created"] += 1

            elif event_type == "PullRequestReviewEvent":
                if payload.get("action") == "submitted":
                    stats["reviews"] += 1

            elif event_type == "CreateEvent":
                if payload.get("ref_type") == "repository":
                    stats["repos_created"] += 1

        user_info = self._get_user(username)
        stats["avatar_url"] = user_info.get("avatar_url", "")

        return stats

    def _fetch_events(self, username: str) -> list:
        """Fetch up to 300 recent public events for a user (3 pages of 100)."""
        events = []
        for page in range(1, 4):
            try:
                resp = self.session.get(
                    f"{BASE_URL}/users/{username}/events",
                    params={"per_page": 100, "page": page},
                    timeout=10,
                )
                resp.raise_for_status()
                page_events = resp.json()
                if not page_events:
                    break
                events.extend(page_events)
                if len(page_events) < 100:
                    break
            except requests.RequestException:
                break
        return events

    def _get_user(self, username: str) -> dict:
        try:
            resp = self.session.get(f"{BASE_URL}/users/{username}", timeout=8)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            return {}

    def verify_token(self) -> bool:
        """Check if the token is valid."""
        try:
            resp = self.session.get(f"{BASE_URL}/user", timeout=8)
            return resp.status_code == 200
        except requests.RequestException:
            return False
