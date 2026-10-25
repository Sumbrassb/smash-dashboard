"""Chapters 2-5 - three settings, expectations, depth of runs, rivals and matchups."""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from utils import cached, viz
from utils.prep import ERA_ORDER, TOP6, events_per_month, summarize

IMG = Path(__file__).resolve().parent.parent / "assets" / "utsmash_winter2025.jpg"


def _pct(x):
    return "n/a" if pd.isna(x) else f"{x:.0f}%"


# -------------------------------------------------------------- chapter 2
def three_settings(ctx):
    view, full = ctx["view"], ctx["full"]
    st.header("Three settings: Paris, Toronto, Paris again")
    rates = events_per_month(view, full, ctx["start"], ctx["end"]).set_index("era")
    wr = view.groupby("era", observed=True)["won"].mean() * 100
    P, T = ERA_ORDER[0], ERA_ORDER[1]
    if P in rates.index and T in rates.index:
        st.markdown(f"**Headline:** in Toronto I entered {rates.loc[T, 'per_month']:.1f} events a month, "
                    f"{rates.loc[T, 'per_month'] / rates.loc[P, 'per_month']:.1f}x my early Paris pace, "
                    f"and my win rate barely moved ({_pct(wr[T])} vs {_pct(wr[P])}).")
    else:
        st.markdown("**Headline:** same player, different settings. Select several periods in the "
                    "sidebar to compare them.")

    ev = cached.events(view)
    cols = st.columns(len(ERA_ORDER))
    for col, era in zip(cols, ERA_ORDER):
        d, e = view[view["era"] == era], ev[ev["era"] == era]
        with col:
            st.subheader(era)
            if d.empty:
                st.caption("No sets with the current filters.")
                continue
            g = summarize(d.assign(all="all"), "all").iloc[0]
            st.metric("Sets", len(d))
            st.metric("Win rate", f"{g['wr']:.0f}%", help=f"95% range {g['lo']:.0f}-{g['hi']:.0f}%")
            st.metric("Median event size", f"{e['num_entrants'].median():.0f} entrants")
            st.metric("Top-6 finishes", f"{e['stage'].isin(TOP6).mean() * 100:.0f}% of events")
    st.caption("Small multiples: the same four numbers for each period. Win-rate hover shows the 95% range.")

    st.subheader("How often I played")
    if not rates.empty:
        st.plotly_chart(viz.events_per_month_chart(rates.reset_index()), key="dd_rates")
        st.caption("Chart description: three bars, one per period, showing tournament events entered per "
                   "month. The Toronto bar is the tallest.")

    st.subheader("Toronto, Sept to Dec 2025")
    c1, c2 = st.columns([3, 2])
    if IMG.exists():
        c1.image(str(IMG), caption="Graphic: invisinat, UTSmash Winter 2025 Power Rankings "
                                   "(Sept to Dec 2025). Shown for illustration; Nintendo characters.")
    else:
        c1.warning("Add the power-ranking graphic as assets/utsmash_winter2025.jpg.")
    c2.markdown(
        "In Toronto I found different players and a different playstyle than in France, and "
        "plenty of free weekly tournaments. The UTSmash power ranking for Sept to Dec 2025 "
        "placed me **10th**.")
    c2.caption("Image description: a gym-themed illustration with a scoreboard listing the top ten "
               "Toronto players; Sumbra is 10th. Smash characters play sports around the court.")

    st.subheader("Where I played")
    zoom = st.radio("Zoom to", ["Everywhere", "Paris area", "Toronto area", "Aix-Marseille"],
                    horizontal=True, key="dd_zoom")
    st.plotly_chart(viz.venue_map(cached.venues(view), zoom), key="dd_map")
    st.caption("Chart description: map of tournament venues. Bubble size is the number of sets, color is "
               "the win rate (dark purple low, yellow high). Hover for city, events and sets.")


# -------------------------------------------------------------- chapter 3
def expectations(ctx):
    view = ctx["view"]
    d = view.dropna(subset=["upset_factor"])
    st.header("Beating expectations")
    fav, und = d[d["role"] == "Favorite"], d[d["role"] == "Underdog"]
    st.markdown(f"**Headline:** seeds predict my results well: I win {_pct(fav['won'].mean() * 100)} of "
                f"sets as the favorite and {_pct(und['won'].mean() * 100)} as the underdog.")

    scored = d[d["won"] & (d["upset_factor"] > 0)]
    suffered = d[~d["won"] & (d["upset_factor"] < 0)]
    c1, c2, c3 = st.columns(3)
    c1.metric("Upsets I scored", len(scored), help="Wins against a better-seeded player.")
    c2.metric("Upsets against me", len(suffered), help="Losses to a worse-seeded player.")
    c3.metric("Biggest upset", f"+{int(scored['upset_factor'].max())}" if len(scored) else "-",
              help="Largest seed tier gap I overcame.")

    st.subheader("Does the seed gap predict the result?")
    st.plotly_chart(viz.upset_curve(d), key="ex_curve")
    st.caption("Chart description: win rate for each seed tier gap, from favorite (left) to underdog (right). "
               "The line falls from about 85-95% when I am a clear favorite to about 20-30% as a clear underdog.")

    st.subheader("Did that change between periods?")
    st.plotly_chart(viz.role_by_era_chart(d), key="ex_role")
    st.caption("Chart description: grouped bars of win rate as favorite, even and underdog for each period, "
               "with 95% error bars. Bars overlap across periods, so I cannot claim a real change.")

    st.subheader("Am I seeded higher, and do I face stronger fields?")
    by = d.groupby("era", observed=True)[["my_seed_pct", "opp_seed_pct"]].median() * 100
    if len(by) > 1:
        a, b = by.iloc[0], by.iloc[-1]
        st.markdown(f"**Headline:** my median seed moved from the top {a['my_seed_pct']:.0f}% to the top "
                    f"{b['my_seed_pct']:.0f}% of the field; my opponents' from the top "
                    f"{a['opp_seed_pct']:.0f}% to {b['opp_seed_pct']:.0f}%.")
    st.plotly_chart(viz.seed_percentile_chart(d, ctx.get("milestones", True)), key="ex_seed")
    st.caption("Chart description: median seed position per quarter for me and for my opponents, as a share "
               "of the field (top of the chart is the best seed). Seeds are organizers' opinions, not results.")

    st.subheader("My biggest upsets")
    top = scored.nlargest(8, "upset_factor")[["date", "tournament", "round", "my_seed", "opponent_seed", "upset_factor"]]
    st.dataframe(top.rename(columns={"my_seed": "My seed", "opponent_seed": "Opponent seed",
                                     "upset_factor": "Upset", "date": "Date", "tournament": "Tournament",
                                     "round": "Round"}), hide_index=True)


