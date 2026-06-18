# Run this to diagnose API problems:
#     .venv\Scripts\python.exe debug_api.py
#
# Checks token validity, scopes, Events API, GraphQL, and Search API
# for both players and prints exactly what each endpoint returns.
import json
import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv(".env")

TOKEN   = os.getenv("GITHUB_TOKEN", "")
P2_TOKEN = os.getenv("PLAYER2_TOKEN", "")
P1      = os.getenv("PLAYER1_USERNAME", "")
P2      = os.getenv("PLAYER2_USERNAME", "")
SINCE   = "2026-06-16"

BASE     = "https://api.github.com"
GQL_URL  = "https://api.github.com/graphql"

GQL_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    name
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      commitContributionsByRepository(maxRepositories: 20) {
        repository { name isPrivate }
        contributions(first: 30) {
          nodes { occurredAt commitCount }
        }
      }
    }
  }
}
"""

TO_DT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def line(title=""):
    print(f"\n{'-' * 60}")
    if title:
        print(f"  {title}")
        print(f"{'-' * 60}")


def ok(label, detail=""):
    print(f"  [OK]   {label}" + (f"  ->  {detail}" if detail else ""))


def fail(label, detail=""):
    print(f"  [FAIL] {label}" + (f"  ->  {detail}" if detail else ""))


def make_session(token):
    s = requests.Session()
    s.headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    return s


def check_token(session, label):
    line(f"TOKEN CHECK — {label}")
    r = session.get(f"{BASE}/user", timeout=8)
    if r.ok:
        u = r.json()
        scopes = r.headers.get("X-OAuth-Scopes", "(fine-grained token — no scope header)")
        ok("Valid", f"logged in as: {u['login']}")
        ok("Scopes", scopes)
        # Warn about missing scopes for classic tokens
        if "X-OAuth-Scopes" in r.headers:
            s = r.headers["X-OAuth-Scopes"]
            if "read:user" not in s and "user" not in s:
                fail("Missing read:user scope — GraphQL contributions may fail")
            if "repo" not in s and "public_repo" not in s:
                fail("Missing repo/public_repo scope")
        return u["login"]
    else:
        fail("Invalid token", f"HTTP {r.status_code}  {r.text[:120]}")
        return None


def check_user(session, username):
    line(f"USER  {username}")
    r = session.get(f"{BASE}/users/{username}", timeout=8)
    if r.ok:
        u = r.json()
        ok("Found", f"name={u.get('name')}  public_repos={u.get('public_repos')}")
    else:
        fail("Not found", f"HTTP {r.status_code}")
        return False
    return True


def check_events(session, username):
    line(f"EVENTS API — {username}")
    r = session.get(f"{BASE}/users/{username}/events",
                    params={"per_page": 100}, timeout=10)
    if not r.ok:
        fail("Request failed", f"HTTP {r.status_code}  {r.text[:120]}")
        return

    events = r.json()
    if not isinstance(events, list):
        fail("Unexpected response", str(events)[:200])
        return

    since_events = [e for e in events if e["created_at"][:10] >= SINCE]
    push = [e for e in since_events if e["type"] == "PushEvent"]
    pr   = [e for e in since_events if e["type"] == "PullRequestEvent"]
    issue= [e for e in since_events if e["type"] == "IssuesEvent"]
    review=[e for e in since_events if e["type"] == "PullRequestReviewEvent"]

    commit_count = sum(len(e["payload"].get("commits", [])) for e in push)
    ok(f"Total events returned: {len(events)}")
    ok(f"Events since {SINCE}: {len(since_events)}")
    ok(f"PushEvents → commits: {commit_count}")
    ok(f"PullRequestEvents: {len(pr)}")
    ok(f"IssuesEvents: {len(issue)}")
    ok(f"ReviewEvents: {len(review)}")

    if push:
        e = push[0]
        repo = e.get("repo", {}).get("name", "?")
        print(f"\n    Latest push: {e['created_at'][:10]}  repo={repo}  "
              f"commits={len(e['payload'].get('commits', []))}")

    if not since_events:
        print("\n    NOTE: No events found since the competition start date.")
        print(f"    Earliest event returned: {events[0]['created_at'][:10] if events else 'none'}")
        print("    This likely means commits are to private repos (events API only shows public).")


def check_graphql(session, username):
    line(f"GRAPHQL — {username}")
    r = session.post(GQL_URL, json={
        "query": GQL_QUERY,
        "variables": {"login": username, "from": f"{SINCE}T00:00:00Z", "to": TO_DT},
    }, timeout=15)

    if not r.ok:
        fail("Request failed", f"HTTP {r.status_code}  {r.text[:120]}")
        return

    body = r.json()
    if "errors" in body:
        fail("GraphQL errors", json.dumps(body["errors"])[:300])
        return

    user_data = body.get("data", {}).get("user")
    if not user_data:
        fail("No user data", json.dumps(body)[:300])
        return

    cc = user_data["contributionsCollection"]
    commits  = cc["totalCommitContributions"]
    prs      = cc["totalPullRequestContributions"]
    issues   = cc["totalIssueContributions"]
    reviews  = cc["totalPullRequestReviewContributions"]

    ok(f"Commits  (default branch, counts private): {commits}")
    ok(f"PRs opened: {prs}")
    ok(f"Issues created: {issues}")
    ok(f"Reviews: {reviews}")

    repos = cc.get("commitContributionsByRepository", [])
    if repos:
        print()
        for r_entry in repos:
            repo = r_entry["repository"]
            count = sum(n["commitCount"] for n in r_entry["contributions"]["nodes"])
            priv = "[private]" if repo["isPrivate"] else "[public] "
            print(f"    {priv}  {repo['name']}: {count} commits")
    else:
        print("\n    No per-repo breakdown returned (0 commits counted).")
        print("    Possible reasons:")
        print("    • Commits are on non-default branches (feature branches)")
        print("    • Commits are in forked repos (forks don't count by default)")
        print("    • No commits at all since", SINCE)


def check_search(session, username):
    line(f"SEARCH API — {username}")
    r = session.get(f"{BASE}/search/commits",
                    params={"q": f"author:{username} committer-date:>={SINCE}", "per_page": 5},
                    headers={"Accept": "application/vnd.github.cloak-preview+json"},
                    timeout=10)
    if not r.ok:
        fail("Request failed", f"HTTP {r.status_code}  {r.text[:120]}")
        return

    data = r.json()
    total = data.get("total_count", 0)
    ok(f"Total commits found: {total}")
    for item in data.get("items", [])[:3]:
        repo = item.get("repository", {}).get("full_name", "?")
        msg  = item.get("commit", {}).get("message", "")[:60]
        date = item.get("commit", {}).get("committer", {}).get("date", "")[:10]
        print(f"    {date}  [{repo}]  {msg}")


# ── Run all checks ───────────────────────────────────────────────

line("GIT BATTLE - API DIAGNOSTIC")
print(f"  Players:    {P1}  vs  {P2}")
print(f"  Since:      {SINCE}")
print(f"  Token:      {TOKEN[:12]}..." if TOKEN else "  Token:  MISSING")
print(f"  P2 Token:   {'set' if P2_TOKEN else 'NOT SET (only public data for ' + P2 + ')'}")

# ── Player 1 (authenticated user) ────────────────────────────────
s1 = make_session(TOKEN)
auth_login = check_token(s1, "PLAYER1 token")
check_user(s1, P1)
check_events(s1, P1)
check_graphql(s1, P1)
check_search(s1, P1)

# ── Player 2 (may or may not have own token) ─────────────────────
line(f"=== PLAYER 2: {P2} ===")
if P2_TOKEN:
    print("  Using Player 2's own token — private activity will be visible.")
    s2 = make_session(P2_TOKEN)
    check_token(s2, "PLAYER2 token")
else:
    print("  No PLAYER2_TOKEN in .env — using Player 1 token.")
    print("  Private repos for this user will NOT be visible.")
    s2 = s1

check_user(s2, P2)
check_events(s2, P2)
check_graphql(s2, P2)
check_search(s2, P2)

line("DONE")
print("  Share the output above to diagnose any remaining issues.\n")
