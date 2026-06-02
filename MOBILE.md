# MyDrive Mobile

Phone-friendly **PWA** + optional **React Native (Expo)** app for Chicagoland.

## Safety first

- **Do not use while driving.**
- **Passenger mode** — copilot picks Fastest / Calmest / Safest, opens Maps.
- **Voice** — only when parked (mic buttons on PWA).
- **Navigation** — always hand off to **Google Maps** or **Apple Maps**.

CarPlay / Android Auto are not included in v1 (requires native entitlements + Apple/Google partnerships). Maps handoff is the supported pattern.

---

## 1. PWA (recommended — fastest to try)

```bash
./scripts/dev.sh setup    # once
./scripts/dev.sh mobile   # API + PWA
```

- **Desktop/simulator:** http://localhost:8000  
- **Phone (same Wi‑Fi):** http://`<your-mac-ip>`:8000  
- **Install:** Safari → Share → **Add to Home Screen**

### PWA features

| Feature | How |
|--------|-----|
| **Passenger mode** | Toggle at top → 3 large buttons (Fastest, Calmest, Safest) |
| **Apple Maps** | Green/gray buttons on each route |
| **Google Maps** | Same row |
| **Voice input** | 🎤 next to From / To (Chrome/Safari, parked only) |
| **Offline** | Popular trips + last route per trip cached |
| **Live traffic** | Placeholder note (API ready for future provider key) |

---

## 2. React Native — **Expo Go** (same phone app, native shell)

Works with the free **Expo Go** app (no Xcode/Android Studio needed for dev).

```bash
./scripts/dev.sh setup    # once
./scripts/dev.sh mobile   # terminal 1
./scripts/dev.sh expo     # terminal 2 — scan QR with Expo Go
```

1. Install **Expo Go** on your iPhone or Android.  
2. Scan the QR code (same Wi‑Fi as your Mac).  
3. If you see “Cannot reach API”, check that `run_mobile.sh` is running and the banner shows your Mac’s IP on port **8000**.

Details: **[mobile-native/README.md](mobile-native/README.md)**

### Native app features

- Full / Passenger mode toggle  
- Popular trips  
- Google + Apple Maps via `Linking`  
- Spoken summary in Passenger mode (`expo-speech`)  
- Same backend API as PWA  

### Ship to stores

1. `npx expo prebuild`  
2. Configure signing (Apple Developer / Google Play)  
3. `eas build` (Expo Application Services)  
4. CarPlay: separate entitlement — see [Apple CarPlay docs](https://developer.apple.com/carplay/)

---

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/config` | Chicagoland presets |
| `POST /api/geocode` | Address → lat/lon |
| `POST /api/routes/compare` | All route types + Your pick |
| `GET /api/traffic/status` | Traffic integration status |

---

## Architecture

```
mobile/              PWA (HTML/CSS/JS)
mobile-native/       Expo React Native
src/api/main.py      FastAPI
src/services/        Shared routing engine
streamlit_app.py     Desktop dashboard (optional)
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Phone can't reach API | Same Wi‑Fi; use Mac IP not `localhost` |
| Voice doesn't work | HTTPS or localhost; allow mic permission |
| Slow first route | OSM download for long trips (30–60s) |
| Expo can't connect | Run `./scripts/dev.sh mobile` first; `./scripts/dev.sh check` |
| Expo login prompt | Don't press `i` in terminal — scan QR with Expo Go app |
| Missing assets error | `./scripts/dev.sh setup` |
| Native navigation | Tap **Navigate** on a route — in-app map + GPS (Expo Go) |
| Location denied | Allow location when starting navigation |
