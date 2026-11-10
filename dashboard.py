import streamlit as st
import requests
import os
from dotenv import load_dotenv
import pandas as pd
import plotly.express as px
from collections import Counter
import random


load_dotenv()
API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

@st.cache_data
def get_trending_movies():
    url = f"{BASE_URL}/trending/movie/week?api_key={API_KEY}"
    response = requests.get(url)
    data = response.json()
    return data["results"]

@st.cache_data
def get_genres():
    url = f"{BASE_URL}/genre/movie/list?api_key={API_KEY}"
    response = requests.get(url)
    data = response.json()
    return data["genres"]

@st.cache_data
def search_movies(query):
    url = f"{BASE_URL}/search/movie?api_key={API_KEY}&query={query}"
    response = requests.get(url)
    data = response.json()
    return data["results"]

st.title("Movie Dashboard")

movies = get_trending_movies()
genres = get_genres()

genre_map = {item["id"]: item["name"] for item in genres}

df = pd.DataFrame(movies)

df_clean = df[["title", "vote_average", "popularity", "release_date"]]

df_rated =df_clean[df["vote_average"] > 0.0]

df_sorted =df_rated.sort_values("vote_average", ascending=False)
df_sorted["popularity_rounded"] = df_sorted["popularity"].round(0)
df_sorted["voteaverage_rounded"] = df_sorted["vote_average"].round(1)

all_genre_ids = []

for movie in movies:
    for item in movie["genre_ids"]:
        all_genre_ids.append(item)

genre_counts = Counter(all_genre_ids)
genre_name_counts = {}

for id, count in  genre_counts.items():
    genre_name_counts[genre_map[id]] = count

df_genres = pd.DataFrame(genre_name_counts.items(), columns=["Genre", "Count"])

st.header("Trending Movies Right Now")
fig = px.bar(df_sorted, x="title", y="voteaverage_rounded",title="", labels={"voteaverage_rounded": "Rating", "title": "Movie"})
fig.update_traces(hovertemplate="<b>%{x}</b><br>Rating = %{y}")
fig.update_layout(title=None, margin=dict(t=0))
st.plotly_chart(fig)

st.header("Trending Genres This Week")
fig3 = px.bar(df_genres, x="Genre", y="Count", title="",labels={"Genre": "Genre", "Count": "Number of Movies"})
fig3.update_traces(hovertemplate="<b>%{x}</b><br>Number of Movies = %{y}")
fig3.update_layout(title=None, margin=dict(t=0))

st.plotly_chart(fig3)

query = st.text_input("Enter a movie title to search for:")

if query:
    results = search_movies(query)
    num_results = st.slider("Number of results:", min_value=1, max_value=20, value=5)
    for movie in results[:num_results]:

        col1, col2 = st.columns([1,3])

        with col1:
            if movie["poster_path"]:
             poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
             st.image(poster_url, width = 150)

        with col2:
            st.subheader(movie["title"])
            st.write(f"Rating: {movie['vote_average']} | Released: {movie['release_date']}")
            st.markdown(f"**Overview:** {movie['overview']}")
            st.divider()

