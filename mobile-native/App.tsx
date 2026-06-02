import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import * as Speech from "expo-speech";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import {
  AppConfig,
  checkHealth,
  compareRoutes,
  geocode,
  LatLon,
  loadPresets,
  PlaceSuggestion,
  RouteResult,
} from "./src/api";
import { PlaceAutocomplete } from "./src/components/PlaceAutocomplete";
import { ApiBanner } from "./src/components/ApiBanner";
import { Header } from "./src/components/Header";
import { ModeToggle } from "./src/components/ModeToggle";
import { RouteCard } from "./src/components/RouteCard";
import { SafetyBanner } from "./src/components/SafetyBanner";
import { NavigationScreen, NavTrip } from "./src/screens/NavigationScreen";
import { BRAND } from "./src/brand";
import { colors, radius, spacing } from "./src/theme";

const PASSENGER_IDS = ["fastest", "calm", "safest"];

export default function App() {
  const [screen, setScreen] = useState<"home" | "nav">("home");
  const [navTrip, setNavTrip] = useState<NavTrip | null>(null);
  const [mode, setMode] = useState<"full" | "passenger">("passenger");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [routes, setRoutes] = useState<RouteResult[]>([]);
  const [presets, setPresets] = useState<AppConfig["presets"]>([]);
  const [selectedId, setSelectedId] = useState("fastest");
  const [tripTitle, setTripTitle] = useState("");
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [showForm, setShowForm] = useState(true);
  const [fromCoords, setFromCoords] = useState<LatLon | null>(null);
  const [toCoords, setToCoords] = useState<LatLon | null>(null);
  const [tripOrigin, setTripOrigin] = useState<LatLon | null>(null);
  const [tripDest, setTripDest] = useState<LatLon | null>(null);

  const visibleRoutes =
    mode === "passenger" ? routes.filter((r) => PASSENGER_IDS.includes(r.id)) : routes;

  const refreshHealth = useCallback(async () => {
    setApiOk(null);
    setApiOk(await checkHealth());
  }, []);

  const loadConfig = useCallback(async () => {
    try {
      const cfg = await loadPresets();
      setPresets(cfg.presets || []);
      setApiOk(true);
    } catch {
      setApiOk(false);
    }
  }, []);

  useEffect(() => {
    refreshHealth();
    loadConfig();
  }, [refreshHealth, loadConfig]);

  const runCompare = async (preset?: AppConfig["presets"][0]) => {
    setLoading(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    try {
      const origin = preset
        ? { lat: preset.from_lat, lon: preset.from_lon }
        : await geocode(from, fromCoords);
      const dest = preset
        ? { lat: preset.to_lat, lon: preset.to_lon }
        : await geocode(to, toCoords);
      const title = preset ? preset.label : `${from} → ${to}`;
      setTripTitle(title);
      setTripOrigin(origin);
      setTripDest(dest);
      const priority = mode === "passenger" ? "balanced" : "balanced";
      const data = await compareRoutes(origin, dest, priority);
      setRoutes(data.routes);
      setSelectedId(
        mode === "passenger" ? "fastest" : data.routes[0]?.id || "fastest"
      );
      setShowForm(false);
      setApiOk(true);
      if (!data.complete) {
        Alert.alert("Heads up", "Route may be incomplete — check your addresses.");
      }
    } catch (e: unknown) {
      setApiOk(false);
      Alert.alert("Error", e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  };

  const openNativeNav = (route: RouteResult) => {
    if (!tripOrigin || !tripDest) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setNavTrip({
      title: tripTitle,
      origin: tripOrigin,
      destination: tripDest,
      routeLabel: route.label,
      polyline: route.polyline,
    });
    setScreen("nav");
  };

  const speakHint = (route: RouteResult) => {
    Speech.speak(
      `${route.label}. ${route.time_display}. ${route.tolls_display}. Open Maps when ready.`,
      { rate: 0.92 }
    );
  };

  if (screen === "nav" && navTrip) {
    return (
      <SafeAreaProvider>
        <StatusBar style="light" />
        <NavigationScreen trip={navTrip} onExit={() => setScreen("home")} />
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safe} edges={["top", "left", "right"]}>
        <StatusBar style="light" />
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
          >
            <Header />
            <ApiBanner connected={apiOk} />
            <ModeToggle mode={mode} onChange={setMode} />
            <SafetyBanner passenger={mode === "passenger"} />

            {showForm ? (
              <View style={styles.panel}>
                <Text style={styles.sectionLabel}>Popular trips</Text>
                {presets.map((p) => (
                  <Pressable
                    key={p.id}
                    style={styles.preset}
                    onPress={() => runCompare(p)}
                    disabled={loading}
                  >
                    <Ionicons name="navigate-outline" size={18} color={colors.brand} />
                    <Text style={styles.presetText}>{p.label}</Text>
                    <Ionicons name="chevron-forward" size={18} color={colors.textDim} />
                  </Pressable>
                ))}

                <Text style={[styles.sectionLabel, styles.sectionGap]}>Your trip</Text>
                <PlaceAutocomplete
                  label="From"
                  placeholder="Search address or place…"
                  value={from}
                  onChangeText={(t) => {
                    setFrom(t);
                    setFromCoords(null);
                  }}
                  onSelect={(p: PlaceSuggestion) => {
                    setFromCoords({ lat: p.lat, lon: p.lon });
                  }}
                />
                <PlaceAutocomplete
                  label="To"
                  placeholder="Search address or place…"
                  value={to}
                  onChangeText={(t) => {
                    setTo(t);
                    setToCoords(null);
                  }}
                  onSelect={(p: PlaceSuggestion) => {
                    setToCoords({ lat: p.lat, lon: p.lon });
                  }}
                />

                <Pressable
                  style={[styles.primary, loading && styles.primaryDisabled]}
                  onPress={() => runCompare()}
                  disabled={loading}
                >
                  {loading ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <>
                      <Ionicons name="git-compare-outline" size={22} color="#fff" />
                      <Text style={styles.primaryText}>Compare routes</Text>
                    </>
                  )}
                </Pressable>
              </View>
            ) : (
              <View style={styles.resultsBar}>
                <View style={styles.tripRow}>
                  <Text style={styles.tripTitle} numberOfLines={2}>
                    {tripTitle}
                  </Text>
                  <Pressable
                    onPress={() => {
                      setShowForm(true);
                      setRoutes([]);
                    }}
                    hitSlop={12}
                  >
                    <Text style={styles.changeLink}>Change</Text>
                  </Pressable>
                </View>
                <Text style={styles.resultsHint}>
                  {mode === "passenger"
                    ? "Tap Navigate for in-app GPS · or Google/Apple Maps"
                    : "Navigate uses your chosen MyDrive route on the map"}
                </Text>
              </View>
            )}

            {visibleRoutes.map((route) => (
              <RouteCard
                key={route.id}
                route={route}
                selected={selectedId === route.id}
                passenger={mode === "passenger"}
                onSelect={() => setSelectedId(route.id)}
                onSpeak={() => speakHint(route)}
                onNavigate={
                  tripOrigin && tripDest ? () => openNativeNav(route) : undefined
                }
              />
            ))}

            <Text style={styles.footer}>
              {BRAND.name} · native maps + GPS · park before you drive
            </Text>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  scroll: {
    paddingHorizontal: spacing.lg,
    paddingBottom: 40,
    paddingTop: spacing.sm,
  },
  panel: {
    backgroundColor: colors.bgElevated,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.lg,
  },
  sectionLabel: {
    color: colors.textDim,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
    marginBottom: spacing.sm,
  },
  sectionGap: { marginTop: spacing.lg },
  preset: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: colors.surface,
    padding: spacing.md,
    borderRadius: radius.md,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  presetText: {
    flex: 1,
    color: colors.text,
    fontSize: 16,
    fontWeight: "600",
  },
  primary: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    backgroundColor: colors.brand,
    paddingVertical: 18,
    borderRadius: radius.md,
    marginTop: spacing.sm,
  },
  primaryDisabled: { opacity: 0.7 },
  primaryText: { color: "#fff", fontSize: 17, fontWeight: "800" },
  resultsBar: { marginBottom: spacing.md },
  tripRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  tripTitle: {
    flex: 1,
    color: colors.text,
    fontSize: 18,
    fontWeight: "700",
  },
  changeLink: { color: colors.brand, fontWeight: "700", fontSize: 15 },
  resultsHint: { color: colors.textMuted, fontSize: 13, marginTop: spacing.xs },
  footer: {
    color: colors.textDim,
    fontSize: 11,
    textAlign: "center",
    marginTop: spacing.xl,
    lineHeight: 16,
  },
});
