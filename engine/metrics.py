from datetime import date, timedelta

import config


def calculate_score(stats: dict) -> int:
    if not stats:
        return 0
    w = config.SCORE_WEIGHTS
    return (
        stats.get("commits", 0) * w["commit"]
        + stats.get("prs_opened", 0) * w["pr_opened"]
        + stats.get("prs_merged", 0) * w["pr_merged"]
        + stats.get("issues_created", 0) * w["issue_created"]
        + stats.get("reviews", 0) * w["code_review"]
        + stats.get("repos_created", 0) * w["repo_created"]
    )


def calculate_streak(daily_commits: dict) -> int:
    """Count consecutive days with ≥1 commit working backwards from today."""
    today = date.today()
    streak = 0
    current = today

    # If today has no commits yet, allow starting the streak from yesterday
    if daily_commits.get(today.strftime("%Y-%m-%d"), 0) == 0:
        current = today - timedelta(days=1)

    while True:
        key = current.strftime("%Y-%m-%d")
        if daily_commits.get(key, 0) > 0:
            streak += 1
            current -= timedelta(days=1)
        else:
            break

    return streak


def get_today_commits(daily_commits: dict) -> int:
    return daily_commits.get(date.today().strftime("%Y-%m-%d"), 0)


def get_peak_day(daily_commits: dict) -> tuple:
    if not daily_commits:
        return ("—", 0)
    peak_date = max(daily_commits, key=daily_commits.get)
    return (peak_date, daily_commits[peak_date])


def competition_days_elapsed() -> int:
    start = date.fromisoformat(config.COMPETITION_START_DATE)
    return (date.today() - start).days + 1


def leadership_periods(
    p1_daily: dict, p2_daily: dict, p1: str, p2: str, days: list[str]
) -> list[dict]:
    """Return consecutive periods of who led the cumulative commit count.

    Each item: {"leader": name|None (tie), "start": date, "end": date,
                "p1": total, "p2": total} where totals are at period end.
    """
    periods: list[dict] = []
    t1 = t2 = 0
    for d in days:
        t1 += p1_daily.get(d, 0)
        t2 += p2_daily.get(d, 0)
        leader = p1 if t1 > t2 else p2 if t2 > t1 else None
        if t1 == 0 and t2 == 0:
            continue
        if periods and periods[-1]["leader"] == leader:
            periods[-1].update(end=d, p1=t1, p2=t2)
        else:
            periods.append({"leader": leader, "start": d, "end": d, "p1": t1, "p2": t2})
    return periods
