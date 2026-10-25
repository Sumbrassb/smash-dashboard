"""Chapter 7 - data quality, assumptions, ethics and licence."""
import streamlit as st

from utils import viz
from utils.prep import quality_report


def render(raw, df):
    st.header("Data quality and method")
    st.markdown("**Headline:** the data is clean and complete, with one trap: a 0-0 score does not always "
                "mean a DQ.")
    q = quality_report(raw, df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sets (rows)", len(raw))
    c2.metric("Events", df["event_id"].nunique())
    c3.metric("First set", df["date"].min().strftime("%d %b %Y"))
    c4.metric("Last set", df["date"].max().strftime("%d %b %Y"))

    st.subheader("Validation checks")
    st.dataframe(q["checks"], hide_index=True)
    with st.expander("Missing values per column (% of rows)"):
        st.dataframe(q["missing"])
    st.caption("Duplicates, impossible seeds and out-of-range dates are all zero. Missing venue coordinates are "
               "online events. Missing opponent characters are sets with no game-level data.")

    st.subheader("The 0-0 problem")
    st.markdown("A 0-0 score can mean a **DQ** (a player did not show up) or that the **organizer did not report "
                "game scores**. I tell them apart by event: if every set of an event is 0-0 (3 sets or more), "
                "scores were simply not reported and the win or loss is real. A 0-0 inside an event that has "
                "scores is treated as a likely DQ, and a 0-0 grand final reset as not played. "
                "The sidebar toggle hides only those last two.")
    st.plotly_chart(viz.status_chart(df), key="dq_status")
    st.caption("Chart description: stacked bars of sets per period by score status. Most 0-0 sets are in events "
               "with no reported scores.")

    st.subheader("Assumptions")
    st.markdown("""
- **Period boundaries:** Toronto = 23 Aug to 18 Dec 2025 (my stay); Paris before and after.
- **Seed gap:** seeds are mapped to bracket placement tiers (1, 2, 3, 4, 5, 7, 9, 13, 17, 25, ...); the upset
  factor is the tier difference.
- **My character** is Greninja by default (about 99% of my sets); opponent characters are used only when reported.
- **Date** is the event start date, so sets of one event share a date.
- **Win rates** carry 95% Wilson intervals; with fewer than about 20 sets they are wide.
""")

    st.subheader("Ethics, source and licence")
    st.markdown("""
- **Source:** start.gg GraphQL API (public tournament results), pulled with `Get_Data.ipynb`.
- **Privacy:** opponents appear only as public gamertags in aggregate (rivals above a set threshold); the biggest
  upsets table omits opponent names.
- **Licence:** data belongs to start.gg and tournament organizers and is used under start.gg's API terms for a
  non-commercial student project. The power-ranking graphic is by invisinat (UTSmash). The code is mine.
""")