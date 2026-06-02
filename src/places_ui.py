from __future__ import annotations

import streamlit as st

from src.places import PlaceSuggestion, search_places


def _pick_suggestions(field: str, query: str, limit: int = 6) -> list[dict]:
    if len(query.strip()) < 2:
        return []
    return search_places(query, limit=limit)


def render_place_suggestions(
    field: str,
    query: str,
    *,
    coords_key: str,
    label_key: str,
) -> None:
    """
    Show tappable suggestion chips under a From/To field.
    Sets session state for address text and resolved coordinates.
    """
    suggestions = _pick_suggestions(field, query)
    if not suggestions:
        return

    st.caption("Suggestions")
    cols = st.columns(3)
    for i, raw in enumerate(suggestions):
        s = PlaceSuggestion(**{k: raw[k] for k in ("id", "label", "subtitle", "lat", "lon", "source")})
        with cols[i % 3]:
            if st.button(
                s.label,
                key=f"sugg_{field}_{s.id}",
                help=s.subtitle,
                use_container_width=True,
            ):
                st.session_state[label_key] = s.label
                st.session_state[coords_key] = (s.lat, s.lon)
                st.session_state[f"{field}_resolved_label"] = s.label
                st.rerun()
