"""Chapter 1 - hook, context and the two headline charts."""
import streamlit as st

from utils import viz
from utils.prep import events_per_month


def render(ctx):
    view, base, full = ctx["view"], ctx["all"], ctx["full"]
    st.header("My story: am I getting better?")

    wr_all = base["won"].mean() * 100
    rates = events_per_month(base, full, full["date"].min(), full["date"].max()).set_index("era")["per_month"]
    pace = (f" while I went from {rates.iloc[0]:.1f} to {rates.iloc[-1]:.1f} events a month"
            if len(rates) > 1 else "")
    st.markdown(f"**Headline:** my set win rate has stayed near {wr_all:.0f}% since 2023{pace}. "
                "So where is the progress? The next chapters look for it.")

    st.markdown(
        "I arrived in Paris in August 2023 to study, and that is when my competitive Smash "
        "career really started: before that I could hardly reach any tournament. Since then I "
        "have played in Paris, spent four months in Toronto, and come back. "
        "**The question for this dashboard: am I getting better, and how would I even know?**")

    st.subheader("When I played")
    st.markdown("**Headline:** my activity follows my life: slumps when studies or holidays "
                "take over, and a burst in Toronto.")
    c1, c2 = st.columns([1, 2])
    metric = c1.radio("Count", ["Sets", "Events"], horizontal=True, key="ov_metric",
                      help="A set is one match; an event is one tournament bracket.")
    show = c2.toggle("Show my life milestones", True, key="ov_milestones",
                     help="Grey and orange bands mark studies, summers, travel and my Toronto stay.")
    st.plotly_chart(viz.volume_chart(view, metric, show), key="ov_volume")
    st.caption("Chart description: monthly bar chart from August 2023 to October 2026, colored by "
               "period (Paris, Toronto, Paris again). Months with no bar are months with no tournament.")

    st.subheader("Is my win rate going up?")
    st.markdown("**Headline:** not really. Quarter after quarter it moves inside the same band.")
    st.plotly_chart(viz.winrate_trend_chart(view, wr_all, show), key="ov_trend")
    st.caption("Chart description: line of the set win rate per quarter with 95% error bars; bigger dots "
               "mean more sets. The dashed line is my overall win rate. Error bars overlap it almost "
               "everywhere, so quarter-to-quarter changes are mostly noise.")
    st.info("A flat win rate does not mean no progress: tournaments got bigger and I was seeded "
            "higher. The rest of the story tests that.")