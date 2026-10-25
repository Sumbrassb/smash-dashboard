"""Chapter 6 - insights, implications and next steps (numbers computed from the data)."""
import streamlit as st

from utils import cached
from utils.prep import ERA_ORDER, TOP6, events_per_month, summarize


def render(ctx):
    base, full = ctx["all"], ctx["full"]
    d = base.dropna(subset=["upset_factor"])
    ev = cached.events(base)
    era = summarize(base, "era").set_index("era")
    by = d.groupby("era", observed=True)[["my_seed_pct", "opp_seed_pct"]].median() * 100
    role = d.groupby("role")["won"].mean() * 100
    top6 = ev.groupby("era", observed=True)["stage"].apply(lambda x: x.isin(TOP6).mean() * 100)
    size = ev.groupby("era", observed=True)["num_entrants"].median()
    rates = events_per_month(base, full, full["date"].min(), full["date"].max()).set_index("era")["per_month"]

    st.header("What I learned")
    st.markdown("**Headline:** I did not win more, but organizers seed me higher and my fields got bigger, "
                "in three different places.")

    st.subheader("Key insights")
    st.markdown(f"""
1. **My win rate is flat.** {era['wr'].iloc[0]:.0f}% in Paris, {era['wr'].get(ERA_ORDER[1], float('nan')):.0f}% in Toronto,
   {era['wr'].iloc[-1]:.0f}% back in Paris; the 95% ranges overlap almost completely.
2. **Seeds predict results.** I win {role.get('Favorite', float('nan')):.0f}% as the favorite and
   {role.get('Underdog', float('nan')):.0f}% as the underdog, a gap I can measure with the upset factor.
3. **Organizers rate me higher over time.** My median seed went from the top {by['my_seed_pct'].iloc[0]:.0f}% to the
   top {by['my_seed_pct'].iloc[-1]:.0f}% of the field, while opponents' seeds moved from
   {by['opp_seed_pct'].iloc[0]:.0f}% to {by['opp_seed_pct'].iloc[-1]:.0f}%.
4. **I reach deep runs, but fields grew.** {int(ev['stage'].isin(TOP6).sum())} top-6 finishes and
   {int((ev['stage'] == 'Champion').sum())} event wins in {len(ev)} events. My top-6 share was
   {top6.iloc[0]:.0f}% in Paris early and {top6.iloc[-1]:.0f}% in 2026, while the median field went from
   {size.iloc[0]:.0f} to {size.iloc[-1]:.0f} entrants.
5. **My environment changed my rhythm, not my results.** I entered {rates.iloc[0]:.1f} events a month at first
   and {rates.max():.1f} at my busiest ({rates.idxmax()}).
""")
    st.success("Progress is not visible in the win rate alone. It shows up when results are read "
               "against the seed, the size of the field and the number of events.")

    st.subheader("Implications and next steps")
    st.markdown("""
- **Train the underdog games.** Converting upsets is where the biggest gap is; the matchup chart shows which
  characters to practice against.
- **Track rivals.** A few opponents explain a large share of my losses and are worth studying.
- **Add the missing pieces to the data.** Final placement from the API, phase names (pools vs bracket seeds)
  and the strength of each field would make the comparison fairer.
- **Compare with peers.** The same pipeline works for any player id; a second player would show whether a
  flat win rate is normal at a given seed.
""")

    st.subheader("Limits of this analysis")
    st.warning("""
- **Correlation, not causation.** I can show that seeds, event size and results moved together, not why.
- **Small samples.** Toronto has far fewer sets than Paris; error bars show how uncertain each number is.
- **Seeds are opinions** of organizers, and the first reported seed can be a pool seed rather than a bracket seed.
- **One player, one source.** Only events I entered and that start.gg recorded are included.
- **Finishes are inferred** from my last counted set, not read from official placements.
""")