from aviation import (
    select_nearest_metar,
    calculate_ceiling_ft_agl,
    build_metar_summary,
    decode_weather_string,
    feet_to_meters,
    meters_to_feet,
    agl_ft_to_msl_m,
    build_wind_profile_variables,
    build_wind_levels,
    interpolate_wind_at_height,
    build_freezing_level,
    format_visibility
)

import pytest


def test_select_nearest_metar():
    reports = [
        {
            "icaoId": "EPWA",
            "lat": 52.1657,
            "lon": 20.9671
        },
        {
            "icaoId": "EPMO",
            "lat": 52.4511,
            "lon": 20.6518
        }
    ]

    nearest = select_nearest_metar(
        reports,
        latitude=52.2297,
        longitude=21.0122
    )

    assert nearest["icaoId"] == "EPWA"


def test_calculate_ceiling_ft_agl():
    clouds = [
        {
            "cover": "SCT",
            "base": 500
        },
        {
            "cover": "BKN",
            "base": 900
        },
        {
            "cover": "OVC",
            "base": 1600
        }
    ]

    ceiling = calculate_ceiling_ft_agl(clouds)

    assert ceiling == 900


def test_build_metar_summary():
    report = {
        "icaoId": "EPWA",
        "name": "Warsaw/Chopin Arpt, MZ, PL",
        "reportTime": "2026-10-28T12:00:00Z",
        "wdir": 140,
        "wspd": 7,
        "wgst": None,
        "visib": "6+",
        "wxString": "-RA BR",
        "clouds": [
            {
                "cover": "OVC",
                "base": 900
            }
        ],
        "fltCat": "IFR",
        "temp": 10,
        "dewp": 8,
        "altim": 1024,
        "rawOb": "METAR EPWA 281200Z 14007KT 9999 -RA BR OVC009 10/08 Q1024"
    }

    summary = build_metar_summary(report)

    assert summary["wind"]["direction_deg"] == 140
    assert summary["wind"]["speed_kt"] == 7
    assert summary["ceiling_ft_agl"] == 900
    assert summary["flight_category"] == "IFR"
    assert summary["temperature_c"] == 10
    assert summary["dewpoint_c"] == 8
    assert summary["qnh_hpa"] == 1024

    assert summary["weather_code"] == "-RA BR"

    assert summary["phenomena"][0]["code"] == "-RA"
    assert summary["phenomena"][0]["description"] == "Light rain"

    assert summary["phenomena"][1]["code"] == "BR"
    assert summary["phenomena"][1]["description"] == "Mist"

def test_decode_weather_string():
    phenomena = decode_weather_string("-RA BR VCTSRA")

    assert phenomena[0]["code"] == "-RA"
    assert phenomena[0]["description"] == "Light rain"

    assert phenomena[1]["code"] == "BR"
    assert phenomena[1]["description"] == "Mist"

    assert phenomena[2]["code"] == "VCTSRA"
    assert phenomena[2]["description"] == "Thunderstorm with rain in vicinity"

def test_feet_to_meters():
    result = feet_to_meters(1000)

    assert result == pytest.approx(304.8)

def test_meters_to_feet():
    result = meters_to_feet(1000)

    assert result == pytest.approx(3280.84)

def test_agl_ft_to_msl_m():
    result = agl_ft_to_msl_m(
        agl_ft=1000,
        terrain_elevation_m=100
    )

    assert result == pytest.approx(404.8)

def test_build_wind_profile_variables():
    variables = build_wind_profile_variables(
        [1000, 975]
    )

    assert variables == [
        "wind_speed_1000hPa",
        "wind_direction_1000hPa",
        "geopotential_height_1000hPa",
        "wind_speed_975hPa",
        "wind_direction_975hPa",
        "geopotential_height_975hPa"
    ]

def test_build_wind_levels():
    profile = {
        "geopotential_height_975hPa": 404.0,
        "wind_speed_975hPa": 6.9,
        "wind_direction_975hPa": 140,

        "geopotential_height_950hPa": 619.0,
        "wind_speed_950hPa": 6.6,
        "wind_direction_950hPa": 143
    }

    levels = build_wind_levels(
        profile,
        [975, 950]
    )

    assert levels == [
        {
            "pressure_hpa": 975,
            "height_msl_m": 404.0,
            "speed_kt": 6.9,
            "direction_deg": 140
        },
        {
            "pressure_hpa": 950,
            "height_msl_m": 619.0,
            "speed_kt": 6.6,
            "direction_deg": 143
        }
    ]

def test_interpolate_wind_at_height():
    wind_levels = [
        {
            "pressure_hpa": 975,
            "height_msl_m": 400,
            "speed_kt": 10,
            "direction_deg": 350
        },
        {
            "pressure_hpa": 950,
            "height_msl_m": 600,
            "speed_kt": 20,
            "direction_deg": 10
        }
    ]

    wind = interpolate_wind_at_height(
        wind_levels,
        target_height_m=500
    )

    assert wind["speed_kt"] == pytest.approx(15)
    assert wind["direction_deg"] == pytest.approx(0)

def test_build_freezing_level():
    profile = {
        "freezing_level_height": 1500
    }

    freezing_level = build_freezing_level(profile)

    assert freezing_level == {
        "height_ft_amsl": 4921
    }


def test_format_visibility_numeric():
    visibility = format_visibility(1.5)

    assert visibility == {
        "statute_miles": 1.5,
        "meters": 2400,
        "display": "2400m"
    }


def test_format_visibility_six_plus():
    visibility = format_visibility("6+")

    assert visibility == {
        "statute_miles": "6+",
        "meters": 10000,
        "display": "10 km or more"
    }


def test_format_visibility_ten_plus():
    visibility = format_visibility("10+")

    assert visibility == {
        "statute_miles": "10+",
        "meters": 16100,
        "display": "16100m or more"
    }
