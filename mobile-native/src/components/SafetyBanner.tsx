import { StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, radius, spacing } from "../theme";

type Props = { passenger: boolean };

export function SafetyBanner({ passenger }: Props) {
  return (
    <View style={styles.banner}>
      <Ionicons name="hand-left-outline" size={20} color={colors.warning} />
      <Text style={styles.text}>
        {passenger
          ? "Passenger picks a style, then opens Maps. Driver keeps eyes on the road."
          : "Park before you drive. Plan here, navigate in Apple or Google Maps."}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: "row",
    gap: spacing.md,
    alignItems: "flex-start",
    backgroundColor: colors.warningBg,
    borderWidth: 1,
    borderColor: "#854d0e",
    borderRadius: radius.md,
    padding: spacing.lg,
    marginBottom: spacing.lg,
  },
  text: {
    flex: 1,
    color: "#fde68a",
    fontSize: 14,
    lineHeight: 20,
  },
});
