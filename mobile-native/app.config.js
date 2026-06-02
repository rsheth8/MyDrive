const brand = require("../config/brand.json");

/** @type {import('expo/config').ExpoConfig} */
module.exports = {
  expo: {
    name: brand.name,
    slug: brand.slug,
    version: "1.0.0",
    orientation: "portrait",
    userInterfaceStyle: "dark",
    scheme: brand.scheme,
    splash: {
      backgroundColor: "#070b14",
    },
    ios: {
      supportsTablet: false,
      bundleIdentifier: "com.mydrive.app",
      infoPlist: {
        NSAppTransportSecurity: {
          NSAllowsArbitraryLoads: true,
          NSExceptionDomains: {
            localhost: { NSExceptionAllowsInsecureHTTPLoads: true },
          },
        },
        NSLocationWhenInUseUsageDescription: `${brand.name} uses your location for turn-by-turn navigation.`,
        NSSpeechRecognitionUsageDescription: `${brand.name} uses speech to enter destinations while parked.`,
        NSMicrophoneUsageDescription: `${brand.name} uses the microphone for voice destination entry while parked.`,
      },
    },
    android: {
      package: "com.mydrive.app",
      permissions: [
        "ACCESS_COARSE_LOCATION",
        "ACCESS_FINE_LOCATION",
        "RECORD_AUDIO",
      ],
    },
    plugins: [
      [
        "expo-location",
        {
          locationWhenInUsePermission: `${brand.name} uses your location for turn-by-turn navigation while the app is open.`,
        },
      ],
    ],
    extra: {
      apiUrl: process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000",
    },
  },
};
