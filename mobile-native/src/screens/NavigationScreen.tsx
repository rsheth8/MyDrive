import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import MapView, { Marker, Polyline, Region } from "react-native-maps";
import * as Location from "expo-location";
import * as Speech from "expo-speech";
import * as Haptics from "expo-haptics";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";

import { DirectionsResult, fetchDirections, LatLon } from "../api";
import { colors, radius, spacing } from "../theme";

export type NavTrip = {
  title: string;
  origin: LatLon;
  destination: LatLon;
  routeLabel: string;
  polyline?: number[][];
};

type Props = {
  trip: NavTrip;
  onExit: () => void;
};

function haversineM(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371000;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

export function NavigationScreen({ trip, onExit }: Props) {
  const mapRef = useRef<MapView>(null);
  const [directions, setDirections] = useState<DirectionsResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeStep, setActiveStep] = useState(0);
  const [navigating, setNavigating] = useState(false);
  const [voiceOn, setVoiceOn] = useState(false);
  const [userLoc, setUserLoc] = useState<LatLon | null>(null);
  const watchRef = useRef<Location.LocationSubscription | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await fetchDirections(trip.origin, trip.destination, {
        routeLabel: trip.routeLabel,
        polyline: trip.polyline,
      });
      setDirections(d);
    } catch (e: unknown) {
      Alert.alert("Navigation", e instanceof Error ? e.message : "Failed to load");
      onExit();
    } finally {
      setLoading(false);
    }
  }, [trip, onExit]);

  useEffect(() => {
    load();
    return () => {
      if (watchRef.current) watchRef.current.remove();
      Speech.stop();
    };
  }, [load]);

  const steps = directions?.steps || [];
  const geometry = directions?.geometry || [];
  const current = steps[activeStep];

  const fitRoute = useCallback(() => {
    if (!geometry.length || !mapRef.current) return;
    mapRef.current.fitToCoordinates(
      geometry.map(([lat, lon]) => ({ latitude: lat, longitude: lon })),
      {
        edgePadding: { top: 120, right: 40, bottom: 220, left: 40 },
        animated: true,
      }
    );
  }, [geometry]);

  useEffect(() => {
    if (directions) setTimeout(fitRoute, 400);
  }, [directions, fitRoute]);

  const advanceByGps = (lat: number, lon: number) => {
    if (!navigating || !steps.length) return;
    for (let i = activeStep; i < steps.length; i++) {
      const [slat, slon] = steps[i].location;
      if (haversineM(lat, lon, slat, slon) < 40 && i > activeStep) {
        setActiveStep(i);
        if (voiceOn) Speech.speak(steps[i].instruction, { rate: 0.92 });
        break;
      }
    }
  };

  const startNavigation = async () => {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== "granted") {
      Alert.alert("Location needed", "Allow location to track your drive.");
      return;
    }
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    setNavigating(true);
    setActiveStep(0);
    if (voiceOn && steps[0]) Speech.speak(steps[0].instruction, { rate: 0.92 });

    watchRef.current = await Location.watchPositionAsync(
      {
        accuracy: Location.Accuracy.High,
        distanceInterval: 8,
        timeInterval: 3000,
      },
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        setUserLoc({ lat, lon });
        advanceByGps(lat, lon);
        mapRef.current?.animateCamera({
          center: { latitude: lat, longitude: lon },
          zoom: 15,
        });
      }
    );
  };

  const initialRegion: Region = {
    latitude: trip.origin.lat,
    longitude: trip.origin.lon,
    latitudeDelta: 0.12,
    longitudeDelta: 0.12,
  };

  if (loading || !directions) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.brand} />
        <Text style={styles.loadingText}>Loading turn-by-turn…</Text>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <MapView ref={mapRef} style={styles.map} initialRegion={initialRegion}>
        {geometry.length > 0 && (
          <Polyline
            coordinates={geometry.map(([lat, lon]) => ({
              latitude: lat,
              longitude: lon,
            }))}
            strokeColor={colors.brand}
            strokeWidth={5}
          />
        )}
        <Marker
          coordinate={{ latitude: trip.origin.lat, longitude: trip.origin.lon }}
          title="Start"
          pinColor="#22c55e"
        />
        <Marker
          coordinate={{
            latitude: trip.destination.lat,
            longitude: trip.destination.lon,
          }}
          title="End"
          pinColor="#f472b6"
        />
        {userLoc && (
          <Marker
            coordinate={{ latitude: userLoc.lat, longitude: userLoc.lon }}
            title="You"
            pinColor={colors.brand}
          />
        )}
      </MapView>

      <SafeAreaView style={styles.topBar} edges={["top"]}>
        <Pressable onPress={onExit} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={22} color={colors.brand} />
          <Text style={styles.backText}>Back</Text>
        </Pressable>
        <View style={styles.topMeta}>
          <Text style={styles.tripTitle} numberOfLines={1}>
            {trip.title}
          </Text>
          <Text style={styles.tripSub}>
            {directions.route_label || trip.routeLabel} · {directions.duration_display}
            {directions.geometry_source === "mydrive" ? " · MyDrive path" : ""}
          </Text>
        </View>
        <Pressable
          onPress={() => {
            setVoiceOn((v) => !v);
            Haptics.selectionAsync();
          }}
          style={[styles.voiceBtn, voiceOn && styles.voiceOn]}
        >
          <Ionicons name={voiceOn ? "volume-high" : "volume-mute"} size={20} color="#fff" />
        </Pressable>
      </SafeAreaView>

      {!navigating && (
        <View style={styles.safetyBanner}>
          <Text style={styles.safetyText}>
            Park to start. Passenger or parked use only — not while driving.
          </Text>
        </View>
      )}

      <View style={styles.instructionCard}>
        <Text style={styles.stepLabel}>
          {navigating ? `Step ${activeStep + 1} of ${steps.length}` : "Next"}
        </Text>
        <Text style={styles.instruction}>{current?.instruction || "Ready"}</Text>
        {current?.distance_display ? (
          <Text style={styles.stepDist}>In about {current.distance_display}</Text>
        ) : null}
      </View>

      <View style={styles.panel}>
        <FlatList
          data={steps}
          keyExtractor={(_, i) => String(i)}
          style={styles.stepList}
          renderItem={({ item, index }) => (
            <Pressable
              style={[
                styles.stepRow,
                index === activeStep && styles.stepActive,
                index < activeStep && styles.stepDone,
              ]}
              onPress={() => setActiveStep(index)}
            >
              <Text style={styles.stepText}>
                {index + 1}. {item.instruction}
              </Text>
              <Text style={styles.stepMeta}>{item.distance_display}</Text>
            </Pressable>
          )}
        />
      </View>

      {!navigating ? (
        <Pressable style={styles.startBtn} onPress={startNavigation}>
          <Ionicons name="navigate" size={22} color="#fff" />
          <Text style={styles.startText}>Start navigation</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  map: { ...StyleSheet.absoluteFillObject },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.bg,
  },
  loadingText: { color: colors.textMuted, marginTop: spacing.md },
  topBar: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.sm,
    backgroundColor: "rgba(7,11,20,0.85)",
  },
  backBtn: { flexDirection: "row", alignItems: "center", paddingRight: spacing.sm },
  backText: { color: colors.brand, fontWeight: "700" },
  topMeta: { flex: 1, minWidth: 0 },
  tripTitle: { color: colors.text, fontWeight: "700", fontSize: 15 },
  tripSub: { color: colors.textMuted, fontSize: 11, marginTop: 2 },
  voiceBtn: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  voiceOn: { backgroundColor: colors.brand },
  safetyBanner: {
    position: "absolute",
    top: 100,
    left: spacing.md,
    right: spacing.md,
    backgroundColor: colors.warningBg,
    borderRadius: radius.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: "#854d0e",
  },
  safetyText: { color: "#fde68a", fontSize: 12, lineHeight: 18 },
  instructionCard: {
    position: "absolute",
    left: spacing.md,
    right: spacing.md,
    bottom: 200,
    backgroundColor: "rgba(20,28,46,0.95)",
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderFocus,
  },
  stepLabel: {
    color: colors.textDim,
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  instruction: {
    color: colors.text,
    fontSize: 20,
    fontWeight: "800",
    marginTop: 4,
    lineHeight: 26,
  },
  stepDist: { color: colors.textMuted, marginTop: 6, fontSize: 14 },
  panel: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    maxHeight: 180,
    backgroundColor: "rgba(20,28,46,0.96)",
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    paddingTop: spacing.sm,
  },
  stepList: { maxHeight: 120 },
  stepRow: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  stepActive: { backgroundColor: "rgba(79,140,255,0.15)" },
  stepDone: { opacity: 0.45 },
  stepText: { color: colors.text, fontSize: 13 },
  stepMeta: { color: colors.textDim, fontSize: 11, marginTop: 2 },
  startBtn: {
    position: "absolute",
    left: spacing.lg,
    right: spacing.lg,
    bottom: spacing.xl + 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    backgroundColor: colors.brand,
    paddingVertical: 16,
    borderRadius: radius.md,
  },
  startText: { color: "#fff", fontWeight: "800", fontSize: 17 },
});
