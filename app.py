"""Same player, three settings: a Smash Ultimate data story built from my start.gg results."""
import streamlit as st

from sections import conclusions, data_quality, deep_dives, intro, overview
from utils import cached
from utils.io import load_data
from utils.prep import ERA_ORDER, TOP6, clean

st.set_page_config(page_title="Same player, three settings", layout="wide")


@st.cache_data(show_spinner=False)
def get_data():
    raw = load_data()
    return raw, clean(raw)


raw, full = get_data()

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Filters")
    hide = st.toggle("Hide likely DQs and unplayed resets", True,
                     help="Hides 0-0 sets inside scored events and grand final resets that were not played. "
                          "Events where no scores were reported are kept: those wins and losses are real.",
                     key="f_hide")
    eras = st.multiselect("Period", ERA_ORDER, default=ERA_ORDER, key="f_era")
    areas = st.multiselect("Area", sorted(full["area"].unique()), default=sorted(full["area"].unique()), key="f_area")
    dmin, dmax = full["date"].min().date(), full["date"].max().date()
    rng = st.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax, key="f_dates")
    min_size = st.slider("Minimum event size (entrants)", 0, 200, 0, step=4,
                         help="Raise it to keep only larger tournaments.", key="f_size")

start, end = (rng if isinstance(rng, (tuple, list)) and len(rng) == 2 else (dmin, dmax))
base = full[~full["is_walkover"]] if hide else full
view = base[base["era"].isin(eras) & base["area"].isin(areas) & (base["num_entrants"] >= min_size)
            & (base["date"] >= str(start)) & (base["date"] <= str(end))]
ctx = {"full": full, "all": base, "view": view, "start": start, "end": end}

# ------------------------------------------------------------ title + KPIs
st.title("Same player, three settings")
st.caption("A Smash Ultimate data story from my own tournament results. "
           "Source: start.gg API, public tournament data, since 1 Aug 2023.")

if view.empty:
    st.warning("No sets match the current filters. Widen them in the sidebar.")
else:
    ev = cached.events(view)
    k = st.columns(5)
    wr, wr_all = view["won"].mean() * 100, base["won"].mean() * 100
    k[0].metric("Sets", len(view))
    k[1].metric("Win rate", f"{wr:.1f}%", f"{wr - wr_all:+.1f} pts vs all sets", delta_color="off")
    k[2].metric("Events", view["event_id"].nunique())
    k[3].metric("Top-6 finishes", int(ev["stage"].isin(TOP6).sum()))
    k[4].metric("Events won", int((ev["stage"] == "Champion").sum()))

# ------------------------------------------------------------------ chapters
tabs = st.tabs(["Smash 101", "My story", "Three settings", "Beating expectations",
                "How deep I go", "Rivals & matchups", "Conclusions", "Data quality"])
with tabs[0]:
    intro.render(base)
for tab, fn in zip(tabs[1:6], [overview.render, deep_dives.three_settings, deep_dives.expectations,
                               deep_dives.depth, deep_dives.rivals]):
    with tab:
        if view.empty:
            st.info("Adjust the filters to see this chapter.")
        else:
            fn(ctx)
with tabs[6]:
    conclusions.render(ctx)
with tabs[7]:
    data_quality.render(raw, full)