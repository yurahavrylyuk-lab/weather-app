from math import radians, sin, cos, sqrt, atan2

import httpx

FEET_PER_METER = 3.28084

AVIATION_WEATHER_URL = "https://aviationweather.gov/api/data/metar"
GFS_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_PHENOMENA = {
    "DZ": "drizzle",
    "RA": "rain",
    "SN": "snow",
    "SG": "snow grains",
    "IC": "ice crystals",
    "PL": "ice pellets",
    "GR": "hail",
    "GS": "small hail or snow pellets",
    "UP": "unknown precipitation",
    "BR": "mist",
    "FG": "fog",
    "FU": "smoke",
    "VA": "volcanic ash",
    "DU": "widespread dust",
    "SA": "sand",
    "HZ": "haze",
    "PY": "spray",
    "PO": "dust or sand whirls",
    "SQ": "squalls",
    "FC": "funnel cloud or tornado",
    "SS": "sandstorm",
    "DS": "dust storm"
}

WEATHER_DESCRIPTORS = {
    "MI": "shallow",
    "PR": "partial",
    "BC": "patches",
    "DR": "low drifting",
    "BL": "blowing",
    "SH": "showers",
    "TS": "thunderstorm",
    "FZ": "freezing"
}

WIND_PRESSURE_LEVELS_HPA = [
    1000,
    975,
    950,
    925,
    900,
    875,
    850,
    825,
    800,
    775,
    750,
    725,
    700
]

def feet_to_meters(feet):
    return feet / FEET_PER_METER

def meters_to_feet(meters):
    return meters * FEET_PER_METER

def agl_ft_to_msl_m(agl_ft, terrain_elevation_m):
    agl_m = feet_to_meters(agl_ft)

    return terrain_elevation_m + agl_m


def decode_weather_code(code):
    original_code = code

    intensity = None
    proximity = None
    descriptor = None
    phenomena = []

    if code.startswith("-"):
        intensity = "light"
        code = code[1:]

    elif code.startswith("+"):
        intensity = "heavy"
        code = code[1:]

    if code.startswith("VC"):
        proximity = "vicinity"
        code = code[2:]

    possible_descriptor = code[:2]

    if possible_descriptor in WEATHER_DESCRIPTORS:
        descriptor = WEATHER_DESCRIPTORS[possible_descriptor]
        code = code[2:]

    while len(code) >= 2:
        phenomenon_code = code[:2]

        phenomenon = WEATHER_PHENOMENA.get(
            phenomenon_code
        )

        if phenomenon:
            phenomena.append(phenomenon)

        code = code[2:]

    description_parts = []

    if intensity:
        description_parts.append(intensity)

    if descriptor:
        description_parts.append(descriptor)

    if descriptor == "thunderstorm" and phenomena:
        description_parts.append("with")

    description_parts.extend(phenomena)

    if proximity:
        description_parts.append("in vicinity")

    description = " ".join(description_parts)

    if description:
        description = description[0].upper() + description[1:]

    return {
        "code": original_code,
        "description": description
    }

def decode_weather_string(weather_string):
    if not weather_string:
        return []

    codes = weather_string.split()

    return [
        decode_weather_code(code)
        for code in codes
    ]


