import os

import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
import streamlit as st


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
DATA_PATH = "tmdb_cleaned_for_api.csv"

st.set_page_config(page_title="TMDB Movies Dashboard", page_icon="🎬", layout="wide")

sns.set_theme(style="whitegrid", palette="deep")

st.title("🎬 TMDB Movies - Analytics Dashboard")
st.caption("Exploratory data analysis report and interactive client for the FastAPI REST API")

@st.cache_data(show_spinner=False)
def load_dataset():
    # load cleaned csv exported from the notebook
    df = pd.read_csv(DATA_PATH)

    if "profit" not in df.columns:
        df["profit"] = df["revenue"] - df["budget"]
    if "roi" not in df.columns:
        df["roi"] = df["revenue"] / df["budget"]
    if "release_year" not in df.columns and "release_date" in df.columns:
        df["release_year"] = pd.to_datetime(
            df["release_date"], errors="coerce"
        ).dt.year.astype("Int64")

    return df


@st.cache_data(show_spinner=False)
def fetch_movies(min_year, min_rating, limit):
    response = requests.get(
        f"{API_URL}/movies",
        params={"min_year": min_year, "min_rating": min_rating, "limit": limit},
        timeout=10,
    )
    response.raise_for_status()
    return pd.DataFrame(response.json()["results"])


# load the data once to build some filter options (cached)
all_data = load_dataset()
if "original_language" in all_data.columns:
    lang_options = sorted(all_data["original_language"].dropna().unique())
else:
    lang_options = []

# sidebar filters (used in API Explorer tab)
st.sidebar.header("⚙️ Filters")

# min year is sent to the API, max year is filtered on the client
year_range = st.sidebar.slider("Release year range", 1888, 2024, (2000, 2024))
min_year, max_year = year_range

min_rating = st.sidebar.slider("Minimum rating", 0.0, 10.0, 6.0, step=0.1)
min_votes = st.sidebar.slider("Minimum vote count", 0, 5000, 0, step=50)

# runtime range in minutes
runtime_min, runtime_max = st.sidebar.slider("Runtime, minutes", 0, 360, (0, 360), step=5)

# language filter (empty = all languages)
languages = st.sidebar.multiselect("Original language", lang_options)

# sorting
sort_by = st.sidebar.selectbox(
    "Sort by", ["vote_average", "revenue", "budget", "roi", "release_year"]
)
sort_desc = st.sidebar.radio("Order", ["Descending", "Ascending"], horizontal=True) == "Descending"

limit = st.sidebar.slider("Record limit", 1, 500, 50)


# tabs: statistic report first, then the API tabs
tab_eda, tab_explore, tab_add = st.tabs(
    ["📈 EDA & Analytics", "📊 API Explorer", "➕ Add Movie"]
)

