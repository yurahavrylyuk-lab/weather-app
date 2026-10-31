# Weather App

Full-stack weather application combining general weather and aviation weather data.

## Structure

- `frontend/` — HTML, CSS and JavaScript frontend
- `backend/` — FastAPI backend

## Weather Data

- Open-Meteo — general weather
- AviationWeather.gov — METAR observations
- Open-Meteo GFS — winds aloft and freezing level

## Local Development

### Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app:app --reload