# -------------------------------------------------------------- chapter 4
def depth(ctx):
    view = ctx["view"]
    ev = cached.events(view)
    st.header("How deep do I go?")
    top6 = ev["stage"].isin(TOP6)
    st.markdown(f"**Headline:** I finished in the top 6 in {top6.sum()} of {len(ev)} events "
                f"({top6.mean() * 100:.0f}%) and won {int((ev['stage'] == 'Champion').sum())}.")
    share = ev.groupby("era", observed=True).agg(top6=("stage", lambda x: x.isin(TOP6).mean() * 100),
                                                 size=("num_entrants", "median"))
    if len(share) > 1:
        parts = ", ".join(f"{e}: {r.top6:.0f}% (median field {r.size:.0f})" for e, r in share.iterrows())
        st.markdown(f"Top-6 share by period: {parts}. Fields get bigger, so the same finish is harder.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Events entered", len(ev))
    c2.metric("Top-6 finishes", int(top6.sum()))
    c3.metric("Events won", int((ev["stage"] == "Champion").sum()))

    st.subheader("Where my runs end, by period")
    st.plotly_chart(viz.stage_chart(ev), key="dp_stage")
    st.caption("Chart description: one horizontal 100% bar per period split by finishing stage, from champion "
               "(dark blue) to outside the top 6 (grey). Finish is inferred from my last counted set.")

    st.subheader("Results against event size")
    st.plotly_chart(viz.size_vs_stage_chart(ev), key="dp_size")
    st.caption("Chart description: each dot is an event, placed by number of entrants (log scale) and my finish. "
               "Deep runs happen at every size; dots are slightly shifted vertically so they do not overlap.")

    won = ev[ev["stage"] == "Champion"][["date", "tournament", "num_entrants", "my_seed"]]
    with st.expander("Events I won"):
        st.dataframe(won.rename(columns={"date": "Date", "tournament": "Tournament",
                                         "num_entrants": "Entrants", "my_seed": "My seed"}), hide_index=True)
    st.caption("Method: the last counted set of an event decides the finish (Grand Final = 1st or 2nd, Losers "
               "Final = 3rd, Semi-Final = 4th, Quarter-Final = 5th-6th). Pool or round formats are grouped apart.")


# -------------------------------------------------------------- chapter 5
def rivals(ctx):
    view = ctx["view"]
    st.header("Rivals and matchups")
    base_wr = view["won"].mean() * 100

    st.subheader("Who I meet most")
    min_sets = st.slider("Minimum sets against the same player", 3, 10, 5, key="rv_min",
                         help="Only public gamertags with at least this many sets are shown.")
    r = cached.rivals(view, min_sets).head(12)
    if r.empty:
        st.info("No opponent reaches that many sets with the current filters.")
    else:
        worst = r[r["sets"] >= min_sets].sort_values("wr").iloc[0]
        st.markdown(f"**Headline:** my toughest regular rival is {worst['opponent']} "
                    f"({int(worst['wins'])}-{int(worst['losses'])}).")
        st.plotly_chart(viz.rivals_chart(r), key="rv_chart")
        st.caption("Chart description: stacked horizontal bars of my wins (blue) and losses (orange) against "
                   "my most frequent opponents. Opponents are shown by public gamertag, only above the threshold.")

    st.subheader("Which characters give me trouble?")
    mu_min = st.slider("Minimum sets against a character", 3, 20, 8, key="rv_mu",
                       help="Matchup (MU) = my character against theirs. Few sets means a very wide error bar.")
    m = cached.matchups(view, mu_min)
    if m.empty:
        st.info("No character reaches that many sets with the current filters.")
    else:
        lo, hi = m.iloc[0], m.iloc[-1]
        st.markdown(f"**Headline:** my best matchup is vs {hi['character']} ({hi['wr']:.0f}%) and my hardest "
                    f"is vs {lo['character']} ({lo['wr']:.0f}%), but error bars are wide.")
        st.plotly_chart(viz.matchup_chart(m, base_wr), key="rv_mu_chart")
        st.caption("Chart description: win rate against each opponent character with 95% error bars; the dashed "
                   "line is my overall win rate. Only sets with reported game data are used (about 99% of scored sets).")