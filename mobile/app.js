const API = "";
const CACHE_CONFIG_KEY = "mydrive_config_v1";
const CACHE_TRIPS_KEY = "mydrive_trips_v1";
const PASSENGER_ROUTE_IDS = ["fastest", "calm", "safest"];

let map = null;
let routeLayers = [];
let lastRouteData = null;

const state = {
  mode: "full",
  origin: null,
  destination: null,
  fromLabel: "",
  toLabel: "",
  selectedId: "fastest",
  fromResolvedQuery: "",
  toResolvedQuery: "",
};

const $ = (id) => document.getElementById(id);

function setStatus(msg, isError = false) {
  const el = $("status");
  if (!el) return;
  el.textContent = msg;
  el.style.color = isError ? "#f87171" : "";
}

function setOfflineBadge(show) {
  $("offline-badge").classList.toggle("hidden", !show);
}

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

async function geocode(query, coords = null) {
  const body = { query };
  if (coords) {
    body.lat = coords.lat;
    body.lon = coords.lon;
  }
  return api("/api/geocode", { method: "POST", body: JSON.stringify(body) });
}

async function fetchPlaceSuggestions(query) {
  if (query.trim().length < 2) return [];
  const data = await api(`/api/places/autocomplete?q=${encodeURIComponent(query.trim())}`);
  return data.suggestions || [];
}

function escapeHtml(text) {
  const el = document.createElement("div");
  el.textContent = text;
  return el.innerHTML;
}

function debounce(fn, delayMs) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delayMs);
  };
}

function attachPlaceAutocomplete(inputId, listId, which) {
  const input = $(inputId);
  const list = $(listId);
  if (!input || !list) return;

  const hide = () => {
    list.classList.add("hidden");
    list.innerHTML = "";
    input.setAttribute("aria-expanded", "false");
  };

  const pick = (suggestion) => {
    input.value = suggestion.label;
    const point = { lat: suggestion.lat, lon: suggestion.lon };
    if (which === "from") {
      state.origin = point;
      state.fromLabel = suggestion.label;
      state.fromResolvedQuery = suggestion.label;
    } else {
      state.destination = point;
      state.toLabel = suggestion.label;
      state.toResolvedQuery = suggestion.label;
    }
    hide();
  };

  const renderList = (suggestions) => {
    list.innerHTML = "";
    if (!suggestions.length) {
      hide();
      return;
    }
    suggestions.forEach((s) => {
      const li = document.createElement("li");
      li.className = "ac-item";
      li.setAttribute("role", "option");
      const badge = s.source === "local" ? "Popular" : "Place";
      li.innerHTML = `
        <div class="ac-row">
          <strong>${escapeHtml(s.label)}</strong>
          <span class="ac-badge">${badge}</span>
        </div>
        <span class="ac-sub">${escapeHtml(s.subtitle)}</span>
      `;
      li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        pick(s);
      });
      list.appendChild(li);
    });
    list.classList.remove("hidden");
    input.setAttribute("aria-expanded", "true");
  };

  const runSearch = debounce(async () => {
    const q = input.value.trim();
    if (q.length < 2) {
      hide();
      return;
    }
    try {
      const suggestions = await fetchPlaceSuggestions(q);
      renderList(suggestions);
    } catch {
      hide();
    }
  }, 280);

  input.addEventListener("input", () => {
    if (which === "from") {
      state.origin = null;
      state.fromResolvedQuery = "";
    } else {
      state.destination = null;
      state.toResolvedQuery = "";
    }
    runSearch();
  });

  input.addEventListener("focus", () => {
    if (input.value.trim().length >= 2) runSearch();
  });

  input.addEventListener("blur", () => {
    setTimeout(hide, 160);
  });

  input.addEventListener("keydown", (e) => {
    const items = list.querySelectorAll(".ac-item");
    if (!items.length || list.classList.contains("hidden")) return;
    if (e.key === "Escape") {
      hide();
      return;
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const dir = e.key === "ArrowDown" ? 1 : -1;
      let idx = Array.from(items).findIndex((el) => el.classList.contains("active"));
      idx = (idx + dir + items.length) % items.length;
      items.forEach((el, i) => el.classList.toggle("active", i === idx));
      return;
    }
    if (e.key === "Enter") {
      const active = list.querySelector(".ac-item.active");
      if (active) {
        e.preventDefault();
        active.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      }
    }
  });
}

