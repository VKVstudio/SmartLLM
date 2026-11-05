/**
 * AETHERIA BIO-ROBOTICS — interactive mission planner, telemetry filter,
 * and fleet deployment inquiry validation.
 *
 * Standalone ES6 module.
 */

const AetheriaApp = (() => {
  "use strict";

  const PLATFORMS = [
    {
      id: "x4",
      name: "AETHER-X4 Multispectral",
      payload: "12-band multispectral + RTK gimbal",
      enduranceMin: 38,
      powerW: 180,
      cruiseSpeed: 14,
      swath: 112,
      ip: "IP67",
      accuracy: "±1.2 cm RTK",
      deployment: "Small-field crop scouting",
      dataLink: "2.4 GHz telemetry + 5.8 GHz video",
      coverageProfile: "RGB / NIR / RedEdge / Vegetation indices",
      status: "active",
    },
    {
      id: "h8",
      name: "AETHER-H8 Heavy Lidar",
      payload: "128-channel LiDAR + thermal payload",
      enduranceMin: 26,
      powerW: 320,
      cruiseSpeed: 11,
      swath: 180,
      ip: "IP68",
      accuracy: "±2.8 cm RTK",
      deployment: "Terrain mapping / biomass volume",
      dataLink: "2.4 GHz telemetry + encrypted uplink",
      coverageProfile: "LiDAR point cloud / thermal / canopy height",
      status: "active",
    },
    {
      id: "s2",
      name: "AETHER-S2 Soil Probe",
      payload: "Electrical conductivity + moisture probe",
      enduranceMin: 42,
      powerW: 150,
      cruiseSpeed: 9,
      swath: 72,
      ip: "IP66",
      accuracy: "±3.5 cm RTK",
      deployment: "Soil sampling / moisture mapping",
      dataLink: "2.4 GHz telemetry + local SD logging",
      coverageProfile: "Conductivity / moisture / compaction",
      status: "active",
    },
  ];

  const state = {
    filter: "all",
    platform: "x4",
    formErrors: {},
  };

  const selectors = {
    filterButtons: "[data-filter-button]",
    platformRows: "[data-platform-row]",
    telemetrySummary: "[data-telemetry-summary]",
    plannerForm: "[data-planner-form]",
    plannerOutputs: "[data-output]",
    inquiryForm: "[data-inquiry-form]",
    inquiryErrors: "[data-inquiry-errors]",
    inquiryStatus: "[data-inquiry-status]",
  };

  function clampNumber(value, min, max, fallback) {
    const n = Number(value);
    if (!Number.isFinite(n)) return fallback;
    return Math.min(max, Math.max(min, n));
  }

  function formatDuration(seconds) {
    if (!Number.isFinite(seconds) || seconds <= 0) return "0h 00m 00s";
    const total = Math.max(0, Math.floor(seconds));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    return `${h}h ${String(m).padStart(2, "0")}m ${String(s).padStart(2, "0")}s`;
  }

  function formatNumber(value, digits = 2) {
    if (!Number.isFinite(value)) return "0";
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: digits,
    }).format(value);
  }

  function calculateMission(inputs) {
    const fieldHa = clampNumber(inputs.fieldHa, 0.01, 100000, 0);
    const swathM = clampNumber(inputs.swathM, 1, 500, 0);
    const cruiseSpeed = clampNumber(inputs.cruiseSpeed, 1, 40, 0);
    const batteryWh = clampNumber(inputs.batteryWh, 1, 20000, 0);
    const powerW = clampNumber(inputs.powerW, 50, 800, 180);
    const overlapPct = clampNumber(inputs.overlapPct, 0, 60, 10);
    const headlandFactor = 1.12;
    const turnSecondsPerPass = 5;

    if (fieldHa <= 0 || swathM <= 0 || cruiseSpeed <= 0 || batteryWh <= 0) {
      return {
        valid: false,
        areaM2: 0,
        effectiveSwath: 0,
        pathLengthM: 0,
        missionTimeSec: 0,
        enduranceSec: 0,
        batterySwaps: 0,
        waypointCount: 0,
        coveragePasses: 0,
      };
    }

    const areaM2 = fieldHa * 10000;
    const effectiveSwath = swathM * (1 - overlapPct / 100);
    const pathLengthM = areaM2 / effectiveSwath;
    const squareSideM = Math.sqrt(areaM2);
    const coveragePasses = Math.max(1, Math.ceil(squareSideM / effectiveSwath));
    const waypointSpacingM = Math.max(50, effectiveSwath * 2);
    const waypointCount = Math.max(
      coveragePasses * 2,
      Math.ceil(pathLengthM / waypointSpacingM) + coveragePasses
    );

    const straightTimeSec = pathLengthM / cruiseSpeed;
    const maneuverTimeSec = coveragePasses * turnSecondsPerPass;
    const missionTimeSec = straightTimeSec * headlandFactor + maneuverTimeSec;

    const enduranceSec = (batteryWh / powerW) * 3600;
    const batterySwaps = enduranceSec > 0
      ? Math.max(1, Math.ceil(missionTimeSec / enduranceSec))
      : 1;

    return {
      valid: true,
      areaM2,
      effectiveSwath,
      pathLengthM,
      missionTimeSec,
      enduranceSec,
      batterySwaps,
      waypointCount,
      coveragePasses,
    };
  }

  function setOutput(name, value) {
    const el = document.querySelector(`${selectors.plannerOutputs}[data-output="${name}"]`);
    if (el) el.textContent = value;
  }

  function updatePlanner() {
    const form = document.querySelector(selectors.plannerForm);
    if (!form) return;

    const inputs = {
      fieldHa: form.elements["field-ha"]?.value,
      swathM: form.elements["swath-m"]?.value,
      cruiseSpeed: form.elements["cruise-speed"]?.value,
      batteryWh: form.elements["battery-wh"]?.value,
      powerW: form.elements["power-w"]?.value,
      overlapPct: form.elements["overlap-pct"]?.value,
    };

    const result = calculateMission(inputs);

    setOutput("area-m2", result.valid ? formatNumber(result.areaM2, 0) : "—");
    setOutput("effective-swath", result.valid ? formatNumber(result.effectiveSwath, 1) : "—");
    setOutput("path-length", result.valid ? formatNumber(result.pathLengthM, 1) : "—");
    setOutput("coverage-passes", result.valid ? formatNumber(result.coveragePasses, 0) : "—");
    setOutput("waypoint-count", result.valid ? formatNumber(result.waypointCount, 0) : "—");
    setOutput("mission-time", result.valid ? formatDuration(result.missionTimeSec) : "—");
    setOutput("endurance", result.valid ? formatDuration(result.enduranceSec) : "—");
    setOutput("battery-swaps", result.valid ? formatNumber(result.batterySwaps, 0) : "—");

    const status = document.querySelector("[data-planner-status]");
    if (status) {
      status.textContent = result.valid
        ? "Coverage model active. Inputs updated live."
        : "Enter positive values to generate a coverage model.";
    }
  }

  function filterPlatforms(filter) {
    state.filter = filter;

    const rows = document.querySelectorAll(selectors.platformRows);
    rows.forEach((row) => {
      const id = row.getAttribute("data-platform-row");
      const visible = filter === "all" || id === filter;
      row.hidden = !visible;
      row.setAttribute("aria-hidden", String(!visible));
    });

    const buttons = document.querySelectorAll(selectors.filterButtons);
    buttons.forEach((button) => {
      const isActive = button.getAttribute("data-filter-button") === filter;
      button.setAttribute("aria-pressed", String(isActive));
    });

    const summary = document.querySelector(selectors.telemetrySummary);
    if (summary) {
      const visible = filter === "all"
        ? "all platforms"
        : PLATFORMS.find((p) => p.id === filter)?.name || filter;
      summary.textContent = `Telemetry filter: ${visible}.`;
    }
  }

  function bindFilterButtons() {
    const buttons = document.querySelectorAll(selectors.filterButtons);
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        filterPlatforms(button.getAttribute("data-filter-button"));
      });
    });
  }

  function bindPlatformSelection() {
    const selects = document.querySelectorAll("[data-platform-select]");
    selects.forEach((select) => {
      select.addEventListener("change", () => {
        state.platform = select.value || "x4";
        const platform = PLATFORMS.find((p) => p.id === state.platform);
        if (!platform) return;

        const form = document.querySelector(selectors.plannerForm);
        if (!form) return;

        if (form.elements["swath-m"]) form.elements["swath-m"].value = platform.swath;
        if (form.elements["cruise-speed"]) form.elements["cruise-speed"].value = platform.cruiseSpeed;
        if (form.elements["power-w"]) form.elements["power-w"].value = platform.powerW;

        updatePlanner();
      });
    });
  }

  function isEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value.trim());
  }

  function validateInquiryForm(form) {
    const errors = {};
    const data = new FormData(form);

    const name = String(data.get("name") || "").trim();
    const email = String(data.get("email") || "").trim();
    const organization = String(data.get("organization") || "").trim();
    const fleet = String(data.get("fleet-size") || "").trim();
    const hectares = String(data.get("hectares") || "").trim();
    const message = String(data.get("message") || "").trim();
    const consent = form.elements["consent"]?.checked;

    if (!name) errors.name = "Required: operator or team name.";
    else if (name.length < 2) errors.name = "Name must be at least 2 characters.";

    if (!email) errors.email = "Required: contact email.";
    else if (!isEmail(email)) errors.email = "Enter a valid email address.";

    if (!organization) errors.organization = "Required: organization name.";
    else if (organization.length < 2) errors.organization = "Organization must be at least 2 characters.";

    const fleetNum = Number(fleet);
    if (!fleet) errors.fleet = "Required: requested fleet size.";
    else if (!Number.isInteger(fleetNum) || fleetNum < 1 || fleetNum > 50) {
      errors.fleet = "Fleet size must be an integer between 1 and 50.";
    }

    const hectaresNum = Number(hectares);
    if (!hectares) errors.hectares = "Required: approximate field hectares.";
    else if (!Number.isFinite(hectaresNum) || hectaresNum < 1 || hectaresNum > 100000) {
      errors.hectares = "Hectares must be between 1 and 100000.";
    }

    if (message.length > 1200) errors.message = "Message must be 1200 characters or fewer.";

    if (!consent) errors.consent = "Required: consent to deployment coordination.";

    state.formErrors = errors;
    return errors;
  }

  function renderInquiryErrors(errors) {
    const container = document.querySelector(selectors.inquiryErrors);
    const status = document.querySelector(selectors.inquiryStatus);

    if (!container) return;

    container.innerHTML = "";

    const entries = Object.entries(errors);
    if (entries.length === 0) {
      if (status) status.textContent = "Inquiry valid. Ready for secure fleet deployment coordination.";
      return;
    }

    entries.forEach(([field, message]) => {
      const p = document.createElement("p");
      p.className = "form-error";
      p.textContent = message;
      container.appendChild(p);

      const input = document.querySelector(`[data-field="${field}"]`);
      if (input) {
        input.setAttribute("aria-invalid", "true");
        input.classList.add("is-invalid");
      }
    });

    if (status) status.textContent = "Inquiry contains validation errors.";
  }

  function clearInquiryErrors() {
    const container = document.querySelector(selectors.inquiryErrors);
    const status = document.querySelector(selectors.inquiryStatus);

    if (container) container.innerHTML = "";

    document.querySelectorAll("[data-field]").forEach((input) => {
      input.removeAttribute("aria-invalid");
      input.classList.remove("is-invalid");
    });

    if (status) status.textContent = "";
  }

  function bindInquiryForm() {
    const form = document.querySelector(selectors.inquiryForm);
    if (!form) return;

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      clearInquiryErrors();

      const errors = validateInquiryForm(form);
      renderInquiryErrors(errors);

      if (Object.keys(errors).length === 0) {
        const status = document.querySelector(selectors.inquiryStatus);
        if (status) {
          status.textContent = "Inquiry submitted locally. A fleet deployment coordinator will route this to mission operations.";
        }
        form.reset();
      }
    });

    form.addEventListener("input", () => {
      clearInquiryErrors();
    });
  }

  function initPlanner() {
    const form = document.querySelector(selectors.plannerForm);
    if (!form) return;

    form.addEventListener("input", updatePlanner);
    form.addEventListener("change", updatePlanner);

    const platformSelect = document.querySelector("[data-platform-select]");
    if (platformSelect && PLATFORMS.length > 0) {
      platformSelect.value = state.platform;
      platformSelect.dispatchEvent(new Event("change"));
    }

    updatePlanner();
  }

  function init() {
    bindFilterButtons();
    bindPlatformSelection();
    initPlanner();
    bindInquiryForm();

    filterPlatforms(state.filter);

    document.querySelectorAll("[data-platform-card]").forEach((card) => {
      const id = card.getAttribute("data-platform-card");
      const platform = PLATFORMS.find((p) => p.id === id);
      if (!platform) return;

      const nameEl = card.querySelector("[data-platform-name]");
      const payloadEl = card.querySelector("[data-platform-payload]");
      const enduranceEl = card.querySelector("[data-platform-endurance]");
      const powerEl = card.querySelector("[data-platform-power]");

      if (nameEl) nameEl.textContent = platform.name;
      if (payloadEl) payloadEl.textContent = platform.payload;
      if (enduranceEl) enduranceEl.textContent = `${platform.enduranceMin} min`;
      if (powerEl) powerEl.textContent = `${platform.powerW} W`;
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }

  return {
    init,
    calculateMission,
    filterPlatforms,
    PLATFORMS,
  };
})();

window.AetheriaApp = AetheriaApp;

export default AetheriaApp;
export { AetheriaApp, calculateMission, filterPlatforms };