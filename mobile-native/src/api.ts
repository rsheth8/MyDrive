import { API_URL } from "./config";

export type LatLon = { lat: number; lon: number };

export type PlaceSuggestion = {
  id: string;
  label: string;
  subtitle: string;
  lat: number;
  lon: number;
  source: string;
};

export type RouteResult = {
  id: string;
  label: string;
  tagline: string;
  detail: string;
  pick_when: string;
  time_display: string;
  tolls_display: string;
  safety: string;
  feel: string;
  vs_fastest: string;
  polyline?: number[][];
  maps: { google: string; apple: string };
};

export type AppConfig = {
  presets: Array<{
    id: string;
    label: string;
    from_address: string;
    to_address: string;
    from_lat: number;
    from_lon: number;
    to_lat: number;
    to_lon: number;
    from_label: string;
    to_label: string;
  }>;
};

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/api/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function searchPlaces(query: string): Promise<PlaceSuggestion[]> {
  const res = await fetch(
    `${API_URL}/api/places/autocomplete?q=${encodeURIComponent(query.trim())}`
  );
  if (!res.ok) return [];
  const data = await res.json();
  return data.suggestions || [];
}

export async function geocode(
  query: string,
  coords?: LatLon | null
): Promise<LatLon> {
  const body: { query: string; lat?: number; lon?: number } = { query };
  if (coords) {
    body.lat = coords.lat;
    body.lon = coords.lon;
  }
  const res = await fetch(`${API_URL}/api/geocode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Geocode failed");
  return res.json();
}

export async function compareRoutes(
  origin: LatLon,
  dest: LatLon,
  priority = "balanced"
) {
  const res = await fetch(`${API_URL}/api/routes/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      origin_lat: origin.lat,
      origin_lon: origin.lon,
      dest_lat: dest.lat,
      dest_lon: dest.lon,
      buffer_km: 2,
      priority,
    }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Routing failed");
  return res.json() as Promise<{ routes: RouteResult[]; complete: boolean }>;
}

export type DirectionsResult = {
  provider: string;
  distance_display: string;
  duration_display: string;
  route_label?: string;
  geometry_source?: string;
  geometry: number[][];
  steps: Array<{
    instruction: string;
    distance_display: string;
    location: [number, number];
  }>;
};

export async function fetchDirections(
  origin: LatLon,
  dest: LatLon,
  opts?: { routeLabel?: string; polyline?: number[][] }
): Promise<DirectionsResult> {
  const res = await fetch(`${API_URL}/api/navigation/directions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      origin_lat: origin.lat,
      origin_lon: origin.lon,
      dest_lat: dest.lat,
      dest_lon: dest.lon,
      provider: "auto",
      route_label: opts?.routeLabel,
      polyline: opts?.polyline,
    }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Directions failed");
  return res.json();
}

/** Opens full-screen nav in the device browser (same as PWA). */
export function navigationPageUrl(trip: {
  title: string;
  origin: LatLon;
  destination: LatLon;
  routeLabel: string;
}): string {
  const json = JSON.stringify(trip);
  const encoded =
    typeof btoa !== "undefined"
      ? btoa(unescape(encodeURIComponent(json)))
      : "";
  return `${API_URL}/mobile/nav.html#trip=${encodeURIComponent(encoded)}`;
}

export async function loadPresets(): Promise<AppConfig> {
  const res = await fetch(`${API_URL}/api/config`);
  if (!res.ok) throw new Error("Could not load config");
  return res.json();
}
