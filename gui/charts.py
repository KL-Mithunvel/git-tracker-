from datetime import date, timedelta

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk

import config
from engine.metrics import leadership_periods

_C = config.COLORS


class _BaseChart(ctk.CTkFrame):
    """Shared resize-responsive base for both chart types."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", _C["surface"])
        super().__init__(master, **kwargs)

        # Figure (not pyplot) so no global figure manager holds references.
        # Constrained layout re-fits titles/labels/legend on every resize,
        # so no manual tight_layout or resize handling is needed.
        self.fig = Figure(facecolor=_C["chart_bg"], layout="constrained")
        self.fig.get_layout_engine().set(w_pad=0.08, h_pad=0.08)
        self.ax = self.fig.add_subplot()
        self.ax.set_facecolor(_C["chart_bg"])

        # matplotlib binds its own <Configure> handler that resizes the figure
        # AND its backing image (DPI-aware). Do NOT re-bind <Configure> here —
        # replacing that handler leaves the image at its initial 640x480 and
        # the chart renders cropped/off-centre.
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        widget = self.canvas.get_tk_widget()
        # Dark background so no white flash; small requested size so the
        # canvas never forces the window taller than the screen — pack's
        # expand=True grows it to fill whatever space is available.
        widget.configure(bg=_C["chart_bg"], width=300, height=150,
                         highlightthickness=0)
        widget.pack(fill="both", expand=True, padx=0, pady=0)


class CommitChart(_BaseChart):
    """Grouped bar chart — commits per day for both players."""

    def update(
        self,
        p1_stats: dict | None,
        p2_stats: dict | None,
        p1_name: str,
        p2_name: str,
    ):
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
        self.canvas.draw_idle()


class CumulativeChart(_BaseChart):
    """Line chart — running total commits over the competition period."""

    def update(
        self,
        p1_stats: dict | None,
        p2_stats: dict | None,
        p1_name: str,
        p2_name: str,
    ):
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
            linewidth=3.5, marker="o", markersize=4, label=p1_name,
        )
        self.ax.plot(
            xs, p2_cumul, color=_C["p2_accent"],
            linewidth=3.5, marker="o", markersize=4, label=p2_name,
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

        # Shade background by who led in each period.
        idx = {d: i for i, d in enumerate(days)}
        for per in leadership_periods(p1_daily, p2_daily, p1_name, p2_name, days):
            if per["leader"] is None:
                continue
            col = _C["p1_accent"] if per["leader"] == p1_name else _C["p2_accent"]
            self.ax.axvspan(idx[per["start"]] - 0.5, idx[per["end"]] + 0.5,
                            color=col, alpha=0.07, linewidth=0)

        _style_axes(self.ax, [d[5:] for d in days], xs, "Cumulative Commits (shaded = who led)", legend_loc="upper left")
        self.canvas.draw_idle()


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
    # Thin out labels so long competitions stay readable.
    step = max(1, -(-len(xs) // 14))
    ax.set_xticks(xs[::step])
    ax.margins(x=0.01)
    ax.set_xticklabels(labels[::step], color=_C["text_secondary"], fontsize=12)
    ax.tick_params(axis="y", colors=_C["text_secondary"], labelsize=12)
    ax.spines[:].set_visible(False)
    ax.set_title(title, color=_C["text_primary"], fontsize=15, pad=8)
    ax.grid(axis="y", color=_C["border"], linewidth=0.6, alpha=0.7)
    ax.legend(
        facecolor=_C["surface"],
        edgecolor=_C["border"],
        labelcolor=_C["text_primary"],
        fontsize=12,
        loc=legend_loc,
    )
