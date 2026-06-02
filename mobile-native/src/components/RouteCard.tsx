import * as Haptics from "expo-haptics";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { RouteResult } from "../api";
import { colors, radius, routeAccent, routeEmoji, spacing } from "../theme";

type Props = {
  route: RouteResult;
  selected: boolean;
  passenger: boolean;
  onSelect: () => void;
  onSpeak?: () => void;
  onNavigate?: () => void;
};

export function RouteCard({
  route,
  selected,
  passenger,
  onSelect,
  onSpeak,
  onNavigate,
}: Props) {
  const accent = routeAccent[route.id] ?? colors.brand;

  const openMaps = (apple: boolean) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    Linking.openURL(apple ? route.maps.apple : route.maps.google);
  };

  return (
    <Pressable
      style={[
        styles.card,
        passenger && styles.passenger,
        selected && { borderColor: accent, shadowColor: accent },
      ]}
      onPress={() => {
        Haptics.selectionAsync();
        onSelect();
        if (passenger && onSpeak) onSpeak();
      }}
    >
      <View style={styles.top}>
        <Text style={styles.emoji}>{routeEmoji[route.id] ?? "🚗"}</Text>
        <View style={styles.head}>
          <Text style={styles.title}>{route.label}</Text>
          <Text style={styles.tagline}>{route.tagline}</Text>
        </View>
      </View>

      <View style={styles.stats}>
        <View style={styles.stat}>
          <Text style={styles.statLabel}>Time</Text>
          <Text style={styles.statVal}>{route.time_display}</Text>
        </View>
        <View style={styles.stat}>
          <Text style={styles.statLabel}>Tolls</Text>
          <Text style={styles.statVal}>{route.tolls_display}</Text>
        </View>
        {!passenger && (
          <>
            <View style={styles.stat}>
              <Text style={styles.statLabel}>Safety</Text>
              <Text style={styles.statVal}>{route.safety}</Text>
            </View>
            <View style={styles.stat}>
              <Text style={styles.statLabel}>Feel</Text>
              <Text style={styles.statVal}>{route.feel}</Text>
            </View>
          </>
        )}
      </View>

      {!passenger && <Text style={styles.vs}>{route.vs_fastest}</Text>}

      <View style={styles.mapsRow}>
        {onNavigate && (
          <Pressable
            style={[styles.mapBtn, styles.navigate]}
            onPress={() => {
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
              onNavigate();
            }}
          >
            <Text style={styles.mapText}>Navigate</Text>
          </Pressable>
        )}
        <Pressable style={[styles.mapBtn, styles.google]} onPress={() => openMaps(false)}>
          <Text style={styles.mapText}>Google</Text>
        </Pressable>
        <Pressable style={[styles.mapBtn, styles.apple]} onPress={() => openMaps(true)}>
          <Text style={styles.mapText}>Apple</Text>
        </Pressable>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
    borderWidth: 2,
    borderColor: colors.border,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 4,
  },
  passenger: { paddingVertical: spacing.xl },
  top: { flexDirection: "row", gap: spacing.md, marginBottom: spacing.md },
  emoji: { fontSize: 32 },
  head: { flex: 1 },
  title: { color: colors.text, fontSize: 20, fontWeight: "800" },
  tagline: { color: colors.textMuted, fontSize: 14, marginTop: 2 },
  stats: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  stat: {
    minWidth: "47%",
    backgroundColor: colors.bgElevated,
    borderRadius: radius.sm,
    padding: spacing.sm,
  },
  statLabel: {
    color: colors.textDim,
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: 0.6,
  },
  statVal: { color: colors.text, fontSize: 15, fontWeight: "700", marginTop: 2 },
  vs: { color: colors.textMuted, fontSize: 13, marginBottom: spacing.md },
  mapsRow: { flexDirection: "row", gap: spacing.sm },
  mapBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: radius.md,
    alignItems: "center",
  },
  navigate: { backgroundColor: colors.brand },
  google: { backgroundColor: colors.google },
  apple: {
    backgroundColor: colors.apple,
    borderWidth: 2,
    borderColor: colors.border,
  },
  mapText: { color: "#fff", fontWeight: "700", fontSize: 14 },
});
