const history = [];
const maxHistory = 40;

const els = {
  statusDot: document.querySelector("#statusDot"),
  stateLabel: document.querySelector("#stateLabel"),
  updatedLabel: document.querySelector("#updatedLabel"),
  deviceMeta: document.querySelector("#deviceMeta"),
  refreshButton: document.querySelector("#refreshButton"),
  chargeStatus: document.querySelector("#chargeStatus"),
  errorStatus: document.querySelector("#errorStatus"),
  currentGauge: document.querySelector("#currentGauge"),
  voltageGauge: document.querySelector("#voltageGauge"),
  tempGauge: document.querySelector("#tempGauge"),
  currentValue: document.querySelector("#currentValue"),
  voltageValue: document.querySelector("#voltageValue"),
  tempValue: document.querySelector("#tempValue"),
  currentUnit: document.querySelector("#currentUnit"),
  voltageUnit: document.querySelector("#voltageUnit"),
  tempUnit: document.querySelector("#tempUnit"),
  powerValue: document.querySelector("#powerValue"),
  energyValue: document.querySelector("#energyValue"),
  maxCurrentValue: document.querySelector("#maxCurrentValue"),
  powerBar: document.querySelector("#powerBar"),
  energyBar: document.querySelector("#energyBar"),
  maxCurrentBar: document.querySelector("#maxCurrentBar"),
  settingsStatus: document.querySelector("#settingsStatus"),
  maxCurrentForm: document.querySelector("#maxCurrentForm"),
  maxCurrentRange: document.querySelector("#maxCurrentRange"),
  maxCurrentInput: document.querySelector("#maxCurrentInput"),
  saveCurrentButton: document.querySelector("#saveCurrentButton"),
  serialValue: document.querySelector("#serialValue"),
  firmwareValue: document.querySelector("#firmwareValue"),
  probeValue: document.querySelector("#probeValue"),
  sampleCount: document.querySelector("#sampleCount"),
  canvas: document.querySelector("#trendCanvas"),
};

function number(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function fixed(value, digits = 1) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "--";
  if (Math.abs(parsed) >= 100 || Number.isInteger(parsed)) return String(Math.round(parsed));
  return parsed.toFixed(digits);
}

function pct(value, max) {
  return `${Math.max(0, Math.min(100, (number(value) / max) * 100))}%`;
}

function setGauge(el, value, max) {
  el.style.setProperty("--pct", pct(value, max));
}

function updateBars(data) {
  els.powerBar.style.width = pct(data.power_active_import, 7400);
  els.energyBar.style.width = pct(data.energy_active_import_interval, 12);
  els.maxCurrentBar.style.width = pct(data.config_maxWorkCurrent, 32);
}

function setSettingsStatus(text, kind = "") {
  els.settingsStatus.textContent = text;
  els.settingsStatus.className = kind;
}

function clampCurrent(value) {
  const parsed = Math.round(number(value, 16));
  return Math.max(6, Math.min(32, parsed));
}

function syncCurrentInputs(value) {
  const current = clampCurrent(value);
  els.maxCurrentRange.value = current;
  els.maxCurrentInput.value = current;
}

function updateHistory(data) {
  if (data.voltage === undefined && data.current_import === undefined && data.temperature === undefined) {
    return;
  }
  history.push({
    time: Date.now(),
    voltage: number(data.voltage, null),
    current: number(data.current_import, null),
    temp: number(data.temperature, null),
  });
  while (history.length > maxHistory) history.shift();
}

function scale(value, min, max, height, pad) {
  if (value === null || value === undefined || !Number.isFinite(value)) return null;
  return pad + (1 - (value - min) / (max - min)) * (height - pad * 2);
}

