// Renders the two dashboard charts from data embedded by the server
// in <script id="chart-data" type="application/json"> (see dashboard.html).

document.addEventListener("DOMContentLoaded", () => {
  const dataEl = document.getElementById("chart-data");
  if (!dataEl || typeof Chart === "undefined") return;

  const data = JSON.parse(dataEl.textContent);

  const trendCtx = document.getElementById("trendChart");
  if (trendCtx) {
    new Chart(trendCtx, {
      type: "line",
      data: {
        labels: data.by_day.map((d) => d.day),
        datasets: [
          {
            label: "Analyses",
            data: data.by_day.map((d) => d.total),
            borderColor: "#5b8cff",
            backgroundColor: "rgba(91,140,255,0.12)",
            tension: 0.35,
            fill: true,
            pointRadius: 3,
          },
          {
            label: "Bugs found",
            data: data.by_day.map((d) => d.bugs || 0),
            borderColor: "#f0616d",
            backgroundColor: "rgba(240,97,109,0.08)",
            tension: 0.35,
            fill: true,
            pointRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#9aa4b8", boxWidth: 12 } } },
        scales: {
          x: { ticks: { color: "#6b7488" }, grid: { color: "#1d2330" } },
          y: { ticks: { color: "#6b7488" }, grid: { color: "#1d2330" }, beginAtZero: true },
        },
      },
    });
  }

  const langCtx = document.getElementById("languageChart");
  if (langCtx) {
    new Chart(langCtx, {
      type: "doughnut",
      data: {
        labels: data.by_language.map((d) => d.language),
        datasets: [
          {
            data: data.by_language.map((d) => d.c),
            backgroundColor: ["#5b8cff", "#7ee8c7", "#f0b429", "#f0616d", "#9b8cff", "#4fd1c5"],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom", labels: { color: "#9aa4b8", boxWidth: 10 } } },
      },
    });
  }
});
