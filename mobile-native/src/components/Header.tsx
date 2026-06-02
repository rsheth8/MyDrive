import { StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { BRAND } from "../brand";
import { colors, spacing } from "../theme";

export function Header() {
  return (
    <View style={styles.wrap}>
      <View style={styles.logo}>
        <Ionicons name="shield-checkmark" size={28} color={colors.brand} />
      </View>
      <View style={styles.text}>
        <Text style={styles.title}>{BRAND.name}</Text>
        <Text style={styles.sub}>{BRAND.tagline}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    marginBottom: spacing.lg,
  },
  logo: {
    width: 52,
    height: 52,
    borderRadius: 16,
    backgroundColor: colors.brandGlow,
    borderWidth: 1,
    borderColor: colors.borderFocus,
    alignItems: "center",
    justifyContent: "center",
  },
  text: { flex: 1 },
  title: {
    color: colors.text,
    fontSize: 26,
    fontWeight: "800",
    letterSpacing: -0.5,
  },
  sub: {
    color: colors.textMuted,
    fontSize: 14,
    marginTop: 2,
  },
});
