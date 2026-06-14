import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DATA_PATH = "tmdb_cleaned_for_api.csv"

app = FastAPI(
    title="TMDB Movies API",
    description="API for accessing the cleaned TMDB movies dataset",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

df: pd.DataFrame = pd.read_csv(DATA_PATH)


class MovieCreate(BaseModel):
    # fields for a new movie sent to the POST endpoint
    title: str
    budget: float = Field(..., gt=0, description="Budget, $ (must be greater than 0)")
    revenue: float = Field(..., ge=0, description="Revenue, $")
    runtime: float = Field(..., gt=0, description="Runtime, minutes")
    vote_average: float = Field(..., ge=0, le=10, description="Rating, 0-10")
    release_year: int = Field(..., ge=1888, le=2100, description="Release year")
    original_language: str = "en"


@app.get("/")
def root():
    # check if API is running and data is loaded
    return {"status": "ok", "movies_loaded": len(df)}


@app.get("/movies")
def get_movies(
    min_year: int | None = Query(None, description="Minimum release year"),
    min_rating: float | None = Query(None, ge=0, le=10, description="Minimum rating"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return"),
):
    # filter movies by year and rating and limit the number of results
    result = df

    if min_year is not None:
        result = result[result["release_year"] >= min_year]
    if min_rating is not None:
        result = result[result["vote_average"] >= min_rating]

    result = result.head(limit)

    records = result.replace({np.nan: None}).to_dict(orient="records")
    return {"count": len(records), "results": records}


@app.post("/movies", status_code=201)
def create_movie(movie: MovieCreate):
    # add the new movie, compute profit and roi, save to CSV and return it
    global df

    new_record = movie.model_dump()
    new_record["id"] = int(df["id"].max()) + 1
    new_record["profit"] = new_record["revenue"] - new_record["budget"]
    new_record["roi"] = new_record["revenue"] / new_record["budget"]

    df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)

    df.to_csv(DATA_PATH, index=False)

    return new_record
