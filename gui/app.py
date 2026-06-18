import threading
from datetime import datetime, date

import customtkinter as ctk

import config
from api.github_client import GitHubClient
from db.database import Database
from engine.metrics import calculate_score, competition_days_elapsed
from gui.player_card import PlayerCard
from gui.charts import CommitChart

_C = config.COLORS


class App(ctk.CTk):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.db = Database()
        self.client = GitHubClient(cfg["token"])
        self.p1 = cfg["player1"]
        self.p2 = cfg["player2"]

        self.title("Git Battle ⚔")
        self.geometry("1300x800")
        self.minsize(1100, 720)
        self.configure(fg_color=_C["bg"])

        self._build_ui()
        self._update_day_counter()

        # Try loading cached data immediately, then fetch fresh
        self._load_cached()
        self.after(300, self._trigger_refresh)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._build_header()
        self._build_main()
        self._build_chart_section()
        self._build_statusbar()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=_C["surface"], height=58, corner_radius=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text="⚔  GIT BATTLE",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=_C["text_primary"],
        ).pack(side="left", padx=22)

        self.day_label = ctk.CTkLabel(
            hdr, text="",
            font=ctk.CTkFont(size=13),
            text_color=_C["text_secondary"],
        )
        self.day_label.pack(side="left", padx=16)

        self.refresh_btn = ctk.CTkButton(
            hdr,
            text="↻  Refresh",
            width=110, height=34,
            fg_color="#238636", hover_color="#2ea043",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._trigger_refresh,
        )
        self.refresh_btn.pack(side="right", padx=20)

    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=18, pady=(14, 6))
        main.columnconfigure(0, weight=5)
        main.columnconfigure(1, weight=2)
        main.columnconfigure(2, weight=5)
        main.rowconfigure(0, weight=1)

        self.p1_card = PlayerCard(main, player_num=1)
        self.p1_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        # VS centre panel
        vs = ctk.CTkFrame(main, fg_color="transparent")
        vs.grid(row=0, column=1, sticky="nsew", padx=6)

        ctk.CTkFrame(vs, fg_color="transparent").pack(expand=True, fill="both")

        ctk.CTkLabel(
            vs, text="VS",
            font=ctk.CTkFont(size=40, weight="bold"),
            text_color=_C["border"],
        ).pack()

        self.score_diff_label = ctk.CTkLabel(
            vs, text="",
            font=ctk.CTkFont(size=13),
            text_color=_C["text_secondary"],
        )
        self.score_diff_label.pack(pady=6)

        self.lead_label = ctk.CTkLabel(
            vs, text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=_C["leading"],
        )
        self.lead_label.pack()

        ctk.CTkFrame(vs, fg_color="transparent").pack(expand=True, fill="both")

        self.p2_card = PlayerCard(main, player_num=2)
        self.p2_card.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

    def _build_chart_section(self):
        outer = ctk.CTkFrame(
            self, fg_color=_C["surface"], corner_radius=12, height=220,
        )
        outer.pack(fill="x", padx=18, pady=(0, 8))
        outer.pack_propagate(False)

        self.chart = CommitChart(outer)
        self.chart.pack(fill="both", expand=True)

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent", height=26)
        bar.pack(fill="x", padx=18)
        bar.pack_propagate(False)

        self.sync_label = ctk.CTkLabel(
            bar, text="Fetching data…",
            font=ctk.CTkFont(size=11),
            text_color=_C["text_secondary"],
        )
        self.sync_label.pack(side="left")

        self.next_label = ctk.CTkLabel(
            bar, text="",
            font=ctk.CTkFont(size=11),
            text_color=_C["text_secondary"],
        )
        self.next_label.pack(side="right")

    # ------------------------------------------------------------------
    # Data refresh logic
    # ------------------------------------------------------------------

    def _load_cached(self):
        p1 = self.db.get_stats(self.p1)
        p2 = self.db.get_stats(self.p2)
        if p1 or p2:
            self._apply_stats(p1, p2, from_cache=True)

    def _trigger_refresh(self):
        self.refresh_btn.configure(state="disabled", text="Syncing…")
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _fetch_and_update(self):
        since = config.COMPETITION_START_DATE
        try:
            p1_stats = self.client.fetch_user_stats(self.p1, since)
            self.db.save_stats(p1_stats)

            p2_stats = self.client.fetch_user_stats(self.p2, since)
            self.db.save_stats(p2_stats)

            self.db.log_sync("ok")
            self.after(0, lambda: self._apply_stats(p1_stats, p2_stats))

        except Exception as exc:
            self.db.log_sync("error", str(exc))
            # Fall back to cached data
            p1_cached = self.db.get_stats(self.p1)
            p2_cached = self.db.get_stats(self.p2)
            self.after(
                0, lambda: self._apply_stats(p1_cached, p2_cached, error=str(exc))
            )
        finally:
            self.after(
                0,
                lambda: self.refresh_btn.configure(state="normal", text="↻  Refresh"),
            )

    def _apply_stats(
        self,
        p1_stats: dict | None,
        p2_stats: dict | None,
        from_cache: bool = False,
        error: str = "",
    ):
        p1_score = calculate_score(p1_stats) if p1_stats else 0
        p2_score = calculate_score(p2_stats) if p2_stats else 0
        p1_leads = p1_score >= p2_score

        if p1_stats:
            self.p1_card.update(p1_stats, is_leading=p1_leads)
        if p2_stats:
            self.p2_card.update(p2_stats, is_leading=not p1_leads)

        diff = abs(p1_score - p2_score)
        self.score_diff_label.configure(text=f"{p1_score:,} vs {p2_score:,} pts")
        if diff == 0:
            self.lead_label.configure(text="TIE!", text_color="#f0c040")
        else:
            leader = self.p1 if p1_leads else self.p2
            self.lead_label.configure(
                text=f"↑ {leader}  +{diff:,} pts", text_color=_C["leading"]
            )

        self.chart.update(p1_stats, p2_stats, self.p1, self.p2)

        now = datetime.now().strftime("%I:%M %p")
        suffix = " (cached)" if from_cache else ""
        err_suffix = f"  ·  Error: {error[:60]}" if error else ""
        self.sync_label.configure(text=f"Last synced: {now}{suffix}{err_suffix}")

        # Schedule next auto-refresh
        self._schedule_next(config.REFRESH_INTERVAL_SECONDS)

    def _schedule_next(self, seconds: int):
        self._cancel_countdown()
        self._countdown = seconds
        self._tick()

    def _tick(self):
        if self._countdown <= 0:
            self._trigger_refresh()
            return
        mins, secs = divmod(self._countdown, 60)
        self.next_label.configure(text=f"Next sync in {mins}:{secs:02d}")
        self._countdown -= 1
        self._countdown_id = self.after(1000, self._tick)

    def _cancel_countdown(self):
        cid = getattr(self, "_countdown_id", None)
        if cid:
            self.after_cancel(cid)
            self._countdown_id = None

    # ------------------------------------------------------------------
    # Day counter
    # ------------------------------------------------------------------

    def _update_day_counter(self):
        day = competition_days_elapsed()
        start = config.COMPETITION_START_DATE
        self.day_label.configure(
            text=f"Day {day}  ·  Started {start}"
        )
        self.after(60_000, self._update_day_counter)
