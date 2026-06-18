from datetime import date, timedelta

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk

import config

_C = config.COLORS


class _BaseChart(ctk.CTkFrame):
    """Shared resize-responsive base for both chart types."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", _C["surface"])
        super().__init__(master, **kwargs)

        self.fig, self.ax = plt.subplots(facecolor=_C["chart_bg"])
        self.ax.set_facecolor(_C["chart_bg"])
        self._last_args: tuple | None = None

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        widget = self.canvas.get_tk_widget()
        # Dark background so no white flash when figure hasn't been sized yet.
        widget.configure(bg=_C["chart_bg"])
        widget.pack(fill="both", expand=True, padx=0, pady=0)
        widget.bind("<Configure>", self._on_resize)
        self._resize_id = None

    def _on_resize(self, event):
        if self._resize_id:
            self.after_cancel(self._resize_id)
        w, h = event.width, event.height
        self._resize_id = self.after(120, lambda: self._apply_resize(w, h))

    def _apply_resize(self, w: int, h: int):
        if w > 50 and h > 50:
            self.fig.set_size_inches(w / self.fig.dpi, h / self.fig.dpi)
            if self._last_args:
                # Full redraw so labels/content fit the new dimensions.
                self.update(*self._last_args)
            else:
                self.canvas.draw_idle()
        self._resize_id = None

    def _fit_to_widget(self):
        w = self.canvas.get_tk_widget().winfo_width()
        h = self.canvas.get_tk_widget().winfo_height()
        if w > 50 and h > 50:
            self.fig.set_size_inches(w / self.fig.dpi, h / self.fig.dpi)


class CommitChart(_BaseChart):
    """Grouped bar chart — commits per day for both players."""

    def update(
        self,
        p1_stats: dict | None,
        p2_stats: dict | None,
        p1_name: str,
        p2_name: str,
    ):
        self._last_args = (p1_stats, p2_stats, p1_name, p2_name)
        self._fit_to_widget()
        self.ax.clear()
        self.ax.set_facecolor(_C["chart_bg"])

        days = _date_range(config.COMPETITION_START_DATE)
        p1_daily = (p1_stats or {}).get("daily_commits", {})
        p2_daily = (p2_stats or {}).get("daily_commits", {})

        p1_vals = [p1_daily.get(d, 0) for d in days]
        p2_vals = [p2_daily.get(d, 0) for d in days]

        xs = list(range(len(days)))
        bar_w = 0.38

        self.ax.bar(
            [x - bar_w / 2 for x in xs], p1_vals, bar_w,
            label=p1_name, color=_C["p1_accent"], alpha=0.88,
        )
        self.ax.bar(
            [x + bar_w / 2 for x in xs], p2_vals, bar_w,
            label=p2_name, color=_C["p2_accent"], alpha=0.88,
        )

        _style_axes(self.ax, [d[5:] for d in days], xs, "Commits per Day")
        self.fig.tight_layout(pad=0.5)
        self.canvas.draw()


class CumulativeChart(_BaseChart):
    """Line chart — running total commits over the competition period."""

    def update(
        self,
        p1_stats: dict | None,
        p2_stats: dict | None,
        p1_name: str,
        p2_name: str,
    ):
        self._last_args = (p1_stats, p2_stats, p1_name, p2_name)
        self._fit_to_widget()
        self.ax.clear()
        self.ax.set_facecolor(_C["chart_bg"])

        days = _date_range(config.COMPETITION_START_DATE)
        p1_daily = (p1_stats or {}).get("daily_commits", {})
        p2_daily = (p2_stats or {}).get("daily_commits", {})

        p1_cumul = _running_total(p1_daily, days)
        p2_cumul = _running_total(p2_daily, days)
        xs = list(range(len(days)))

        self.ax.plot(
            xs, p1_cumul, color=_C["p1_accent"],
            linewidth=2.5, marker="o", markersize=5, label=p1_name,
        )
        self.ax.plot(
            xs, p2_cumul, color=_C["p2_accent"],
            linewidth=2.5, marker="o", markersize=5, label=p2_name,
        )
        self.ax.fill_between(
            xs, p1_cumul, p2_cumul,
            where=[a >= b for a, b in zip(p1_cumul, p2_cumul)],
            alpha=0.12, color=_C["p1_accent"],
        )
        self.ax.fill_between(
            xs, p1_cumul, p2_cumul,
            where=[a < b for a, b in zip(p1_cumul, p2_cumul)],
            alpha=0.12, color=_C["p2_accent"],
        )

        _style_axes(self.ax, [d[5:] for d in days], xs, "Cumulative Commits", legend_loc="upper left")
        self.fig.tight_layout(pad=0.5)
        self.canvas.draw()


# --- helpers ---

def _date_range(since: str) -> list[str]:
    days = []
    d = date.fromisoformat(since)
    while d <= date.today():
        days.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return days


def _running_total(daily: dict, days: list) -> list:
    total = 0
    result = []
    for d in days:
        total += daily.get(d, 0)
        result.append(total)
    return result


def _style_axes(ax, labels, xs, title, legend_loc="upper right"):
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, color=_C["text_secondary"], fontsize=9)
    ax.tick_params(axis="y", colors=_C["text_secondary"], labelsize=9)
    ax.spines[:].set_visible(False)
    ax.set_title(title, color=_C["text_primary"], fontsize=11, pad=6)
    ax.grid(axis="y", color=_C["border"], linewidth=0.6, alpha=0.7)
    ax.legend(
        facecolor=_C["surface"],
        edgecolor=_C["border"],
        labelcolor=_C["text_primary"],
        fontsize=9,
        loc=legend_loc,
    )
