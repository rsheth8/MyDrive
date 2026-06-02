import Constants from "expo-constants";

/**
 * Expo Go on a physical phone cannot reach `localhost` — use your Mac's LAN IP:
 *   EXPO_PUBLIC_API_URL=http://192.168.1.x:8000 npx expo start
 */
const fromEnv = process.env.EXPO_PUBLIC_API_URL;
const fromExtra = Constants.expoConfig?.extra?.apiUrl as string | undefined;

export const API_URL = (fromEnv || fromExtra || "http://localhost:8000").replace(/\/$/, "");

export function apiHint(): string {
  if (API_URL.includes("localhost") || API_URL.includes("127.0.0.1")) {
    return "On a real device, set EXPO_PUBLIC_API_URL to your computer's IP (port 8000).";
  }
  return `API: ${API_URL}`;
}
