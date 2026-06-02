import * as Haptics from "expo-haptics";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, radius, spacing } from "../theme";

type Props = {
  mode: "full" | "passenger";
  onChange: (mode: "full" | "passenger") => void;
};

export function ModeToggle({ mode, onChange }: Props) {
  const pick = (m: "full" | "passenger") => {
    Haptics.selectionAsync();
    onChange(m);
  };

  return (
    <View style={styles.row}>
      <Pressable
        style={[styles.btn, mode === "full" && styles.active]}
        onPress={() => pick("full")}
      >
        <Text style={[styles.label, mode === "full" && styles.labelActive]}>Full</Text>
        <Text style={styles.hint}>All route types</Text>
      </Pressable>
      <Pressable
        style={[styles.btn, mode === "passenger" && styles.active]}
        onPress={() => pick("passenger")}
      >
        <Text style={[styles.label, mode === "passenger" && styles.labelActive]}>
          Passenger
        </Text>
        <Text style={styles.hint}>3 big choices</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.lg },
  btn: {
    flex: 1,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
    borderRadius: radius.md,
    borderWidth: 2,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  active: {
    borderColor: colors.brand,
    backgroundColor: "#152a52",
  },
  label: {
    color: colors.textMuted,
    fontSize: 16,
    fontWeight: "800",
    textAlign: "center",
  },
  labelActive: { color: colors.text },
  hint: {
    color: colors.textDim,
    fontSize: 11,
    textAlign: "center",
    marginTop: 2,
  },
});
