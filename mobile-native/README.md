# MyDrive Native (Expo Go)

React Native app that uses the **same FastAPI backend** as the PWA. Runs in **Expo Go** — no custom native build required for development.

## Expo Go — quick start

From repo root:

```bash
./scripts/dev.sh setup    # once
./scripts/dev.sh mobile   # terminal 1
./scripts/dev.sh expo     # terminal 2
```

1. Install **Expo Go** from the App Store or Play Store.
2. Scan the QR code in the terminal (same Wi‑Fi as your computer).
3. If the app shows “Cannot reach API”, run `./scripts/dev.sh mobile` first, then `./scripts/dev.sh check`.

### Simulator

Open the **Expo Go** app in the simulator manually and enter the URL from the terminal. Avoid pressing **`i`** in the Expo CLI — it may prompt for an Expo account login.

### Tunnel (different networks)

```bash
EXPO_PUBLIC_API_URL=http://YOUR_IP:8000 npx expo start --tunnel
```

Note: the **API** must still be reachable from the phone; tunnel only helps load the JS bundle.

## What works in Expo Go

| Package | Purpose |
|---------|---------|
| `expo-speech` | Passenger route readout |
| `expo-haptics` | Tap feedback |
| `expo-linking` | Open Google / Apple Maps |
| `@expo/vector-icons` | UI icons |
| `react-native-safe-area-context` | Notch / home indicator |

All listed dependencies are **Expo Go compatible** (no custom dev client required).

## Features

- Full / Passenger mode
- Popular Chicagoland trips
- Google Maps + Apple Maps handoff
- API connection banner when backend is unreachable
- Spoken route summary (passenger mode)

## CarPlay / Android Auto

Not in v1. Choose a route in MyDrive, then open Apple or Google Maps for turn-by-turn.

## Production builds

When you are ready for the App Store:

```bash
npx expo prebuild
eas build
```
