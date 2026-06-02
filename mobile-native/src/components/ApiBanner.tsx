import { StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { apiHint } from "../config";
import { colors, radius, spacing } from "../theme";

type Props = { connected: boolean | null };

export function ApiBanner({ connected }: Props) {
  if (connected === true) return null;

  return (
    <View style={[styles.banner, connected === false && styles.error]}>
      <Ionicons
        name={connected === false ? "cloud-offline-outline" : "hourglass-outline"}
        size={18}
        color={connected === false ? colors.danger : colors.warning}
      />
      <Text style={styles.text}>
        {connected === false
          ? `Cannot reach API. ${apiHint()}`
          : "Checking API connection…"}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: "row",
    gap: spacing.sm,
    alignItems: "center",
    backgroundColor: colors.surface,
    borderRadius: radius.sm,
    padding: spacing.md,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  error: { borderColor: "#7f1d1d", backgroundColor: "#1c0a0a" },
  text: { flex: 1, color: colors.textMuted, fontSize: 12, lineHeight: 17 },
});
