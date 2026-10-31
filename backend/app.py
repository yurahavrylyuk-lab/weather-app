from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
import httpx
from sqlmodel import Session, select

from auth import authenticate_user, create_access_token, get_current_user, hash_password
from database import create_db_and_tables, get_session
from models import User, UserCreate, UserPublic

from aviation import (
    fetch_nearby_metars,
    select_nearest_metar,
    haversine_distance_km,
    build_metar_summary,
    agl_ft_to_msl_m,
    fetch_current_wind_profile,
    build_agl_winds,
    build_freezing_level
)
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
def root():
    return {"message": "Weather API is running"}


@app.post(
    "/api/register",
    response_model=UserPublic,
    status_code=201
)
def register_user(
    user_data: UserCreate,
    session: Session = Depends(get_session)
):
    existing_user = session.exec(
        select(User).where(User.username == user_data.username)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Username already registered"
        )

    user = User(
        username=user_data.username,
        hashed_password=hash_password(user_data.password)
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


@app.post("/api/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    user = authenticate_user(
        session,
        form_data.username,
        form_data.password
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(user.username)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get(
    "/api/users/me",
    response_model=UserPublic
)
def read_current_user(
    current_user: User = Depends(get_current_user)
):
    return current_user


@app.get("/api/weather")
def get_weather(city: str):

    # STEP 1: Convert city name into coordinates

    geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"

    geocoding_params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json"
    }

    geocoding_response = httpx.get(
        geocoding_url,
        params=geocoding_params
    )

    geocoding_response.raise_for_status()

    geocoding_data = geocoding_response.json()

    results = geocoding_data.get("results")

    if not results:
        raise HTTPException(
            status_code=404,
            detail="City not found"
        )

    location = results[0]

    latitude = location["latitude"]
    longitude = location["longitude"]
    terrain_elevation_m = location.get("elevation")

    wind_levels_agl_ft = [
        1000,
        2000,
        3000,
        5000
    ]

    wind_target_altitudes_msl = {}

    if terrain_elevation_m is not None:
        for agl_ft in wind_levels_agl_ft:
            wind_target_altitudes_msl[agl_ft] = agl_ft_to_msl_m(
                agl_ft,
                terrain_elevation_m
            )

    winds_aloft = None
    freezing_level = None

    try:
        wind_profile = fetch_current_wind_profile(
            latitude,
            longitude
        )

        winds_aloft = build_agl_winds(
            wind_profile,
            wind_target_altitudes_msl
        )

        freezing_level = build_freezing_level(
            wind_profile
        )

    except httpx.HTTPError:
        pass

    if terrain_elevation_m is not None:
        wind_target_altitudes_msl = {
            1000: agl_ft_to_msl_m(
                1000,
                terrain_elevation_m
            ),
            2000: agl_ft_to_msl_m(
                2000,
                terrain_elevation_m
            ),
            3000: agl_ft_to_msl_m(
                3000,
                terrain_elevation_m
            ),
            5000: agl_ft_to_msl_m(
                5000,
                terrain_elevation_m
            )
        }

    metar_reports = []

    try:
        metar_reports = fetch_nearby_metars(
            latitude,
            longitude
        )
    except httpx.HTTPError:
        pass

    nearest_metar = select_nearest_metar(
        metar_reports,
        latitude,
        longitude
    )

    metar_distance_km = None

    if nearest_metar:
        metar_distance_km = haversine_distance_km(
            latitude,
            longitude,
            nearest_metar["lat"],
            nearest_metar["lon"]
        )

    metar_data = None

    if nearest_metar:
        metar_data = build_metar_summary(nearest_metar)
        metar_data["distance_km"] = round(
            metar_distance_km,
            1
        )

    # STEP 2: Use coordinates to request current weather

    weather_url = "https://api.open-meteo.com/v1/forecast"

    weather_params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "weather_code,"
            "wind_speed_10m"
        ),
        "timezone": "auto"
    }

    weather_response = httpx.get(
        weather_url,
        params=weather_params
    )

    weather_response.raise_for_status()

    weather_data = weather_response.json()

    current = weather_data["current"]


    # STEP 3: Return only the information our frontend needs

    return {
      "city": location["name"],
      "country": location.get("country"),
      "latitude": latitude,
      "longitude": longitude,
      "temperature": current["temperature_2m"],
      "apparent_temperature": current["apparent_temperature"],
      "humidity": current["relative_humidity_2m"],
      "wind_speed": current["wind_speed_10m"],
      "weather_code": current["weather_code"],
      "metar": metar_data,
      "winds_aloft": winds_aloft,
      "freezing_level": freezing_level
  }
