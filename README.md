# TMDB Movies — analysis, API, dashboard and a Telegram bot

A learning project built around the [TMDB](https://www.themoviedb.org/) movie dataset. First I cleaned and analysed the data in a notebook. Then I put the clean data behind a small REST API and added two ways to use it: a Streamlit dashboard and a Telegram bot.

## How it works

There is one backend and two clients that connect to it over HTTP.

- `main.py` — the API (FastAPI). It loads the clean CSV file into memory when it starts and gives you a few endpoints to read movies and add new ones.
- `app.py` — the dashboard (Streamlit). It has filters in the sidebar, a sortable table, a budget/revenue chart, and a form to add a movie.
- `bot.py` — the Telegram bot (pyTelegramBotAPI). A small menu with buttons: short project info, the top 5 movies by rating, and a random movie.

Both clients send requests to the API at `http://127.0.0.1:8000` on your computer, or `http://api:8000` when everything runs in Docker.

## What is in the repo

| File | What it is |
|------|------------|
| `TMDB_EDA_English.ipynb` | The notebook: statistics, data cleaning, charts, and a few tests |
| `main.py` | FastAPI backend |
| `app.py` | Streamlit dashboard (uses the API) |
| `bot.py` | Telegram bot (uses the API) |
| `tmdb_cleaned_for_api.csv` | Clean dataset exported from the notebook |
| `TMDB_movie_dataset_v11.csv` | Raw source data (about 1.44M rows). Not in the repo — too big |
| `requirements.txt` | Dependencies |
| `Dockerfile` / `docker-compose.yml` | Docker setup for the API, dashboard, bot and Caddy |
| `Caddyfile` | Reverse proxy config (domain and HTTPS) |
| `.env.example` | Template for `BOT_TOKEN` and `API_URL` |

## What it does

The notebook does the analysis. It cleans the data in two steps (it removes empty and zero values, trailers and teasers, and movies with no rating). It also adds three new columns from the raw data: `profit`, `roi` and `release_year`. At the end it compares ROI for movies with different budgets, and looks at how rating and popularity are connected for each language.

The API gives you the clean data. You can filter the list of movies, or send a new movie with `POST`. When you add a movie, the API calculates `profit` and `roi` for you and saves the new row to the CSV file.

The dashboard and the bot are just two simple clients for this API. One is for the browser, one is for Telegram.

## Run it on your computer

You need Python 3.10 or newer.

Create a virtual environment and install the dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The clean file `tmdb_cleaned_for_api.csv` is already in the repo, so you can run everything right away. If you want to make it again, run all the cells in `TMDB_EDA_English.ipynb` — the last cell exports the CSV again. For that you need the raw file `TMDB_movie_dataset_v11.csv`, which is not included.

The backend and the two clients run in separate terminals.

**Backend:**

```powershell
uvicorn main:app --reload
```

API: `http://127.0.0.1:8000`. Docs: `/docs`.

**Dashboard:**

```powershell
streamlit run app.py
```

It opens at `http://localhost:8501`.

**Telegram bot:**

Copy `.env.example` to `.env` and add a token from [@BotFather](https://t.me/BotFather):

```
BOT_TOKEN="put it here"
API_URL=http://127.0.0.1:8000
```

The bot reads both values from the environment. On PowerShell you can also set the token for the current session:

```powershell
$env:BOT_TOKEN = "put it here"
python bot.py
```

Then open the bot in Telegram and press **Start** (@tmdbanalyticsbot).

Start the backend first — the dashboard and the bot send requests to it as soon as they start.

## Deploy with Docker + Caddy

On a real server, all four services (`api`, `frontend`, `bot`, `caddy`) run together with Docker Compose. Caddy works as a reverse proxy and gets the HTTPS certificate for you.

You need a Linux server with a public IP, a domain with an `A` record that points to it, and Docker with the Compose plugin:

```bash
curl -fsSL https://get.docker.com | sh
docker compose version
```

Then clone the repo:

```bash
git clone <repo url> tmdb-project
cd tmdb-project
```

Put your domain in the `Caddyfile`:

```
your-domain.com {
    reverse_proxy 127.0.0.1:8501
}
```

Create the `.env` file. Note that here `API_URL` uses the internal service name, not localhost:

```bash
cp .env.example .env
```

```
BOT_TOKEN="put it here"
API_URL=http://api:8000
```

Build and start everything:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f caddy
```

When Caddy has the certificate, the dashboard is at `https://your-domain.com`, the bot is online in Telegram, and the API stays internal on `api:8000`. You can run it without Caddy, but then you only get plain HTTP.

## API endpoints

| Method | Path | What it does |
|--------|------|--------------|
| `GET` | `/` | Health check — returns the number of loaded movies |
| `GET` | `/movies` | List movies. Query params: `min_year`, `min_rating`, `limit` (default 50) |
| `POST` | `/movies` | Add a movie. The API calculates `profit`/`roi` and saves the row to the CSV |

## Some notes

`POST /movies` rewrites the file `tmdb_cleaned_for_api.csv`. With `--reload` on, this write can restart the server, so in production it is better to run `uvicorn` without `--reload`.

The clean dataset has mostly big commercial movies with public budget and revenue numbers. This is a kind of bias, so be careful when you read the results.