function drawLine(ctx, points, color, min, max, key, width, height, pad) {
  ctx.beginPath();
  ctx.lineWidth = 3;
  ctx.strokeStyle = color;
  let started = false;
  points.forEach((point, index) => {
    const x = pad + (index / Math.max(1, points.length - 1)) * (width - pad * 2);
    const y = scale(point[key], min, max, height, pad);
    if (y === null) return;
    if (!started) {
      ctx.moveTo(x, y);
      started = true;
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();
}

function drawChart() {
  const canvas = els.canvas;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(rect.width * ratio);
  canvas.height = Math.round(rect.height * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);

  const width = rect.width;
  const height = rect.height;
  const pad = 34;
  ctx.clearRect(0, 0, width, height);

  ctx.strokeStyle = "rgba(20,32,30,0.10)";
  ctx.lineWidth = 1;
  for (let i = 0; i < 5; i += 1) {
    const y = pad + (i / 4) * (height - pad * 2);
    ctx.beginPath();
    ctx.moveTo(pad, y);
    ctx.lineTo(width - pad, y);
    ctx.stroke();
  }

  drawLine(ctx, history, "#168187", 200, 260, "voltage", width, height, pad);
  drawLine(ctx, history, "#1d8f64", 0, 32, "current", width, height, pad);
  drawLine(ctx, history, "#d68a1f", 0, 90, "temp", width, height, pad);

  ctx.fillStyle = "#65716e";
  ctx.font = "12px Avenir Next, Segoe UI, Verdana, sans-serif";
  ctx.fillText("Voltage", pad, 18);
  ctx.fillStyle = "#1d8f64";
  ctx.fillText("Current", pad + 72, 18);
  ctx.fillStyle = "#d68a1f";
  ctx.fillText("Temp", pad + 142, 18);
  els.sampleCount.textContent = `${history.length} samples`;
}

function updateUi(payload) {
  const data = payload.data || {};
  const online = payload.ok && Object.keys(data).length > 0;
  const age = payload.age ?? (payload.updated_at ? Math.max(0, Math.round(Date.now() / 1000 - payload.updated_at)) : null);
  els.statusDot.className = `dot ${online ? "online" : "offline"}`;
  els.stateLabel.textContent = online ? "Online" : "No data";
  els.updatedLabel.textContent = age === null ? "No update yet" : `Updated ${age}s ago`;

  els.deviceMeta.textContent = data.chargePointModel
    ? `${data.chargePointModel} - ${data.chargePointVendor || "Unknown vendor"}`
    : payload.error || "Waiting for charger data";

  els.chargeStatus.textContent = data.status_status || "Unknown";
  els.errorStatus.textContent = data.status_errorCode || payload.error || "No error data";

  els.currentValue.textContent = fixed(data.current_import);
  els.voltageValue.textContent = fixed(data.voltage);
  els.tempValue.textContent = fixed(data.temperature);
  els.currentUnit.textContent = data.current_import_unit || "A";
  els.voltageUnit.textContent = data.voltage_unit || "V";
  els.tempUnit.textContent = data.temperature_unit || "C";

  setGauge(els.currentGauge, data.current_import, data.config_maxWorkCurrent || 32);
  setGauge(els.voltageGauge, Math.abs(number(data.voltage) - 200), 80);
  setGauge(els.tempGauge, data.temperature, data.config_maxWorkTemp || 90);

  els.powerValue.textContent = `${fixed(data.power_active_import)} ${data.power_active_import_unit || "W"}`;
  els.energyValue.textContent = `${fixed(data.energy_active_import_interval, 2)} ${data.energy_active_import_interval_unit || "kWh"}`;
  els.maxCurrentValue.textContent = `${fixed(data.config_maxWorkCurrent)} A`;
  if (data.config_maxWorkCurrent !== undefined && document.activeElement !== els.maxCurrentInput) {
    syncCurrentInputs(data.config_maxWorkCurrent);
  }
  updateBars(data);

  els.serialValue.textContent = data.chargePointSerialNumber || "--";
  els.firmwareValue.textContent = data.firmwareVersion || "--";
  els.probeValue.textContent = payload.duration ? `${payload.duration}s` : "--";
  if (payload.last_command?.type === "set_max_current") {
    setSettingsStatus(`Utolsó mentés: ${fixed(payload.last_command.value)} A (${payload.last_command.status})`, "ok");
  } else if (!payload.ok && payload.error) {
    setSettingsStatus(payload.error, "error");
  }

  updateHistory(data);
  drawChart();
}

async function loadState() {
  const response = await fetch("/api/state", { cache: "no-store" });
  updateUi(await response.json());
}

async function refreshNow() {
  els.refreshButton.disabled = true;
  try {
    await fetch("/api/refresh", { cache: "no-store" });
    setTimeout(loadState, 1200);
  } finally {
    setTimeout(() => {
      els.refreshButton.disabled = false;
    }, 3000);
  }
}

async function saveMaxCurrent(event) {
  event.preventDefault();
  const value = clampCurrent(els.maxCurrentInput.value);
  syncCurrentInputs(value);
  els.saveCurrentButton.disabled = true;
  setSettingsStatus("Mentés folyamatban...", "busy");
  try {
    const response = await fetch("/api/config/max-current", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify({ value }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    setSettingsStatus(`Mentve: ${value} A`, "ok");
    updateUi(payload.state);
  } catch (error) {
    setSettingsStatus(error.message || String(error), "error");
  } finally {
    els.saveCurrentButton.disabled = false;
  }
}

els.refreshButton.addEventListener("click", refreshNow);
els.maxCurrentRange.addEventListener("input", () => syncCurrentInputs(els.maxCurrentRange.value));
els.maxCurrentInput.addEventListener("input", () => syncCurrentInputs(els.maxCurrentInput.value));
els.maxCurrentForm.addEventListener("submit", saveMaxCurrent);
window.addEventListener("resize", drawChart);

loadState();
setInterval(loadState, 5000);
