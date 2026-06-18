from datetime import date, timedelta

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk

import config


_C = config.COLORS


class CommitChart(ctk.CTkFrame):
    """Grouped bar chart — commits per day for both players."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", _C["surface"])
        super().__init__(master, **kwargs)

        self.fig, self.ax = plt.subplots(figsize=(11, 2.6), facecolor=_C["surface"])
        self.ax.set_facecolor(_C["chart_bg"])
        self.fig.subplots_adjust(left=0.04, right=0.98, top=0.82, bottom=0.18)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

    def update(
        self,
        p1_stats: dict | None,
        p2_stats: dict | None,
        p1_name: str,
        p2_name: str,
    ):
        self.ax.clear()
        self.ax.set_facecolor(_C["chart_bg"])

        start = date.fromisoformat(config.COMPETITION_START_DATE)
        today = date.today()
        days: list[str] = []
        d = start
        while d <= today:
            days.append(d.strftime("%Y-%m-%d"))
            d += timedelta(days=1)

        p1_daily = (p1_stats or {}).get("daily_commits", {})
        p2_daily = (p2_stats or {}).get("daily_commits", {})

        p1_vals = [p1_daily.get(day, 0) for day in days]
        p2_vals = [p2_daily.get(day, 0) for day in days]

        xs = list(range(len(days)))
        w = 0.38

        self.ax.bar(
            [x - w / 2 for x in xs], p1_vals, w,
            label=p1_name, color=_C["p1_accent"], alpha=0.88,
        )
        self.ax.bar(
            [x + w / 2 for x in xs], p2_vals, w,
            label=p2_name, color=_C["p2_accent"], alpha=0.88,
        )

        labels = [d[5:] for d in days]  # MM-DD
        self.ax.set_xticks(xs)
        self.ax.set_xticklabels(labels, color=_C["text_secondary"], fontsize=9)
        self.ax.tick_params(axis="y", colors=_C["text_secondary"], labelsize=9)
        self.ax.spines[:].set_visible(False)
        self.ax.set_title(
            "Commits per Day", color=_C["text_primary"], fontsize=11, pad=6,
        )
        self.ax.grid(axis="y", color=_C["border"], linewidth=0.6, alpha=0.7)
        self.ax.legend(
            facecolor=_C["surface"],
            edgecolor=_C["border"],
            labelcolor=_C["text_primary"],
            fontsize=9,
            loc="upper right",
        )

        self.canvas.draw()
