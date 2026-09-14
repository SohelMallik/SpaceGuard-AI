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
      backgroundColor: '#1c2230',
      borderColor: '#30363d',
      borderWidth: 1,
      titleColor: '#7d8590',
      bodyColor: '#e6edf3',
    },
  },
  scales: {
    x: {
      ticks: { color: '#7d8590', maxTicksLimit: 6, font: { size: 10 } },
      grid: { color: 'rgba(48,54,61,0.5)' },
    },
    y: {
      ticks: { color: '#7d8590', font: { size: 10 } },
      grid: { color: 'rgba(48,54,61,0.5)' },
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
/**
 * Build Chart.js options with a title plugin safely merged in.
 */
function chartOptions(titleText) {
  return {
    responsive: true,
    animation: false,
    plugins: {
      legend: { display: false },
      tooltip: CHART_DEFAULTS.plugins.tooltip,
      title: { display: true, text: titleText, color: '#7d8590', font: { size: 11 } },
    },
    scales: CHART_DEFAULTS.scales,
  };
}

function initCharts(d) {
  if (!d || !d.labels) return;

  new Chart(document.getElementById('tempChart'), {
    type: 'line',
    data: { labels: d.labels, datasets: [makeDataset(d.temperature, '#f85149', 'Temperature (°C)')] },
    options: chartOptions('Temperature (°C)'),
  });

  new Chart(document.getElementById('voltChart'), {
    type: 'line',
    data: { labels: d.labels, datasets: [makeDataset(d.battery_voltage, '#3b82d4', 'Battery Voltage (V)')] },
    options: chartOptions('Battery Voltage (V)'),
  });

  new Chart(document.getElementById('fuelChart'), {
    type: 'line',
    data: { labels: d.labels, datasets: [makeDataset(d.fuel_level, '#3fb950', 'Fuel Level (%)')] },
    options: chartOptions('Fuel Level (%)'),
  });

  new Chart(document.getElementById('signalChart'), {
    type: 'line',
    data: { labels: d.labels, datasets: [makeDataset(d.signal_strength, '#7c5cd8', 'Signal Strength (dBm)')] },
    options: chartOptions('Signal Strength (dBm)'),
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
  if (btn) {
    btn.classList.add('loading');
    btn.disabled = true;
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Analyzing…';
  }

  fetch(`/api/missions/${missionId}/analyze/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json' },
  })
  .then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  })
  .then(() => {
    window.location.reload();
  })
  .catch(err => {
    console.error('Analysis failed:', err);
    if (btn) {
      btn.classList.remove('loading');
      btn.disabled = false;
      btn.innerHTML = btn.dataset.originalText || '<i class="bi bi-play-fill me-1"></i>Run Analysis';
    }
    // Show inline error instead of blocking alert()
    const errEl = document.getElementById('analysisError');
    if (errEl) {
      errEl.textContent = `Analysis failed: ${err.message}. Check console for details.`;
      errEl.classList.remove('d-none');
      setTimeout(() => errEl.classList.add('d-none'), 6000);
    }
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
  if (!missionId) return;

  fetch(`/api/missions/${missionId}/health/`)
    .then(r => r.json())
    .then(data => {
      if (!data || !data.health_score) return;

      // Update health score number
      const scoreEl = document.querySelector('.health-score-num');
      if (scoreEl) scoreEl.textContent = data.health_score;

      // Update risk badge
      const riskBadge = document.querySelector('.badge[class*="status-badge"]');
      if (riskBadge) riskBadge.textContent = data.risk_level || '';

      // Update last-refreshed indicator
      const tsEl = document.getElementById('lastRefreshed');
      if (tsEl) {
        const now = new Date();
        tsEl.textContent = `Refreshed ${now.toLocaleTimeString()}`;
      }
    })
    .catch(() => {});
}, 30000);
