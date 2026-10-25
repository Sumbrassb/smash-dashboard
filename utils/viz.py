"""Chart builders: one consistent look, labelled axes and units, hover tooltips."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .prep import ERA_ORDER, MILESTONES, STAGES, summarize, wilson

BLUE, ORANGE, GREEN, GREY = "#0072B2", "#D55E00", "#009E73", "#6b7280"
ERA_COLORS = {ERA_ORDER[0]: BLUE, ERA_ORDER[1]: "#E69F00", ERA_ORDER[2]: GREEN}
STAGE_COLORS = dict(zip(STAGES, ["#08306b", "#2171b5", "#4292c6", "#6baed6",
                                 "#9ecae1", "#c7c7c7", "#e6e6e6"]))
ROLE_ORDER = ["Favorite", "Even", "Underdog"]


def finish(fig, xt=None, yt=None, height=380, legend=True):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), hovermode="closest",
                      showlegend=legend, legend=dict(orientation="h", y=-0.22, title=None))
    if xt:
        fig.update_xaxes(title_text=xt)
    if yt:
        fig.update_yaxes(title_text=yt)
    return fig


def add_milestones(fig):
    """Shaded life periods (study, Toronto, summers) on a date axis."""
    for m in MILESTONES:
        s, e = pd.Timestamp(m["start"]), pd.Timestamp(m["end"])
        fig.add_shape(type="rect", xref="x", yref="paper", x0=s, x1=e, y0=0, y1=1,
                      fillcolor=m["color"], opacity=0.16, line_width=0, layer="below")
        fig.add_annotation(x=s + (e - s) / 2, y=m["y"], yref="paper", text=m["label"],
                           showarrow=False, yanchor="top", font=dict(size=11))
    return fig


# --------------------------------------------------------------- my story
def volume_chart(df, metric="Sets", milestones=True):
    if metric == "Sets":
        g = df.groupby(["year_month", "era"], observed=True).size().rename("n").reset_index()
        unit, ylab = "sets", "Sets played per month (count)"
    else:
        g = df.groupby(["year_month", "era"], observed=True)["event_id"].nunique().rename("n").reset_index()
        unit, ylab = "events", "Tournament events per month (count)"
    fig = px.bar(g, x="year_month", y="n", color="era", color_discrete_map=ERA_COLORS,
                 category_orders={"era": ERA_ORDER})
    fig.update_traces(hovertemplate="%{x|%b %Y}<br>%{y} " + unit + "<extra>%{fullData.name}</extra>")
    fig.update_xaxes(dtick="M3", tickformat="%b %Y")
    if milestones:
        add_milestones(fig)
    return finish(fig, "Month", ylab, 400)


def winrate_trend_chart(df, baseline, milestones=True):
    q = df.assign(q=df["date"].dt.to_period("Q")).groupby("q")["won"].agg(sets="size", wins="sum").reset_index()
    q["x"] = q["q"].dt.start_time + pd.Timedelta(days=45)
    q["wr"] = q["wins"] / q["sets"] * 100
    lo, hi = wilson(q["wins"], q["sets"])
    q["lo"], q["hi"] = lo * 100, hi * 100
    fig = go.Figure(go.Scatter(
        x=q["x"], y=q["wr"], mode="lines+markers", line=dict(color=BLUE, width=2),
        marker=dict(color=BLUE, size=6 + 1.3 * np.sqrt(q["sets"])),
        error_y=dict(type="data", symmetric=False, array=q["hi"] - q["wr"],
                     arrayminus=q["wr"] - q["lo"], color=GREY),
        customdata=np.c_[q["q"].astype(str), q["sets"], q["lo"], q["hi"]],
        hovertemplate="%{customdata[0]}<br>Win rate %{y:.0f}% (%{customdata[1]} sets)"
                      "<br>95% range %{customdata[2]:.0f}-%{customdata[3]:.0f}%<extra></extra>"))
    fig.add_hline(y=baseline, line_dash="dash", line_color=GREY,
                  annotation_text=f"All sets: {baseline:.0f}%", annotation_position="bottom right")
    if milestones:
        add_milestones(fig)
    fig.update_yaxes(range=[0, 100])
    return finish(fig, "Quarter", "Set win rate (%)", 400, legend=False)


# ------------------------------------------------------------ three settings
def events_per_month_chart(rates):
    fig = px.bar(rates, x="era", y="per_month", color="era", color_discrete_map=ERA_COLORS,
                 text=rates["per_month"].round(1), category_orders={"era": ERA_ORDER},
                 custom_data=["events", "months"])
    fig.update_traces(hovertemplate="%{x}<br>%{y:.1f} events per month<br>"
                                    "%{customdata[0]} events over %{customdata[1]} months<extra></extra>")
    return finish(fig, "Period", "Tournament events per month", 330, legend=False)


def venue_map(venues, zoom="Everywhere"):
    views = {"Everywhere": (35, -40, 1.6), "Paris area": (48.85, 2.38, 9.5),
             "Toronto area": (43.68, -79.5, 8.8), "Aix-Marseille": (43.4, 5.45, 9)}
    lat, lon, z = views[zoom]
    fig = px.scatter_map(venues, lat="lat", lon="lng", size="sets", size_max=34, color="win_rate",
                         color_continuous_scale="Viridis", range_color=[0, 100],
                         custom_data=["city", "events", "sets", "win_rate"],
                         center=dict(lat=lat, lon=lon), zoom=z, map_style="carto-positron")
    fig.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} events, "
                                    "%{customdata[2]} sets<br>Win rate %{customdata[3]:.0f}%<extra></extra>")
    fig.update_layout(height=470, margin=dict(l=0, r=0, t=0, b=0),
                      coloraxis_colorbar=dict(title="Win rate (%)"))
    return fig


# ------------------------------------------------------ beating expectations
def upset_curve(df, cap=6):
    d = df.dropna(subset=["upset_factor"]).assign(gap=lambda x: x["upset_factor"].clip(-cap, cap))
    g = summarize(d, "gap")
    fig = go.Figure(go.Scatter(
        x=g["gap"], y=g["wr"], mode="markers+lines", line=dict(color=GREY, width=1),
        marker=dict(color=BLUE, size=8 + 1.6 * np.sqrt(g["sets"])),
        error_y=dict(type="data", symmetric=False, array=g["hi"] - g["wr"],
                     arrayminus=g["wr"] - g["lo"], color=GREY),
        customdata=np.c_[g["sets"], g["lo"], g["hi"]],
        hovertemplate="Tier gap %{x:+d}<br>Win rate %{y:.0f}% (%{customdata[0]} sets)"
                      "<br>95% range %{customdata[1]:.0f}-%{customdata[2]:.0f}%<extra></extra>"))
    fig.add_hline(y=50, line_dash="dash", line_color=GREY)
    fig.add_vline(x=0, line_dash="dot", line_color=GREY)
    ticks = list(range(-cap, cap + 1))
    fig.update_xaxes(tickvals=ticks, ticktext=[f"≤{t}" if t == -cap else f"≥+{t}" if t == cap else f"{t:+d}" if t else "0" for t in ticks])
    fig.add_annotation(x=0.01, y=1.0, xref="paper", yref="paper", text="◄ I am the favorite",
                       showarrow=False, xanchor="left", yanchor="bottom")
    fig.add_annotation(x=0.99, y=1.0, xref="paper", yref="paper", text="I am the underdog ►",
                       showarrow=False, xanchor="right", yanchor="bottom")
    fig.update_yaxes(range=[0, 100])
    return finish(fig, "Seed tier gap (my tier minus opponent's tier)", "Set win rate (%)", 400, legend=False)


def role_by_era_chart(df):
    g = summarize(df[df["role"].isin(ROLE_ORDER)], ["era", "role"])
    g["up"], g["down"] = g["hi"] - g["wr"], g["wr"] - g["lo"]
    fig = px.bar(g, x="role", y="wr", color="era", barmode="group", color_discrete_map=ERA_COLORS,
                 category_orders={"role": ROLE_ORDER, "era": ERA_ORDER}, error_y="up", error_y_minus="down",
                 custom_data=["sets", "lo", "hi"])
    fig.update_traces(hovertemplate="%{x}, %{fullData.name}<br>Win rate %{y:.0f}% (%{customdata[0]} sets)"
                                    "<br>95% range %{customdata[1]:.0f}-%{customdata[2]:.0f}%<extra></extra>")
    fig.update_yaxes(range=[0, 100])
    return finish(fig, "My seed relative to the opponent's", "Set win rate (%)", 380)


def seed_percentile_chart(df, milestones=True):
    q = df.assign(q=df["date"].dt.to_period("Q")).groupby("q").agg(
        me=("my_seed_pct", "median"), opp=("opp_seed_pct", "median"), sets=("won", "size")).reset_index()
    q["x"] = q["q"].dt.start_time + pd.Timedelta(days=45)
    fig = go.Figure()
    for col, name, color in [("me", "My seed", BLUE), ("opp", "Opponents' seed", ORANGE)]:
        fig.add_trace(go.Scatter(x=q["x"], y=q[col] * 100, mode="lines+markers", name=name,
                                 line=dict(color=color, width=2), customdata=np.c_[q["q"].astype(str), q["sets"]],
                                 hovertemplate=name + "<br>%{customdata[0]}: top %{y:.0f}% of the field"
                                                      " (%{customdata[1]} sets)<extra></extra>"))
    if milestones:
        add_milestones(fig)
    fig.update_yaxes(autorange="reversed")
    return finish(fig, "Quarter", "Median seed position (% of field, top = best)", 400)


# --------------------------------------------------------------- how deep I go
def stage_chart(ev):
    g = ev.groupby(["era", "stage"], observed=True).size().rename("events").reset_index()
    fig = px.bar(g, y="era", x="events", color="stage", orientation="h",
                 color_discrete_map=STAGE_COLORS, category_orders={"stage": STAGES, "era": ERA_ORDER[::-1]},
                 text="events", custom_data=["stage"])
    fig.update_layout(barnorm="percent")
    fig.update_traces(hovertemplate="%{y}<br>%{customdata[0]}: %{text} events<extra></extra>")
    return finish(fig, "Share of events (%)", "Period", 330)


def size_vs_stage_chart(ev):
    rng = np.random.default_rng(42)
    d = ev.copy()
    d["yi"] = d["stage"].map({s: i for i, s in enumerate(STAGES)}).astype(float)
    d["yj"] = d["yi"] + rng.uniform(-0.2, 0.2, len(d))
    fig = px.scatter(d, x="num_entrants", y="yj", color="era", log_x=True, color_discrete_map=ERA_COLORS,
                     category_orders={"era": ERA_ORDER}, custom_data=["tournament", "date", "my_seed", "stage"])
    fig.update_traces(marker=dict(size=9, line=dict(width=1, color="white")),
                      hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]|%d %b %Y}<br>"
                                    "%{x} entrants, my seed %{customdata[2]}<br>Finish: %{customdata[3]}<extra></extra>")
    fig.update_yaxes(tickvals=list(range(len(STAGES))), ticktext=STAGES, autorange="reversed")
    return finish(fig, "Event size (entrants, log scale)", "Where I finished", 420)


# --------------------------------------------------------- rivals & matchups
def rivals_chart(t):
    t = t.sort_values("sets")
    fig = go.Figure()
    fig.add_bar(y=t["opponent"], x=t["wins"], orientation="h", name="My wins", marker_color=BLUE,
                text=t["wins"], hovertemplate="%{y}: %{x} wins<extra></extra>")
    fig.add_bar(y=t["opponent"], x=t["losses"], orientation="h", name="My losses", marker_color=ORANGE,
                text=t["losses"], hovertemplate="%{y}: %{x} losses<extra></extra>")
    fig.update_layout(barmode="stack")
    return finish(fig, "Sets played (count)", "Opponent", max(300, 30 * len(t) + 120))


def matchup_chart(t, baseline):
    fig = go.Figure(go.Bar(
        y=t["character"], x=t["wr"], orientation="h", marker_color=BLUE,
        error_x=dict(type="data", symmetric=False, array=t["hi"] - t["wr"], arrayminus=t["wr"] - t["lo"], color=GREY),
        customdata=np.c_[t["sets"], t["lo"], t["hi"]],
        hovertemplate="vs %{y}<br>Win rate %{x:.0f}% (%{customdata[0]} sets)"
                      "<br>95% range %{customdata[1]:.0f}-%{customdata[2]:.0f}%<extra></extra>"))
    fig.add_vline(x=baseline, line_dash="dash", line_color=GREY,
                  annotation_text=f"All sets: {baseline:.0f}%", annotation_position="top")
    fig.update_xaxes(range=[0, 100])
    return finish(fig, "Set win rate (%)", "Opponent's character", max(320, 26 * len(t) + 120), legend=False)


def status_chart(df):
    g = df.groupby(["era", "score_status"], observed=True).size().rename("sets").reset_index()
    fig = px.bar(g, x="era", y="sets", color="score_status", barmode="stack",
                 category_orders={"era": ERA_ORDER},
                 color_discrete_map={"Scored": BLUE, "Score not reported": "#E69F00",
                                     "Likely DQ": ORANGE, "Unplayed reset": GREY})
    return finish(fig, "Period", "Sets (count)", 330)