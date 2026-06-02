/** Shared design tokens — PWA uses the same palette in mobile/app.css */

export const colors = {
  bg: "#070b14",
  bgElevated: "#0d1424",
  surface: "#141c2e",
  surfaceHover: "#1a2540",
  border: "#2a3654",
  borderFocus: "#4f8cff",
  text: "#f1f5f9",
  textMuted: "#94a3b8",
  textDim: "#64748b",
  brand: "#4f8cff",
  brandDark: "#2563eb",
  brandGlow: "rgba(79, 140, 255, 0.25)",
  success: "#22c55e",
  warning: "#fbbf24",
  warningBg: "#3d2a06",
  danger: "#f87171",
  google: "#22c55e",
  apple: "#1e293b",
} as const;

export const routeAccent: Record<string, string> = {
  fastest: "#4f8cff",
  calm: "#a78bfa",
  safest: "#fb923c",
  cheapest: "#34d399",
  reliable: "#22d3ee",
  balanced: "#2dd4bf",
  parking: "#f472b6",
  your_pick: "#94a3b8",
};

export const routeEmoji: Record<string, string> = {
  fastest: "⚡",
  calm: "😌",
  safest: "🛡️",
  cheapest: "💵",
  reliable: "📊",
  balanced: "⚖️",
  parking: "🅿️",
  your_pick: "✨",
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
} as const;

export const radius = {
  sm: 10,
  md: 14,
  lg: 18,
  xl: 22,
  pill: 999,
} as const;
