const API = "";
const NAV_SESSION_KEY = "mydrive_nav_trip_v1";

const $ = (id) => document.getElementById(id);

let map = null;
let routeLine = null;
let userMarker = null;
let watchId = null;
let directions = null;
let activeStep = 0;
let navigating = false;
let voiceOn = false;
let trip = null;

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function loadTrip() {
  try {
    if (location.hash.startsWith("#trip=")) {
      const encoded = location.hash.slice(6);
      return JSON.parse(decodeURIComponent(atob(encoded)));
    }
    const raw = sessionStorage.getItem(NAV_SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function haversineM(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

function initMap() {
  map = L.map("nav-map", { zoomControl: false }).setView([41.8781, -87.6298], 11);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap",
    maxZoom: 19,
  }).addTo(map);
}

function drawRoute(geometry, origin, destination) {
  if (routeLine) map.removeLayer(routeLine);
  const latlngs = geometry.length ? geometry : [[origin.lat, origin.lon], [destination.lat, destination.lon]];
  routeLine = L.polyline(latlngs, { color: "#4f8cff", weight: 6, opacity: 0.9 }).addTo(map);
  L.circleMarker([origin.lat, origin.lon], { radius: 8, color: "#22c55e", fillColor: "#22c55e", fillOpacity: 1 })
    .addTo(map)
    .bindPopup("Start");
  L.circleMarker([destination.lat, destination.lon], { radius: 8, color: "#f472b6", fillColor: "#f472b6", fillOpacity: 1 })
    .addTo(map)
    .bindPopup("End");
  map.fitBounds(routeLine.getBounds(), { padding: [80, 40] });
}

function renderSteps() {
  const list = $("nav-steps");
  list.innerHTML = "";
  (directions?.steps || []).forEach((step, i) => {
    const li = document.createElement("li");
    li.textContent = `${step.instruction} · ${step.distance_display}`;
    if (i < activeStep) li.classList.add("done");
    if (i === activeStep) li.classList.add("active");
    list.appendChild(li);
  });
}

function updateCurrentStep() {
  const steps = directions?.steps || [];
  if (!steps.length) return;
  const step = steps[Math.min(activeStep, steps.length - 1)];
  $("nav-instruction").textContent = step.instruction;
  $("nav-step-distance").textContent = step.distance_display
    ? `In about ${step.distance_display}`
    : "";
  renderSteps();
  if (voiceOn && navigating) {
    speak(step.instruction);
  }
}

function speak(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.95;
  window.speechSynthesis.speak(u);
}

function findNearestStep(lat, lon) {
  const steps = directions?.steps || [];
  let best = activeStep;
  let bestDist = Infinity;
  steps.forEach((step, i) => {
    if (i < activeStep) return;
    const [slat, slon] = step.location;
    const d = haversineM(lat, lon, slat, slon);
    if (d < bestDist) {
      bestDist = d;
      best = i;
    }
  });
  if (bestDist < 35 && best > activeStep) {
    activeStep = best;
    updateCurrentStep();
  }
  if (bestDist < 25 && activeStep < steps.length - 1) {
    const next = steps[activeStep + 1];
    const nd = haversineM(lat, lon, next.location[0], next.location[1]);
    if (nd < 30) {
      activeStep += 1;
      updateCurrentStep();
    }
  }
}

function startGps() {
  if (!navigator.geolocation) return;
  const icon = L.divIcon({ className: "user-marker", iconSize: [18, 18] });
  watchId = navigator.geolocation.watchPosition(
    (pos) => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;
      if (!userMarker) {
        userMarker = L.marker([lat, lon], { icon }).addTo(map);
      } else {
        userMarker.setLatLng([lat, lon]);
      }
      if (navigating) findNearestStep(lat, lon);
    },
    () => {},
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
  );
}

function startNavigation() {
  navigating = true;
  document.body.classList.add("nav-active");
  $("nav-safety").classList.add("hidden");
  activeStep = 0;
  updateCurrentStep();
  startGps();
  if (map && directions?.geometry?.length) {
    map.setView(directions.geometry[0], 14);
  }
}

async function loadDirections() {
  trip = loadTrip();
  if (!trip?.origin || !trip?.destination) {
    $("nav-instruction").textContent = "No trip loaded. Go back and compare a route first.";
    return;
  }

  $("nav-title").textContent = trip.title || "Your trip";
  $("nav-meta").textContent = `${trip.routeLabel || "Driving"} · loading…`;

  directions = await api("/api/navigation/directions", {
    method: "POST",
    body: JSON.stringify({
      origin_lat: trip.origin.lat,
      origin_lon: trip.origin.lon,
      dest_lat: trip.destination.lat,
      dest_lon: trip.destination.lon,
      provider: "auto",
      route_label: trip.routeLabel,
      polyline: trip.polyline,
    }),
  });

  const routeNote = directions.route_label
    ? `${directions.route_label} route`
    : directions.provider;
  const geomNote = directions.geometry_source === "mydrive" ? " · MyDrive path" : "";
  $("nav-meta").textContent = `${directions.duration_display} · ${directions.distance_display} · ${routeNote}${geomNote}`;
  $("nav-provider").textContent = directions.provider;

  drawRoute(directions.geometry, trip.origin, trip.destination);
  renderSteps();
  updateCurrentStep();

  const o = `${trip.origin.lat},${trip.origin.lon}`;
  const d = `${trip.destination.lat},${trip.destination.lon}`;
  $("open-google").onclick = () => {
    window.location.href = `https://www.google.com/maps/dir/?api=1&origin=${o}&destination=${d}&travelmode=driving`;
  };
  $("open-apple").onclick = () => {
    window.location.href = `http://maps.apple.com/?saddr=${o}&daddr=${d}&dirflg=d`;
  };
}

$("nav-start").addEventListener("click", startNavigation);
$("nav-voice").addEventListener("click", () => {
  voiceOn = !voiceOn;
  $("nav-voice").setAttribute("aria-pressed", String(voiceOn));
});

initMap();
loadDirections().catch((err) => {
  $("nav-instruction").textContent = err.message || "Could not load directions.";
});

window.addEventListener("beforeunload", () => {
  if (watchId != null) navigator.geolocation.clearWatch(watchId);
});
