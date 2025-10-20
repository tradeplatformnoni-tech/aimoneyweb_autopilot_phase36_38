
/*
  AI Money Web — Glow Charts Boot (Chart.js v4)
  - Adds subtle glow to line datasets
  - Safe init if canvas elements are present
*/
(() => {
  function glowPlugin() {
    return {
      id: "glow",
      afterDatasetsDraw(chart, args, pluginOptions) {
        const { ctx } = chart;
        chart.data.datasets.forEach((ds, i) => {
          const meta = chart.getDatasetMeta(i);
          if (!meta || meta.hidden) return;
          ctx.save();
          ctx.shadowColor = pluginOptions?.color || "rgba(63,125,240,0.6)";
          ctx.shadowBlur = pluginOptions?.blur || 12;
          ctx.lineWidth = (ds.borderWidth || 2) + 1;
          ctx.stroke(meta.dataset);
          ctx.restore();
        });
      }
    };
  }

  function initCharts() {
    if (typeof Chart === "undefined") return;
    const canvases = document.querySelectorAll("canvas.chart-glow");
    canvases.forEach((cv) => {
      if (cv._aimw) return; // prevent double init
      const ctx = cv.getContext("2d");
      const gradient = ctx.createLinearGradient(0, 0, 0, cv.height);
      gradient.addColorStop(0, "#3f7df0");
      gradient.addColorStop(1, "rgba(63,125,240,0.1)");
      const data = cv.dataset.series ? JSON.parse(cv.dataset.series) : { labels: [], datasets: [] };
      const cfg = {
        type: "line",
        data: data.labels?.length ? data : {
          labels: Array.from({length: 30}, (_,i)=>i+1),
          datasets: [{
            label: cv.dataset.label || "Waiting for data…",
            data: Array.from({length: 30}, ()=> null),
            borderColor: "#3f7df0",
            borderWidth: 2,
            tension: 0.35,
            fill: true,
            backgroundColor: gradient,
            pointRadius: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: { display: !!cv.dataset.showLegend },
            tooltip: { enabled: true }
          },
          scales: {
            x: { grid: { display: false } },
            y: { grid: { color: "rgba(255,255,255,0.06)" } }
          }
        },
        plugins: [glowPlugin()]
      };
      cv._aimw = new Chart(ctx, cfg);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCharts, { once: true });
  } else {
    initCharts();
  }
})();
