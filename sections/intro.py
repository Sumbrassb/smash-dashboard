"""Smash 101: how a tournament works, for readers who have never seen one."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.prep import PLACEMENTS, seed_tier

# ---------------------------------------------------------------- toy bracket
# id: (round name as start.gg would print it, x, y)
MATCHES = {
    "W1a": ("Winners Quarter-Final", 0, 7), "W1b": ("Winners Quarter-Final", 0, 5),
    "W1c": ("Winners Quarter-Final", 0, 3), "W1d": ("Winners Quarter-Final", 0, 1),
    "WSF1": ("Winners Semi-Final", 1, 6), "WSF2": ("Winners Semi-Final", 1, 2),
    "WF": ("Winners Final", 2, 4),
    "L1a": ("Losers Round 1", 0.5, -1), "L1b": ("Losers Round 1", 0.5, -3),
    "L2a": ("Losers Quarter-Final", 1.5, -1), "L2b": ("Losers Quarter-Final", 1.5, -3),
    "L3": ("Losers Semi-Final", 2.5, -2),
    "LF": ("Losers Final", 3.5, -2),
    "GF": ("Grand Final", 4.5, 1),
}
WIN_EDGES = [("W1a", "WSF1"), ("W1b", "WSF1"), ("W1c", "WSF2"), ("W1d", "WSF2"),
             ("WSF1", "WF"), ("WSF2", "WF"), ("WF", "GF"),
             ("L1a", "L2a"), ("L1b", "L2b"), ("L2a", "L3"), ("L2b", "L3"),
             ("L3", "LF"), ("LF", "GF")]
DROP_EDGES = [("W1a", "L1a"), ("W1b", "L1a"), ("W1c", "L1b"), ("W1d", "L1b"),
              ("WSF1", "L2b"), ("WSF2", "L2a"), ("WF", "LF")]

SCENARIOS = {
    "Win every set": [("W1a", "W"), ("WSF1", "W"), ("WF", "W"), ("GF", "W")],
    "Lose once, fight back": [("W1a", "W"), ("WSF1", "W"), ("WF", "L"), ("LF", "W"), ("GF", "W")],
    "Lose the first set, climb back": [("W1a", "L"), ("L1a", "W"), ("L2a", "W"),
                                       ("L3", "W"), ("LF", "W"), ("GF", "W")],
    "Lose twice": [("W1a", "W"), ("WSF1", "L"), ("L2b", "L")],
}
WON, LOST, IDLE, PATH = "#1b7f3b", "#b3261e", "#9aa0a6", "#3b6fd4"


def _line(fig, a, b, color, width, dash=None):
    (_, xa, ya), (_, xb, yb) = MATCHES[a], MATCHES[b]
    fig.add_trace(go.Scatter(x=[xa, xb], y=[ya, yb], mode="lines", hoverinfo="skip",
                             showlegend=False, line=dict(color=color, width=width, dash=dash)))


def bracket_figure(steps: list) -> go.Figure:
    result = dict(steps)
    path_pairs = {(steps[i][0], steps[i + 1][0]) for i in range(len(steps) - 1)}
    fig = go.Figure()
    for a, b in WIN_EDGES:
        _line(fig, a, b, IDLE, 1)
    for a, b in DROP_EDGES:
        _line(fig, a, b, IDLE, 1, "dot")
    for a, b in path_pairs:
        _line(fig, a, b, PATH, 4)

    ids = list(MATCHES)
    fig.add_trace(go.Scatter(
        x=[MATCHES[i][1] for i in ids], y=[MATCHES[i][2] for i in ids],
        mode="markers+text", showlegend=False,
        text=[result.get(i, "") for i in ids], textfont=dict(color="white", size=14),
        marker=dict(size=30, color=[WON if result.get(i) == "W" else LOST if result.get(i) == "L"
                                    else IDLE for i in ids], line=dict(width=1, color="white")),
        customdata=[[MATCHES[i][0], {"W": "you won", "L": "you lost"}.get(result.get(i), "not played")]
                    for i in ids],
        hovertemplate="%{customdata[0]}<br>%{customdata[1]}<extra></extra>"))
    for txt, x, y in [("Winners bracket", -0.35, 8), ("Losers bracket", -0.35, -4.3),
                      ("Grand final", 4.5, 2.1)]:
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False, xanchor="left")
    fig.update_xaxes(visible=False, range=[-0.5, 5.1])
    fig.update_yaxes(visible=False, range=[-4.8, 8.6])
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=10, b=0))
    return fig


def _path_text(steps) -> str:
    parts = [f"**{MATCHES[m][0]}** ({'won' if r == 'W' else 'lost'})" for m, r in steps]
    losses = sum(r == "L" for _, r in steps)
    end = ("eliminated after a second loss" if losses == 2
           else "champion" if steps[-1] == ("GF", "W") else "")
    return f"{len(steps)} sets played, {losses} loss(es), {end}.  \n" + " → ".join(parts)


# ------------------------------------------------------------------- glossary
GLOSSARY = [
    ("Set", "A match between two players, usually first to win 2 games (best of 3). "
            "Scores look like 2-0 or 2-1. Finals are sometimes best of 5."),
    ("Game", "One fight on one stage, until a player loses all their lives (stocks)."),
    ("Character and main", "Every player picks a fighter. Your main is the one you play most. "
                           "Mine is Greninja."),
    ("Matchup (MU)", "Your character against the opponent's character. Some matchups are "
                     "much harder than others, so players talk about them a lot."),
    ("Seeding", "Before the event, the organizer ranks every entrant from 1 (expected best) "
                "to last, using past results. Seeds decide who meets whom in the first rounds."),
    ("Pools", "Some events start with small groups before the main bracket. Your seed can "
              "differ between pools and bracket, a limitation of my data."),
    ("Round names", "Early rounds are numbered (Winners Round 1, 2, 3). The last rounds are "
                    "named from the end: Quarter-Final, Semi-Final, Final."),
    ("Upset", "Beating a player seeded better than you. The bigger the seed gap, the bigger "
              "the upset (see the calculator below)."),
    ("DQ", "Disqualification, usually because a player did not show up. It is recorded as a "
           "0-0 set, but 0-0 can also mean the organizer did not report game scores. The sidebar "
           "can hide likely DQs."),
    ("Tournament organizer (TO)", "The person who runs the event and sets the seeds."),
    ("Power ranking (PR)", "A community list of the best players of a region over a season."),
]


def _glossary():
    left, right = st.columns(2)
    for i, (term, text) in enumerate(GLOSSARY):
        (left if i % 2 == 0 else right).markdown(f"**{term}**  \n{text}")


def _upset_calculator(df=None):
    c1, c2 = st.columns(2)
    me = c1.number_input("Your seed", 1, 2000, 19, help="1 is the best seed.")
    opp = c2.number_input("Opponent's seed", 1, 2000, 13)
    t_me = int(seed_tier(pd.Series([me])).iloc[0])
    t_opp = int(seed_tier(pd.Series([opp])).iloc[0])
    uf = t_me - t_opp
    st.caption(f"Seed {me} sits in the tier starting at seed {PLACEMENTS[t_me]}; "
               f"seed {opp} in the tier starting at seed {PLACEMENTS[t_opp]}.")
    if uf > 0:
        st.success(f"You are the underdog. Winning would be a **+{uf} upset**.")
    elif uf < 0:
        st.info(f"You are the favorite by {-uf} tier(s). Losing would be a **+{-uf} upset against you**.")
    else:
        st.warning("Same tier: an even match, no upset possible.")
    if df is not None and len(df):
        same = df[df["upset_factor"] == uf]
        if len(same) >= 5:
            st.caption(f"In my own data, at a gap of {uf:+d} I won {same['won'].mean() * 100:.0f}% "
                       f"of {len(same)} sets.")
        else:
            st.caption(f"In my own data, only {len(same)} sets had a gap of {uf:+d}: too few to say.")
    st.caption("Tiers: " + ", ".join(str(p) for p in PLACEMENTS[:12]) + ", … "
               "A gap of 6 seeds near the top is huge, near the bottom it is almost nothing.")


def render(df=None):
    st.header("Smash 101")
    st.markdown("**In short:** a Smash tournament is a bracket of one-on-one sets where "
                "you are out after two losses, and seeds tell you who is expected to win.")
    st.markdown(
        "I'm Sumbra, a *Super Smash Bros. Ultimate* player. Everything in this dashboard comes "
        "from my own tournament results on start.gg since August 2023. If you have never seen "
        "a tournament, this page is all you need.")

    st.subheader("The double-elimination bracket")
    st.markdown("**Headline:** you can lose once and still win the tournament, but the road "
                "back is longer.")
    choice = st.radio("Follow one player through an 8-player bracket:", list(SCENARIOS), horizontal=True)
    steps = SCENARIOS[choice]
    st.plotly_chart(bracket_figure(steps))
    st.markdown(_path_text(steps))
    st.caption("Chart description: a double-elimination bracket with a winners side on top and a "
               "losers side below. Circles marked W or L show the selected player's path; solid "
               "lines are wins, dotted lines send losers to the losers bracket.")

    st.subheader("Words you will meet")
    _glossary()

    st.subheader("How big is an upset?")
    st.markdown("**Headline:** an upset is measured in seeding tiers, not raw seed numbers.")
    _upset_calculator(df)