(function () {
  'use strict';

  var charts = [];
  var colours = ['#299b62', '#d69b2d', '#2878a6', '#8e6cb0', '#d36b4d', '#4c9a9a'];

  function setText(selector, value) {
    var element = document.querySelector(selector);
    if (element) element.textContent = value;
  }

  function formatDate(value) {
    var date = new Date(value);
    return Number.isNaN(date.getTime())
      ? '\u2014'
      : date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  function setStatus(selector, online) {
    var element = document.querySelector(selector);
    if (!element) return;
    element.textContent = online ? 'Operational' : 'Unavailable';
    element.className = online ? 'is-online' : 'is-offline';
  }

  function fetchJson(url) {
    return fetch(url, { headers: { Accept: 'application/json' } }).then(function (response) {
      if (!response.ok) throw new Error(String(response.status));
      return response.json();
    });
  }

  function chartOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: getComputedStyle(document.documentElement).getPropertyValue('--text').trim(),
            font: { family: 'Poppins' }
          }
        }
      }
    };
  }

  function makeChart(id, config) {
    var canvas = document.getElementById(id);
    if (canvas && window.Chart) charts.push(new window.Chart(canvas, config));
  }

  function setKpis(dashboard, model) {
    setText('[data-kpi-total]', dashboard.total_predictions || '0');
    setText('[data-kpi-today]', dashboard.predictions_today || '0');
    setText('[data-kpi-crop]', dashboard.most_predicted_crop || '\u2014');
    var accuracy = model && model.accuracy != null ? model.accuracy : dashboard.model_accuracy;
    setText('[data-kpi-accuracy]', accuracy == null ? '\u2014' : (Number(accuracy) * 100).toFixed(1) + '%');
    document.querySelectorAll('[data-skeleton]').forEach(function (element) {
      element.removeAttribute('data-skeleton');
    });
  }

  function renderDistribution(statistics) {
    var entries = Object.entries(statistics.crop_distribution || {});
    var emptyState = document.querySelector('[data-empty-distribution]');
    if (emptyState) emptyState.classList.toggle('hidden', entries.length > 0);
    makeChart('distribution-chart', {
      type: 'doughnut',
      data: {
        labels: entries.map(function (entry) { return entry[0]; }),
        datasets: [{
          data: entries.map(function (entry) { return entry[1]; }),
          backgroundColor: entries.map(function (_, index) { return colours[index % colours.length]; }),
          borderWidth: 2,
          borderColor: getComputedStyle(document.documentElement).getPropertyValue('--surface').trim()
        }]
      },
      options: Object.assign(chartOptions(), { cutout: '66%' })
    });
  }

  function renderTrend(recent) {
    var dates = [];
    var counts = [];
    for (var offset = 6; offset >= 0; offset -= 1) {
      var date = new Date();
      date.setHours(0, 0, 0, 0);
      date.setDate(date.getDate() - offset);
      dates.push(date);
      counts.push(recent.filter(function (item) {
        return new Date(item.created_at).toDateString() === date.toDateString();
      }).length);
    }
    makeChart('trend-chart', {
      type: 'line',
      data: {
        labels: dates.map(function (date) { return date.toLocaleDateString([], { weekday: 'short' }); }),
        datasets: [{ label: 'Predictions', data: counts, borderColor: '#299b62', backgroundColor: 'rgba(41,155,98,.14)', fill: true, tension: 0.35, pointRadius: 3 }]
      },
      options: Object.assign(chartOptions(), { scales: { x: { ticks: { color: '#698075' }, grid: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0, color: '#698075' }, grid: { color: 'rgba(105,128,117,.15)' } } } })
    });
  }

  function renderConfidence(recent) {
    var grouped = {};
    recent.forEach(function (item) {
      var crop = item.predicted_crop || 'Unknown';
      if (!grouped[crop]) grouped[crop] = [];
      grouped[crop].push(Number(item.confidence) || 0);
    });
    var entries = Object.entries(grouped).map(function (entry) {
      var total = entry[1].reduce(function (sum, value) { return sum + value; }, 0);
      return [entry[0], total / entry[1].length];
    });
    var emptyState = document.querySelector('[data-empty-confidence]');
    if (emptyState) emptyState.classList.toggle('hidden', entries.length > 0);
    makeChart('confidence-chart', {
      type: 'bar',
      data: {
        labels: entries.map(function (entry) { return entry[0]; }),
        datasets: [{ label: 'Average confidence', data: entries.map(function (entry) { return entry[1]; }), backgroundColor: '#d69b2d', borderRadius: 6, maxBarThickness: 50 }]
      },
      options: Object.assign(chartOptions(), { scales: { x: { ticks: { color: '#698075' }, grid: { display: false } }, y: { beginAtZero: true, max: 100, ticks: { callback: function (value) { return value + '%'; }, color: '#698075' }, grid: { color: 'rgba(105,128,117,.15)' } } } })
    });
  }

  function recentTable(recent) {
    var body = document.querySelector('[data-recent-predictions]');
    if (!body) return;
    body.replaceChildren();
    if (!recent.length) {
      var emptyRow = document.createElement('tr');
      var emptyCell = document.createElement('td');
      emptyCell.colSpan = 4;
      emptyCell.textContent = 'No predictions have been recorded yet.';
      emptyRow.appendChild(emptyCell);
      body.appendChild(emptyRow);
      return;
    }
    recent.forEach(function (item) {
      var row = document.createElement('tr');
      [formatDate(item.created_at), item.predicted_crop || '\u2014', (Number(item.confidence) || 0).toFixed(1) + '%'].forEach(function (value) {
        var cell = document.createElement('td');
        cell.textContent = value;
        row.appendChild(cell);
      });
      var status = document.createElement('td');
      var badge = document.createElement('span');
      badge.className = 'badge badge--success';
      badge.textContent = 'Complete';
      status.appendChild(badge);
      row.appendChild(status);
      body.appendChild(row);
    });
  }

  function modelInfo(model) {
    setText('[data-model-algorithm]', (model && model.algorithm) || 'Unavailable');
    setText('[data-model-version]', (model && model.version) || '\u2014');
    setText('[data-model-training]', model && model.training_date ? formatDate(model.training_date) : '\u2014');
    setText('[data-model-dataset]', (model && model.dataset_name) || '\u2014');
    setText('[data-model-features]', model && model.feature_count != null ? model.feature_count : '\u2014');
  }

  function showPartialDataAlert() {
    var alert = document.querySelector('[data-dashboard-alert]');
    if (!alert) return;
    alert.textContent = 'Some dashboard information is temporarily unavailable. Showing the data that could be loaded.';
    alert.classList.remove('hidden');
  }

  function load() {
    charts.forEach(function (chart) { chart.destroy(); });
    charts = [];
    var alert = document.querySelector('[data-dashboard-alert]');
    if (alert) alert.classList.add('hidden');

    return Promise.allSettled([
      fetchJson('/api/dashboard'), fetchJson('/api/statistics'), fetchJson('/api/model'), fetchJson('/health')
    ]).then(function (results) {
      var dashboard = results[0].status === 'fulfilled' ? results[0].value.data : null;
      var statistics = results[1].status === 'fulfilled' ? results[1].value.data : null;
      var model = results[2].status === 'fulfilled' ? results[2].value.data : null;
      var health = results[3].status === 'fulfilled' ? results[3].value : null;
      var failed = results.some(function (result) { return result.status === 'rejected'; });

      setStatus('[data-status-backend]', Boolean(health && health.application_status === 'running'));
      setStatus('[data-status-database]', Boolean(health && health.database_status === 'available'));
      setStatus('[data-status-model]', Boolean(health && health.model_status === 'loaded'));
      setStatus('[data-status-api]', !failed);
      if (failed) showPartialDataAlert();

      var safeDashboard = dashboard || { total_predictions: 0, predictions_today: 0, most_predicted_crop: null, recent_predictions: [] };
      var recent = Array.isArray(safeDashboard.recent_predictions) ? safeDashboard.recent_predictions : [];
      setKpis(safeDashboard, model);
      renderDistribution(statistics || {});
      renderTrend(recent);
      renderConfidence(recent);
      recentTable(recent);
      modelInfo(model);
      if (!window.Chart) showPartialDataAlert();
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var refresh = document.querySelector('[data-dashboard-refresh]');
    if (refresh) refresh.addEventListener('click', function () { load(); });
    load().catch(function () {
      var alert = document.querySelector('[data-dashboard-alert]');
      if (!alert) return;
      alert.textContent = 'The dashboard could not be loaded. Check your connection and refresh the page.';
      alert.classList.remove('hidden');
    });
  });
}());
