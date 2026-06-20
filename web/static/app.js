// Front-end logic: fetch /api/stats, render the scoreboard + charts,
// and auto-refresh on the same interval the desktop app uses.

const css = getComputedStyle(document.documentElement);
const P1_COLOR = css.getPropertyValue("--p1").trim();
const P2_COLOR = css.getPropertyValue("--p2").trim();
const GRID_COLOR = css.getPropertyValue("--border").trim();
const TEXT_COLOR = css.getPropertyValue("--text-secondary").trim();

let dailyChart = null;
let cumulativeChart = null;
let countdownId = null;

// ---- Helpers -------------------------------------------------------------

function plural(n, word) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

function renderStatsGrid(el, p) {
  const peak =
    p.peak_date && p.peak_date !== "—"
      ? `${p.peak_val} commits (${p.peak_date.slice(5)})`
      : "—";
  const cells = [
    ["🔀  PRs", `${p.prs_opened} opened · ${p.prs_merged} merged`],
    ["⚠  Issues", String(p.issues_created)],
    ["👁  Reviews", String(p.reviews)],
    ["🔥  Streak", plural(p.streak, "day")],
    ["📅  Today", plural(p.today, "commit")],
    ["⚡  Peak Day", peak],
  ];
  el.innerHTML = cells
    .map(
      ([label, value]) =>
        `<div class="stat"><div class="stat-label">${label}</div>` +
        `<div class="stat-value">${value}</div></div>`
    )
    .join("");
}

function renderPlayer(prefix, p, isLeading) {
  if (!p) return;
  document.getElementById(`${prefix}-username`).textContent = p.username;
  document.getElementById(`${prefix}-crown`).textContent = isLeading
    ? "👑  LEADING"
    : "";
  document.getElementById(`${prefix}-commits`).textContent = p.commits;
  document.getElementById(`${prefix}-score`).textContent =
    `${p.score.toLocaleString()} pts`;

  const avatar = document.getElementById(`${prefix}-avatar`);
  if (p.avatar_url) avatar.src = p.avatar_url;

  renderStatsGrid(document.getElementById(`${prefix}-stats`), p);
}

// Build a continuous list of YYYY-MM-DD from start_date to today.
function buildDateRange(startDate) {
  const days = [];
  const start = new Date(startDate + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  for (let d = new Date(start); d <= today; d.setDate(d.getDate() + 1)) {
    days.push(d.toISOString().slice(0, 10));
  }
  return days;
}

function seriesFor(daily, dates) {
  return dates.map((d) => daily[d] || 0);
}

function cumulative(arr) {
  let total = 0;
  return arr.map((v) => (total += v));
}

function renderCharts(data) {
  const dates = buildDateRange(data.start_date);
  const labels = dates.map((d) => d.slice(5)); // MM-DD
  const p1 = data.player1 || { username: "P1", daily_commits: {} };
  const p2 = data.player2 || { username: "P2", daily_commits: {} };
  const p1Daily = seriesFor(p1.daily_commits, dates);
  const p2Daily = seriesFor(p2.daily_commits, dates);

  const common = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: TEXT_COLOR } } },
    scales: {
      x: { ticks: { color: TEXT_COLOR }, grid: { color: GRID_COLOR } },
      y: { ticks: { color: TEXT_COLOR }, grid: { color: GRID_COLOR }, beginAtZero: true },
    },
  };

  // Daily grouped bars
  if (dailyChart) dailyChart.destroy();
  dailyChart = new Chart(document.getElementById("daily-chart"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: p1.username, data: p1Daily, backgroundColor: P1_COLOR },
        { label: p2.username, data: p2Daily, backgroundColor: P2_COLOR },
      ],
    },
    options: common,
  });

  // Cumulative lines
  if (cumulativeChart) cumulativeChart.destroy();
  cumulativeChart = new Chart(document.getElementById("cumulative-chart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: p1.username,
          data: cumulative(p1Daily),
          borderColor: P1_COLOR,
          backgroundColor: P1_COLOR,
          tension: 0.25,
        },
        {
          label: p2.username,
          data: cumulative(p2Daily),
          borderColor: P2_COLOR,
          backgroundColor: P2_COLOR,
          tension: 0.25,
        },
      ],
    },
    options: common,
  });
}

// ---- Countdown to next auto-refresh -------------------------------------

function startCountdown(seconds) {
  if (countdownId) clearInterval(countdownId);
  let remaining = seconds;
  const label = document.getElementById("next-label");
  const tick = () => {
    if (remaining <= 0) {
      clearInterval(countdownId);
      load(false);
      return;
    }
    const m = Math.floor(remaining / 60);
    const s = String(remaining % 60).padStart(2, "0");
    label.textContent = `Next sync in ${m}:${s}`;
    remaining -= 1;
  };
  tick();
  countdownId = setInterval(tick, 1000);
}

// ---- Main load -----------------------------------------------------------

async function load(force) {
  const btn = document.getElementById("refresh-btn");
  const sync = document.getElementById("sync-label");
  btn.disabled = true;
  btn.textContent = "Syncing…";
  try {
    const resp = await fetch(`/api/stats${force ? "?force=1" : ""}`);
    const data = await resp.json();

    if (data.error) {
      sync.innerHTML = `<span class="error">${data.error}</span>`;
      return;
    }

    document.getElementById("day-label").textContent =
      `Day ${data.day}  ·  Started ${data.start_date}`;

    renderPlayer("p1", data.player1, data.p1_leads);
    renderPlayer("p2", data.player2, !data.p1_leads);

    document.getElementById("score-diff").textContent = data.score_line;
    const lead = document.getElementById("lead-label");
    lead.textContent = data.leader_text;
    lead.style.color =
      data.diff === 0 ? "#f0c040" : css.getPropertyValue("--leading").trim();

    renderCharts(data);

    sync.textContent = `Last synced: ${data.synced_at}`;
    startCountdown(window.REFRESH_SECONDS);
  } catch (err) {
    sync.innerHTML = `<span class="error">Sync failed — ${err.message}</span>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "↻  Refresh";
  }
}

// ---- Tab switching -------------------------------------------------------

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const target = tab.dataset.tab;
    document.querySelectorAll(".chart-wrap").forEach((w) => {
      w.classList.toggle("hidden", w.dataset.panel !== target);
    });
  });
});

document.getElementById("refresh-btn").addEventListener("click", () => load(true));

// Initial load
load(false);
