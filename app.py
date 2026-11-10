import os
from collections import Counter

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from dotenv import load_dotenv

# Must be the first Streamlit command
st.set_page_config(page_title="Movie Dashboard", layout="wide")

# Use Helvetica everywhere in the app
st.markdown(
    """
    <style>
    html, body, h1, h2, h3, h4, h5, h6, p, li, label, input, textarea,
    [data-testid="stMarkdownContainer"], [data-testid="stMetricValue"],
    [data-testid="stMetricLabel"], [data-baseweb="tab"], [data-baseweb="select"] {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif !important;
    }
    /* Keep Streamlit's icon font so icons show as icons, not words */
    [data-testid="stIconMaterial"], span[class*="material-symbols"] {
        font-family: "Material Symbols Rounded" !important;
    }    </style>
    """,
    unsafe_allow_html=True,
)

load_dotenv()
API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

# Sage green palette (the page colors are set in .streamlit/config.toml)
SAGE = "#7A9E7E"
SAGE_DARK = "#4F6F55"
TEXT = "#2F3E33"


def style_chart(fig):
    """Give every chart the same clean, sage look."""
    fig.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",  # transparent so the page color shows through
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Helvetica Neue, Helvetica, Arial, sans-serif", color=TEXT),
        hoverlabel=dict(bgcolor="white", font_color=TEXT),
    )
    fig.update_xaxes(gridcolor="#E3E8E0")
    fig.update_yaxes(gridcolor="#E3E8E0")
    return fig


def tmdb_get(path, **params):
    """Call the TMDB API and return the JSON response."""
    params["api_key"] = API_KEY
    response = requests.get(f"{BASE_URL}{path}", params=params)
    response.raise_for_status()
    return response.json()


@st.cache_data
def get_trending_movies():
    return tmdb_get("/trending/movie/week")["results"]


@st.cache_data
def get_genres():
    return tmdb_get("/genre/movie/list")["genres"]


@st.cache_data
def search_movies(query):
    return tmdb_get("/search/movie", query=query)["results"]


st.title("Movie Dashboard")
st.caption("This week's trending movies from TMDB")

if not API_KEY:
    st.error("No TMDB_API_KEY found. Put it in a .env file next to app.py.")
    st.stop()

movies = get_trending_movies()
genres = get_genres()
genre_map = {g["id"]: g["name"] for g in genres}

# --- Build the main table ---
df = pd.DataFrame(movies)
df = df[["title", "vote_average", "popularity", "release_date", "genre_ids"]]
df = df[df["vote_average"] > 0].copy()  # drop movies with no ratings yet
df["rating"] = df["vote_average"].round(1)
# Turn each movie's list of genre IDs into a list of genre names
df["genres"] = df["genre_ids"].apply(lambda ids: [genre_map.get(i, "Unknown") for i in ids])

# --- Sidebar filters ---
st.sidebar.header("Filters")
all_genres = sorted({g for genre_list in df["genres"] for g in genre_list})
selected_genres = st.sidebar.multiselect("Genres (leave empty for all)", all_genres)
min_rating = st.sidebar.slider("Minimum rating", min_value=0.0, max_value=10.0, value=0.0, step=0.5)

df_filtered = df[df["rating"] >= min_rating]
if selected_genres:
    # Keep a movie if it has at least one of the selected genres
    has_selected_genre = df_filtered["genres"].apply(
        lambda genre_list: any(g in selected_genres for g in genre_list)
    )
    df_filtered = df_filtered[has_selected_genre]

tab_trends, tab_search = st.tabs(["Trends", "Search"])

# ===================== Trends tab =====================
with tab_trends:
    if df_filtered.empty:
        st.warning("No movies match these filters. Try lowering the rating or picking other genres.")
    else:
        # --- Key stats row ---
        genre_counts = Counter(g for genre_list in df_filtered["genres"] for g in genre_list)
        top_genre = genre_counts.most_common(1)[0][0] if genre_counts else "—"

        c1, c2, c3 = st.columns(3)
        c1.metric("Movies shown", f"{len(df_filtered)} of {len(df)}")
        c2.metric("Average rating", f"{df_filtered['rating'].mean():.1f}")
        c3.metric("Top genre", top_genre)

        # --- Trending movies chart ---
        st.subheader("Ratings")
        df_by_rating = df_filtered.sort_values("rating")
        fig = px.bar(
            df_by_rating,
            x="rating",
            y="title",
            orientation="h",
            labels={"rating": "Rating", "title": ""},
            height=max(400, 25 * len(df_by_rating)),
            color_discrete_sequence=[SAGE],
        )
        fig.update_traces(hovertemplate="<b>%{y}</b><br>Rating = %{x}<extra></extra>")
        st.plotly_chart(style_chart(fig), use_container_width=True)

        # --- Genres and scatter plot side by side ---
        left, right = st.columns(2)

        with left:
            st.subheader("Trending Genres")
            df_genres = pd.DataFrame(genre_counts.items(), columns=["Genre", "Count"])
            df_genres = df_genres.sort_values("Count", ascending=False)
            fig2 = px.bar(
                df_genres,
                x="Genre",
                y="Count",
                labels={"Genre": "", "Count": "Number of Movies"},
                color_discrete_sequence=[SAGE],
            )
            fig2.update_traces(hovertemplate="<b>%{x}</b><br>Number of Movies = %{y}<extra></extra>")
            st.plotly_chart(style_chart(fig2), use_container_width=True)

        with right:
            st.subheader("Popularity vs. Rating")
            fig3 = px.scatter(
                df_filtered,
                x="popularity",
                y="rating",
                hover_name="title",
                labels={"popularity": "Popularity (TMDB score)", "rating": "Rating"},
                color_discrete_sequence=[SAGE_DARK],
            )
            fig3.update_traces(
                marker=dict(size=11, opacity=0.8, line=dict(width=1, color="white")),
                hovertemplate="<b>%{hovertext}</b><br>Popularity = %{x:.0f}<br>Rating = %{y}<extra></extra>",
            )
            st.plotly_chart(style_chart(fig3), use_container_width=True)

# ===================== Search tab =====================
with tab_search:
    query = st.text_input("Search for a movie", placeholder="e.g. Inception")
    num_results = st.slider("Number of results", min_value=1, max_value=20, value=5)

    if query:
        results = search_movies(query)
        if not results:
            st.info("No movies found.")
        for movie in results[:num_results]:
            with st.container(border=True):
                col1, col2 = st.columns([1, 4])
                with col1:
                    if movie.get("poster_path"):
                        st.image(f"https://image.tmdb.org/t/p/w500{movie['poster_path']}", width=150)
                with col2:
                    st.subheader(movie.get("title", "Unknown title"))
                    st.caption(
                        f"Rating: {movie.get('vote_average', 'N/A')}  ·  "
                        f"Released {movie.get('release_date') or 'Unknown'}"
                    )
                    st.write(movie.get("overview") or "No overview available.")