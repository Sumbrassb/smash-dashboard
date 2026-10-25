"""Cached wrappers so each aggregation runs once per set of filters."""
import streamlit as st

from . import prep


@st.cache_data(show_spinner=False)
def events(df):
    return prep.event_table(df)


@st.cache_data(show_spinner=False)
def rivals(df, min_sets):
    return prep.rival_table(df, min_sets)


@st.cache_data(show_spinner=False)
def matchups(df, min_sets):
    return prep.matchup_table(df, min_sets)


@st.cache_data(show_spinner=False)
def venues(df):
    return prep.venue_table(df)