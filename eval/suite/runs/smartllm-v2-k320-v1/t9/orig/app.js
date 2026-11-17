(function () {
  'use strict';

  const platformData = {
    x4: {
      name: 'AETHER-X4 Multispectral',
      powerDrawW: 28,
      sensor: '12-band multispectral',
      link: '2.4 GHz telemetry',
      ip: 'IP67',
      payload: '2.4 kg'
    },
    h8: {
      name: 'AETHER-H8 Heavy Lidar',
      powerDrawW: 58,
      sensor: '128-channel lidar',
      link: '2.4 GHz telemetry',
      ip: 'IP67',
      payload: '6.2 kg'
    },
    s2: {
      name: 'AETHER-S2 Soil Probe',
      powerDrawW: 24,
      sensor: 'Soil probe array',
      link: '2.4 GHz telemetry',
      ip: 'IP66',
      payload: '1.8 kg'
    }
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const formatNumber = (value) => Number(value).toLocaleString('en-US');

  const state = {
    filter: 'all'
  };

  const filterButtons = $$('[data-filter]');
  const platformCards = $$('[data-platform-card]');
  const tableRows = $$('[data-platform-row]');
  const form = $('#deployment-form');
  const formStatus = $('#form-status');

  const coverageForm = $('#coverage-form');
  const coverageStatus = $('#coverage-status');
  const outputFlightTime = $('#output-flight-time');
  const outputBatterySwaps = $('#output-battery-swaps');
  const outputWaypoints = $('#output-waypoints');
  const outputCoverageTime = $('#output-coverage-time');
  const outputAreaCovered = $('#output-area-covered');

  function setFilter(filter) {
    state.filter = filter;

    filterButtons.forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.filter === filter));
    });

    platformCards.forEach((card) => {
      const platform = card.dataset.platform;
      const visible = filter === 'all' || platform === filter;
      card.classList.toggle('is-hidden', !visible);
    });

    tableRows.forEach((row) => {
      const platform = row.dataset.platform;
      const visible = filter === 'all' || platform === filter;
      row.classList.toggle('is-hidden', !visible);
    });
  }

  filterButtons.forEach((button) => {
    button.addEventListener('click', () => setFilter(button.dataset.filter));
  });

  function formatDuration(seconds) {
    if (!Number.isFinite(seconds) || seconds <= 0) return '0 min';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor(seconds % 3600 / 60);
    if (hours > 0) return `${hours} h ${minutes} min`;
    return `${minutes} min`;
  }

  function calculateCoverage() {
    const fieldAreaHa = Number($('#field-area').value);
    const swathWidth = Number($('#swath-width').value);
    const cruiseSpeed = Number($('#cruise-speed').value);
    const batteryWh = Number($('#battery-capacity').value);
    const selectedPlatform = $('#platform-select').value;
    const platform = platformData[selectedPlatform] || platformData.x4;

    const valid =
      fieldAreaHa > 0 &&
      swathWidth > 0 &&
      cruiseSpeed > 0 &&
      batteryWh > 0;

    if (!valid) {
      coverageStatus.textContent = 'Enter positive values for field area, swath width, cruise speed, and battery capacity.';
      return;
    }

    coverageStatus.textContent = 'Telemetry estimate updated.';

    const fieldAreaM2 = fieldAreaHa * 10000;
    const coverageSeconds = fieldAreaM2 / (swathWidth * cruiseSpeed);
    const flightSeconds = batteryWh / platform.powerDrawW * 3600;
    const requiredBatteries = Math.max(1, Math.ceil(coverageSeconds / flightSeconds));
    const batterySwaps = requiredBatteries > 1 ? requiredBatteries - 1 : 0;
    const waypoints = Math.max(1, Math.ceil(coverageSeconds / flightSeconds));

    outputAreaCovered.textContent = `${formatNumber(fieldAreaHa)} ha`;
    outputCoverageTime.textContent = formatDuration(coverageSeconds);
    outputFlightTime.textContent = formatDuration(flightSeconds);
    outputBatterySwaps.textContent = String(batterySwaps);
    outputWaypoints.textContent = String(waypoints);
  }

  if (coverageForm) {
    coverageForm.addEventListener('submit', (event) => {
      event.preventDefault();
      calculateCoverage();
    });

    coverageForm.addEventListener('input', () => {
      calculateCoverage();
    });
  }

  if (form) {
    form.addEventListener('submit', (event) => {
      event.preventDefault();

      const errors = [];
      const name = $('#contact-name').value.trim();
      const email = $('#contact-email').value.trim();
      const organization = $('#contact-org').value.trim();
      const message = $('#contact-message').value.trim();

      if (name.length < 2) errors.push('Enter a valid contact name.');
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.push('Enter a valid email address.');
      if (organization.length < 2) errors.push('Enter your organization.');
      if (message.length < 10) errors.push('Enter a deployment request with at least 10 characters.');

      if (errors.length > 0) {
        formStatus.textContent = `Validation issues: ${errors.join(' ')}`;
        return;
      }

      formStatus.textContent = 'Deployment inquiry validated. A fleet planning team will review the request.';
    });
  }
})();