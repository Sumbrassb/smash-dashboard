# Same player, three settings: a Smash Ultimate data story

Streamlit data-storytelling dashboard built from my own tournament results on start.gg
(player Sumbra, sets since 1 Aug 2023). Project: EFREI #DataStories2026.

**Question:** am I getting better as a player? **Answer in one line:** my win rate is flat
(~63% in Paris, Toronto and Paris again), but organizers seed me higher and my fields got bigger.

## Story arc
Smash 101 (for newcomers) -> My story (hook, volume, win rate) -> Three settings (Paris/Toronto/map) ->
Beating expectations (seed tiers and upsets) -> How deep I go -> Rivals & matchups -> Conclusions -> Data quality.

## Data
- **Source:** start.gg GraphQL API (public tournament data), pulled with `Get_Data.ipynb`.
- **File:** `data/player_sets.csv` (one row per set, 20 columns). It is small, so it is committed;
  re-run the notebook to refresh it (needs a start.gg token in the `STARTGG_TOKEN` environment variable).
- **Licence:** data belongs to start.gg and the organizers, used under start.gg's API terms for a
  non-commercial student project. Power-ranking graphic: invisinat (UTSmash).

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Structure
```
app.py                 sidebar filters, KPI header, chapter tabs
sections/              intro, overview, deep_dives, conclusions, data_quality
utils/io.py            load_data()
utils/prep.py          cleaning, features (upset factor, seed tiers, eras, finishes), tables, quality checks
utils/viz.py           all chart builders (one consistent style)
utils/cached.py        st.cache_data wrappers
assets/                power-ranking graphic
data/player_sets.csv   dataset
```

## Method notes
- **Seed gap:** seeds map to placement tiers (1, 2, 3, 4, 5, 7, 9, 13, 17, 25, ...); upset factor = tier difference.
- **0-0 scores:** if every set of an event is 0-0 (3+ sets) the organizer did not report scores and the result
  is kept; other 0-0 sets are treated as likely DQs and hidden by default (sidebar toggle).
- **Finishes** are inferred from my last set of each event. **Win rates** carry 95% Wilson intervals.
- Deterministic: no sampling; the only random element (point jitter in one chart) uses a fixed seed (42).

## Limitations
Correlation not causation; small samples (Toronto); seeds are organizers' opinions and the first reported seed
may be a pool seed; only events I entered; finishes are not official placements.