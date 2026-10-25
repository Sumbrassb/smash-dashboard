"""Cleaning, feature engineering and summary tables for the Smash dashboard."""
import numpy as np
import pandas as pd

# ------------------------------------------------------------------ constants
# Standard bracket placement tiers (seeds 5-6 tie, 7-8 tie, 9-12 tie, ...)
PLACEMENTS = [1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129,
              193, 257, 385, 513, 769, 1025, 1537, 2049]

DATA_START = pd.Timestamp("2023-08-01")
TORONTO_START = pd.Timestamp("2025-08-23")
TORONTO_END = pd.Timestamp("2025-12-18")
ERA_ORDER = ["Paris (2023-25)", "Toronto (2025)", "Paris again (2026)"]

# Hubs used to group nearby venues: name -> (lat, lng, radius in km)
HUBS = {"Paris area": (48.8566, 2.3522, 30),
        "Toronto area": (43.6532, -79.3832, 50),
        "Aix-Marseille": (43.40, 5.42, 40)}

# Life milestones drawn on the timelines (edit here only)
GREY_BAND, ORANGE_BAND = "#8c8c8c", "#E69F00"
MILESTONES = [
    dict(label="Tough<br>studies", start="2024-10-01", end="2025-01-31", color=GREY_BAND, y=1.0),
    dict(label="Toronto<br>PR #10", start=TORONTO_START, end=TORONTO_END, color=ORANGE_BAND, y=1.0),
    dict(label="Travel", start=TORONTO_END, end="2026-01-02", color=GREY_BAND, y=0.80),
    dict(label="Summer", start="2024-07-01", end="2024-08-31", color=GREY_BAND, y=1.0),
    dict(label="Summer", start="2025-07-01", end="2025-08-22", color=GREY_BAND, y=0.80),
    dict(label="Summer", start="2026-07-01", end="2026-08-31", color=GREY_BAND, y=1.0),
]

STAGES = ["Champion", "Runner-up (2nd)", "3rd", "4th", "5th-6th",
          "Outside top 6", "Pools / unfinished"]
TOP6 = STAGES[:5]
SCORE_STATUSES = ["Scored", "Score not reported", "Likely DQ", "Unplayed reset"]


# ------------------------------------------------------------------- features
def seed_tier(seed: pd.Series) -> pd.Series:
    """Seed -> index of the placement tier it falls in (seed 19 -> 8, seed 13 -> 7)."""
    s = pd.to_numeric(seed, errors="coerce")
    tier = np.searchsorted(PLACEMENTS, s.fillna(0), side="right") - 1
    return pd.Series(tier, index=s.index).where(s.notna())


def assign_era(d: pd.Timestamp) -> str:
    if d < TORONTO_START:
        return ERA_ORDER[0]
    return ERA_ORDER[1] if d <= TORONTO_END else ERA_ORDER[2]


def bracket_side(r: str) -> str:
    r = str(r)
    if r.startswith("Winners"):
        return "Winners"
    if r.startswith("Losers"):
        return "Losers"
    return "Grand final" if "Grand" in r else "Pools / other"


