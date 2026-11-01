from contextlib import asynccontextmanager
from datetime import timedelta
from action_tokens import consume_action_token, create_action_token
import os

import jwt

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
import httpx
from sqlmodel import Session, select

from auth import (
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    normalize_email,
)
from database import create_db_and_tables, get_session
from email_service import (
    send_password_reset_email,
    send_verification_email,
)
from models import EmailRequest, EmailTokenRequest, PasswordResetConfirm, User, UserCreate, UserPublic, UserUpdate

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

    normalized_email = normalize_email(user_data.email)

    existing_email = session.exec(
        select(User).where(User.email == normalized_email)
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    user = User(
        username=user_data.username,
        email=normalized_email,
        email_verified=False,
        hashed_password=hash_password(user_data.password),
        preferred_city=user_data.preferred_city
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    verification_token = create_action_token(
        session,
        user,
        purpose="verify_email",
        expires_in=timedelta(hours=24),
    )

    send_verification_email(
        user.email,
        verification_token,
    )

    return user


@app.post("/api/password-reset/request")
def request_password_reset(
    request: EmailRequest,
    session: Session = Depends(get_session),
):
    normalized_email = normalize_email(request.email)

    user = session.exec(
        select(User).where(User.email == normalized_email)
    ).first()

    if (
        user is not None
        and user.email is not None
        and user.email_verified
        and user.is_active
    ):
        reset_token = create_action_token(
            session,
            user,
            purpose="reset_password",
            expires_in=timedelta(minutes=30),
        )

        send_password_reset_email(
            user.email,
            reset_token,
        )

    return {
        "message": (
            "If a verified account exists for that email, "
            "password reset instructions have been sent"
        )
    }


@app.post("/api/password-reset/confirm")
def confirm_password_reset(
    request: PasswordResetConfirm,
    session: Session = Depends(get_session),
):
    action_token = consume_action_token(
        session,
        request.token,
        purpose="reset_password",
    )

    if action_token is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired password reset token",
        )

    user = session.get(
        User,
        action_token.user_id,
    )

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired password reset token",
        )

    user.hashed_password = hash_password(
        request.new_password
    )

    user.auth_version += 1

    session.add(user)
    session.commit()

    return {
        "message": "Password reset successful"
    }


@app.post("/api/email/resend-verification")
def resend_verification_email(
    request: EmailRequest,
    session: Session = Depends(get_session),
):
    normalized_email = normalize_email(request.email)

    user = session.exec(
        select(User).where(User.email == normalized_email)
    ).first()

    if (
        user is not None
        and user.email is not None
        and not user.email_verified
    ):
        verification_token = create_action_token(
            session,
            user,
            purpose="verify_email",
            expires_in=timedelta(hours=24),
        )

        send_verification_email(
            user.email,
            verification_token,
        )

    return {
        "message": (
            "If an unverified account exists, "
            "a verification email has been sent"
        )
    }


@app.post("/api/email/verify")
def verify_email(
    request: EmailTokenRequest,
    session: Session = Depends(get_session),
):
    action_token = consume_action_token(
        session,
        request.token,
        purpose="verify_email",
    )

    if action_token is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token",
        )

    user = session.get(User, action_token.user_id)

    if user is None or user.email is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token",
        )

    user.email_verified = True

    session.add(user)
    session.commit()

    return {"message": "Email verified"}


@app.post("/api/token")
def login_for_access_token(
    response: Response,
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

    access_token = create_access_token(
        user.username,
        auth_version=user.auth_version,
    )
    refresh_token = create_refresh_token(
        user.username,
        auth_version=user.auth_version,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=os.getenv("VERCEL_ENV") in {"production", "preview"},
        samesite="lax",
        path="/api",
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.post("/api/refresh")
def refresh_access_token(
    request: Request,
    response: Response,
    session: Session = Depends(get_session)
):
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Refresh token required"
        )

    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    try:
        payload = jwt.decode(
            refresh_token,
            secret_key,
            algorithms=[ALGORITHM]
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    username = payload.get("sub")
    auth_version = payload.get("auth_version")

    if not username or type(auth_version) is not int:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    user = session.exec(
        select(User).where(User.username == username)
    ).first()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    if user.auth_version != auth_version:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    new_access_token = create_access_token(
        user.username,
        auth_version=user.auth_version,
    )
    new_refresh_token = create_refresh_token(
        user.username,
        auth_version=user.auth_version,
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=os.getenv("VERCEL_ENV") in {"production", "preview"},
        samesite="lax",
        path="/api",
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/api",
        secure=os.getenv("VERCEL_ENV") in {"production", "preview"},
        httponly=True,
        samesite="lax",
    )

    return {"message": "Logged out"}


@app.get(
    "/api/users/me",
    response_model=UserPublic
)
def read_current_user(
    current_user: User = Depends(get_current_user)
):
    return current_user


@app.patch(
    "/api/users/me",
    response_model=UserPublic
)
def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    current_user.preferred_city = user_data.preferred_city

    session.add(current_user)
    session.commit()
    session.refresh(current_user)

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
