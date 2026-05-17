/**
 * Shared Chart.js factory functions
 * Used by dashboard.html and attendance.html
 */

const CHART_DEFAULTS = {
  primary:  '#4f46e5',
  accent:   '#10b981',
  grid:     'rgba(255,255,255,0.06)',
  text:     '#64748b',
  font:     'Inter',
};

Chart.defaults.color          = CHART_DEFAULTS.text;
Chart.defaults.font.family    = CHART_DEFAULTS.font;
Chart.defaults.font.size      = 11;
Chart.defaults.plugins.legend.display = false;

/** Build a compact bar chart */
function buildBarChart(canvasId, labels, data, label = 'Count') {
  const ctx = document.getElementById(canvasId).getContext('2d');

  const gradient = ctx.createLinearGradient(0, 0, 0, 200);
  gradient.addColorStop(0,   'rgba(79,70,229,0.7)');
  gradient.addColorStop(1,   'rgba(79,70,229,0.05)');

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label,
        data,
        backgroundColor: gradient,
        borderColor:     CHART_DEFAULTS.primary,
        borderWidth:     1,
        borderRadius:    4,
        borderSkipped:   false,
      }],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      animation:           { duration: 400 },
      plugins: {
        tooltip: {
          backgroundColor: '#1e2230',
          borderColor:     'rgba(255,255,255,0.1)',
          borderWidth:     1,
          padding:         8,
          titleFont:       { size: 11 },
          bodyFont:        { size: 11 },
        },
      },
      scales: {
        x: {
          grid:  { color: CHART_DEFAULTS.grid, drawBorder: false },
          ticks: { font: { size: 10 } },
        },
        y: {
          beginAtZero: true,
          grid:        { color: CHART_DEFAULTS.grid, drawBorder: false },
          ticks:       { precision: 0, font: { size: 10 } },
        },
      },
    },
  });
}

/** Build a line chart (monthly/yearly trends) */
function buildLineChart(canvasId, labels, data, label = 'Attendance') {
  const ctx = document.getElementById(canvasId).getContext('2d');

  const gradient = ctx.createLinearGradient(0, 0, 0, 200);
  gradient.addColorStop(0,   'rgba(16,185,129,0.25)');
  gradient.addColorStop(1,   'rgba(16,185,129,0)');

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label,
        data,
        borderColor:     CHART_DEFAULTS.accent,
        backgroundColor: gradient,
        borderWidth:     2,
        fill:            true,
        tension:         0.4,
        pointRadius:     3,
        pointBackgroundColor: CHART_DEFAULTS.accent,
      }],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      animation:           { duration: 400 },
      plugins: {
        tooltip: {
          backgroundColor: '#1e2230',
          borderColor:     'rgba(255,255,255,0.1)',
          borderWidth:     1,
          padding:         8,
        },
      },
      scales: {
        x: { grid: { color: CHART_DEFAULTS.grid, drawBorder: false },
             ticks: { font: { size: 10 } } },
        y: { beginAtZero: true,
             grid: { color: CHART_DEFAULTS.grid, drawBorder: false },
             ticks: { precision: 0, font: { size: 10 } } },
      },
    },
  });
}
