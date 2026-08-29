/**
 * SpaceGuard AI — Dashboard JavaScript
 * Chart.js initialisation and analysis trigger.
 */

const CHART_DEFAULTS = {
  responsive: true,
  animation: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      mode: 'index',
      intersect: false,
      backgroundColor: '#ffffff',
      borderColor: '#dde2ea',
      borderWidth: 1,
      titleColor: '#5a6678',
      bodyColor: '#1e2530',
    },
  },
  scales: {
    x: {
      ticks: { color: '#9aa5b4', maxTicksLimit: 6, font: { size: 10 } },
      grid: { color: '#e8ecf2' },
    },
    y: {
      ticks: { color: '#9aa5b4', font: { size: 10 } },
      grid: { color: '#e8ecf2' },
    },
  },
};

function makeDataset(data, color, label) {
  return {
    label,
    data,
    borderColor: color,
    backgroundColor: color + '22',
    borderWidth: 1.5,
    fill: true,
    tension: 0.3,
    pointRadius: 0,
    pointHoverRadius: 4,
  };
}

/**
 * Initialize all dashboard charts.
 * @param {object} d - chart data object from Django context
 */
function initCharts(d) {
  if (!d || !d.labels) return;

  new Chart(document.getElementById('tempChart'), {
    type: 'line',
    data: { labels: d.labels, datasets: [makeDataset(d.temperature, '#f85149', 'Temperature (°C)')] },
    options: { ...CHART_DEFAULTS, plugins: { ...CHART_DEFAULTS.plugins, title: { display: true, text: 'Temperature (°C)', color: '#7d8590', font: { size: 11 } } } },
  });

  new Chart(document.getElementById('voltChart'), {
    type: 'line',
    data: { labels: d.labels, datasets: [makeDataset(d.battery_voltage, '#3b82d4', 'Battery Voltage (V)')] },
    options: { ...CHART_DEFAULTS, plugins: { ...CHART_DEFAULTS.plugins, title: { display: true, text: 'Battery Voltage (V)', color: '#7d8590', font: { size: 11 } } } },
  });

  new Chart(document.getElementById('fuelChart'), {
    type: 'line',
    data: { labels: d.labels, datasets: [makeDataset(d.fuel_level, '#3fb950', 'Fuel Level (%)')] },
    options: { ...CHART_DEFAULTS, plugins: { ...CHART_DEFAULTS.plugins, title: { display: true, text: 'Fuel Level (%)', color: '#7d8590', font: { size: 11 } } } },
  });

  new Chart(document.getElementById('signalChart'), {
    type: 'line',
    data: { labels: d.labels, datasets: [makeDataset(d.signal_strength, '#7c5cd8', 'Signal Strength (dBm)')] },
    options: { ...CHART_DEFAULTS, plugins: { ...CHART_DEFAULTS.plugins, title: { display: true, text: 'Signal Strength (dBm)', color: '#7d8590', font: { size: 11 } } } },
  });
}

/**
 * Initialize history page charts.
 */
function initHistoryCharts(d) {
  if (!d || !d.labels) return;
  const configs = [
    { id: 'histTempChart',   key: 'temperature',        color: '#f85149', label: 'Temperature (°C)' },
    { id: 'histVoltChart',   key: 'battery_voltage',    color: '#3b82d4', label: 'Battery Voltage (V)' },
    { id: 'histFuelChart',   key: 'fuel_level',         color: '#3fb950', label: 'Fuel Level (%)' },
    { id: 'histSignalChart', key: 'signal_strength',    color: '#7c5cd8', label: 'Signal (dBm)' },
    { id: 'histRadChart',    key: 'radiation',          color: '#e06c00', label: 'Radiation (mSv)' },
    { id: 'histPressChart',  key: 'pressure',           color: '#00bcd4', label: 'Pressure (kPa)' },
  ];
  configs.forEach(cfg => {
    const el = document.getElementById(cfg.id);
    if (!el) return;
    new Chart(el, {
      type: 'line',
      data: { labels: d.labels, datasets: [makeDataset(d[cfg.key], cfg.color, cfg.label)] },
      options: CHART_DEFAULTS,
    });
  });
}

/**
 * Run AI analysis pipeline for a mission.
 */
function runAnalysis(missionId) {
  const btn = document.getElementById('runAnalysisBtn');
  if (btn) { btn.classList.add('loading'); btn.disabled = true; }

  fetch(`/api/missions/${missionId}/analyze/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json' },
  })
  .then(r => r.json())
  .then(data => {
    if (btn) { btn.classList.remove('loading'); btn.disabled = false; }
    window.location.reload();
  })
  .catch(err => {
    console.error('Analysis failed:', err);
    if (btn) { btn.classList.remove('loading'); btn.disabled = false; }
    alert('Analysis request failed. Check the console for details.');
  });
}

/**
 * Get CSRF token from cookies.
 */
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    for (const cookie of document.cookie.split(';')) {
      const c = cookie.trim();
      if (c.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(c.slice(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Auto-refresh health indicator every 30 seconds
setInterval(() => {
  const missionId = typeof MISSION_ID !== 'undefined' ? MISSION_ID : null;
  if (missionId) {
    fetch(`/api/missions/${missionId}/health/`)
      .then(r => r.json())
      .then(data => {
        // Silently update — full refresh only when needed
        console.log('Health check:', data.health_score, data.risk_level);
      })
      .catch(() => {});
  }
}, 30000);
