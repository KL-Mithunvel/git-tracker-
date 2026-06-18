import io
import threading

import requests
from PIL import Image, ImageDraw
import customtkinter as ctk

import config
from engine.metrics import calculate_score, calculate_streak, get_today_commits, get_peak_day

_C = config.COLORS


class PlayerCard(ctk.CTkFrame):
    def __init__(self, master, player_num: int, **kwargs):
        accent = _C["p1_accent"] if player_num == 1 else _C["p2_accent"]
        # Subtle tinted background for the commit highlight box
        commit_bg = "#1a2a3a" if player_num == 1 else "#2a1a1a"

        kwargs.setdefault("fg_color", _C["surface"])
        kwargs.setdefault("corner_radius", 14)
        kwargs.setdefault("border_width", 2)
        kwargs.setdefault("border_color", accent)
        super().__init__(master, **kwargs)

        self.accent = accent
        self._commit_bg = commit_bg
        self._avatar_cache = None
        self._build_ui()

    def _build_ui(self):
        # --- Top row: avatar + username ---
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 6))

        self.avatar_label = ctk.CTkLabel(
            top, text="👤", font=ctk.CTkFont(size=32), width=52, height=52,
        )
        self.avatar_label.pack(side="left", padx=(0, 12))

        name_col = ctk.CTkFrame(top, fg_color="transparent")
        name_col.pack(side="left", fill="both", expand=True)

        self.username_label = ctk.CTkLabel(
            name_col, text="Loading…",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=self.accent, anchor="w",
        )
        self.username_label.pack(fill="x")

        self.crown_label = ctk.CTkLabel(
            name_col, text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f0c040", anchor="w",
        )
        self.crown_label.pack(fill="x")

        # --- Commits — highlighted box ---
        commit_box = ctk.CTkFrame(
            self, fg_color=self._commit_bg, corner_radius=10,
        )
        commit_box.pack(fill="x", padx=14, pady=(2, 6))

        ctk.CTkLabel(
            commit_box, text="COMMITS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=_C["text_secondary"],
        ).pack(pady=(8, 0))

        self.commits_label = ctk.CTkLabel(
            commit_box, text="—",
            font=ctk.CTkFont(size=64, weight="bold"),
            text_color=self.accent,
        )
        self.commits_label.pack(pady=(0, 2))

        self.score_label = ctk.CTkLabel(
            commit_box, text="0 pts",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=_C["text_primary"],
        )
        self.score_label.pack(pady=(0, 8))

        # --- Divider ---
        ctk.CTkFrame(self, height=1, fg_color=_C["border"]).pack(
            fill="x", padx=16, pady=(0, 6)
        )

        # --- Stats grid ---
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=(0, 8))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        stat_defs = [
            ("prs",     "PRs",      "🔀"),
            ("issues",  "Issues",   "⚠"),
            ("reviews", "Reviews",  "👁"),
            ("streak",  "Streak",   "🔥"),
            ("today",   "Today",    "📅"),
            ("peak",    "Peak Day", "⚡"),
        ]

        self._stat_labels: dict[str, ctk.CTkLabel] = {}

        for idx, (key, label, icon) in enumerate(stat_defs):
            row, col = divmod(idx, 2)
            cell = ctk.CTkFrame(grid, fg_color="transparent")
            cell.grid(row=row, column=col, sticky="ew", padx=4, pady=2)

            ctk.CTkLabel(
                cell, text=f"{icon}  {label}",
                font=ctk.CTkFont(size=10),
                text_color=_C["text_secondary"], anchor="w",
            ).pack(fill="x")

            val = ctk.CTkLabel(
                cell, text="—",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=_C["text_primary"], anchor="w",
            )
            val.pack(fill="x")
            self._stat_labels[key] = val

    def update(self, stats: dict, is_leading: bool):
        if not stats:
            return

        daily = stats.get("daily_commits", {})
        streak = calculate_streak(daily)
        today_ct = get_today_commits(daily)
        peak_date, peak_val = get_peak_day(daily)
        score = calculate_score(stats)
        prs_opened = stats.get("prs_opened", 0)
        prs_merged = stats.get("prs_merged", 0)

        self.username_label.configure(text=stats.get("username", "?"))
        self.crown_label.configure(text="👑  LEADING" if is_leading else "")
        self.commits_label.configure(text=str(stats.get("commits", 0)))
        self.score_label.configure(text=f"{score:,} pts")

        self._stat_labels["prs"].configure(
            text=f"{prs_opened} opened · {prs_merged} merged"
        )
        self._stat_labels["issues"].configure(text=str(stats.get("issues_created", 0)))
        self._stat_labels["reviews"].configure(text=str(stats.get("reviews", 0)))
        self._stat_labels["streak"].configure(
            text=f"{streak} day{'s' if streak != 1 else ''}"
        )
        self._stat_labels["today"].configure(
            text=f"{today_ct} commit{'s' if today_ct != 1 else ''}"
        )
        peak_str = (
            f"{peak_val} commits ({peak_date[5:]})" if peak_date != "—" else "—"
        )
        self._stat_labels["peak"].configure(text=peak_str)

        avatar_url = stats.get("avatar_url", "")
        if avatar_url and self._avatar_cache is None:
            threading.Thread(
                target=self._load_avatar, args=(avatar_url,), daemon=True
            ).start()

    def _load_avatar(self, url: str):
        try:
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGBA").resize((52, 52))

            mask = Image.new("L", (52, 52), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 51, 51), fill=255)
            img.putalpha(mask)

            ctk_img = ctk.CTkImage(img, size=(52, 52))
            self._avatar_cache = ctk_img
            self.after(0, lambda: self.avatar_label.configure(image=ctk_img, text=""))
        except Exception:
            pass
