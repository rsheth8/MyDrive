import { useCallback, useRef, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { searchPlaces, PlaceSuggestion } from "../api";
import { colors, radius, spacing } from "../theme";

type Props = {
  label: string;
  placeholder: string;
  value: string;
  onChangeText: (text: string) => void;
  onSelect: (place: PlaceSuggestion) => void;
};

export function PlaceAutocomplete({
  label,
  placeholder,
  value,
  onChangeText,
  onSelect,
}: Props) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<PlaceSuggestion[]>([]);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSearch = useCallback(
    (q: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (q.trim().length < 2) {
        setItems([]);
        setOpen(false);
        return;
      }
      debounceRef.current = setTimeout(async () => {
        setLoading(true);
        try {
          const suggestions = await searchPlaces(q);
          setItems(suggestions);
          setOpen(suggestions.length > 0);
        } catch {
          setItems([]);
          setOpen(false);
        } finally {
          setLoading(false);
        }
      }, 280);
    },
    []
  );

  const handleChange = (text: string) => {
    onChangeText(text);
    runSearch(text);
  };

  const pick = (place: PlaceSuggestion) => {
    onChangeText(place.label);
    onSelect(place);
    setOpen(false);
    setItems([]);
  };

  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.inputWrap}>
        <TextInput
          style={styles.input}
          placeholder={placeholder}
          placeholderTextColor={colors.textDim}
          value={value}
          onChangeText={handleChange}
          onFocus={() => value.trim().length >= 2 && runSearch(value)}
          autoCapitalize="words"
          autoCorrect={false}
        />
        {loading && (
          <ActivityIndicator size="small" color={colors.brand} style={styles.spinner} />
        )}
      </View>
      {open && items.length > 0 && (
        <View style={styles.list}>
          {items.map((item) => (
            <Pressable key={item.id} style={styles.item} onPress={() => pick(item)}>
              <View style={styles.row}>
                <Text style={styles.itemTitle} numberOfLines={1}>
                  {item.label}
                </Text>
                {item.source === "local" && <Text style={styles.badge}>Popular</Text>}
              </View>
              <Text style={styles.itemSub} numberOfLines={2}>
                {item.subtitle}
              </Text>
            </Pressable>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: spacing.sm, zIndex: 10 },
  label: {
    color: colors.textMuted,
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 6,
  },
  inputWrap: { position: "relative" },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.lg,
    paddingRight: 40,
    color: colors.text,
    fontSize: 16,
    borderWidth: 1,
    borderColor: colors.border,
  },
  spinner: { position: "absolute", right: 14, top: 16 },
  list: {
    marginTop: 4,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderFocus,
    overflow: "hidden",
    maxHeight: 220,
  },
  item: {
    padding: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.sm,
  },
  itemTitle: { flex: 1, color: colors.text, fontWeight: "700", fontSize: 15 },
  badge: {
    color: colors.brand,
    fontSize: 10,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  itemSub: { color: colors.textMuted, fontSize: 12, marginTop: 4 },
});
