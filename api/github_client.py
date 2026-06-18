import requests
from datetime import datetime, timezone

BASE_URL = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"

# contributionsCollection includes private repo contributions — same data the
# GitHub profile contribution graph shows. This is the key query.
_CONTRIBUTIONS_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      commitContributionsByRepository(maxRepositories: 50) {
        contributions(first: 100) {
          nodes {
            occurredAt
            commitCount
          }
        }
      }
      pullRequestContributions(first: 100) {
        nodes {
          pullRequest {
            merged
          }
        }
      }
    }
  }
}
"""


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

        # Events API — only public activity, but needed for repos_created
        # and as a fallback daily breakdown if GraphQL fails.
        events = self._fetch_events(username)
        events_commits = 0
        for event in events:
            event_date = event["created_at"][:10]
            if event_date < since:
                continue
            event_type = event["type"]
            payload = event.get("payload", {})

            if event_type == "PushEvent":
                count = len(payload.get("commits", []))
                if count > 0:
                    events_commits += count
                    stats["daily_commits"][event_date] = (
                        stats["daily_commits"].get(event_date, 0) + count
                    )
            elif event_type == "PullRequestEvent":
                action = payload.get("action", "")
                if action == "opened":
                    stats["prs_opened"] += 1
                elif action == "closed" and payload.get("pull_request", {}).get("merged"):
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

        # GraphQL contributionsCollection — includes private repos.
        # Overrides the events-based numbers if successful.
        gql = self._fetch_via_graphql(username, since)
        if gql:
            stats["commits"] = gql["commits"]
            stats["prs_opened"] = gql["prs_opened"]
            stats["prs_merged"] = gql["prs_merged"]
            stats["issues_created"] = gql["issues_created"]
            stats["reviews"] = gql["reviews"]
            if gql["daily_commits"]:
                stats["daily_commits"] = gql["daily_commits"]
        else:
            # GraphQL failed — fall back to search API for a more accurate total
            search_commits = self._search_commit_count(username, since)
            stats["commits"] = max(events_commits, search_commits)

        user_info = self._get_user(username)
        stats["avatar_url"] = user_info.get("avatar_url", "")
        return stats

    def _fetch_via_graphql(self, username: str, since: str) -> dict | None:
        """contributionsCollection via GraphQL — covers private repos too."""
        since_dt = f"{since}T00:00:00Z"
        to_dt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            resp = self.session.post(
                GRAPHQL_URL,
                json={
                    "query": _CONTRIBUTIONS_QUERY,
                    "variables": {"login": username, "from": since_dt, "to": to_dt},
                },
                timeout=15,
            )
            resp.raise_for_status()
            body = resp.json()

            if "errors" in body or not body.get("data", {}).get("user"):
                return None

            cc = body["data"]["user"]["contributionsCollection"]

            # Build daily commits from per-repo per-day breakdown
            daily: dict[str, int] = {}
            for repo_contrib in cc.get("commitContributionsByRepository", []):
                for node in repo_contrib["contributions"]["nodes"]:
                    day = node["occurredAt"][:10]
                    if day >= since:
                        daily[day] = daily.get(day, 0) + node["commitCount"]

            prs_merged = sum(
                1 for node in (cc.get("pullRequestContributions") or {}).get("nodes", [])
                if node and (node.get("pullRequest") or {}).get("merged")
            )

            return {
                "commits": cc["totalCommitContributions"],
                "prs_opened": cc["totalPullRequestContributions"],
                "prs_merged": prs_merged,
                "issues_created": cc["totalIssueContributions"],
                "reviews": cc["totalPullRequestReviewContributions"],
                "daily_commits": daily,
            }

        except (requests.RequestException, KeyError, TypeError, ValueError, AttributeError):
            return None

    def _search_commit_count(self, username: str, since: str) -> int:
        """Commit total via search API — catches private repo commits."""
        try:
            resp = self.session.get(
                f"{BASE_URL}/search/commits",
                params={"q": f"author:{username} committer-date:>={since}", "per_page": 1},
                headers={"Accept": "application/vnd.github.cloak-preview+json"},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json().get("total_count", 0)
        except requests.RequestException:
            pass
        return 0

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
        try:
            resp = self.session.get(f"{BASE_URL}/user", timeout=8)
            return resp.status_code == 200
        except requests.RequestException:
            return False