# tab 1
with tab_eda:
    data = load_dataset()

    st.header("Exploratory Analysis of the TMDB Movies Dataset")

    st.markdown(
        """
This is an exploratory data analysis of the
[TMDB (The Movie Database)](https://www.themoviedb.org/) movies dataset. The raw dataset
has about **1.44 million** movies of all kinds - feature films, shorts, trailers, and
unreleased projects. The goal here is to look only at commercial feature films and see
how budget, revenue, rating, and release year are connected.
        """
    )

    # top metrics
    median_roi = data["roi"].median()
    share_profitable = (data["profit"] > 0).mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Films analysed", f"{len(data):,}")
    c2.metric("Median ROI", f"{median_roi:.2f}x")
    c3.metric("Profitable films", f"{share_profitable:.0%}")
    c4.metric(
        "Years covered",
        f"{int(data['release_year'].min())}-{int(data['release_year'].max())}",
    )

    st.divider()

    st.subheader("Descriptive Statistics (raw dataset)")
    st.markdown(
        """
Before cleaning, here are the basic stats on the full **1,440,254** raw movies:

| Field | Mean | Median | Std |
|---|---|---|---|
| `budget` | 233,547 | 0 | 5,121,386 |
| `revenue` | 616,978 | 0 | 19,653,942 |
| `runtime` | 43.7 | 15.0 | 60.6 |
| `vote_average` | 1.54 | 0.0 | 2.85 |

The median is **0** for budget, revenue and rating, which means more than half of the raw
rows have no money data and no votes at all. The mean is also much bigger than the median
for budget and revenue, so a few huge movies pull the average way up (the data is
right-skewed). `runtime` and `vote_average` are less skewed. This is already a sign that
most of the raw data is empty and needs cleaning.
        """
    )

    st.subheader("Data Quality Check (raw dataset)")
    st.markdown(
        """
Then I looked for broken or empty rows in the raw data:

| Problem | Count |
|---|---|
| Missing values (NaN) | 0 |
| `runtime` < 0 | 1 |
| `revenue` <= 0 | 1,415,663 |
| `budget` <= 0 | 1,356,977 |

There are no literal `NaN` values, but the zeros are the real problem: about **98%** of
rows have `revenue <= 0` and **94%** have `budget <= 0`. These zeros are just missing data
stored as 0, so they have to be removed before any money analysis. Of course it was possible 
to analyse them separately but I wanted to focus on the real commercial movies, so I dropped 
all rows with zero or negative budget/revenue.
        """
    )

    st.divider()

    st.subheader("Data Cleaning")
    st.markdown(
        """
I cleaned the data in **two passes**:

1. **First pass - drop missing and zero values.** Most rows store missing money data as
   zeros (`budget = 0`, `revenue = 0`) or have a non-positive `runtime`. These are not
   real values, so I removed them.

2. **Second pass - drop fake and short entries.** After the first pass there were still
   bad rows: **\\$1-\\$10 placeholder budgets**, **1-5 minute runtimes** (trailers, not
   real movies), and **unrated films** with `vote_average = 0`. So I used a stricter
   filter:

   ```python
   budget > 10000 and revenue > 10000 and runtime >= 40
   and vote_average > 0 and vote_count >= 10
   ```

This keeps only real commercial movies with believable money figures and enough votes.
I also added two columns: **profit** (`revenue - budget`) and **ROI**
(`revenue / budget`).

> ⚠️ **Note on bias.** After this filter the data leans toward big releases that publish
> their finances, so the results apply to those films, not to all movies.
        """
    )

    st.divider()

    st.subheader("Cleaned Data Summary")
    st.caption("Summary statistics of the key columns after cleaning")
    st.dataframe(
        data[["budget", "revenue", "runtime", "profit", "roi", "release_year"]].describe(),
        use_container_width=True,
    )

    st.divider()
    st.markdown("### Distributions of the Key Variables")

    # budget distribution
    st.markdown(
        "**Budget distribution.** On a log scale most movies sit in the few-million-dollar "
        "range, with a long tail of expensive blockbusters on the right."
    )
    fig_b, ax_b = plt.subplots(figsize=(11, 5))
    sns.histplot(data["budget"], bins=50, log_scale=True, color="steelblue", ax=ax_b)
    ax_b.set_title("Budget Distribution")
    ax_b.set_xlabel("Budget, $ (log scale)")
    ax_b.set_ylabel("Number of Films")
    fig_b.tight_layout()
    st.pyplot(fig_b)

    # revenue boxplot
    st.markdown(
        "**Revenue.** The boxplot (log scale) shows the median and the middle 50% of "
        "revenue, plus how far the big earners stretch the upper range."
    )
    fig_rv, ax_rv = plt.subplots(figsize=(11, 3.5))
    sns.boxplot(x=data["revenue"], color="lightcoral", ax=ax_rv)
    ax_rv.set_xscale("log")
    ax_rv.set_title("Box Office Revenue")
    ax_rv.set_xlabel("Revenue, $ (log scale)")
    fig_rv.tight_layout()
    st.pyplot(fig_rv)

    # rating distribution
    st.markdown(
        "**Ratings.** After cleaning, the rating distribution no longer has the fake spike "
        "at 0 (from unrated films) and looks like a normal bell curve centered around "
        "**6-7**. This is a good sign that the cleaned data behaves like a normal set of "
        "rated movies."
    )
    fig_vr, ax_vr = plt.subplots(figsize=(11, 5))
    sns.histplot(data["vote_average"], bins=40, kde=True, color="seagreen", ax=ax_vr)
    ax_vr.set_title("Distribution of Audience Ratings")
    ax_vr.set_xlabel("Rating (vote_average)")
    ax_vr.set_ylabel("Number of Films")
    fig_vr.tight_layout()
    st.pyplot(fig_vr)

    # runtime vs rating
    st.markdown(
        "**Runtime vs rating.** Duration plotted against rating. There is no strong link - "
        "longer movies are not automatically rated higher."
    )
    runtime_sample = data.sample(n=min(len(data), 5000), random_state=42)
    fig_rr, ax_rr = plt.subplots(figsize=(11, 5))
    sns.scatterplot(data=runtime_sample, x="runtime", y="vote_average",
                    alpha=0.3, s=15, ax=ax_rr)
    ax_rr.set_title("Runtime and Rating")
    ax_rr.set_xlabel("Duration, minutes")
    ax_rr.set_ylabel("Rating (vote_average)")
    fig_rr.tight_layout()
    st.pyplot(fig_rr)

    st.divider()
    st.markdown("### Relationships and Trends")

    # plot 1: budget vs revenue
    st.subheader("1. Bigger Budgets Usually Mean Bigger Revenue")
    st.markdown(
        """
Both axes use a log scale. Budget and revenue clearly go up together: spend more, usually
earn more. The dashed line is the break-even line (`revenue = budget`) - points above it
made a profit, points below lost money, and most points are above. The colours also show
that the cloud shifts up and to the right over the decades, so both budgets and revenues
grew over time.
        """
    )

    plot_df = data.dropna(subset=["budget", "revenue", "release_year"]).copy()
    plot_df["decade"] = (
        (plot_df["release_year"].astype(int) // 10 * 10).astype(str) + "s"
    )
    sample = plot_df.sample(n=min(len(plot_df), 6000), random_state=42)

    fig1, ax1 = plt.subplots(figsize=(11, 6))
    sns.scatterplot(
        data=sample, x="budget", y="revenue",
        hue="decade", hue_order=sorted(sample["decade"].unique()),
        palette="viridis", alpha=0.5, s=18, ax=ax1,
    )
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    lims = [sample["budget"].min(), sample["budget"].max()]
    ax1.plot(lims, lims, color="red", linestyle="--", linewidth=1,
             label="Break-even (revenue = budget)")
    ax1.set_title("Revenue vs. Budget by Decade")
    ax1.set_xlabel("Budget, $ (log scale)")
    ax1.set_ylabel("Revenue, $ (log scale)")
    ax1.legend(title="Decade", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig1.tight_layout()
    st.pyplot(fig1)

    # plot 2: budget/revenue over time
    st.subheader("2. Budgets and Revenues Grow Over Time")
    st.markdown(
        """
Grouping by release year (only years with at least 20 movies, to avoid noise), both the
average budget and average revenue keep rising over time. This is mostly inflation plus
the shift toward big franchise movies. Revenue stays above budget on average, so the
industry makes money overall.
        """
    )

    yearly = (
        data.dropna(subset=["release_year"])
        .groupby("release_year")
        .agg(mean_budget=("budget", "mean"),
             mean_revenue=("revenue", "mean"),
             n_movies=("id", "count"))
        .query("n_movies >= 20")
        .reset_index()
    )

    fig2, ax2 = plt.subplots(figsize=(11, 5))
    sns.lineplot(data=yearly, x="release_year", y="mean_budget",
                 label="Average Budget", linewidth=2, ax=ax2)
    sns.lineplot(data=yearly, x="release_year", y="mean_revenue",
                 label="Average Revenue", linewidth=2, ax=ax2)
    ax2.set_title("Trend of Average Budget and Revenue by Release Year")
    ax2.set_xlabel("Release Year")
    ax2.set_ylabel("Amount, $")
    ax2.legend(title="Metric")
    fig2.tight_layout()
    st.pyplot(fig2)

    # plot 3: roi by rating
    st.subheader("3. Higher-Rated Films Earn More")
    st.markdown(
        """
The median ROI goes up as the rating goes up. I use the **median** instead of the mean
because ROI has huge outliers (cheap films with thousand times returns) that would break
the mean. So better-rated films tend to make their money back more efficiently.
        """
    )

    rating_bins = [0, 4, 5, 6, 7, 8, 10]
    rating_labels = ["<4", "4-5", "5-6", "6-7", "7-8", "8+"]
    roi_data = data.copy()
    roi_data["rating_band"] = pd.cut(
        roi_data["vote_average"], bins=rating_bins, labels=rating_labels
    )
    roi_by_rating = (
        roi_data.groupby("rating_band", observed=True)["roi"]
        .median()
        .reset_index()
    )

    fig3, ax3 = plt.subplots(figsize=(10, 5))
    sns.barplot(data=roi_by_rating, x="rating_band", y="roi",
                color="steelblue", ax=ax3)
    ax3.set_title("Median ROI by Rating Band")
    ax3.set_xlabel("Rating Band (vote_average)")
    ax3.set_ylabel("Median ROI (revenue / budget)")
    fig3.tight_layout()
    st.pyplot(fig3)

    # plot 4: profit of long vs short films
    st.subheader("4. Longer Movies Tend to Make More Profit")
    st.markdown(
        """
Splitting movies at the 2-hour mark and comparing **profit** (outliers hidden so the
boxes stay readable): longer movies usually have a higher median profit. They are often
the big-budget films that also bring in the most money.
        """
    )

    length_data = data.copy()
    length_data["length_group"] = (length_data["runtime"] > 120).map(
        {True: "Longer than 2 hours", False: "2 hours or shorter"}
    )
    fig5, ax5 = plt.subplots(figsize=(10, 5))
    sns.boxplot(data=length_data, x="length_group", y="profit", showfliers=False, ax=ax5)
    ax5.set_title("Profit Distribution: Long vs. Short Films")
    ax5.set_xlabel("Runtime Group")
    ax5.set_ylabel("Profit, $")
    fig5.tight_layout()
    st.pyplot(fig5)

    st.divider()
    st.subheader("Hypothesis Testing")
    st.markdown(
        "Finally I checked two hypotheses on the cleaned data. The numbers below are "
        "calculated live from the dataset."
    )

    # hypothesis 1: blockbuster ROI vs mid-budget ROI
    st.markdown(
        "**H1 - Do blockbusters have a lower median ROI than mid-budget films?** "
        "Idea: very big budgets grow faster than the extra money they bring in, so the "
        "return on each dollar should be smaller."
    )
    blockbusters = data[data["budget"] > 100_000_000]
    mid_budget = data[(data["budget"] >= 10_000_000) & (data["budget"] <= 100_000_000)]
    roi_block = blockbusters["roi"].median()
    roi_mid = mid_budget["roi"].median()

    h1a, h1b = st.columns(2)
    h1a.metric(f"Blockbusters >$100M (n={len(blockbusters):,})", f"{roi_block:.2f}x ROI")
    h1b.metric(f"Mid-budget $10-100M (n={len(mid_budget):,})", f"{roi_mid:.2f}x ROI")
    if roi_block < roi_mid:
        st.success("✅ Confirmed: blockbusters have a lower median ROI, so bigger budgets "
                   "are less efficient per dollar.")
    else:
        st.info("❌ Rejected: blockbusters' median ROI is not lower.")

    # hypothesis 2: rating-popularity correlation by language
    st.markdown(
        "**H2 - Is rating more correlated with popularity for English films?** "
        "Idea: English-language movies target a global mass audience, where quality and "
        "popularity may line up more closely than for other languages."
    )
    if "popularity" in data.columns:
        en_films = data[data["original_language"] == "en"]
        other_films = data[data["original_language"] != "en"]
        corr_en = en_films["vote_average"].corr(en_films["popularity"])
        corr_other = other_films["vote_average"].corr(other_films["popularity"])

        h2a, h2b = st.columns(2)
        h2a.metric(f"English films (n={len(en_films):,})", f"r = {corr_en:.3f}")
        h2b.metric(f"Other languages (n={len(other_films):,})", f"r = {corr_other:.3f}")
        if corr_en > corr_other:
            st.success("✅ Confirmed: rating and popularity are more correlated for "
                       "English-language films.")
        else:
            st.info("❌ Rejected: the correlation for English films is not higher.")
    else:
        st.warning("The `popularity` column is not available, so H2 cannot be checked.")

    st.divider()
    st.subheader("Conclusions")
    st.markdown(
        """
- The raw data was **mostly empty** (over 90% of rows had zero budget/revenue), so heavy
  two-pass cleaning was needed before anything useful could be measured.
- **Budget is strongly linked to revenue** - they rise together across the whole range.
- Budgets and revenues have **grown over the decades** (inflation + franchise movies).
- **Higher-rated films have higher ROI** - they earn their money back better.
- **Longer movies tend to make more profit**, since they are usually the big-budget films.
- Both hypotheses I set up were actually **not supported** by this sample (see the
  Hypothesis Testing section): blockbusters did not have a lower median ROI, and English
  films did not have a higher rating popularity correlation.
- The cleaned data mostly covers **big commercial films that publish their finances**, so
  keep that bias in mind.
        """
    )

# tab 2
with tab_explore:
    st.subheader("Live data from the API")
    st.caption("Adjust the filters in the sidebar to query the FastAPI backend.")

    try:
        movies = fetch_movies(min_year, min_rating, limit)
    except requests.exceptions.RequestException as exc:
        st.error(f"Failed to fetch data from the API ({API_URL}). "
                 f"Make sure the server is running.\n\n{exc}")
        st.stop()

    # apply the extra filters on the data returned by the API
    if not movies.empty:
        if "release_year" in movies.columns:
            movies = movies[movies["release_year"] <= max_year]
        if "vote_count" in movies.columns:
            movies = movies[movies["vote_count"] >= min_votes]
        if "runtime" in movies.columns:
            movies = movies[movies["runtime"].between(runtime_min, runtime_max)]
        if languages and "original_language" in movies.columns:
            movies = movies[movies["original_language"].isin(languages)]
        if sort_by in movies.columns:
            movies = movies.sort_values(sort_by, ascending=not sort_desc)

    if movies.empty:
        st.warning("No movies found for the selected filters.")
    else:
        st.subheader(f"Movies found: {len(movies)}")
        st.dataframe(movies, use_container_width=True)

        # draw chart only if budget and revenue columns exist
        chart_cols = {"budget", "revenue"}
        if chart_cols.issubset(movies.columns):
            st.subheader("Revenue vs Budget")
            plot_data = movies.dropna(subset=["budget", "revenue"])
            st.scatter_chart(plot_data, x="budget", y="revenue", color="vote_average"
                             if "vote_average" in plot_data.columns else None)

# tab 3
with tab_add:
    st.subheader("Add a new movie")
    with st.form("add_movie_form"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Title", "Untitled")
            budget = st.number_input("Budget, $", min_value=1.0, value=1_000_000.0, step=100_000.0)
            revenue = st.number_input("Revenue, $", min_value=0.0, value=5_000_000.0, step=100_000.0)
        with col2:
            runtime = st.number_input("Runtime, minutes", min_value=1.0, value=120.0, step=1.0)
            vote_average = st.number_input("Rating", min_value=0.0, max_value=10.0, value=7.0, step=0.1)
            release_year = st.number_input("Release year", min_value=1888, max_value=2100, value=2024, step=1)

        submitted = st.form_submit_button("Create movie")

        if submitted:
            payload = {
                "title": title,
                "budget": budget,
                "revenue": revenue,
                "runtime": runtime,
                "vote_average": vote_average,
                "release_year": int(release_year),
            }
            try:
                response = requests.post(f"{API_URL}/movies", json=payload, timeout=10)
                response.raise_for_status()
                created = response.json()
                st.success(
                    f"Movie \"{created['title']}\" added! "
                    f"profit = ${created['profit']:,.0f}, ROI = {created['roi']:.2f}"
                )
                # clear cache so the new movie shows up in the table
                st.cache_data.clear()
            except requests.exceptions.RequestException as exc:
                detail = ""
                if exc.response is not None:
                    detail = f"\n\nServer response: {exc.response.text}"
                st.error(f"Failed to add movie.{detail}")