function cacheConfig(config) {
  try {
    localStorage.setItem(CACHE_CONFIG_KEY, JSON.stringify(config));
  } catch (_) {}
}

function loadCachedConfig() {
  try {
    const raw = localStorage.getItem(CACHE_CONFIG_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

function cacheTripResult(presetId, payload) {
  try {
    const trips = JSON.parse(localStorage.getItem(CACHE_TRIPS_KEY) || "{}");
    trips[presetId] = { savedAt: Date.now(), payload };
    localStorage.setItem(CACHE_TRIPS_KEY, JSON.stringify(trips));
  } catch (_) {}
}

function renderPresets(config) {
  const container = $("presets");
  container.innerHTML = "";
  config.presets.forEach((p) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "preset-btn";
    btn.textContent = p.label;
    btn.addEventListener("click", () => {
      $("from-input").value = p.from_address;
      $("to-input").value = p.to_address;
      state.origin = { lat: p.from_lat, lon: p.from_lon };
      state.destination = { lat: p.to_lat, lon: p.to_lon };
      state.fromLabel = p.from_label;
      state.toLabel = p.to_label;
      compareRoutes(p.id);
    });
    container.appendChild(btn);
  });
}

function applyBrand(config) {
  const brand = config.brand;
  if (!brand) return;
  document.title = brand.name;
  const nameEl = $("brand-name");
  const tagEl = $("brand-tagline");
  const footEl = $("brand-footer");
  if (nameEl) nameEl.textContent = brand.name;
  if (tagEl) tagEl.textContent = brand.tagline;
  if (footEl) {
    footEl.textContent = `Plan in ${brand.name} · navigate in Apple or Google Maps`;
  }
}

async function loadPresets() {
  try {
    const config = await api("/api/config");
    cacheConfig(config);
    applyBrand(config);
    setOfflineBadge(false);
    renderPresets(config);
  } catch (e) {
    const cached = loadCachedConfig();
    if (cached) {
      applyBrand(cached);
      setOfflineBadge(true);
      renderPresets(cached);
      setStatus("Using offline popular trips.");
    } else {
      throw e;
    }
  }
}

async function loadTrafficNote() {
  try {
    const t = await api("/api/traffic/status");
    $("traffic-note").textContent = t.message;
  } catch (_) {
    $("traffic-note").textContent = "";
  }
}

/* ——— Voice (Web Speech API) ——— */
function speechSupported() {
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}

function listenIntoInput(inputId) {
  if (!speechSupported()) {
    setStatus("Voice not supported in this browser. Use Chrome/Safari.", true);
    return;
  }
  const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
  const rec = new Rec();
  rec.lang = "en-US";
  rec.interimResults = false;
  rec.maxAlternatives = 1;
  setStatus("Listening… (parked only)");
  rec.onresult = (ev) => {
    const text = ev.results[0][0].transcript;
    $(inputId).value = text;
    setStatus(`Heard: "${text}"`);
  };
  rec.onerror = () => setStatus("Could not hear you — try again.", true);
  rec.onend = () => {};
  rec.start();
}

/* ——— Map ——— */
function initMap() {
  if (map) return;
  map = L.map("map", { zoomControl: false }).setView([41.8781, -87.6298], 10);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap",
    maxZoom: 19,
  }).addTo(map);
}

const ROUTE_COLORS = {
  fastest: "#4f8cff",
  calm: "#a78bfa",
  safest: "#fb923c",
  cheapest: "#34d399",
  reliable: "#22d3ee",
  balanced: "#2dd4bf",
  parking: "#f472b6",
  your_pick: "#94a3b8",
};

