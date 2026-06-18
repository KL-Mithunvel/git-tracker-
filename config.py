COMPETITION_START_DATE = "2026-06-16"

COLORS = {
    "bg": "#0d1117",
    "surface": "#161b22",
    "border": "#30363d",
    "text_primary": "#e6edf3",
    "text_secondary": "#848d97",
    "p1_accent": "#58a6ff",
    "p2_accent": "#f78166",
    "leading": "#3fb950",
    "danger": "#f85149",
    "chart_bg": "#0d1117",
}

SCORE_WEIGHTS = {
    "commit": 10,
    "pr_opened": 10,
    "pr_merged": 25,
    "issue_created": 3,
    "code_review": 8,
    "repo_created": 15,
}

REFRESH_INTERVAL_SECONDS = 300
DB_PATH = "data/tracker.db"
ENV_FILE = ".env"
