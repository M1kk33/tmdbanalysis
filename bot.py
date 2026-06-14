# telegram bot

import os
import random

import requests
import telebot
from telebot import types


BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# menu buttons
BTN_INFO = "📊 Project Info"
BTN_TOP = "🏆 Top 5 Movies"
BTN_RANDOM = "🎲 Random Movie"


def main_menu() -> types.ReplyKeyboardMarkup:
    # reply keyboard
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(BTN_INFO)
    markup.row(BTN_TOP, BTN_RANDOM)
    return markup


def fetch_movies(params: dict | None = None) -> list[dict]:
    response = requests.get(f"{API_URL}/movies", params=params or {}, timeout=10)
    response.raise_for_status()
    return response.json().get("results", [])


def format_movie(movie: dict) -> str:
    # movie data
    title = movie.get("title", "Unknown title")
    year = movie.get("release_year", "-")
    rating = movie.get("vote_average")
    runtime = movie.get("runtime")
    budget = movie.get("budget")
    revenue = movie.get("revenue")

    lines = [f"🎬 *{title}* ({year})"]
    if rating is not None:
        lines.append(f"⭐ Rating: *{rating:.1f}* / 10")
    if runtime is not None:
        lines.append(f"⏱ Runtime: {int(runtime)} min")
    if budget is not None:
        lines.append(f"💰 Budget: ${budget:,.0f}")
    if revenue is not None:
        lines.append(f"💵 Revenue: ${revenue:,.0f}")
    return "\n".join(lines)


@bot.message_handler(commands=["start"]) # start message
def handle_start(message):
    text = (
        "👋 *Welcome to the TMDB Movies bot!*\n\n"
        "I'm a Telegram client for our movie-analytics API. "
        "Use the menu below to explore the project.\n\n"
        "Choose an option to get started 👇"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu())


@bot.message_handler(func=lambda m: m.text == BTN_INFO) # project info
def handle_info(message):
    text = (
        "📊 *TMDB Movies - Project Overview*\n\n"
        "A student project about data analysis and full-stack development "
        "on the [TMDB](https://www.themoviedb.org/) movies dataset.\n\n"
        "*The process:*\n"
        "- 🧹 Two-pass cleaning of ~1.44M raw records down to credible "
        "commercial feature films\n"
        "- 📈 Descriptive statistics and visual graphs for better visualization\n"
        "- ⚙️ A *FastAPI* REST backend serving the cleaned data\n"
        "- 🖥 A *Streamlit* dashboard and this *Telegram bot* as API clients\n\n"
        "*Key fields:* `budget`, `revenue`, `runtime`, `vote_average`, "
        "`profit`, `roi`, `release_year`.\n\n"
        "🌐 *Full analysis and dashboard:* https://xevara.space"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu(),
                     disable_web_page_preview=True)


@bot.message_handler(func=lambda m: m.text == BTN_TOP) # top 5 movies by rating
def handle_top(message):
    try:
        # get a lot of well-rated movies, then sort them by rating to take the top 5
        movies = fetch_movies({"min_rating": 7.5, "limit": 500})
    except requests.RequestException:
        bot.send_message(message.chat.id, api_error_text(), reply_markup=main_menu())
        return

    if not movies:
        bot.send_message(message.chat.id, "🤷 No movies returned by the API.",
                         reply_markup=main_menu())
        return

    top5 = sorted(
        movies,
        key=lambda m: m.get("vote_average") or 0,
        reverse=True,
    )[:5]

    blocks = ["🏆 *Top 5 Movies by Rating*\n"]
    for rank, movie in enumerate(top5, start=1):
        blocks.append(f"*{rank}.* {format_movie(movie)}")
    bot.send_message(message.chat.id, "\n\n".join(blocks), reply_markup=main_menu())


@bot.message_handler(func=lambda m: m.text == BTN_RANDOM) # random movie
def handle_random(message):
    try:
        movies = fetch_movies({"limit": 500})
    except requests.RequestException:
        bot.send_message(message.chat.id, api_error_text(), reply_markup=main_menu())
        return

    if not movies:
        bot.send_message(message.chat.id, "🤷 No movies returned by the API.",
                         reply_markup=main_menu())
        return

    movie = random.choice(movies)
    text = "🎲 *Your random pick:*\n\n" + format_movie(movie)
    bot.send_message(message.chat.id, text, reply_markup=main_menu())


@bot.message_handler(func=lambda m: True) # if user sends something else
def handle_fallback(message):
    bot.send_message(
        message.chat.id,
        "🤔 I didn't get that. Please use the menu below.",
        reply_markup=main_menu(),
    )


def api_error_text() -> str:
    """Friendly message shown when the API is unreachable."""
    return (
        "⚠️ *Could not reach the API.*\n\n"
        f"Make sure the FastAPI server is running at `{API_URL}` and try again."
    )


if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