const ROUTE_EMOJI = {
  fastest: "⚡",
  calm: "😌",
  safest: "🛡️",
  cheapest: "💵",
  reliable: "📊",
  balanced: "⚖️",
  parking: "🅿️",
  your_pick: "✨",
};

function drawRoutes(data) {
  initMap();
  routeLayers.forEach((l) => map.removeLayer(l));
  routeLayers = [];

  const bounds = [];
  const origin = [data.origin.lat, data.origin.lon];
  const dest = [data.destination.lat, data.destination.lon];
  bounds.push(origin, dest);

  L.marker(origin).addTo(map).bindPopup("Start");
  L.marker(dest).addTo(map).bindPopup("End");

  const routes = filterRoutesForMode(data.routes);
  routes.forEach((route) => {
    if (!route.polyline?.length) return;
    const isSelected = route.id === state.selectedId;
    const line = L.polyline(route.polyline, {
      color: ROUTE_COLORS[route.id] || "#2f6fed",
      weight: isSelected ? 7 : 4,
      opacity: isSelected ? 1 : 0.45,
    }).addTo(map);
    routeLayers.push(line);
    route.polyline.forEach((pt) => bounds.push(pt));
  });

  map.fitBounds(bounds, { padding: [24, 24] });
}

function filterRoutesForMode(routes) {
  if (state.mode === "passenger") {
    return routes.filter((r) => PASSENGER_ROUTE_IDS.includes(r.id));
  }
  return routes;
}

function openMaps(route, provider) {
  const url = provider === "apple" ? route.maps.apple : route.maps.google;
  window.location.href = url;
}

const NAV_SESSION_KEY = "mydrive_nav_trip_v1";

function mapsButtonsHtml(route) {
  return `
    <div class="maps-row maps-row-3">
      <button type="button" class="btn maps navigate" data-action="navigate">Navigate</button>
      <button type="button" class="btn maps google" data-provider="google">Google</button>
      <button type="button" class="btn maps apple" data-provider="apple">Apple</button>
    </div>
  `;
}

function startInAppNavigation(data, route) {
  const trip = {
    title: `${state.fromLabel || "Start"} → ${state.toLabel || "End"}`,
    origin: data.origin,
    destination: data.destination,
    routeLabel: route.label,
    polyline: route.polyline || null,
  };
  try {
    sessionStorage.setItem(NAV_SESSION_KEY, JSON.stringify(trip));
  } catch (_) {}
  window.location.href = "/mobile/nav.html";
}

function bindMapsButtons(card, route, data) {
  card.querySelectorAll(".btn.maps").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (btn.dataset.action === "navigate") {
        startInAppNavigation(data, route);
        return;
      }
      openMaps(route, btn.dataset.provider);
    });
  });
}

/* ——— Passenger mode cards ——— */
function renderPassengerCards(data) {
  const container = $("passenger-cards");
  container.innerHTML = "";
  const labels = {
    fastest: { emoji: "⚡", title: "Fastest", sub: "Quickest arrival" },
    calm: { emoji: "😌", title: "Calmest", sub: "Easier drive, fewer highways" },
    safest: { emoji: "🛡️", title: "Safest", sub: "Lower predicted risk" },
  };

  filterRoutesForMode(data.routes).forEach((route) => {
    const meta = labels[route.id] || { emoji: "🚗", title: route.label, sub: route.tagline };
    const card = document.createElement("button");
    card.type = "button";
    card.className = `passenger-card${route.id === state.selectedId ? " selected" : ""}`;
    card.dataset.route = route.id;
    card.innerHTML = `
      <span class="passenger-emoji">${meta.emoji}</span>
      <span class="passenger-title">${meta.title}</span>
      <span class="passenger-time">${route.time_display} · ${route.tolls_display}</span>
      <span class="passenger-sub">${meta.sub}</span>
      ${mapsButtonsHtml(route)}
    `;
    card.addEventListener("click", (e) => {
      if (e.target.closest(".btn.maps")) return;
      state.selectedId = route.id;
      renderResults(data);
    });
    bindMapsButtons(card, route, data);
    container.appendChild(card);
  });
}