def haversine_distance_km(
    latitude_1,
    longitude_1,
    latitude_2,
    longitude_2
):
    earth_radius_km = 6371

    lat_1 = radians(latitude_1)
    lon_1 = radians(longitude_1)
    lat_2 = radians(latitude_2)
    lon_2 = radians(longitude_2)

    difference_lat = lat_2 - lat_1
    difference_lon = lon_2 - lon_1

    a = (
        sin(difference_lat / 2) ** 2
        + cos(lat_1)
        * cos(lat_2)
        * sin(difference_lon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return earth_radius_km * c


def select_nearest_metar(reports, latitude, longitude):
    if not reports:
        return None

    return min(
        reports,
        key=lambda report: haversine_distance_km(
            latitude,
            longitude,
            report["lat"],
            report["lon"]
        )
    )


def fetch_nearby_metars(latitude, longitude):
    search_sizes = [
        1.0,
        2.0,
        3.0,
        4.0
    ]

    headers = {
        "User-Agent": "weather-app-backend/1.0"
    }

    for search_size in search_sizes:
        bbox = (
            f"{latitude - search_size},"
            f"{longitude - search_size},"
            f"{latitude + search_size},"
            f"{longitude + search_size}"
        )

        params = {
            "bbox": bbox,
            "format": "json",
            "hours": 1
        }

        try:
            response = httpx.get(
                AVIATION_WEATHER_URL,
                params=params,
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 204:
                continue

            response.raise_for_status()

            reports = response.json()

            if reports:
                return reports

        except httpx.HTTPError:
            continue

    return []

def calculate_ceiling_ft_agl(clouds, vertical_visibility_ft=None):
    ceiling_bases = []

    for layer in clouds:
        cover = layer.get("cover")
        base = layer.get("base")

        if cover in ("BKN", "OVC") and base is not None:
            ceiling_bases.append(base)

    if vertical_visibility_ft is not None:
        ceiling_bases.append(vertical_visibility_ft)

    if not ceiling_bases:
        return None

    return min(ceiling_bases)

def build_metar_summary(report):
    clouds = report.get("clouds") or []

    phenomena = decode_weather_string(
        report.get("wxString")
    )

    ceiling_ft_agl = calculate_ceiling_ft_agl(
        clouds,
        report.get("vertVis")
    )

    formatted_clouds = []

    for layer in clouds:
        formatted_clouds.append({
            "cover": layer.get("cover"),
            "base_ft_agl": layer.get("base")
        })

    return {
        "station": report.get("icaoId"),
        "station_name": report.get("name"),
        "observed_at": report.get("reportTime"),

        "wind": {
            "direction_deg": report.get("wdir"),
            "speed_kt": report.get("wspd"),
            "gust_kt": report.get("wgst")
        },

        "visibility": format_visibility(
            report.get("visib")
        ),

        "weather_code": report.get("wxString"),
        "phenomena": phenomena,
        "clouds": formatted_clouds,

        "ceiling_ft_agl": ceiling_ft_agl,

        "flight_category": report.get("fltCat"),

        "temperature_c": report.get("temp"),
        "dewpoint_c": report.get("dewp"),
        "qnh_hpa": report.get("altim"),

        "raw": report.get("rawOb")
    }

def build_wind_profile_variables(levels):
    variables = []

    for level in levels:
        variables.append(
            f"wind_speed_{level}hPa"
        )

        variables.append(
            f"wind_direction_{level}hPa"
        )

        variables.append(
            f"geopotential_height_{level}hPa"
        )

    return variables

def fetch_current_wind_profile(latitude, longitude):
    variables = build_wind_profile_variables(
        WIND_PRESSURE_LEVELS_HPA
    )

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(
            variables + ["freezing_level_height"]
        ),
        "wind_speed_unit": "kn",
        "models": "ncep_gfs_seamless"
    }

    response = httpx.get(
        GFS_FORECAST_URL,
        params=params,
        timeout=10.0
    )

    response.raise_for_status()

    data = response.json()

    return data["current"]

def build_wind_levels(profile, pressure_levels):
    wind_levels = []

    for pressure in pressure_levels:
        height = profile.get(
            f"geopotential_height_{pressure}hPa"
        )

        speed = profile.get(
            f"wind_speed_{pressure}hPa"
        )

        direction = profile.get(
            f"wind_direction_{pressure}hPa"
        )

        if (
            height is None
            or speed is None
            or direction is None
        ):
            continue

        wind_levels.append({
            "pressure_hpa": pressure,
            "height_msl_m": height,
            "speed_kt": speed,
            "direction_deg": direction
        })

    wind_levels.sort(
        key=lambda level: level["height_msl_m"]
    )

    return wind_levels

def interpolate_wind_at_height(
    wind_levels,
    target_height_m
):
    for lower, upper in zip(
        wind_levels,
        wind_levels[1:]
    ):
        lower_height = lower["height_msl_m"]
        upper_height = upper["height_msl_m"]

        if lower_height <= target_height_m <= upper_height:
            height_range = upper_height - lower_height

            fraction = (
                target_height_m - lower_height
            ) / height_range

            speed_difference = (
                upper["speed_kt"]
                - lower["speed_kt"]
            )

            speed = (
                lower["speed_kt"]
                + fraction * speed_difference
            )

            direction_difference = (
                (
                    upper["direction_deg"]
                    - lower["direction_deg"]
                    + 180
                )
                % 360
                - 180
            )

            direction = (
                lower["direction_deg"]
                + fraction * direction_difference
            ) % 360

            return {
                "direction_deg": round(direction),
                "speed_kt": round(speed, 1)
            }

    return None

def build_agl_winds(
    wind_profile,
    target_altitudes_msl
):
    wind_levels = build_wind_levels(
        wind_profile,
        WIND_PRESSURE_LEVELS_HPA
    )

    winds = {}

    for agl_ft, target_msl_m in target_altitudes_msl.items():
        winds[f"{agl_ft}_ft_agl"] = (
            interpolate_wind_at_height(
                wind_levels,
                target_msl_m
            )
        )

    return winds

def build_freezing_level(profile):
    height_m = profile.get(
        "freezing_level_height"
    )

    if height_m is None:
        return None

    return {
        "height_ft_amsl": round(
            meters_to_feet(height_m)
        )
    }

def format_visibility(visibility):
    if visibility == "6+":
        return {
            "statute_miles": visibility,
            "meters": 10000,
            "display": "10 km or more"
        }

    if isinstance(visibility, str) and visibility.endswith("+"):
        try:
            visibility_miles = float(
                visibility.removesuffix("+")
            )

            meters = round(
                visibility_miles * 1609.344 / 100
            ) * 100

            return {
                "statute_miles": visibility,
                "meters": meters,
                "display": f"{meters}m or more"
            }

        except ValueError:
            pass

    try:
        visibility_miles = float(visibility)

        meters = round(
            visibility_miles * 1609.344 / 100
        ) * 100

        return {
            "statute_miles": visibility,
            "meters": meters,
            "display": f"{meters}m"
        }

    except (TypeError, ValueError):
        return {
            "statute_miles": visibility,
            "meters": None,
            "display": "N/A"
        }