def _haversine_km(lat1, lng1, lat2, lng2):
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2)
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def assign_area(df: pd.DataFrame) -> pd.Series:
    """Nearest hub within its radius, computed from coordinates."""
    area = pd.Series("Other / online", index=df.index, dtype="object")
    best = pd.Series(np.inf, index=df.index)
    for name, (lat, lng, radius) in HUBS.items():
        d = _haversine_km(df["lat"], df["lng"], lat, lng)
        hit = (d <= radius) & (d < best)
        area.loc[hit] = name
        best.loc[hit] = d[hit]
    return area


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["won"] = df["won"].astype(str).str.lower().eq("true")
    for c in ["my_seed", "opponent_seed", "num_entrants", "lat", "lng", "my_score", "opponent_score"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # File order is latest set first within an event; keep it as an explicit column.
    df["set_order"] = df.groupby("event_id").cumcount()

    # A 0-0 score is NOT always a DQ: if every set of an event is 0-0, the organizer
    # simply did not report game scores (win/loss is still valid).
    zero = (df["my_score"] + df["opponent_score"]) == 0
    n_ev = df.groupby("event_id")["won"].transform("size")
    zero_ev = zero.groupby(df["event_id"]).transform("sum")
    unreported_event = (zero_ev == n_ev) & (n_ev >= 3)
    df["score_status"] = np.select(
        [~zero, zero & (df["round"] == "Grand Final Reset"), zero & unreported_event],
        ["Scored", "Unplayed reset", "Score not reported"], default="Likely DQ")
    df["is_walkover"] = df["score_status"].isin(["Likely DQ", "Unplayed reset"])

    # Finish per event, from all sets: my own walkover losses (no-shows) are ignored,
    # opponents' no-shows still count as progress. Filters can then never change a finish.
    valid = ~(df["is_walkover"] & ~df["won"])
    last = df[valid].sort_values("set_order").drop_duplicates("event_id")
    stage = pd.Series([stage_of(r, w) for r, w in zip(last["round"], last["won"])], index=last["event_id"])
    df["stage"] = pd.Categorical(df["event_id"].map(stage).fillna("Pools / unfinished"),
                                 categories=STAGES, ordered=True)

    df["year_month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["quarter"] = df["date"].dt.to_period("Q").astype(str)
    df["era"] = pd.Categorical(df["date"].map(assign_era), categories=ERA_ORDER, ordered=True)
    df["side"] = df["round"].map(bracket_side)
    df["area"] = assign_area(df)

    df["my_tier"] = seed_tier(df["my_seed"])
    df["opp_tier"] = seed_tier(df["opponent_seed"])
    df["upset_factor"] = df["my_tier"] - df["opp_tier"]            # >0 underdog, <0 favorite
    df["role"] = np.select([df["upset_factor"] > 0, df["upset_factor"] < 0],
                           ["Underdog", "Favorite"], default="Even")
    df["my_seed_pct"] = df["my_seed"] / df["num_entrants"]          # 0 = top seed
    df["opp_seed_pct"] = df["opponent_seed"] / df["num_entrants"]
    return df


# ----------------------------------------------------------------- statistics
def wilson(k: pd.Series, n: pd.Series, z: float = 1.96):
    """95% Wilson interval for a proportion (honest error bars for small samples)."""
    n = n.astype(float).replace(0, np.nan)
    p = k / n
    d = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return centre - half, centre + half


def summarize(df: pd.DataFrame, by) -> pd.DataFrame:
    """Sets, wins, win rate (%) and 95% interval (%) per group."""
    g = df.groupby(by, observed=True)["won"].agg(sets="size", wins="sum").reset_index()
    g["wr"] = g["wins"] / g["sets"] * 100
    lo, hi = wilson(g["wins"], g["sets"])
    g["lo"], g["hi"] = lo * 100, hi * 100
    return g


# --------------------------------------------------------------- summary tables
def stage_of(round_name: str, won: bool) -> str:
    r = str(round_name)
    if r.startswith("Grand Final"):
        return "Champion" if won else "Runner-up (2nd)"
    if won:
        return "Pools / unfinished"
    return {"Losers Final": "3rd", "Losers Semi-Final": "4th",
            "Losers Quarter-Final": "5th-6th"}.get(
        r, "Outside top 6" if r.startswith("Losers") else "Pools / unfinished")


def event_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per event with at least one set in df (finish comes from clean())."""
    first = df.sort_values("set_order").drop_duplicates("event_id", keep="first").copy()
    first["n_sets"] = first["event_id"].map(df["event_id"].value_counts())
    keep = ["event_id", "tournament", "date", "era", "area", "num_entrants",
            "my_seed", "my_seed_pct", "stage", "n_sets"]
    return first[keep].sort_values("date").reset_index(drop=True)


def rival_table(df: pd.DataFrame, min_sets: int) -> pd.DataFrame:
    t = df.groupby("opponent")["won"].agg(sets="size", wins="sum").reset_index()
    t["losses"] = t["sets"] - t["wins"]
    t["wr"] = t["wins"] / t["sets"] * 100
    return t[t["sets"] >= min_sets].sort_values(["sets", "wr"], ascending=[False, True])


def matchup_table(df: pd.DataFrame, min_sets: int) -> pd.DataFrame:
    d = df[df["opponent_characters"] != "unreported"].copy()
    d["character"] = d["opponent_characters"].str.split(", ")
    t = summarize(d.explode("character"), "character")
    return t[t["sets"] >= min_sets].sort_values("wr")


def venue_table(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["lat", "lng"]).assign(la=lambda x: x["lat"].round(3), lo=lambda x: x["lng"].round(3))
    g = d.groupby(["la", "lo"]).agg(city=("city", lambda s: s.mode().iat[0]), sets=("won", "size"),
                                    wins=("won", "sum"), events=("event_id", "nunique")).reset_index()
    g = g.rename(columns={"la": "lat", "lo": "lng"})
    g["win_rate"] = (g["wins"] / g["sets"] * 100).round(0)
    return g


def era_bounds(full: pd.DataFrame) -> dict:
    day = pd.Timedelta(days=1)
    return {ERA_ORDER[0]: (full["date"].min(), TORONTO_START - day),
            ERA_ORDER[1]: (TORONTO_START, TORONTO_END),
            ERA_ORDER[2]: (TORONTO_END + day, full["date"].max())}


def events_per_month(view: pd.DataFrame, full: pd.DataFrame, start, end) -> pd.DataFrame:
    """Events entered per month in each era, with era spans clipped to the date filter."""
    rows = []
    for era, (a, b) in era_bounds(full).items():
        a, b = max(a, pd.Timestamp(start)), min(b, pd.Timestamp(end))
        months = (b - a).days / 30.44
        n = view.loc[view["era"] == era, "event_id"].nunique()
        if months >= 1 and n:
            rows.append(dict(era=era, events=n, months=round(months, 1), per_month=n / months))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------- data quality
def quality_report(raw: pd.DataFrame, df: pd.DataFrame) -> dict:
    missing = (raw.replace("unreported", np.nan).isna().mean() * 100).round(1)
    missing = missing.rename("% missing").to_frame()
    status = df["score_status"].value_counts()
    checks = pd.DataFrame([
        ("Duplicate set ids", int(raw["set_id"].duplicated().sum())),
        ("Fully duplicated rows", int(raw.duplicated().sum())),
        ("Negative scores", int(((df["my_score"] < 0) | (df["opponent_score"] < 0)).sum())),
        ("Seed below 1", int(((df["my_seed"] < 1) | (df["opponent_seed"] < 1)).sum())),
        ("Seed larger than number of entrants", int((df["my_seed"] > df["num_entrants"]).sum())),
        ("Dates before the 2023-08-01 cutoff", int((df["date"] < DATA_START).sum())),
        ("Sets without a seed", int(df[["my_seed", "opponent_seed"]].isna().any(axis=1).sum())),
        ("0-0 sets in events where no scores were reported", int(status.get("Score not reported", 0))),
        ("0-0 sets inside scored events (likely DQ)", int(status.get("Likely DQ", 0))),
        ("0-0 grand final resets (not played)", int(status.get("Unplayed reset", 0))),
        ("Opponent character not reported", int((raw["opponent_characters"] == "unreported").sum())),
        ("No venue coordinates (online events)", int(df["lat"].isna().sum())),
    ], columns=["Check", "Rows affected"])
    checks["Share of sets (%)"] = (checks["Rows affected"] / len(df) * 100).round(1)
    return {"missing": missing, "checks": checks}