/* ——— Full mode cards ——— */
function renderFullCards(data) {
  const container = $("route-cards");
  container.innerHTML = "";

  data.routes.forEach((route) => {
    const card = document.createElement("article");
    card.className = `route-card${route.id === state.selectedId ? " selected" : ""}`;
    card.dataset.route = route.id;

    const emoji = ROUTE_EMOJI[route.id] || "🚗";
    const riskSummary = data?.risk?.summary ? `<p class="traffic-note">${escapeHtml(data.risk.summary)}</p>` : "";
    card.innerHTML = `
      <div class="route-card-head">
        <span class="route-emoji" aria-hidden="true">${emoji}</span>
        <div>
          <h3>${route.label}</h3>
          <p class="tagline">${route.tagline}</p>
        </div>
      </div>
      <div class="stats">
        <div class="stat"><label>Time</label><strong>${route.time_display}</strong></div>
        <div class="stat"><label>Tolls</label><strong>${route.tolls_display}</strong></div>
        <div class="stat"><label>Safety</label><strong>${route.safety}</strong></div>
        <div class="stat"><label>Feel</label><strong>${route.feel}</strong></div>
      </div>
      ${riskSummary}
      <p class="vs-fastest">${route.vs_fastest}</p>
      <button type="button" class="info-toggle" aria-expanded="false">ℹ️ What does this mean?</button>
      <div class="info-body">
        <p>${route.detail}</p>
        <p><em>Best when:</em> ${route.pick_when}</p>
      </div>
      ${mapsButtonsHtml(route)}
    `;

    card.querySelector(".info-toggle").addEventListener("click", (e) => {
      e.stopPropagation();
      const body = card.querySelector(".info-body");
      const open = body.classList.toggle("open");
      e.target.setAttribute("aria-expanded", open);
      e.target.textContent = open ? "ℹ️ Hide details" : "ℹ️ What does this mean?";
    });

    card.addEventListener("click", (e) => {
      if (e.target.closest(".info-toggle") || e.target.closest(".btn.maps")) return;
      state.selectedId = route.id;
      renderResults(data);
    });

    bindMapsButtons(card, route, data);
    container.appendChild(card);
  });
}

function renderResults(data) {
  lastRouteData = data;
  const routes = filterRoutesForMode(data.routes);
  if (!routes.find((r) => r.id === state.selectedId)) {
    state.selectedId = routes[0]?.id || "fastest";
  }

  drawRoutes(data);

  const isPassenger = state.mode === "passenger";
  $("passenger-results").classList.toggle("hidden", !isPassenger);
  $("full-results").classList.toggle("hidden", isPassenger);
  $("map").classList.toggle("map-compact", isPassenger);

  if (isPassenger) {
    renderPassengerCards(data);
  } else {
    renderFullCards(data);
  }
}

function setMode(mode) {
  state.mode = mode;
  $("mode-full").classList.toggle("active", mode === "full");
  $("mode-passenger").classList.toggle("active", mode === "passenger");
  $("mode-full").setAttribute("aria-selected", mode === "full");
  $("mode-passenger").setAttribute("aria-selected", mode === "passenger");
  $("priority-field").classList.toggle("hidden", mode === "passenger");
  $("safety-text").textContent =
    mode === "passenger"
      ? "Passenger picks Fastest, Calmest, or Safest — then opens Maps. Driver does not touch the phone."
      : "Set your trip before driving. Compare all route types, then open Maps.";
  document.body.classList.toggle("passenger-mode", mode === "passenger");
  if (lastRouteData) renderResults(lastRouteData);
}

async function compareRoutes(presetId = null) {
  const btn = $("compare-btn");
  btn.disabled = true;
  setStatus("Finding routes…");

  try {
    if (!state.origin || !state.destination) {
      const fromQ = $("from-input").value.trim();
      const toQ = $("to-input").value.trim();
      if (!fromQ || !toQ) throw new Error("Enter From and To, or pick a popular trip.");
      setStatus("Looking up addresses…");
      if (!state.origin) {
        state.origin = await geocode(fromQ);
        state.fromLabel = fromQ;
      }
      if (!state.destination) {
        state.destination = await geocode(toQ);
        state.toLabel = toQ;
      }
    }

    const priority = state.mode === "passenger" ? "balanced" : $("priority").value;
    const departAt = $("depart-at")?.value || null;
    const parseOpt = (id) => {
      const raw = $(id)?.value?.trim();
      if (!raw) return null;
      const n = Number(raw);
      return Number.isFinite(n) ? n : null;
    };
    const precipitation = parseOpt("w-precip");
    const visibility = parseOpt("w-vis");
    const wind_speed = parseOpt("w-wind");
    const traffic_volume = parseOpt("w-traffic");
    let data;
    try {
      data = await api("/api/routes/compare", {
        method: "POST",
        body: JSON.stringify({
          origin_lat: state.origin.lat,
          origin_lon: state.origin.lon,
          dest_lat: state.destination.lat,
          dest_lon: state.destination.lon,
          buffer_km: 2,
          priority,
          depart_at_iso: departAt ? new Date(departAt).toISOString() : null,
          precipitation,
          visibility,
          wind_speed,
          traffic_volume,
        }),
      });
      if (presetId) cacheTripResult(presetId, data);
      setOfflineBadge(false);
    } catch (netErr) {
      if (presetId) {
        const trips = JSON.parse(localStorage.getItem(CACHE_TRIPS_KEY) || "{}");
        if (trips[presetId]?.payload) {
          data = trips[presetId].payload;
          setOfflineBadge(true);
          setStatus("Offline — showing last saved route for this trip.");
        } else throw netErr;
      } else throw netErr;
    }

    $("results").classList.remove("hidden");
    $("setup-panel").classList.add("collapsed");
    $("trip-title").textContent = `${state.fromLabel || "Start"} → ${state.toLabel || "End"}`;
    if ($("risk-note") && data?.risk?.summary) {
      $("risk-note").textContent = data.risk.summary;
    }

    if (!data.complete) {
      setStatus("Route may be incomplete — check addresses.", true);
    } else {
      setStatus("");
    }

    if (state.mode === "passenger") state.selectedId = "fastest";
    renderResults(data);
    loadTrafficNote();

    state.origin = null;
    state.destination = null;
  } catch (err) {
    setStatus(err.message || "Something went wrong", true);
  } finally {
    btn.disabled = false;
  }
}

/* ——— Events ——— */
$("compare-btn").addEventListener("click", () => {
  state.origin = null;
  state.destination = null;
  compareRoutes();
});

$("change-trip").addEventListener("click", () => {
  $("results").classList.add("hidden");
  $("setup-panel").classList.remove("collapsed");
  lastRouteData = null;
});

$("mode-full").addEventListener("click", () => setMode("full"));
$("mode-passenger").addEventListener("click", () => setMode("passenger"));

$("voice-from").addEventListener("click", () => listenIntoInput("from-input"));
$("voice-to").addEventListener("click", () => listenIntoInput("to-input"));

if (!speechSupported()) {
  $("voice-from").disabled = true;
  $("voice-to").disabled = true;
}

attachPlaceAutocomplete("from-input", "from-ac", "from");
attachPlaceAutocomplete("to-input", "to-ac", "to");

loadPresets().catch((e) => setStatus(e.message, true));

// Set default departure datetime-local to "now"
(() => {
  const el = $("depart-at");
  if (!el) return;
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const local = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(
    now.getHours()
  )}:${pad(now.getMinutes())}`;
  el.value = local;
})();

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/mobile/sw.js").catch(() => {});
}
